"""
Tests for updating industrial properties via the API.
Tests property updates with industrial-specific type details.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch

from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from ..base_test import BasePropertyTest


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestIndustrialPropertyUpdate(BasePropertyTest):
    """Test industrial property UPDATE endpoints."""
    
    def create_property_response(self, property_id, name, type_details=None, units=None, stats=None):
        """Helper to create a proper property response."""
        return {
            "id": property_id,
            "name": name,
            "address": "123 Test St",
            "city": "Test City",
            "province": "TC",
            "postal_code": "12345",
            "property_type": PropertyType.INDUSTRIAL.value,
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
    async def test_update_industrial_success(self):
        """Test successful update of an industrial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create update data
        update_data = {
            "name": "Updated Distribution Center",
            "description": "Modern warehouse facility with expanded loading docks",
            "type_specific_details": {
                "total_square_feet": 120000,
                "warehouse_square_feet": 100000,
                "office_square_feet": 15000,
                "manufacturing_square_feet": 5000,
                "clear_height": 36.0,
                "loading_docks_count": 15,
                "drive_in_doors_count": 3,
                "rail_access": True,
                "truck_court_size": 20000
            }
        }
        
        # Use helper function to create response
        type_details = {
            "total_square_feet": 120000,
            "warehouse_square_feet": 100000,
            "office_square_feet": 15000,
            "manufacturing_square_feet": 5000,
            "clear_height": 36.0,
            "loading_docks_count": 15,
            "drive_in_doors_count": 3,
            "rail_access": True,
            "truck_court_size": 20000,
            "power_capacity": "3000 amps",
            "power_voltage": "480V 3-phase",
            "has_crane": True,
            "crane_capacity": "15 ton",
            "sprinkler_system_type": "ESFR",
            "environmental_compliance": {
                "phase_1_completed": True,
                "phase_2_completed": True,
                "last_inspection": "2024-01-15"
            },
            "hazmat_storage_permitted": True,
            "zoning_classification": "M-3",
            "permitted_uses": ["warehouse", "distribution", "light_industrial"]
        }
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Updated Distribution Center",
            type_details=type_details,
            units=[]
        )
        # Override description to match update_data
        updated_property["description"] = "Modern warehouse facility with expanded loading docks"
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            
            # Test basic property updates
            assert data["name"] == "Updated Distribution Center"
            assert data["description"] == "Modern warehouse facility with expanded loading docks"
            
            # Test all type-specific details from update_data
            details = data["type_specific_details"]
            assert details["total_square_feet"] == 120000
            assert details["warehouse_square_feet"] == 100000
            assert details["office_square_feet"] == 15000
            assert details["manufacturing_square_feet"] == 5000
            assert details["clear_height"] == 36.0
            assert details["loading_docks_count"] == 15
            assert details["drive_in_doors_count"] == 3
            assert details["rail_access"] is True
            assert details["truck_court_size"] == 20000
            
            # Test additional infrastructure details
            assert details["power_capacity"] == "3000 amps"
            assert details["power_voltage"] == "480V 3-phase"
            assert details["has_crane"] is True
            assert details["crane_capacity"] == "15 ton"
            assert details["sprinkler_system_type"] == "esfr"
            assert details["hazmat_storage_permitted"] is True
            assert details["zoning_classification"] == "M-3"
            assert "warehouse" in details["permitted_uses"]
            assert "distribution" in details["permitted_uses"]
            
            # Test environmental compliance
            env_compliance = details["environmental_compliance"]
            assert env_compliance["phase_1_completed"] is True
            assert env_compliance["phase_2_completed"] is True
            assert env_compliance["last_inspection"] == "2024-01-15"
    
    @pytest.mark.asyncio
    async def test_update_industrial_type_details_only(self):
        """Test updating only type-specific details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Update only type-specific details
        update_data = {
            "type_specific_details": {
                "power_capacity": "4000 amps",
                "power_voltage": "480V 3-phase",
                "has_crane": True,
                "crane_capacity": "25 ton",
                "sprinkler_system_type": "ESFR",
                "environmental_compliance": {
                    "phase_1_completed": True,
                    "phase_2_completed": True,
                    "last_inspection": "2024-01-15"
                },
                "hazmat_storage_permitted": True,
                "permitted_uses": ["warehouse", "distribution", "light_industrial"]
            }
        }
        
        # Use helper function to create response
        type_details = {
            "total_square_feet": 100000,
            "warehouse_square_feet": 85000,
            "office_square_feet": 10000,
            "manufacturing_square_feet": 5000,
            "power_capacity": "4000 amps",
            "power_voltage": "480V 3-phase",
            "has_crane": True,
            "crane_capacity": "25 ton",
            "sprinkler_system_type": "ESFR",
            "environmental_compliance": {
                "phase_1_completed": True,
                "phase_2_completed": True,
                "last_inspection": "2024-01-15"
            },
            "hazmat_storage_permitted": True,
            "permitted_uses": ["warehouse", "distribution", "light_industrial"]
        }
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Distribution Center",
            type_details=type_details,
            units=[]
        )
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["type_specific_details"]["crane_capacity"] == "25 ton"
            assert data["type_specific_details"]["hazmat_storage_permitted"] is True
    
    @pytest.mark.asyncio
    async def test_update_industrial_not_found(self):
        """Test updating non-existent industrial property."""
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
    async def test_update_industrial_forbidden_non_owner(self):
        """Test that non-owners cannot update industrial properties."""
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
    async def test_update_industrial_validation_error(self):
        """Test update with invalid data."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Invalid data - space components exceed total
        update_data = {
            "type_specific_details": {
                "total_square_feet": 50000,
                "warehouse_square_feet": 40000,
                "office_square_feet": 15000,  # Combined would exceed total
                "manufacturing_square_feet": 10000
            }
        }
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.side_effect = HTTPException(
                status_code=422,
                detail="Sum of space components exceeds total square feet"
            )
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_update_industrial_partial_update(self):
        """Test partial update of industrial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Only update description
        update_data = {
            "description": "State-of-the-art logistics facility with automated systems"
        }
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Distribution Center",
            type_details=None,
            units=[]
        )
        # Override description for this test
        updated_property["description"] = "State-of-the-art logistics facility with automated systems"
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["description"] == "State-of-the-art logistics facility with automated systems"
            assert data["name"] == "Distribution Center"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_industrial_admin_can_update_any(self):
        """Test that admin users can update any industrial property."""
        mock_session = AsyncMock()
        
        # Set up admin user
        self.mock_user.is_admin = True
        self.setup_mocks(mock_session)
        
        property_id = 1
        update_data = {
            "name": "Admin Updated Facility",
            "type_specific_details": {
                "total_square_feet": 150000,
                "warehouse_square_feet": 130000,
                "office_square_feet": 20000,
                "zoning_classification": "M-3"
            }
        }
        
        type_details = {
            "total_square_feet": 150000,
            "warehouse_square_feet": 130000,
            "office_square_feet": 20000,
            "zoning_classification": "M-3"
        }
        
        updated_property = self.create_property_response(
            property_id=property_id,
            name="Admin Updated Facility",
            type_details=type_details,
            units=[]
        )
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Admin Updated Facility"
            assert data["type_specific_details"]["total_square_feet"] == 150000