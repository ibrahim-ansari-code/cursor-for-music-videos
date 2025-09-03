"""
Tests for creating mixed-use properties via the API.
Tests property creation with mixed-use-specific type details.
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from ..base_test import (
    BasePropertyTest,
    get_base_property_payload,
    get_mixed_use_details,
    create_test_property
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestMixedUsePropertyCreate(BasePropertyTest):
    """Test mixed-use property creation endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_property_success(self):
        """Test successful creation of a mixed-use property."""
        # Setup
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        # Create property payload
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        payload["type_specific_details"] = get_mixed_use_details()
        
        # Mock the service response
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE,
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
            assert data["property_type"] == PropertyType.MIXED_USE.value
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_residential_retail(self):
        """Test creating a mixed-use property with residential and retail components."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        details = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "retail_residential",  # Required field
            "residential_square_feet": 80000,
            "commercial_square_feet": 20000,
            "residential_units_count": 60,
            "commercial_units_count": 8,
            "residential_unit_types": {
                "studio": 10,
                "1br": 25,
                "2br": 20,
                "3br": 5
            },
            "commercial_space_types": ["retail", "restaurant", "cafe"],
            "shared_amenities": ["lobby", "parking_garage", "rooftop_deck"],
            "separate_entrances": True,
            "shared_parking": False,
            "parking_spaces_total": 100,
            "single_management_company": True,
            "management_structure": "Unified property management for all components",
            "zoning_designation": "MU-2"
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.residential_units_count == 60
            assert mock_create.call_args[0][0].type_specific_details.commercial_units_count == 8
            assert "retail" in mock_create.call_args[0][0].type_specific_details.commercial_space_types
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_residential_office(self):
        """Test creating a mixed-use property with residential and office components."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        details = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "office_residential",  # Required field
            "residential_square_feet": 120000,
            "commercial_square_feet": 80000,
            "residential_units_count": 100,
            "commercial_units_count": 20,
            "residential_unit_types": {
                "studio": 20,
                "1br": 40,
                "2br": 30,
                "3br": 10
            },
            "commercial_space_types": ["office", "medical", "service"],
            "shared_amenities": ["gym", "concierge", "business_center", "parking_garage"],
            "separate_entrances": True,
            "shared_parking": True,
            "parking_spaces_total": 250,
            "single_management_company": False,
            "management_structure": "Separate management for residential and commercial",
            "zoning_designation": "MU-3"
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.residential_units_count == 100
            assert "office" in mock_create.call_args[0][0].type_specific_details.commercial_space_types
            assert mock_create.call_args[0][0].type_specific_details.single_management_company == False
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_comprehensive(self):
        """Test creating a comprehensive mixed-use development."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        details = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "vertical_mixed",  # Required field
            "residential_square_feet": 200000,
            "commercial_square_feet": 100000,
            "residential_units_count": 150,
            "commercial_units_count": 30,
            "residential_unit_types": {
                "studio": 30,
                "1br": 60,
                "2br": 45,
                "3br": 15
            },
            "commercial_space_types": ["retail", "office", "restaurant", "fitness", "medical"],
            "shared_amenities": [
                "lobby", "concierge", "gym", "pool", 
                "rooftop_deck", "courtyard", "business_center", "parking_garage"
            ],
            "separate_entrances": True,
            "shared_parking": False,
            "parking_spaces_total": 400,
            "single_management_company": True,
            "management_structure": "Integrated management with dedicated teams per component",
            "zoning_designation": "MU-4"
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            details = mock_create.call_args[0][0].type_specific_details
            assert details.residential_units_count == 150
            assert len(details.commercial_space_types) >= 5
            assert len(details.shared_amenities) >= 8
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_minimal(self):
        """Test creating a minimal mixed-use property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        details = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "live_work",  # Required field
            "residential_square_feet": 30000,
            "commercial_square_feet": 10000,
            "residential_units_count": 20,
            "commercial_units_count": 3,
            "residential_unit_types": {"1br": 10, "2br": 10},
            "commercial_space_types": ["retail"],
            "shared_amenities": [],
            "separate_entrances": False,
            "shared_parking": True,
            "parking_spaces_total": 30,
            "single_management_company": True,
            "zoning_designation": "MU-1"
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            details = mock_create.call_args[0][0].type_specific_details
            assert details.separate_entrances == False
            assert details.shared_parking == True
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_validate_unit_distribution(self):
        """Test validation of residential unit type distribution."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        details = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "retail_residential",  # Required field
            "residential_square_feet": 50000,
            "commercial_square_feet": 15000,
            "residential_units_count": 40,
            "commercial_units_count": 5,
            "residential_unit_types": {
                "studio": 15,
                "1br": 20,
                "2br": 10  # Sum is 45, exceeds residential_units_count of 40
            },
            "commercial_space_types": ["retail", "office"],
            "shared_amenities": ["lobby"],
            "separate_entrances": True,
            "shared_parking": True,
            "parking_spaces_total": 60,
            "single_management_company": True,
            "zoning_designation": "MU-2"
        }
        payload["type_specific_details"] = details
        
        response = self.client.post("/api/properties/", json=payload)
        
        assert response.status_code == 422
        assert "exceeds total" in str(response.json()).lower()
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_normalize_commercial_types(self):
        """Test normalization of commercial space types."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        details = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "live_work",  # Required field
            "residential_square_feet": 60000,
            "commercial_square_feet": 20000,
            "residential_units_count": 50,
            "commercial_units_count": 10,
            "residential_unit_types": {"1br": 25, "2br": 25},
            "commercial_space_types": ["shop", "food", "gym", "medical"],  # Will be normalized
            "shared_amenities": ["parking"],
            "separate_entrances": True,
            "shared_parking": True,
            "parking_spaces_total": 80,
            "single_management_company": True,
            "zoning_designation": "MU-2"
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            types = mock_create.call_args[0][0].type_specific_details.commercial_space_types
            # Check normalized values
            assert "retail" in types  # "shop" normalizes to "retail"
            assert "restaurant" in types  # "food" normalizes to "restaurant"
            assert "fitness" in types  # "gym" normalizes to "fitness"
            assert "medical" in types
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_normalize_amenities(self):
        """Test normalization of shared amenities."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        details = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "office_residential",  # Required field
            "residential_square_feet": 70000,
            "commercial_square_feet": 30000,
            "residential_units_count": 60,
            "commercial_units_count": 12,
            "residential_unit_types": {"1br": 30, "2br": 30},
            "commercial_space_types": ["retail", "office"],
            "shared_amenities": ["fitness", "garage", "rooftop", "business center"],  # Will be normalized
            "separate_entrances": True,
            "shared_parking": True,
            "parking_spaces_total": 100,
            "single_management_company": True,
            "zoning_designation": "MU-3"
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            amenities = mock_create.call_args[0][0].type_specific_details.shared_amenities
            # Check normalized values
            assert "gym" in amenities  # "fitness" normalizes to "gym"
            assert "parking_garage" in amenities  # "garage" normalizes to "parking_garage"
            assert "rooftop_deck" in amenities  # "rooftop" normalizes to "rooftop_deck"
            assert "business_center" in amenities
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_only_commercial_initially(self):
        """Test creating mixed-use with only commercial defined initially."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        details = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "retail_residential",  # Required field
            "residential_square_feet": 1,  # Minimal residential component
            "commercial_square_feet": 50000,
            "commercial_units_count": 15,
            "commercial_space_types": ["retail", "office", "restaurant"],
            "shared_amenities": ["lobby", "parking"],
            "separate_entrances": True,
            "shared_parking": True,
            "single_management_company": True,
            "zoning_designation": "MU-2"
        }
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            # Should succeed - mixed use can be created with partial info
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.commercial_square_feet == 50000
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_with_initial_status(self):
        """Test creating mixed-use property with specific initial status."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        details = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "live_work",  # Required field
            "residential_square_feet": 90000,
            "commercial_square_feet": 40000,
            "residential_units_count": 75,
            "commercial_units_count": 15,
            "residential_unit_types": {
                "studio": 15,
                "1br": 30,
                "2br": 25,
                "3br": 5
            },
            "commercial_space_types": ["retail", "restaurant", "office"],
            "shared_amenities": ["lobby", "parking_garage", "gym"],
            "separate_entrances": True,
            "shared_parking": False,
            "parking_spaces_total": 150,
            "single_management_company": True,
            "management_structure": "Professional property management company",
            "zoning_designation": "MU-3"
        }
        payload["type_specific_details"] = details
        payload["status"] = PropertyStatus.RENTED.value  # Mixed use partially rented
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE,
            status=PropertyStatus.RENTED
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].status == PropertyStatus.RENTED
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_missing_details(self):
        """Test creating mixed-use with minimal/missing type-specific details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        # Minimal details with required fields
        payload["type_specific_details"] = {
            "property_type": "Mixed-Use",  # Discriminator field
            "mixed_use_type": "live_work",  # Required field
            "residential_square_feet": 1,  # Minimal residential component
            "commercial_square_feet": 1   # Minimal commercial component
        }
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.MIXED_USE
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            # Should succeed with default/empty values
            assert response.status_code == 201
    
    @pytest.mark.asyncio
    async def test_create_mixed_use_unauthorized(self):
        """Test that unauthenticated users cannot create properties."""
        # Don't setup auth mock to simulate unauthenticated request
        
        payload = get_base_property_payload(PropertyType.MIXED_USE)
        payload["type_specific_details"] = get_mixed_use_details()
        
        response = self.client.post("/api/properties/", json=payload)
        
        # Accept either 401 or 403 as both indicate lack of proper auth
        # 401: No auth header provided (authentication required)
        # 403: Invalid/expired token or host validation failed (authorization failed)
        assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"