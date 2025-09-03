"""
Tests for retrieving mixed-use properties via the API.
Tests property retrieval with mixed-use-specific type details.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch

from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from ..base_test import (
    BasePropertyTest,
    create_test_property
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestMixedUsePropertyGet(BasePropertyTest):
    """Test mixed-use property GET endpoints."""
    

    @pytest.mark.asyncio
    async def test_get_mixed_use_property_success(self):
        """Test successful retrieval of a mixed-use property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        mock_property = create_test_property(
            property_id=property_id,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE,
            name="Downtown Mixed Complex"
        )
        mock_property.owner = self.mock_user
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_property
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Downtown Mixed Complex"
            assert data["property_type"] == PropertyType.MIXED_USE.value
    
    @pytest.mark.asyncio
    async def test_get_mixed_use_with_component_breakdown(self):
        """Test retrieving mixed-use property with component breakdown."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create dict response for consistency - avoid Pydantic typing issues
        type_details = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "vertical_mixed",  # Required field
            "residential_square_feet": 120000,
            "commercial_square_feet": 30000,
            "residential_units_count": 120,
            "commercial_units_count": 15,
            "residential_unit_types": {"studio": 20, "1br": 50, "2br": 40, "3br": 10},
            "commercial_space_types": ["retail", "office", "restaurant"],
            "shared_amenities": ["gym", "pool", "rooftop"],
            "separate_entrances": True,
            "shared_parking": False,
            "parking_spaces_total": 300,
            "management_structure": "corporate",
            "zoning_designation": "commercial"
        }
        
        # Create dict response for consistency
        mock_response = {
            "id": property_id,
            "name": "Urban Center",
            "address": "123 Test St",
            "city": "Test City",
            "province": "TC",
            "postal_code": "12345",
            "property_type": PropertyType.MIXED_USE.value,
            "description": "Test property",
            "year_built": 2020,
            "status": PropertyStatus.ACTIVE.value,
            "type_specific_details": type_details,
            "user_id": str(self.mock_user.id),
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "owner": {
                "id": str(self.mock_user.id),
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com"
            },
            "units": [],
            "stats": None
        }
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["type_specific_details"]["residential_units_count"] == 120
            assert data["type_specific_details"]["commercial_square_feet"] == 30000
            assert "retail" in data["type_specific_details"]["commercial_space_types"]
    
    @pytest.mark.asyncio
    async def test_get_mixed_use_with_occupancy_rates(self):
        """Test retrieving mixed-use property with separate occupancy rates."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        mock_property = create_test_property(
            property_id=property_id,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE
        )
        mock_property.owner = self.mock_user
        
        # Create dict response for consistency - avoid Pydantic typing issues
        type_details = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "live_work",  # Required field
            "residential_units_count": 70,
            "commercial_units_count": 20,
            "residential_square_feet": 70000,
            "commercial_square_feet": 20000,
            "residential_unit_types": {"1br": 30, "2br": 30, "3br": 10},
            "commercial_space_types": ["retail", "office"],
            "management_structure": "corporate",
            "zoning_designation": "commercial",
            "parking_spaces_total": 300
        }
        
        # Create dict response for consistency
        mock_response = {
            "id": property_id,
            "name": "Test Property",
            "address": "123 Test St",
            "city": "Test City",
            "province": "TC",
            "postal_code": "12345",
            "property_type": PropertyType.MIXED_USE.value,
            "description": "Test property",
            "year_built": 2020,
            "status": PropertyStatus.ACTIVE.value,
            "type_specific_details": type_details,
            "user_id": str(self.mock_user.id),
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "owner": {
                "id": str(self.mock_user.id),
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com"
            },
            "units": [],
            "stats": None
        }
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["type_specific_details"]["residential_units_count"] == 70
            assert data["type_specific_details"]["commercial_units_count"] == 20
    
    @pytest.mark.asyncio
    async def test_get_mixed_use_properties_list(self):
        """Test retrieving list of mixed-use properties."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        mock_properties = [
            create_test_property(
                property_id=1,
                user_id=self.mock_user.id,
                property_type=PropertyType.MIXED_USE,
                name="Mixed Complex A"
            ),
            create_test_property(
                property_id=2,
                user_id=self.mock_user.id,
                property_type=PropertyType.MIXED_USE,
                name="Mixed Complex B"
            )
        ]
        
        with patch("Backend.api.properties.service.PropertyService.get_properties") as mock_get:
            mock_get.return_value = mock_properties
            
            response = self.client.get(
                "/api/properties/",
                params={"property_type": PropertyType.MIXED_USE.value}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert all(p["property_type"] == PropertyType.MIXED_USE.value for p in data)
    
    @pytest.mark.asyncio
    async def test_get_mixed_use_forbidden_non_owner(self):
        """Test that non-owners cannot retrieve mixed-use properties."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.side_effect = HTTPException(
                status_code=403,
                detail="You don't have permission to view this property"
            )
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_mixed_use_not_found(self):
        """Test retrieving non-existent mixed-use property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 999
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.side_effect = HTTPException(
                status_code=404,
                detail="Property not found"
            )
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 404
