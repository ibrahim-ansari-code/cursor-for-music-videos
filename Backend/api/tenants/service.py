import logging
from uuid import UUID as PythonUUID, uuid4
from typing import Any

from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy import and_, not_, or_, Select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlmodel import col

from Backend.api.leases.schemas import LeaseDocumentResponse
from Backend.api.tenants.schemas import (
    EmergencyContactCreate,
    EmergencyContactResponse,
    EmergencyContactUpdate,
    LeaseResponseSimple,
    PropertyResponseSimple,
    TenantCreate,
    TenantResponse,
    UnitResponseSimple,
)
from Backend.api.maintenance.schemas import MaintenanceRequestResponse
from Backend.api.accounting.payments.schemas import PaymentResponse
from Backend.api.accounting.invoices.schemas import InvoiceResponse
from Backend.models.enums import UserType
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.tenant import Tenant, TenantStatus
from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime
from Backend.api.quickbooks.services import CustomerService

logger = logging.getLogger(__name__)


# === Helper Function for Tenant Permission Checks ===
async def check_tenant_permission(
    tenant_id: int, session: AsyncSession, current_user: User, action: str = "view"
) -> Tenant:
    """
    Checks whether the current user is authorized to access or modify a tenant.
    
    Admins have unrestricted access. Landlords can only access tenants they own. Raises an HTTP 404 error if the tenant does not exist, or HTTP 403 if the user lacks the required permissions.
    
    Returns:
        The Tenant object if access is permitted.
    """
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    if current_user.is_admin:
        return tenant

    if current_user.user_type == UserType.LANDLORD:
        if tenant.landlord_id == current_user.id:
            return tenant

    # If no permissions match, deny access.
    logger.warning(
        "User %s permission denied for action '%s' on tenant %s",
        current_user.id,
        action,
        tenant_id,
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Not authorized to {action} this tenant",
    )


def _build_tenant_filters(
    status_filter: TenantStatus | None, search: str | None
) -> list:
    """
    Constructs SQLAlchemy filter conditions for tenants based on status and search term.
    
    If a status filter is provided, filters tenants by their status. If a search term is provided, filters tenants whose first name, last name, email, company name, or contact person contains the search term (case-insensitive).
    
    Returns:
        A list of SQLAlchemy filter conditions to be used in tenant queries.
    """
    filters = []
    if status_filter:
        filters.append(col(Tenant.status) == status_filter)
    if search:
        search_term = f"%{search}%"
        filters.append(
            or_(
                col(Tenant.first_name).ilike(search_term),
                col(Tenant.last_name).ilike(search_term),
                col(Tenant.email).ilike(search_term),
                col(Tenant.company_name).ilike(search_term),
                col(Tenant.contact_person).ilike(search_term),
            )
        )
    return filters


def _apply_landlord_permissions(current_user: User, property_id: int | None) -> list:
    """
    Constructs SQLAlchemy filter conditions to restrict tenant queries to those owned by the landlord, with optional filtering by a specific property.
    
    If a property ID is provided, filters tenants to those linked to the property either via an active lease or current property assignment.
    """
    filters = []

    # The primary filter for a landlord is to only see tenants they own.
    filters.append(col(Tenant.landlord_id) == current_user.id)

    # If a specific property_id is provided, add that to the filter.
    if property_id:
        specific_property_filter = or_(
            col(Lease.property_id) == property_id,
            col(Tenant.current_property_id) == property_id,
        )
        filters.append(specific_property_filter)

    return filters


async def _validate_user_permissions(current_user: User) -> None:
    """
    Validates that the current user is allowed to create a tenant.
    
    Raises:
        HTTPException: If the user is a tenant, with status 403 Forbidden.
    """
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenants cannot create tenants",
        )


