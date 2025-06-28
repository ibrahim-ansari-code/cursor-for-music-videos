"""
API tests for password-related operations in the auth API endpoint.
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
        updated_at=now
    )


# =============================================================================
# VERIFY PASSWORD TESTS
# =============================================================================

@patch('Backend.api.auth.service.AuthService.verify_user_password')
def test_verify_password_success(mock_verify):
    """Test successful password verification."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    mock_verify.return_value = True
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    request_data = {
        "password": "correct_password"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/verify-password",
        json=request_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "verified" in data["message"].lower()
    mock_verify.assert_called_once_with(
        email=test_user.email,
        password="correct_password"
    )


@patch('Backend.api.auth.service.AuthService.verify_user_password')
def test_verify_password_incorrect(mock_verify):
    """Test password verification with incorrect password."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    mock_verify.return_value = False
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    request_data = {
        "password": "wrong_password"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/verify-password",
        json=request_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 401
    assert "Invalid password" in response.json()["detail"]


def test_verify_password_unauthenticated():
    """Test password verification without authentication."""
    # Arrange
    request_data = {
        "password": "some_password"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/verify-password",
        json=request_data
    )
    
    # Assert
    assert response.status_code == 403  # HTTPBearer returns 403 when no auth header is present
    assert "Not authenticated" in response.json()["detail"]


def test_verify_password_missing_password():
    """Test password verification with missing password."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/verify-password",
        json={},
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 422
    assert "Field required" in response.json()["detail"][0]["msg"]


# =============================================================================
# CHANGE PASSWORD TESTS
# =============================================================================

@patch('Backend.api.auth.service.AuthService.change_user_password')
def test_change_password_success(mock_change):
    """Test successful password change."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    mock_change.return_value = True
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    request_data = {
        "current_password": "old_password",
        "new_password": "NewSecure123!@#"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/change-password",
        json=request_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "changed successfully" in data["message"]
    mock_change.assert_called_once_with(
        email=test_user.email,
        current_password="old_password",
        new_password="NewSecure123!@#"
    )


@patch('Backend.api.auth.service.AuthService.change_user_password')
def test_change_password_wrong_current(mock_change):
    """Test password change with incorrect current password."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Mock service to raise HTTPException for wrong password
    mock_change.side_effect = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Current password is incorrect"
    )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    request_data = {
        "current_password": "wrong_password",
        "new_password": "NewSecure123!@#"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/change-password",
        json=request_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 401
    assert "Current password is incorrect" in response.json()["detail"]


def test_change_password_weak_new_password():
    """Test password change with weak new password."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    request_data = {
        "current_password": "old_password",
        "new_password": "weak"  # Too short, no uppercase, no special chars
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/change-password",
        json=request_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 422
    # Check for validation error about password length
    error_msgs = [err["msg"] for err in response.json()["detail"]]
    assert any("at least 8 characters" in msg for msg in error_msgs)


def test_change_password_same_as_current():
    """Test password change with new password same as current."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    request_data = {
        "current_password": "SamePass123!@#",
        "new_password": "SamePass123!@#"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/change-password",
        json=request_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 422
    error_msgs = [err["msg"] for err in response.json()["detail"]]
    assert any("different from current password" in msg for msg in error_msgs)


def test_change_password_unauthenticated():
    """Test password change without authentication."""
    # Arrange
    request_data = {
        "current_password": "old_password",
        "new_password": "NewSecure123!@#"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/change-password",
        json=request_data
    )
    
    # Assert
    assert response.status_code == 403  # HTTPBearer returns 403 when no auth header is present
    assert "Not authenticated" in response.json()["detail"]


def test_change_password_missing_fields():
    """Test password change with missing fields."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    # Test missing current_password
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/change-password",
        json={"new_password": "NewSecure123!@#"},
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 422
    assert "Field required" in response.json()["detail"][0]["msg"]
    
    # Test missing new_password
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "old_password"},
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 422
    assert "Field required" in response.json()["detail"][0]["msg"]


def test_change_password_invalid_format():
    """Test password change with various invalid password formats."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    client = TestClientWithHost(app)
    
    # Test cases for invalid passwords
    invalid_passwords = [
        ("nouppercase123!", "uppercase letter"),
        ("NOLOWERCASE123!", "lowercase letter"),
        ("NoNumbers!@#", "number"),
        ("NoSpecialChars123", "special character"),
        ("Short1!", "8 characters")
    ]
    
    for invalid_pass, expected_error in invalid_passwords:
        request_data = {
            "current_password": "old_password",
            "new_password": invalid_pass
        }
        
        response = client.post(
            "/api/auth/change-password",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422
        error_msgs = [err["msg"] for err in response.json()["detail"]]
        assert any(expected_error in msg for msg in error_msgs), f"Expected error about {expected_error} for password: {invalid_pass}"


@patch('Backend.api.auth.service.AuthService.change_user_password')
def test_change_password_service_error(mock_change):
    """Test password change when service raises unexpected error."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    # Mock service to raise generic exception
    mock_change.side_effect = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred"
    )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    request_data = {
        "current_password": "old_password",
        "new_password": "NewSecure123!@#"
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/change-password",
        json=request_data,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 500
    assert "unexpected error" in response.json()["detail"].lower()