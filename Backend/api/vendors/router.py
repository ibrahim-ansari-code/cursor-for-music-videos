"""
Vendor Contact Router

RESTful API endpoints for vendor contact management.
"""
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.user import User

from .schemas import (
    VendorContactCreate,
    VendorContactUpdate,
    VendorContactResponse,
    VendorContactListResponse,
    VendorContactBulkDelete,
)
from .service import VendorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vendors", tags=["Vendors"])


def _merge_vendor_response(vendor, user_vendor) -> dict:
    """Merge vendor and user_vendor data into a single response dict"""
    return {
        # Vendor data
        "id": vendor.id,
        "company_name": vendor.company_name,
        "contact_person": vendor.contact_person,
        "trade_category": vendor.trade_category,
        "phone": vendor.phone,
        "email": vendor.email,
        "created_at": vendor.created_at,
        "updated_at": vendor.updated_at,
        "is_verified": vendor.is_verified,
        "average_rating": vendor.average_rating,
        "total_reviews": vendor.total_reviews,
        # UserVendor data
        "user_id": user_vendor.user_id,
        "notes": user_vendor.notes,
        "is_active": user_vendor.is_active,
        "is_favorite": user_vendor.is_favorite,
        "personal_rating": user_vendor.personal_rating,
    }


@router.post("", response_model=VendorContactResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    data: VendorContactCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> VendorContactResponse:
    """
    Create a new vendor contact for the current user.
    
    Finds or creates vendor in central table, then associates with user.
    Deduplicates vendors by phone number automatically.
    """
    try:
        vendor, user_vendor = await VendorService.create_vendor(
            data=data,
            current_user=current_user,
            session=session
        )
        return VendorContactResponse.model_validate(_merge_vendor_response(vendor, user_vendor))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creating vendor contact")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vendor contact: {str(e)}"
        )


@router.get("", response_model=VendorContactListResponse)
async def list_vendors(
    trade_category: Annotated[
        Optional[str], Query(description="Filter by trade category")
    ] = None,
    is_active: Annotated[
        Optional[bool], Query(description="Filter by active status")
    ] = None,
    search: Annotated[
        Optional[str], Query(description="Search in company name and contact person")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Number of results to return (max 100)")
    ] = 50,
    offset: Annotated[
        int, Query(ge=0, description="Number of results to skip")
    ] = 0,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> VendorContactListResponse:
    """
    List vendor contacts for the current user with optional filtering and pagination.
    
    Returns vendors from the central table with user-specific association data.
    """
    try:
        vendor_tuples, total = await VendorService.list_vendors(
            current_user=current_user,
            session=session,
            trade_category=trade_category,
            is_active=is_active,
            search=search,
            limit=limit,
            offset=offset
        )
        
        vendor_responses = [
            VendorContactResponse.model_validate(_merge_vendor_response(vendor, user_vendor))
            for vendor, user_vendor in vendor_tuples
        ]
        
        return VendorContactListResponse(
            vendors=vendor_responses,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.exception("Error listing vendor contacts")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list vendor contacts: {str(e)}"
        )


@router.get("/trade-categories", response_model=list[str])
async def get_trade_categories(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[str]:
    """
    Get list of unique trade categories used by the current user.
    
    Returns a list of trade categories from the user's existing vendor contacts,
    useful for populating dropdowns and filters.
    """
    try:
        categories = await VendorService.get_trade_categories(
            current_user=current_user,
            session=session
        )
        return categories
    except Exception as e:
        logger.exception("Error getting trade categories")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trade categories: {str(e)}"
        )


@router.get("/{vendor_id}", response_model=VendorContactResponse)
async def get_vendor(
    vendor_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> VendorContactResponse:
    """
    Get a specific vendor by ID with user's association data.
    
    Returns 404 if the vendor isn't in user's contacts.
    """
    try:
        vendor, user_vendor = await VendorService.get_vendor(
            vendor_id=vendor_id,
            current_user=current_user,
            session=session
        )
        return VendorContactResponse.model_validate(_merge_vendor_response(vendor, user_vendor))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving vendor contact {vendor_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve vendor contact: {str(e)}"
        )


@router.put("/{vendor_id}", response_model=VendorContactResponse)
async def update_vendor(
    vendor_id: int,
    data: VendorContactUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> VendorContactResponse:
    """
    Update user's association with a vendor (notes, favorites, rating, etc.).
    
    NOTE: This updates user-specific fields only. Central vendor data cannot be updated.
    """
    try:
        vendor, user_vendor = await VendorService.update_vendor(
            vendor_id=vendor_id,
            data=data,
            current_user=current_user,
            session=session
        )
        return VendorContactResponse.model_validate(_merge_vendor_response(vendor, user_vendor))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating vendor contact {vendor_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update vendor contact: {str(e)}"
        )


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Remove vendor from user's contacts.
    
    NOTE: This removes the association, not the vendor itself.
    The vendor remains available in the system for other users.
    """
    try:
        await VendorService.delete_vendor(
            vendor_id=vendor_id,
            current_user=current_user,
            session=session
        )
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting vendor contact {vendor_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete vendor contact: {str(e)}"
        )


@router.delete("/bulk", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_vendors(
    data: VendorContactBulkDelete,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete multiple vendor contacts at once.
    
    Only vendors belonging to the current user will be deleted.
    Returns 404 if no vendors found with the provided IDs.
    """
    try:
        count = await VendorService.bulk_delete_vendors(
            vendor_ids=data.vendor_ids,
            current_user=current_user,
            session=session
        )
        logger.info(f"Bulk deleted {count} vendor contacts")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error bulk deleting vendor contacts")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk delete vendor contacts: {str(e)}"
        )

