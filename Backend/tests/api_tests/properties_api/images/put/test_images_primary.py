"""
Tests for property image set primary PUT endpoint.
Tests setting primary image functionality with proper authorization.
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


class TestPropertyImageSetPrimary(BasePropertyTest):
    """Test property image set primary endpoint."""
    
    @pytest.mark.asyncio
    async def test_set_primary_image_success(self):
        """Test successful setting of primary image."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        image_id = 2
        
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
        
        # Create mock updated primary image
        mock_primary_image = create_test_image(
            image_id=image_id, 
            property_id=property_id, 
            is_primary=True
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.set_primary_image") as mock_set_primary:
            
            mock_get_property.return_value = mock_property
            mock_set_primary.return_value = mock_primary_image
            
            response = self.client.put(f"/api/properties/{property_id}/images/{image_id}/primary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == image_id
            assert data["property_id"] == property_id
            assert data["is_primary"] is True
            
            mock_get_property.assert_called_once_with(property_id, self.mock_user, mock_session)
            mock_set_primary.assert_called_once_with(mock_session, property_id, image_id)
    
    @pytest.mark.asyncio
    async def test_set_primary_image_property_not_found(self):
        """Test set primary when property doesn't exist."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 999
        image_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=404,
                detail="Property not found or you don't have access"
            )
            
            response = self.client.put(f"/api/properties/{property_id}/images/{image_id}/primary")
            
            assert response.status_code == 404
            assert response.json()["detail"] == "Property not found or you don't have access"
    
    @pytest.mark.asyncio
    async def test_set_primary_image_unauthorized(self):
        """Test set primary when user doesn't own property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        image_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=403,
                detail="Property not found or you don't have access"
            )
            
            response = self.client.put(f"/api/properties/{property_id}/images/{image_id}/primary")
            
            assert response.status_code == 403
            assert response.json()["detail"] == "Property not found or you don't have access"
    
    @pytest.mark.asyncio
    async def test_set_primary_image_image_not_found(self):
        """Test set primary when image doesn't exist."""
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
             patch("Backend.api.properties.image_service.PropertyImageService.set_primary_image") as mock_set_primary:
            
            mock_get_property.return_value = mock_property
            mock_set_primary.side_effect = ValueError(f"Image {image_id} not found for property {property_id}")
            
            response = self.client.put(f"/api/properties/{property_id}/images/{image_id}/primary")
            
            # Should return 404 when image not found (ValueError becomes 404)
            assert response.status_code == 404
            assert f"Image {image_id} not found for property {property_id}" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_set_primary_image_replace_existing_primary(self):
        """Test setting primary image when another image is already primary."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        old_primary_id = 1
        new_primary_id = 2
        
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
        
        # Create mock new primary image
        mock_new_primary_image = create_test_image(
            image_id=new_primary_id, 
            property_id=property_id, 
            is_primary=True
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.set_primary_image") as mock_set_primary:
            
            mock_get_property.return_value = mock_property
            mock_set_primary.return_value = mock_new_primary_image
            
            response = self.client.put(f"/api/properties/{property_id}/images/{new_primary_id}/primary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == new_primary_id
            assert data["is_primary"] is True
            
            # Verify the service method was called to handle primary switching
            mock_set_primary.assert_called_once_with(mock_session, property_id, new_primary_id)
    
    @pytest.mark.asyncio
    async def test_set_primary_image_already_primary(self):
        """Test setting an image as primary when it's already primary."""
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
        
        # Create mock image that's already primary
        mock_already_primary_image = create_test_image(
            image_id=image_id, 
            property_id=property_id, 
            is_primary=True
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property, \
             patch("Backend.api.properties.image_service.PropertyImageService.set_primary_image") as mock_set_primary:
            
            mock_get_property.return_value = mock_property
            mock_set_primary.return_value = mock_already_primary_image
            
            response = self.client.put(f"/api/properties/{property_id}/images/{image_id}/primary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == image_id
            assert data["is_primary"] is True
            
            # Service should still be called even if already primary (idempotent operation)
            mock_set_primary.assert_called_once_with(mock_session, property_id, image_id)
    
    @pytest.mark.asyncio
    async def test_set_primary_image_database_error(self):
        """Test handling of database errors during set primary."""
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
             patch("Backend.api.properties.image_service.PropertyImageService.set_primary_image") as mock_set_primary:
            
            mock_get_property.return_value = mock_property
            mock_set_primary.side_effect = Exception("Database connection error")
            
            response = self.client.put(f"/api/properties/{property_id}/images/{image_id}/primary")
            
            # Should return 500 with proper error message
            assert response.status_code == 500
            assert response.json()["detail"] == "Failed to set primary image"
    
    @pytest.mark.asyncio
    async def test_set_primary_image_invalid_image_id(self):
        """Test set primary with invalid image ID."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        invalid_image_id = "invalid"
        
        response = self.client.put(f"/api/properties/{property_id}/images/{invalid_image_id}/primary")
        
        # Should return 422 due to validation error
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_set_primary_image_invalid_property_id(self):
        """Test set primary with invalid property ID."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        invalid_property_id = "invalid"
        image_id = 1
        
        response = self.client.put(f"/api/properties/{invalid_property_id}/images/{image_id}/primary")
        
        # Should return 422 due to validation error
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_set_primary_image_zero_ids(self):
        """Test set primary with zero IDs."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 0
        image_id = 0
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=404,
                detail="Property not found"
            )
            
            response = self.client.put(f"/api/properties/{property_id}/images/{image_id}/primary")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_set_primary_image_negative_ids(self):
        """Test set primary with negative IDs."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = -1
        image_id = -1
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=404,
                detail="Property not found"
            )
            
            response = self.client.put(f"/api/properties/{property_id}/images/{image_id}/primary")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_set_primary_image_large_ids(self):
        """Test set primary with very large IDs."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 999999999
        image_id = 999999999
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get_property:
            mock_get_property.side_effect = HTTPException(
                status_code=404,
                detail="Property not found"
            )
            
            response = self.client.put(f"/api/properties/{property_id}/images/{image_id}/primary")
            
            assert response.status_code == 404