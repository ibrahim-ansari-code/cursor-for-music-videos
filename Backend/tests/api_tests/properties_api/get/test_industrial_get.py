"""
Tests for retrieving industrial properties via the API.
Tests property retrieval with industrial-specific type details.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from Backend.api.properties.schemas import PropertyDetailResponse, OwnerResponse
from ..base_test import (
    BasePropertyTest,
    create_test_property,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestIndustrialPropertyGet(BasePropertyTest):
    """Test industrial property GET endpoints."""
    
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
    async def test_get_industrial_property_success(self):
        """Test successful retrieval of an industrial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create proper response object that matches service return type
        mock_response = PropertyDetailResponse(
            id=property_id,
            name="Distribution Center Alpha",
            address="123 Test St",
            city="Test City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.INDUSTRIAL,
            description="Test industrial property",
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
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Distribution Center Alpha"
            assert data["property_type"] == PropertyType.INDUSTRIAL.value
    
    @pytest.mark.asyncio
    async def test_get_warehouse_with_details(self):
        """Test retrieving warehouse with type-specific details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        type_details = {
            "total_square_feet": 150000,
            "warehouse_square_feet": 140000,
            "office_square_feet": 10000,
            "clear_height": 36.0,
            "loading_docks_count": 20,
            "drive_in_doors_count": 4,
            "rail_access": True,
            "truck_court_size": 30000,
            "power_capacity": "2000 amps",
            "power_voltage": "480V 3-phase",
            "has_crane": True,
            "crane_capacity": "20 ton",
            "sprinkler_system_type": "ESFR"
        }
        
        mock_property = create_test_property(
            property_id=property_id,
            user_id=self.mock_user.id,
            property_type=PropertyType.INDUSTRIAL,
            name="Logistics Hub"
        )
        mock_property.owner = self.mock_user
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get, \
             patch("Backend.api.properties.service.PropertyService._get_type_specific_details") as mock_get_details:
            
            # Mock the type-specific details retrieval
            mock_get_details.return_value = type_details
            
            # Create the expected response structure
            mock_response = self.create_property_response(
                property_id=property_id,
                name="Logistics Hub",
                type_details=type_details
            )
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["type_specific_details"]["total_square_feet"] == 150000
            assert data["type_specific_details"]["rail_access"] is True
            assert data["type_specific_details"]["has_crane"] is True
    
    @pytest.mark.asyncio
    async def test_get_manufacturing_facility(self):
        """Test retrieving manufacturing facility with production details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        mock_property = create_test_property(
            property_id=property_id,
            user_id=self.mock_user.id,
            property_type=PropertyType.INDUSTRIAL,
            name="Production Plant"
        )
        mock_property.owner = self.mock_user
        
        type_details = {
            "total_square_feet": 80000,
            "warehouse_square_feet": 20000,
            "office_square_feet": 5000,
            "manufacturing_square_feet": 55000,
            "clear_height": 24.0,
            "power_capacity": "4000 amps",
            "power_voltage": "600V 3-phase",
            "has_crane": True,
            "crane_capacity": "50 ton",
            "environmental_compliance": {
                "air_permits": True,
                "wastewater_permits": True,
                "iso_certifications": ["ISO_9001", "ISO_14001"]
            },
            "permitted_uses": ["manufacturing", "assembly", "warehouse"]
        }
        
        mock_response = self.create_property_response(
            property_id=property_id,
            name="Production Plant",
            type_details=type_details
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["type_specific_details"]["manufacturing_square_feet"] == 55000
            assert "manufacturing" in data["type_specific_details"]["permitted_uses"]
    
    @pytest.mark.asyncio
    async def test_get_cold_storage_facility(self):
        """Test retrieving cold storage facility with temperature zones."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        mock_property = create_test_property(
            property_id=property_id,
            user_id=self.mock_user.id,
            property_type=PropertyType.INDUSTRIAL,
            name="Cold Storage Facility"
        )
        mock_property.owner = self.mock_user
        
        type_details = {
            "total_square_feet": 50000,
            "warehouse_square_feet": 45000,
            "office_square_feet": 2500,
            "clear_height": 35.0,
            "loading_docks_count": 8,
            "sprinkler_system_type": "dry",
            "environmental_compliance": {
                "refrigerant_type": "ammonia",
                "temperature_zones": ["frozen", "refrigerated", "temperate"]
            },
            "hazmat_storage_permitted": True,
            "permitted_uses": ["cold_storage", "warehouse", "distribution"]
        }
        
        mock_response = self.create_property_response(
            property_id=property_id,
            name="Cold Storage Facility",
            type_details=type_details
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert "cold_storage" in data["type_specific_details"]["permitted_uses"]
            assert data["type_specific_details"]["hazmat_storage_permitted"] is True
    
    @pytest.mark.asyncio
    async def test_get_industrial_properties_list(self):
        """Test retrieving list of industrial properties."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        mock_properties = [
            create_test_property(
                property_id=1,
                user_id=self.mock_user.id,
                property_type=PropertyType.INDUSTRIAL,
                name="Warehouse A"
            ),
            create_test_property(
                property_id=2,
                user_id=self.mock_user.id,
                property_type=PropertyType.INDUSTRIAL,
                name="Factory B"
            )
        ]
        
        with patch("Backend.api.properties.service.PropertyService.get_properties") as mock_get:
            mock_get.return_value = mock_properties
            
            response = self.client.get(
                "/api/properties/",
                params={"property_type": PropertyType.INDUSTRIAL.value}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert all(p["property_type"] == PropertyType.INDUSTRIAL.value for p in data)
    
    @pytest.mark.asyncio
    async def test_get_industrial_forbidden_non_owner(self):
        """Test that non-owners cannot retrieve industrial properties."""
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
    async def test_get_industrial_not_found(self):
        """Test retrieving non-existent industrial property."""
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