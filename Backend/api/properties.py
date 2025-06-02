import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import col

from Backend.api.auth import get_current_user
from Backend.api.units import TenantInfo
from Backend.database import get_session
from Backend.models.enums import PropertyStatus
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property, PropertyUnit
from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime

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
    description: str | None = None
    year_built: int | None = None
    status: PropertyStatus | None = PropertyStatus.ACTIVE
    units: list[str] | None = None

# New Model for Property Updates (Excludes units and potentially immutable fields like property_type)


class PropertyUpdate(BaseModel):
    """Schema for updating an existing property's details."""
    name: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
    description: str | None = None
    year_built: int | None = None
    status: PropertyStatus | None = None

    class Config:
        extra = 'forbid'  # Prevent unexpected fields like 'units'


class PropertyResponse(BaseModel):
    id: int
    name: str
    address: str
    city: str
    province: str
    postal_code: str
    property_type: str
    description: str | None = None
    year_built: int | None = None
    status: PropertyStatus = PropertyStatus.ACTIVE
    user_id: str  # Changed from int to str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OwnerResponse(BaseModel):
    id: str  # Changed from int to str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    profile_image_url: str | None = None

    class Config:
        from_attributes = True


class UnitResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    size: float | None = None
    monthly_rent: float | None = None
    is_rented: bool
    bedrooms: int | None = None
    bathrooms: float | None = None
    floor: int | None = None
    created_at: datetime
    updated_at: datetime
    tenant: TenantInfo | None = None

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
    description: str | None = None
    year_built: int | None = None
    status: str  # Changed from PropertyStatus to str
    user_id: str  # Will inherit str from PropertyResponse if it was based on it, explicitly set for clarity
    created_at: datetime
    updated_at: datetime
    # Additional fields for detail view
    owner: OwnerResponse | None = None
    units: list[UnitResponse] = []  # Changed from List[UnitResponse]

    class Config:
        from_attributes = True
        # Ensure status default logic if needed, but we calculate it


# Keep original for reference if needed
class PropertyDetailResponse(PropertyResponse):
    owner: OwnerResponse | None = None
    # Add additional fields for property details
    # Changed from str to PropertyStatus
    status: PropertyStatus = PropertyStatus.ACTIVE
    units: list[UnitResponse] = []  # Changed from List[UnitResponse]

# === API Routes ===


@router.get("/{property_id}", response_model=PropertyDetailResponse_Standalone)
async def get_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Retrieves a property by its ID, including owner and unit details with tenant
    information.

    Checks that the requesting user is the property owner or an admin. Calculates
    the property's status based on the rental status of its units, overriding the
    stored status if all units are vacant, all are rented, or some are partially
    rented. Serializes all related data for the response. Raises a 404 error if
    the property does not exist, a 403 error if the user lacks permission, or a
    500 error if a critical retrieval issue occurs.

    Returns:
        A detailed property response including owner and units with tenant info.
    """
    try:
        # Get property with owner and units relationship loaded
        # Also ensure the tenant within each unit is loaded
        query = (
            select(Property)
            .options(
                joinedload(getattr(Property, "owner")),
                # Use selectinload for the collection of units
                selectinload(getattr(Property, "units")).options(
                    # Within each unit, use selectinload for the single tenant
                    selectinload(getattr(PropertyUnit, "tenant"))
                )
            )
            .where(col(Property.id) == property_id)
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
            occupied_units = [
                unit for unit in property_orm.units if unit.is_rented]
            if not occupied_units:
                response_status = "vacant"  # Override if units exist but none are rented
            elif len(occupied_units) == len(property_orm.units):
                response_status = "rented"
            elif len(occupied_units) > 0:
                response_status = "partially_rented"
            # If units exist but logic doesn't set rented/partially_rented/vacant, keep original property.status

        # Explicitly serialize units
        serialized_units_models = []  # Store Pydantic models
        if property_orm.units:
            for unit in property_orm.units:
                try:
                    # Create the base UnitResponse model from the ORM object
                    unit_model = UnitResponse.model_validate(unit)

                    # Manually check and assign the tenant if loaded on the ORM object
                    if unit.tenant:
                        try:
                            # Create TenantInfo model from the loaded ORM tenant
                            tenant_info_model = TenantInfo.model_validate(
                                unit.tenant)
                            unit_model.tenant = tenant_info_model  # Assign the TenantInfo model
                        except Exception as tenant_e:
                            # Log the error but continue processing
                            logger.error(
                                "Error serializing tenant for unit %s: %s", unit.id, tenant_e)
                            unit_model.tenant = None  # Clear tenant if serialization fails

                    serialized_units_models.append(unit_model)

                except Exception as e:
                    # Log the error but continue processing other units
                    logger.error("Error serializing unit %s: %s", unit.id, e)
                    continue  # Skip this unit and continue with the next one

        # Construct the standalone response model instance
        if property_orm.id is None:
            logger.error(
                "Property ID is None after database fetch, which should not happen.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Critical error: Property ID missing after retrieval."
            )

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
            # Ensure user_id is explicitly cast to string
            user_id=str(property_orm.user_id),
            created_at=property_orm.created_at,
            updated_at=property_orm.updated_at,
            owner=OwnerResponse.model_validate(
                property_orm.owner) if property_orm.owner else None,
            units=serialized_units_models  # Assign the list of UnitResponse models
        )

        return response  # Return the Pydantic model instance directly

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error retrieving property")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve property: {str(e)}"
        )


@router.get("/", response_model=list[PropertyResponse])
async def get_properties(
    status_filter: Annotated[PropertyStatus | None, Query(
        description="Filter by property status")] = None,
    property_type: Annotated[str | None, Query(
        description="Filter by property type")] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Retrieves all properties accessible to the current user, with optional
    filtering.

    Admins receive all properties, while regular users see only their own.
    Supports filtering by property status and property type. Ensures all returned
    properties have a non-null status, defaulting to ACTIVE if missing.

    Returns:
        A list of PropertyResponse objects representing the accessible properties.
    """
    try:
        query = select(Property)

        # Apply filters if provided
        if status_filter:
            query = query.where(col(Property.status) == status_filter)

        if property_type:
            query = query.where(col(Property.property_type) == property_type)

        if not current_user.is_admin:
            # Regular users can only see their own properties
            query = query.where(col(Property.user_id) == current_user.id)

        result = await session.execute(query)
        properties = result.scalars().all()

        # Ensure status is not null for any property
        for prop in properties:
            if prop.status is None:
                prop.status = PropertyStatus.ACTIVE

        return properties
    except Exception as e:
        logger.exception("Error fetching properties")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch properties: {str(e)}"
        )


