"""
Tests for creating industrial properties via the API.
Tests property creation with industrial-specific type details.
"""

import pytest
from unittest.mock import AsyncMock, patch

from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from ..base_test import (
    BasePropertyTest,
    get_base_property_payload,
    get_industrial_details,
    create_test_property
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestIndustrialPropertyCreate(BasePropertyTest):
    """Test industrial property creation endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_industrial_property_success(self):
        """Test successful creation of an industrial property."""
        # Setup
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        # Create property payload
        payload = get_base_property_payload(PropertyType.INDUSTRIAL)
        payload["type_specific_details"] = get_industrial_details()
        
        # Mock the service response
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.INDUSTRIAL,
            name=payload["name"]
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            # Make request
            response = self.client.post("/api/properties/", json=payload)
            
            # Assertions
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == payload["name"]
            assert data["property_type"] == PropertyType.INDUSTRIAL.value
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_industrial_warehouse(self):
        """Test creating a warehouse industrial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.INDUSTRIAL)
        details = {
            "property_type": "Industrial",  # Discriminator field
            "industrial_type": "warehouse",  # Required field
            "total_square_feet": 100000,
            "warehouse_square_feet": 90000,
            "office_square_feet": 5000,
            "clear_height": 32.0,
            "loading_docks_count": 10,
            "drive_in_doors_count": 2,
            "rail_access": False,
            "truck_court_size": 20000,
            "power_capacity": "2000 amps",
            "power_voltage": "480V 3-phase",
            "has_crane": False,
            "sprinkler_system_type": "esfr",
            "hazmat_storage_permitted": False,
            "zoning_classification": "M-2",
            "permitted_uses": ["warehouse", "distribution"]
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.INDUSTRIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.total_square_feet == 100000
            assert mock_create.call_args[0][0].type_specific_details.warehouse_square_feet == 90000
            assert mock_create.call_args[0][0].type_specific_details.loading_docks_count == 10
    
    @pytest.mark.asyncio
    async def test_create_industrial_manufacturing(self):
        """Test creating a manufacturing industrial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.INDUSTRIAL)
        details = {
            "property_type": "Industrial",  # Discriminator field
            "industrial_type": "manufacturing",  # Required field
            "total_square_feet": 150000,
            "manufacturing_square_feet": 100000,
            "warehouse_square_feet": 30000,
            "office_square_feet": 20000,
            "clear_height": 28.0,
            "loading_docks_count": 5,
            "drive_in_doors_count": 3,
            "rail_access": True,
            "power_capacity": "4000 amps",
            "power_voltage": "480V 3-phase",
            "has_crane": True,
            "crane_capacity": "20 ton",
            "sprinkler_system_type": "wet",
            "environmental_compliance": {
                "iso_14001": True,
                "air_quality_permit": "AQ-2024-001"
            },
            "hazmat_storage_permitted": True,
            "zoning_classification": "M-3",
            "permitted_uses": ["manufacturing", "assembly", "warehouse"]
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.INDUSTRIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.manufacturing_square_feet == 100000
            assert mock_create.call_args[0][0].type_specific_details.has_crane == True
            assert mock_create.call_args[0][0].type_specific_details.crane_capacity == "20 ton"
            assert mock_create.call_args[0][0].type_specific_details.rail_access == True
    
    @pytest.mark.asyncio
    async def test_create_industrial_distribution_center(self):
        """Test creating a distribution center industrial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.INDUSTRIAL)
        details = {
            "property_type": "Industrial",  # Discriminator field
            "industrial_type": "distribution",  # Required field
            "total_square_feet": 250000,
            "warehouse_square_feet": 230000,
            "office_square_feet": 10000,
            "clear_height": 40.0,
            "loading_docks_count": 30,
            "drive_in_doors_count": 5,
            "rail_access": True,
            "truck_court_size": 50000,
            "power_capacity": "3000 amps",
            "power_voltage": "480V 3-phase",
            "has_crane": False,
            "sprinkler_system_type": "esfr",
            "hazmat_storage_permitted": False,
            "zoning_classification": "M-1", 
            "permitted_uses": ["warehouse", "distribution", "logistics"]
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,  
            user_id=self.mock_user.id,
            property_type=PropertyType.INDUSTRIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.loading_docks_count == 30
            assert mock_create.call_args[0][0].type_specific_details.truck_court_size == 50000
    
    @pytest.mark.asyncio
    async def test_create_industrial_flex_space(self):
        """Test creating a flex/light industrial space."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.INDUSTRIAL)
        details = {
            "property_type": "Industrial",  # Discriminator field
            "industrial_type": "flex",  # Required field
            "total_square_feet": 25000,
            "warehouse_square_feet": 15000,
            "office_square_feet": 10000,
            "clear_height": 18.0,
            "loading_docks_count": 2,
            "drive_in_doors_count": 1,
            "rail_access": False,
            "power_capacity": "800 amps",
            "power_voltage": "208V 3-phase",
            "has_crane": False,
            "sprinkler_system_type": "wet",
            "hazmat_storage_permitted": False,
            "zoning_classification": "LI",
            "permitted_uses": ["light_industrial", "flex_space", "r&d"]
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.INDUSTRIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            call_details = mock_create.call_args[0][0].type_specific_details
            assert call_details.total_square_feet == 25000
            assert "flex_space" in call_details.permitted_uses or "flex" in call_details.permitted_uses
    
    @pytest.mark.asyncio
    async def test_create_industrial_cold_storage(self):
        """Test creating a cold storage facility."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.INDUSTRIAL)
        details = {
            "property_type": "Industrial",  # Discriminator field
            "industrial_type": "cold_storage",  # Required field
            "total_square_feet": 50000,
            "warehouse_square_feet": 45000,
            "office_square_feet": 2500,
            "clear_height": 35.0,
            "loading_docks_count": 8,
            "drive_in_doors_count": 0,
            "rail_access": False,
            "truck_court_size": 15000,
            "power_capacity": "3000 amps",
            "power_voltage": "480V 3-phase",
            "has_crane": False,
            "sprinkler_system_type": "dry",
            "environmental_compliance": {
                "refrigerant_type": "ammonia",
                "temperature_zones": "frozen, refrigerated, temperate"
            },
            "hazmat_storage_permitted": True,  # For ammonia refrigeration
            "zoning_classification": "M-2",
            "permitted_uses": ["cold_storage", "warehouse", "distribution"]
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.INDUSTRIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.sprinkler_system_type == "dry"
            assert "cold_storage" in mock_create.call_args[0][0].type_specific_details.permitted_uses
    
    @pytest.mark.asyncio
    async def test_create_industrial_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.INDUSTRIAL)
        details = {
            "property_type": "Industrial",  # Discriminator field
            "industrial_type": "warehouse",  # Required field
            # Missing required total_square_feet
            "warehouse_square_feet": 50000,
            "loading_docks_count": 5
        }
        payload["type_specific_details"] = details
        
        response = self.client.post("/api/properties/", json=payload)
        
        assert response.status_code == 422
        assert "total_square_feet" in str(response.json()).lower()
    
    @pytest.mark.asyncio
    async def test_create_industrial_with_environmental_compliance(self):
        """Test creating industrial property with environmental compliance details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.INDUSTRIAL)
        details = {
            "property_type": "Industrial",  # Discriminator field
            "industrial_type": "warehouse",  # Required field
            "total_square_feet": 75000,
            "warehouse_square_feet": 60000,
            "office_square_feet": 5000,
            "loading_docks_count": 8,
            "hazmat_storage_permitted": True,
            "environmental_compliance": {
                "phase_1_esa": "2023-06-15",
                "phase_2_esa": "2023-07-20",
                "permits": ["air_quality", "wastewater", "hazmat"],
                "certifications": ["ISO_14001", "LEED_Silver"]
            },
            "zoning_classification": "M-2",
            "permitted_uses": ["warehouse", "light_industrial"]
        }
        payload["type_specific_details"] = details
        payload["status"] = PropertyStatus.ACTIVE.value
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.INDUSTRIAL,
            status=PropertyStatus.ACTIVE
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.hazmat_storage_permitted == True
            assert mock_create.call_args[0][0].type_specific_details.environmental_compliance
    
    @pytest.mark.asyncio
    async def test_create_industrial_unauthorized(self):
        """Test that unauthenticated users cannot create properties."""
        # Don't setup auth mock to simulate unauthenticated request
        
        payload = get_base_property_payload(PropertyType.INDUSTRIAL)
        payload["type_specific_details"] = get_industrial_details()
        
        response = self.client.post("/api/properties/", json=payload)
        
        # Accept either 401 or 403 as both indicate lack of proper auth
        # 401: No auth header provided (authentication required)
        # 403: Invalid/expired token or host validation failed (authorization failed)
        assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"