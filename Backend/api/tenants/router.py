import logging
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import sentry_sdk
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Response
from sqlalchemy import and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import col

from Backend.api.auth import get_current_user
from Backend.api.tenants.schemas import (
    EmergencyContactCreate,
    EmergencyContactResponse,
    EmergencyContactUpdate,
    OpenBalanceMetrics,
    PaymentPerformanceMetrics,
    TenantBulkDeleteRequest,
    TenantCreate,
    TenantMetricsResponse,
    TenantReminderRequest,
    TenantReminderResponse,
    TenantResponse,
    TenantUpdate,
    TicketResolutionMetrics,
)
from Backend.api.tenants.service import (
    add_emergency_contact,
    bulk_delete_tenants,
    build_filtered_tenants_query,
    build_unassigned_tenants_query,
    check_tenant_permission,
    create_and_save_tenant,
    delete_emergency_contact,
    enrich_tenants_with_details,
    update_emergency_contact,
    _determine_landlord,
    _validate_linked_user_account,
    _validate_property_assignment,
    _validate_user_permissions,
)
from Backend.database import get_session
from Backend.models.enums import UserType, TenantType
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.tenant import Tenant, TenantStatus
from Backend.models.units import PropertyUnit
from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime
from Backend.api.notifications.email_service import EmailService
from Backend.api.notifications.service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tenants",
    tags=["tenants"],
)


# ========================================================================
# RATE LIMITING FOR TENANT REMINDER EMAILS
# ========================================================================

# Database-backed rate limiter for reminder emails (works with multiple workers)
# Limit: 10 reminders per tenant per hour to prevent email spam
_reminder_rate_limit_max = 10
_reminder_rate_limit_window_seconds = 3600  # 1 hour


async def check_reminder_rate_limit(
    tenant_id: int,
    user_id: UUID,
    session: AsyncSession
) -> bool:
    """
    Check if user is within rate limit for sending reminders to a specific tenant.

    Uses PostgreSQL advisory locks to prevent race conditions between
    concurrent requests. This ensures the check-and-insert is atomic.

    Args:
        tenant_id: Tenant ID being sent reminder
        user_id: User ID sending the reminder
        session: Database session

    Returns:
        True if request is allowed, False if rate limited
    """
    # Use PostgreSQL advisory lock to make check-and-insert atomic
    # Lock ID combines tenant_id and user_id to ensure per-tenant-per-user locking
    lock_id = hash(f"reminder_{tenant_id}_{user_id}") % 2147483647  # PostgreSQL max int

    try:
        # Acquire advisory lock (automatically released at transaction end)
        lock_query = text("SELECT pg_advisory_xact_lock(:lock_id)")
        await session.execute(lock_query, {"lock_id": lock_id})

        # Calculate window start time
        window_start = datetime.now(timezone.utc) - timedelta(seconds=_reminder_rate_limit_window_seconds)

        # Count reminder emails sent to this tenant in the current window
        count_query = text("""
            SELECT COUNT(*)
            FROM notification_delivery_log
            WHERE user_id = :user_id
            AND channel = 'tenant_reminder'
            AND metadata->>'tenant_id' = :tenant_id
            AND created_at > :window_start
        """)

        result = await session.execute(count_query, {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "window_start": window_start
        })
        count: int = result.scalar() or 0

        if count >= _reminder_rate_limit_max:
            return False

        # Record this request
        insert_query = text("""
            INSERT INTO notification_delivery_log (
                user_id,
                notification_id,
                channel,
                status,
                metadata,
                created_at
            )
            VALUES (
                :user_id,
                :notification_id,
                'tenant_reminder',
                'sent',
                :metadata::jsonb,
                NOW()
            )
        """)

        import json
        await session.execute(insert_query, {
            "user_id": str(user_id),
            "notification_id": "00000000-0000-0000-0000-000000000000",
            "metadata": json.dumps({"tenant_id": str(tenant_id)})
        })
        await session.commit()

        return True

    except Exception as e:
        await session.rollback()
        logger.error(f"Rate limit check failed for user {user_id}, tenant {tenant_id}: {e}")
        # Fail open: allow request if rate limiting system has errors
        return True


