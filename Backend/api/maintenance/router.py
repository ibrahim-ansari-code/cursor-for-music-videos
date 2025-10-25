import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.enums import MaintenancePriority, MaintenanceStatus
from Backend.models.user import User

from .schemas import (
    MaintenancePhotoUploadResponse,
    MaintenanceRequestCreate,
    MaintenanceRequestResponse,
    MaintenanceRequestUpdate,
    MaintenanceSummaryResponse,
    SecurePhotoUrlResponse,
)
from .service import MaintenanceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


@router.get("/requests", response_model=list[MaintenanceRequestResponse])
async def list_maintenance_requests(
    req_status: Annotated[
        MaintenanceStatus | None, Query(description="Filter by status")
    ] = None,
    priority: Annotated[
        MaintenancePriority | None, Query(description="Filter by priority")
    ] = None,
    property_id: Annotated[
        int | None, Query(description="Filter by property ID")
    ] = None,
    unit_id: Annotated[
        int | None, Query(description="Filter by unit ID")
    ] = None,
    tenant_id: Annotated[
        int | None, Query(description="Filter by tenant ID")
    ] = None,
    assigned_to: Annotated[
        str | None, Query(description="Filter by assigned to")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Number of results to return (max 100)")
    ] = 50,
    offset: Annotated[
        int, Query(ge=0, description="Number of results to skip")
    ] = 0,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[MaintenanceRequestResponse]:
    """
    Retrieves a list of maintenance requests with optional filtering and pagination.
    
    Filters maintenance requests by status, priority, property, unit, tenant, or assigned user.
    Non-admin users only see requests for properties they own. Supports pagination via limit and offset.
    
    Returns:
        A list of maintenance requests matching the specified filters.
    """
    try:
        return await MaintenanceService.list_maintenance_requests(
            current_user=current_user,
            session=session,
            req_status=req_status,
            priority=priority,
            property_id=property_id,
            unit_id=unit_id,
            tenant_id=tenant_id,
            assigned_to=assigned_to,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.exception("Error listing maintenance requests")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list maintenance requests: {str(e)}"
        )


@router.post("/requests", response_model=MaintenanceRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_maintenance_request(
    data: MaintenanceRequestCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new maintenance request for a property.
    
    Validates that the current user has permission to create a request for the specified property
    unless the user is an admin. Associates the request with the current user, sets its status to pending,
    and saves it to the database. Returns the created maintenance request with related property, unit,
    and tenant information loaded.
    """
    try:
        return await MaintenanceService.create_maintenance_request(
            data=data,
            current_user=current_user,
            session=session
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error creating maintenance request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create maintenance request: {str(e)}"
        )


@router.get("/requests/{request_id}", response_model=MaintenanceRequestResponse)
async def get_maintenance_request(
    request_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a maintenance request by its ID after verifying user permissions.
    
    Raises:
        HTTPException: If the maintenance request is not found or the user lacks permission.
    
    Returns:
        The maintenance request with related property information loaded.
    """
    try:
        return await MaintenanceService.get_maintenance_request(
            request_id=request_id,
            current_user=current_user,
            session=session
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error retrieving maintenance request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve maintenance request: {str(e)}"
        )


@router.put("/requests/{request_id}", response_model=MaintenanceRequestResponse)
async def update_maintenance_request(
    request_id: int,
    data: MaintenanceRequestUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Updates an existing maintenance request with new data, validating property and unit ownership.
    
    Checks user permissions and ensures that any changes to property or unit associations are authorized
    and consistent. Validates that the specified unit belongs to the specified property when either is updated.
    Commits changes and returns the updated maintenance request with related entities loaded.
    
    Args:
        request_id: The ID of the maintenance request to update.
        data: The fields to update in the maintenance request.
    
    Returns:
        The updated maintenance request with related property, unit, and tenant information.
    """
    try:
        return await MaintenanceService.update_maintenance_request(
            request_id=request_id,
            data=data,
            current_user=current_user,
            session=session
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating maintenance request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update maintenance request: {str(e)}"
        )


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_maintenance_request(
    request_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a maintenance request by its ID after verifying user permissions.
    
    Raises a 404 error if the maintenance request does not exist or a 403 error if the user lacks
    permission to delete it.
    """
    try:
        await MaintenanceService.delete_maintenance_request(
            request_id=request_id,
            current_user=current_user,
            session=session
        )
        return
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting maintenance request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete maintenance request: {str(e)}"
        )


@router.get("/summary", response_model=MaintenanceSummaryResponse)
async def get_maintenance_summary(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Returns a summary of maintenance requests grouped by status for the current user.
    
    If the user is not an admin, only requests for properties owned by the user are included.
    The summary contains counts for each status and the total number of requests.
     
    Returns:
        A dictionary with counts of maintenance requests by status and a total count.
    """
    try:
        return await MaintenanceService.get_maintenance_summary(
            current_user=current_user,
            session=session
        )
    except Exception as e:
        logger.exception("Error getting maintenance summary")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get maintenance summary: {str(e)}"
        )


@router.post("/upload-photo", response_model=MaintenancePhotoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_maintenance_photo(
    upload_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a maintenance photo (JPEG, PNG, or PDF) to Azure Blob Storage and returns its public URL.
    
    Only users with landlord or admin roles are authorized to upload. Validates the file type by inspecting
    its magic bytes and enforces a maximum file size of 10 MB. Returns a dictionary containing the public
    URL of the uploaded photo.
    """
    try:
        return await MaintenanceService.upload_maintenance_photo(
            upload_file=upload_file,
            current_user=current_user
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error uploading maintenance photo")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload maintenance photo: {str(e)}"
        )


@router.post("/photos/secure-url", response_model=SecurePhotoUrlResponse)
async def get_photo_secure_url(
    request: Request,
    current_user: User = Depends(get_current_user),
    photo_url: str = Query(..., description="The original Azure Blob URL of the photo")
):
    """
    Generate a time-limited, authenticated URL for secure photo access.
    
    Security Features:
        - Requires JWT authentication
        - Generates 1-hour expiring SAS token
        - Read-only access (no write/delete)
        - HTTPS enforced
        - Audit logging enabled
    
    Args:
        photo_url: The original Azure Blob URL of the photo
        
    Returns:
        SecurePhotoUrlResponse containing:
            - secure_url: Azure Blob URL with SAS token appended
            - expires_at: ISO 8601 UTC datetime when URL expires
            - expires_in_seconds: Seconds until expiration (3600 for 1 hour)
    """
    try:
        # NOTE: We don't restrict by IP for photos because they're loaded by the browser
        # The browser's IP won't match the backend server IP, causing 403 errors
        # For document downloads, IP restriction could be useful as backend proxies the download
        
        # Generate secure URL with SAS token (no IP restriction)
        secure_url_data = await MaintenanceService.generate_photo_secure_url(
            photo_url=photo_url,
            current_user=current_user,
            client_ip=None  # No IP restriction for browser-loaded images
        )
        
        return secure_url_data
        
    except HTTPException:
        raise
    except ValueError as ve:
        error_msg = str(ve)
        
        if "not found in storage" in error_msg.lower():
            logger.error(f"Orphaned photo record detected: {photo_url}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The photo no longer exists in storage. It may have been deleted."
            )
        else:
            logger.error(f"Validation error generating SAS token for photo: {ve}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid photo URL: {error_msg}"
            )
    except Exception as e:
        logger.exception("Error generating secure URL for photo")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate secure preview URL. Please try again."
        )