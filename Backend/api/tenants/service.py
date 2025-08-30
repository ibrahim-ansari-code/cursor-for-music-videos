import logging
from uuid import UUID as PythonUUID
from typing import Any

from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy import and_, not_, or_, Select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlmodel import col

from Backend.api.tenants.schemas import (
    LeaseResponseSimple,
    PropertyResponseSimple,
    TenantCreate,
    TenantResponse,
    UnitResponseSimple,
)
from Backend.models.enums import UserType
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.tenant import Tenant, TenantStatus
from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime
from Backend.api.quickbooks.customers import link_or_create_qb_customer

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
        await link_or_create_qb_customer(user=user, tenant_data=tenant_data)
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
    
    For each tenant, loads:
    1. Latest assigned property unit and its property information (from current_property_id)
    2. All leases with their associated property and unit details
    
    Returns only tenants with valid IDs.
    """
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

        # Load all leases for this tenant with property/unit details
        lease_query = (
            select(Lease)
            .options(
                selectinload(getattr(Lease, "property")),
                selectinload(getattr(Lease, "unit"))
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
            
            lease_responses.append(lease_response)

        tenant_response.leases = lease_responses

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