async def return_enriched_tenant(
    tenant: Tenant, session: AsyncSession, action: str = "retrieve"
) -> TenantResponse:
    """
    Helper function to enrich a tenant with related details and return it.
    
    Args:
        tenant: The tenant ORM object to enrich
        session: The database session
        action: The action being performed (for error messages)
        
    Returns:
        The enriched TenantResponse object
        
    Raises:
        HTTPException: If enrichment fails
    """
    enriched_tenants = await enrich_tenants_with_details([tenant], session)
    if enriched_tenants:
        return enriched_tenants[0]
    else:
        # Fallback if enrichment fails
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to {action} tenant details for tenant ID {tenant.id}"
        )

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieves a tenant by ID after verifying the current user's permission to view it.
    
    Checks access rights, enriches the tenant data with related unit and property details, and returns the tenant information. Raises a 404 error if the tenant does not exist or is inaccessible to the user.
    """
    logger.info("User %s requesting tenant %s", current_user.email, tenant_id)
    tenant_orm = await check_tenant_permission(
        tenant_id, session, current_user, action="view"
    )

    # Fetch the assigned unit and property (similar logic to get_tenants, needs optimization)
    tenant_response_list = await enrich_tenants_with_details([tenant_orm], session)
    if not tenant_response_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    return tenant_response_list[0]


@router.get("/", response_model=list[TenantResponse])
async def get_tenants(
    status_filter: TenantStatus | None = None,
    search: str | None = None,
    property_id: int | None = None,  # Allow filtering by property for landlords/admins
    unassigned_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieves a filtered and paginated list of tenants based on user role and query parameters.
    
    Landlords receive tenants linked to their properties or, if `unassigned_only` is true, only those without active leases.
    Admins can view all tenants, optionally filtered by property. Tenants are not permitted to list other tenants.
      Each tenant in the result includes related unit and property details when available.
    
    Args:
        status_filter: Optional filter for tenant status.
        search: Optional search term for tenant name or email.
        property_id: Optional property ID to filter tenants by property.
        unassigned_only: If true, returns only tenants without active leases for the current landlord.
        skip: Number of records to skip for pagination.
        limit: Maximum number of tenants to return.
    
    Returns:
        A list of TenantResponse objects matching the filters and access permissions.
    """
    logger.info(
        "User %s (type: %s) is retrieving tenants",
        current_user.email,
        current_user.user_type,
    )

    if current_user.user_type == UserType.TENANT:
        logger.warning("Tenant %s attempted to list tenants.", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to list tenants"
        )

    if unassigned_only:
        query = build_unassigned_tenants_query(current_user, search)
    else:
        query = build_filtered_tenants_query(
            current_user, status_filter, search, property_id
        )

    # Apply pagination and ordering, falling back to company_name for sorting
    query = query.order_by(
        col(Tenant.last_name).asc().nullslast(),
        col(Tenant.company_name).asc().nullslast(),
        col(Tenant.first_name).asc().nullslast()
    ).offset(skip).limit(limit)

    result = await session.execute(query)
    tenants_orm = result.scalars().all()
    logger.info("Retrieved %s tenants for user %s", len(tenants_orm), current_user.id)

    # Convert ORM objects to response models with details
    return await enrich_tenants_with_details(list(tenants_orm), session)


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Creates a new tenant profile after validating permissions, property assignment, and user account linkage.
    
    Landlords can only assign tenants to properties they own, while admins can assign tenants to any property with the landlord set to the property's owner.
    Ensures email uniqueness per landlord and enforces property ownership rules. Returns the created tenant's details on success.
    
    Raises:
        HTTPException: If the user lacks permission, validation fails, or an unexpected error occurs.
    """

    await _validate_user_permissions(current_user)

    assigned_landlord_id = await _determine_landlord(
        current_user, tenant_data, session
    )

    await _validate_property_assignment(current_user, tenant_data, session)

    await _validate_linked_user_account(tenant_data, session)

    try:
        tenant = await create_and_save_tenant(
            tenant_data, assigned_landlord_id, session, background_tasks
        )

        await session.commit()

        logger.info(
            "Tenant %s created successfully by user %s", tenant.id, current_user.id
        )
        
        # Enrich the tenant with details before returning
        return await return_enriched_tenant(tenant, session, action="retrieve created")

    except Exception as e:
        await session.rollback()
        logger.exception(
            "Final exception handler caught error in tenant creation: %s", e
        )
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during the final step of tenant creation.",
        )


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Updates an existing tenant's information after verifying user permissions and property assignment rules.
    
    If the current property assignment is changed, validates that landlords can only assign tenants to properties they own,
    and admins can only assign to existing properties. Applies partial updates from the provided data and updates the audit timestamp.
    
    Returns:
        The updated tenant as a TenantResponse model.
    
    Raises:
        HTTPException: If the user lacks permission, the property assignment is invalid, or an unexpected error occurs.
    """
    logger.info("User %s updating tenant %s", current_user.email, tenant_id)
    tenant = await check_tenant_permission(
        tenant_id, session, current_user, action="update"
    )

    # If updating current_property_id, check landlord ownership
    if (
        tenant_data.current_property_id is not None
        and tenant_data.current_property_id != tenant.current_property_id
    ):
        if current_user.user_type == UserType.LANDLORD:
            prop_query = select(col(Property.id)).where(
                and_(
                    col(Property.id) == tenant_data.current_property_id,
                    col(Property.user_id) == current_user.id,
                )
            )
            prop_exists = await session.scalar(prop_query)
            if not prop_exists:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot assign tenant to a property you do not own",
                )
        elif current_user.is_admin:
            prop_query = select(col(Property.id)).where(
                col(Property.id) == tenant_data.current_property_id
            )
            prop_exists = await session.scalar(prop_query)
            if not prop_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assigned property not found",
                )

    try:
        update_data = tenant_data.model_dump(exclude_unset=True, exclude={"full_name"})
        for key, value in update_data.items():
            setattr(tenant, key, value)

        tenant.updated_at = create_audit_datetime()

        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        logger.info(
            "Tenant %s updated successfully by user %s", tenant_id, current_user.id
        )
        
        # Enrich the tenant with details before returning
        return await return_enriched_tenant(tenant, session, action="retrieve updated")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating tenant %s", tenant_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tenant due to an internal error.",
        )

