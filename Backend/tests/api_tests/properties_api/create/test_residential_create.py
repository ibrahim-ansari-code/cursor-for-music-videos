"""
Tests for creating residential properties via the API.
Tests property creation with residential-specific type details.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from ..base_test import (
    BasePropertyTest,
    get_base_property_payload,
    get_residential_details,
    create_test_property
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestResidentialPropertyCreate(BasePropertyTest):
    """Test residential property creation endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_residential_property_success(self):
        """Test successful creation of a residential property."""
        # Setup
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        # Create property payload
        payload = get_base_property_payload(PropertyType.RESIDENTIAL)
        payload["type_specific_details"] = get_residential_details()
        
        # Mock the service response
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.RESIDENTIAL,
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
            assert data["property_type"] == PropertyType.RESIDENTIAL.value
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_residential_single_family(self):
        """Test creating a single-family residential property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.RESIDENTIAL)
        details = get_residential_details()
        details["property_subtype"] = "single_family"
        details["bedrooms"] = 4
        details["bathrooms"] = 3.5
        details["square_footage"] = 3500
        details["lot_size"] = 8000
        details["has_driveway"] = True
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.RESIDENTIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.property_subtype == "single_family"
            assert mock_create.call_args[0][0].type_specific_details.bedrooms == 4
            assert mock_create.call_args[0][0].type_specific_details.has_driveway == True
    
    @pytest.mark.asyncio
    async def test_create_residential_condo(self):
        """Test creating a condominium residential property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.RESIDENTIAL)
        details = get_residential_details()
        details["property_subtype"] = "condo"
        details["bedrooms"] = 2
        details["bathrooms"] = 2
        details["square_footage"] = 1200
        details["floor"] = 15
        details["has_balcony"] = True
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.RESIDENTIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            # Verify property type is correct
            assert mock_create.call_args[0][0].property_type == PropertyType.RESIDENTIAL
    
    @pytest.mark.asyncio
    async def test_create_residential_townhouse(self):
        """Test creating a townhouse residential property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.RESIDENTIAL)
        details = get_residential_details()
        details["property_subtype"] = "townhouse"
        details["bedrooms"] = 3
        details["bathrooms"] = 2.5
        details["square_footage"] = 1800
        details["stories"] = 3
        details["garage_type"] = "attached"
        payload["type_specific_details"] = details
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.RESIDENTIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].type_specific_details.property_subtype == "townhouse"
            assert mock_create.call_args[0][0].type_specific_details.stories == 3
    
    @pytest.mark.asyncio
    async def test_create_residential_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        # Payload missing required address field
        payload = {
            "name": "Test Property",
            "city": "Toronto",
            "province": "ON",
            "postal_code": "M5V 3A8",
            "property_type": PropertyType.RESIDENTIAL.value
        }
        
        response = self.client.post("/api/properties/", json=payload)
        
        assert response.status_code == 422
        assert "address" in str(response.json())
    
    @pytest.mark.asyncio
    async def test_create_residential_invalid_details(self):
        """Test validation error for invalid type-specific details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.RESIDENTIAL)
        details = get_residential_details()
        details["bedrooms"] = -1  # Invalid: negative bedrooms
        details["square_footage"] = -500  # Invalid: negative square footage
        payload["type_specific_details"] = details
        
        response = self.client.post("/api/properties/", json=payload)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_residential_with_initial_units(self):
        """Test creating residential property with initial units."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.RESIDENTIAL)
        payload["type_specific_details"] = get_residential_details()
        payload["units"] = ["Main House", "Guest House", "Pool House"]
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.RESIDENTIAL
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            assert mock_create.call_args[0][0].units == ["Main House", "Guest House", "Pool House"]
    
    @pytest.mark.asyncio
    async def test_create_residential_with_rental_info(self):
        """Test creating residential property with rental information."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        payload = get_base_property_payload(PropertyType.RESIDENTIAL)
        details = get_residential_details()
        payload["type_specific_details"] = details
        payload["status"] = PropertyStatus.RENTED.value
        
        created_property = create_test_property(
            property_id=1,
            user_id=self.mock_user.id,
            property_type=PropertyType.RESIDENTIAL,
            status=PropertyStatus.RENTED
        )
        
        with patch("Backend.api.properties.service.PropertyService.create_property") as mock_create:
            mock_create.return_value = created_property
            
            response = self.client.post("/api/properties/", json=payload)
            
            assert response.status_code == 201
            # Verify the status was set correctly
            assert mock_create.call_args[0][0].status == PropertyStatus.RENTED
            # Note: occupied and rental_price are not part of the schema
    
    @pytest.mark.asyncio
    async def test_create_residential_unauthorized(self):
        """Test that unauthenticated users cannot create properties."""
        # Don't setup auth mock to simulate unauthenticated request
        
        payload = get_base_property_payload(PropertyType.RESIDENTIAL)
        payload["type_specific_details"] = get_residential_details()
        
        response = self.client.post("/api/properties/", json=payload)
        
        # Accept either 401 or 403 as both indicate lack of proper auth
        # 401: No auth header provided (authentication required)
        # 403: Invalid/expired token or host validation failed (authorization failed)
        assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"