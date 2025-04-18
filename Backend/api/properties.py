from typing import List, Optional
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from pydantic import BaseModel, constr

from Backend.database import get_session
from Backend.models.property import Property, PropertyStatus, PropertyUnit
from Backend.models.user import User
from Backend.api.auth import get_current_user
from Backend.models.lease import Lease, LeaseStatus

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/properties",
    tags=["properties"],
)

# === Models ===
class PropertyCreate(BaseModel):
    name: constr(min_length=1, max_length=255)
    address: constr(min_length=1, max_length=255)
    city: constr(min_length=1, max_length=100)
    province: constr(min_length=1, max_length=50)
    postal_code: constr(min_length=1, max_length=20)
    property_type: constr(min_length=1, max_length=50)
    description: Optional[str] = None
    year_built: Optional[int] = None
    status: Optional[str] = PropertyStatus.ACTIVE

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
    status: str = PropertyStatus.ACTIVE  # Default to ACTIVE if None
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        # Make sure obj has all expected attributes with proper values
        if obj.status is None:
            obj.status = PropertyStatus.ACTIVE
        return super().from_orm(obj)

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
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PropertyDetailResponse(PropertyResponse):
    owner: Optional[OwnerResponse] = None
    # Add additional fields for property details
    status: str = "vacant"  # Default status
    units: List[UnitResponse] = []

    class Config:
        from_attributes = True

# === API Routes ===
@router.get("/{property_id}", response_model=PropertyDetailResponse)
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
        query = select(Property).options(joinedload(Property.owner), joinedload(Property.units)).where(Property.id == property_id)
        result = await session.execute(query)
        # Call .unique() before scalar_one_or_none() for joined collections
        property = result.unique().scalar_one_or_none()
        
        if not property:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )
        
        # Check permission - only owner or admin can view property details
        if property.owner_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this property"
            )
        
        # Use the property's database status as the default
        response_status = property.status 
        
        # Determine property status based on units if they exist (using already loaded units)
        if property.units:
            occupied_units = [unit for unit in property.units if unit.is_rented]
            if not occupied_units:
                response_status = "vacant" # Override if units exist but none are rented
            elif len(occupied_units) == len(property.units):
                response_status = "rented"
            elif len(occupied_units) > 0:
                response_status = "partially_rented"
            # If units exist but logic doesn't set rented/partially_rented/vacant, keep original property.status
        
        # Create response with owner info, status and units
        response = PropertyDetailResponse.from_orm(property) # Includes units
        response.status = response_status # Assign the determined status
        
        return response
        
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
    status: Optional[str] = Query(None, description="Filter by property status"),
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
            query = query.where(Property.owner_id == current_user.id)
        
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

@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new property.
    The current authenticated user will be set as the owner.
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
            status=property_data.status,
            owner_id=current_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Add to database
        session.add(new_property)
        await session.commit()
        await session.refresh(new_property)

        return new_property

    except Exception as e:
        logger.error(f"Error creating property: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the property"
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
        if property_to_delete.owner_id != current_user.id and not current_user.is_admin:
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