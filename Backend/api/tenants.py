import logging
from datetime import datetime
from uuid import UUID as PythonUUID
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, computed_field, model_validator, field_validator, ValidationError
from sqlalchemy import and_, not_, or_, func
from sqlalchemy.exc import IntegrityError
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
    first_name: str
    last_name: str
    phone: str
    email: str
    status: TenantStatus = TenantStatus.ACTIVE
    user_id: PythonUUID | None = None
    current_property_id: int | None = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """
        Normalizes and validates an email address.
        
        Ensures the email is present, trims whitespace, converts to lowercase, and checks for a valid format. Raises a ValueError if the email is missing or invalid.
        """
        if not v:
            raise ValueError('Email is required')
        email = v.strip().lower()
        if not email:
            raise ValueError('Email cannot be empty')
        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValueError('Invalid email format')
        return email

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validates that a name field is not empty or whitespace.
        
        Raises:
            ValueError: If the name is empty or contains only whitespace.
        
        Returns:
            The trimmed name string.
        """
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """
        Validates a phone number.

        The number must contain 10 to 15 digits, and may only include common
        formatting characters such as spaces, hyphens, parentheses, and a plus
        sign.
        
        Raises:
            ValueError: If the phone number is missing, contains an invalid number of digits, or includes disallowed characters.
        """
        # The 'if not v:' check is redundant because Pydantic ensures required fields are present.
        # An empty string will be caught by the digit length check.
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'[^0-9]', '', v)
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError('Phone number must contain 10-15 digits')
        # Additional validation: ensure the original string contains only allowed characters
        allowed_chars_pattern = r'^[\d\s\-\(\)\+]+$'
        if not re.match(allowed_chars_pattern, v):
            raise ValueError('Phone number contains invalid characters')
        return v.strip()


class TenantCreate(TenantBase):
    # Allow receiving full_name from frontend for backward compatibility
    full_name: str | None = None
    # Make all fields required except these optional ones
    current_property_id: int | None = None
    user_id: PythonUUID | None = None

    @model_validator(mode='before')
    @classmethod
    def split_full_name(cls, data: dict) -> dict:
        """
        Splits a combined full name into first and last names in input data if separate fields are missing.
        
        This pre-validation step ensures backward compatibility by extracting first and last names from a 'full_name' field when 'first_name' and 'last_name' are not provided.
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
                    data['last_name'] = ''  # Will be caught by field validator
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
    unassigned_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Retrieves a list of tenants filtered by status, search term, property, and assignment status, with results limited by user role and ownership.
    
    Landlords receive tenants associated with their properties or, if `unassigned_only` is true, only those without active leases. Admins can view all tenants, optionally filtered by property. Tenants cannot list other tenants and will receive an empty list. Each tenant in the result includes related unit and property information when available.
    
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

    if unassigned_only:
        # Security First: Always filter by the current landlord.
        base_query = select(Tenant).where(col(Tenant.landlord_id) == current_user.id)
        
        # Find all of the landlord's tenants who already have an active lease.
        active_lease_subquery = (
            select(col(Lease.tenant_id))
            .join(Property, col(Lease.property_id) == col(Property.id))
            .where(
                and_(
                    col(Property.user_id) == current_user.id,
                    col(Lease.status) == LeaseStatus.ACTIVE
                )
            )
            .distinct()
        )
        
        # Filter out tenants who are in the active list.
        query = base_query.where(not_(col(Tenant.id).in_(active_lease_subquery)))

        # Additionally, allow searching within the unassigned tenants.
        if search:
            search_term = f"%{search}%"
            query = query.where(or_(
                col(Tenant.first_name).ilike(search_term),
                col(Tenant.last_name).ilike(search_term),
                col(Tenant.email).ilike(search_term)
            ))
        
        # The main query is now the one we just built.
        # The original `filters` are ignored in this mode.
    else:
        # Apply user-type specific permission filters if not fetching unassigned
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
        
        # Apply the original filters to the query
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
    Creates a new tenant profile with validated data and appropriate landlord assignment.
    
    Landlords can only assign tenants to properties they own. Admins can assign tenants to any property, with the landlord set to the property's owner. Tenants cannot create other tenants. Validates user account linkage, ensures email uniqueness per landlord, and enforces property ownership rules. Returns the created tenant's details on success.
    
    Raises:
        HTTPException: If the user lacks permission, the property or user does not exist, the email is not unique, or validation fails.
    """
    logger.info("User %s creating tenant: %s", current_user.email, tenant_data.first_name + " " + tenant_data.last_name)

    if current_user.user_type == UserType.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Tenants cannot create tenants")

    assigned_landlord_id = current_user.id

    # For now, if admin is creating a tenant with a property, use the property owner as landlord
    if current_user.is_admin and tenant_data.current_property_id:
        # Admin assigning to a property - use property owner as landlord
        property_owner_query = select(col(Property.user_id)).where(
            col(Property.id) == tenant_data.current_property_id
        )
        property_owner_id = await session.scalar(property_owner_query)
        if property_owner_id:
            assigned_landlord_id = property_owner_id
        else:
            logger.warning("Admin creating tenant but property %s has no owner", 
                         tenant_data.current_property_id)

    # If assigning to a property, check ownership permissions
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
        elif current_user.is_admin:
            # Admin needs to ensure the property exists
            prop_query = select(col(Property.id)).where(
                col(Property.id) == tenant_data.current_property_id)
            prop_exists = await session.scalar(prop_query)
            if not prop_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Assigned property not found")

    # Check if user_id is provided and validate user account
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

    # Create tenant with database-level constraints for email uniqueness
    try:
        # Exclude full_name before validating with the Tenant model
        tenant_dict = tenant_data.model_dump(exclude={"full_name"})
        
        # Set the landlord_id from the assigned landlord
        tenant_dict["landlord_id"] = assigned_landlord_id
        
        # Create tenant instance - Pydantic validation already done
        tenant = Tenant.model_validate(tenant_dict)
        tenant.created_at = create_audit_datetime()
        tenant.updated_at = create_audit_datetime()

        session.add(tenant)
        
        try:
            await session.flush()  # Get the ID without committing
            await session.refresh(tenant)  # Refresh to get generated fields
            await session.commit()
            
            logger.info("Tenant %s created successfully by user %s",
                        tenant.id, current_user.id)
            return TenantResponse.model_validate(tenant)
            
        except IntegrityError as e:
            # Handle database constraint violations during flush
            logger.warning("Database integrity error creating tenant: %s", str(e))
            await session.rollback()
            
            # Check for unique constraint violations on email
            error_str = str(e).lower()
            if (("unique constraint" in error_str or "duplicate key" in error_str) and 
                ("email" in error_str or "idx_tenant_email_unique_per_landlord" in error_str)):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A tenant with this email address already exists."
                )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint violation. Please check your data."
            )
        except Exception as e:
            # Handle SQLAlchemy session state exceptions that wrap IntegrityError
            error_str = str(e).lower()
            
            # Check if this is a session rollback exception wrapping an IntegrityError for duplicate email
            if ("session's transaction has been rolled back" in error_str and 
                "integrityerror" in error_str and
                ("unique constraint" in error_str or "duplicate key" in error_str) and 
                ("email" in error_str or "idx_tenant_email_unique_per_landlord" in error_str)):
                # Don't rollback again since SQLAlchemy already did it
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A tenant with this email address already exists."
                )
            
            # For any other exception, rollback and re-raise
            logger.exception("Unexpected error during tenant creation: %s", str(e))
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while creating tenant."
            )
    except ValidationError as e:
        # Handle Pydantic validation errors
        logger.warning("Validation error creating tenant: %s", str(e))
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Validation error occurred while creating tenant."
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
