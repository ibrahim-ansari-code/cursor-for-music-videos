"""
Tests for property image DELETE endpoint.
Tests image deletion functionality with proper authorization and cleanup.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch
from datetime import datetime

from Backend.models.property import PropertyType, PropertyImage
from Backend.models.enums import PropertyStatus
from Backend.api.properties.schemas import PropertyImageResponse, PropertyDetailResponse, OwnerResponse
from ...base_test import (
    BasePropertyTest,
    create_test_property,
    create_test_user
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


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


class TestPropertyImageDelete(BasePropertyTest):
    """Test property image delete endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_property_image_success(self):
        """Test successful deletion of property image."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        image_id = 1
        
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
             patch("Backend.api.properties.image_service.PropertyImageService.delete_property_image") as mock_delete:
            
            mock_get_property.return_value = mock_property
            mock_delete.return_value = True  # Successful deletion
            
            response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Image deleted successfully"
            
            mock_get_property.assert_called_once_with(property_id, self.mock_user, mock_session)
            mock_delete.assert_called_once_with(mock_session, image_id, str(self.mock_user.id))
    
    @pytest.mark.asyncio
    async def test_delete_property_image_property_not_found(self):
        """Test delete when property doesn't exist."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 999
        image_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=404,
                detail="Property not found or you don't have access"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
            
            assert response.status_code == 404
            assert response.json()["detail"] == "Property not found or you don't have access"
    
    @pytest.mark.asyncio
    async def test_delete_property_image_unauthorized(self):
        """Test delete when user doesn't own property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        image_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=403,
                detail="Property not found or you don't have access"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
            
            assert response.status_code == 403
            assert response.json()["detail"] == "Property not found or you don't have access"
    
    @pytest.mark.asyncio
    async def test_delete_property_image_not_found(self):
        """Test delete when image doesn't exist."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        image_id = 999
        
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
             patch("Backend.api.properties.image_service.PropertyImageService.delete_property_image") as mock_delete:
            
            mock_get_property.return_value = mock_property
            mock_delete.return_value = False  # Image not found
            
            response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
            
            assert response.status_code == 404
            assert response.json()["detail"] == "Image not found"
            
            mock_delete.assert_called_once_with(mock_session, image_id, str(self.mock_user.id))
    
    @pytest.mark.asyncio
    async def test_delete_property_image_primary_image(self):
        """Test deletion of primary image."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        image_id = 1
        
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
             patch("Backend.api.properties.image_service.PropertyImageService.delete_property_image") as mock_delete:
            
            mock_get_property.return_value = mock_property
            mock_delete.return_value = True  # Successfully deleted primary image
            
            response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Image deleted successfully"
            
            # Service should handle primary image deletion logic
            mock_delete.assert_called_once_with(mock_session, image_id, str(self.mock_user.id))
    
    @pytest.mark.asyncio
    async def test_delete_property_image_database_error(self):
        """Test handling of database errors during deletion."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        image_id = 1
        
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
             patch("Backend.api.properties.image_service.PropertyImageService.delete_property_image") as mock_delete:
            
            mock_get_property.return_value = mock_property
            mock_delete.side_effect = Exception("Database connection error")
            
            response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
            
            # Should return 500 with proper error message
            assert response.status_code == 500
            assert response.json()["detail"] == "Failed to delete image"
    
    @pytest.mark.asyncio
    async def test_delete_property_image_blob_storage_cleanup(self):
        """Test that blob storage cleanup is handled by the service."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        image_id = 1
        
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
             patch("Backend.api.properties.image_service.PropertyImageService.delete_property_image") as mock_delete:
            
            mock_get_property.return_value = mock_property
            mock_delete.return_value = True  # Service handles both DB and blob storage cleanup
            
            response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Image deleted successfully"
            
            # The service method should handle both database and blob storage cleanup
            mock_delete.assert_called_once_with(mock_session, image_id, str(self.mock_user.id))
    
    @pytest.mark.asyncio
    async def test_delete_property_image_invalid_image_id(self):
        """Test delete with invalid image ID."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        invalid_image_id = "invalid"
        
        response = self.client.delete(f"/api/properties/{property_id}/images/{invalid_image_id}")
        
        # Should return 422 due to validation error
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_delete_property_image_invalid_property_id(self):
        """Test delete with invalid property ID."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        invalid_property_id = "invalid"
        image_id = 1
        
        response = self.client.delete(f"/api/properties/{invalid_property_id}/images/{image_id}")
        
        # Should return 422 due to validation error
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_delete_property_image_zero_ids(self):
        """Test delete with zero IDs."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 0
        image_id = 0
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=404,
                detail="Property not found"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_property_image_negative_ids(self):
        """Test delete with negative IDs."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = -1
        image_id = -1
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=404,
                detail="Property not found"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_property_image_large_ids(self):
        """Test delete with very large IDs."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 999999999
        image_id = 999999999
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=404,
                detail="Property not found"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_property_image_user_id_string_conversion(self):
        """Test that user ID is properly converted to string for service call."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        image_id = 1
        
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
             patch("Backend.api.properties.image_service.PropertyImageService.delete_property_image") as mock_delete:
            
            mock_get_property.return_value = mock_property
            mock_delete.return_value = True
            
            response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
            
            assert response.status_code == 200
            
            # Verify that user_id was converted to string
            mock_delete.assert_called_once_with(mock_session, image_id, str(self.mock_user.id))
    
    @pytest.mark.asyncio
    async def test_delete_multiple_images_sequentially(self):
        """Test deleting multiple images in sequence."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        image_ids = [1, 2, 3]
        
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
             patch("Backend.api.properties.image_service.PropertyImageService.delete_property_image") as mock_delete:
            
            mock_get_property.return_value = mock_property
            mock_delete.return_value = True
            
            # Delete each image
            for image_id in image_ids:
                response = self.client.delete(f"/api/properties/{property_id}/images/{image_id}")
                assert response.status_code == 200
                assert response.json()["message"] == "Image deleted successfully"
            
            # Verify all deletions were called
            assert mock_delete.call_count == len(image_ids)
            for i, image_id in enumerate(image_ids):
                assert mock_delete.call_args_list[i][0] == (mock_session, image_id, str(self.mock_user.id))