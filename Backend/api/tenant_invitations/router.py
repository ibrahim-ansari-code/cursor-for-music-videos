"""
Tenant Invitations API Router

API endpoints for managing tenant portal invitations.
Serves both landlord portal (app.brikli.com) and tenant portal (tenant.brikli.com).

Note: Rate limiting for public endpoints should be handled at infrastructure level
(nginx, cloudflare, API gateway) or via the license/seat mechanism (future).
"""
import logging
from uuid import UUID as PythonUUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from Backend.api.auth.dependencies import (
    get_current_user,
    get_current_user_no_subscription_check,
)
from Backend.api.tenant_invitations.schemas import (
    InvitationAcceptRequest,
    InvitationAcceptResponse,
    InvitationCreateRequest,
    InvitationListResponse,
    InvitationResendResponse,
    InvitationResponse,
    InvitationRevokeResponse,
    InvitationValidateRequest,
    InvitationValidateResponse,
)
from Backend.api.tenant_invitations.service import TenantInvitationService
from Backend.database import get_session
from Backend.models.tenant_portal_invitation import InvitationStatus
from Backend.models.user import User
from Backend.models.enums import UserType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenant-invitations", tags=["Tenant Invitations"])


# =============================================================================
# LANDLORD ENDPOINTS (app.brikli.com)
# =============================================================================

@router.post(
    "/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tenant portal invitation",
    description="Send an invitation to a tenant to join the portal. Only landlords can create invitations.",
)
async def create_invitation(
    request: InvitationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> InvitationResponse:
    """
    Create and send a tenant portal invitation.
    
    - Validates tenant belongs to the landlord
    - Checks if tenant already has portal access
    - Creates invitation with secure token
    - Sends invitation email with link to tenant.brikli.com
    """
    # Verify user is a landlord
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only landlords can invite tenants to the portal",
        )
    
    result = await TenantInvitationService.create_invitation(
        db=db,
        landlord_id=current_user.id,
        request=request,
    )
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create invitation. The tenant may not exist, may not have an email, or may already have portal access.",
        )
    
    return result


@router.get(
    "/invitations",
    response_model=InvitationListResponse,
    summary="List tenant portal invitations",
    description="List all invitations created by the current landlord.",
)
async def list_invitations(
    status_filter: InvitationStatus | None = Query(
        None,
        description="Filter by invitation status",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> InvitationListResponse:
    """List all invitations for the current landlord."""
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenants cannot manage invitations",
        )
    
    return await TenantInvitationService.list_invitations(
        db=db,
        landlord_id=current_user.id,
        status_filter=status_filter,
    )


@router.get(
    "/invitations/tenant/{tenant_id}",
    response_model=InvitationResponse | None,
    summary="Get invitation for a specific tenant",
    description="Get the most recent invitation status for a specific tenant. More efficient than listing all invitations.",
)
async def get_invitation_for_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> InvitationResponse | None:
    """Get the most recent invitation for a specific tenant."""
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenants cannot view landlord invitations",
        )
    
    return await TenantInvitationService.get_invitation_for_tenant(
        db=db,
        landlord_id=current_user.id,
        tenant_id=tenant_id,
    )


@router.delete(
    "/invitations/{invitation_id}",
    response_model=InvitationRevokeResponse,
    summary="Revoke an invitation",
    description="Revoke a pending invitation so it can no longer be used.",
)
async def revoke_invitation(
    invitation_id: PythonUUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> InvitationRevokeResponse:
    """Revoke a pending invitation."""
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenants cannot revoke invitations",
        )
    
    return await TenantInvitationService.revoke_invitation(
        db=db,
        landlord_id=current_user.id,
        invitation_id=invitation_id,
    )


@router.post(
    "/invitations/{invitation_id}/resend",
    response_model=InvitationResendResponse,
    summary="Resend an invitation",
    description="Resend the invitation email and extend the expiry period.",
)
async def resend_invitation(
    invitation_id: PythonUUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> InvitationResendResponse:
    """Resend an invitation email."""
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenants cannot resend invitations",
        )
    
    return await TenantInvitationService.resend_invitation(
        db=db,
        landlord_id=current_user.id,
        invitation_id=invitation_id,
    )


# =============================================================================
# TENANT ENDPOINTS (tenant.brikli.com)
# =============================================================================

@router.get(
    "/validate-invite",
    response_model=InvitationValidateResponse,
    summary="Validate invitation token",
    description="Public endpoint to validate an invitation token and get tenant info.",
)
async def validate_invitation(
    token: str = Query(
        ...,
        min_length=40,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Invitation token (URL-safe base64)",
    ),
    db: AsyncSession = Depends(get_session),
) -> InvitationValidateResponse:
    """
    Validate an invitation token (public endpoint for tenant portal).
    
    This endpoint is called by the tenant portal when a user visits
    tenant.brikli.com/accept-invite?token=xxx
    
    Returns tenant and landlord info to display on the registration page.
    """
    return await TenantInvitationService.validate_token(
        db=db,
        token=token,
    )


@router.post(
    "/accept-invite",
    response_model=InvitationAcceptResponse,
    summary="Accept invitation and link account",
    description="Accept an invitation and link the tenant record to the user account.",
)
async def accept_invitation(
    request: InvitationAcceptRequest,
    current_user: User = Depends(get_current_user_no_subscription_check),
    db: AsyncSession = Depends(get_session),
) -> InvitationAcceptResponse:
    """
    Accept an invitation and link tenant to user account.
    
    This endpoint is called after the tenant has:
    1. Validated the invitation token
    2. Created a Supabase account (or signed in to existing one)
    3. Authenticated with the backend
    
    The user's email must match the invitation email.
    Upon success, the tenant record is linked to the user account.
    """
    # Verify user is a tenant type (or will become one)
    # This endpoint should only be used by tenant users
    
    return await TenantInvitationService.accept_invitation(
        db=db,
        token=request.token,
        user_id=current_user.id,
    )


# =============================================================================
# TENANT STATUS ENDPOINTS (for both portals)
# =============================================================================

@router.get(
    "/status",
    summary="Get portal access status",
    description="Check if the current user has tenant portal access.",
)
async def get_portal_status(
    current_user: User = Depends(get_current_user_no_subscription_check),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Check portal access status for the current user.
    
    Used by both landlord portal (to check tenant status) and
    tenant portal (to verify account linking).
    """
    from sqlalchemy import select
    from Backend.models.tenant import Tenant
    
    # For tenant users, check if they have a linked tenant record
    if current_user.user_type == UserType.TENANT:
        result = await db.execute(
            select(Tenant).where(col(Tenant.user_id) == current_user.id)
        )
        tenant = result.scalar_one_or_none()
        
        # Note: landlord_id intentionally excluded to minimize information exposure
        return {
            "has_portal_access": tenant is not None,
            "tenant_id": tenant.id if tenant else None,
            "property_name": tenant.current_property.name if tenant and tenant.current_property else None,
        }
    
    # For landlords, return their tenant count with portal access
    result = await db.execute(
        select(Tenant)
        .where(col(Tenant.landlord_id) == current_user.id)
        .where(col(Tenant.user_id).isnot(None))
    )
    tenants_with_access = result.scalars().all()
    
    return {
        "user_type": "landlord",
        "tenants_with_portal_access": len(tenants_with_access),
    }

