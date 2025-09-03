"""
Tests for retrieving residential properties via the API.
Tests property retrieval with residential-specific type details.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from Backend.api.properties.schemas.property import PropertyDetailResponse, OwnerResponse
from Backend.api.properties.schemas.types.residential import ResidentialPropertyDetailsResponse
from ..base_test import (
    BasePropertyTest,
    create_test_property,
    create_test_unit,
    create_test_user
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestResidentialPropertyGet(BasePropertyTest):
    """Test residential property GET endpoints."""
    
    def create_property_response(self, property_id, name, type_details=None, units=None, stats=None):
        """Helper to create a proper property response."""
        return {
            "id": property_id,
            "name": name,
            "address": "123 Test St",
            "city": "Test City",
            "province": "TC",
            "postal_code": "12345",
            "property_type": PropertyType.RESIDENTIAL.value,
            "description": "Test property",
            "year_built": 2020,
            "status": PropertyStatus.ACTIVE.value,
            "type_specific_details": type_details,
            "user_id": self.mock_user.id,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "owner": {
                "id": self.mock_user.id,
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com"
            },
            "units": units or [],
            "stats": stats
        }
    
    @pytest.mark.asyncio
    async def test_get_residential_property_success(self):
        """Test successful retrieval of a residential property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        mock_property = create_test_property(
            property_id=property_id,
            user_id=self.mock_user.id,
            property_type=PropertyType.RESIDENTIAL,
            name="Family Home"
        )
        mock_property.owner = self.mock_user
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_property
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Family Home"
            assert data["property_type"] == PropertyType.RESIDENTIAL.value
    
    @pytest.mark.asyncio
    async def test_get_single_family_home_details(self):
        """Test retrieving single family home with type-specific details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        mock_property = create_test_property(
            property_id=property_id,
            user_id=self.mock_user.id,
            property_type=PropertyType.RESIDENTIAL,
            name="Suburban House"
        )
        mock_property.owner = self.mock_user
        
        type_details = {
            "property_type": "Residential",  # Discriminator field
            "property_subtype": "single_family",
            "bedrooms": 4,
            "bathrooms": Decimal("3.5"),
            "square_feet": 2500,
            "lot_size": 8000,
            "stories": 2,
            "garage_spaces": 2,
            "has_driveway": True,
            "heating_type": "forced_air",
            "cooling_type": "central_air"
        }
        
        mock_response = self.create_property_response(
            property_id=property_id,
            name="Suburban House",
            type_details=type_details
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["type_specific_details"]["property_subtype"] == "single_family"
            assert data["type_specific_details"]["bedrooms"] == 4
            assert data["type_specific_details"]["has_driveway"] is True
    
    @pytest.mark.asyncio
    async def test_get_condo_with_amenities(self):
        """Test retrieving condo with building amenities."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        mock_property = create_test_property(
            property_id=property_id,
            user_id=self.mock_user.id,
            property_type=PropertyType.RESIDENTIAL,
            name="Luxury Condo"
        )
        mock_property.owner = self.mock_user
        
        type_details = {
            "property_type": "Residential",  # Discriminator field
            "property_subtype": "condo",
            "bedrooms": 2,
            "bathrooms": Decimal("2.0"),
            "square_feet": 1200,
            "stories": 1,
            "garage_spaces": 1,
            "heating_type": "forced_air",
            "cooling_type": "central_air"
        }
        
        mock_response = self.create_property_response(
            property_id=property_id,
            name="Luxury Condo",
            type_details=type_details
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["type_specific_details"]["property_subtype"] == "condo"
    
    @pytest.mark.asyncio
    async def test_get_residential_with_rental_info(self):
        """Test retrieving residential property with rental information."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        mock_property = create_test_property(
            property_id=property_id,
            user_id=self.mock_user.id,
            property_type=PropertyType.RESIDENTIAL
        )
        mock_property.owner = self.mock_user
        
        type_details = {
            "property_type": "Residential",  # Discriminator field
            "property_subtype": "townhouse",
            "bedrooms": 3,
            "bathrooms": Decimal("2.5"),
            "square_feet": 1800,
            "lot_size": 3000,
            "stories": 2,
            "garage_spaces": 1,
            "has_driveway": True,
            "street_parking": False,
            "heating_type": "forced_air",
            "cooling_type": "central_air",
        }
        
        mock_response = self.create_property_response(
            property_id=property_id,
            name="Test Property",
            type_details=type_details
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["type_specific_details"]["property_subtype"] == "townhouse"
            assert data["type_specific_details"]["bedrooms"] == 3
            assert float(data["type_specific_details"]["bathrooms"]) == 2.5
            assert data["type_specific_details"]["square_feet"] == 1800
            assert data["type_specific_details"]["has_driveway"] is True
    
    @pytest.mark.asyncio
    async def test_get_residential_properties_list(self):
        """Test retrieving list of residential properties."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        mock_properties = [
            create_test_property(
                property_id=1,
                user_id=self.mock_user.id,
                property_type=PropertyType.RESIDENTIAL,
                name="House A"
            ),
            create_test_property(
                property_id=2,
                user_id=self.mock_user.id,
                property_type=PropertyType.RESIDENTIAL,
                name="Condo B"
            ),
            create_test_property(
                property_id=3,
                user_id=self.mock_user.id,
                property_type=PropertyType.RESIDENTIAL,
                name="Townhouse C"
            )
        ]
        
        with patch("Backend.api.properties.service.PropertyService.get_properties") as mock_get:
            mock_get.return_value = mock_properties
            
            response = self.client.get(
                "/api/properties/",
                params={"property_type": PropertyType.RESIDENTIAL.value}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert all(p["property_type"] == PropertyType.RESIDENTIAL.value for p in data)
    
    @pytest.mark.asyncio
    async def test_get_residential_forbidden_non_owner(self):
        """Test that non-owners cannot retrieve residential properties."""
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
    async def test_get_residential_not_found(self):
        """Test retrieving non-existent residential property."""
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
