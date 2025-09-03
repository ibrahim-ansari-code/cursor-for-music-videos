"""
Tests for creating commercial properties via the API.
Tests property creation with commercial-specific type details.
"""

import pytest
from unittest.mock import AsyncMock, patch

from Backend.models.property import PropertyType
from ..base_test import (
    BasePropertyTest,
    get_base_property_payload,
    get_commercial_details,
    create_test_property
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestCommercialPropertyCreate(BasePropertyTest):
    """Test commercial property creation endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_commercial_property_success(self):
        """Test successful creation of a commercial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.COMMERCIAL)
        payload["type_specific_details"] = get_commercial_details()
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL,
            name=payload["name"]
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == payload["name"]
            assert data["property_type"] == PropertyType.COMMERCIAL.value
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_office_building(self):
        """Test creating an office building commercial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.COMMERCIAL)
        details = get_commercial_details()
        details["property_subtype"] = "office"
        details["building_class"] = "A"
        details["total_floors"] = 25
        details["rentable_area"] = 150000
        details["occupancy_rate"] = 95.0
        details["elevators"] = 8
        details["parking_spaces"] = 500
        details["parking_ratio"] = 3.3
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            # Verify property type is correct
            assert mock_create.call_args[0][0].property_type == PropertyType.COMMERCIAL
    
    @pytest.mark.asyncio
    async def test_create_retail_property(self):
        """Test creating a retail commercial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.COMMERCIAL)
        details = get_commercial_details()
        details["property_subtype"] = "retail"
        details["retail_type"] = "strip_mall"
        details["rentable_area"] = 25000
        details["number_of_units"] = 10
        details["anchor_tenants"] = ["Grocery Store", "Pharmacy"]
        details["parking_spaces"] = 150
        details["foot_traffic_count"] = 5000
        details["visibility"] = "high"
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].property_type == PropertyType.COMMERCIAL
    
    @pytest.mark.asyncio
    async def test_create_shopping_center(self):
        """Test creating a shopping center commercial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.COMMERCIAL)
        details = get_commercial_details()
        details["property_subtype"] = "shopping_center"
        details["rentable_area"] = 500000
        details["anchor_tenants"] = ["Department Store", "Cinema", "Supermarket"]
        details["total_tenants"] = 120
        details["parking_spaces"] = 2500
        details["food_court"] = True
        details["entertainment_facilities"] = ["cinema", "arcade", "bowling"]
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            # Verify property type is correct  
            assert mock_create.call_args[0][0].property_type == PropertyType.COMMERCIAL
    
    @pytest.mark.asyncio
    async def test_create_medical_office(self):
        """Test creating a medical office commercial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.COMMERCIAL)
        details = get_commercial_details()
        details["property_subtype"] = "medical"
        details["building_class"] = "B"
        details["total_floors"] = 5
        details["rentable_area"] = 30000
        details["medical_gas_system"] = True
        details["backup_generator"] = True
        details["ada_compliant"] = True
        details["exam_rooms"] = 25
        details["parking_spaces"] = 120
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            # Verify property type is correct
            assert mock_create.call_args[0][0].property_type == PropertyType.COMMERCIAL
    
    @pytest.mark.asyncio
    async def test_create_commercial_with_lease_details(self):
        """Test creating commercial property with lease information."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.COMMERCIAL)
        details = get_commercial_details()
        details["lease_types"] = ["triple_net", "gross", "modified_gross", "percentage"]
        details["average_lease_term"] = 5
        details["average_rent_psf"] = 45.50
        details["cam_charges"] = 8.25
        details["operating_expenses"] = 15.75
        details["expense_stops"] = {"utilities": 5.00, "taxes": 3.50}
        details["tenant_improvements_allowance"] = 50.00
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].property_type == PropertyType.COMMERCIAL
    
    @pytest.mark.asyncio
    async def test_create_retail_with_percentage_lease(self):
        """Test creating retail property with percentage lease structure."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.COMMERCIAL)
        details = get_commercial_details()
        details["space_type"] = "retail"
        details["lease_type"] = "percentage"
        details["usable_square_feet"] = 5000
        details["rentable_square_feet"] = 5500
        details["anchor_tenant"] = "Fashion Retailer"
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].property_type == PropertyType.COMMERCIAL
    
    @pytest.mark.asyncio
    async def test_create_commercial_with_other_lease_type(self):
        """Test creating commercial property with 'other' lease structure."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.COMMERCIAL)
        details = get_commercial_details()
        details["lease_type"] = "other"
        details["space_type"] = "office"
        details["usable_square_feet"] = 12000
        details["rentable_square_feet"] = 13500
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].property_type == PropertyType.COMMERCIAL
    
    @pytest.mark.asyncio
    async def test_create_commercial_with_amenities(self):
        """Test creating commercial property with building amenities."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.COMMERCIAL)
        details = get_commercial_details()
        details["building_amenities"] = [
            "conference_center", "fitness_center", "cafeteria",
            "rooftop_terrace", "concierge", "valet_parking",
            "bike_storage", "showers", "daycare"
        ]
        details["security_features"] = ["24/7_security", "keycard_access", "cctv"]
        details["technology_features"] = ["fiber_optic", "backup_internet", "smart_building"]
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].property_type == PropertyType.COMMERCIAL
    
    @pytest.mark.asyncio
    async def test_create_commercial_with_certifications(self):
        """Test creating commercial property with certifications."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.COMMERCIAL)
        details = get_commercial_details()
        details["energy_rating"] = "LEED Platinum"
        details["energy_star_score"] = 92
        details["boma_certified"] = True
        details["wired_certified"] = "Gold"
        details["walk_score"] = 98
        details["transit_score"] = 95
        details["bike_score"] = 88
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].property_type == PropertyType.COMMERCIAL
    
    
    @pytest.mark.asyncio
    async def test_create_commercial_with_tenant_mix(self):
        """Test creating commercial property with tenant mix information."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.COMMERCIAL)
        details = get_commercial_details()
        details["tenant_mix"] = {
            "technology": 40,
            "finance": 25,
            "law": 20,
            "medical": 10,
            "other": 5
        }
        details["major_tenants"] = [
            {"name": "Tech Corp", "square_footage": 25000, "lease_expiry": "2028-12-31"},
            {"name": "Finance Inc", "square_footage": 15000, "lease_expiry": "2026-06-30"}
        ]
        details["vacancy_rate"] = 5.5
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].property_type == PropertyType.COMMERCIAL