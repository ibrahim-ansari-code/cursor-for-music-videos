"""
Unit tests for DELETE operations in the properties API endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException

from Backend.api.app import app
from Backend.models.user import User
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()

# Create a custom TestClient that sets the proper host header
class TestClientWithHost(TestClient):
    def request(self, method: str, url, **kwargs):
        # Always add localhost to headers if not present
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)

def create_test_user(user_id=None, email="test@example.com", user_type="LANDLORD", is_admin=False):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=is_admin,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )

# =============================================================================
# DELETE PROPERTY TESTS
# =============================================================================

def test_delete_property_success():
    """Test successful property deletion."""
    # Arrange
    property_id = 123
    owner_id = uuid4()
    fake_user = create_test_user(user_id=owner_id, email="owner@example.com")
    
    # Mock the service layer - successful deletion returns None
    with patch("Backend.api.properties.router.PropertyService.delete_property", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/properties/{property_id}")
            
            # Assert
            assert response.status_code == 204  # No Content
            assert response.text == ""  # Empty response body


def test_delete_property_with_active_leases():
    """Test 400 error when trying to delete property with active leases."""
    # Arrange
    property_id = 123
    owner_id = uuid4()
    fake_user = create_test_user(user_id=owner_id, email="owner@example.com")
    
    # Mock the service layer to raise 400 error
    with patch(
        "Backend.api.properties.router.PropertyService.delete_property",
        new=AsyncMock(side_effect=HTTPException(status_code=400, detail="Cannot delete property with active leases"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/properties/{property_id}")
            
            # Assert
            assert response.status_code == 400
            assert "Cannot delete property with active leases" in response.json()["detail"]


def test_delete_property_not_found():
    """Test 404 error when trying to delete non-existent property."""
    # Arrange
    property_id = 999
    fake_user = create_test_user(email="owner@example.com")
    
    # Mock the service layer to raise 404 error
    with patch(
        "Backend.api.properties.router.PropertyService.delete_property",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Property not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/properties/{property_id}")
            
            # Assert
            assert response.status_code == 404
            assert "Property not found" in response.json()["detail"]


def test_delete_property_forbidden():
    """Test 403 error when non-owner tries to delete property."""
    # Arrange
    property_id = 123
    other_user_id = uuid4()
    
    other_user = create_test_user(
        user_id=other_user_id,
        email="other@example.com"
    )
    
    # Mock the service layer to raise 403 error
    with patch(
        "Backend.api.properties.router.PropertyService.delete_property",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="You don't have permission to delete this property"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: other_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/properties/{property_id}")
            
            # Assert
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()


def test_delete_property_admin_can_delete_any():
    """Test that admin can delete properties they don't own."""
    # Arrange
    property_id = 456
    admin_id = uuid4()
    
    admin_user = create_test_user(
        user_id=admin_id,
        email="admin@example.com",
        user_type="ADMIN",
        is_admin=True
    )
    
    # Mock the service layer - successful deletion returns None
    with patch("Backend.api.properties.router.PropertyService.delete_property", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/properties/{property_id}")
            
            # Assert - Admin should be able to delete
            assert response.status_code == 204  # No Content
            assert response.text == ""  # Empty response body


def test_delete_property_with_pending_leases():
    """Test 400 error when trying to delete property with pending leases."""
    # Arrange
    property_id = 789
    owner_id = uuid4()
    fake_user = create_test_user(user_id=owner_id, email="owner@example.com")
    
    # Mock the service layer to raise 400 error specific to pending leases
    with patch(
        "Backend.api.properties.router.PropertyService.delete_property",
        new=AsyncMock(side_effect=HTTPException(status_code=400, detail="Cannot delete property with pending leases"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/properties/{property_id}")
            
            # Assert
            assert response.status_code == 400
            assert "Cannot delete property with pending leases" in response.json()["detail"]


def test_delete_property_with_expired_leases_allowed():
    """Test that property with only expired leases can be deleted."""
    # Arrange
    property_id = 321
    owner_id = uuid4()
    fake_user = create_test_user(user_id=owner_id, email="owner@example.com")
    
    # Mock the service layer - successful deletion returns None
    with patch("Backend.api.properties.router.PropertyService.delete_property", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/properties/{property_id}")
            
            # Assert - Should be able to delete
            assert response.status_code == 204  # No Content
            assert response.text == ""  # Empty response body


def test_delete_property_database_error_during_deletion():
    """Test error handling when database deletion fails."""
    # Arrange
    property_id = 654
    owner_id = uuid4()
    fake_user = create_test_user(user_id=owner_id, email="owner@example.com")
    
    # Mock the service layer to raise a generic database error
    with patch(
        "Backend.api.properties.router.PropertyService.delete_property",
        new=AsyncMock(side_effect=HTTPException(status_code=500, detail="Database commit failed"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/properties/{property_id}")
            
            # Assert
            assert response.status_code == 500
            assert "Database commit failed" in response.json()["detail"]


def test_delete_property_unauthorized():
    """Test that deleting a property requires authentication."""
    # Arrange - don't override get_current_user to simulate unauthenticated request
    property_id = 123
    
    # Only override the session
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.delete(f"/api/properties/{property_id}")
        
        # Assert - Accept either 401 or 403 as both indicate lack of proper auth
        assert response.status_code in [401, 403] 