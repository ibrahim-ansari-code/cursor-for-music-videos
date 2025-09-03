"""
Tests for updating commercial properties via the API.
Tests property updates with commercial-specific type details.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from uuid import uuid4
from decimal import Decimal

from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from Backend.api.properties.schemas import PropertyDetailResponse, OwnerResponse
from Backend.api.properties.schemas.types.commercial import CommercialPropertyDetailsResponse
from ..base_test import BasePropertyTest


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestCommercialPropertyUpdate(BasePropertyTest):
    """Test commercial property UPDATE endpoints."""
    
    @pytest.mark.asyncio
    async def test_update_commercial_success(self):
        """Test successful update of a commercial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Create update data
        update_data = {
            "name": "Updated Tech Plaza",
            "description": "Renovated commercial building in tech district",
            "type_specific_details": {
                "property_type": "Commercial",  # Discriminator field
                "space_type": "office",
                "usable_square_feet": 15000,
                "rentable_square_feet": 16500,
                "lease_type": "triple_net",
                "common_area_factor": 10.0,
                "zoning_code": "C-3",
                "ceiling_height": 12.5,
                "has_loading_area": True,
                "loading_docks_count": 2
            }
        }
        
        # Create the updated property response
        type_details = CommercialPropertyDetailsResponse(
            space_type="office",
            usable_square_feet=15000,
            rentable_square_feet=16500,
            common_area_factor=Decimal("10.0"),
            lease_type="triple_net",
            zoning_code="C-3",
            ceiling_height=Decimal("12.5"),
            has_loading_area=True,
            loading_docks_count=2,
            permitted_uses=["office", "retail"],
            business_licensing_compliance={"status": "compliant"},
            loading_area_details="Loading area details",
            signage_restrictions="Signage restrictions",
            common_area_maintenance_fee=Decimal("10.00")
        )
        
        updated_property = PropertyDetailResponse(
            id=property_id,
            name="Updated Tech Plaza",
            address="123 Tech St",
            city="Tech City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.COMMERCIAL,
            description="Renovated commercial building in tech district",
            year_built=2020,
            status=PropertyStatus.ACTIVE,
            type_specific_details=type_details,
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
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Tech Plaza"
            assert data["description"] == "Renovated commercial building in tech district"
            assert data["type_specific_details"]["space_type"] == "office"
    
    @pytest.mark.asyncio
    async def test_update_commercial_not_found(self):
        """Test updating non-existent commercial property."""
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
    async def test_update_commercial_forbidden_non_owner(self):
        """Test that non-owners cannot update commercial properties."""
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
    async def test_update_commercial_validation_error(self):
        """Test update with invalid data."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Invalid data - rentable square feet less than usable
        update_data = {
            "type_specific_details": {
                "property_type": "Commercial",  # Discriminator field
                "space_type": "office",
                "usable_square_feet": 10000,
                "rentable_square_feet": 8000,  # Less than usable - should be invalid
                "lease_type": "gross"
            }
        }
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.side_effect = HTTPException(
                status_code=422,
                detail="Rentable square feet should be >= usable square feet"
            )
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_update_commercial_partial_update(self):
        """Test partial update of commercial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Only update description
        update_data = {
            "description": "Prime location with modern amenities and tech infrastructure"
        }
        
        updated_property = PropertyDetailResponse(
            id=property_id,
            name="Tech Plaza",
            address="123 Tech St",
            city="Tech City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.COMMERCIAL,
            description="Prime location with modern amenities and tech infrastructure",
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
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["description"] == "Prime location with modern amenities and tech infrastructure"
            assert data["name"] == "Tech Plaza"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_commercial_admin_can_update_any(self):
        """Test that admin users can update any commercial property."""
        mock_session = AsyncMock()
        
        # Set up admin user
        self.mock_user.is_admin = True
        self.setup_mocks(mock_session)
        
        property_id = 1
        update_data = {
            "name": "Admin Updated Plaza",
            "type_specific_details": {
                "property_type": "Commercial",  # Discriminator field
                "space_type": "retail",
                "usable_square_feet": 8000,
                "rentable_square_feet": 9000,
                "lease_type": "percentage"
            }
        }
        
        type_details = CommercialPropertyDetailsResponse(
            space_type="retail",
            usable_square_feet=8000,
            rentable_square_feet=9000,
            lease_type="percentage",
            zoning_code="C-3",
            ceiling_height=Decimal("12.5"),
            loading_area_details="Loading area details",
            signage_restrictions="Signage restrictions",
            common_area_maintenance_fee=Decimal("350.00"),
            common_area_factor=Decimal("10.0"),
            on_site_maintenance=True
        )
        
        updated_property = PropertyDetailResponse(
            id=property_id,
            name="Admin Updated Plaza",
            address="123 Tech St",
            city="Tech City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.COMMERCIAL,
            description="Test property",
            year_built=2020,
            status=PropertyStatus.ACTIVE,
            type_specific_details=type_details,
            user_id=uuid4(),  # Different owner
            created_at=datetime.now(),
            updated_at=datetime.now(),
            owner=OwnerResponse(
                id=uuid4(),
                first_name="Other",
                last_name="Owner",
                email="other@example.com"
            ),
            units=[],
            stats=None
        )
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Admin Updated Plaza"
            assert data["type_specific_details"]["space_type"] == "retail"
    
    @pytest.mark.asyncio
    async def test_update_commercial_with_other_lease_type(self):
        """Test updating commercial property with 'other' lease type."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        update_data = {
            "type_specific_details": {
                "property_type": "Commercial",  # Discriminator field
                "space_type": "office",
                "usable_square_feet": 10000,  # Required field
                "rentable_square_feet": 11000,  # Required field
                "lease_type": "other"
            }
        }
        
        type_details = CommercialPropertyDetailsResponse(
            space_type="office",
            usable_square_feet=10000,
            rentable_square_feet=11000,
            lease_type="other",
            zoning_code="C-3",
            ceiling_height=Decimal("12.5"),
            loading_area_details="Loading area details",
            signage_restrictions="Signage restrictions",
            common_area_maintenance_fee=Decimal("350.00"),
            common_area_factor=Decimal("10.0"),
            on_site_maintenance=True
        )
        
        updated_property = PropertyDetailResponse(
            id=property_id,
            name="Tech Plaza",
            address="123 Tech St",
            city="Tech City",
            province="TC",
            postal_code="12345",
            property_type=PropertyType.COMMERCIAL,
            description="Test property",
            year_built=2020,
            status=PropertyStatus.ACTIVE,
            type_specific_details=type_details,
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
        
        with patch("Backend.api.properties.service.PropertyService.update_property") as mock_update:
            mock_update.return_value = updated_property
            
            response = self.client.put(f"/api/properties/{property_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["type_specific_details"]["lease_type"] == "other"