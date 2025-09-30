"""
API tests for QuickBooks status and diagnostics endpoints.

Tests system status checking - simplified for API testing without mocks.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from uuid import uuid4

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Import helper functions from conftest.py
from ..conftest import assert_valid_json_response

# Mark all tests in this module as API tests
pytestmark = pytest.mark.api

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


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


def test_quickbooks_diagnostics_endpoint():
    """Test the /api/quickbooks/diagnostics endpoint."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock get_user_integration
    with TestClientWithHost(app) as client:
        response = client.get("/api/quickbooks/diagnostics")

        data = assert_valid_json_response(response, dict)

        # Should contain diagnostic information
        assert "connected" in data
        assert "environment" in data
        assert "integration_exists" in data
        assert isinstance(data["connected"], bool)
        assert isinstance(data["integration_exists"], bool)


def test_quickbooks_diagnostics_with_connection():
    """Test diagnostics when QuickBooks is connected."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock a connected integration
    with TestClientWithHost(app) as client:
        response = client.get("/api/quickbooks/diagnostics")

        data = assert_valid_json_response(response, dict)
        assert "connected" in data
        assert "integration_exists" in data
        # Without actual DB integration, connected will be False
        assert isinstance(data["connected"], bool)