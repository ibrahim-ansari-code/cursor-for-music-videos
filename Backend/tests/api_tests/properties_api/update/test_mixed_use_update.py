"""
Tests for updating mixed-use properties via the API.
Tests property updates with mixed-use-specific type details.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch
from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from ..base_test import BasePropertyTest


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestMixedUsePropertyUpdate(BasePropertyTest):
    """Test mixed-use property UPDATE endpoints."""
    
    def create_property_response(self, property_id, name, type_details=None, units=None, stats=None):
        """Helper to create a proper property response."""
        return {
            "id": property_id,
            "name": name,
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
            "units": units or [],
            "stats": stats
        }
    
    @pytest.mark.asyncio
    async def test_update_mixed_use_success(self):
        """Test successful update of a mixed-use property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create update data
        update_data = {
            "name": "Updated Urban Living Center",
            "description": "Modern mixed-use development with enhanced amenities",
            "type_specific_details": {
                "residential_square_feet": 60000,
                "commercial_square_feet": 18000,
                "residential_units_count": 48,
                "commercial_units_count": 6,
                "residential_unit_types": {
                    "studio": 12,
                    "1br": 24,
                    "2br": 12
                },
                "commercial_space_types": ["retail", "restaurant", "office"],
                "parking_spaces_total": 80,
                "shared_amenities": ["gym", "rooftop_deck", "concierge"]
            }
        }
        
        # Use helper function to create response
        type_details = {
            "residential_square_feet": 60000,
            "commercial_square_feet": 18000,
            "residential_units_count": 48,
            "commercial_units_count": 6,
            "residential_unit_types": {
                "studio": 12,
                "1br": 24,
                "2br": 12
            },
            "commercial_space_types": ["retail", "restaurant", "office"],
            "parking_spaces_total": 80,
            "shared_amenities": ["gym", "rooftop_deck", "concierge"],
            "separate_entrances": True,
            "shared_parking": True,
            "single_management_company": True
        }
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Updated Urban Living Center",
            type_details=type_details,
            units=[]
        )
        updated_property["description"] = "Modern mixed-use development with enhanced amenities"
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Urban Living Center"
            assert data["description"] == "Modern mixed-use development with enhanced amenities"
            assert data["type_specific_details"]["residential_units_count"] == 48
    
    @pytest.mark.asyncio
    async def test_update_mixed_use_type_details_only(self):
        """Test updating only type-specific details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Update only type-specific details
        update_data = {
            "type_specific_details": {
                "shared_amenities": ["gym", "pool", "business_center", "rooftop_deck", "concierge"],
                "separate_entrances": False,
                "shared_parking": False,
                "management_structure": "Separate management for residential and commercial components",
                "single_management_company": False,
                "zoning_designation": "MU-3"
            }
        }
        
        # Use helper function to create response
        type_details = {
            "residential_square_feet": 50000,
            "commercial_square_feet": 15000,
            "residential_units_count": 40,
            "commercial_units_count": 5,
            "shared_amenities": ["gym", "pool", "business_center", "rooftop_deck", "concierge"],
            "separate_entrances": False,
            "shared_parking": False,
            "management_structure": "Separate management for residential and commercial components",
            "single_management_company": False,
            "zoning_designation": "MU-3",
            "parking_spaces_total": 80
        }
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Urban Living Center",
            type_details=type_details,
            units=[]
        )
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "concierge" in data["type_specific_details"]["shared_amenities"]
            assert data["type_specific_details"]["separate_entrances"] is False
            assert data["type_specific_details"]["zoning_designation"] == "MU-3"
    
    @pytest.mark.asyncio
    async def test_update_mixed_use_not_found(self):
        """Test updating non-existent mixed-use property."""
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
    async def test_update_mixed_use_forbidden_non_owner(self):
        """Test that non-owners cannot update mixed-use properties."""
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
    async def test_update_mixed_use_validation_error(self):
        """Test update with invalid data."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Invalid data - unit types exceed total count
        update_data = {
            "type_specific_details": {
                "residential_units_count": 20,
                "residential_unit_types": {
                    "studio": 10,
                    "1br": 15,  # Total would be 25, exceeds count of 20
                    "2br": 10
                }
            }
        }
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.side_effect = HTTPException(
                status_code=422,
                detail="Sum of residential unit types exceeds total residential units"
            )
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_update_mixed_use_partial_update(self):
        """Test partial update of mixed-use property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Only update description
        update_data = {
            "description": "Luxury mixed-use development in prime downtown location"
        }
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Urban Living Center",
            type_details=None,
            units=[]
        )
        updated_property["description"] = "Luxury mixed-use development in prime downtown location"
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["description"] == "Luxury mixed-use development in prime downtown location"
            assert data["name"] == "Urban Living Center"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_mixed_use_admin_can_update_any(self):
        """Test that admin users can update any mixed-use property."""
        mock_session = AsyncMock()
        
        # Set up admin user
        self.mock_user.is_admin = True
        self.setup_mocks(mock_session)
        
        property_id = 1
        update_data = {
            "name": "Admin Updated Development",
            "type_specific_details": {
                "residential_square_feet": 80000,
                "commercial_square_feet": 25000,
                "residential_units_count": 65,
                "commercial_units_count": 8
            }
        }
        
        type_details = {
            "residential_square_feet": 80000,
            "commercial_square_feet": 25000,
            "residential_units_count": 65,
            "commercial_units_count": 8
        }
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Admin Updated Development",
            type_details=type_details,
            units=[]
        )
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Admin Updated Development"
            assert data["type_specific_details"]["residential_units_count"] == 65