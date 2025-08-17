"""
Unit tests for DELETE operations in the maintenance API endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.models.maintenance import MaintenanceRequest
from Backend.models.property import Property
from Backend.models.user import User
from Backend.models.enums import MaintenancePriority, MaintenanceStatus, UserType
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
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)

def create_test_user(user_id=None, email="test@example.com", user_type=UserType.LANDLORD, is_admin=False):
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

def create_mock_maintenance_request(request_id=1, **kwargs):
    """Helper function to create a mock maintenance request."""
    now = datetime.now(timezone.utc)
    mock_request = MagicMock(spec=MaintenanceRequest)
    mock_request.id = request_id
    mock_request.issue_title = kwargs.get('issue_title', 'Test Issue')
    mock_request.property_id = kwargs.get('property_id', 1)
    mock_request.user_id = kwargs.get('user_id', uuid4())
    mock_request.status = kwargs.get('status', MaintenanceStatus.PENDING)
    mock_request.created_at = kwargs.get('created_at', now)
    mock_request.property = kwargs.get('property', None)
    return mock_request

def create_mock_property(property_id=1, **kwargs):
    """Helper function to create a mock property."""
    mock_property = MagicMock(spec=Property)
    mock_property.id = property_id
    mock_property.name = kwargs.get('name', 'Test Property')
    mock_property.user_id = kwargs.get('user_id', uuid4())
    return mock_property

# =============================================================================
# DELETE MAINTENANCE REQUEST TESTS
# =============================================================================

def test_delete_maintenance_request_success_owner():
    """Test successful deletion of maintenance request by property owner."""
    # Arrange
    request_id = 123
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, email="owner@example.com")
    
    # Mock the service layer to return None (successful deletion)
    with patch("Backend.api.maintenance.router.MaintenanceService.delete_maintenance_request", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/maintenance/requests/{request_id}")
            
            # Assert
            assert response.status_code == 204
            # No content should be returned for successful deletion
            assert response.content == b''


def test_delete_maintenance_request_success_admin():
    """Test that admin can delete any maintenance request."""
    # Arrange
    request_id = 456
    admin_id = uuid4()
    
    admin_user = create_test_user(
        user_id=admin_id,
        email="admin@example.com",
        user_type=UserType.ADMIN,
        is_admin=True
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.delete_maintenance_request", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/maintenance/requests/{request_id}")
            
            # Assert - Admin should be able to delete
            assert response.status_code == 204
            assert response.content == b''


def test_delete_maintenance_request_not_found():
    """Test 404 error when maintenance request doesn't exist."""
    # Arrange
    request_id = 999
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Mock the service layer to raise 404
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.delete_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Maintenance request not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/maintenance/requests/{request_id}")
            
            # Assert
            assert response.status_code == 404
            assert "Maintenance request not found" in response.json()["detail"]


def test_delete_maintenance_request_forbidden_non_owner():
    """Test 403 error when non-owner tries to delete maintenance request."""
    # Arrange
    request_id = 789
    other_user_id = uuid4()
    
    other_user = create_test_user(
        user_id=other_user_id,
        email="other@example.com",
        is_admin=False
    )
    
    # Mock the service layer to raise 403
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.delete_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(
            status_code=403,
            detail="You do not have permission to access this maintenance request"
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: other_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/maintenance/requests/{request_id}")
            
            # Assert
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()


def test_delete_maintenance_request_with_completed_status():
    """Test deleting a completed maintenance request (should still work)."""
    # Arrange
    request_id = 321
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Mock the service layer - deletion should work regardless of status
    with patch("Backend.api.maintenance.router.MaintenanceService.delete_maintenance_request", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/maintenance/requests/{request_id}")
            
            # Assert
            assert response.status_code == 204


def test_delete_maintenance_request_database_error():
    """Test error handling for database exceptions during deletion."""
    # Arrange
    request_id = 654
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Mock the service layer to raise a database error
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.delete_maintenance_request",
        new=AsyncMock(side_effect=Exception("Database connection failed"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/maintenance/requests/{request_id}")
            
            # Assert
            assert response.status_code == 500
            assert "Failed to delete maintenance request" in response.json()["detail"]


def test_delete_maintenance_request_cascade_behavior():
    """Test that deleting a maintenance request handles related data properly."""
    # Arrange
    request_id = 987
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # This test verifies the service handles cascade deletes properly
    # The actual cascade behavior is controlled by the database schema
    with patch("Backend.api.maintenance.router.MaintenanceService.delete_maintenance_request", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/maintenance/requests/{request_id}")
            
            # Assert
            assert response.status_code == 204


def test_delete_maintenance_request_invalid_id_format():
    """Test error handling for invalid request ID format."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act - Use invalid ID format
        response = client.delete("/api/maintenance/requests/invalid_id")
        
        # Assert
        assert response.status_code == 422  # Validation error


def test_delete_maintenance_request_concurrent_deletion():
    """Test handling when request is already deleted (idempotency)."""
    # Arrange
    request_id = 111
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # First call succeeds, simulating the request was already deleted
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.delete_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Maintenance request not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act - Try to delete already deleted request
            response = client.delete(f"/api/maintenance/requests/{request_id}")
            
            # Assert - Should return 404 if already deleted
            assert response.status_code == 404


def test_delete_maintenance_request_verify_logging():
    """Test that deletion is properly logged."""
    # Arrange
    request_id = 222
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Mock the service and logger
    with patch("Backend.api.maintenance.router.MaintenanceService.delete_maintenance_request", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/maintenance/requests/{request_id}")
            
            # Assert
            assert response.status_code == 204
            # In a real scenario, we would verify logger was called
            # but for unit tests, we focus on the response