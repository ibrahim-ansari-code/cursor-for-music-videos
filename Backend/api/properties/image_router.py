"""
Router for property image endpoints including SAS token generation.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.api.properties.service import PropertyService
from Backend.api.properties.image_service import PropertyImageService, FileValidationError
from Backend.api.properties.schemas import PropertyImageResponse
from Backend.database import get_session
from Backend.models.user import User
from Backend.utils.azure_blob import upload_property_image_to_blob
from Backend.utils.file_validation import validate_file_from_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/properties", tags=["Property Images"])


# Removed SAS token models - using simplified direct upload approach


class ImageReorderRequest(BaseModel):
    """Request model for reordering images."""
    image_id: int
    display_order: int


class SecureImageUrlResponse(BaseModel):
    """Response schema for secure, time-limited image URLs"""
    secure_url: str
    expires_at: str  # ISO 8601 datetime string
    expires_in_seconds: int


# Removed SAS token endpoints - using simplified direct upload approach


@router.get("/{property_id}/images", response_model=List[PropertyImageResponse])
async def get_property_images(
    property_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> List[PropertyImageResponse]:
    """Get all images for a property."""
    # Verify user owns the property
    property = await PropertyService.get_property(property_id, current_user, db)
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found or you don't have access"
        )
    
    images = await PropertyImageService.get_property_images(db, property_id)
    
    return [PropertyImageResponse.model_validate(img) for img in images]


@router.delete("/{property_id}/images/{image_id}")
async def delete_property_image(
    property_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    """Delete a property image."""
    # Verify user owns the property
    property = await PropertyService.get_property(property_id, current_user, db)
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found or you don't have access"
        )
    
    try:
        deleted = await PropertyImageService.delete_property_image(db, image_id, str(current_user.id))
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )
        
        return {"message": "Image deleted successfully"}
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error("Property image deletion failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete image"
        )


@router.put("/{property_id}/images/reorder", response_model=List[PropertyImageResponse])
async def reorder_property_images(
    property_id: int,
    image_orders: List[ImageReorderRequest],
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> List[PropertyImageResponse]:
    """Reorder property images."""
    # Verify user owns the property
    property = await PropertyService.get_property(property_id, current_user, db)
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found or you don't have access"
        )
    
    # Prepare reorder data
    reorder_data = [
        {"image_id": item.image_id, "display_order": item.display_order}
        for item in image_orders
    ]
    
    try:
        images = await PropertyImageService.reorder_images(db, property_id, reorder_data)
        return [PropertyImageResponse.model_validate(img) for img in images]
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error("Property image reorder failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder images"
        )


@router.put("/{property_id}/images/{image_id}/primary", response_model=PropertyImageResponse)
async def set_primary_image(
    property_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> PropertyImageResponse:
    """Set an image as the primary image for a property."""
    # Verify user owns the property
    property = await PropertyService.get_property(property_id, current_user, db)
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found or you don't have access"
        )
    
    try:
        image = await PropertyImageService.set_primary_image(db, property_id, image_id)
        return PropertyImageResponse.model_validate(image)
        
    except ValueError as e:
        # Handle specific ValueError for image not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error("Set primary image failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set primary image"
        )


# Removed batch SAS token endpoint - using simplified direct upload approach


@router.post("/{property_id}/images/upload", response_model=PropertyImageResponse)
async def upload_property_image_direct(
    property_id: int,
    file: UploadFile = File(...),
    is_primary: bool = Form(False),
    display_order: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> PropertyImageResponse:
    """
    Direct upload of property image (simplified approach that matches expense receipts).
    
    This endpoint:
    1. Verifies the user owns the property
    2. Validates and uploads the file directly to Azure Blob Storage
    3. Saves the image record to the database
    4. Returns the created image record
    
    This is a simpler alternative to the SAS token approach and follows
    the same pattern used successfully for expense receipts.
    """
    # Verify user owns the property
    property = await PropertyService.get_property(property_id, current_user, db)
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found or you don't have access"
        )
    
    # Check image limits before upload
    try:
        await PropertyImageService.validate_property_image_limits(db, property_id)
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    
    try:
        # Validate the file (same security checks as expense receipts)
        _, validated_mime_type = await validate_file_from_upload(file, file.content_type)
        logger.info("Property image file validated: declared=%s, detected=%s",
                    file.content_type, validated_mime_type)

        # Upload directly to Azure Blob Storage (same pattern as expense receipts)
        image_url = await upload_property_image_to_blob(file, current_user.id)
        logger.info("Property image uploaded successfully: %s", image_url)

        # Save image record to database
        image = await PropertyImageService.save_property_image_record(
            db=db,
            property_id=property_id,
            image_url=image_url,
            is_primary=is_primary,
            display_order=display_order
        )
        
        return PropertyImageResponse.model_validate(image)
        
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service temporarily unavailable"
        )
    except Exception as e:
        logger.error("Property image upload failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image"
        )


@router.post("/images/secure-url", response_model=SecureImageUrlResponse)
async def get_image_secure_url(
    request: Request,
    current_user: User = Depends(get_current_user),
    image_url: str = Query(..., description="The original Azure Blob URL of the image")
):
    """
    Generate a time-limited, authenticated URL for secure property image access.
    
    For private Azure containers, images require SAS tokens to be accessed.
    This endpoint generates a 1-hour expiring SAS token for secure image viewing.
    """
    try:
        return await PropertyImageService.generate_image_secure_url(
            image_url=image_url,
            current_user=current_user
        )
    except HTTPException:
        raise
    except ValueError as ve:
        error_msg = str(ve)
        if "not found in storage" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The image file no longer exists in storage."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image URL: {error_msg}"
        )
    except Exception as e:
        logger.exception("Error generating secure URL for property image")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate secure preview URL."
        )