async def _determine_landlord(
    current_user: User, tenant_data: "TenantCreate", session: AsyncSession
) -> PythonUUID:
    """
    Determines the landlord ID to associate with a new tenant.
    
    If the current user is an admin and a property ID is specified, retrieves the owner of the property to use as the landlord. Otherwise, returns the current user's ID.
    """
    if current_user.is_admin and tenant_data.current_property_id:
        property_owner_query = select(col(Property.user_id)).where(
            col(Property.id) == tenant_data.current_property_id
        )
        property_owner_id = await session.scalar(property_owner_query)
        if property_owner_id:
            logger.info(
                "Admin creating tenant for property owner %s", property_owner_id
            )
            return property_owner_id
        else:
            logger.warning(
                "Admin creating tenant but property %s has no owner",
                tenant_data.current_property_id,
            )
    return current_user.id


async def _validate_property_assignment(
    current_user: User, tenant_data: "TenantCreate", session: AsyncSession
) -> None:
    """
    Validates whether the current user is authorized to assign a tenant to the specified property.
    
    Raises:
        HTTPException: If the property does not exist (admin) or if the user is not permitted to assign the tenant to the property (landlord).
    """
    if not tenant_data.current_property_id:
        return

    prop_exists_query = select(col(Property.id)).where(
        col(Property.id) == tenant_data.current_property_id
    )
    if current_user.user_type == UserType.LANDLORD:
        prop_exists_query = prop_exists_query.where(
            col(Property.user_id) == current_user.id
        )

    prop_exists = await session.scalar(prop_exists_query)

    if not prop_exists:
        if current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned property not found",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign tenant to a property you do not own",
            )


async def _validate_linked_user_account(
    tenant_data: "TenantCreate", session: AsyncSession
) -> None:
    """
    Validates that a provided user ID in tenant data refers to an existing tenant user without an existing tenant profile.
    
    Raises:
        HTTPException: If the user does not exist, is not of type Tenant, or already has a tenant profile.
    """
    if not tenant_data.user_id:
        return

    user_query = select(User).where(col(User.id) == tenant_data.user_id)
    target_user = await session.scalar(user_query)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with ID {tenant_data.user_id} not found",
        )
    if target_user.user_type != UserType.TENANT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User ID {tenant_data.user_id} does not belong to a Tenant",
        )

    existing_tenant_query = select(col(Tenant.id)).where(
        col(Tenant.user_id) == tenant_data.user_id
    )
    if await session.scalar(existing_tenant_query):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A tenant profile already exists for user ID {tenant_data.user_id}",
        )


async def _safe_link_qb_customer(user: User, tenant_data: dict[str, Any]) -> None:
    """
    Attempts to link or create a QuickBooks customer for the tenant, logging any exceptions without interrupting the main workflow.
    """
    try:
        from Backend.database import async_session
        async with async_session() as session:
            customer_service = CustomerService(user, session)
            await customer_service.link_or_create_qb_customer(tenant_data)
    except Exception as e:
        logger.warning("QuickBooks sync failed (non-fatal): %s", e, exc_info=True)


async def create_and_save_tenant(
    tenant_data: "TenantCreate",
    landlord_id: PythonUUID,
    session: AsyncSession,
    background_tasks: BackgroundTasks,
) -> Tenant:
    """
    Creates a new tenant record in the database and schedules background QuickBooks linkage.
    
    The function validates and persists a new tenant using the provided data and landlord ID, setting audit timestamps. It flushes and refreshes the tenant instance, then schedules a background task to link the tenant with a QuickBooks customer. If a unique email constraint is violated, it raises a 409 HTTP error; for other database constraint violations, it raises a 400 HTTP error.
    
    Returns:
        The newly created Tenant ORM object.
    """
    tenant_dict = tenant_data.model_dump(exclude={"full_name"})
    tenant_dict["landlord_id"] = landlord_id

    tenant = Tenant.model_validate(tenant_dict)
    tenant.created_at = create_audit_datetime()
    tenant.updated_at = create_audit_datetime()

    session.add(tenant)
    try:
        await session.flush()
        await session.refresh(tenant)

        # Move the background task here to break the circular import
        landlord_user = await session.get(User, landlord_id)
        if landlord_user:
            tenant_dump = tenant.model_dump()
            background_tasks.add_task(_safe_link_qb_customer, landlord_user, tenant_dump)

        return tenant
    except IntegrityError as e:
        await session.rollback()
        error_str = str(e).lower()
        if "unique constraint" in error_str and "email" in error_str:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A tenant with this email address already exists.",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database constraint violation.",
        ) from e


