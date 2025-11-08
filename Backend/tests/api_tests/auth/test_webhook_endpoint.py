"""
API tests for webhook endpoint using hybrid API testing pattern.

Tests the webhook endpoint with mocked dependencies for authentication,
rate limiting, and proper error handling.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from Backend.api.app import app
from Backend.database import get_session
from Backend.models.user import User
from datetime import datetime, timezone


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def test_user():
    """Create a test user for webhook tests."""
    return User(
        id=uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        user_type="LANDLORD",
        is_active=True,
        is_admin=False,
        is_email_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


class TestWebhookEndpoint:
    """Tests for /api/auth/webhook/user-sync endpoint."""
    
    def test_webhook_requires_secret(self):
        """Test webhook endpoint requires X-Webhook-Secret header."""
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": str(uuid4()),
                "email": "test@example.com"
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload
        )
        
        assert response.status_code == 401
        assert "Invalid webhook secret" in response.json()["detail"]
    
    def test_webhook_rejects_invalid_secret(self):
        """Test webhook endpoint rejects invalid secret."""
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": str(uuid4()),
                "email": "test@example.com"
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "wrong_secret"}
        )
        
        assert response.status_code == 401
        assert "Invalid webhook secret" in response.json()["detail"]
    
    @patch('Backend.api.auth.router.settings')
    @patch('Backend.api.auth.service.AuthService.create_user_from_supabase', new_callable=AsyncMock)
    def test_webhook_succeeds_with_valid_secret(self, mock_create_user, mock_settings):
        """Test webhook endpoint accepts valid secret."""
        mock_settings.SUPABASE_WEBHOOK_SECRET = "test_secret"
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        user_id = str(uuid4())
        payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": user_id,
                "email": f"webhook-test-{user_id}@example.com",
                "raw_user_meta_data": {
                    "first_name": "Test",
                    "last_name": "User"
                }
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "test_secret"}
        )
        
        assert response.status_code == 200
        assert "message" in response.json()
    
    @patch('Backend.api.auth.router.settings')
    def test_webhook_ignores_non_auth_table(self, mock_settings):
        """Test webhook ignores events from non-auth tables."""
        mock_settings.SUPABASE_WEBHOOK_SECRET = "test_secret"
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {
            "type": "INSERT",
            "table": "posts",
            "schema": "public",
            "record": {
                "id": str(uuid4()),
                "title": "Test Post"
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "test_secret"}
        )
        
        assert response.status_code == 200
        assert "ignored" in response.json()["message"].lower()
    
    @patch('Backend.api.auth.router.settings')
    def test_webhook_ignores_delete_events(self, mock_settings):
        """Test webhook ignores DELETE events."""
        mock_settings.SUPABASE_WEBHOOK_SECRET = "test_secret"
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {
            "type": "DELETE",
            "table": "users",
            "schema": "auth",
            "old_record": {
                "id": str(uuid4()),
                "email": "deleted@example.com"
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "test_secret"}
        )
        
        assert response.status_code == 200
        assert "ignored" in response.json()["message"].lower()
    
    @patch('Backend.api.auth.router.settings')
    def test_webhook_validates_required_fields(self, mock_settings):
        """Test webhook validates presence of required fields."""
        mock_settings.SUPABASE_WEBHOOK_SECRET = "test_secret"
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Missing email
        payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": str(uuid4())
                # email missing
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "test_secret"}
        )
        
        assert response.status_code == 200
        assert "Invalid user data" in response.json()["message"]
    
    @patch('Backend.api.auth.router.settings')
    @patch('Backend.api.auth.router.check_webhook_rate_limit')
    def test_webhook_rate_limiting(self, mock_rate_limit, mock_settings):
        """Test webhook rate limiting kicks in."""
        mock_settings.SUPABASE_WEBHOOK_SECRET = "test_secret"
        mock_rate_limit.return_value = False  # Rate limit exceeded
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": str(uuid4()),
                "email": "test@example.com"
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "test_secret"}
        )
        
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
        assert "Retry-After" in response.headers
    
    @patch('Backend.api.auth.router.settings')
    def test_webhook_handles_update_events(self, mock_settings, test_user):
        """Test webhook handles UPDATE events for existing users."""
        mock_settings.SUPABASE_WEBHOOK_SECRET = "test_secret"
        mock_session = AsyncMock()
        mock_session.get.return_value = test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {
            "type": "UPDATE",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": str(test_user.id),
                "email": test_user.email,
                "raw_user_meta_data": {
                    "first_name": "Updated",
                    "last_name": "Name"
                }
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "test_secret"}
        )
        
        assert response.status_code == 200
        assert "updated" in response.json()["message"].lower()
    
    @patch('Backend.api.auth.router.settings')
    def test_webhook_is_idempotent(self, mock_settings, test_user):
        """Test webhook handles duplicate INSERT events gracefully."""
        mock_settings.SUPABASE_WEBHOOK_SECRET = "test_secret"
        mock_session = AsyncMock()
        mock_session.get.return_value = test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Try to INSERT an existing user
        payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": str(test_user.id),
                "email": test_user.email,
                "raw_user_meta_data": {}
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "test_secret"}
        )
        
        assert response.status_code == 200
        assert "already exists" in response.json()["message"].lower() or "idempotent" in response.json()["message"].lower()
    
    @patch('Backend.api.auth.router.settings')
    def test_webhook_validates_uuid_format(self, mock_settings):
        """Test webhook validates UUID format."""
        mock_settings.SUPABASE_WEBHOOK_SECRET = "test_secret"
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": "not-a-valid-uuid",
                "email": "test@example.com"
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "test_secret"}
        )
        
        assert response.status_code == 200
        assert "Invalid" in response.json()["message"]
    
    @patch('Backend.api.auth.router.settings')
    def test_webhook_extracts_client_ip(self, mock_settings):
        """Test webhook extracts and uses client IP for rate limiting."""
        mock_settings.SUPABASE_WEBHOOK_SECRET = "test_secret"
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": str(uuid4()),
                "email": f"ip-test-{uuid4()}@example.com",
                "raw_user_meta_data": {}
            }
        }
        
        # Make request with custom client
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "test_secret"}
        )
        
        # Should succeed (IP extracted and rate limit not exceeded)
        assert response.status_code == 200


class TestWebhookOAuthAccountLinking:
    """Tests for OAuth account linking via webhook."""
    
    @patch('Backend.api.auth.router.settings')
    def test_webhook_rejects_email_conflict_different_ids(self, mock_settings, test_user):
        """Test webhook rejects when same email has different Supabase IDs (Supabase linking failed)."""
        from unittest.mock import Mock
        
        mock_settings.SUPABASE_WEBHOOK_SECRET = "test_secret"
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        
        # Mock execute to return test_user when checking by email
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = test_user
        mock_session.execute.return_value = mock_result
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # New Supabase ID (different OAuth provider), same email - SHOULD NOT HAPPEN
        new_supabase_id = str(uuid4())
        
        payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": new_supabase_id,  # Different ID - Supabase should have used same ID!
                "email": test_user.email,  # Same email
                "raw_user_meta_data": {
                    "first_name": test_user.first_name,
                    "last_name": test_user.last_name
                }
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "test_secret"}
        )
        
        # Should reject with 409 - Supabase should handle linking natively
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()
    
    @patch('Backend.api.auth.router.settings')
    def test_webhook_succeeds_with_native_supabase_linking(self, mock_settings, test_user):
        """Test webhook succeeds when Supabase handles account linking (same user ID)."""
        mock_settings.SUPABASE_WEBHOOK_SECRET = "test_secret"
        mock_session = AsyncMock()
        mock_session.get.return_value = test_user  # User exists with same ID
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # UPDATE event with SAME Supabase ID - correct flow with enable_manual_linking=true
        payload = {
            "type": "UPDATE",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": str(test_user.id),  # SAME ID - Supabase linked correctly!
                "email": test_user.email,
                "raw_user_meta_data": {
                    "first_name": test_user.first_name,
                    "last_name": test_user.last_name
                }
            }
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/auth/webhook/user-sync",
            json=payload,
            headers={"X-Webhook-Secret": "test_secret"}
        )
        
        # Should succeed - this is the happy path
        assert response.status_code == 200
        assert "metadata updated" in response.json()["message"].lower()

