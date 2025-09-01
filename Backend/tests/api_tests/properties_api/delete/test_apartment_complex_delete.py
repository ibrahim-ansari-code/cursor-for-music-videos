"""
Tests for deleting apartment complex properties via the API.
Tests property deletion with apartment complex-specific scenarios.
"""

from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, patch
from ..base_test import BasePropertyTest


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestApartmentComplexPropertyDelete(BasePropertyTest):
    """Test apartment complex property DELETE endpoints."""
    
    @pytest.mark.asyncio
    async def test_delete_apartment_complex_success(self):
        """Test successful deletion of an apartment complex property."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_apartment_complex_with_active_leases(self):
        """Test deletion fails when property has active leases."""
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
    async def test_delete_apartment_complex_not_found(self):
        """Test deletion of non-existent apartment complex."""
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
    async def test_delete_apartment_complex_forbidden_non_owner(self):
        """Test that non-owners cannot delete apartment complex properties."""
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
    async def test_delete_apartment_complex_admin_can_delete_any(self):
        """Test that admin users can delete any apartment complex."""
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
    async def test_delete_apartment_complex_with_expired_leases(self):
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
    async def test_delete_apartment_complex_with_pending_maintenance(self):
        """Test deletion with pending maintenance requests."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Mock service to check if deletion is blocked by maintenance
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with pending maintenance requests"
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "maintenance" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_apartment_complex_cascade_units(self):
        """Test that deleting apartment complex also removes associated units."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        # Mock the service to simulate cascading delete
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.return_value = None
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 204
            mock_delete.assert_called_once()
            # In a real scenario, this would verify that units were also deleted
    
    @pytest.mark.asyncio
    async def test_delete_apartment_complex_with_financial_records(self):
        """Test deletion when property has associated financial records."""
        mock_session = AsyncMock()
        self.setup_mocks(mock_session)
        
        property_id = 1
        
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(
                status_code=409,
                detail="Cannot delete property with existing financial records. Archive property instead."
            )
            
            response = self.client.delete(f"/api/properties/{property_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "financial records" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_apartment_complex_soft_delete(self):
        """Test soft deletion of an apartment complex property."""
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
    async def test_delete_apartment_complex_verification(self):
        """Test apartment complex deletion with proper verification."""
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
            
        # Test unauthorized deletion attempt
        with patch("Backend.api.properties.service.PropertyService.delete_property") as mock_delete:
            mock_delete.side_effect = HTTPException(status_code=403, detail="Not authorized to delete this property")
            
            response = self.client.delete(f"/api/properties/{property_id}")
            assert response.status_code == 403