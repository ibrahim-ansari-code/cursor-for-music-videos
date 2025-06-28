"""
Unit tests for PUT operations in the auth API endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
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
        is_email_verified=True,
        created_at=now,
        updated_at=now,
        phone="1234567890",
        address="123 Test St",
        city="Test City",
        province="TS",
        postal_code="12345"
    )


@patch('Backend.api.auth.service.AuthService.update_user_profile')
def test_update_profile_success(mock_update):
    """Test successful profile update."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Mock the service response
    updated_user = create_test_user()
    updated_user.first_name = "Updated"
    updated_user.last_name = "Name"
    updated_user.phone = "9876543210"
    mock_update.return_value = updated_user
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    update_data = {
        "first_name": "Updated",
        "last_name": "Name",
        "phone": "9876543210"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/auth/users/{test_user.id}/profile",
        json=update_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name"
    assert data["phone"] == "9876543210"
    mock_update.assert_called_once()


def test_update_profile_unauthorized_different_user():
    """Test that users cannot update other users' profiles."""
    # Arrange
    test_user = create_test_user()
    other_user_id = uuid4()
    mock_session = AsyncMock()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    update_data = {
        "first_name": "Hacker",
        "last_name": "Attempt"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/auth/users/{other_user_id}/profile",
        json=update_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]


@patch('Backend.api.auth.service.AuthService.update_user_profile')
def test_update_profile_admin_for_any_user(mock_update):
    """Test that admin users can update any user's profile."""
    # Arrange
    admin_user = create_test_user(is_admin=True)
    other_user_id = uuid4()
    mock_session = AsyncMock()
    
    # Mock the service response
    updated_user = create_test_user(user_id=other_user_id)
    updated_user.first_name = "Admin"
    updated_user.last_name = "Updated"
    mock_update.return_value = updated_user
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    update_data = {
        "first_name": "Admin",
        "last_name": "Updated"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/auth/users/{other_user_id}/profile",
        json=update_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Admin"
    assert data["last_name"] == "Updated"


@patch('Backend.api.auth.service.AuthService.update_user_profile')
def test_update_profile_partial_update(mock_update):
    """Test partial profile update (only some fields)."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Mock the service response
    updated_user = create_test_user()
    updated_user.phone = "5555555555"
    mock_update.return_value = updated_user
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    # Only update phone
    update_data = {
        "phone": "5555555555"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/auth/users/{test_user.id}/profile",
        json=update_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "5555555555"
    # Other fields should remain unchanged
    assert data["first_name"] == test_user.first_name
    assert data["last_name"] == test_user.last_name


@patch('Backend.api.auth.service.AuthService.update_user_profile')
def test_update_profile_address_fields(mock_update):
    """Test updating address-related fields."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Mock the service response
    updated_user = create_test_user()
    updated_user.address = "456 New St"
    updated_user.city = "New City"
    updated_user.province = "NC"
    updated_user.postal_code = "54321"
    mock_update.return_value = updated_user
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    update_data = {
        "address": "456 New St",
        "city": "New City",
        "province": "NC",
        "postal_code": "54321"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/auth/users/{test_user.id}/profile",
        json=update_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["address"] == "456 New St"
    assert data["city"] == "New City"
    assert data["province"] == "NC"
    assert data["postal_code"] == "54321"


@patch('Backend.api.auth.service.AuthService.update_user_profile')
def test_update_profile_clear_optional_fields(mock_update):
    """Test clearing optional fields by setting them to None."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Mock the service response
    updated_user = create_test_user()
    updated_user.phone = None
    updated_user.address = None
    mock_update.return_value = updated_user
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    update_data = {
        "phone": None,
        "address": None
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/auth/users/{test_user.id}/profile",
        json=update_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] is None
    assert data["address"] is None


def test_update_profile_empty_body():
    """Test profile update with empty body (no changes).
    
    Note: We intentionally accept empty update requests (status 200) as this is
    a common pattern in RESTful APIs. An empty update is essentially a no-op
    and doesn't cause any harm. Some APIs might choose to return 400 Bad Request
    for empty updates, but we've chosen to be more permissive.
    """
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/auth/users/{test_user.id}/profile",
        json={},
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    # Should still succeed even with no fields to update
    assert response.status_code == 200


def test_update_profile_invalid_field():
    """Test profile update with invalid field."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    # Try to update a field that doesn't exist in ProfileUpdateRequest
    update_data = {
        "email": "newemail@example.com",  # Email cannot be updated via profile endpoint
        "is_admin": True  # Also cannot be updated
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/auth/users/{test_user.id}/profile",
        json=update_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    # Should reject unknown fields with 422 validation error
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("Extra inputs are not permitted" in err["msg"] for err in error_detail)


@patch('Backend.api.auth.service.AuthService.update_user_profile')
def test_update_profile_service_error(mock_update):
    """Test profile update when service raises an error."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Mock service to raise an exception
    mock_update.side_effect = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database error"
    )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    update_data = {
        "first_name": "Error",
        "last_name": "Test"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/auth/users/{test_user.id}/profile",
        json=update_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 500
    assert "Database error" in response.json()["detail"]