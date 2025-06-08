import logging
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import col

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.enums import MaintenancePriority, MaintenanceStatus, UserType
from Backend.models.maintenance import MaintenanceRequest
from Backend.models.property import Property, PropertyUnit
from Backend.models.user import User
from Backend.utils.azure_blob import upload_maintenance_photo_to_blob

logger = logging.getLogger(__name__)


# === Helper Functions ===

async def validate_file_content(upload_file: UploadFile) -> bool:
    """
    Checks whether the uploaded file's content matches allowed file types (JPEG, PNG, or PDF) by inspecting its magic bytes.
    
    Args:
        upload_file: The file to validate.
    
    Returns:
        True if the file's signature matches an allowed type; otherwise, False.
    """
    # Magic bytes for supported file types (now as a tuple of byte signatures)
    magic_bytes = (
        b'\xFF\xD8\xFF',  # JPEG
        b'\x89PNG\r\n\x1a\n',  # PNG
        b'%PDF-',  # PDF
    )
    # Read the first 16 bytes to check magic bytes
    await upload_file.seek(0)
    header = await upload_file.read(16)
    await upload_file.seek(0)  # Reset position
    # Check if file starts with any of the allowed magic bytes
    return any(header.startswith(magic) for magic in magic_bytes)


async def validate_file_size(upload_file: UploadFile, max_size_bytes: int) -> int:
    """
    Asynchronously validates that an uploaded file does not exceed a specified size limit.
    
    Reads the file in chunks to efficiently calculate its size. Raises an HTTP 413 error if the file exceeds the maximum allowed size.
    
    Args:
        upload_file: The file to validate.
        max_size_bytes: The maximum allowed file size in bytes.
    
    Returns:
        The actual size of the file in bytes.
    """
    await upload_file.seek(0)
    
    # Read in chunks to avoid loading the entire file into memory
    size = 0
    chunk_size = 8192  # 8 KB chunks
    
    while True:
        chunk = await upload_file.read(chunk_size)
        if not chunk:
            break
        size += len(chunk)
        
        # If we've exceeded the max size, stop reading and reject
        if size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum allowed size is {max_size_bytes // (1024 * 1024)} MB."
            )
    
    # Reset file position for the actual upload
    await upload_file.seek(0)
    return size

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])

# === Pydantic Models ===


class MaintenanceRequestCreate(BaseModel):
    issue_title: str
    description: Optional[str] = None
    property_id: int
    unit_id: Optional[int] = None
    tenant_id: Optional[int] = None
    priority: MaintenancePriority
    scheduled_date: Optional[date] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    photos: Optional[List[str]] = None
    assigned_to: Optional[str] = None


class MaintenanceRequestUpdate(BaseModel):
    issue_title: Optional[str] = None
    description: Optional[str] = None
    property_id: Optional[int] = None
    unit_id: Optional[int] = None
    tenant_id: Optional[int] = None
    priority: Optional[MaintenancePriority] = None
    status: Optional[MaintenanceStatus] = None
    scheduled_date: Optional[date] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    photos: Optional[List[str]] = None
    assigned_to: Optional[str] = None


class PropertyInfo(BaseModel):
    id: int
    name: str


class UnitInfo(BaseModel):
    id: int
    name: str


class TenantInfo(BaseModel):
    id: int
    first_name: str
    last_name: str


class MaintenanceRequestResponse(BaseModel):
    id: int
    issue_title: str
    description: Optional[str]
    property: Optional[PropertyInfo]
    unit: Optional[UnitInfo]
    tenant: Optional[TenantInfo]
    request_date: datetime
    priority: MaintenancePriority
    status: MaintenanceStatus
    scheduled_date: Optional[date]
    estimated_cost: Optional[float]
    actual_cost: Optional[float]
    photos: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[str]

    class Config:
        from_attributes = True


class MaintenanceSummaryResponse(BaseModel):
    total_requests: int
    pending: int
    in_progress: int
    completed: int
    scheduled: int
    cancelled: int

# === Helper: Permission Check ===


