"""
Service for handling property image uploads with Azure Blob Storage.
Includes comprehensive file validation for security and data integrity.
"""
import logging
import uuid
import mimetypes
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path
from uuid import UUID

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col
from fastapi import HTTPException, status

from Backend.config import settings
from Backend.models.property import Property, PropertyImage
from Backend.models.user import User
from Backend.utils.azure_blob import blob_service_client, delete_blob_by_url, generate_secure_document_url

logger = logging.getLogger(__name__)

PROPERTY_IMAGES_CONTAINER = "property-images"

# Security configurations
ALLOWED_MIME_TYPES = {
    'image/jpeg',
    'image/jpg', 
    'image/jfif',
    'image/png',
    'image/webp',
    'image/gif'
}

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.jfif', '.png', '.webp', '.gif'}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MIN_FILE_SIZE = 1024  # 1KB
MAX_IMAGES_PER_PROPERTY = 20
MAX_FILENAME_LENGTH = 255

# Dangerous file extensions to reject
DANGEROUS_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar', '.msi',
    '.dll', '.app', '.deb', '.pkg', '.dmg', '.iso', '.zip', '.rar', '.7z', '.tar',
    '.php', '.asp', '.jsp', '.py', '.rb', '.pl', '.sh', '.ps1'
}


class FileValidationError(Exception):
    """Custom exception for file validation errors."""
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class PropertyImageService:
    """Service for managing property images and SAS token generation."""

    @staticmethod
    def validate_file_upload(
        filename: str,
        content_type: str,
        file_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive file validation for security and data integrity.
        
        Args:
            filename: Original filename from client
            content_type: MIME type from client
            file_size: File size in bytes (if available)
            
        Returns:
            Dict containing validation results and cleaned data
            
        Raises:
            FileValidationError: If validation fails
        """
        # 1. Filename validation
        if not filename or not filename.strip():
            raise FileValidationError("Filename is required", "MISSING_FILENAME")
        
        filename = filename.strip()
        
        if len(filename) > MAX_FILENAME_LENGTH:
            raise FileValidationError(
                f"Filename too long. Maximum {MAX_FILENAME_LENGTH} characters allowed",
                "FILENAME_TOO_LONG"
            )
        
        # 2. Extension validation
        file_path = Path(filename.lower())
        file_extension = file_path.suffix.lower()
        
        if not file_extension:
            raise FileValidationError("File must have an extension", "MISSING_EXTENSION")
        
        if file_extension in DANGEROUS_EXTENSIONS:
            raise FileValidationError(
                f"File type '{file_extension}' is not allowed for security reasons",
                "DANGEROUS_FILE_TYPE"
            )
        
        if file_extension not in ALLOWED_EXTENSIONS:
            allowed = ', '.join(sorted(ALLOWED_EXTENSIONS))
            raise FileValidationError(
                f"File type '{file_extension}' not supported. Allowed types: {allowed}",
                "UNSUPPORTED_FILE_TYPE"
            )
        
        # 3. MIME type validation
        if not content_type:
            # Try to infer from extension
            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        content_type = content_type.lower().strip()
        
        if content_type not in ALLOWED_MIME_TYPES:
            allowed = ', '.join(sorted(ALLOWED_MIME_TYPES))
            raise FileValidationError(
                f"Content type '{content_type}' not supported. Allowed types: {allowed}",
                "UNSUPPORTED_MIME_TYPE"
            )
        
        # 4. File size validation (if provided)
        if file_size is not None:
            if file_size < MIN_FILE_SIZE:
                raise FileValidationError(
                    f"File too small. Minimum size: {MIN_FILE_SIZE} bytes",
                    "FILE_TOO_SMALL"
                )
            
            if file_size > MAX_FILE_SIZE:
                max_mb = MAX_FILE_SIZE / (1024 * 1024)
                raise FileValidationError(
                    f"File too large. Maximum size: {max_mb}MB",
                    "FILE_TOO_LARGE"
                )
        
        # 5. Generate safe filename
        safe_filename = PropertyImageService._generate_safe_filename(filename, file_extension)
        
        return {
            "original_filename": filename,
            "safe_filename": safe_filename,
            "file_extension": file_extension,
            "content_type": content_type,
            "validated": True
        }
    
    @staticmethod
    def _generate_safe_filename(original_filename: str, extension: str) -> str:
        """Generate a safe, unique filename."""
        # Remove the original extension and clean the name
        base_name = Path(original_filename).stem
        
        # Sanitize the base name (keep only alphanumeric, hyphens, underscores)
        safe_base = re.sub(r'[^a-zA-Z0-9\-_]', '_', base_name)
        safe_base = safe_base[:50]  # Limit length
        
        # Generate unique identifier
        unique_id = str(uuid.uuid4())

        # Combine: timestamp_uuid_originalname.ext
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{unique_id}_{safe_base}{extension}"
        
        return safe_filename
    
    @staticmethod
    async def validate_property_image_limits(
        db: AsyncSession,
        property_id: int
    ) -> None:
        """
        Validate that property doesn't exceed image limits.
        
        Args:
            db: Database session
            property_id: Property ID to check
            
        Raises:
            FileValidationError: If limits are exceeded
        """
        # Count existing images
        stmt = select(func.count()).select_from(PropertyImage).where(
            col(PropertyImage.property_id) == property_id
        )
        result = await db.execute(stmt)
        image_count = result.scalar() or 0
        
        if image_count >= MAX_IMAGES_PER_PROPERTY:
            raise FileValidationError(
                f"Maximum {MAX_IMAGES_PER_PROPERTY} images allowed per property",
                "IMAGE_LIMIT_EXCEEDED"
            )

    # Removed SAS token generation - using simplified direct upload approach
    @staticmethod
    async def save_property_image_record(
        db: AsyncSession,
        property_id: int,
        image_url: str,
        is_primary: bool = False,
        display_order: Optional[int] = None
    ) -> PropertyImage:
        """
        Save a property image record to the database after successful upload.
        
        Args:
            db: Database session
            property_id: The property this image belongs to
            image_url: The public URL of the uploaded image
            is_primary: Whether this is the primary image
            display_order: Display order for the image
            
        Returns:
            The created PropertyImage record
        """
        try:
            # If setting as primary, unset other primary images
            if is_primary:
                stmt = select(PropertyImage).where(
                    col(PropertyImage.property_id) == property_id,
                    col(PropertyImage.is_primary) == True
                )
                result = await db.execute(stmt)
                existing_primary = result.scalars().all()
                
                for img in existing_primary:
                    img.is_primary = False
            
            # Create new image record
            new_image = PropertyImage(
                property_id=property_id,
                image_url=image_url,
                is_primary=is_primary,
                display_order=display_order if display_order is not None else 0
            )
            
            db.add(new_image)
            await db.commit()
            await db.refresh(new_image)
            
            return new_image
        except Exception as e:
            logger.error(f"Failed to save image record for property {property_id}: {e}")
            await db.rollback()
            raise
    
    @staticmethod
    async def get_property_images(
        db: AsyncSession,
        property_id: int
    ) -> List[PropertyImage]:
        """
        Get all images for a property.
        
        Args:
            db: Database session
            property_id: The property ID
            
        Returns:
            List of PropertyImage records
        """
        stmt = select(PropertyImage).where(
        col(PropertyImage.property_id) == property_id
        ).order_by(col(PropertyImage.display_order), col(PropertyImage.created_at))
        
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    async def delete_property_image(
        db: AsyncSession,
        image_id: int,
        user_id: str
    ) -> bool:
        """
        Delete a property image from both database and blob storage.
        
        Args:
            db: Database session
            image_id: The image ID to delete
            user_id: The user ID for authorization
            
        Returns:
            True if deleted, False otherwise
        """
        # Get the image record with proper type alignment
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            logger.warning(f"Invalid user_id format: {user_id}")
            return False
            
        stmt = select(PropertyImage).join(Property).where(
            col(PropertyImage.id) == image_id,
            col(Property.user_id) == user_uuid  # Ensure type alignment
        )
        result = await db.execute(stmt)
        image = result.scalar_one_or_none()
        
        if not image:
            logger.warning(f"Image {image_id} not found or unauthorized")
            return False
        
        try:
            # Delete from database first (within transaction)
            await db.delete(image)
            await db.commit()
            
            # After successful database deletion, delete from blob storage
            if image.image_url:
                deleted = await delete_blob_by_url(image.image_url)
                if not deleted:
                    logger.warning(f"Database deleted but blob cleanup failed for image {image_id}. Manual cleanup may be needed for: {image.image_url}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete image {image_id}: {e}")
            await db.rollback()
            return False
    
    @staticmethod
    async def reorder_images(
        db: AsyncSession,
        property_id: int,
        image_orders: List[Dict[str, Any]]
    ) -> List[PropertyImage]:
        """
        Reorder property images with transactional safety.
        
        Args:
            db: Database session
            property_id: The property ID
            image_orders: List of dicts with image_id and display_order
            
        Returns:
            Updated list of PropertyImage records
        """
        try:
            # Get all images for the property
            stmt = select(PropertyImage).where(
                col(PropertyImage.property_id) == property_id
            )
            result = await db.execute(stmt)
            images = {str(img.id): img for img in result.scalars().all()}
            
            # Validate inputs before making any changes
            seen_orders = set()
            for order_info in image_orders:
                if 'image_id' not in order_info:
                    raise ValueError("Each order item must include 'image_id'")
                
                image_id_raw = order_info.get('image_id')
                if image_id_raw is None:
                    raise ValueError("'image_id' cannot be None")
                
                image_id = str(image_id_raw)
                
                if 'display_order' not in order_info:
                    raise ValueError("Each order item must include 'display_order'")
                    
                display_order = order_info.get('display_order')
                if not isinstance(display_order, int) or display_order < 0:
                    raise ValueError(f"'display_order' must be a non-negative integer, got: {display_order}")
                
                if image_id not in images:
                    raise ValueError(f"Image {order_info['image_id']} does not belong to property {property_id}")
                
                # Check for duplicate display orders to prevent inconsistent ordering
                if display_order in seen_orders:
                    raise ValueError(f"Duplicate display_order {display_order} found. Each image must have a unique display order.")
                seen_orders.add(display_order)
            
            # Apply updates after validation
            for order_info in image_orders:
                image_id = str(order_info['image_id'])
                display_order = order_info['display_order']
                images[image_id].display_order = display_order
            
            await db.commit()
            
        except Exception:
            # Rollback on error to avoid partial updates
            await db.rollback()
            raise
        
        # Return updated images
        return await PropertyImageService.get_property_images(db, property_id)
    
    @staticmethod
    async def set_primary_image(
        db: AsyncSession,
        property_id: int,
        image_id: int
    ) -> PropertyImage:
        """
        Set an image as the primary image for a property, atomically.
        
        Args:
            db: Database session
            property_id: The property ID
            image_id: The image ID to set as primary
            
        Returns:
            The updated PropertyImage record
        """
        try:
            # Verify the image exists first, before making any changes
            stmt = select(PropertyImage).where(
                col(PropertyImage.id) == image_id,
                col(PropertyImage.property_id) == property_id
            )
            result = await db.execute(stmt)
            image = result.scalar_one_or_none()
            
            if not image:
                raise ValueError(f"Image {image_id} not found for property {property_id}")
            
            # Unset current primary images
            stmt = select(PropertyImage).where(
                col(PropertyImage.property_id) == property_id,
                col(PropertyImage.is_primary) == True
            )
            result = await db.execute(stmt)
            existing_primary = result.scalars().all()
            
            for img in existing_primary:
                img.is_primary = False
            
            # Set new primary
            image.is_primary = True
            
            # Commit all changes atomically
            await db.commit()
            await db.refresh(image)
            
        except Exception:
            # Rollback on any error to maintain consistency
            await db.rollback()
            raise
        
        return image
    
    @staticmethod
    async def generate_image_secure_url(
        image_url: str,
        current_user: User
    ) -> dict:
        """
        Generate a time-limited SAS token URL for property image access.
        
        Args:
            image_url: The Azure Blob URL of the image
            current_user: Current authenticated user
            
        Returns:
            Dict with secure_url, expires_at, expires_in_seconds
        """
        # Authorization check - all authenticated users can view property images they have access to
        # The property ownership check should be done at the router level if needed
        
        try:
            # Generate secure URL with SAS token
            url_data = await generate_secure_document_url(
                blob_url=image_url,
                user_id=current_user.id,
                document_id=image_url,  # Use URL as identifier for logging
                expires_in_hours=1,
                client_ip=None,  # No IP restriction for browser-loaded images
            )
            
            return url_data
            
        except Exception as e:
            logger.error(f"Error generating secure URL for property image: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate secure URL: {str(e)}"
            )