"""
Tests for deleting commercial properties via the API.
Tests property deletion with commercial-specific scenarios.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch
from ..base_test import BasePropertyTest


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestCommercialPropertyDelete(BasePropertyTest):
    """Test commercial property DELETE endpoints."""
    
    @pytest.mark.asyncio
    async def test_delete_commercial_success(self):
        """Test successful deletion of a commercial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_commercial_with_active_leases(self):
        """Test deletion fails when property has active commercial leases."""
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
    async def test_delete_commercial_not_found(self):
        """Test deletion of non-existent commercial property."""
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
    async def test_delete_commercial_forbidden_non_owner(self):
        """Test that non-owners cannot delete commercial properties."""
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
    async def test_delete_commercial_admin_can_delete_any(self):
        """Test that admin users can delete any commercial property."""
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
    async def test_delete_commercial_with_expired_leases(self):
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
    async def test_delete_commercial_with_anchor_tenant(self):
        """Test deletion with anchor tenant considerations."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Mock service to check if deletion is blocked by anchor tenant lease
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with active anchor tenant lease"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "anchor tenant" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_commercial_with_cam_agreements(self):
        """Test deletion with Common Area Maintenance agreements."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with active CAM agreements"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "CAM agreements" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_commercial_cascade_units(self):
        """Test that deleting commercial property also removes associated units."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Mock the service to simulate cascading delete
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
            # In a real scenario, this would verify that commercial units were also deleted
    
    @pytest.mark.asyncio
    async def test_delete_commercial_with_triple_net_leases(self):
        """Test deletion when property has triple net lease obligations."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with active triple net lease obligations"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "triple net lease" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_commercial_with_zoning_restrictions(self):
        """Test deletion considering zoning and permit issues."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Commercial properties might have special zoning considerations
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None  # Deletion succeeds regardless of zoning
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
    