async def check_permission(request: MaintenanceRequest, user: User, session: AsyncSession) -> None:
    """
    Verifies that the user has permission to access or modify a maintenance request.
    
    Raises an HTTP 403 error if the user is not an admin and does not own the property associated with the request. Raises HTTP 404 if the property is not found, or HTTP 500 if the property relationship cannot be loaded.
    """
    # Only property owner or admin can access
    if user.is_admin:
        return

    prop = getattr(request, "property", None)

    # If property relationship is not loaded, try to load it
    if prop is None:
        try:
            # Load the property relationship
            result = await session.execute(
                select(Property)
                .where(col(Property.id) == request.property_id)
            )
            prop = result.scalar_one_or_none()

            if prop is None:
                raise HTTPException(
                    status_code=404,
                    detail="Property not found for this maintenance request."
                )

            # Set the property on the request object for future use
            setattr(request, "property", prop)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load property relationship: {str(e)}"
            )

    # Now check if the user owns the property
    if hasattr(prop, "user_id") and prop.user_id == user.id:
        return
    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this maintenance request."
        )

# === Endpoints ===


@router.get("/requests", response_model=List[MaintenanceRequestResponse])
async def list_maintenance_requests(
    req_status: Optional[MaintenanceStatus] = Query(
        None, description="Filter by status"),
    priority: Optional[MaintenancePriority] = Query(
        None, description="Filter by priority"),
    property_id: Optional[int] = Query(
        None, description="Filter by property ID"),
    unit_id: Optional[int] = Query(None, description="Filter by unit ID"),
    tenant_id: Optional[int] = Query(None, description="Filter by tenant ID"),
    assigned_to: Optional[str] = Query(
        None, description="Filter by assigned to"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return (max 100)"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a list of maintenance requests with optional filtering and pagination.
    
    Filters maintenance requests by status, priority, property, unit, tenant, or assigned user. Non-admin users only see requests for properties they own. Supports pagination via limit and offset.
    
    Returns:
        A list of maintenance requests matching the specified filters.
    """
    logger.info(
        "User %s listing maintenance requests with filters: status=%s, priority=%s, property_id=%s, unit_id=%s, tenant_id=%s, assigned_to=%s",
        current_user.id, req_status, priority, property_id, unit_id, tenant_id, assigned_to
    )

    query = select(MaintenanceRequest).options(
        selectinload(getattr(MaintenanceRequest, "property")),
        selectinload(getattr(MaintenanceRequest, "unit")),
        selectinload(getattr(MaintenanceRequest, "tenant"))
    )

    # Restrict to properties owned by the current user unless admin
    if not current_user.is_admin:
        query = query.join(Property, col(
            MaintenanceRequest.property_id) == col(Property.id))
        query = query.where(col(Property.user_id) == current_user.id)

    if req_status is not None:
        query = query.where(col(MaintenanceRequest.status) == req_status)
    if priority is not None:
        query = query.where(col(MaintenanceRequest.priority) == priority)
    if property_id is not None:
        query = query.where(col(MaintenanceRequest.property_id) == property_id)
    if unit_id is not None:
        query = query.where(col(MaintenanceRequest.unit_id) == unit_id)
    if tenant_id is not None:
        query = query.where(col(MaintenanceRequest.tenant_id) == tenant_id)
    if assigned_to is not None:
        query = query.where(col(MaintenanceRequest.assigned_to) == assigned_to)

    # Add pagination
    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    requests = result.unique().scalars().all()
    return requests


@router.post("/requests", response_model=MaintenanceRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_maintenance_request(
    data: MaintenanceRequestCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new maintenance request for a property.
    
    Validates that the current user has permission to create a request for the specified property unless the user is an admin. Associates the request with the current user, sets its status to pending, and saves it to the database. Returns the created maintenance request with related property, unit, and tenant information loaded.
    """
    logger.info(
        f"User {current_user.id} creating maintenance request for property {data.property_id}")

    # Check property ownership unless admin
    if not current_user.is_admin:
        result = await session.execute(
            select(Property).where(col(Property.id) == data.property_id)
        )
        prop = result.scalar_one_or_none()
        if not prop or prop.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to create a maintenance request for this property."
            )

    # Validate unit_id if provided
    if data.unit_id is not None:
        unit_result = await session.execute(
            select(PropertyUnit).where(col(PropertyUnit.id) == data.unit_id)
        )
        unit = unit_result.scalar_one_or_none()
        if not unit:
            raise HTTPException(
                status_code=404,
                detail="The specified unit does not exist."
            )
        if unit.property_id != data.property_id:
            raise HTTPException(
                status_code=400,
                detail="The specified unit does not belong to the specified property."
            )
        # If not admin, check landlord owns the property
        if not current_user.is_admin:
            prop_result = await session.execute(
                select(Property).where(col(Property.id) == unit.property_id)
            )
            prop = prop_result.scalar_one_or_none()
            if not prop or prop.user_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to create a maintenance request for this unit/property."
                )

    # Validate tenant_id if provided
    if data.tenant_id is not None:
        tenant_result = await session.execute(
            select(User).where(col(User.id) == data.tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(
                status_code=404,
                detail="The specified tenant does not exist."
            )
        # If unit_id is provided, check tenant is associated with the unit (if such a relationship exists)
        # Otherwise, check tenant is associated with the property (if such a relationship exists)
        # This logic may need to be adapted to your data model
        if data.unit_id is not None:
            # Check tenant is associated with the unit (if your model supports this)
            # For now, just a placeholder check; adapt as needed
            pass
        else:
            # Check tenant is associated with the property (if your model supports this)
            pass

    # Manually construct the MaintenanceRequest object
    db_request = MaintenanceRequest(
        issue_title=data.issue_title,
        description=data.description,
        property_id=data.property_id,
        unit_id=data.unit_id,
        tenant_id=data.tenant_id,
        user_id=current_user.id,  # Associate with the current user
        priority=data.priority,
        status=MaintenanceStatus.PENDING,
        request_date=datetime.utcnow(),
        scheduled_date=data.scheduled_date,
        estimated_cost=data.estimated_cost,
        actual_cost=data.actual_cost,
        photos=data.photos,
        assigned_to=data.assigned_to
    )

    session.add(db_request)
    await session.commit()
    await session.refresh(db_request)

    # Eagerly load relationships before returning
    result = await session.execute(
        select(MaintenanceRequest)
        .options(
            selectinload(getattr(MaintenanceRequest, "property")),
            selectinload(getattr(MaintenanceRequest, "unit")),
            selectinload(getattr(MaintenanceRequest, "tenant"))
        )
        .where(col(MaintenanceRequest.id) == db_request.id)
    )
    return result.unique().scalar_one()


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
    result = await session.execute(
        select(MaintenanceRequest)
        .options(selectinload(getattr(MaintenanceRequest, "property")))
        .where(col(MaintenanceRequest.id) == request_id)
    )
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=404, detail="Maintenance request not found")

    await check_permission(req, current_user, session)
    return req


@router.put("/requests/{request_id}", response_model=MaintenanceRequestResponse)
async def update_maintenance_request(
    request_id: int,
    data: MaintenanceRequestUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Updates an existing maintenance request with new data, validating property and unit ownership.
    
    Checks user permissions and ensures that any changes to property or unit associations are authorized and consistent. Validates that the specified unit belongs to the specified property when either is updated. Commits changes and returns the updated maintenance request with related entities loaded.
    
    Args:
        request_id: The ID of the maintenance request to update.
        data: The fields to update in the maintenance request.
    
    Returns:
        The updated maintenance request with related property, unit, and tenant information.
    """
    result = await session.execute(
        select(MaintenanceRequest)
        .options(selectinload(getattr(MaintenanceRequest, "property")))
        .where(col(MaintenanceRequest.id) == request_id)
    )
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=404, detail="Maintenance request not found")

    await check_permission(req, current_user, session)

    update_data = data.dict(exclude_unset=True)

    # Check if property_id or unit_id are being changed, if so verify ownership
    if ('property_id' in update_data and update_data['property_id'] != req.property_id) or \
       ('unit_id' in update_data and update_data['unit_id'] != req.unit_id):

        new_property_id = update_data.get('property_id', req.property_id)
        new_unit_id = update_data.get('unit_id', req.unit_id)
        
        # Variables to store the fetched objects
        new_property = None
        new_unit = None
        unit_to_check = None

        # If property_id is being updated, check if user owns the new property
        if 'property_id' in update_data and not current_user.is_admin:
            prop_result = await session.execute(
                select(Property).where(col(Property.id) == new_property_id)
            )
            new_property = prop_result.scalar_one_or_none()

            if not new_property or new_property.user_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to assign this maintenance request to the specified property."
                )

        # If unit_id is being updated, check if user owns the property of the new unit
        if 'unit_id' in update_data and update_data['unit_id'] != req.unit_id:
            # Skip ownership check for admins
            if not current_user.is_admin:
                unit_result = await session.execute(
                    select(PropertyUnit)
                    .where(col(PropertyUnit.id) == new_unit_id)
                )
                new_unit = unit_result.scalar_one_or_none()

                if not new_unit:
                    raise HTTPException(
                        status_code=404,
                        detail="The specified unit does not exist."
                    )

                # Now fetch the property to check ownership
                prop_result = await session.execute(
                    select(Property).where(
                        col(Property.id) == new_unit.property_id)
                )
                prop = prop_result.scalar_one_or_none()

                if not prop or prop.user_id != current_user.id:
                    raise HTTPException(
                        status_code=403,
                        detail="You do not have permission to assign this maintenance request to a unit from another landlord's property."
                    )

        # If we are only changing the property_id, we need to ensure the existing unit belongs to the new property
        if 'property_id' in update_data and 'unit_id' not in update_data and req.unit_id is not None:
            unit_result = await session.execute(
                select(PropertyUnit).where(col(PropertyUnit.id) == req.unit_id)
            )
            unit_to_check = unit_result.scalar_one_or_none()
        
        # If unit_id is being updated, new_unit will be set. Otherwise, use the existing unit.
        if new_unit:
            unit_to_check = new_unit

        # Validate that the unit belongs to the property
        if unit_to_check and unit_to_check.property_id != new_property_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The specified unit does not belong to the specified property."
            )

    # Apply the updates
    for key, value in update_data.items():
        setattr(req, key, value)

    session.add(req)
    await session.commit()
    await session.refresh(req)

    # Eagerly load relationships before returning
    result = await session.execute(
        select(MaintenanceRequest)
        .options(
            selectinload(getattr(MaintenanceRequest, "property")),
            selectinload(getattr(MaintenanceRequest, "unit")),
            selectinload(getattr(MaintenanceRequest, "tenant"))
        )
        .where(col(MaintenanceRequest.id) == req.id)
    )
    return result.unique().scalar_one()


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_maintenance_request(
    request_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a maintenance request by its ID after verifying user permissions.
    
    Raises a 404 error if the maintenance request does not exist or a 403 error if the user lacks permission to delete it.
    """
    result = await session.execute(
        select(MaintenanceRequest)
        .options(selectinload(getattr(MaintenanceRequest, "property")))
        .where(col(MaintenanceRequest.id) == request_id)
    )
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=404, detail="Maintenance request not found")

    await check_permission(req, current_user, session)
    await session.delete(req)
    await session.commit()
    logger.info(
        f"User {current_user.id} deleted maintenance request {request_id}")
    return None


@router.get("/summary", response_model=MaintenanceSummaryResponse)
async def get_maintenance_summary(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Returns a summary of maintenance requests grouped by status for the current user.
    
    If the user is not an admin, only requests for properties owned by the user are included. The summary contains counts for each status and the total number of requests.
     
    Returns:
        A dictionary with counts of maintenance requests by status and a total count.
    """
    logger.info(f"User {current_user.id} requesting maintenance summary")

    query = select(
        col(MaintenanceRequest.status),
        func.count(col(MaintenanceRequest.id))
    ).group_by(col(MaintenanceRequest.status))
    
    # Restrict to properties owned by the current user unless admin
    if not current_user.is_admin:
        query = query.join(Property, col(
            MaintenanceRequest.property_id) == col(Property.id))
        query = query.where(col(Property.user_id) == current_user.id)
    
    result = await session.execute(query)

    summary = {status.value.lower().replace(
        " ", "_"): 0 for status in MaintenanceStatus}
    summary["total_requests"] = 0

    for status_value, count in result:
        status_key = status_value.value.lower().replace(" ", "_")
        if status_key in summary:
            summary[status_key] = count
        summary["total_requests"] += count

    return summary


@router.post("/upload-photo", status_code=201)
async def upload_maintenance_photo(
    upload_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a maintenance photo (JPEG, PNG, or PDF) to Azure Blob Storage and returns its public URL.
    
    Only users with landlord or admin roles are authorized to upload. Validates the file type by inspecting its magic bytes and enforces a maximum file size of 10 MB. Returns a dictionary containing the public URL of the uploaded photo.
    """
    if current_user.user_type not in [UserType.LANDLORD, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload maintenance photos."
        )

    # Validate file content by checking magic bytes (more secure than relying on MIME type)
    if not await validate_file_content(upload_file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only PDF, JPG, and PNG files are allowed."
        )

    # Validate file size - 10 MB limit
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB in bytes
    await validate_file_size(upload_file, MAX_SIZE)

    try:
        url = await upload_maintenance_photo_to_blob(upload_file, current_user.id)
        return {"photo_url": url}
    except Exception as e:
        logger.exception("Failed to upload maintenance photo to blob storage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload maintenance photo: {str(e)}"
        )
