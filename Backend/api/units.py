from typing import List, Optional
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from pydantic import BaseModel, constr

from Backend.database import get_session
from Backend.models.property import Property, PropertyUnit
from Backend.models.user import User
from Backend.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# === Models ===
class UnitBase(BaseModel):
    name: constr(min_length=1, max_length=255)
    description: Optional[str] = None
    size: Optional[float] = None
    monthly_rent: Optional[float] = None
    is_rented: bool = False
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    floor: Optional[int] = None

class UnitCreate(UnitBase):
    pass

class UnitUpdate(UnitBase):
    name: Optional[constr(min_length=1, max_length=255)] = None # Allow partial updates
    is_rented: Optional[bool] = None
    floor: Optional[int] = None # Added optional floor for updates

class UnitResponse(UnitBase):
    id: int
    property_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# === Helper Function ===
async def get_unit_or_404(unit_id: int, session: AsyncSession, current_user: User) -> PropertyUnit:
    """Retrieve a unit by ID, ensuring the current user has permission."""
    result = await session.execute(
        select(PropertyUnit)
        .options(joinedload(PropertyUnit.property)) # Load property for permission check
        .where(PropertyUnit.id == unit_id)
    )
    unit = result.scalar_one_or_none()

    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

    # Permission check: User must own the parent property or be an admin
    if unit.property.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this unit"
        )
    return unit

# === API Routes ===

@router.post("/properties/{property_id}/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED, tags=["units"])
async def create_unit_for_property(
    property_id: int,
    unit_data: UnitCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new unit for a specific property."""
    # Check if property exists and user has permission
    result = await session.execute(select(Property).where(Property.id == property_id))
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    if property_obj.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add units to this property"
        )

    # Create the new unit
    new_unit = PropertyUnit(
        **unit_data.model_dump(),
        property_id=property_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(new_unit)
    try:
        await session.commit()
        await session.refresh(new_unit)
        return new_unit
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating unit for property {property_id}: {e}")
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
    """Update an existing unit."""
    unit_to_update = await get_unit_or_404(unit_id, session, current_user)

    update_data = unit_data.model_dump(exclude_unset=True) # Get only fields that were provided
    if not update_data:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update data provided"
        )

    for key, value in update_data.items():
        setattr(unit_to_update, key, value)
    unit_to_update.updated_at = datetime.utcnow()

    try:
        await session.commit()
        await session.refresh(unit_to_update)
        return unit_to_update
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating unit {unit_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the unit."
        )


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["units"])
async def delete_unit(
    unit_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a unit."""
    unit_to_delete = await get_unit_or_404(unit_id, session, current_user)

    # Potential future check: Ensure unit is not tied to active leases before deletion
    # query = select(Lease).where(Lease.unit_id == unit_id, Lease.status == LeaseStatus.ACTIVE)
    # active_lease = await session.scalar(query)
    # if active_lease:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete unit with an active lease.")

    await session.delete(unit_to_delete)
    try:
        await session.commit()
        return None # No content response
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting unit {unit_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the unit."
        )

@router.get("/properties/{property_id}/units", response_model=List[UnitResponse], tags=["units"])
async def get_units_for_property(
    property_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all units for a specific property."""
    # Check if property exists and user has permission
    result = await session.execute(select(Property).where(Property.id == property_id))
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    if property_obj.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view units for this property"
        )

    # Retrieve units for the property
    result = await session.execute(
        select(PropertyUnit).where(PropertyUnit.property_id == property_id)
    )
    units = result.scalars().all()
    return units 