import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.user import User

from Backend.api.leases.schemas import LeaseResponse

from .schemas import (
    UnitCreate, UnitCreateResponse, UnitResponse, UnitUpdate,
    BulkUnitCreate, BulkUnitCreateResponse, UnitSearchFilters
)
from .service import UnitService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["units"])


@router.post("/properties/{property_id}/units", response_model=UnitCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_unit_for_property(
    property_id: int,
    unit_data: UnitCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new unit, ensuring user owns the property."""
    try:
        return await UnitService.create_unit(property_id, unit_data, session, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error creating unit")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the unit."
        )


@router.post("/properties/{property_id}/units/bulk", response_model=BulkUnitCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_units_bulk(
    property_id: int,
    bulk_data: BulkUnitCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create multiple units for a property in a single request.
    
    This endpoint allows bulk creation of units, which is useful when setting up a new property
    with multiple units. The operation is transactional - either all valid units are created
    or none are created if there's a database error.
    
    Returns a response containing successfully created units and any failures with error details.
    """
    try:
        return await UnitService.create_units_bulk(property_id, bulk_data, session, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in bulk unit creation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during bulk unit creation."
        )


@router.post("/units/search", response_model=list[UnitResponse])
async def search_units(
    filters: UnitSearchFilters,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0, description="Number of units to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of units to return")
) -> list[UnitResponse]:
    """
    Search for units across all properties with various filters.
    
    This endpoint allows searching for units based on criteria like rent range, number of bedrooms,
    bathrooms, and rental status. Non-admin users can only search their own properties.
    
    Example filters:
    - Find all 2-bedroom units under $1500/month that are available
    - Find all units in specific properties
    - Find units with at least 2 bathrooms
    """
    try:
        return await UnitService.search_units(filters, session, current_user, skip, limit)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error searching units")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while searching units."
        )


@router.get("/units/{unit_id}", response_model=UnitResponse)
async def get_unit(
    unit_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> UnitResponse:
    """
    Retrieves a single unit by its ID, ensuring the user has permission.
    """
    try:
        return await UnitService.get_unit(unit_id, session, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error retrieving unit")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the unit."
        )


@router.get("/properties/{property_id}/units", response_model=list[UnitResponse])
async def get_units_for_property(
    property_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0, description="Number of units to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of units to return")
) -> list[UnitResponse]:
    """
    Retrieves all units for a specified property, ensuring the user has permission to access them.

    Checks that the property exists and that the current user is either an admin or the owner of the property. Returns a list of units for the property, including tenant information, ordered by unit name.
    """
    try:
        return await UnitService.get_units_for_property(property_id, session, current_user, skip, limit)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error retrieving units for property")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the units."
        )


@router.put("/units/{unit_id}", response_model=UnitResponse)
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
    try:
        return await UnitService.update_unit(unit_id, unit_data, session, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error updating unit")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the unit."
        )


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
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
    try:
        await UnitService.delete_unit(unit_id, session, current_user)
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error deleting unit")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the unit."
        )


@router.get("/units/{unit_id}/lease", response_model=LeaseResponse)
async def get_unit_lease(
    unit_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> LeaseResponse:
    """
    Get the active lease for a unit.
    
    Returns the currently active lease for the specified unit.
    Raises 404 if the unit doesn't exist or has no active lease.
    """
    try:
        return await UnitService.get_unit_lease(unit_id, session, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error retrieving unit lease")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the unit lease."
        )
