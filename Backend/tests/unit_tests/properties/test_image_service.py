"""
Unit tests for PropertyImageService.
Tests file validation, database operations, and Azure blob storage integration.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import uuid

from Backend.api.properties.image_service import (
    PropertyImageService,
    FileValidationError,
    MAX_FILE_SIZE,
    MIN_FILE_SIZE,
    MAX_IMAGES_PER_PROPERTY,
    MAX_FILENAME_LENGTH,
)
from Backend.models.property import PropertyImage

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestPropertyImageServiceFileValidation:
    """Test file validation methods."""
    
    def test_validate_file_upload_success(self):
        """Test successful file validation."""
        result = PropertyImageService.validate_file_upload(
            filename="test_image.jpg",
            content_type="image/jpeg",
            file_size=5000000  # 5MB
        )
        
        assert result["original_filename"] == "test_image.jpg"
        assert result["file_extension"] == ".jpg"
        assert result["content_type"] == "image/jpeg"
        assert result["validated"] is True
        assert "safe_filename" in result
    
    def test_validate_file_upload_missing_filename(self):
        """Test validation with missing filename."""
        with pytest.raises(FileValidationError) as exc_info:
            PropertyImageService.validate_file_upload(
                filename="",
                content_type="image/jpeg"
            )
        
        assert exc_info.value.error_code == "MISSING_FILENAME"
        assert "Filename is required" in str(exc_info.value)
    
    def test_validate_file_upload_filename_too_long(self):
        """Test validation with filename too long."""
        long_filename = "a" * (MAX_FILENAME_LENGTH + 1) + ".jpg"
        
        with pytest.raises(FileValidationError) as exc_info:
            PropertyImageService.validate_file_upload(
                filename=long_filename,
                content_type="image/jpeg"
            )
        
        assert exc_info.value.error_code == "FILENAME_TOO_LONG"
        assert f"Maximum {MAX_FILENAME_LENGTH} characters" in str(exc_info.value)
    
    def test_validate_file_upload_missing_extension(self):
        """Test validation with missing file extension."""
        with pytest.raises(FileValidationError) as exc_info:
            PropertyImageService.validate_file_upload(
                filename="test_image",
                content_type="image/jpeg"
            )
        
        assert exc_info.value.error_code == "MISSING_EXTENSION"
        assert "File must have an extension" in str(exc_info.value)
    
    def test_validate_file_upload_dangerous_extension(self):
        """Test validation with dangerous file extension."""
        for dangerous_ext in [".exe", ".bat", ".cmd", ".php", ".js"]:
            with pytest.raises(FileValidationError) as exc_info:
                PropertyImageService.validate_file_upload(
                    filename=f"malicious{dangerous_ext}",
                    content_type="application/octet-stream"
                )
            
            assert exc_info.value.error_code == "DANGEROUS_FILE_TYPE"
            assert "not allowed for security reasons" in str(exc_info.value)
    
    def test_validate_file_upload_unsupported_extension(self):
        """Test validation with unsupported file extension."""
        with pytest.raises(FileValidationError) as exc_info:
            PropertyImageService.validate_file_upload(
                filename="document.pdf",
                content_type="application/pdf"
            )
        
        assert exc_info.value.error_code == "UNSUPPORTED_FILE_TYPE"
        assert "not supported" in str(exc_info.value)
    
    def test_validate_file_upload_unsupported_mime_type(self):
        """Test validation with unsupported MIME type."""
        with pytest.raises(FileValidationError) as exc_info:
            PropertyImageService.validate_file_upload(
                filename="test.jpg",
                content_type="application/pdf"
            )
        
        assert exc_info.value.error_code == "UNSUPPORTED_MIME_TYPE"
        assert "not supported" in str(exc_info.value)
    
    def test_validate_file_upload_file_too_small(self):
        """Test validation with file too small."""
        with pytest.raises(FileValidationError) as exc_info:
            PropertyImageService.validate_file_upload(
                filename="tiny.jpg",
                content_type="image/jpeg",
                file_size=MIN_FILE_SIZE - 1
            )
        
        assert exc_info.value.error_code == "FILE_TOO_SMALL"
        assert f"Minimum size: {MIN_FILE_SIZE}" in str(exc_info.value)
    
    def test_validate_file_upload_file_too_large(self):
        """Test validation with file too large."""
        with pytest.raises(FileValidationError) as exc_info:
            PropertyImageService.validate_file_upload(
                filename="huge.jpg",
                content_type="image/jpeg",
                file_size=MAX_FILE_SIZE + 1
            )
        
        assert exc_info.value.error_code == "FILE_TOO_LARGE"
        assert "Maximum size:" in str(exc_info.value)
    
    def test_validate_file_upload_mime_type_inference(self):
        """Test MIME type inference when not provided."""
        result = PropertyImageService.validate_file_upload(
            filename="test.png",
            content_type=""
        )
        
        assert result["content_type"] == "image/png"
        assert result["validated"] is True
    
    def test_validate_file_upload_all_supported_formats(self):
        """Test validation with all supported image formats."""
        supported_formats = [
            ("image.jpg", "image/jpeg"),
            ("image.jpeg", "image/jpeg"),
            ("image.png", "image/png"),
            ("image.gif", "image/gif"),
            ("image.webp", "image/webp")
        ]
        
        for filename, content_type in supported_formats:
            result = PropertyImageService.validate_file_upload(
                filename=filename,
                content_type=content_type,
                file_size=5000000
            )
            assert result["validated"] is True
    
    def test_generate_safe_filename(self):
        """Test safe filename generation."""
        original_filename = "My Test Image!@#$.jpg"
        extension = ".jpg"
        
        safe_filename = PropertyImageService._generate_safe_filename(original_filename, extension)
        
        # Should contain timestamp, UUID, sanitized name, and extension
        assert safe_filename.endswith(".jpg")
        assert "My_Test_Image" in safe_filename
        assert len(safe_filename.split("_")) >= 4  # timestamp_uuid_name.ext
        
        # Should be unique each time
        safe_filename2 = PropertyImageService._generate_safe_filename(original_filename, extension)
        assert safe_filename != safe_filename2
    
    def test_generate_safe_filename_long_name(self):
        """Test safe filename generation with very long name."""
        long_name = "a" * 100 + ".jpg"
        extension = ".jpg"
        
        safe_filename = PropertyImageService._generate_safe_filename(long_name, extension)
        
        # Should truncate the base name
        assert len(safe_filename) < len(long_name) + 50  # UUID and timestamp add length
        assert safe_filename.endswith(".jpg")
    
    def test_generate_safe_filename_special_characters(self):
        """Test safe filename generation with special characters."""
        special_name = "файл изображения (тест) [2024].jpg"
        extension = ".jpg"
        
        safe_filename = PropertyImageService._generate_safe_filename(special_name, extension)
        
        # Should sanitize special characters
        assert "(" not in safe_filename
        assert ")" not in safe_filename
        assert "[" not in safe_filename
        assert "]" not in safe_filename
        assert safe_filename.endswith(".jpg")


class TestPropertyImageServiceDatabaseOperations:
    """Test database operation methods."""
    
    @pytest.mark.asyncio
    async def test_validate_property_image_limits_success(self):
        """Test image limit validation when under limit."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = MAX_IMAGES_PER_PROPERTY - 1
        mock_session.execute.return_value = mock_result
        
        # Should not raise an exception
        await PropertyImageService.validate_property_image_limits(mock_session, 1)
        
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_property_image_limits_exceeded(self):
        """Test image limit validation when limit exceeded."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = MAX_IMAGES_PER_PROPERTY
        mock_session.execute.return_value = mock_result
        
        with pytest.raises(FileValidationError) as exc_info:
            await PropertyImageService.validate_property_image_limits(mock_session, 1)
        
        assert exc_info.value.error_code == "IMAGE_LIMIT_EXCEEDED"
        assert f"Maximum {MAX_IMAGES_PER_PROPERTY} images" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_property_image_limits_no_images(self):
        """Test image limit validation when no images exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        # Should not raise an exception
        await PropertyImageService.validate_property_image_limits(mock_session, 1)
    
    @pytest.mark.asyncio
    async def test_save_property_image_record_success(self):
        """Test successful saving of image record."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        image_url = "https://briklicorestorage.blob.core.windows.net/images/test.jpg"
        
        result = await PropertyImageService.save_property_image_record(
            db=mock_session,
            property_id=1,
            image_url=image_url,
            is_primary=False,
            display_order=0
        )
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_property_image_record_as_primary(self):
        """Test saving image record as primary (unsets other primaries)."""
        mock_session = AsyncMock()
        
        # Mock existing primary images
        mock_existing_primary = PropertyImage(
            id=1, property_id=1, image_url="existing.jpg", is_primary=True
        )
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_existing_primary]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        image_url = "https://briklicorestorage.blob.core.windows.net/images/new_primary.jpg"
        
        result = await PropertyImageService.save_property_image_record(
            db=mock_session,
            property_id=1,
            image_url=image_url,
            is_primary=True,
            display_order=0
        )
        
        # Should unset existing primary
        assert mock_existing_primary.is_primary is False
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_property_images_success(self):
        """Test successful retrieval of property images."""
        mock_session = AsyncMock()
        mock_images = [
            PropertyImage(id=1, property_id=1, image_url="image1.jpg", display_order=0),
            PropertyImage(id=2, property_id=1, image_url="image2.jpg", display_order=1),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_images
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = await PropertyImageService.get_property_images(mock_session, 1)
        
        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_property_images_empty(self):
        """Test retrieval when no images exist."""
        mock_session = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = await PropertyImageService.get_property_images(mock_session, 1)
        
        assert len(result) == 0
        assert result == []
    
    @pytest.mark.asyncio
    async def test_delete_property_image_success(self):
        """Test successful image deletion."""
        mock_session = AsyncMock()
        user_id = str(uuid.uuid4())
        mock_image = PropertyImage(
            id=1, 
            property_id=1, 
            image_url="https://briklicorestorage.blob.core.windows.net/images/test.jpg"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_image
        mock_session.execute.return_value = mock_result
        
        with patch("Backend.api.properties.image_service.delete_blob_by_url") as mock_delete_blob:
            mock_delete_blob.return_value = True
            
            result = await PropertyImageService.delete_property_image(
                mock_session, 1, user_id
            )
            
            assert result is True
            mock_delete_blob.assert_called_once_with(mock_image.image_url)
            mock_session.delete.assert_called_once_with(mock_image)
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_property_image_not_found(self):
        """Test deletion when image not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await PropertyImageService.delete_property_image(
            mock_session, 999, str(uuid.uuid4())
        )
        
        assert result is False
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_delete_property_image_blob_deletion_fails(self):
        """Test deletion when blob storage deletion fails."""
        mock_session = AsyncMock()
        mock_image = PropertyImage(
            id=1, 
            property_id=1, 
            image_url="https://briklicorestorage.blob.core.windows.net/images/test.jpg"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_image
        mock_session.execute.return_value = mock_result
        
        with patch("Backend.api.properties.image_service.delete_blob_by_url") as mock_delete_blob:
            mock_delete_blob.return_value = False  # Blob deletion failed
            
            result = await PropertyImageService.delete_property_image(
                mock_session, 1, str(uuid.uuid4())
            )
            
            # Should still delete from database even if blob deletion fails
            assert result is True
            mock_session.delete.assert_called_once_with(mock_image)
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reorder_images_success(self):
        """Test successful image reordering."""
        mock_session = AsyncMock()
        
        # Mock existing images
        mock_images = {
            "1": PropertyImage(id=1, property_id=1, image_url="image1.jpg", display_order=0),
            "2": PropertyImage(id=2, property_id=1, image_url="image2.jpg", display_order=1),
        }
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = list(mock_images.values())
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        # Mock the get_property_images call
        reordered_images = [
            PropertyImage(id=2, property_id=1, image_url="image2.jpg", display_order=0),
            PropertyImage(id=1, property_id=1, image_url="image1.jpg", display_order=1),
        ]
        
        with patch.object(PropertyImageService, 'get_property_images') as mock_get_images:
            mock_get_images.return_value = reordered_images
            
            image_orders = [
                {"image_id": 2, "display_order": 0},
                {"image_id": 1, "display_order": 1}
            ]
            
            result = await PropertyImageService.reorder_images(
                mock_session, 1, image_orders
            )
            
            assert len(result) == 2
            assert result[0].display_order == 0
            assert result[1].display_order == 1
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reorder_images_partial_update(self):
        """Test reordering with partial image list."""
        mock_session = AsyncMock()
        
        # Mock existing images (3 images)
        mock_images = {
            "1": PropertyImage(id=1, property_id=1, image_url="image1.jpg", display_order=0),
            "2": PropertyImage(id=2, property_id=1, image_url="image2.jpg", display_order=1),
            "3": PropertyImage(id=3, property_id=1, image_url="image3.jpg", display_order=2),
        }
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = list(mock_images.values())
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(PropertyImageService, 'get_property_images') as mock_get_images:
            mock_get_images.return_value = list(mock_images.values())
            
            # Only reorder image 2
            image_orders = [
                {"image_id": 2, "display_order": 5}
            ]
            
            result = await PropertyImageService.reorder_images(
                mock_session, 1, image_orders
            )
            
            # Should only update the specified image
            assert mock_images["2"].display_order == 5
            # Other images should remain unchanged
            assert mock_images["1"].display_order == 0
            assert mock_images["3"].display_order == 2
    
    @pytest.mark.asyncio
    async def test_set_primary_image_success(self):
        """Test successful setting of primary image."""
        mock_session = AsyncMock()
        
        # Mock the target image (first query due to my changes)
        mock_target_image = PropertyImage(
            id=2, 
            property_id=1, 
            image_url="target.jpg", 
            is_primary=False
        )
        mock_target_result = MagicMock()
        mock_target_result.scalar_one_or_none.return_value = mock_target_image
        
        # Mock existing primary images (to unset) (second query)
        mock_existing_primary = PropertyImage(
            id=1, 
            property_id=1, 
            image_url="existing.jpg", 
            is_primary=True
        )
        mock_existing_scalars = MagicMock()
        mock_existing_scalars.all.return_value = [mock_existing_primary]
        mock_existing_result = MagicMock()
        mock_existing_result.scalars.return_value = mock_existing_scalars
        
        # Setup execute to return results in the new order (target first, then existing)
        mock_session.execute.side_effect = [mock_target_result, mock_existing_result]
        
        result = await PropertyImageService.set_primary_image(mock_session, 1, 2)
        
        # Should unset existing primary
        assert mock_existing_primary.is_primary is False
        # Should set new primary
        assert mock_target_image.is_primary is True
        assert result == mock_target_image
        
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_target_image)
    
    @pytest.mark.asyncio
    async def test_set_primary_image_not_found(self):
        """Test setting primary when image not found."""
        mock_session = AsyncMock()
        
        # Mock image not found (first query due to my changes)
        mock_target_result = MagicMock()
        mock_target_result.scalar_one_or_none.return_value = None
        
        # The function should return early and not execute second query
        mock_session.execute.side_effect = [mock_target_result]
        
        with pytest.raises(ValueError) as exc_info:
            await PropertyImageService.set_primary_image(mock_session, 1, 999)
        
        assert "Image 999 not found for property 1" in str(exc_info.value)
        # Should rollback on error
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_primary_image_already_primary(self):
        """Test setting image as primary when it's already primary."""
        mock_session = AsyncMock()
        
        # Mock the target image (already primary)
        mock_target_image = PropertyImage(
            id=1, 
            property_id=1, 
            image_url="target.jpg", 
            is_primary=True
        )
        
        # First query: get the target image 
        mock_target_result = MagicMock()
        mock_target_result.scalar_one_or_none.return_value = mock_target_image
        
        # Second query: get existing primaries (includes the same image)
        mock_existing_scalars = MagicMock()
        mock_existing_scalars.all.return_value = [mock_target_image]
        mock_existing_result = MagicMock()
        mock_existing_result.scalars.return_value = mock_existing_scalars
        
        # Setup execution order: target first, then existing
        mock_session.execute.side_effect = [mock_target_result, mock_existing_result]
        
        result = await PropertyImageService.set_primary_image(mock_session, 1, 1)
        
        # Should still set as primary (idempotent)
        assert mock_target_image.is_primary is True
        assert result == mock_target_image
        
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_target_image)
