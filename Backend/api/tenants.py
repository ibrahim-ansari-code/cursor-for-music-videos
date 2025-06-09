import logging
from datetime import datetime
from uuid import UUID as PythonUUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, computed_field, model_validator
from sqlalchemy import and_, not_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlmodel import col

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.enums import UserType
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property, PropertyUnit
from Backend.models.tenant import Tenant, TenantStatus
from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime

# Explicitly import property decorator (though usually built-in)
# from builtins import property # No longer needed


# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/tenants",
    tags=["tenants"],
)

# === Helper Function for Tenant Permission Checks ===


async def check_tenant_permission(
    tenant_id: int,
    session: AsyncSession,
    current_user: User,
    action: str = "view"
) -> Tenant:
    """
    Checks if the current user has permission to access or modify a tenant.
    - Admins have full access.
    - Landlords can only access tenants they own (via tenant.landlord_id).
    - Raises HTTPException 404 if tenant not found, 403 if not authorized.
    """
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if current_user.is_admin:
        return tenant

    if current_user.user_type == UserType.LANDLORD:
        if tenant.landlord_id == current_user.id:
            return tenant

    # If no permissions match, deny access.
    logger.warning("User %s permission denied for action '%s' on tenant %s",
                   current_user.id, action, tenant_id)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Not authorized to {action} this tenant")