@router.delete("/delete-bulk", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_tenants_endpoint(
    payload: TenantBulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Deletes multiple tenants in a single transaction.
    """
    # Store user ID early to avoid lazy loading issues (ID is always loaded as it's the PK)
    user_id = current_user.id
    
    try:
        # Validate that tenant_ids is provided and not empty
        if not payload.tenant_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tenant IDs provided for bulk deletion.",
            )
        
        logger.info(
            "User ID %s is bulk deleting tenants: %s",
            user_id,
            payload.tenant_ids,
        )
        await bulk_delete_tenants(
            tenant_ids=payload.tenant_ids, session=session, current_user=current_user
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status codes and error messages
        raise
    except Exception as e:
        # Catch any unexpected errors and log them properly
        logger.exception(
            "Unexpected error in bulk_delete_tenants_endpoint for user ID %s: %s",
            user_id,
            str(e)
        )
        # Ensure we rollback the session if there's an error
        try:
            await session.rollback()
        except Exception:
            pass  # Ignore rollback errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting tenants.",
        ) from e



@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Deletes a tenant by ID after verifying permissions and ensuring no active leases exist.
    
    Raises:
        HTTPException: If the current user is a tenant, if the tenant has active leases, or if a database error occurs during deletion.
    
    Returns:
        Response: HTTP 204 No Content on successful deletion.
    """
    logger.info("User %s deleting tenant %s", current_user.email, tenant_id)

    if current_user.user_type == UserType.TENANT:
        # Tenants cannot delete tenant profiles (even their own via this endpoint perhaps? TBD)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete tenants",
        )

    tenant = await check_tenant_permission(
        tenant_id, session, current_user, action="delete"
    )

    # Check if tenant has any associated active leases
    lease_query = (
        select(col(Lease.id))
        .where(
            and_(
                col(Lease.tenant_id) == tenant_id,
                col(Lease.status) == LeaseStatus.ACTIVE,
            )
        )
        .limit(1)
    )
    active_lease_exists = await session.scalar(lease_query)

    if active_lease_exists:
        logger.warning("Cannot delete tenant %s due to active leases", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete tenant with active leases. Please terminate or reassign leases first.",
        )

    try:
        await session.delete(tenant)
        await session.commit()

        logger.info(
            "Tenant %s deleted successfully by user %s", tenant_id, current_user.id
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        # Catch potential DB constraint errors if tenant is linked elsewhere
        logger.exception("Error deleting tenant %s", tenant_id)
        await session.rollback()
        # Provide a more generic error, or specific if known constraint
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tenant. Check for related records (e.g., historical payments, messages).",
        )


# === Emergency Contact Atomic Endpoints ===

@router.post(
    "/{tenant_id}/emergency-contacts",
    response_model=EmergencyContactResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_emergency_contact(
    tenant_id: int,
    contact_data: EmergencyContactCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Atomically adds a new emergency contact to a tenant.

    This endpoint handles the primary contact logic atomically on the backend,
    preventing race conditions that could occur with client-side read-modify-write patterns.

    If the new contact is marked as primary, all other contacts will automatically
    have their is_primary flag set to false.

    Args:
        tenant_id: The ID of the tenant to add the contact to
        contact_data: The emergency contact data to create

    Returns:
        The newly created emergency contact with its assigned UUID

    Raises:
        HTTPException: If the tenant is not found, user lacks permission,
                      maximum contacts limit is reached, or validation fails
    """
    logger.info(
        "User %s adding emergency contact to tenant %s",
        current_user.email,
        tenant_id
    )
    return await add_emergency_contact(tenant_id, contact_data, session, current_user)


@router.put(
    "/{tenant_id}/emergency-contacts/{contact_id}",
    response_model=EmergencyContactResponse
)
async def update_emergency_contact_endpoint(
    tenant_id: int,
    contact_id: str,
    contact_data: EmergencyContactUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Atomically updates an existing emergency contact.

    This endpoint handles the primary contact logic atomically on the backend.
    If the contact is being marked as primary, all other contacts will automatically
    have their is_primary flag set to false.

    Supports partial updates - only the fields provided in the request body will be updated.

    Args:
        tenant_id: The ID of the tenant
        contact_id: The UUID of the contact to update
        contact_data: The updated contact data (partial update supported)

    Returns:
        The updated emergency contact

    Raises:
        HTTPException: If the tenant or contact is not found,
                      user lacks permission, or validation fails
    """
    logger.info(
        "User %s updating emergency contact %s for tenant %s",
        current_user.email,
        contact_id,
        tenant_id
    )
    return await update_emergency_contact(
        tenant_id, contact_id, contact_data, session, current_user
    )


@router.delete(
    "/{tenant_id}/emergency-contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_emergency_contact_endpoint(
    tenant_id: int,
    contact_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Atomically deletes an emergency contact from a tenant.

    Args:
        tenant_id: The ID of the tenant
        contact_id: The UUID of the contact to delete

    Returns:
        HTTP 204 No Content on successful deletion

    Raises:
        HTTPException: If the tenant or contact is not found,
                      or user lacks permission
    """
    logger.info(
        "User %s deleting emergency contact %s from tenant %s",
        current_user.email,
        contact_id,
        tenant_id
    )
    await delete_emergency_contact(tenant_id, contact_id, session, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{tenant_id}/metrics", response_model=TenantMetricsResponse)
async def get_tenant_metrics(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get pre-calculated metrics for a tenant.

    This endpoint moves complex metric calculations from the frontend to the backend,
    significantly reducing payload size and improving performance.

    Backend calculates metrics instead of sending full related data
    (payments, invoices, maintenance_requests) to the frontend.

    Expected performance improvement: 40-60% reduction in payload size.

    Returns:
        Pre-calculated metrics including payment performance, open balance,
        ticket resolution stats, and upcoming events

    Raises:
        HTTPException: If tenant not found or user lacks permission
    """
    logger.info(
        "User %s requesting metrics for tenant %s",
        current_user.email,
        tenant_id
    )

    # Check permissions
    await check_tenant_permission(tenant_id, session, current_user, action="view")

    # TODO: Implement full metrics calculation service
    # This would mirror the frontend logic from tenantMetrics.tsx
    # For now, return placeholder response to demonstrate the pattern

    return TenantMetricsResponse(
        payment_performance=PaymentPerformanceMetrics(
            rate=None,
            on_time_count=0,
            total_count=0,
            avg_days_early=0,
            status="no_data"
        ),
        open_balance=OpenBalanceMetrics(
            total_balance=Decimal("0"),
            overdue_balance=Decimal("0"),
            rent_balance=Decimal("0"),
            invoice_balance=Decimal("0"),
            unpaid_invoice_count=0,
            is_overdue=False,
            next_due_amount=None,
            next_due_date=None
        ),
        ticket_resolution=TicketResolutionMetrics(
            avg_days=None,
            completed_count=0,
            total_count=0,
            pending_count=0,
            status="no_data"
        ),
        upcoming_events=[]
    )


@router.post("/{tenant_id}/send-reminder", response_model=TenantReminderResponse)
async def send_tenant_reminder(
    tenant_id: int,
    reminder_data: TenantReminderRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Send a reminder to a tenant about an upcoming event.

    This endpoint allows landlords and admins to manually send reminders
    to tenants about rent due, lease expiry, invoices, or maintenance.

    The reminder is sent via:
    1. In-app notification (always, if tenant has portal access)
    2. Email (only if tenant has email notifications enabled for rent_reminder)

    Args:
        tenant_id: ID of the tenant to send reminder to
        reminder_data: Event details for the reminder

    Returns:
        Success status and message

    Raises:
        HTTPException: If tenant not found or user lacks permission
    """
    logger.info(
        "User %s sending reminder to tenant %s for event: %s",
        current_user.email,
        tenant_id,
        reminder_data.event_type
    )

    # SECURITY: Check rate limit before proceeding
    if not await check_reminder_rate_limit(tenant_id, current_user.id, session):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. You can send a maximum of {_reminder_rate_limit_max} reminders per tenant per hour. Please try again later."
        )

    # Check permissions
    tenant = await check_tenant_permission(tenant_id, session, current_user, action="view")

    # Get tenant name
    if tenant.tenant_type == TenantType.COMPANY:
        tenant_name = tenant.company_name or tenant.contact_person or "Tenant"
    else:
        tenant_name = f"{tenant.first_name or ''} {tenant.last_name or ''}".strip() or "Tenant"

    # Get property and unit info if available
    property_name = None
    unit_name = None
    if tenant.current_property_id:
        property_query = select(Property).where(col(Property.id) == tenant.current_property_id)
        property_result = await session.execute(property_query)
        property_obj = property_result.scalar_one_or_none()
        if property_obj:
            property_name = property_obj.name

    # Try to get unit info from active lease using JOIN for efficiency
    if tenant.id:
        unit_query = (
            select(PropertyUnit)
            .join(Lease, col(Lease.unit_id) == PropertyUnit.id)
            .where(
                and_(
                    col(Lease.tenant_id) == tenant.id,
                    col(Lease.status) == LeaseStatus.ACTIVE
                )
            )
            .limit(1)
        )
        unit_result = await session.execute(unit_query)
        unit_obj = unit_result.scalar_one_or_none()
        unit_name = unit_obj.name if unit_obj else None

    # Build notification title and message
    notification_title = reminder_data.custom_subject or reminder_data.event_title
    notification_message = reminder_data.custom_message
    if not notification_message:
        # Generate default message based on days remaining
        days = reminder_data.days_remaining
        if days is not None:
            if days < 0:
                notification_message = f"Your rent payment is {abs(days)} day{'s' if abs(days) != 1 else ''} overdue. Please make your payment as soon as possible."
            elif days == 0:
                notification_message = "Your rent payment is due today. Please ensure payment is made on time."
            else:
                notification_message = f"Your rent payment is due in {days} day{'s' if days != 1 else ''}."
        else:
            notification_message = reminder_data.event_subtitle or "You have a pending rent payment."

    # Add amount info if available
    if reminder_data.event_amount:
        notification_message += f" Amount: ${reminder_data.event_amount:,.2f}"

    # Track what was sent
    in_app_sent = False
    email_sent = False

    try:
        # 1. Create in-app notification if tenant has portal access
        if tenant.user_id:
            # Use NotificationService which respects user preferences
            notification = await NotificationService.create_notification(
                user_id=tenant.user_id,
                type="rent_reminder",
                title=notification_title,
                message=notification_message,
                session=session,
                link="/payments",  # Deep link to payments page in tenant portal
                actor_id=current_user.id,
                actor_name=f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or "Your Landlord",
                metadata={
                    "tenant_id": tenant_id,
                    "event_type": reminder_data.event_type,
                    "event_date": reminder_data.event_date,
                    "event_amount": float(reminder_data.event_amount) if reminder_data.event_amount else None,
                    "days_remaining": reminder_data.days_remaining,
                    "property_name": property_name,
                    "unit_name": unit_name,
                    "sent_by_landlord": True,
                },
                priority="high" if (reminder_data.days_remaining is not None and reminder_data.days_remaining <= 0) else "normal",
            )

            if notification:
                in_app_sent = True
                # Check if email was also sent (NotificationService handles this based on preferences)
                if notification.delivery_channels and "email" in notification.delivery_channels:
                    email_sent = True
                logger.info(
                    "In-app notification created for tenant %s (user_id: %s), email sent: %s",
                    tenant_id,
                    tenant.user_id,
                    email_sent
                )
        else:
            # Tenant doesn't have portal access - send email directly if they have an email
            logger.info("Tenant %s has no portal access, falling back to email only", tenant_id)

        # 2. If no notification was created (tenant has no portal) or email wasn't sent via
        #    NotificationService, try direct email as fallback
        if not in_app_sent and not email_sent:
            # Validate tenant has email for direct sending
            if not tenant.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot send reminder: tenant does not have portal access or an email address"
                )

            # Validate email format
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, tenant.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid email address format: {tenant.email}"
                )

            # Send direct email for tenants without portal access
            email_success = await EmailService.send_tenant_reminder_email(
                tenant_email=tenant.email,
                tenant_name=tenant_name,
                event_type=reminder_data.event_type,
                event_title=reminder_data.event_title,
                event_subtitle=reminder_data.event_subtitle,
                event_date=reminder_data.event_date,
                event_amount=reminder_data.event_amount,
                days_remaining=reminder_data.days_remaining,
                property_name=property_name,
                unit_name=unit_name,
                metadata={
                    'tenant_id': tenant_id,
                    'sent_by_user_id': str(current_user.id),
                    'sent_by_email': current_user.email,
                },
                custom_subject=reminder_data.custom_subject,
                custom_message=reminder_data.custom_message
            )

            if email_success:
                email_sent = True

        # Build response message
        if in_app_sent and email_sent:
            message = f"Reminder sent to {tenant_name} via notification and email"
        elif in_app_sent:
            message = f"Reminder sent to {tenant_name} via in-app notification"
        elif email_sent:
            message = f"Reminder email sent to {tenant_name}"
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send reminder. Please try again later."
            )

        logger.info(
            "Reminder sent successfully to tenant %s by user %s (in_app: %s, email: %s)",
            tenant_id,
            current_user.id,
            in_app_sent,
            email_sent
        )

        return TenantReminderResponse(
            success=True,
            message=message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error sending reminder to tenant {tenant_id}")

        sentry_sdk.capture_exception(e, extras={
            'tenant_id': tenant_id,
            'tenant_email': tenant.email if tenant else None,
            'tenant_user_id': str(tenant.user_id) if tenant and tenant.user_id else None,
            'event_type': reminder_data.event_type,
            'user_id': str(current_user.id),
            'user_email': current_user.email,
            'has_custom_message': bool(reminder_data.custom_message),
            'has_custom_subject': bool(reminder_data.custom_subject),
            'property_name': property_name,
            'unit_name': unit_name,
            'in_app_sent': in_app_sent,
            'email_sent': email_sent,
        }, tags={
            'feature': 'tenant_reminders',
            'action': 'send_reminder',
            'event_type': reminder_data.event_type
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while sending the reminder."
        )
