"""
Tests for property image reorder PUT endpoint.
Tests reordering functionality with proper authorization.
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


class TestPropertyImageReorder(BasePropertyTest):
    """Test property image reorder endpoint."""
    
    @pytest.mark.asyncio
    async def test_reorder_property_images_success(self):
        """Test successful reordering of property images."""
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
        
        # Create mock reordered images
        mock_reordered_images = [
            create_test_image(image_id=3, property_id=property_id, display_order=0),
            create_test_image(image_id=1, property_id=property_id, display_order=1),
            create_test_image(image_id=2, property_id=property_id, display_order=2)
        ]
        
        reorder_request = [
            {"image_id": 3, "display_order": 0},
            {"image_id": 1, "display_order": 1},
            {"image_id": 2, "display_order": 2}
        ]
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.reorder_images") as mock_reorder:
            
            mock_get_property.return_value = mock_property
            mock_reorder.return_value = mock_reordered_images
            
            response = self.client.put(
                f"/api/properties/{property_id}/images/reorder",
                json=reorder_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert data[0]["id"] == 3
            assert data[0]["display_order"] == 0
            assert data[1]["id"] == 1
            assert data[1]["display_order"] == 1
            assert data[2]["id"] == 2
            assert data[2]["display_order"] == 2
            
            mock_get_property.assert_called_once_with(property_id, self.mock_user, mock_session)
            mock_reorder.assert_called_once_with(mock_session, property_id, reorder_request)
    
    @pytest.mark.asyncio
    async def test_reorder_property_images_empty_list(self):
        """Test reordering with empty list."""
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
        
        reorder_request = []
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.reorder_images") as mock_reorder:
            
            mock_get_property.return_value = mock_property
            mock_reorder.return_value = []
            
            response = self.client.put(
                f"/api/properties/{property_id}/images/reorder",
                json=reorder_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 0
            assert data == []
            
            mock_get_property.assert_called_once_with(property_id, self.mock_user, mock_session)
            mock_reorder.assert_called_once_with(mock_session, property_id, reorder_request)
    
    @pytest.mark.asyncio
    async def test_reorder_property_images_single_image(self):
        """Test reordering with single image."""
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
        
        # Single image reorder
        mock_reordered_images = [
            create_test_image(image_id=1, property_id=property_id, display_order=5)
        ]
        
        reorder_request = [
            {"image_id": 1, "display_order": 5}
        ]
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.reorder_images") as mock_reorder:
            
            mock_get_property.return_value = mock_property
            mock_reorder.return_value = mock_reordered_images
            
            response = self.client.put(
                f"/api/properties/{property_id}/images/reorder",
                json=reorder_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == 1
            assert data[0]["display_order"] == 5
    
    @pytest.mark.asyncio
    async def test_reorder_property_images_property_not_found(self):
        """Test reorder when property doesn't exist."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 999
        
        reorder_request = [
            {"image_id": 1, "display_order": 0}
        ]
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=404,
                detail="Property not found or you don't have access"
            )
            
            response = self.client.put(
                f"/api/properties/{property_id}/images/reorder",
                json=reorder_request
            )
            
            assert response.status_code == 404
            assert response.json()["detail"] == "Property not found or you don't have access"
    
    @pytest.mark.asyncio
    async def test_reorder_property_images_unauthorized(self):
        """Test reorder when user doesn't own property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        reorder_request = [
            {"image_id": 1, "display_order": 0}
        ]
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=403,
                detail="Property not found or you don't have access"
            )
            
            response = self.client.put(
                f"/api/properties/{property_id}/images/reorder",
                json=reorder_request
            )
            
            assert response.status_code == 403
            assert response.json()["detail"] == "Property not found or you don't have access"
    
    @pytest.mark.asyncio
    async def test_reorder_property_images_invalid_request_format(self):
        """Test reorder with invalid request format."""
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
        
        # Invalid request format - missing required fields
        invalid_request = [
            {"image_id": 1},  # missing display_order
            {"display_order": 0}  # missing image_id
        ]
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.return_value = mock_property
            
            response = self.client.put(
                f"/api/properties/{property_id}/images/reorder",
                json=invalid_request
            )
            
            # Should return 422 due to validation error
            assert response.status_code == 422
    

    
    @pytest.mark.asyncio
    async def test_reorder_property_images_service_error(self):
        """Test handling of service errors during reorder."""
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
        
        reorder_request = [
            {"image_id": 1, "display_order": 0}
        ]
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.reorder_images") as mock_reorder:
            
            mock_get_property.return_value = mock_property
            mock_reorder.side_effect = Exception("Database error")
            
            response = self.client.put(
                f"/api/properties/{property_id}/images/reorder",
                json=reorder_request
            )
            
            # Should return 500 with proper error message
            assert response.status_code == 500
            assert response.json()["detail"] == "Failed to reorder images"
    
    @pytest.mark.asyncio
    async def test_reorder_property_images_large_display_order(self):
        """Test reordering with very large display order values."""
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
        
        large_order = 999999
        mock_reordered_images = [
            create_test_image(image_id=1, property_id=property_id, display_order=large_order)
        ]
        
        reorder_request = [
            {"image_id": 1, "display_order": large_order}
        ]
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.reorder_images") as mock_reorder:
            
            mock_get_property.return_value = mock_property
            mock_reorder.return_value = mock_reordered_images
            
            response = self.client.put(
                f"/api/properties/{property_id}/images/reorder",
                json=reorder_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data[0]["display_order"] == large_order