def _build_tenant_filters(status_filter: TenantStatus | None, search: str | None) -> list:
    """
    Builds basic tenant filters for status and search criteria.

    Args:
        status_filter: Optional filter for tenant status.
        search: Optional search term for tenant name or email.

    Returns:
        List of SQLAlchemy filter conditions.
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
                col(Tenant.email).ilike(search_term)
            )
        )
    return filters


def _apply_landlord_permissions(current_user: User, property_id: int | None) -> list:
    """
    Applies landlord-specific permission filters for tenant access.

    Args:
        current_user: The current user (must be a landlord).
        property_id: Optional property ID to filter by.

    Returns:
        List of SQLAlchemy filter conditions for landlord permissions.
    """
    filters = []
    
    # The primary filter for a landlord is to only see tenants they own.
    filters.append(col(Tenant.landlord_id) == current_user.id)

    # If a specific property_id is provided, add that to the filter.
    if property_id:
        specific_property_filter = or_(
            col(Lease.property_id) == property_id,
            col(Tenant.current_property_id) == property_id
        )
        filters.append(specific_property_filter)

    return filters

# === Models ===

# Minimal response models for related entities


class PropertyResponseSimple(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class UnitResponseSimple(BaseModel):
    id: int
    name: str  # Assuming unit has a 'name' or 'unit_number' field
    property: PropertyResponseSimple | None = None  # Nested property info

    class Config:
        from_attributes = True


class TenantBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: TenantStatus = TenantStatus.ACTIVE
    user_id: PythonUUID | None = None
    current_property_id: int | None = None


class TenantCreate(TenantBase):
    # Allow receiving full_name from frontend for backward compatibility
    full_name: str | None = None

    @model_validator(mode='before')
    @classmethod
    def split_full_name(cls, data: dict) -> dict:
        """
        Pre-processes input data to split a combined full name into first and last names.

        If only `full_name` is provided and both `first_name` and `last_name` are missing,
        splits `full_name` at the first space into `first_name` and `last_name`. Ensures
        that `first_name` and `last_name` are never None, defaulting to empty strings if
        necessary.
        """
        if isinstance(data, dict):
            full_name = data.get('full_name')
            first_name = data.get('first_name')
            last_name = data.get('last_name')

            if full_name and not first_name and not last_name:
                names = full_name.split(' ', 1)
                data['first_name'] = names[0]
                if len(names) > 1:
                    data['last_name'] = names[1]
                else:
                    # Or handle as an error if last_name is required
                    data['last_name'] = ''
            # Ensure first_name and last_name are not None if not derived
            if data.get('first_name') is None:
                data['first_name'] = ''  # Or raise error
            if data.get('last_name') is None:
                data['last_name'] = ''  # Or raise error
        return data


class TenantUpdate(BaseModel):
    """Schema for updating an existing tenant profile."""
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: TenantStatus | None = None
    current_property_id: int | None = None

    # Allow receiving full_name from frontend
    full_name: str | None = None

    @model_validator(mode='before')
    @classmethod
    def split_full_name_update(cls, data: dict) -> dict:
        """
        Pre-processes input data to split a 'full_name' field into 'first_name' and 'last_name'
        for tenant updates.

        If 'full_name' is provided and both 'first_name' and 'last_name' are missing, splits
        'full_name' at the first space and assigns the parts accordingly. Removes 'full_name'
        from the data after processing.
        """
        if not isinstance(data, dict) or 'full_name' not in data or not data['full_name']:
            return data

        full_name = data.pop('full_name')  # Remove full_name after extracting

        # Only populate if first_name and last_name are not already provided
        if data.get('first_name') is not None or data.get('last_name') is not None:
            return data

        names = full_name.split(' ', 1)
        data['first_name'] = names[0]
        data['last_name'] = names[1] if len(
            names) > 1 else data.get('last_name')

        return data


class TenantResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: str | None = None
    email: str | None = None
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
    current_property_id: int | None = None
    # Add fields for unit and property
    unit: UnitResponseSimple | None = None
    property: PropertyResponseSimple | None = None

    class Config:
        from_attributes = True

    @computed_field
    def full_name(self) -> str:
        """
        Returns the tenant's full name by concatenating first and last names.
        """
        return f"{self.first_name} {self.last_name}".strip()

# === API Routes ===


@router.get("/", response_model=list[TenantResponse])
async def get_tenants(
    status_filter: TenantStatus | None = None,
    search: str | None = None,
    property_id: int | None = None,  # Allow filtering by property for landlords/admins
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Retrieves a list of tenants filtered by status, search term, and property, with results 
    limited by user role and ownership.

    Landlords receive tenants associated with their properties or unassigned tenants. Admins can 
    view all tenants, optionally filtered by property. Tenants cannot list other tenants and will 
    receive an empty list. Results include related unit and property information when available.

    Args:
        status_filter: Optional filter for tenant status.
        search: Optional search term for tenant name or email.
        property_id: Optional property ID to filter tenants by property.
        skip: Number of records to skip for pagination.
        limit: Maximum number of tenants to return.

    Returns:
        A list of TenantResponse objects matching the filters and access permissions.
    """
    logger.info("User %s (type: %s) is retrieving tenants",
                current_user.email, current_user.user_type)

    if current_user.user_type == UserType.TENANT:
        logger.warning("Tenant %s attempted to list tenants.", current_user.id)
        return []

    # Base query joining Tenant -> Lease -> Property to check ownership
    query = (
        select(Tenant).distinct()
        .outerjoin(Lease, col(Tenant.id) == col(Lease.tenant_id))
        .outerjoin(Property, col(Lease.property_id) == col(Property.id))
    )

    # Build basic filters
    filters = _build_tenant_filters(status_filter, search)

    # Apply user-type specific permission filters
    if current_user.user_type == UserType.LANDLORD:
        landlord_filters = _apply_landlord_permissions(
            current_user, property_id)
        filters.extend(landlord_filters)
    elif current_user.is_admin:
        # Admin can filter by any property_id if provided
        if property_id:
            filters.append(or_(
                col(Lease.property_id) == property_id,
                col(Tenant.current_property_id) == property_id
            ))

    if filters:
        query = query.where(and_(*filters))

    # Apply pagination and ordering
    query = query.order_by(
        Tenant.last_name, Tenant.first_name).offset(skip).limit(limit)

    result = await session.execute(query)
    tenants_orm = result.scalars().all()
    logger.info("Retrieved %s tenants for user %s",
                len(tenants_orm), current_user.id)

    # Convert ORM objects to response models, fetching related unit/property info
    response_data = []
    for tenant in tenants_orm:
        tenant_response = TenantResponse.model_validate(tenant)
        # Find the most relevant/current unit/property for display
        current_prop_id_to_check = tenant.current_property_id

        if current_prop_id_to_check:
            unit_query = (
                select(PropertyUnit)
                .options(selectinload(getattr(PropertyUnit, "property")))
                .where(col(PropertyUnit.tenant_id) == tenant.id, col(PropertyUnit.property_id) == current_prop_id_to_check)
                .order_by(col(PropertyUnit.id).desc())
                .limit(1)
            )
            unit_result = await session.execute(unit_query)
            assigned_unit = unit_result.scalar_one_or_none()

            if assigned_unit and assigned_unit.property:
                property_info = PropertyResponseSimple.model_validate(
                    assigned_unit.property)
                unit_info = UnitResponseSimple.model_validate(assigned_unit)
                unit_info.property = property_info
                tenant_response.unit = unit_info
                tenant_response.property = property_info

        response_data.append(tenant_response)

    return [TenantResponse.model_validate(t) for t in response_data if t is not None and t.id is not None]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get a specific tenant by ID, checking permissions."""
    logger.info("User %s requesting tenant %s", current_user.email, tenant_id)
    tenant_orm = await check_tenant_permission(tenant_id, session, current_user, action="view")

    # Fetch the assigned unit and property (similar logic to get_tenants, needs optimization)
    tenant_response = TenantResponse.model_validate(tenant_orm)
    current_prop_id_to_check = tenant_orm.current_property_id

    if current_prop_id_to_check:
        unit_query = (
            select(PropertyUnit)
            .options(selectinload(getattr(PropertyUnit, "property")))
            .where(col(PropertyUnit.tenant_id) == tenant_orm.id, col(PropertyUnit.property_id) == current_prop_id_to_check)
            .order_by(col(PropertyUnit.id).desc())
            .limit(1)
        )
        unit_result = await session.execute(unit_query)
        assigned_unit = unit_result.scalar_one_or_none()

        if assigned_unit and assigned_unit.property:
            property_info = PropertyResponseSimple.model_validate(
                assigned_unit.property)
            unit_info = UnitResponseSimple.model_validate(assigned_unit)
            unit_info.property = property_info
            tenant_response.unit = unit_info
            tenant_response.property = property_info

    return tenant_response


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new tenant. Landlords can only assign to their own properties.
    Tenants cannot create other tenants.
    """
    logger.info("User %s creating tenant: %s", current_user.email, tenant_data)

    if current_user.user_type == UserType.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Tenants cannot create tenants")

    # If assigning to a property, check landlord ownership
    if tenant_data.current_property_id:
        if current_user.user_type == UserType.LANDLORD:
            prop_query = select(col(Property.id)).where(
                and_(col(Property.id) == tenant_data.current_property_id,
                     col(Property.user_id) == current_user.id)
            )
            prop_exists = await session.scalar(prop_query)
            if not prop_exists:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="Cannot assign tenant to a property you do not own")
        # Admin doesn't need this check but we need to ensure the property exists
        elif current_user.is_admin:
            prop_query = select(col(Property.id)).where(
                col(Property.id) == tenant_data.current_property_id)
            prop_exists = await session.scalar(prop_query)
            if not prop_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Assigned property not found")

    # Check if user_id is provided and if that user exists and is a Tenant type
    if tenant_data.user_id:
        user_query = select(User).where(col(User.id) == tenant_data.user_id)
        target_user = await session.scalar(user_query)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"User with ID {tenant_data.user_id} not found")
        if target_user.user_type != UserType.TENANT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"User ID {tenant_data.user_id} does not belong to a Tenant")
        # Check if a Tenant record already exists for this user_id
        existing_tenant_query = select(col(Tenant.id)).where(
            col(Tenant.user_id) == tenant_data.user_id)
        existing_tenant = await session.scalar(existing_tenant_query)
        if existing_tenant:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"A tenant profile already exists for user ID {tenant_data.user_id}")

    try:
        # Exclude full_name before validating with the Tenant model
        tenant_dict = tenant_data.model_dump(exclude={"full_name"})
        tenant = Tenant.model_validate(tenant_dict)  # Use Pydantic validation
        
        # Set the landlord_id from the currently authenticated user
        tenant.landlord_id = current_user.id

        tenant.created_at = create_audit_datetime()
        tenant.updated_at = create_audit_datetime()

        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        logger.info("Tenant %s created successfully by user %s",
                    tenant.id, current_user.id)
        return TenantResponse.model_validate(tenant)
    except Exception as e:
        logger.exception("Error creating tenant: %s",
                         tenant_data.email if tenant_data else 'Unknown')
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}"
        )


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update an existing tenant, checking permissions."""
    logger.info("User %s updating tenant %s", current_user.email, tenant_id)
    tenant = await check_tenant_permission(tenant_id, session, current_user, action="update")

    # If updating current_property_id, check landlord ownership
    if tenant_data.current_property_id is not None and tenant_data.current_property_id != tenant.current_property_id:
        if current_user.user_type == UserType.LANDLORD:
            prop_query = select(col(Property.id)).where(
                and_(col(Property.id) == tenant_data.current_property_id,
                     col(Property.user_id) == current_user.id)
            )
            prop_exists = await session.scalar(prop_query)
            if not prop_exists:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="Cannot assign tenant to a property you do not own")
        elif current_user.is_admin:
            prop_query = select(col(Property.id)).where(
                col(Property.id) == tenant_data.current_property_id)
            prop_exists = await session.scalar(prop_query)
            if not prop_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Assigned property not found")

    try:
        update_data = tenant_data.model_dump(
            exclude_unset=True, exclude={"full_name"})
        for key, value in update_data.items():
            setattr(tenant, key, value)

        tenant.updated_at = create_audit_datetime()

        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        logger.info("Tenant %s updated successfully by user %s",
                    tenant_id, current_user.id)
        return TenantResponse.model_validate(tenant)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating tenant %s", tenant_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant: {str(e)}"
        )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete a tenant, checking permissions."""
    logger.info("User %s deleting tenant %s", current_user.email, tenant_id)

    if current_user.user_type == UserType.TENANT:
        # Tenants cannot delete tenant profiles (even their own via this endpoint perhaps? TBD)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to delete tenants")

    tenant = await check_tenant_permission(tenant_id, session, current_user, action="delete")

    # Check if tenant has any associated active leases
    lease_query = select(col(Lease.id)).where(
        and_(col(Lease.tenant_id) == tenant_id, col(
            Lease.status) == LeaseStatus.ACTIVE)
    ).limit(1)
    active_lease_exists = await session.scalar(lease_query)

    if active_lease_exists:
        logger.warning(
            "Cannot delete tenant %s due to active leases", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete tenant with active leases. Please terminate or reassign leases first."
        )

    try:
        await session.delete(tenant)
        await session.commit()

        logger.info("Tenant %s deleted successfully by user %s",
                    tenant_id, current_user.id)
        return None
    except Exception as e:
        # Catch potential DB constraint errors if tenant is linked elsewhere
        logger.exception("Error deleting tenant %s", tenant_id)
        await session.rollback()
        # Provide a more generic error, or specific if known constraint
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tenant. Check for related records (e.g., historical payments, messages). Error: {str(e)}"
        )