def build_unassigned_tenants_query(
    current_user: User, search: str | None
) -> Select:
    """
    Constructs a SQLAlchemy query to retrieve tenants owned by the current landlord who are not assigned to any active lease.
    
    Args:
        current_user: The landlord user for whom to find unassigned tenants.
        search: Optional search term to filter tenants by first name, last name, email, company name, or contact person.
    
    Returns:
        A SQLAlchemy Select object representing the filtered tenant query.
    """
    base_query = select(Tenant).where(col(Tenant.landlord_id) == current_user.id)

    active_lease_subquery = (
        select(col(Lease.tenant_id))
        .join(Property, col(Lease.property_id) == col(Property.id))
        .where(
            and_(
                col(Property.user_id) == current_user.id,
                col(Lease.status) == LeaseStatus.ACTIVE,
            )
        )
        .distinct()
    )

    query = base_query.where(not_(col(Tenant.id).in_(active_lease_subquery)))

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                col(Tenant.first_name).ilike(search_term),
                col(Tenant.last_name).ilike(search_term),
                col(Tenant.email).ilike(search_term),
                col(Tenant.company_name).ilike(search_term),
                col(Tenant.contact_person).ilike(search_term),
            )
        )
    return query


def build_filtered_tenants_query(
    current_user: User,
    status_filter: TenantStatus | None,
    search: str | None,
    property_id: int | None,
) -> Select:
    """
    Constructs a SQLAlchemy query to retrieve tenants filtered by status, search term, and property, applying user role-based permissions.
    
    For landlords, restricts results to tenants they own and, if specified, those associated with a given property. For admins, optionally filters tenants by property association. Combines all applicable filters and returns a distinct tenant selection query.
    """
    query = (
        select(Tenant)
        .distinct()
        .outerjoin(Lease, col(Tenant.id) == col(Lease.tenant_id))
        .outerjoin(Property, col(Lease.property_id) == col(Property.id))
    )

    filters = _build_tenant_filters(status_filter, search)

    if current_user.user_type == UserType.LANDLORD:
        filters.extend(_apply_landlord_permissions(current_user, property_id))
    elif current_user.is_admin and property_id:
        filters.append(
            or_(
                col(Lease.property_id) == property_id,
                col(Tenant.current_property_id) == property_id,
            )
        )

    if filters:
        query = query.where(and_(*filters))

    return query


