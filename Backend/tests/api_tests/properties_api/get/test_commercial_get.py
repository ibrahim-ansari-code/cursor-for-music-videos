"""
Tests for retrieving commercial properties via the API.
Tests property retrieval with commercial-specific type details.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch


from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from ..base_test import (
    BasePropertyTest,
    create_test_property
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestCommercialPropertyGet(BasePropertyTest):
    """Test commercial property GET endpoints."""
    
    def create_property_response(self, property_id, name, type_details=None, units=None, stats=None):
        """Helper to create a proper property response."""
        return {
            "id": property_id,
            "name": name,
            "address": "123 Test St",
            "city": "Test City",
            "province": "TC",
            "postal_code": "12345",
            "property_type": PropertyType.COMMERCIAL.value,
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
    async def test_get_commercial_property_success(self):
        """Test successful retrieval of a commercial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        mock_property = create_test_property(
            property_id=property_id,
            user_id=self.mock_user.id,
            property_type=PropertyType.COMMERCIAL,
            name="Downtown Office Tower"
        )
        mock_property.owner = self.mock_user
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_property
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Downtown Office Tower"
            assert data["property_type"] == PropertyType.COMMERCIAL.value
    
    @pytest.mark.asyncio
    async def test_get_office_building_with_details(self):
        """Test retrieving office building with type-specific details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create dict response for consistency - avoid Pydantic typing issues
        type_details = {
            "space_type": "office",
            "usable_square_feet": 45000,
            "rentable_square_feet": 50000,
            "lease_type": "triple_net",
            "ceiling_height": 10.5,
            "floor_count": 10,
            "signage_rights": True,
            "zoning_code": "C-1",
            "loading_area_details": "Loading area details",
            "signage_restrictions": "Signage restrictions",
            "common_area_maintenance_fee": 8500.00,
            "common_area_factor": 20.0
        }
        
        # Create dict response for consistency
        mock_response = {
            "id": property_id,
            "name": "Corporate Plaza",
            "address": "123 Test St",
            "city": "Test City",
            "province": "TC",
            "postal_code": "12345",
            "property_type": PropertyType.COMMERCIAL.value,
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
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            # Test the actual fields that exist in the schema
            assert data["type_specific_details"]["space_type"] == "office"
            assert data["type_specific_details"]["usable_square_feet"] == 45000
            assert data["type_specific_details"]["lease_type"] == "triple_net"
    
    @pytest.mark.asyncio
    async def test_get_retail_property_with_tenants(self):
        """Test retrieving retail property with tenant information."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        

        
        # Create retail units with tenants
        units_data = [
            {"id": 1, "name": "Unit A", "is_rented": True, 
             "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"},
            {"id": 2, "name": "Unit B", "is_rented": True,
             "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"},
            {"id": 3, "name": "Unit C", "is_rented": False,
             "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"}
        ]
        
        # Use the helper function that creates a dict response to avoid Pydantic typing issues
        mock_response = self.create_property_response(
            property_id=property_id,
            name="Riverside Shopping Center",
            type_details={
                "space_type": "retail",
                "usable_square_feet": 25000,
                "rentable_square_feet": 30000,
                "lease_type": "triple_net",
                "common_area_factor": 20.0,
                "ceiling_height": 10.0,
                "floor_count": 1,
                "signage_rights": True,
                "has_loading_area": True,
                "loading_docks_count": 2,
                "loading_area_details": "Loading area details",
                "signage_restrictions": "Signage restrictions",
                "common_area_maintenance_fee": 8500.00,
                "on_site_maintenance": True,
                "zoning_code": "C-1"
            },
            units=units_data
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            # Test the actual fields that exist in the schema
            assert data["type_specific_details"]["space_type"] == "retail"
            assert data["type_specific_details"]["usable_square_feet"] == 25000
            assert data["type_specific_details"]["lease_type"] == "triple_net"
            assert len(data.get("units", [])) == 3
    
    @pytest.mark.asyncio
    async def test_get_commercial_with_lease_details(self):
        """Test retrieving commercial property with lease information."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create dict response for consistency - avoid Pydantic typing issues
        type_details = {
            "space_type": "office",
            "usable_square_feet": 20000,
            "rentable_square_feet": 25000,
            "lease_type": "triple_net",
            "common_area_factor": 20.0,
            "ceiling_height": 12.0,
            "floor_count": 5,
            "common_area_maintenance_fee": 8500.00,
            "on_site_maintenance": True,
            "zoning_code": "C-1",
            "loading_area_details": "Loading area details",
            "signage_restrictions": "Signage restrictions"
        }
        
        # Create dict response for consistency
        mock_response = {
            "id": property_id,
            "name": "Corporate Office Building",
            "address": "123 Test St",
            "city": "Test City",
            "province": "TC",
            "postal_code": "12345",
            "property_type": PropertyType.COMMERCIAL.value,
            "description": "Test property",
            "year_built": 2020,
            "status": PropertyStatus.ACTIVE.value,
            "type_specific_details": type_details,
            "user_id": self.mock_user.id,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "owner": {
                "id": self.mock_user.id,
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com"
            },
            "units": [],
            "stats": None
        }
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            # Test the actual fields that exist in the schema
            assert data["type_specific_details"]["lease_type"] == "triple_net"
            assert data["type_specific_details"]["space_type"] == "office"
            assert float(data["type_specific_details"]["common_area_maintenance_fee"]) == 8500.0
    
    @pytest.mark.asyncio
    async def test_get_shopping_center_details(self):
        """Test retrieving shopping center with complex details."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Remove unused imports since we use dict format
        
        # Create dict response for consistency - avoid Pydantic typing issues
        type_details = {
            "space_type": "retail",
            "usable_square_feet": 400000,
            "rentable_square_feet": 450000,
            "lease_type": "modified_gross",
            "common_area_factor": 12.5,
            "ceiling_height": 16.0,
            "floor_count": 2,
            "has_loading_area": True,
            "loading_docks_count": 8,
            "signage_rights": True,
            "common_area_maintenance_fee": 250000.00,
            "on_site_maintenance": True, 
            "zoning_code": "C-1",
            "loading_area_details": "Loading area details",
            "signage_restrictions": "Signage restrictions"
        }
        
        # Create dict response for consistency
        mock_response = {
            "id": property_id,
            "name": "Valley Mall",
            "address": "123 Test St",
            "city": "Test City",
            "province": "TC",
            "postal_code": "12345",
            "property_type": PropertyType.COMMERCIAL.value,
            "description": "Test property",
            "year_built": 2020,
            "status": PropertyStatus.ACTIVE.value,
            "type_specific_details": type_details,
            "user_id": self.mock_user.id,
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
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            # Test the actual fields that exist in the schema
            assert data["type_specific_details"]["space_type"] == "retail"
            assert data["type_specific_details"]["usable_square_feet"] == 400000
            assert float(data["type_specific_details"]["common_area_maintenance_fee"]) == 250000.0
    
    @pytest.mark.asyncio
    async def test_get_commercial_properties_list(self):
        """Test retrieving list of commercial properties."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        mock_properties = [
            create_test_property(
                property_id=1,
                user_id=self.mock_user.id,
                property_type=PropertyType.COMMERCIAL,
                name="Office Building A"
            ),
            create_test_property(
                property_id=2,
                user_id=self.mock_user.id,
                property_type=PropertyType.COMMERCIAL,
                name="Retail Center B"
            ),
            create_test_property(
                property_id=3,
                user_id=self.mock_user.id,
                property_type=PropertyType.COMMERCIAL,
                name="Medical Office C"
            )
        ]
        
        with patch("Backend.api.properties.service.PropertyService.get_properties") as mock_get:
            mock_get.return_value = mock_properties
            
            response = self.client.get(
                "/api/properties/",
                params={"property_type": PropertyType.COMMERCIAL.value}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert all(p["property_type"] == PropertyType.COMMERCIAL.value for p in data)

    @pytest.mark.asyncio
    async def test_get_multi_tenant_center(self):
        """Test retrieving a multi-tenant commercial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)

        property_id = 42

        # Build a plain dict response using the existing helper to avoid strict typing conflicts
        type_details = {
            "space_type": "multi_tenant",
            "usable_square_feet": 20000,
            "rentable_square_feet": 22000,
            "lease_type": "gross",
            "floor_count": 1,
            "signage_rights": True
        }

        mock_response = self.create_property_response(
            property_id=property_id,
            name="Neighborhood Center",
            type_details=type_details,
            units=[]
        )

        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response

            response = self.client.get(f"/api/properties/{property_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["type_specific_details"]["space_type"] == "multi_tenant"
    
    @pytest.mark.asyncio
    async def test_get_commercial_with_environmental_certifications(self):
        """Test retrieving commercial property with environmental certifications."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create type-specific details as dict to avoid Pydantic typing issues
        type_details = {
            "space_type": "office",
            "usable_square_feet": 65000,
            "rentable_square_feet": 75000,
            "lease_type": "gross",
            "common_area_factor": 15.4,
            "ceiling_height": 12.0,
            "floor_count": 8,
            "zoning_code": "C-1",
            "permitted_uses": ["office", "professional", "service"],
            "signage_rights": True,
            "on_site_maintenance": True,
            "loading_area_details": "Loading area details",
            "signage_restrictions": "Signage restrictions",
            "common_area_maintenance_fee": 8500.00
        }
        
        # Use helper function that creates dict response
        mock_response = self.create_property_response(
            property_id=property_id,
            name="Green Office Complex",
            type_details=type_details,
            units=[]
        )
        
        with patch("Backend.api.properties.service.PropertyService.get_property") as mock_get:
            mock_get.return_value = mock_response
            
            response = self.client.get(f"/api/properties/{property_id}")
            
            assert response.status_code == 200
            data = response.json()
            # Test the actual fields that exist in the schema
            assert data["type_specific_details"]["space_type"] == "office"
            assert data["type_specific_details"]["usable_square_feet"] == 65000
            assert data["type_specific_details"]["lease_type"] == "gross"
    
    @pytest.mark.asyncio
    async def test_get_commercial_forbidden_non_owner(self):
        """Test that non-owners cannot retrieve commercial properties."""
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
    async def test_get_commercial_not_found(self):
        """Test retrieving non-existent commercial property."""
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