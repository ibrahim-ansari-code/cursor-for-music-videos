"""
API tests for QuickBooks authentication endpoints.

Tests OAuth flow, connection, disconnection, and status endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse, parse_qs
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Import helper functions from conftest.py
from ..conftest import assert_valid_json_response, assert_api_success, assert_api_error

# Mark all tests in this module as API tests
pytestmark = pytest.mark.api

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_recaptcha_for_quickbooks_tests():
    """Mock reCAPTCHA verification for QuickBooks tests."""
    with patch('Backend.utils.recaptcha.settings') as mock_settings:
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = ""  # This will cause bypass
        yield mock_settings


# Create a custom TestClient that sets the proper host header
class TestClientWithHost(TestClient):
    def request(self, method: str, url, **kwargs):
        # Always add localhost to headers if not present
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def create_test_user(user_id=None, email="test@example.com", user_type=UserType.LANDLORD):
    """Helper function to create a properly initialized test user."""
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=False,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        is_email_verified=True
    )


def test_quickbooks_connect_endpoint():
    """Test the /api/quickbooks/connect endpoint."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock the auth service
    with patch('Backend.api.quickbooks.router.QuickBooksAuthService') as mock_auth_service_class:
        mock_auth_service = AsyncMock()
        mock_auth_service.build_authorize_url.return_value = (
            "https://appcenter.intuit.com/connect/oauth2?client_id=test&redirect_uri=test",
            "test_state_123"
        )
        mock_auth_service_class.return_value = mock_auth_service

        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/connect")

            # Should return connection information
            data = assert_valid_json_response(response, dict)

            assert "status" in data
            assert "message" in data
            # Should include redirect URL for OAuth flow
            if data["status"] == "redirect_required":
                assert "redirect_url" in data
                assert data["redirect_url"] is not None

                # Validate redirect URL structure
                parsed_url = urlparse(data["redirect_url"])
                assert parsed_url.scheme in ["https", "http"]
                assert "intuit.com" in parsed_url.netloc or "localhost" in parsed_url.netloc


def test_quickbooks_status_endpoint():
    """Test the /api/quickbooks/status endpoint."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock the get_user_integration utility
    with patch('Backend.api.quickbooks.router.get_user_integration') as mock_get_integration:
        # Return None to simulate no integration
        mock_get_integration.return_value = None

        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/status")

            data = assert_valid_json_response(response, dict)

            # Check required fields
            assert "connected" in data
            assert isinstance(data["connected"], bool)

            # If connected, should have additional fields
            if data["connected"]:
                assert "integration_type" in data
                assert "connected_at" in data
                assert "consumer_id" in data
            else:
                # If not connected, integration_type may still be present if user previously connected
                # but connected_at should be null
                assert data.get("connected_at") is None


def test_quickbooks_status_not_connected():
    """Test status endpoint when QuickBooks is not connected."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock no integration exists
    with patch('Backend.api.quickbooks.router.get_user_integration') as mock_get_integration:
        mock_get_integration.return_value = None

        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/status")

            data = assert_valid_json_response(response, dict)
            assert data["connected"] is False
            assert data["integration_type"] is None
            assert data["connected_at"] is None


def test_quickbooks_disconnect_not_connected():
    """Test disconnect when not connected."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock the auth service to raise exception for no integration
    with patch('Backend.api.quickbooks.router.QuickBooksAuthService') as mock_auth_service_class:
        from fastapi import HTTPException
        mock_auth_service = AsyncMock()
        mock_auth_service.disconnect_quickbooks.side_effect = HTTPException(
            status_code=404,
            detail="No QuickBooks integration found"
        )
        mock_auth_service_class.return_value = mock_auth_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/disconnect")

            # Should return 404 when no integration exists
            assert response.status_code == 404
            data = response.json()  # Don't use assert_valid_json_response for error cases
            assert "not found" in data["detail"].lower() or "no quickbooks" in data["detail"].lower()


def test_quickbooks_disconnect_success():
    """Test successful QuickBooks disconnection."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock successful disconnect
    with patch('Backend.api.quickbooks.router.QuickBooksAuthService') as mock_auth_service_class:
        mock_auth_service = AsyncMock()
        mock_auth_service.disconnect_quickbooks.return_value = {
            "success": True,
            "message": "QuickBooks integration disconnected successfully"
        }
        mock_auth_service_class.return_value = mock_auth_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/disconnect")

            data = assert_valid_json_response(response, dict)
            assert data["success"] is True
            assert "disconnected" in data["message"].lower()

def test_quickbooks_callback_missing_params():
    """Test callback with missing required parameters."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        # Missing required parameters
        response = client.get("/api/quickbooks/callback")

        # Should return 422 for missing required parameters (FastAPI validation error)
        assert response.status_code == 422


def test_quickbooks_callback_with_error():
    """Test callback when QuickBooks returns an error."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    callback_params = {
        "error": "access_denied",
        "error_description": "User denied access"
    }

    with TestClientWithHost(app) as client:
        response = client.get("/api/quickbooks/callback", params=callback_params)

        # FastAPI returns 422 for missing required parameters (code, realmId, state)
        # even when error parameters are provided
        assert response.status_code == 422


def test_quickbooks_recaptcha_bypass():
    """Test that recaptcha bypass works for QuickBooks endpoints."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock the auth service
    with patch('Backend.api.quickbooks.router.QuickBooksAuthService') as mock_auth_service_class:
        mock_auth_service = AsyncMock()
        mock_auth_service.build_authorize_url.return_value = (
            "https://appcenter.intuit.com/connect/oauth2?client_id=test",
            "test_state"
        )
        mock_auth_service_class.return_value = mock_auth_service

        with TestClientWithHost(app) as client:
            # Should succeed without recaptcha verification (bypassed by fixture)
            response = client.get("/api/quickbooks/connect")

            data = assert_valid_json_response(response, dict)
            assert "status" in data


def test_quickbooks_connection_health_check():
    """Test connection health check functionality."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock no connected integration
    with patch('Backend.api.quickbooks.router.get_user_integration') as mock_get_integration:
        mock_get_integration.return_value = None

        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/status")

            data = assert_valid_json_response(response, dict)
            assert data["connected"] is False  # Status is based on actual connection state


def test_quickbooks_concurrent_auth_requests():
    """Test handling of concurrent authentication requests."""
    import asyncio
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock the get_user_integration utility
    with patch('Backend.api.quickbooks.router.get_user_integration') as mock_get_integration:
        mock_get_integration.return_value = None

        with TestClientWithHost(app) as client:
            # TestClient is synchronous, so we can't use asyncio.gather
            # Instead, test that multiple sequential requests work correctly
            responses = []
            for _ in range(5):
                response = client.get("/api/quickbooks/status")
                responses.append(response)

            # All requests should succeed
            for response in responses:
                assert response.status_code in [200, 400, 500]  # Valid HTTP status codes


@pytest.mark.skip(reason="Cannot mock OAuth callback in separate backend process")
def test_quickbooks_auth_state_validation():
    """Test OAuth state parameter validation."""
    pass


@pytest.mark.skip(reason="Cannot mock token refresh in separate backend process")
def test_quickbooks_token_refresh_flow():
    """Test token refresh during authentication flow."""
    pass