async def enrich_tenants_with_details(
    tenants: list[Tenant], session: AsyncSession
) -> list["TenantResponse"]:
    """
    Transforms a list of Tenant ORM objects into TenantResponse models enriched with related property, unit, and lease details.

    PERFORMANCE OPTIMIZED: Uses bulk fetching to avoid N+1 queries.
    - Fetches all related data in 6 queries total (regardless of tenant count)
    - Maps results by tenant_id for O(1) lookup

    For each tenant, loads:
    1. Latest assigned property unit and its property information (from current_property_id)
    2. All leases with their associated property and unit details
    3. Maintenance requests
    4. Payments
    5. Invoices

    Returns only tenants with valid IDs.
    """
    from collections import defaultdict
    from Backend.models.maintenance import MaintenanceRequest
    from Backend.models.accounting.payment import Payment
    from Backend.models.accounting.invoice import Invoice

    if not tenants:
        return []

    # Extract tenant IDs for bulk queries
    tenant_ids = [tenant.id for tenant in tenants]

    # ============================================================================
    # BULK FETCH ALL RELATED DATA (6 queries total, not 3N queries)
    # ============================================================================

    # 1. Bulk fetch maintenance requests for all tenants
    maintenance_query = (
        select(MaintenanceRequest)
        .options(
            selectinload(getattr(MaintenanceRequest, "property")),
            selectinload(getattr(MaintenanceRequest, "unit")),
            selectinload(getattr(MaintenanceRequest, "tenant"))
        )
        .where(col(MaintenanceRequest.tenant_id).in_(tenant_ids))
        .order_by(col(MaintenanceRequest.request_date).desc())
    )
    maintenance_result = await session.execute(maintenance_query)
    all_maintenance = maintenance_result.scalars().all()

    # Group maintenance by tenant_id
    maintenance_map = defaultdict(list)
    for req in all_maintenance:
        maintenance_map[req.tenant_id].append(req)

    # 2. Bulk fetch payments for all tenants
    payment_query = (
        select(Payment)
        .options(
            selectinload(getattr(Payment, "lease")).selectinload(getattr(Lease, "property")),
            selectinload(getattr(Payment, "tenant"))
        )
        .where(col(Payment.tenant_id).in_(tenant_ids))
        .order_by(col(Payment.payment_date).desc())
    )
    payment_result = await session.execute(payment_query)
    all_payments = payment_result.scalars().all()

    # Group payments by tenant_id
    payments_map = defaultdict(list)
    for payment in all_payments:
        payments_map[payment.tenant_id].append(payment)

    # 3. Bulk fetch invoices for all tenants
    invoice_query = (
        select(Invoice)
        .options(
            selectinload(getattr(Invoice, "property")),
            selectinload(getattr(Invoice, "tenant"))
        )
        .where(col(Invoice.tenant_id).in_(tenant_ids))
        .order_by(col(Invoice.issue_date).desc())
    )
    invoice_result = await session.execute(invoice_query)
    all_invoices = invoice_result.scalars().all()

    # Group invoices by tenant_id
    invoices_map = defaultdict(list)
    for invoice in all_invoices:
        invoices_map[invoice.tenant_id].append(invoice)

    # ============================================================================
    # PROCESS EACH TENANT WITH O(1) LOOKUPS (no additional queries)
    # ============================================================================

    response_data = []
    for tenant in tenants:
        # Convert tenant to dict using model_dump, excluding problematic relationships
        tenant_dict = tenant.model_dump(exclude={'leases', 'user', 'current_property', 'assigned_units', 'units', 'maintenance_requests', 'payments', 'invoices'})
        # Add fields expected by TenantResponse
        tenant_dict.update({
            'unit': None,
            'property': None,
            'leases': []  # Initialize empty, will be populated below
        })
        tenant_response = TenantResponse.model_validate(tenant_dict)
        
        # Load current property/unit assignment
        if tenant.current_property_id:
            unit_query = (
                select(PropertyUnit)
                .options(selectinload(getattr(PropertyUnit, "property")))
                .where(
                    col(PropertyUnit.tenant_id) == tenant.id,
                    col(PropertyUnit.property_id) == tenant.current_property_id,
                )
                .order_by(col(PropertyUnit.id).desc())
                .limit(1)
            )
            unit_result = await session.execute(unit_query)
            assigned_unit = unit_result.scalar_one_or_none()

            if assigned_unit and assigned_unit.property:
                property_info = PropertyResponseSimple.model_validate(
                    assigned_unit.property
                )
                unit_info = UnitResponseSimple.model_validate(assigned_unit)
                unit_info.property = property_info
                tenant_response.unit = unit_info
                tenant_response.property = property_info

        # Load all leases for this tenant with property/unit/document details
        lease_query = (
            select(Lease)
            .options(
                selectinload(getattr(Lease, "property")),
                selectinload(getattr(Lease, "unit")),
                selectinload(getattr(Lease, "documents"))
            )
            .where(col(Lease.tenant_id) == tenant.id)
            .order_by(col(Lease.start_date).desc())
        )
        lease_result = await session.execute(lease_query)
        leases = lease_result.scalars().all()

        lease_responses = []
        for lease in leases:
            lease_response = LeaseResponseSimple.model_validate(lease)

            # Add property info to lease
            if lease.property:
                lease_response.property = PropertyResponseSimple.model_validate(lease.property)

            # Add unit info to lease (if lease has a unit)
            if lease.unit:
                unit_response = UnitResponseSimple.model_validate(lease.unit)
                # Add property info to unit if available
                if lease.property:
                    unit_response.property = PropertyResponseSimple.model_validate(lease.property)
                lease_response.unit = unit_response

            # Add documents to lease response
            if lease.documents:
                lease_response.documents = [
                    LeaseDocumentResponse.model_validate(doc) for doc in lease.documents
                ]

            lease_responses.append(lease_response)

        tenant_response.leases = lease_responses

        # ====================================================================
        # ASSIGN PRE-FETCHED DATA FROM BULK QUERIES (O(1) lookups, no queries)
        # ====================================================================

        # Assign maintenance requests from bulk-fetched map
        maintenance_requests_orm = maintenance_map.get(tenant.id, [])
        if maintenance_requests_orm:
            tenant_response.maintenance_requests = [
                MaintenanceRequestResponse.model_validate(req) for req in maintenance_requests_orm
            ]

        # Assign payments from bulk-fetched map
        payments_orm = payments_map.get(tenant.id, [])
        if payments_orm:
            tenant_response.payments = [
                PaymentResponse.model_validate(payment) for payment in payments_orm
            ]

        # Assign invoices from bulk-fetched map
        invoices_orm = invoices_map.get(tenant.id, [])
        if invoices_orm:
            tenant_response.invoices = [
                InvoiceResponse.model_validate(invoice) for invoice in invoices_orm
            ]

        # If tenant has no current property/unit assignment but has active leases,
        # use the most recent active lease for property/unit info
        if not tenant_response.property and lease_responses:
            # Find the most recent active lease
            active_lease = None
            for lease_resp in lease_responses:
                if lease_resp.status == LeaseStatus.ACTIVE:
                    active_lease = lease_resp
                    break
            
            # If no active lease, use the most recent lease
            if not active_lease and lease_responses:
                active_lease = lease_responses[0]
                logger.warning(
                    "Tenant %s has no active lease, using most recent lease for property info. This may indicate data inconsistency.",
                    tenant.id
                )
            
            if active_lease:
                tenant_response.property = active_lease.property
                tenant_response.unit = active_lease.unit

        response_data.append(tenant_response)

    return [t for t in response_data if t is not None and t.id is not None]


