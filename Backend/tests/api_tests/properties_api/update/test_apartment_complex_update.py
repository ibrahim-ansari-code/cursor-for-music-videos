"""
Tests for updating apartment complex properties via the API.
Tests property updates with apartment complex-specific type details.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch
from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus

from ..base_test import BasePropertyTest


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestApartmentComplexPropertyUpdate(BasePropertyTest):
    """Test apartment complex property UPDATE endpoints."""
    
    @pytest.mark.asyncio
    async def test_update_apartment_complex_success(self):
        """Test successful update of an apartment complex property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create update data
        update_data = {
            "name": "Updated Maple Ridge",
            "description": "Newly renovated apartment complex",
            "type_specific_details": {
                "property_type": "Apartment Complex",  # Discriminator field
                "complex_style": "garden",  # Required field
                "total_units": 50,
                "number_of_buildings": 3,
                "parking_spaces_total": 75,
                "on_site_management": True
            }
        }
        
        # Create dict response for consistency - avoid Pydantic typing issues
        type_details = {            
            "property_type": "Apartment Complex",  # Discriminator field
            "complex_style": "garden",  # Required field
            "total_units": 50,
            "number_of_buildings": 3,
            "parking_spaces_total": 75,
            "on_site_management": True,
            "shared_amenities": ["gym", "pool"],
            "assigned_property_manager": "John Smith",
            "security_system_type": "24/7 monitored",
            "security_system_details": "Card access and CCTV",
            "trash_system_type": "chute",
            "trash_collection_schedule": "Daily",
            "property_management_company": "Test Management Co",
            "management_office_location": "Building A, Suite 100",
            "vacancy_rate": 10.0,
            "management_contact_phone": "123-456-7890",
            "management_contact_email": "test@example.com",
            "trash_system_details": "Daily trash collection",
            "pet_policy": "Cats and dogs under 50lbs allowed with deposit",
            "utilities_included": ["water", "trash", "sewer"],
            "average_rent_by_type": {"studio": "1200.00", "1br": "1500.00", "2br": "2000.00"}
        }
        
        # Create dict response for consistency
        updated_property = {
            "id": property_id,
            "name": "Updated Maple Ridge",
            "address": "123 Test St",
            "city": "Test City",
            "province": "TC",
            "postal_code": "12345",
            "property_type": PropertyType.APARTMENT_COMPLEX.value,
            "description": "Newly renovated apartment complex",
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
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Maple Ridge"
            assert data["description"] == "Newly renovated apartment complex"
    
    @pytest.mark.asyncio
    async def test_update_apartment_complex_type_details_only(self):
        """Test updating only type-specific details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Update only type-specific details
        update_data = {
            "type_specific_details": {
                "property_type": "Apartment Complex",  # Discriminator field
                "complex_style": "garden",  # Required field
                "total_units": 50,  # Required field
                "shared_amenities": ["gym", "pool", "sauna", "playground"],
                "pet_policy": "cats_and_dogs",
                "parking_ratio": 1.5,
                "unit_mix": {
                    "studio": 10,
                    "1br": 20,
                    "2br": 15,
                    "3br": 5
                }
            }
        }
        
        # Create dict response for consistency - avoid Pydantic typing issues
        type_details = {
            "property_type": "Apartment Complex",  # Discriminator field
            "complex_style": "garden",  # Required field
            "total_units": 50,
            "shared_amenities": ["gym", "pool", "sauna", "playground"],
            "pet_policy": "cats_and_dogs",
            "unit_mix": {
                "studio": 10,
                "1br": 20,
                "2br": 15,
                "3br": 5
            },
            "assigned_property_manager": "John Smith",
            "security_system_type": "24/7 monitored",
            "security_system_details": "Card access and CCTV",
            "trash_system_type": "chute",
            "trash_collection_schedule": "Daily",
            "property_management_company": "Test Management Co",
            "management_office_location": "Building A, Suite 100",
            "vacancy_rate": 10.0,
            "management_contact_phone": "123-456-7890",
            "management_contact_email": "test@example.com",
            "trash_system_details": "Daily trash collection",
            "parking_spaces_total": 75
        }
        
        # Create dict response for consistency
        updated_property = {
            "id": property_id,
            "name": "Maple Ridge",
            "address": "123 Test St",
            "city": "Test City",
            "province": "TC",
            "postal_code": "12345",
            "property_type": PropertyType.APARTMENT_COMPLEX.value,
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
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "sauna" in data["type_specific_details"]["shared_amenities"]
            assert data["type_specific_details"]["pet_policy"] == "cats_and_dogs"
    
    @pytest.mark.asyncio
    async def test_update_apartment_complex_not_found(self):
        """Test updating non-existent apartment complex."""
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
    async def test_update_apartment_complex_forbidden_non_owner(self):
        """Test that non-owners cannot update apartment complex properties."""
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
    async def test_update_apartment_complex_validation_error(self):
        """Test update with invalid data."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Invalid data - unit distribution exceeds total
        update_data = {
            "type_specific_details": {
                "property_type": "Apartment Complex",  # Discriminator field
                "complex_style": "garden",  # Required field
                "total_units": 10,
                "unit_mix": {
                    "studio": 5,
                    "1br": 10,  # This would exceed total
                    "2br": 5
                }
            }
        }
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.side_effect = HTTPException(
                status_code=422,
                detail="Unit distribution sum exceeds total units"
            )
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_update_apartment_complex_partial_update(self):
        """Test partial update of apartment complex."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Only update description
        update_data = {
            "description": "Premium apartment complex with modern amenities"
        }
        
        # Create dict response for consistency
        updated_property = {
            "id": property_id,
            "name": "Maple Ridge",
            "address": "123 Test St",
            "city": "Test City",
            "province": "TC",
            "postal_code": "12345",
            "property_type": PropertyType.APARTMENT_COMPLEX.value,
            "description": "Premium apartment complex with modern amenities",
            "year_built": 2020,
            "status": PropertyStatus.ACTIVE.value,
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
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["description"] == "Premium apartment complex with modern amenities"
            assert data["name"] == "Maple Ridge"  # Unchanged
