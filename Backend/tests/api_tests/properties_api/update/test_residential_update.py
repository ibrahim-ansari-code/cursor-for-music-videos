"""
Tests for updating residential properties via the API.
Tests property updates with residential-specific type details.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from decimal import Decimal

from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus   
from Backend.api.properties.schemas.types.residential import ResidentialPropertyDetailsResponse
from ..base_test import BasePropertyTest


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestResidentialPropertyUpdate(BasePropertyTest):
    """Test residential property UPDATE endpoints."""
    
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
            "user_id": str(self.mock_user.id),
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "owner": {
                "id": str(self.mock_user.id),
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com"
            },
            "units": units or [],
            "stats": stats
        }
    
    @pytest.mark.asyncio
    async def test_update_residential_success(self):
        """Test successful update of a residential property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create update data
        update_data = {
            "name": "Updated Family Home",
            "description": "Beautifully renovated single-family home",
            "type_specific_details": {
                "property_type": "Residential",  # Discriminator field
                "bedrooms": 4,
                "bathrooms": 3.5,
                "square_feet": 2800,
                "lot_size": 8500,
                "stories": 2,
                "garage_spaces": 3,
                "has_driveway": True,
                "street_parking": False,
                "property_subtype": "single_family",
                "heating_type": "forced_air",
                "cooling_type": "central_air"
            }
        }
        
        # Use helper function to create response
        type_details = {
            "property_type": "Residential",  # Discriminator field
            "bedrooms": 4,
            "bathrooms": 3.5,
            "square_feet": 2800,
            "lot_size": 8500,
            "stories": 2,
            "garage_spaces": 3,
            "has_driveway": True,
            "street_parking": False,
            "property_subtype": "single_family",
            "heating_type": "forced_air",
            "cooling_type": "central_air"
        }
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Updated Family Home",
            type_details=type_details,
            units=[]
        )
        updated_property["description"] = "Beautifully renovated single-family home"
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Family Home"
            assert data["description"] == "Beautifully renovated single-family home"
            assert data["type_specific_details"]["bedrooms"] == 4
            assert data["type_specific_details"]["has_driveway"] is True
    
    @pytest.mark.asyncio
    async def test_update_residential_type_details_only(self):
        """Test updating only type-specific details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Update only type-specific details
        update_data = {
            "type_specific_details": {
                "property_type": "Residential",  # Discriminator field
                "bedrooms": 3,  # Required field
                "bathrooms": 2.5,  # Required field
                "roof_type": "metal",
                "exterior_material": "stone",
                "water_heater_type": "tankless",
                "street_parking": True
            }
        }
        
        # Use helper function to create response
        type_details = {
            "property_type": "Residential",  # Discriminator field
            "bedrooms": 3,
            "bathrooms": 2.5,
            "square_feet": 2000,
            "roof_type": "metal",
            "exterior_material": "stone",
            "water_heater_type": "tankless",
            "street_parking": True,
            "heating_type": "forced_air",
            "cooling_type": "central_air",
            "lot_size": 8500,
            "property_subtype": "single_family"
        }
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Family Home",
            type_details=type_details,
            units=[]
        )
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["type_specific_details"]["roof_type"] == "metal"
            assert data["type_specific_details"]["exterior_material"] == "stone"
            assert data["type_specific_details"]["water_heater_type"] == "tankless"
            assert data["type_specific_details"]["street_parking"] is True
    
    @pytest.mark.asyncio
    async def test_update_residential_not_found(self):
        """Test updating non-existent residential property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 999
        update_data = {"name": "New Name"}
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.side_effect = HTTPException(
                status_code=404,
                detail="Property not found"
            )
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_residential_forbidden_non_owner(self):
        """Test that non-owners cannot update residential properties."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        update_data = {"name": "Unauthorized Update"}
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.side_effect = HTTPException(
                status_code=403,
                detail="You don't have permission to update this property"
            )
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_update_residential_validation_error(self):
        """Test update with invalid data."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Invalid data - bathrooms not in 0.5 increments
        update_data = {
            "type_specific_details": {
                "property_type": "Residential",  # Discriminator field
                "bedrooms": 3,
                "bathrooms": 2.3,  # Invalid - not in 0.5 increments
                "square_feet": 2000
            }
        }
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.side_effect = HTTPException(
                status_code=422,
                detail="Bathrooms must be in 0.5 increments (e.g., 1, 1.5, 2, 2.5)"
            )
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_update_residential_partial_update(self):
        """Test partial update of residential property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Only update description
        update_data = {
            "description": "Charming home in quiet neighborhood with excellent schools"
        }
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Family Home",
            units=[]
        )
        updated_property.update({
            "address": "123 Residential St",
            "city": "Family City",
            "province": "FC",
            "postal_code": "98765",
            "description": "Charming home in quiet neighborhood with excellent schools",
            "year_built": 2019
        })
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["description"] == "Charming home in quiet neighborhood with excellent schools"
            assert data["name"] == "Family Home"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_residential_admin_can_update_any(self):
        """Test that admin users can update any residential property."""
        mock_session = AsyncMock()
        
        # Set up admin user
        self.mock_user.is_admin = True
        self.setup_mocks(mock_session)
        
        property_id = 1
        update_data = {
            "name": "Admin Updated Home",
            "type_specific_details": {
                "property_type": "Residential",  # Discriminator field
                "bedrooms": 5,
                "bathrooms": "4.0",
                "square_feet": 3500,
                "property_subtype": "townhouse"
            }
        }
        
        type_details = ResidentialPropertyDetailsResponse(
            bedrooms=5,
            bathrooms=Decimal("4.0"),
            square_feet=3500,
            lot_size=8500,
            heating_type="forced_air",
            cooling_type="central_air",
            water_heater_type="tankless",
            roof_type="metal",
            exterior_material="stone",
            property_subtype="townhouse"
        )
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Admin Updated Home",
            type_details=type_details,
            units=[]
        )
        updated_property.update({
            "address": "123 Residential St",
            "city": "Family City",
            "province": "FC",
            "postal_code": "98765",
            "year_built": 2019,
            "owner": {
                "id": str(uuid4()),
                "first_name": "Other",
                "last_name": "Owner",
                "email": "other@example.com"
            }
        })
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Admin Updated Home"
            assert data["type_specific_details"]["bedrooms"] == 5
            assert data["type_specific_details"]["property_subtype"] == "townhouse"