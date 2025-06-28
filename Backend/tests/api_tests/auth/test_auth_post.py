"""
Unit tests for POST operations in the auth API endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.models.user import User
from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.config import settings

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


@patch('Backend.api.auth.service.upload_avatar_to_blob')
def test_upload_avatar_success(mock_upload):
    """Test successful avatar upload."""
    # Arrange
    test_user = create_test_user()
    mock_session = AsyncMock()
    mock_upload.return_value = "https://storage.blob.core.windows.net/avatars/test-avatar.jpg"
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    # Create mock file
    file_content = b"fake image content"
    files = {"file": ("avatar.jpg", file_content, "image/jpeg")}
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/auth/users/{test_user.id}/avatar",
        files=files,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["profile_image_url"] == "https://storage.blob.core.windows.net/avatars/test-avatar.jpg"
    mock_upload.assert_called_once()
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


def test_upload_avatar_unauthorized_different_user():
    """Test that users cannot upload avatars for other users."""
    # Arrange
    test_user = create_test_user()
    other_user_id = uuid4()
    mock_session = AsyncMock()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    # Create mock file
    file_content = b"fake image content"
    files = {"file": ("avatar.jpg", file_content, "image/jpeg")}
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/auth/users/{other_user_id}/avatar",
        files=files,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]


@patch('Backend.api.auth.service.upload_avatar_to_blob')
def test_upload_avatar_admin_for_any_user(mock_upload):
    """Test that admin users can upload avatars for any user."""
    # Arrange
    admin_user = create_test_user(is_admin=True)
    other_user_id = uuid4()
    mock_session = AsyncMock()
    mock_upload.return_value = "https://storage.blob.core.windows.net/avatars/admin-uploaded.jpg"
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    # Create mock file
    file_content = b"fake image content"
    files = {"file": ("avatar.jpg", file_content, "image/jpeg")}
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/auth/users/{other_user_id}/avatar",
        files=files,
        headers={"Authorization": "Bearer test-token"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["profile_image_url"] == "https://storage.blob.core.windows.net/avatars/admin-uploaded.jpg"


@patch('Backend.api.auth.service.AuthService.handle_webhook_user_sync')
def test_webhook_user_sync_success(mock_sync):
    """Test successful webhook user sync."""
    # Arrange
    mock_session = AsyncMock()
    mock_sync.return_value = {"message": "User created successfully"}
    
    # Set webhook secret
    with patch.object(settings, 'SUPABASE_WEBHOOK_SECRET', 'test-webhook-secret'):
        app.dependency_overrides[get_session] = lambda: mock_session
        
        webhook_payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": str(uuid4()),
                "email": "newuser@example.com",
                "raw_user_meta_data": {
                    "first_name": "New",
                    "last_name": "User"
                }
            }
        }
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=webhook_payload,
            headers={"X-Webhook-Secret": "test-webhook-secret"}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "User created successfully"
        mock_sync.assert_called_once()


def test_webhook_user_sync_invalid_secret():
    """Test webhook rejection with invalid secret."""
    # Arrange
    mock_session = AsyncMock()
    
    # Set webhook secret
    with patch.object(settings, 'SUPABASE_WEBHOOK_SECRET', 'test-webhook-secret'):
        app.dependency_overrides[get_session] = lambda: mock_session
        
        webhook_payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {"id": str(uuid4())}
        }
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=webhook_payload,
            headers={"X-Webhook-Secret": "wrong-secret"}
        )
        
        # Assert
        assert response.status_code == 401
        assert "Invalid webhook secret" in response.json()["detail"]


def test_webhook_user_sync_no_secret_configured():
    """Test webhook error when no secret is configured."""
    # Arrange
    mock_session = AsyncMock()
    
    # No webhook secret configured
    with patch.object(settings, 'SUPABASE_WEBHOOK_SECRET', None):
        app.dependency_overrides[get_session] = lambda: mock_session
        
        webhook_payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth"
        }
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=webhook_payload,
            headers={"X-Webhook-Secret": "any-secret"}
        )
        
        # Assert
        assert response.status_code == 500
        assert "Webhook secret not configured" in response.json()["detail"]


@patch('Backend.api.auth.service.AuthService.sync_user_from_supabase')
def test_sync_user_success(mock_sync):
    """Test successful manual user sync."""
    # Arrange
    mock_session = AsyncMock()
    test_user = create_test_user()
    mock_sync.return_value = test_user
    
    # Set webhook secret
    with patch.object(settings, 'SUPABASE_WEBHOOK_SECRET', 'test-webhook-secret'):
        app.dependency_overrides[get_session] = lambda: mock_session
        
        sync_request = {
            "supabase_user_id": str(uuid4()),
            "email": "sync@example.com",
            "first_name": "Sync",
            "last_name": "User",
            "phone": "1234567890",
            "user_type": "LANDLORD"
        }
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/auth/sync-user",
            json=sync_request,
            headers={"X-Webhook-Secret": "test-webhook-secret"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        mock_sync.assert_called_once()


@patch('Backend.api.auth.service.AuthService.resend_verification_email')
def test_resend_verification_success(mock_resend):
    """Test successful email verification resend."""
    # Arrange
    mock_resend.return_value = {
        "success": True,
        "message": "If an account exists with this email, a verification email has been sent."
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/resend-verification",
        json={"email": "test@example.com"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "verification email has been sent" in data["message"]
    mock_resend.assert_called_once_with("test@example.com")


def test_resend_verification_invalid_email():
    """Test resend verification with invalid email format."""
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/resend-verification",
        json={"email": "not-an-email"}
    )
    
    # Assert
    assert response.status_code == 422
    # Check for email validation error - Pydantic returns specific email error message
    assert "email address" in response.json()["detail"][0]["msg"].lower()


def test_resend_verification_missing_email():
    """Test resend verification without email."""
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/resend-verification",
        json={}
    )
    
    # Assert
    assert response.status_code == 422
    # Check for missing field error - Pydantic capitalizes "Field required"
    assert "Field required" in response.json()["detail"][0]["msg"]


@patch('Backend.api.auth.service.AuthService.resend_verification_email')
def test_resend_verification_rate_limit(mock_resend):
    """Test rate limiting on verification resend."""
    # Arrange
    mock_resend.side_effect = HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Please wait before trying again."
    )
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/resend-verification",
        json={"email": "ratelimited@example.com"}
    )
    
    # Assert
    assert response.status_code == 429
    assert "Too many requests" in response.json()["detail"]


@patch('Backend.api.auth.service.AuthService.resend_verification_email')
def test_resend_verification_generic_error(mock_resend):
    """Test generic error handling for verification resend."""
    # Arrange
    mock_resend.side_effect = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please try again later."
    )
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/auth/resend-verification",
        json={"email": "error@example.com"}
    )
    
    # Assert
    assert response.status_code == 500
    assert "unexpected error occurred" in response.json()["detail"]