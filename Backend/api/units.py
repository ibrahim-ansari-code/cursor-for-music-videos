from typing import List, Optional
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from pydantic import BaseModel, constr, ValidationError

from Backend.database import get_session
from Backend.models.property import Property, PropertyUnit
from Backend.models.user import User
from Backend.models.tenant import Tenant
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
    floor: Optional[int] = None
    tenant_id: Optional[int] = None # Added tenant_id for assignments
    monthly_rent: Optional[float] = None # Ensure monthly_rent is included

class TenantInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    
    class Config:
        from_attributes = True

# Specific response model for creating a unit (omits tenant)
class UnitCreateResponse(UnitBase):
    id: int
    property_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Standard response model including optional tenant info
class UnitResponse(UnitBase):
    id: int
    property_id: int
    created_at: datetime
    updated_at: datetime
    tenant: Optional[TenantInfo] = None

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

@router.post("/properties/{property_id}/units", response_model=UnitCreateResponse, status_code=status.HTTP_201_CREATED, tags=["units"])
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
        logger.info(f"Created unit {new_unit.id}. Returning response without tenant info.")
        return new_unit
    except ValidationError as e: # Catch Pydantic validation errors specifically
        logger.error(f"Response validation error for new unit: {e.errors()}")
        # Don't rollback if commit succeeded but response failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unit created, but failed to serialize response: {e.errors()}"
        )
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
    """Update an existing unit, including tenant assignment."""
    unit_to_update = await get_unit_or_404(unit_id, session, current_user)

    update_data = unit_data.model_dump(exclude_unset=True) # Get only fields that were provided
    if not update_data:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update data provided"
        )

    # Apply all provided updates directly first
    tenant_id_updated = False
    new_tenant_id_value = update_data.get('tenant_id') # Get potential new value
    is_rented_updated = False
    new_is_rented_value = update_data.get('is_rented') # Get potential new value
    rent_explicitly_set = 'monthly_rent' in update_data

    for key, value in update_data.items():
        if hasattr(unit_to_update, key):
            setattr(unit_to_update, key, value)
            if key == 'tenant_id':
                tenant_id_updated = True
                # Verify tenant exists if ID is not None
                if value is not None:
                    tenant_result = await session.execute(select(Tenant).where(Tenant.id == value))
                    tenant = tenant_result.scalar_one_or_none()
                    if not tenant:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND, 
                            detail=f"Tenant with ID {value} not found"
                        )
            elif key == 'is_rented':
                is_rented_updated = True
        else:
             logger.warning(f"Attempted to update non-existent field '{key}' on PropertyUnit")

    # Handle dependencies after direct updates

    # Scenario 1: Unit is being made vacant
    if (tenant_id_updated and new_tenant_id_value is None) or \
       (is_rented_updated and new_is_rented_value is False):
        unit_to_update.tenant_id = None
        unit_to_update.is_rented = False
        # Clear rent ONLY if it wasn't explicitly provided in this update
        if not rent_explicitly_set:
            unit_to_update.monthly_rent = None
            
    # Scenario 2: Tenant is being assigned
    elif tenant_id_updated and new_tenant_id_value is not None:
        # If tenant assigned and is_rented wasn't explicitly set to False, mark as rented
        # (Handles case where is_rented is provided as True, or not provided at all)
        if not (is_rented_updated and new_is_rented_value is False):
             unit_to_update.is_rented = True
    # Scenario 3: Only is_rented changed (to True, handled by setattr)
    # Scenario 4: Only monthly_rent changed (handled by setattr)
    # Scenario 5: Only other fields changed (handled by setattr)

    unit_to_update.updated_at = datetime.utcnow()

    try:
        session.add(unit_to_update) 
        await session.commit()

        # Explicitly re-fetch the unit with the tenant relationship loaded
        # This ensures the data is ready for Pydantic serialization.
        query = (
            select(PropertyUnit)
            .options(selectinload(PropertyUnit.tenant)) # Use selectinload
            .where(PropertyUnit.id == unit_id)
        )
        result = await session.execute(query)
        final_unit = result.unique().scalar_one_or_none()

        if not final_unit:
             # This case is highly unlikely after a successful commit but good practice to check
             logger.error(f"Failed to re-fetch unit {unit_id} after update.")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Updated unit could not be found.")

        # Log the final unit state before returning
        logger.info(f"Final unit state before return: id={final_unit.id}, name={final_unit.name}, floor={final_unit.floor}, rent={final_unit.monthly_rent}, is_rented={final_unit.is_rented}, tenant_id={final_unit.tenant_id}")
        
        logger.info(f"Successfully updated and re-fetched unit {final_unit.id}. Tenant loaded: {final_unit.tenant}")
        return final_unit # Return the newly fetched instance

    except ValidationError as e:
        # Handle Pydantic validation errors during response serialization
        logger.error(f"Response validation error for unit {unit_id}: {e.errors()}")
        # Don't rollback if commit succeeded but response failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unit updated, but failed to serialize response: {e.errors()}"
        )
    except Exception as e:
        await session.rollback() # Rollback on other commit/DB errors
        logger.error(f"Error updating unit {unit_id}: {e}")
        # Check for the specific loader strategy error to provide a clearer message
        if "expected ORM mapped attribute for loader strategy argument" in str(e):
             logger.error("Loader strategy error still occurring despite API changes.")
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ORM relationship loading error after update. Please check model definitions. Error: {str(e)}"
             )
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
    """Get all units for a specific property, ensuring tenant data is loaded."""
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

    # Retrieve units for the property, explicitly loading tenant info
    result = await session.execute(
        select(PropertyUnit)
        .options(
            selectinload(PropertyUnit.tenant),
            selectinload(PropertyUnit.property)
        )
        .where(PropertyUnit.property_id == property_id)
    )
    units = result.unique().scalars().all()

    
    return units 