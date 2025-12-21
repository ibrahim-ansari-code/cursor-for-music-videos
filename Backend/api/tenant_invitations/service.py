"""
Tenant Invitation Service

Business logic for managing tenant portal invitations.
"""
import hashlib
import hmac
import logging
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from uuid import UUID as PythonUUID
from Backend.api.tenant_portal_seats.service import SeatManagementService


def normalize_email(email: str) -> str:
    """
    Apply RFC-compliant normalization to an email address.
    
    - Strips leading/trailing whitespace
    - Converts to lowercase
    - Applies Unicode NFC normalization (handles Unicode equivalents)
    
    Args:
        email: Raw email address
        
    Returns:
        Normalized email address for comparison
    """
    # Strip whitespace
    normalized = email.strip()
    # Apply Unicode NFC normalization (standard form for text comparison)
    normalized = unicodedata.normalize("NFC", normalized)
    # Lowercase (email local parts are technically case-sensitive per RFC,
    # but in practice all major providers treat them as case-insensitive)
    normalized = normalized.lower()
    return normalized

import sentry_sdk
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col

from Backend.api.notifications.email_templates import (
    BrikliEmailTemplate,
    EmailCTA,
    EmailMetadataRow,
    EmailNotice,
    EmailSection,
)
from Backend.api.notifications.sendgrid_service import SendGridService
from Backend.api.tenant_invitations.schemas import (
    InvitationAcceptResponse,
    InvitationCreateRequest,
    InvitationListResponse,
    InvitationResendResponse,
    InvitationResponse,
    InvitationRevokeResponse,
    InvitationValidateResponse,
)
from Backend.config import settings
from Backend.models.enums import TenantType
from Backend.models.tenant import Tenant
from Backend.models.tenant_portal_invitation import (
    InvitationStatus,
    TenantPortalInvitation,
    hash_token,
)
from Backend.models.user import User

logger = logging.getLogger(__name__)

# Invitation token byte length (32 bytes = 256 bits of entropy)
# secrets.token_urlsafe(32) produces ~43 character tokens
TOKEN_LENGTH = 32
# Invitation validity period
INVITATION_EXPIRY_DAYS = 7


