from typing import List, Optional
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload, selectinload
from pydantic import BaseModel

from Backend.database import get_session
from Backend.models.property import Property, PropertyUnit
from Backend.models.enums import PropertyStatus
from Backend.models.user import User
from Backend.api.auth import get_current_user
from Backend.models.lease import Lease, LeaseStatus
from Backend.api.units import TenantInfo, UnitResponse

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/properties",
    tags=["properties"],
)

# === Models ===
class PropertyCreate(BaseModel):
    name: str
    address: str
    city: str
    province: str
    postal_code: str
    property_type: str
    description: Optional[str] = None
    year_built: Optional[int] = None
    status: Optional[PropertyStatus] = PropertyStatus.ACTIVE
    units: Optional[List[str]] = None  # Optional list of unit names/numbers

# New Model for Property Updates (Excludes units and potentially immutable fields like property_type)
class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    description: Optional[str] = None
    year_built: Optional[int] = None
    status: Optional[PropertyStatus] = None

    class Config:
        extra = 'forbid' # Prevent unexpected fields like 'units'

class PropertyResponse(BaseModel):
    id: int
    name: str
    address: str
    city: str
    province: str
    postal_code: str
    property_type: str
    description: Optional[str] = None
    year_built: Optional[int] = None
    status: PropertyStatus = PropertyStatus.ACTIVE
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OwnerResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True

class UnitResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    size: Optional[float] = None
    monthly_rent: Optional[float] = None
    is_rented: bool
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    floor: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    tenant: Optional[TenantInfo] = None

    class Config:
        from_attributes = True

class PropertyDetailResponse_Standalone(BaseModel):
    # Fields from PropertyResponse
    id: int
    name: str
    address: str
    city: str
    province: str
    postal_code: str
    property_type: str
    description: Optional[str] = None
    year_built: Optional[int] = None
    status: PropertyStatus
    user_id: int
    created_at: datetime
    updated_at: datetime
    # Additional fields for detail view
    owner: Optional[OwnerResponse] = None
    units: List[UnitResponse] = []

    class Config:
        from_attributes = True
        # Ensure status default logic if needed, but we calculate it

class PropertyDetailResponse(PropertyResponse): # Keep original for reference if needed
    owner: Optional[OwnerResponse] = None
    # Add additional fields for property details
    status: str = "vacant"  # Default status
    units: List[UnitResponse] = []

    class Config:
        from_attributes = True

