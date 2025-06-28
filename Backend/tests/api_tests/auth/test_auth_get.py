"""
Unit tests for GET operations in the auth API endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.models.user import User
from Backend.api.auth import get_current_user

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
        postal_code="12345",
        profile_image_url="https://example.com/avatar.jpg"
    )


def test_get_current_user_success():
    """Test successful retrieval of current user profile."""
    # Arrange
    test_user = create_test_user()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert data["first_name"] == test_user.first_name
    assert data["last_name"] == test_user.last_name
    assert data["user_type"] == test_user.user_type
    assert data["is_active"] == test_user.is_active
    assert data["is_admin"] == test_user.is_admin
    assert data["is_email_verified"] == test_user.is_email_verified
    assert data["phone"] == test_user.phone
    assert data["address"] == test_user.address
    assert data["city"] == test_user.city
    assert data["province"] == test_user.province
    assert data["postal_code"] == test_user.postal_code
    assert data["profile_image_url"] == test_user.profile_image_url


def test_get_current_user_unauthenticated():
    """Test that unauthenticated requests are rejected."""
    # Arrange
    # Override get_current_user to raise authentication error
    def mock_get_current_user():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.get("/api/auth/me")
    
    # Assert
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"


def test_get_current_user_inactive():
    """Test that inactive users can still retrieve their profile."""
    # Arrange
    test_user = create_test_user()
    test_user.is_active = False
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["is_active"] == False


def test_get_current_user_unverified_email():
    """Test that users with unverified emails can still retrieve their profile."""
    # Arrange
    test_user = create_test_user()
    test_user.is_email_verified = False
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["is_email_verified"] == False


def test_get_current_user_admin():
    """Test that admin users have is_admin flag set correctly."""
    # Arrange
    test_user = create_test_user(is_admin=True)
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] == True


def test_get_current_user_tenant_type():
    """Test that tenant users are properly identified."""
    # Arrange
    test_user = create_test_user(user_type="TENANT")
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["user_type"] == "TENANT"


def test_get_current_user_minimal_profile():
    """Test user with minimal profile (many None fields)."""
    # Arrange
    test_user = create_test_user()
    test_user.phone = None
    test_user.address = None
    test_user.city = None
    test_user.province = None
    test_user.postal_code = None
    test_user.profile_image_url = None
    test_user.first_name = None
    test_user.last_name = None
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert data["phone"] is None
    assert data["address"] is None
    assert data["city"] is None
    assert data["province"] is None
    assert data["postal_code"] is None
    assert data["profile_image_url"] is None
    assert data["first_name"] is None
    assert data["last_name"] is None