class TenantInvitationService:
    """Service for managing tenant portal invitations."""

    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        landlord_id: PythonUUID,
        request: InvitationCreateRequest,
    ) -> InvitationResponse | None:
        """
        Create a new tenant portal invitation.
        
        Args:
            db: Database session
            landlord_id: UUID of the landlord creating the invitation
            request: Invitation create request
            
        Returns:
            InvitationResponse or None if tenant not found/not owned
        """
        try:
            # Verify tenant exists and belongs to this landlord
            tenant_result = await db.execute(
                select(Tenant)
                .where(col(Tenant.id) == request.tenant_id)
                .where(col(Tenant.landlord_id) == landlord_id)
                .options(
                    selectinload(getattr(Tenant, "current_property")),
                    selectinload(getattr(Tenant, "assigned_units")),
                )
            )
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                logger.warning(
                    f"Tenant {request.tenant_id} not found or not owned by landlord {landlord_id}"
                )
                return None
            
            if not tenant.email:
                logger.warning(f"Tenant {request.tenant_id} has no email address")
                return None
            
            # Check if tenant already has a linked user account
            if tenant.user_id:
                logger.info(
                    f"Tenant {request.tenant_id} already has portal access (user_id: {tenant.user_id})"
                )
                return None
            
            # First, expire any pending invitations that have passed their expiry date
            now = datetime.now(timezone.utc)
            await db.execute(
                update(TenantPortalInvitation)
                .where(col(TenantPortalInvitation.tenant_id) == request.tenant_id)
                .where(col(TenantPortalInvitation.status) == InvitationStatus.PENDING)
                .where(col(TenantPortalInvitation.expires_at) <= now)
                .values(status=InvitationStatus.EXPIRED, updated_at=now)
            )
            
            # Check for existing valid pending invitation
            existing_result = await db.execute(
                select(TenantPortalInvitation)
                .where(col(TenantPortalInvitation.tenant_id) == request.tenant_id)
                .where(col(TenantPortalInvitation.status) == InvitationStatus.PENDING)
                .where(col(TenantPortalInvitation.expires_at) > now)
            )
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                # Return existing invitation - but resend email since user is clicking "Invite"
                logger.info(
                    f"Found existing invitation for tenant {request.tenant_id}, resending email"
                )
                # Generate new token for security (old token may be compromised)
                plaintext_token = secrets.token_urlsafe(TOKEN_LENGTH)
                existing.invitation_token = hash_token(plaintext_token)
                existing.updated_at = datetime.now(timezone.utc)
                # Extend expiry when resending (new token = fresh 7-day window)
                existing.expires_at = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)
                await db.commit()
                await db.refresh(existing)

                # Send email with new token
                await TenantInvitationService._send_invitation_email(
                    invitation=existing,
                    tenant=tenant,
                    landlord_id=landlord_id,
                    db=db,
                    plaintext_token=plaintext_token,
                )

                return await TenantInvitationService._build_invitation_response(existing, tenant)
            
            # Generate secure token - store hash, send plaintext to user
            plaintext_token = secrets.token_urlsafe(TOKEN_LENGTH)
            token_hash_value = hash_token(plaintext_token)
            
            # Create invitation with hashed token
            invitation = TenantPortalInvitation(
                tenant_id=request.tenant_id,
                invited_by=landlord_id,
                invitation_token=token_hash_value,  # Store only the hash
                email=tenant.email,
                status=InvitationStatus.PENDING,
                expires_at=now + timedelta(days=INVITATION_EXPIRY_DAYS),
            )
            
            db.add(invitation)
            await db.commit()
            await db.refresh(invitation)
            
            # Send invitation email with plaintext token
            await TenantInvitationService._send_invitation_email(
                invitation=invitation,
                tenant=tenant,
                landlord_id=landlord_id,
                db=db,
                plaintext_token=plaintext_token,  # Pass plaintext for email URL
            )
            
            logger.info(
                f"Created invitation {invitation.id} for tenant {tenant.id}"
            )
            
            return await TenantInvitationService._build_invitation_response(invitation, tenant)
            
        except Exception as e:
            logger.exception(f"Error creating invitation for tenant {request.tenant_id}")
            sentry_sdk.capture_exception(e)
            await db.rollback()
            raise

    @staticmethod
    async def list_invitations(
        db: AsyncSession,
        landlord_id: PythonUUID,
        status_filter: InvitationStatus | None = None,
    ) -> InvitationListResponse:
        """
        List all invitations created by a landlord.
        
        Args:
            db: Database session
            landlord_id: UUID of the landlord
            status_filter: Optional status filter
            
        Returns:
            List of invitations
        """
        try:
            query = (
                select(TenantPortalInvitation)
                .where(col(TenantPortalInvitation.invited_by) == landlord_id)
                .options(selectinload(getattr(TenantPortalInvitation, "tenant")))
                .order_by(col(TenantPortalInvitation.created_at).desc())
            )
            
            if status_filter:
                query = query.where(col(TenantPortalInvitation.status) == status_filter)
            
            result = await db.execute(query)
            invitations = result.scalars().all()
            
            responses = []
            for inv in invitations:
                response = await TenantInvitationService._build_invitation_response(
                    inv, inv.tenant
                )
                responses.append(response)
            
            return InvitationListResponse(
                invitations=responses,
                total=len(responses),
            )
            
        except Exception as e:
            logger.exception(f"Error listing invitations for landlord {landlord_id}")
            sentry_sdk.capture_exception(e)
            raise

    @staticmethod
    async def get_invitation_for_tenant(
        db: AsyncSession,
        landlord_id: PythonUUID,
        tenant_id: int,
    ) -> InvitationResponse | None:
        """
        Get the most recent invitation for a specific tenant.
        
        This is more efficient than listing all invitations and filtering
        client-side when you only need one tenant's status.
        
        Args:
            db: Database session
            landlord_id: UUID of the landlord (for authorization)
            tenant_id: ID of the tenant to get invitation for
            
        Returns:
            InvitationResponse or None if no invitation exists
        """
        try:
            # Get the most recent invitation for this tenant (owned by landlord)
            result = await db.execute(
                select(TenantPortalInvitation)
                .where(col(TenantPortalInvitation.tenant_id) == tenant_id)
                .where(col(TenantPortalInvitation.invited_by) == landlord_id)
                .options(selectinload(getattr(TenantPortalInvitation, "tenant")))
                .order_by(col(TenantPortalInvitation.created_at).desc())
                .limit(1)
            )
            invitation = result.scalar_one_or_none()
            
            if not invitation:
                return None
            
            return await TenantInvitationService._build_invitation_response(
                invitation, invitation.tenant
            )
            
        except Exception as e:
            logger.exception(f"Error getting invitation for tenant {tenant_id}")
            sentry_sdk.capture_exception(e)
            raise

    @staticmethod
    async def revoke_invitation(
        db: AsyncSession,
        landlord_id: PythonUUID,
        invitation_id: PythonUUID,
    ) -> InvitationRevokeResponse:
        """
        Revoke a pending invitation.
        
        Args:
            db: Database session
            landlord_id: UUID of the landlord
            invitation_id: UUID of the invitation to revoke
            
        Returns:
            Revoke response
        """
        try:
            result = await db.execute(
                select(TenantPortalInvitation)
                .where(col(TenantPortalInvitation.id) == invitation_id)
                .where(col(TenantPortalInvitation.invited_by) == landlord_id)
            )
            invitation = result.scalar_one_or_none()
            
            if not invitation:
                return InvitationRevokeResponse(
                    success=False,
                    message="Invitation not found",
                )
            
            if invitation.status != InvitationStatus.PENDING:
                return InvitationRevokeResponse(
                    success=False,
                    message=f"Cannot revoke invitation with status '{invitation.status}'",
                )
            
            invitation.status = InvitationStatus.REVOKED
            invitation.revoked_at = datetime.now(timezone.utc)
            invitation.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            logger.info(f"Revoked invitation {invitation_id}")
            
            return InvitationRevokeResponse(
                success=True,
                message="Invitation revoked successfully",
            )
            
        except Exception as e:
            logger.exception(f"Error revoking invitation {invitation_id}")
            sentry_sdk.capture_exception(e)
            await db.rollback()
            raise

    @staticmethod
    async def resend_invitation(
        db: AsyncSession,
        landlord_id: PythonUUID,
        invitation_id: PythonUUID,
    ) -> InvitationResendResponse:
        """
        Resend an invitation email and extend expiry.
        
        Args:
            db: Database session
            landlord_id: UUID of the landlord
            invitation_id: UUID of the invitation
            
        Returns:
            Resend response
        """
        try:
            result = await db.execute(
                select(TenantPortalInvitation)
                .where(col(TenantPortalInvitation.id) == invitation_id)
                .where(col(TenantPortalInvitation.invited_by) == landlord_id)
                .options(
                    selectinload(getattr(TenantPortalInvitation, "tenant"))
                    .selectinload(getattr(Tenant, "current_property")),
                    selectinload(getattr(TenantPortalInvitation, "tenant"))
                    .selectinload(getattr(Tenant, "assigned_units")),
                )
            )
            invitation = result.scalar_one_or_none()
            
            if not invitation:
                return InvitationResendResponse(
                    success=False,
                    message="Invitation not found",
                )
            
            if invitation.status not in [InvitationStatus.PENDING, InvitationStatus.EXPIRED]:
                return InvitationResendResponse(
                    success=False,
                    message=f"Cannot resend invitation with status '{invitation.status}'",
                )
            
            # Generate new token (store hash, send plaintext) and extend expiry
            plaintext_token = secrets.token_urlsafe(TOKEN_LENGTH)
            invitation.invitation_token = hash_token(plaintext_token)  # Store only the hash
            invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)
            invitation.status = InvitationStatus.PENDING
            invitation.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            # Resend email - tenant is guaranteed to exist since invitation exists
            tenant = invitation.tenant
            if tenant:
                await TenantInvitationService._send_invitation_email(
                    invitation=invitation,
                    tenant=tenant,
                    landlord_id=landlord_id,
                    db=db,
                    plaintext_token=plaintext_token,  # Pass plaintext for email URL
                )
            
            logger.info(f"Resent invitation {invitation_id}")
            
            return InvitationResendResponse(
                success=True,
                message="Invitation resent successfully",
                new_expires_at=invitation.expires_at,
            )
            
        except Exception as e:
            logger.exception(f"Error resending invitation {invitation_id}")
            sentry_sdk.capture_exception(e)
            await db.rollback()
            raise

    @staticmethod
    async def validate_token(
        db: AsyncSession,
        token: str,
    ) -> InvitationValidateResponse:
        """
        Validate an invitation token (public endpoint for tenant portal).
        
        Args:
            db: Database session
            token: Plaintext invitation token from URL
            
        Returns:
            Validation response with tenant/landlord info
        """
        try:
            # Hash the incoming token to compare with stored hash
            token_hash_value = hash_token(token)
            
            result = await db.execute(
                select(TenantPortalInvitation)
                .where(col(TenantPortalInvitation.invitation_token) == token_hash_value)
                .options(
                    selectinload(getattr(TenantPortalInvitation, "tenant"))
                    .selectinload(getattr(Tenant, "current_property")),
                    selectinload(getattr(TenantPortalInvitation, "tenant"))
                    .selectinload(getattr(Tenant, "assigned_units")),
                    selectinload(getattr(TenantPortalInvitation, "inviter")),
                )
            )
            invitation = result.scalar_one_or_none()
            
            if not invitation:
                return InvitationValidateResponse(
                    valid=False,
                    message="Invalid invitation link",
                )
            
            # Check if expired
            if invitation.expires_at <= datetime.now(timezone.utc):
                # Update status if not already expired
                if invitation.status == InvitationStatus.PENDING:
                    invitation.status = InvitationStatus.EXPIRED
                    invitation.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                
                return InvitationValidateResponse(
                    valid=False,
                    message="This invitation has expired. Please ask your landlord to send a new one.",
                )
            
            # Check status
            if invitation.status != InvitationStatus.PENDING:
                status_messages = {
                    InvitationStatus.ACCEPTED: "This invitation has already been accepted.",
                    InvitationStatus.REVOKED: "This invitation has been revoked.",
                    InvitationStatus.EXPIRED: "This invitation has expired.",
                }
                return InvitationValidateResponse(
                    valid=False,
                    message=status_messages.get(
                        invitation.status,
                        "This invitation is no longer valid.",
                    ),
                )
            
            # Build tenant name
            tenant = invitation.tenant
            if not tenant:
                return InvitationValidateResponse(
                    valid=False,
                    message="Tenant record not found.",
                )
            
            if tenant.tenant_type == TenantType.COMPANY:
                tenant_name = tenant.company_name or "Company Tenant"
            else:
                tenant_name = f"{tenant.first_name or ''} {tenant.last_name or ''}".strip() or "Tenant"
            
            # Build landlord name
            inviter = invitation.inviter
            landlord_name = (
                f"{inviter.first_name or ''} {inviter.last_name or ''}".strip()
                if inviter
                else "Your Landlord"
            )
            
            # Get property/unit info from direct assignments
            property_name = None
            unit_name = None
            
            try:
                if tenant.current_property:
                    property_name = tenant.current_property.name
                
                if tenant.assigned_units and len(tenant.assigned_units) > 0:
                    unit_name = tenant.assigned_units[0].name
            except Exception as e:
                logger.error(f"Error loading property/unit for tenant {tenant.id}: {e}")
                sentry_sdk.capture_exception(e)
            
            return InvitationValidateResponse(
                valid=True,
                email=invitation.email,
                tenant_name=tenant_name,
                landlord_name=landlord_name,
                property_name=property_name,
                unit_name=unit_name,
                expires_at=invitation.expires_at,
            )
            
        except Exception as e:
            logger.exception("Error validating invitation token")
            sentry_sdk.capture_exception(e)
            return InvitationValidateResponse(
                valid=False,
                message="An error occurred. Please try again.",
            )

    @staticmethod
    async def accept_invitation(
        db: AsyncSession,
        token: str,
        user_id: PythonUUID,
    ) -> InvitationAcceptResponse:
        """
        Accept an invitation and link tenant to user account.
        
        Args:
            db: Database session
            token: Plaintext invitation token from request
            user_id: UUID of the authenticated tenant user
            
        Returns:
            Accept response
        """
        try:
            # Hash the incoming token to compare with stored hash
            token_hash_value = hash_token(token)
            
            # Get invitation by hashed token
            result = await db.execute(
                select(TenantPortalInvitation)
                .where(col(TenantPortalInvitation.invitation_token) == token_hash_value)
                .options(selectinload(getattr(TenantPortalInvitation, "tenant")))
            )
            invitation = result.scalar_one_or_none()
            
            if not invitation:
                return InvitationAcceptResponse(
                    success=False,
                    message="Invalid invitation",
                )
            
            # Validate invitation
            if invitation.status != InvitationStatus.PENDING:
                return InvitationAcceptResponse(
                    success=False,
                    message="This invitation is no longer valid",
                )
            
            if invitation.expires_at <= datetime.now(timezone.utc):
                invitation.status = InvitationStatus.EXPIRED
                invitation.updated_at = datetime.now(timezone.utc)
                await db.commit()
                return InvitationAcceptResponse(
                    success=False,
                    message="This invitation has expired",
                )
            
            # Verify user email matches invitation email
            user_result = await db.execute(
                select(User).where(col(User.id) == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                # Log specifics server-side, return generic message to prevent enumeration
                logger.warning(f"Accept invitation failed: user {user_id} not found")
                return InvitationAcceptResponse(
                    success=False,
                    message="Unable to accept invitation. Please try again or contact support.",
                )
            
            # Email must match (RFC-compliant normalization)
            # Use generic error message to prevent account enumeration attacks
            if normalize_email(user.email) != normalize_email(invitation.email):
                logger.warning(
                    f"Accept invitation failed: email mismatch for user {user_id} "
                    f"(invitation email hash: {hash_token(invitation.email)[:8]})"
                )
                return InvitationAcceptResponse(
                    success=False,
                    message="Unable to accept invitation. Please try again or contact support.",
                )
            
            # Check tenant isn't already linked
            tenant = invitation.tenant
            if not tenant:
                return InvitationAcceptResponse(
                    success=False,
                    message="Tenant record not found",
                )
            
            if tenant.user_id:
                return InvitationAcceptResponse(
                    success=False,
                    message="This tenant record is already linked to an account",
                )

            # ✅ CRITICAL: Check seat availability BEFORE linking tenant to user account
            # This is the enforcement point - seats are consumed when tenant.user_id is set

            availability = await SeatManagementService.get_seat_availability(
                landlord_user_id=invitation.invited_by,
                session=db
            )

            if availability["available"] <= 0:
                logger.warning(
                    f"Seat limit reached for landlord {invitation.invited_by} | "
                    f"Used: {availability['used']}, Limit: {availability['limit']}"
                )
                return InvitationAcceptResponse(
                    success=False,
                    message=(
                        f"Your landlord has reached their tenant portal seat limit "
                        f"({availability['limit']} seats). Please contact your landlord "
                        f"to purchase additional seats before accepting this invitation."
                    ),
                )

            # Link tenant to user (consumes seat automatically via real-time counting)
            tenant.user_id = user_id
            tenant.updated_at = datetime.now(timezone.utc)
            
            # Update invitation status
            invitation.status = InvitationStatus.ACCEPTED
            invitation.accepted_at = datetime.now(timezone.utc)
            invitation.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            logger.info(
                f"Tenant {tenant.id} linked to user {user_id} via invitation {invitation.id}"
            )
            
            return InvitationAcceptResponse(
                success=True,
                message="Welcome to the Tenant Portal! Your account has been linked successfully.",
                tenant_id=tenant.id,
            )
            
        except Exception as e:
            logger.exception("Error accepting invitation")
            sentry_sdk.capture_exception(e)
            await db.rollback()
            return InvitationAcceptResponse(
                success=False,
                message="An error occurred. Please try again.",
            )

    @staticmethod
    async def _build_invitation_response(
        invitation: TenantPortalInvitation,
        tenant: Tenant | None,
    ) -> InvitationResponse:
        """Build invitation response from model."""
        tenant_name = None
        tenant_email = None
        
        if tenant:
            if tenant.tenant_type == TenantType.COMPANY:
                tenant_name = tenant.company_name
            else:
                tenant_name = f"{tenant.first_name or ''} {tenant.last_name or ''}".strip()
            tenant_email = tenant.email
        
        return InvitationResponse(
            id=invitation.id,
            tenant_id=invitation.tenant_id,
            invited_by=invitation.invited_by,
            email=invitation.email,
            status=invitation.status,
            created_at=invitation.created_at,
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
            revoked_at=invitation.revoked_at,
            tenant_name=tenant_name,
            tenant_email=tenant_email,
        )

    @staticmethod
    async def _send_invitation_email(
        invitation: TenantPortalInvitation,
        tenant: Tenant,
        landlord_id: PythonUUID,
        db: AsyncSession,
        plaintext_token: str,
    ) -> bool:
        """
        Send invitation email to tenant.
        
        Args:
            invitation: The invitation record
            tenant: The tenant record
            landlord_id: UUID of the landlord
            db: Database session
            plaintext_token: The plaintext token to include in the email URL
            
        Returns:
            True if email sent successfully
        """
        try:
            # Get landlord info
            landlord_result = await db.execute(
                select(User).where(col(User.id) == landlord_id)
            )
            landlord = landlord_result.scalar_one_or_none()
            
            landlord_name = "Your Landlord"
            if landlord:
                landlord_name = f"{landlord.first_name or ''} {landlord.last_name or ''}".strip() or "Your Landlord"
            
            # Build tenant name
            if tenant.tenant_type == TenantType.COMPANY:
                tenant_name = tenant.company_name or "Tenant"
            else:
                tenant_name = tenant.first_name or "Tenant"
            
            # Get property/unit info - fetch separately to avoid lazy loading issues
            property_name = None
            unit_name = None
            
            if tenant.current_property_id:
                try:
                    from Backend.models.property import Property
                    from Backend.models.units import PropertyUnit
                    
                    property_result = await db.execute(
                        select(Property).where(col(Property.id) == tenant.current_property_id)
                    )
                    property_obj = property_result.scalar_one_or_none()
                    if property_obj:
                        property_name = property_obj.name
                        
                        # Get unit if tenant has one assigned
                        unit_result = await db.execute(
                            select(PropertyUnit)
                            .where(col(PropertyUnit.tenant_id) == tenant.id)
                            .limit(1)
                        )
                        unit_obj = unit_result.scalar_one_or_none()
                        if unit_obj:
                            unit_name = unit_obj.name
                except Exception as e:
                    logger.warning(f"Error loading property/unit for email: {e}")
            
            # Build invitation URL for Tenant Portal with plaintext token
            # Use URL fragment (#token=) instead of query param (?token=) to prevent:
            # - Token leakage via browser history, referrer headers, and server logs
            # - The fragment is only accessible via JavaScript, never sent to server in URL
            base_url = "http://localhost:5174" if settings.ENVIRONMENT == "development" else settings.TENANT_PORTAL_URL
            invitation_url = f"{base_url}/accept-invite#token={plaintext_token}"
            
            # Build email content
            sections = [
                EmailSection(
                    text=f"Your landlord, {landlord_name}, has invited you to join the Brikli Tenant Portal."
                ),
                EmailSection(
                    text="The Tenant Portal gives you easy access to:"
                ),
            ]
            
            # Add metadata
            metadata_rows = []
            if property_name:
                metadata_rows.append(
                    EmailMetadataRow(label="Property", value=property_name, emoji="🏠")
                )
            if unit_name:
                metadata_rows.append(
                    EmailMetadataRow(label="Unit", value=unit_name, emoji="🚪")
                )
            metadata_rows.append(
                EmailMetadataRow(
                    label="Features",
                    value="Pay rent, view lease documents, submit maintenance requests",
                    emoji="✨",
                )
            )
            
            # CTA button
            cta = EmailCTA(
                text="Accept Invitation",
                url=invitation_url,
            )
            
            # Expiry notice
            days_until_expiry = (invitation.expires_at - datetime.now(timezone.utc)).days
            notice = EmailNotice(
                emoji="⏰",
                title="Invitation Expires Soon",
                message=f"This invitation will expire in {days_until_expiry} days. Click the button above to get started!",
                color="#3b82f6",
                bg_color="#eff6ff",
            )
            
            # Generate HTML email
            html_body = BrikliEmailTemplate.create_email(
                title="You're Invited to the Tenant Portal",
                greeting=f"Hi {tenant_name},",
                sections=sections,
                metadata=metadata_rows,
                cta=cta,
                notice=notice,
                footer_note="If you didn't expect this invitation, you can safely ignore this email.",
            )
            
            # Send via SendGrid
            # Use HMAC with EMAIL_CORRELATION_SECRET (isolated from JWT secret)
            # This prevents enumeration attacks if email logs are exposed
            correlation_id = hmac.new(
                key=settings.EMAIL_CORRELATION_SECRET.encode(),
                msg=str(invitation.id).encode(),
                digestmod=hashlib.sha256,
            ).hexdigest()[:16]
            
            success = await SendGridService.send_raw_email(
                to_email=invitation.email,
                to_name=tenant_name,
                subject=f"Your landlord, {landlord_name}, has invited you to the Brikli Tenant Portal",
                html_content=html_body,
                metadata={
                    "correlation_id": correlation_id,
                    "email_type": "tenant_invitation",
                },
            )
            
            if success:
                logger.info(f"Invitation email sent to {invitation.email}")
            else:
                logger.warning(f"Failed to send invitation email to {invitation.email}")
            
            return success
            
        except Exception as e:
            logger.exception(f"Error sending invitation email to {invitation.email}")
            sentry_sdk.capture_exception(e)
            return False