@router.post("/", response_model=PropertyDetailResponse_Standalone, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Creates a new property with the current user as the owner.

    If unit names are provided, creates associated units for the property,
    assigning each to the appropriate floor if possible. Returns the created
    property with owner and units included in the response. Raises a 500 error
    if property creation or retrieval fails.
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
            # Ensure user_id is explicitly cast to string
            user_id=str(current_user.id),
            created_at=create_audit_datetime(),
            updated_at=create_audit_datetime()
        )

        # Add to database
        session.add(new_property)
        await session.commit()
        await session.refresh(new_property)

        # Remember the created property ID
        property_id = new_property.id

        # Create units if provided
        if property_data.units:
            now = create_audit_datetime()
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
                 .options(joinedload(getattr(Property, "owner")), joinedload(getattr(Property, "units")))
                 .where(col(Property.id) == property_id))

        result = await session.execute(query)
        loaded_property = result.unique().scalar_one_or_none()

        if not loaded_property:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Property was created but could not be retrieved"
            )

        # Return the property with owner and units
        response = PropertyDetailResponse_Standalone.model_validate(
            loaded_property)
        return response

    except Exception as e:
        await session.rollback()
        logger.exception("Error creating property")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create property: {str(e)}"
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
    Updates an existing property's details and returns the updated information.

    Only the property owner or an admin can update a property. This operation
    does not allow modifying or creating property units. The response includes
    the updated property details, recalculated status based on unit occupancy,
    and related owner and unit information. Raises a 404 error if the property
    does not exist, a 403 error if the user lacks permission, and a 400 error
    if no update data is provided.
    """
    # Fetch the existing property
    result = await session.execute(
        select(Property)
        .where(col(Property.id) == property_id)
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
        if value is not None:
            setattr(property_to_update, key, value)

    property_to_update.updated_at = create_audit_datetime()

    try:
        session.add(property_to_update)
        await session.commit()
        await session.refresh(property_to_update)

        # Re-fetch with relationships for the response model
        query = (
            select(Property)
            .options(
                joinedload(getattr(Property, "owner")),
                selectinload(getattr(Property, "units")).options(
                    selectinload(getattr(PropertyUnit, "tenant"))
                )
            )
            .where(col(Property.id) == property_id)
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
            occupied_units = [
                unit for unit in updated_property_orm.units if unit.is_rented]
            if not occupied_units:
                response_status = "vacant"
            elif len(occupied_units) == len(updated_property_orm.units):
                response_status = "rented"
            elif len(occupied_units) > 0:
                response_status = "partially_rented"

        serialized_units = []
        if updated_property_orm.units:
            for unit in updated_property_orm.units:
                unit_model = UnitResponse.model_validate(unit)
                if unit.tenant:
                    try:
                        tenant_info = TenantInfo.model_validate(unit.tenant)
                        unit_model.tenant = tenant_info
                    except Exception as e:
                        # Log the error but continue processing
                        logger.error(
                            "Tenant serialization error in update response: %s", e)
                        # Continue without tenant info rather than failing the whole request
                        unit_model.tenant = None
                else:
                    unit_model.tenant = None
                serialized_units.append(unit_model)

        # Ensure ID is not None after database operations
        if updated_property_orm.id is None:
            logger.error(
                "Property ID is None after database update, which should not happen.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Critical error: Property ID missing after update."
            )

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
            # Ensure user_id is explicitly cast to string
            user_id=str(updated_property_orm.user_id),
            created_at=updated_property_orm.created_at,
            updated_at=updated_property_orm.updated_at,
            owner=OwnerResponse.model_validate(
                updated_property_orm.owner) if updated_property_orm.owner else None,
            units=serialized_units
        )
        return response

    except Exception as e:
        await session.rollback()
        logger.exception("Error updating property %s", property_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update property: {str(e)}"
        )


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Deletes a property by its ID if the current user is the owner or an admin.

    Raises a 404 error if the property does not exist, a 403 error if the user
    lacks permission, and a 400 error if there are active leases associated with
    the property. Performs a cascade delete for related entities unless blocked
    by active leases. Returns HTTP 204 No Content on successful deletion.
    """
    try:
        # Get property
        query = select(Property).where(col(Property.id) == property_id)
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
                col(Lease.property_id) == property_id,
                col(Lease.status).in_(
                    [LeaseStatus.ACTIVE, LeaseStatus.PENDING])
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
        await session.rollback()
        logger.exception("Error deleting property")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete property: {str(e)}"
        )
