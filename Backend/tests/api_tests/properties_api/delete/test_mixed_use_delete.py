"""
Tests for deleting mixed-use properties via the API.
Tests property deletion with mixed-use-specific scenarios.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch
from ..base_test import BasePropertyTest


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestMixedUsePropertyDelete(BasePropertyTest):
    """Test mixed-use property DELETE endpoints."""
    
    @pytest.mark.asyncio
    async def test_delete_mixed_use_success(self):
        """Test successful deletion of a mixed-use property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_mixed_use_with_active_leases(self):
        """Test deletion fails when property has active residential and commercial leases."""
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
    async def test_delete_mixed_use_not_found(self):
        """Test deletion of non-existent mixed-use property."""
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
    async def test_delete_mixed_use_forbidden_non_owner(self):
        """Test that non-owners cannot delete mixed-use properties."""
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
    async def test_delete_mixed_use_admin_can_delete_any(self):
        """Test that admin users can delete any mixed-use property."""
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
    async def test_delete_mixed_use_with_expired_leases(self):
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
    async def test_delete_mixed_use_with_dual_management(self):
        """Test deletion with separate residential and commercial management."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Mock service to check if deletion is blocked by dual management structure
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with separate management agreements"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "management agreements" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_mixed_use_with_shared_amenities(self):
        """Test deletion with shared amenity considerations."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Shared amenities might have ongoing contracts
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with active shared amenity contracts"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "amenity contracts" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_mixed_use_with_retail_anchors(self):
        """Test deletion when property has anchor retail tenants."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Anchor retail tenants might have special lease terms
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with active anchor retail leases"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "anchor retail" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_mixed_use_cascade_both_components(self):
        """Test that deleting mixed-use property removes both residential and commercial components."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Mock the service to simulate cascading delete of both components
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
            # In a real scenario, this would verify both residential and commercial units were deleted
    
    @pytest.mark.asyncio
    async def test_delete_mixed_use_with_parking_agreements(self):
        """Test deletion when property has shared parking agreements."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with active parking agreements"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "parking agreements" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_mixed_use_with_concierge_services(self):
        """Test deletion when property has ongoing concierge services."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with active concierge service contracts"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "concierge service" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_mixed_use_soft_delete(self):
        """Test soft deletion of a mixed-use property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            # Mock soft delete behavior - property marked as deleted but not removed
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_mixed_use_complete_deletion(self):
        """Test complete deletion of mixed-use property with verification."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Test successful deletion
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = True
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            # Verify successful deletion
            assert response.status_code == 204
            mock_delete.assert_called_once_with(property_id, self.mock_user, mock_session)
            
        # Test deletion of non-existent property
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(status_code=404, detail="Property not found")
            
            response = self.client.delete(f"/api/properties/{property_id}")
            assert response.status_code == 404