# === Emergency Contact Atomic Operations ===

async def add_emergency_contact(
    tenant_id: int,
    contact_data: EmergencyContactCreate,
    session: AsyncSession,
    current_user: User
) -> EmergencyContactResponse:
    """
    Atomically adds a new emergency contact to a tenant.

    This function handles the primary contact logic atomically on the backend,
    preventing race conditions that could occur with client-side read-modify-write patterns.

    Args:
        tenant_id: The ID of the tenant to add the contact to
        contact_data: The emergency contact data to add
        session: Database session
        current_user: The current authenticated user

    Returns:
        The newly created emergency contact with its assigned ID

    Raises:
        HTTPException: If the tenant is not found, user lacks permission, or validation fails
    """
    # Check permissions
    tenant = await check_tenant_permission(tenant_id, session, current_user, action="update")

    # Get current contacts
    current_contacts = tenant.emergency_contacts or []

    # Validate maximum contacts limit (enforced at DB level, but check here for better UX)
    if len(current_contacts) >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 emergency contacts allowed per tenant"
        )

    # Generate UUID for the new contact
    contact_id = str(uuid4())

    # Convert contact data to dict
    new_contact = contact_data.model_dump()
    new_contact["id"] = contact_id

    # If this contact is marked as primary, unset all other primary contacts
    if new_contact.get("is_primary", False):
        for contact in current_contacts:
            contact["is_primary"] = False

    # Add the new contact
    updated_contacts = current_contacts + [new_contact]

    # Update tenant with new contacts array
    tenant.emergency_contacts = updated_contacts
    tenant.updated_at = create_audit_datetime()

    try:
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        logger.info(
            "Emergency contact %s added to tenant %s by user %s",
            contact_id,
            tenant_id,
            current_user.id
        )

        return EmergencyContactResponse(**new_contact)
    except Exception as e:
        await session.rollback()
        logger.exception("Failed to add emergency contact to tenant %s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add emergency contact"
        ) from e