# === API Routes ===
@router.get("/{property_id}", response_model=PropertyDetailResponse_Standalone)
async def get_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get a specific property by ID with related data.
    """
    try:
        # Get property with owner and units relationship loaded
        # Also ensure the tenant within each unit is loaded
        query = (
            select(Property)
            .options(
                joinedload(Property.owner), 
                # Use selectinload for the collection of units
                selectinload(Property.units).options(
                    # Within each unit, use selectinload for the single tenant
                    selectinload(PropertyUnit.tenant)
                )
            )
            .where(Property.id == property_id)
        )
        result = await session.execute(query)
        # Call .unique() before scalar_one_or_none() for joined collections
        property_orm = result.unique().scalar_one_or_none()
        
        if not property_orm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )
        
        # Check permission - only owner or admin can view property details
        if property_orm.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this property"
            )
        
        # Use the property's database status as the default
        response_status = property_orm.status 
        
        # Determine property status based on units if they exist (using already loaded units)
        if property_orm.units:
            occupied_units = [unit for unit in property_orm.units if unit.is_rented]
            if not occupied_units:
                response_status = "vacant" # Override if units exist but none are rented
            elif len(occupied_units) == len(property_orm.units):
                response_status = "rented"
            elif len(occupied_units) > 0:
                response_status = "partially_rented"
            # If units exist but logic doesn't set rented/partially_rented/vacant, keep original property.status
        
        # Explicitly serialize units
        serialized_units_models = [] # Store Pydantic models
        if property_orm.units:
            for unit in property_orm.units:
                try:
                    # Create the base UnitResponse model from the ORM object
                    unit_model = UnitResponse.from_orm(unit)
                    
                    # Manually check and assign the tenant if loaded on the ORM object
                    if unit.tenant: 
                        try:
                            # Create TenantInfo model from the loaded ORM tenant
                            tenant_info_model = TenantInfo.from_orm(unit.tenant)
                            unit_model.tenant = tenant_info_model # Assign the TenantInfo model
                        except Exception as tenant_e:
                            logger.error(f"Error serializing tenant for unit {unit.id}: {tenant_e}")
                            unit_model.tenant = None # Ensure tenant is None if serialization fails
                    else:
                         unit_model.tenant = None # Ensure tenant is None if not loaded
                         
                    serialized_units_models.append(unit_model)

                except Exception as e:
                    logger.error(f"Error serializing unit {unit.id}: {e}")
                    # Optionally add placeholder or skip
        
        # Construct the standalone response model instance
        response = PropertyDetailResponse_Standalone(
            id=property_orm.id,
            name=property_orm.name,
            address=property_orm.address,
            city=property_orm.city,
            province=property_orm.province,
            postal_code=property_orm.postal_code,
            property_type=property_orm.property_type,
            description=property_orm.description,
            year_built=property_orm.year_built,
            status=response_status,  # Use calculated status
            user_id=property_orm.user_id,
            created_at=property_orm.created_at,
            updated_at=property_orm.updated_at,
            owner=OwnerResponse.from_orm(property_orm.owner) if property_orm.owner else None,
            units=serialized_units_models # Assign the list of UnitResponse models
        )
        
        return response # Return the Pydantic model instance directly
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving property: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the property"
        )

@router.get("/", response_model=List[PropertyResponse])
async def get_properties(
    status: Optional[PropertyStatus] = Query(None, description="Filter by property status"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all properties for the current user.
    If the user is an admin, they can see all properties.
    """
    try:
        query = select(Property)
        
        # Apply filters if provided
        if status:
            query = query.where(Property.status == status)
            
        if property_type:
            query = query.where(Property.property_type == property_type)
            
        if not current_user.is_admin:
            # Regular users can only see their own properties
            query = query.where(Property.user_id == current_user.id)
        
        result = await session.execute(query)
        properties = result.scalars().all()
        
        # Ensure status is not null for any property
        for prop in properties:
            if prop.status is None:
                prop.status = PropertyStatus.ACTIVE
        
        return properties
    except Exception as e:
        logger.error(f"Error fetching properties: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching properties"
        )

