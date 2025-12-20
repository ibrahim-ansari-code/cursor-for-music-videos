import logging

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import col

from Backend.models.maintenance import MaintenanceRequest
from Backend.models.property import Property
from Backend.models.user import User
from Backend.models.enums import UserType

logger = logging.getLogger(__name__)


async def validate_file_content(upload_file: UploadFile) -> bool:
    """
    Validates uploaded file content by signature (JPEG, PNG, PDF).
    """
    # Read a larger header to accommodate common signatures and segments
    await upload_file.seek(0)
    header = await upload_file.read(32)
    await upload_file.seek(0)

    if not header:
        return False

    # PNG: 8-byte fixed signature
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return True

    # PDF: starts with %PDF-
    if header.startswith(b"%PDF-"):
        return True

    # JPEG: starts with SOI 0xFFD8 and commonly followed by 0xFF
    # Validate SOI and not just naive prefix
    if len(header) >= 3 and header[0:2] == b"\xFF\xD8" and header[2] == 0xFF:
        return True

    return False


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
    
    size = 0
    chunk_size = 8192  # 8 KB chunks
    
    while True:
        chunk = await upload_file.read(chunk_size)
        if not chunk:
            break
        size += len(chunk)
        
        if size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum allowed size is {max_size_bytes // (1024 * 1024)} MB."
            )
    
    await upload_file.seek(0)
    return size


async def check_permission(request: MaintenanceRequest, user: User, session: AsyncSession) -> None:
    """
    Verifies that the user has permission to access or modify a maintenance request.
    
    Raises an HTTP 403 error if the user is not an admin and does not own the property associated with the request.
    Raises HTTP 404 if the property is not found, or HTTP 500 if the property relationship cannot be loaded.
    """
    logger.info(f"Checking permissions for user {user.id} on request {request.id}")
    if user.is_admin:
        logger.info(f"User {user.id} is an admin, permission granted.")
        return

    prop = getattr(request, "property", None)

    if prop is None:
        logger.info(f"Property not loaded for request {request.id}, fetching from database.")
        try:
            result = await session.execute(
                select(Property)
                .where(col(Property.id) == request.property_id)
            )
            prop = result.scalar_one_or_none()

            if prop is None:
                logger.error(f"Property not found for maintenance request {request.id}")
                raise HTTPException(
                    status_code=404,
                    detail="Property not found for this maintenance request."
                )

            setattr(request, "property", prop)
            logger.info(f"Property {prop.id} loaded for request {request.id}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to load property relationship for request {request.id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load property relationship: {str(e)}"
            )

    if hasattr(prop, "user_id") and prop.user_id == user.id:
        logger.info(f"User {user.id} owns property {prop.id}, permission granted.")
        return

    if user.user_type == UserType.TENANT and request.user_id == user.id:
        logger.info(f"User {user.id} is a tenant and created the request, permission granted.")
        return
    
    logger.warning(f"User {user.id} does not have permission to access request {request.id}")
    raise HTTPException(
        status_code=403,
        detail="You do not have permission to access this maintenance request."
    )
