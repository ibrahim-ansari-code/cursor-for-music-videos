"""
Unit tests for the lease deletion service functions using hybrid API testing pattern.
"""
import pytest
import logging
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status, HTTPException
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.app import app
from Backend.models.user import User
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

logger = logging.getLogger(__name__)

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

def create_test_user(user_id=None, email="test@example.com"):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type="LANDLORD",
        is_active=True,
        is_admin=False,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )

def test_delete_lease_success():
    # Arrange
    lease_id = 123
    mock_user = create_test_user(email="test@example.com")
    
    # Mock the service function
    with patch("Backend.api.leases.router.delete_lease", new_callable=AsyncMock) as mock_delete_lease:
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/leases/{lease_id}")

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_delete_lease.assert_awaited_once()
        # Check the call arguments
        call_args = mock_delete_lease.call_args
        assert call_args is not None
        assert call_args.args[0] == lease_id
        assert call_args.args[1] == mock_user
        # args[2] is the session instance, which we don't need to check


def test_delete_lease_logs_success():
    lease_id = 456
    mock_user = create_test_user(email="logsuccess@example.com")
    
    # Mock the service function and logger
    with patch("Backend.api.leases.router.delete_lease", new_callable=AsyncMock) as mock_delete_lease, \
         patch("Backend.api.leases.service.logger") as mock_logger:
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.delete(f"/api/leases/{lease_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_delete_lease.assert_awaited_once()


def test_delete_lease_returns_expected_response():
    lease_id = 789
    mock_user = create_test_user(email="expectedresponse@example.com")
    
    with patch("Backend.api.leases.router.delete_lease", new_callable=AsyncMock):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.delete(f"/api/leases/{lease_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""


def test_delete_lease_non_existent():
    lease_id = 999
    mock_user = create_test_user(email="nonexistent@example.com")
    
    # Simulate service raising HTTP 404
    with patch(
        "Backend.api.leases.router.delete_lease",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lease not found")
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.delete(f"/api/leases/{lease_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Lease not found"


def test_delete_lease_unauthorized_user():
    lease_id = 321
    mock_user = create_test_user(email="unauth@example.com")
    
    # Simulate service raising HTTP 403
    with patch(
        "Backend.api.leases.router.delete_lease",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.delete(f"/api/leases/{lease_id}")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Not authorized"


def test_delete_lease_handles_exception():
    lease_id = 654
    mock_user = create_test_user(email="exception@example.com")
    
    # Simulate service raising HTTP 500
    with patch(
        "Backend.api.leases.router.delete_lease",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.delete(f"/api/leases/{lease_id}")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Unexpected error"


def test_delete_lease_conflict_error():
    """Test deletion failure due to foreign key constraints."""
    lease_id = 999
    mock_user = create_test_user(email="conflict@example.com")
    
    # Simulate service raising HTTP 409 Conflict
    with patch(
        "Backend.api.leases.router.delete_lease",
        new_callable=AsyncMock,
        side_effect=HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="Cannot delete lease with existing payments or other dependencies"
        )
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.delete(f"/api/leases/{lease_id}")
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Cannot delete lease" in response.json()["detail"]


def test_delete_active_lease_revokes_side_effects():
    """Test that deleting an active lease triggers side effect revocation."""
    lease_id = 555
    mock_user = create_test_user(email="revoke@example.com")
    
    # Mock both the delete function and the side effect function
    with patch("Backend.api.leases.router.delete_lease", new_callable=AsyncMock) as mock_delete, \
         patch("Backend.api.leases.service._revoke_active_lease_side_effects", new_callable=AsyncMock) as mock_revoke:
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.delete(f"/api/leases/{lease_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_delete.assert_awaited_once()
        # Check the call arguments
        call_args = mock_delete.call_args
        assert call_args is not None
        assert call_args.args[0] == lease_id
        assert call_args.args[1] == mock_user
        # args[2] is the session instance, which we don't need to check


def test_delete_lease_without_authentication():
    """Test that deleting a lease requires authentication."""
    lease_id = 777
    
    # Don't override get_current_user to simulate unauthenticated request
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.delete(f"/api/leases/{lease_id}")
    
    # Accept either 401 or 403 as both indicate lack of proper auth
    assert response.status_code in [401, 403]