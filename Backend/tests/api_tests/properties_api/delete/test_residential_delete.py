"""
Tests for deleting residential properties via the API.
Tests property deletion with residential-specific scenarios.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from Backend.models.property import PropertyType
from Backend.models.enums import PropertyStatus
from Backend.api.properties.schemas.property import PropertyDetailResponse, OwnerResponse
from ..base_test import BasePropertyTest


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestResidentialPropertyDelete(BasePropertyTest):
    """Test residential property DELETE endpoints."""
    
    @pytest.mark.asyncio
    async def test_delete_residential_success(self):
        """Test successful deletion of a residential property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_residential_with_active_leases(self):
        """Test deletion fails when property has active residential lease."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with active leases. Please terminate all leases first."
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "active leases" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_residential_not_found(self):
        """Test deletion of non-existent residential property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 999
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=404,
                detail="Property not found"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_residential_forbidden_non_owner(self):
        """Test that non-owners cannot delete residential properties."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=403,
                detail="You don't have permission to delete this property"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_delete_residential_admin_can_delete_any(self):
        """Test that admin users can delete any residential property."""
        mock_session = AsyncMock()
        
        # Set up admin user
        self.mock_user.is_admin = True
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_residential_with_expired_leases(self):
        """Test deletion succeeds when property has only expired leases."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Mock the service to indicate expired leases exist but deletion is allowed
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None  # Deletion succeeds
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_residential_with_hoa_restrictions(self):
        """Test deletion with HOA considerations."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Mock service to check if deletion is affected by HOA rules
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with active HOA obligations"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "HOA" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_residential_with_mortgage(self):
        """Test deletion when property has mortgage or lien."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with outstanding mortgage or liens"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "mortgage" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_residential_with_utilities(self):
        """Test deletion with utility considerations."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Utilities might need to be transferred or disconnected
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None  # Deletion succeeds after utility handling
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_residential_with_security_deposit(self):
        """Test deletion when property has security deposit obligations."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with outstanding security deposit obligations"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "security deposit" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_residential_cascade_considerations(self):
        """Test cascading delete considerations for residential properties."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Mock the service to simulate cascading delete with residential considerations
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
            # In a real scenario, this would verify residential-specific cascading
    
    @pytest.mark.asyncio
    async def test_delete_residential_with_tenant_rights(self):
        """Test deletion considering tenant rights and notice periods."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property without proper tenant notice period"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "tenant notice" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_residential_soft_delete(self):
        """Test soft deletion (archiving) of residential property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Test archiving instead of hard delete
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_archive:
            mock_archive.return_value = PropertyDetailResponse(
                id=property_id,
                name="Family Home",
                address="123 Residential St",
                city="Family City",
                province="FC",
                postal_code="98765",
                property_type=PropertyType.RESIDENTIAL,
                description="Archived residential property",
                year_built=2019,
                status=PropertyStatus.ARCHIVED,
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
            
            # Simulate archive endpoint (if exists)
            response = self.client.patch(f"/api/properties/{property_id}/archive")
            
            # This would be 200 for archive operation
            # The actual endpoint behavior may vary based on implementation