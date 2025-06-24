import logging
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import col

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property, PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# === Models ===


class UnitBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    size: float | None = None
    monthly_rent: Decimal | None = None
    is_rented: bool = False
    bedrooms: int | None = None
    bathrooms: float | None = None
    floor: int | None = None


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    """Represents the fields that can be updated for a property unit."""
    name: str | None = None  # Allow partial updates
    description: str | None = None
    size: float | None = None
    monthly_rent: Decimal | None = None
    is_rented: bool | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    floor: int | None = None
    tenant_id: int | None = None  # Added tenant_id for assignments


class TenantInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str | None = None

    model_config = ConfigDict(from_attributes=True)

# Specific response model for creating a unit (omits tenant)


class UnitCreateResponse(UnitBase):
    id: int
    property_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Standard response model including optional tenant info


class UnitResponse(UnitBase):
    id: int
    property_id: int
    created_at: datetime
    updated_at: datetime
    tenant: TenantInfo | None = None

    model_config = ConfigDict(from_attributes=True)

# === Helper Function ===


async def get_unit_or_404(unit_id: int, session: AsyncSession, current_user: User) -> PropertyUnit:
    """Retrieve a unit by ID, ensuring the current user has permission."""
    result = await session.execute(
        select(PropertyUnit)
        # Load property for permission check, and tenant for potential use in response
        .options(
            joinedload(getattr(PropertyUnit, "property")),
            selectinload(getattr(PropertyUnit, "tenant"))
        )
        .where(col(PropertyUnit.id) == unit_id)
    )
    unit = result.unique().scalar_one_or_none()

    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

    # Permission check: User must own the parent property or be an admin
    if not current_user.is_admin and unit.property and unit.property.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this unit"
        )
    return unit

# === API Routes ===


