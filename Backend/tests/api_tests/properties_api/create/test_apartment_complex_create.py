"""
Tests for creating apartment complex properties via the API.
Tests property creation with apartment complex-specific type details.
"""

import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from ..base_test import (
    BasePropertyTest,
    get_base_property_payload,
    get_apartment_complex_details,
    create_test_property
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestApartmentComplexPropertyCreate(BasePropertyTest):
    """Test apartment complex property creation endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_apartment_complex_success(self):
        """Test successful creation of an apartment complex property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.APARTMENT_COMPLEX)
        payload["type_specific_details"] = get_apartment_complex_details()
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.APARTMENT_COMPLEX,
            name=payload["name"]
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == payload["name"]
            assert data["property_type"] == PropertyType.APARTMENT_COMPLEX.value
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_large_apartment_complex(self):
        """Test creating a large apartment complex with multiple buildings."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.APARTMENT_COMPLEX)
        details = get_apartment_complex_details()
        details["number_of_buildings"] = 5
        details["total_units"] = 250
        details["studio_units"] = 30
        details["one_bed_units"] = 100
        details["two_bed_units"] = 80
        details["three_bed_units"] = 30
        details["penthouse_units"] = 10
        details["elevator_count"] = 10
        details["parking_spaces_total"] = 400
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.APARTMENT_COMPLEX
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.number_of_buildings == 5
            assert mock_create.call_args[0][0].type_specific_details.total_units == 250
    
    @pytest.mark.asyncio
    async def test_create_apartment_complex_with_amenities(self):
        """Test creating apartment complex with extensive amenities."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.APARTMENT_COMPLEX)
        details = get_apartment_complex_details()
        details["shared_amenities"] = [
            "gym", "pool", "parking_garage", "clubhouse",
            "business_center", "dog_park", "playground",
            "bbq_area", "rooftop_terrace", "concierge"
        ]
        details["has_security_system"] = True
        details["security_system_type"] = "24/7 security with biometric access"
        details["concierge_service"] = True
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.APARTMENT_COMPLEX
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert len(mock_create.call_args[0][0].type_specific_details.shared_amenities) == 10
            assert mock_create.call_args[0][0].type_specific_details.has_security_system == True
    
    @pytest.mark.asyncio
    async def test_create_apartment_complex_with_management(self):
        """Test creating apartment complex with management details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.APARTMENT_COMPLEX)
        details = get_apartment_complex_details()
        details["property_management_company"] = "Premium Property Management Inc."
        details["on_site_management"] = True
        details["management_office_location"] = "Building A, Ground Floor"
        details["assigned_property_manager"] = "Jane Smith"
        details["management_contact_phone"] = "416-555-0123"
        details["management_contact_email"] = "manager@propertymanagement.com"
        details["emergency_contacts"] = [
            {"name": "Emergency Maintenance", "phone": "416-555-0911"},
            {"name": "Security", "phone": "416-555-0112"}
        ]
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.APARTMENT_COMPLEX
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            call_details = mock_create.call_args[0][0].type_specific_details
            assert call_details.property_management_company == "Premium Property Management Inc."
            assert call_details.on_site_management == True
            assert len(call_details.emergency_contacts) == 2
    
    @pytest.mark.asyncio
    async def test_create_apartment_complex_validate_unit_distribution(self):
        """Test validation of unit distribution totals."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.APARTMENT_COMPLEX)
        details = get_apartment_complex_details()
        details["total_units"] = 100
        details["studio_units"] = 30
        details["one_bed_units"] = 40
        details["two_bed_units"] = 30
        details["three_bed_units"] = 10  
        details["penthouse_units"] = 5  # Total = 115, exceeds total_units (100)
        payload["type_specific_details"] = details
        
        response = self.client.post("/api/properties/", json=payload)
        
        # Should fail validation as sum of unit types exceeds total
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_apartment_complex_with_occupancy_rates(self):
        """Test creating apartment complex with occupancy information."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.APARTMENT_COMPLEX)
        details = get_apartment_complex_details()
        details["vacancy_rate"] = 7.5
        details["average_rent_by_type"] = {
            "studio": 1200.00,
            "1br": 1600.00,
            "2br": 2200.00,
            "3br": 3000.00
        }
        details["lease_expiry_distribution"] = {
            "2024-03": 5,
            "2024-06": 8,
            "2024-09": 12,
            "2024-12": 15
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.APARTMENT_COMPLEX
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            call_details = mock_create.call_args[0][0].type_specific_details
            assert float(call_details.vacancy_rate) == 7.5
    
    @pytest.mark.asyncio
    async def test_create_apartment_complex_with_vacancy_rate(self):
        """Test creating apartment complex with vacancy rate."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.APARTMENT_COMPLEX)
        details = get_apartment_complex_details()
        details["vacancy_rate"] = 7.5
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.APARTMENT_COMPLEX,
            name=payload["name"]
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
    
    @pytest.mark.asyncio
    async def test_create_apartment_complex_with_waste_management(self):
        """Test creating apartment complex with waste management details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.APARTMENT_COMPLEX)
        details = get_apartment_complex_details()
        details["trash_system_type"] = "compactor"
        details["trash_collection_schedule"] = "Monday, Wednesday, Friday"
        details["trash_system_details"] = "Compactor on each floor with recycling bins"
        details["recycling_program"] = True
        details["composting_available"] = True
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.APARTMENT_COMPLEX
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            call_details = mock_create.call_args[0][0].type_specific_details
            assert call_details.trash_system_type == "compactor"
            assert "Monday" in call_details.trash_collection_schedule
    
    @pytest.mark.asyncio
    async def test_create_apartment_complex_with_policies(self):
        """Test creating apartment complex with various policies."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.APARTMENT_COMPLEX)
        details = get_apartment_complex_details()
        details["pet_policy"] = "Cats and dogs under 30lbs, $500 deposit, 2 pet maximum"
        details["smoking_policy"] = "No smoking in units or common areas"
        details["guest_policy"] = "Guests allowed for max 14 consecutive days"
        details["utilities_included"] = ["water", "trash", "sewer", "heat"]
        details["parking_policy"] = "One space per unit, additional $100/month"
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.APARTMENT_COMPLEX
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            call_details = mock_create.call_args[0][0].type_specific_details
            assert "30lbs" in call_details.pet_policy
            assert len(call_details.utilities_included) == 4
    
    @pytest.mark.asyncio
    async def test_create_apartment_complex_minimal(self):
        """Test creating apartment complex with only required fields."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.APARTMENT_COMPLEX)
        # Only required field for apartment complex
        payload["type_specific_details"] = {
            "total_units": 24
        }
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.APARTMENT_COMPLEX
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.total_units == 24
            # number_of_buildings should default to 1
            assert mock_create.call_args[0][0].type_specific_details.number_of_buildings == 1