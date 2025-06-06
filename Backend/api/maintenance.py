import logging
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID as PythonUUID

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
from Backend.models.property import Property
from Backend.models.user import User
from Backend.utils.azure_blob import upload_maintenance_photo_to_blob

logger = logging.getLogger(__name__)

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


async def check_permission(request: MaintenanceRequest, user: User, session: AsyncSession):
    """Check if the user has permission to access/modify the maintenance request."""
    # Only property owner or admin can access
    if user.is_admin:
        return True

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
        return True
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
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"User {current_user.id} listing maintenance requests with filters: status={req_status}, priority={priority}, property_id={property_id}, unit_id={unit_id}, tenant_id={tenant_id}, assigned_to={assigned_to}")

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

    result = await session.execute(query)
    requests = result.unique().scalars().all()
    return requests


@router.post("/requests", response_model=MaintenanceRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_maintenance_request(
    data: MaintenanceRequestCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
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

        # If property_id is being updated, check if user owns the new property
        if 'property_id' in update_data:
            new_property_id = update_data['property_id']

            # Skip ownership check for admins
            if not current_user.is_admin:
                prop_result = await session.execute(
                    select(Property).where(col(Property.id) == new_property_id)
                )
                prop = prop_result.scalar_one_or_none()

                if not prop or prop.user_id != current_user.id:
                    raise HTTPException(
                        status_code=403,
                        detail="You do not have permission to assign this maintenance request to the specified property."
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
    Get a summary of maintenance requests by status.
    """
    logger.info(f"User {current_user.id} requesting maintenance summary")

    query = select(
        col(MaintenanceRequest.status),
        func.count(col(MaintenanceRequest.id))
    ).group_by(col(MaintenanceRequest.status))
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
    Upload a maintenance photo (image or PDF) to Azure Blob Storage and return its public URL.
    Only landlords and admins are allowed.
    """
    if current_user.user_type not in [UserType.LANDLORD, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload maintenance photos."
        )

    allowed_content_types = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/jpg"
    ]
    if upload_file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {upload_file.content_type}. Allowed types are PDF, JPG, PNG."
        )

    # Check file size - 10 MB limit
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB in bytes

    # First check Content-Length header if available
    content_length = upload_file.size if hasattr(upload_file, 'size') else None
    if content_length and content_length > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is 10 MB."
        )

    # If no reliable Content-Length, check by reading file
    if not content_length:
        # Reset file position to start
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
            if size > MAX_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum allowed size is 10 MB."
                )

        # Reset file position for the actual upload
        await upload_file.seek(0)

    try:
        url = await upload_maintenance_photo_to_blob(upload_file, current_user.id)
        return {"photo_url": url}
    except Exception as e:
        logger.exception("Failed to upload maintenance photo to blob storage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload maintenance photo: {str(e)}"
        )