@router.post("/properties/{property_id}/units", response_model=UnitCreateResponse, status_code=status.HTTP_201_CREATED, tags=["units"])
async def create_unit_for_property(
    property_id: int,
    unit_data: UnitCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new unit, ensuring user owns the property."""
    # Check if property exists and user has permission
    result = await session.execute(select(Property).where(col(Property.id) == property_id))
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    # Permission check using user_id
    if not current_user.is_admin and property_obj.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add units to this property"
        )

    # Create the new unit
    # Ensure created_at/updated_at are handled by model defaults if configured
    new_unit = PropertyUnit(
        **unit_data.model_dump(),
        property_id=property_id
        # created_at=datetime.utcnow(), # Handled by model?
        # updated_at=datetime.utcnow() # Handled by model?
    )
    session.add(new_unit)
    try:
        await session.commit()
        await session.refresh(new_unit)
        logger.info(
            f"Created unit {new_unit.id} for property {property_id} by user {current_user.id}")
        # Use the specific create response model which omits tenant info
        return UnitCreateResponse.model_validate(new_unit)
    except ValidationError as e:  # Catch Pydantic validation errors specifically
        logger.error(f"Response validation error for new unit: {e.errors()}")
        # Don't rollback if commit succeeded but response failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unit created, but failed to serialize response: {e.errors()}"
        )
    except Exception as e:
        await session.rollback()
        logger.error(
            f"Error creating unit for property {property_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the unit."
        )


@router.put("/units/{unit_id}", response_model=UnitResponse, tags=["units"])
async def update_unit(
    unit_id: int,
    unit_data: UnitUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Updates a property unit with partial or full data, enforcing permission and data consistency.

    Validates user authorization, applies requested updates, and ensures consistency between tenant assignment and rental status. Checks for tenant existence when assigning a tenant, and automatically clears or sets related fields to maintain logical integrity (e.g., vacating a unit clears tenant and rent unless explicitly set). Returns the updated unit with tenant information.

    Raises:
        HTTPException: If the unit or tenant does not exist, if no update data is provided, or if an error occurs during update or response serialization.
    """
    # get_unit_or_404 already performs the ownership check
    unit_to_update = await get_unit_or_404(unit_id, session, current_user)

    update_data = unit_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update data provided"
        )

    # Check if assigning a tenant
    new_tenant_id = update_data.get('tenant_id')
    if new_tenant_id is not None:
        # Verify tenant exists
        tenant_result = await session.execute(select(Tenant).where(Tenant.id == new_tenant_id))
        if not tenant_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID {new_tenant_id} not found"
            )
        # Optionally: Verify tenant is associated with the landlord if needed?
        # This might be too complex here, assume tenant assignment is allowed if landlord owns property.

    tenant_id_updated = 'tenant_id' in update_data
    is_rented_updated = 'is_rented' in update_data
    rent_explicitly_set = 'monthly_rent' in update_data

    # Apply updates from request
    for key, value in update_data.items():
        if hasattr(unit_to_update, key):
            setattr(unit_to_update, key, value)
        else:
            logger.warning(
                f"Attempted to update non-existent field '{key}' on PropertyUnit")

    # --- Logic to handle dependencies (tenant assignment <-> is_rented) ---
    # Scenario 1: Explicitly setting tenant_id to null (vacating)
    if tenant_id_updated and new_tenant_id is None:
        unit_to_update.is_rented = False  # Vacant units are not rented
        if not rent_explicitly_set:  # Clear rent only if not explicitly set in this request
            unit_to_update.monthly_rent = None

    # Scenario 2: Explicitly setting is_rented to False (vacating)
    elif is_rented_updated and update_data.get('is_rented') is False:
        unit_to_update.tenant_id = None  # Vacant units have no tenant assigned
        if not rent_explicitly_set:
            unit_to_update.monthly_rent = None

    # Scenario 3: Explicitly assigning a tenant (making rented)
    elif tenant_id_updated and new_tenant_id is not None:
        unit_to_update.is_rented = True  # Assigning a tenant implies rented

    # Scenario 4: Explicitly setting is_rented to True (but no tenant assigned yet)
    elif is_rented_updated and update_data.get('is_rented') is True and not tenant_id_updated:
        # If marking as rented without assigning a tenant, we might leave tenant_id as is or null?
        # Current logic: simply marks is_rented=True. tenant_id remains unchanged unless specified.
        pass  # is_rented already set by setattr loop

    # updated_at handled by model?
    # unit_to_update.updated_at = datetime.utcnow()

    try:
        session.add(unit_to_update)
        await session.commit()

        # Re-fetch with tenant loaded for response
        query = (
            select(PropertyUnit)
            .options(selectinload(getattr(PropertyUnit, "tenant")))
            .where(col(PropertyUnit.id) == unit_id)
        )
        result = await session.execute(query)
        final_unit = result.unique().scalar_one_or_none()

        if not final_unit:
            logger.error(f"Failed to re-fetch unit {unit_id} after update.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Updated unit could not be found.")

        logger.info(
            f"Unit {final_unit.id} updated successfully by user {current_user.id}")
        return final_unit

    except ValidationError as e:
        logger.error(
            f"Response validation error for unit {unit_id}: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unit updated, but failed to serialize response: {e.errors()}"
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating unit {unit_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the unit: {str(e)}"
        )


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["units"])
async def delete_unit(
    unit_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a property unit after verifying permissions and ensuring no active leases exist.

    Raises:
        HTTPException: If the unit has an active lease (400) or if an error occurs during deletion (500).
    """
    # get_unit_or_404 already performs the ownership check
    unit_to_delete = await get_unit_or_404(unit_id, session, current_user)

    # Add check for active leases associated with the unit
    active_lease_query = select(col(Lease.id)).where(
        and_(col(Lease.unit_id) == unit_id, col(
            Lease.status) == LeaseStatus.ACTIVE)
    ).limit(1)
    active_lease_exists = await session.scalar(active_lease_query)
    if active_lease_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot delete unit with an active lease.")

    await session.delete(unit_to_delete)
    try:
        await session.commit()
        logger.info(
            f"Unit {unit_id} deleted successfully by user {current_user.id}")
        return None
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting unit {unit_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the unit."
        )


@router.get("/units/{unit_id}", response_model=UnitResponse, tags=["units"])
async def get_unit(
    unit_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> UnitResponse:
    """
    Retrieves a single unit by its ID, ensuring the user has permission.
    """
    # The helper function performs the fetch, permission check, and eager loads the tenant.
    unit = await get_unit_or_404(unit_id, session, current_user)

    return UnitResponse.model_validate(unit)


@router.get("/properties/{property_id}/units", response_model=list[UnitResponse], tags=["units"])
async def get_units_for_property(
    property_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[UnitResponse]:
    """
    Retrieves all units for a specified property, ensuring the user has permission to access them.

    Checks that the property exists and that the current user is either an admin or the owner of the property. Returns a list of units for the property, including tenant information, ordered by unit name.
    """
    # Check if property exists and user has permission
    result = await session.execute(select(Property).where(col(Property.id) == property_id))
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    # Permission check using user_id
    if not current_user.is_admin and property_obj.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view units for this property"
        )

    # Retrieve units for the property, explicitly loading tenant info
    result = await session.execute(
        select(PropertyUnit)
        .options(
            selectinload(getattr(PropertyUnit, "tenant")),
            # selectinload(PropertyUnit.property) # Property already fetched and checked
        )
        .where(col(PropertyUnit.property_id) == property_id)
        .order_by(PropertyUnit.name)  # Add consistent ordering
    )
    units = result.unique().scalars().all()

    # Convert ORM objects to Pydantic response models
    return [UnitResponse.model_validate(unit) for unit in units]
