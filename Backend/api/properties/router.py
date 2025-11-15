import logging
from typing import Annotated
from uuid import UUID as PythonUUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.enums import PropertyStatus
from Backend.models.user import User
from .schemas import (
    PropertyCreate,
    PropertyDetailResponse,
    PropertyResponse,
    PropertyUpdate,
    PropertyBulkDelete,
)
from .service import PropertyService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/properties",
    tags=["properties"],
)


@router.get("/{property_id}", response_model=PropertyDetailResponse)
async def get_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieves a property by its ID, including owner details and all units with tenant information.
    """
    try:
        return await PropertyService.get_property(property_id, current_user, session)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error retrieving property")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve property: {str(e)}",
        )


@router.get("/", response_model=list[PropertyResponse])
async def get_properties(
    status_filter: Annotated[
        PropertyStatus | None, Query(description="Filter by property status")
    ] = None,
    property_type: Annotated[
        str | None, Query(description="Filter by property type")
    ] = None,
    owner_id: Annotated[
        PythonUUID | None, Query(description="Filter by owner's user ID (for admins)")
    ] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieves all properties accessible to the current user, with optional
    filtering.
    """
    try:
        return await PropertyService.get_properties(
            current_user, session, status_filter, property_type, owner_id
        )
    except Exception as e:
        logger.exception("Error fetching properties")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch properties: {str(e)}",
        )


@router.post(
    "/",
    response_model=PropertyDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Creates a new property for the current user, optionally including associated units.
    """
    try:
        return await PropertyService.create_property(
            property_data, current_user, session
        )
    except HTTPException:
        # Let HTTPException pass through (for validation errors, etc.)
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.exception("Error creating property")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create property: {str(e)}",
        )


@router.put("/{property_id}", response_model=PropertyDetailResponse)
async def update_property(
    property_id: int,
    property_data: PropertyUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Updates an existing property's details and returns the updated property information.
    """
    try:
        return await PropertyService.update_property(
            property_id, property_data, current_user, session
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.exception("Error updating property %s", property_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update property: {str(e)}",
        )


@router.delete("/bulk-delete-property", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_properties(
    data: PropertyBulkDelete,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Bulk deletes multiple properties if the current user is the owner or an admin.
    
    Prevents deletion of properties with:
    - Active or pending leases
    - Rented units (is_rented=True)
    - Tenants with current_property_id pointing to the property
    """
    try:
        await PropertyService.bulk_delete_properties(
            data.property_ids, current_user, session
        )
        return None
    except HTTPException:
        raise
    except Exception as e:
        # Service layer handles rollback, just log and re-raise
        logger.exception("Error bulk deleting properties")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk delete properties: {str(e)}",
        )


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Deletes a property by its ID if the current user is the owner or an admin.
    """
    try:
        await PropertyService.delete_property(property_id, current_user, session)
        return None
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.exception("Error deleting property")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete property: {str(e)}",
        ) 