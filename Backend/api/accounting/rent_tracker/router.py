"""
API router for rent tracker endpoints.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.user import User

from .schemas import (
    RentTrackingEntry,
    RentTrackerSummary,
    RentTrackerFilter,
    RentStatus
)
from .service import RentTrackerService


logger = logging.getLogger(__name__)


# Set up API router
# Note: Prefix is handled by the accounting router that includes this one
router = APIRouter(
    tags=["rent-tracker"],
)


@router.get(
    "/",
    response_model=List[RentTrackingEntry],
    status_code=status.HTTP_200_OK,
    summary="Get rent tracking entries",
    description="Retrieve rent payment status for all active leases for a specified month."
)
async def get_rent_tracker(
    month: Optional[int] = Query(None, ge=1, le=12, description="Month (1-12)"),
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Year"),
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    status: Optional[RentStatus] = Query(None, description="Filter by payment status"),
    include_vacant: bool = Query(False, description="Include vacant units"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> List[RentTrackingEntry]:
    """
    Get rent tracking entries for the specified filters.
    
    This endpoint provides a comprehensive view of rent payment status for all active
    leases. It calculates payment amounts, determines payment status (PAID, PARTIAL, 
    DUE, OVERDUE), and includes tenant and property information.
    
    **Authorization**: Only ADMIN and LANDLORD users can access this endpoint.
    
    **Features**:
    - Automatic calculation of payment status based on amounts paid
    - Detection of overdue payments with days overdue calculation
    - Filtering by month, year, property, and payment status
    - Optimized queries to prevent N+1 problems
    - Sorted results with overdue entries prioritized
    
    **Returns**:
    - List of rent tracking entries with payment details
    - Empty list if no matching leases found
    """
    filters = RentTrackerFilter(
        month=month,
        year=year,
        property_id=property_id,
        status=status,
        include_vacant=include_vacant
    )
    
    return await RentTrackerService.get_rent_tracker(
        session=session,
        current_user=current_user,
        filters=filters
    )


@router.get(
    "/summary",
    response_model=RentTrackerSummary,
    status_code=status.HTTP_200_OK,
    summary="Get rent tracker summary",
    description="Get summary statistics for rent collection."
)
async def get_rent_tracker_summary(
    month: Optional[int] = Query(None, ge=1, le=12, description="Month (1-12)"),
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Year"),
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> RentTrackerSummary:
    """
    Get summary statistics for rent tracking.
    
    This endpoint provides aggregate statistics about rent collection including:
    - Total expected vs collected amounts
    - Number of units by payment status
    - Overall collection rate percentage
    
    **Authorization**: Only ADMIN and LANDLORD users can access this endpoint.
    
    **Use Cases**:
    - Dashboard widgets showing collection performance
    - Monthly/yearly rent collection reports
    - Property-specific collection analysis
    
    **Returns**:
    - Summary object with collection statistics
    """
    filters = RentTrackerFilter(
        month=month,
        year=year,
        property_id=property_id,
        status=None,  # Summary doesn't filter by status
        include_vacant=False  # Summary doesn't include vacant units by default
    )
    
    return await RentTrackerService.get_rent_tracker_summary(
        session=session,
        current_user=current_user,
        filters=filters
    )