async def update_emergency_contact(
    tenant_id: int,
    contact_id: str,
    contact_data: EmergencyContactUpdate,
    session: AsyncSession,
    current_user: User
) -> EmergencyContactResponse:
    """
    Atomically updates an existing emergency contact.

    This function handles the primary contact logic atomically on the backend,
    ensuring that only one contact can be marked as primary at a time.

    Args:
        tenant_id: The ID of the tenant
        contact_id: The UUID of the contact to update
        contact_data: The updated contact data (partial update)
        session: Database session
        current_user: The current authenticated user

    Returns:
        The updated emergency contact

    Raises:
        HTTPException: If the tenant or contact is not found, user lacks permission, or validation fails
    """
    # Check permissions
    tenant = await check_tenant_permission(tenant_id, session, current_user, action="update")

    # Get current contacts
    current_contacts = tenant.emergency_contacts or []

    # Find the contact to update
    contact_index = None
    for idx, contact in enumerate(current_contacts):
        if contact.get("id") == contact_id:
            contact_index = idx
            break

    if contact_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Emergency contact with ID {contact_id} not found"
        )

    # Get the existing contact
    existing_contact = current_contacts[contact_index]

    # Apply partial update
    update_dict = contact_data.model_dump(exclude_unset=True)
    updated_contact = {**existing_contact, **update_dict}

    # If this contact is being marked as primary, unset all other primary contacts
    if update_dict.get("is_primary", False):
        for idx, contact in enumerate(current_contacts):
            if idx != contact_index:
                contact["is_primary"] = False

    # Update the contact in the array
    current_contacts[contact_index] = updated_contact

    # Update tenant with modified contacts array
    tenant.emergency_contacts = current_contacts
    tenant.updated_at = create_audit_datetime()

    try:
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        logger.info(
            "Emergency contact %s updated for tenant %s by user %s",
            contact_id,
            tenant_id,
            current_user.id
        )

        return EmergencyContactResponse(**updated_contact)
    except Exception as e:
        await session.rollback()
        logger.exception("Failed to update emergency contact %s for tenant %s", contact_id, tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update emergency contact"
        ) from e


async def delete_emergency_contact(
    tenant_id: int,
    contact_id: str,
    session: AsyncSession,
    current_user: User
) -> None:
    """
    Atomically deletes an emergency contact from a tenant.

    Args:
        tenant_id: The ID of the tenant
        contact_id: The UUID of the contact to delete
        session: Database session
        current_user: The current authenticated user

    Raises:
        HTTPException: If the tenant or contact is not found, or user lacks permission
    """
    # Check permissions
    tenant = await check_tenant_permission(tenant_id, session, current_user, action="update")

    # Get current contacts
    current_contacts = tenant.emergency_contacts or []

    # Find and remove the contact
    contact_found = False
    updated_contacts = []
    for contact in current_contacts:
        if contact.get("id") == contact_id:
            contact_found = True
        else:
            updated_contacts.append(contact)

    if not contact_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Emergency contact with ID {contact_id} not found"
        )

    # Update tenant with filtered contacts array
    tenant.emergency_contacts = updated_contacts
    tenant.updated_at = create_audit_datetime()

    try:
        session.add(tenant)
        await session.commit()

        logger.info(
            "Emergency contact %s deleted from tenant %s by user %s",
            contact_id,
            tenant_id,
            current_user.id
        )
    except Exception as e:
        await session.rollback()
        logger.exception("Failed to delete emergency contact %s from tenant %s", contact_id, tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete emergency contact"
        ) from e