@router.post("/", response_model=PropertyDetailResponse_Standalone, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new property.
    The current authenticated user will be set as the owner.
    Optionally create units if provided in the request.
    """
    try:
        # Create new property instance
        new_property = Property(
            name=property_data.name,
            address=property_data.address,
            city=property_data.city,
            province=property_data.province,
            postal_code=property_data.postal_code,
            property_type=property_data.property_type,
            description=property_data.description,
            year_built=property_data.year_built,
            status=property_data.status or PropertyStatus.ACTIVE,
            user_id=current_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Add to database
        session.add(new_property)
        await session.commit()
        await session.refresh(new_property)
        
        # Remember the created property ID
        property_id = new_property.id
        
        # Create units if provided
        if property_data.units:
            now = datetime.utcnow()
            # Create unit objects
            for unit_name in property_data.units:
                # Extract floor from unit name if possible (e.g., "101" => floor 1)
                floor = 0  # Default floor
                if unit_name and unit_name[0].isdigit():
                    try:
                        floor = int(unit_name[0])
                    except ValueError:
                        pass
                    
                new_unit = PropertyUnit(
                    property_id=property_id,
                    name=unit_name,
                    floor=floor,
                    is_rented=False,  # Default to vacant
                    created_at=now,
                    updated_at=now
                )
                session.add(new_unit)
            
            await session.commit()
        
        # After creating everything, do a fresh query with proper relationship loading
        # to ensure all related data is included in response
        query = (select(Property)
                .options(joinedload(Property.owner), joinedload(Property.units))
                .where(Property.id == property_id))
        
        result = await session.execute(query)
        loaded_property = result.unique().scalar_one_or_none()
        
        if not loaded_property:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Property was created but could not be retrieved"
            )
        
        # Return the property with owner and units
        response = PropertyDetailResponse_Standalone.from_orm(loaded_property)
        return response

    except Exception as e:
        logger.error(f"Error creating property: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the property: {str(e)}"
        )

# New PUT Endpoint for Updating Properties
@router.put("/{property_id}", response_model=PropertyDetailResponse_Standalone)
async def update_property(
    property_id: int,
    property_data: PropertyUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update an existing property's details.
    This endpoint does NOT handle unit creation/modification.
    """
    # Fetch the existing property
    result = await session.execute(
        select(Property)
        .where(Property.id == property_id)
    )
    property_to_update = result.scalar_one_or_none()

    if not property_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )

    # Check permission - only owner or admin can update
    if property_to_update.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this property"
        )

    # Get update data, excluding unset fields
    update_data = property_data.model_dump(exclude_unset=True)

    if not update_data:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update data provided"
        )

    # Update the property fields
    for key, value in update_data.items():
        setattr(property_to_update, key, value)

    property_to_update.updated_at = datetime.utcnow()

    try:
        session.add(property_to_update)
        await session.commit()
        await session.refresh(property_to_update)

        # Re-fetch with relationships for the response model
        query = (
            select(Property)
            .options(
                joinedload(Property.owner),
                selectinload(Property.units).options(
                    selectinload(PropertyUnit.tenant)
                )
            )
            .where(Property.id == property_id)
        )
        result = await session.execute(query)
        updated_property_orm = result.unique().scalar_one_or_none()

        if not updated_property_orm:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Property updated but could not be re-retrieved"
            )

        # Manually construct the response to recalculate status if needed
        # (similar logic as get_property)
        response_status = updated_property_orm.status
        if updated_property_orm.units:
            occupied_units = [unit for unit in updated_property_orm.units if unit.is_rented]
            if not occupied_units:
                response_status = "vacant"
            elif len(occupied_units) == len(updated_property_orm.units):
                response_status = "rented"
            elif len(occupied_units) > 0:
                response_status = "partially_rented"

        serialized_units = []
        if updated_property_orm.units:
             for unit in updated_property_orm.units:
                 unit_model = UnitResponse.from_orm(unit)
                 if unit.tenant:
                     try:
                         tenant_info = TenantInfo.from_orm(unit.tenant)
                         unit_model.tenant = tenant_info
                     except Exception as e:
                         logger.error(f"Tenant serialization error in update response: {e}")
                         unit_model.tenant = None
                 else:
                      unit_model.tenant = None
                 serialized_units.append(unit_model)

        response = PropertyDetailResponse_Standalone(
            id=updated_property_orm.id,
            name=updated_property_orm.name,
            address=updated_property_orm.address,
            city=updated_property_orm.city,
            province=updated_property_orm.province,
            postal_code=updated_property_orm.postal_code,
            property_type=updated_property_orm.property_type,
            description=updated_property_orm.description,
            year_built=updated_property_orm.year_built,
            status=response_status,
            user_id=updated_property_orm.user_id,
            created_at=updated_property_orm.created_at,
            updated_at=updated_property_orm.updated_at,
            owner=OwnerResponse.from_orm(updated_property_orm.owner) if updated_property_orm.owner else None,
            units=serialized_units
        )
        return response

    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating property {property_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the property: {str(e)}"
        )

@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a property by ID.
    Only the property owner or an admin can delete a property.
    """
    try:
        # Get property
        query = select(Property).where(Property.id == property_id)
        result = await session.execute(query)
        property_to_delete = result.scalar_one_or_none()
        
        if not property_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )
        
        # Check permission - only owner or admin can delete property
        if property_to_delete.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this property"
            )
        
        # Check for related entities that might block deletion
        # Units, leases, and expenses should be deleted in cascade
        # but we'll check for active leases which might block deletion
        
        # Check if there are active leases
        active_leases_query = select(Lease).where(
            and_(
                Lease.property_id == property_id,
                Lease.status.in_([LeaseStatus.ACTIVE, LeaseStatus.PENDING])
            )
        )
        active_leases_result = await session.execute(active_leases_query)
        active_leases = active_leases_result.scalars().all()
        
        if active_leases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete property with active leases"
            )
            
        # Delete property
        await session.delete(property_to_delete)
        await session.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting property: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the property: {str(e)}"
        ) 