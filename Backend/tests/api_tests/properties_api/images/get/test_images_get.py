"""
Tests for property image GET endpoints.
Tests retrieval of property images with proper authorization.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch
from datetime import datetime

from Backend.models.property import PropertyType, PropertyImage
from Backend.models.enums import PropertyStatus
from Backend.api.properties.schemas import PropertyDetailResponse, OwnerResponse
from ...base_test import BasePropertyTest

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


class TestPropertyImagesGet(BasePropertyTest):
    """Test property image GET endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_property_images_success(self):
        """Test successful retrieval of property images."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create mock images
        mock_images = [
            create_test_image(image_id=1, property_id=property_id, is_primary=True, display_order=0),
            create_test_image(image_id=2, property_id=property_id, display_order=1),
            create_test_image(image_id=3, property_id=property_id, display_order=2)
        ]
        
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
             patch("Backend.api.properties.image_service.PropertyImageService.get_property_images") as mock_get_images:
            
            mock_get_property.return_value = mock_property
            mock_get_images.return_value = mock_images
            
            response = self.client.get(f"/api/properties/{property_id}/images")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert data[0]["id"] == 1
            assert data[0]["is_primary"] is True
            assert data[0]["display_order"] == 0
            assert data[1]["id"] == 2
            assert data[1]["is_primary"] is False
            assert data[1]["display_order"] == 1
            
            mock_get_property.assert_called_once_with(property_id, self.mock_user, mock_session)
            mock_get_images.assert_called_once_with(mock_session, property_id)
    
    @pytest.mark.asyncio
    async def test_get_property_images_empty_list(self):
        """Test retrieval when property has no images."""
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
             patch("Backend.api.properties.image_service.PropertyImageService.get_property_images") as mock_get_images:
            
            mock_get_property.return_value = mock_property
            mock_get_images.return_value = []
            
            response = self.client.get(f"/api/properties/{property_id}/images")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 0
            assert data == []
            
            mock_get_property.assert_called_once_with(property_id, self.mock_user, mock_session)
            mock_get_images.assert_called_once_with(mock_session, property_id)
    
    @pytest.mark.asyncio
    async def test_get_property_images_property_not_found(self):
        """Test get images when property doesn't exist."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 999
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=404,
                detail="Property not found"
            )
            
            response = self.client.get(f"/api/properties/{property_id}/images")
            
            assert response.status_code == 404
            assert response.json()["detail"] == "Property not found"
            
            mock_get_property.assert_called_once_with(property_id, self.mock_user, mock_session)
    
    @pytest.mark.asyncio
    async def test_get_property_images_unauthorized_user(self):
        """Test get images when user doesn't own the property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=403,
                detail="You don't have permission to access this property"
            )
            
            response = self.client.get(f"/api/properties/{property_id}/images")
            
            assert response.status_code == 403
            assert response.json()["detail"] == "You don't have permission to access this property"
            
            mock_get_property.assert_called_once_with(property_id, self.mock_user, mock_session)
    
    @pytest.mark.asyncio
    async def test_get_property_images_with_ordering(self):
        """Test that images are returned in correct display order."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create mock images with specific ordering
        mock_images = [
            create_test_image(image_id=1, property_id=property_id, display_order=5),
            create_test_image(image_id=2, property_id=property_id, display_order=0, is_primary=True),
            create_test_image(image_id=3, property_id=property_id, display_order=10)
        ]
        
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
             patch("Backend.api.properties.image_service.PropertyImageService.get_property_images") as mock_get_images:
            
            mock_get_property.return_value = mock_property
            mock_get_images.return_value = mock_images
            
            response = self.client.get(f"/api/properties/{property_id}/images")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            
            # Verify the order is preserved as returned by the service
            assert data[0]["id"] == 1
            assert data[0]["display_order"] == 5
            assert data[1]["id"] == 2
            assert data[1]["display_order"] == 0
            assert data[1]["is_primary"] is True
            assert data[2]["id"] == 3
            assert data[2]["display_order"] == 10