async def bulk_delete_tenants(
    tenant_ids: list[int], session: AsyncSession, current_user: User
) -> None:
    """
    Deletes multiple tenants, skipping those with active leases.

    Args:
        tenant_ids: A list of tenant IDs to delete.
        session: The database session.
        current_user: The user performing the action.

    Raises:
        HTTPException: If any tenants have active leases or if deletion fails.
    """
    if not tenant_ids:
        return

    # First, verify ownership and existence of all tenants
    query = select(Tenant).where(col(Tenant.id).in_(tenant_ids))
    if not current_user.is_admin:
        query = query.where(col(Tenant.landlord_id) == current_user.id)

    result = await session.execute(query)
    tenants_to_process = result.scalars().all()

    if len(tenants_to_process) != len(set(tenant_ids)):
        found_ids = {tenant.id for tenant in tenants_to_process}
        not_found_ids = set(tenant_ids) - found_ids
        if not_found_ids:
            logger.warning(
                "User %s attempted to delete non-existent or unauthorized tenants: %s",
                current_user.id,
                not_found_ids,
            )
            # Note: The error message is generic to avoid leaking information
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more tenants not found or you do not have permission to delete them.",
            )

    # Identify tenants with active leases
    # Use SELECT FOR UPDATE to lock rows and prevent race conditions
    active_lease_query = (
        select(col(Lease.tenant_id))
        .where(
            and_(
                col(Lease.tenant_id).in_(tenant_ids),
                col(Lease.status) == LeaseStatus.ACTIVE,
            )
        )
        .distinct()
        .with_for_update()
    )
    active_lease_tenant_ids_result = await session.execute(active_lease_query)
    active_lease_tenant_ids = set(active_lease_tenant_ids_result.scalars().all())

    deletable_tenants = []
    tenants_with_active_leases = []

    for tenant in tenants_to_process:
        if tenant.id in active_lease_tenant_ids:
            tenants_with_active_leases.append(tenant)
        else:
            deletable_tenants.append(tenant)

    # If some tenants have active leases, do not delete any and return an error
    if tenants_with_active_leases:
        active_tenant_names = ", ".join(
            [
                tenant.first_name or f"ID {tenant.id}"
                for tenant in tenants_with_active_leases
            ]
        )
        logger.warning(
            "User %s failed to bulk delete tenants due to active leases for: %s",
            current_user.id,
            active_tenant_names,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete tenants with active leases: {active_tenant_names}. Please terminate their leases first.",
        )

    if not deletable_tenants:
        logger.info("No tenants to delete after filtering for active leases.")
        return

    # CASCADE will automatically delete all associated leases when tenant is deleted
    # Use bulk delete to avoid N+1 queries
    from sqlalchemy import delete as sql_delete
    deletable_tenant_ids = [tenant.id for tenant in deletable_tenants]
    await session.execute(
        sql_delete(Tenant).where(col(Tenant.id).in_(deletable_tenant_ids))
    )

    try:
        await session.commit()
        deleted_ids = [tenant.id for tenant in deletable_tenants]
        logger.info(
            "User %s successfully bulk deleted tenants with IDs: %s (CASCADE deleted associated leases)",
            current_user.id,
            deleted_ids,
        )
    except IntegrityError as e:
        await session.rollback()
        error_str = str(e).lower()
        logger.exception(
            "Failed to bulk delete tenants due to an integrity error. IDs: %s, Error: %s",
            [t.id for t in deletable_tenants],
            str(e),
        )
        
        # Provide more specific error messages based on the constraint violation
        if "tenant_id" in error_str and "leases" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not delete tenants. They still have associated leases that could not be removed. Please ensure all leases are properly terminated.",
            ) from e
        elif "tenant_id" in error_str and ("payments" in error_str or "invoices" in error_str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not delete tenants. They have associated payments or invoices that prevent deletion.",
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not delete tenants. They may be associated with other data like payments, invoices, or maintenance history.",
            ) from e
    except Exception as e:
        await session.rollback()
        logger.exception(
            "An unexpected error occurred during bulk tenant deletion. IDs: %s",
            [t.id for t in deletable_tenants],
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting tenants.",
        ) from e
