"""
Tests for property image POST upload endpoint.
Tests image upload functionality with comprehensive error handling.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from io import BytesIO

from Backend.models.property import PropertyType, PropertyImage
from Backend.models.enums import PropertyStatus
from Backend.api.properties.schemas import PropertyDetailResponse, OwnerResponse
from Backend.api.properties.image_service import FileValidationError
from ...base_test import BasePropertyTest


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


def create_mock_upload_file(filename: str = "test.jpg", content_type: str = "image/jpeg", content: bytes = b"fake_image_content"):
    """Create a mock UploadFile object."""
    # Create a minimal valid JPEG header for tests
    if filename.endswith('.jpg') or filename.endswith('.jpeg'):
        # JPEG file signature: FF D8 FF
        content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00' + content
    elif filename.endswith('.png'):
        # PNG file signature: 89 50 4E 47 0D 0A 1A 0A
        content = b'\x89PNG\r\n\x1a\n' + content
    
    mock_file = MagicMock()
    mock_file.filename = filename
    mock_file.content_type = content_type
    mock_file.file = BytesIO(content)
    mock_file.read.return_value = content
    return mock_file


def create_test_image(image_id: int = 1, property_id: int = 1, **kwargs):
    """Helper to create a test PropertyImage."""
    defaults = {
        "id": image_id,
        "property_id": property_id,
        "image_url": f"https://test.blob.core.windows.net/property-images/test_image_{image_id}.jpg",
        "image_type": "photo",
        "is_primary": False,
        "caption": f"Test image {image_id}",
        "display_order": image_id,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    defaults.update(kwargs)
    return PropertyImage(**defaults)


class TestPropertyImageUpload(BasePropertyTest):
    """Test property image upload endpoint."""
    
    @pytest.mark.asyncio
    async def test_upload_property_image_success(self):
        """Test successful image upload."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create content with JPEG header
        jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00fake_image_content'
        
        # Create mock property response
        mock_property = PropertyDetailResponse(
            id=property_id,
            name="Test Property",
            address="123 Test St",
            city="Test City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.RESIDENTIAL,
            description="Test property",
            year_built=2020,
            status=PropertyStatus.ACTIVE,
            user_id=self.mock_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            owner=OwnerResponse(
                id=self.mock_user.id,
                first_name="Test",
                last_name="User",
                email="test@example.com"
            ),
            units=[],
            stats=None
        )
        
        # Create mock uploaded image
        mock_uploaded_image = create_test_image(
            image_id=1, 
            property_id=property_id, 
            is_primary=False, 
            display_order=0
        )
        
        mock_file = create_mock_upload_file()
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.validate_property_image_limits") as mock_validate_limits, \
             patch("Backend.api.properties.image_router.validate_file_from_upload") as mock_validate_file, \
             patch("Backend.api.properties.image_router.upload_property_image_to_blob") as mock_upload_blob, \
             patch("Backend.api.properties.image_service.PropertyImageService.save_property_image_record") as mock_save_record:
            
            mock_get_property.return_value = mock_property
            mock_validate_limits.return_value = None
            mock_validate_file.return_value = (jpeg_content, "image/jpeg")
            mock_upload_blob.return_value = "https://test.blob.core.windows.net/property-images/uploaded_image.jpg"
            mock_save_record.return_value = mock_uploaded_image
            
            files = {"file": ("test.jpg", BytesIO(jpeg_content), "image/jpeg")}
            response = self.client.post(
                f"/api/properties/{property_id}/images/upload",
                files=files,
                data={"is_primary": "false", "display_order": "0"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["property_id"] == property_id
            assert data["is_primary"] is False
            assert data["display_order"] == 0
            assert "https://test.blob.core.windows.net" in data["image_url"]
            
            mock_get_property.assert_called_once_with(property_id, self.mock_user, mock_session)
            mock_validate_limits.assert_called_once_with(mock_session, property_id)
            mock_validate_file.assert_called_once()
            mock_upload_blob.assert_called_once()
            mock_save_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_property_image_as_primary(self):
        """Test uploading image as primary."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create content with JPEG header
        jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00fake_image_content'
        
        # Create mock property response
        mock_property = PropertyDetailResponse(
            id=property_id,
            name="Test Property",
            address="123 Test St",
            city="Test City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.RESIDENTIAL,
            description="Test property",
            year_built=2020,
            status=PropertyStatus.ACTIVE,
            user_id=self.mock_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            owner=OwnerResponse(
                id=self.mock_user.id,
                first_name="Test",
                last_name="User",
                email="test@example.com"
            ),
            units=[],
            stats=None
        )
        
        # Create mock uploaded image as primary
        mock_uploaded_image = create_test_image(
            image_id=1, 
            property_id=property_id, 
            is_primary=True, 
            display_order=0
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.validate_property_image_limits") as mock_validate_limits, \
             patch("Backend.api.properties.image_router.validate_file_from_upload") as mock_validate_file, \
             patch("Backend.api.properties.image_router.upload_property_image_to_blob") as mock_upload_blob, \
             patch("Backend.api.properties.image_service.PropertyImageService.save_property_image_record") as mock_save_record:
            
            mock_get_property.return_value = mock_property
            mock_validate_limits.return_value = None
            mock_validate_file.return_value = (jpeg_content, "image/jpeg")
            mock_upload_blob.return_value = "https://test.blob.core.windows.net/property-images/uploaded_image.jpg"
            mock_save_record.return_value = mock_uploaded_image
            
            # Create content with JPEG header
            jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00fake_image_content'
            files = {"file": ("test.jpg", BytesIO(jpeg_content), "image/jpeg")}
            response = self.client.post(
                f"/api/properties/{property_id}/images/upload",
                files=files,
                data={"is_primary": "true", "display_order": "0"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["is_primary"] is True
            
            # Verify save_property_image_record was called with is_primary=True
            mock_save_record.assert_called_once_with(
                db=mock_session,
                property_id=property_id,
                image_url="https://test.blob.core.windows.net/property-images/uploaded_image.jpg",
                is_primary=True,
                display_order=0
            )
    
    @pytest.mark.asyncio
    async def test_upload_property_image_property_not_found(self):
        """Test upload when property doesn't exist."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 999
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=404,
                detail="Property not found or you don't have access"
            )
            
            # Create content with JPEG header
            jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00fake_image_content'
            files = {"file": ("test.jpg", BytesIO(jpeg_content), "image/jpeg")}
            response = self.client.post(
                f"/api/properties/{property_id}/images/upload",
                files=files
            )
            
            assert response.status_code == 404
            assert response.json()["detail"] == "Property not found or you don't have access"
    
    @pytest.mark.asyncio
    async def test_upload_property_image_unauthorized(self):
        """Test upload when user doesn't own property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=403,
                detail="Property not found or you don't have access"
            )
            
            # Create content with JPEG header
            jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00fake_image_content'
            files = {"file": ("test.jpg", BytesIO(jpeg_content), "image/jpeg")}
            response = self.client.post(
                f"/api/properties/{property_id}/images/upload",
                files=files
            )
            
            assert response.status_code == 403
            assert response.json()["detail"] == "Property not found or you don't have access"
    
    @pytest.mark.asyncio
    async def test_upload_property_image_limit_exceeded(self):
        """Test upload when property image limit is exceeded."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create mock property response
        mock_property = PropertyDetailResponse(
            id=property_id,
            name="Test Property",
            address="123 Test St",
            city="Test City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.RESIDENTIAL,
            description="Test property",
            year_built=2020,
            status=PropertyStatus.ACTIVE,
            user_id=self.mock_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            owner=OwnerResponse(
                id=self.mock_user.id,
                first_name="Test",
                last_name="User",
                email="test@example.com"
            ),
            units=[],
            stats=None
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.validate_property_image_limits") as mock_validate_limits:
            
            mock_get_property.return_value = mock_property
            mock_validate_limits.side_effect = FileValidationError(
                "Maximum 20 images allowed per property",
                "IMAGE_LIMIT_EXCEEDED"
            )
            
            # Create content with JPEG header
            jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00fake_image_content'
            files = {"file": ("test.jpg", BytesIO(jpeg_content), "image/jpeg")}
            response = self.client.post(
                f"/api/properties/{property_id}/images/upload",
                files=files
            )
            
            assert response.status_code == 400
            assert "Maximum 20 images allowed per property" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_property_image_file_validation_error(self):
        """Test upload with invalid file."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create mock property response
        mock_property = PropertyDetailResponse(
            id=property_id,
            name="Test Property",
            address="123 Test St",
            city="Test City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.RESIDENTIAL,
            description="Test property",
            year_built=2020,
            status=PropertyStatus.ACTIVE,
            user_id=self.mock_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            owner=OwnerResponse(
                id=self.mock_user.id,
                first_name="Test",
                last_name="User",
                email="test@example.com"
            ),
            units=[],
            stats=None
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.validate_property_image_limits") as mock_validate_limits, \
             patch("Backend.api.properties.image_router.validate_file_from_upload") as mock_validate_file:
            
            mock_get_property.return_value = mock_property
            mock_validate_limits.return_value = None
            mock_validate_file.side_effect = FileValidationError(
                "File type '.exe' is not allowed for security reasons",
                "DANGEROUS_FILE_TYPE"
            )
            
            files = {"file": ("malicious.exe", BytesIO(b"fake_content"), "application/octet-stream")}
            response = self.client.post(
                f"/api/properties/{property_id}/images/upload",
                files=files
            )
            
            # The FileValidationError should be caught and converted to 400 by the router
            assert response.status_code == 400
            assert "not allowed for security reasons" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_property_image_storage_unavailable(self):
        """Test upload when storage service is unavailable."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create content with JPEG header
        jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00fake_image_content'
        
        # Create mock property response
        mock_property = PropertyDetailResponse(
            id=property_id,
            name="Test Property",
            address="123 Test St",
            city="Test City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.RESIDENTIAL,
            description="Test property",
            year_built=2020,
            status=PropertyStatus.ACTIVE,
            user_id=self.mock_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            owner=OwnerResponse(
                id=self.mock_user.id,
                first_name="Test",
                last_name="User",
                email="test@example.com"
            ),
            units=[],
            stats=None
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.validate_property_image_limits") as mock_validate_limits, \
             patch("Backend.api.properties.image_router.validate_file_from_upload") as mock_validate_file, \
             patch("Backend.api.properties.image_router.upload_property_image_to_blob") as mock_upload_blob:
            
            mock_get_property.return_value = mock_property
            mock_validate_limits.return_value = None
            mock_validate_file.return_value = (jpeg_content, "image/jpeg")
            mock_upload_blob.side_effect = ConnectionError("Storage unavailable")
            
            files = {"file": ("test.jpg", BytesIO(jpeg_content), "image/jpeg")}
            response = self.client.post(
                f"/api/properties/{property_id}/images/upload",
                files=files
            )
            
            assert response.status_code == 503
            assert response.json()["detail"] == "Storage service temporarily unavailable"
    
    @pytest.mark.asyncio
    async def test_upload_property_image_general_error(self):
        """Test upload with general server error."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create content with JPEG header
        jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00fake_image_content'
        
        # Create mock property response
        mock_property = PropertyDetailResponse(
            id=property_id,
            name="Test Property",
            address="123 Test St",
            city="Test City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.RESIDENTIAL,
            description="Test property",
            year_built=2020,
            status=PropertyStatus.ACTIVE,
            user_id=self.mock_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            owner=OwnerResponse(
                id=self.mock_user.id,
                first_name="Test",
                last_name="User",
                email="test@example.com"
            ),
            units=[],
            stats=None
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.validate_property_image_limits") as mock_validate_limits, \
             patch("Backend.api.properties.image_router.validate_file_from_upload") as mock_validate_file, \
             patch("Backend.api.properties.image_router.upload_property_image_to_blob") as mock_upload_blob:
            
            mock_get_property.return_value = mock_property
            mock_validate_limits.return_value = None
            mock_validate_file.return_value = (jpeg_content, "image/jpeg")
            mock_upload_blob.side_effect = Exception("Unexpected error")
            
            files = {"file": ("test.jpg", BytesIO(jpeg_content), "image/jpeg")}
            response = self.client.post(
                f"/api/properties/{property_id}/images/upload",
                files=files
            )
            
            assert response.status_code == 500
            assert response.json()["detail"] == "Failed to upload image"
    
    @pytest.mark.asyncio
    async def test_upload_property_image_with_custom_display_order(self):
        """Test upload with custom display order."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        custom_display_order = 5
        
        # Create content with JPEG header
        jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00fake_image_content'
        
        # Create mock property response
        mock_property = PropertyDetailResponse(
            id=property_id,
            name="Test Property",
            address="123 Test St",
            city="Test City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.RESIDENTIAL,
            description="Test property",
            year_built=2020,
            status=PropertyStatus.ACTIVE,
            user_id=self.mock_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            owner=OwnerResponse(
                id=self.mock_user.id,
                first_name="Test",
                last_name="User",
                email="test@example.com"
            ),
            units=[],
            stats=None
        )
        
        # Create mock uploaded image
        mock_uploaded_image = create_test_image(
            image_id=1, 
            property_id=property_id, 
            display_order=custom_display_order
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.validate_property_image_limits") as mock_validate_limits, \
             patch("Backend.api.properties.image_router.validate_file_from_upload") as mock_validate_file, \
             patch("Backend.api.properties.image_router.upload_property_image_to_blob") as mock_upload_blob, \
             patch("Backend.api.properties.image_service.PropertyImageService.save_property_image_record") as mock_save_record:
            
            mock_get_property.return_value = mock_property
            mock_validate_limits.return_value = None
            mock_validate_file.return_value = (jpeg_content, "image/jpeg")
            mock_upload_blob.return_value = "https://test.blob.core.windows.net/property-images/uploaded_image.jpg"
            mock_save_record.return_value = mock_uploaded_image
            
            # Create content with JPEG header
            jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00fake_image_content'
            files = {"file": ("test.jpg", BytesIO(jpeg_content), "image/jpeg")}
            response = self.client.post(
                f"/api/properties/{property_id}/images/upload",
                files=files,
                data={"display_order": str(custom_display_order)}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["display_order"] == custom_display_order
            
            # Verify save_property_image_record was called with correct display_order
            mock_save_record.assert_called_once_with(
                db=mock_session,
                property_id=property_id,
                image_url="https://test.blob.core.windows.net/property-images/uploaded_image.jpg",
                is_primary=False,
                display_order=custom_display_order
            )