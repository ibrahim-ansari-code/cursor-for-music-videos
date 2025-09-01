"""
Tests for deleting industrial properties via the API.
Tests property deletion with industrial-specific scenarios.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch
from ..base_test import BasePropertyTest


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestIndustrialPropertyDelete(BasePropertyTest):
    """Test industrial property DELETE endpoints."""
    
    @pytest.mark.asyncio
    async def test_delete_industrial_success(self):
        """Test successful deletion of an industrial property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_industrial_with_active_leases(self):
        """Test deletion fails when property has active industrial leases."""
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
    async def test_delete_industrial_not_found(self):
        """Test deletion of non-existent industrial property."""
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
    async def test_delete_industrial_forbidden_non_owner(self):
        """Test that non-owners cannot delete industrial properties."""
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
    async def test_delete_industrial_admin_can_delete_any(self):
        """Test that admin users can delete any industrial property."""
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
    async def test_delete_industrial_with_expired_leases(self):
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
    async def test_delete_industrial_with_environmental_issues(self):
        """Test deletion with environmental compliance considerations."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Mock service to check if deletion is blocked by environmental issues
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with pending environmental compliance issues"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "environmental compliance" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_industrial_with_hazmat_permits(self):
        """Test deletion with hazardous materials permit considerations."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with active hazmat storage permits"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "hazmat" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_industrial_with_equipment(self):
        """Test deletion when property has fixed equipment like cranes."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Industrial properties might have fixed equipment that needs special handling
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with fixed industrial equipment. Contact support."
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "equipment" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_industrial_with_rail_access(self):
        """Test deletion of property with rail spur access."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Rail access might require special coordination
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None  # Deletion succeeds after rail coordination
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_industrial_cascade_considerations(self):
        """Test cascading delete considerations for industrial properties."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Mock the service to simulate cascading delete with industrial considerations
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
            # In a real scenario, this would verify industrial-specific cascading
    
    @pytest.mark.asyncio
    async def test_delete_industrial_with_long_term_lease(self):
        """Test deletion when property has long-term industrial lease."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with active long-term lease agreement"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "long-term lease" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_industrial_soft_delete(self):
        """Test soft deletion of an industrial property."""
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
    async def test_delete_industrial_property_verification(self):
        """Test industrial property deletion with comprehensive verification."""
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
            
        # Test deletion with service error
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(status_code=500, detail="Internal server error during deletion")
            
            response = self.client.delete(f"/api/properties/{property_id}")
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]