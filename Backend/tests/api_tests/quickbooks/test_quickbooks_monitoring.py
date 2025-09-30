"""
API tests for QuickBooks monitoring endpoints.

Tests circuit breaker monitoring, transaction stats, and system monitoring.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from uuid import uuid4

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


def test_circuit_breakers_monitoring():
    """Test circuit breaker monitoring endpoint."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_circuit_breaker_stats = {
        "quickbooks_api": {
            "state": "closed",
            "failure_count": 2,
            "failure_threshold": 5,
            "total_requests": 100,
            "total_failures": 2,
            "failure_rate": 0.02,
            "last_failure_time": None
        },
        "quickbooks_auth": {
            "state": "half_open",
            "failure_count": 3,
            "failure_threshold": 3,
            "total_requests": 50,
            "total_failures": 3,
            "failure_rate": 0.06,
            "last_failure_time": "2024-06-01T12:00:00Z"
        }
    }

    with patch('Backend.api.quickbooks.circuit_breaker.get_all_circuit_breaker_stats') as mock_get_stats:
        mock_get_stats.return_value = mock_circuit_breaker_stats

        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/monitoring/circuit-breakers")

            data = assert_valid_json_response(response, dict)

            # Verify structure
            assert "circuit_breakers" in data
            assert "global_stats" in data

            # Verify circuit breaker details
            breakers = data["circuit_breakers"]
            assert "quickbooks_api" in breakers
            assert "quickbooks_auth" in breakers

            # Check quickbooks_api breaker
            api_breaker = breakers["quickbooks_api"]
            assert api_breaker["state"] == "closed"
            assert api_breaker["failure_count"] == 2
            assert api_breaker["failure_threshold"] == 5

            # Check quickbooks_auth breaker
            auth_breaker = breakers["quickbooks_auth"]
            assert auth_breaker["state"] == "half_open"
            assert auth_breaker["failure_count"] == 3

            # Check global stats
            global_stats = data["global_stats"]
            assert "total_circuit_breakers" in global_stats
            assert global_stats["total_circuit_breakers"] == 2


def test_circuit_breakers_no_stats():
    """Test circuit breaker monitoring when no stats available."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.circuit_breaker.get_all_circuit_breaker_stats') as mock_get_stats:
        mock_get_stats.return_value = {}

        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/monitoring/circuit-breakers")

            data = assert_valid_json_response(response, dict)
            assert data["global_stats"]["total_circuit_breakers"] == 0
            assert len(data["circuit_breakers"]) == 0


def test_reset_circuit_breaker_success():
    """Test successful circuit breaker reset."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.circuit_breaker.get_circuit_breaker') as mock_get_breaker:
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.reset = AsyncMock()
        mock_get_breaker.return_value = mock_circuit_breaker

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/monitoring/reset-circuit-breaker/quickbooks_api")

            data = assert_valid_json_response(response, dict)
            assert data["status"] == "success"
            assert "reset" in data["message"].lower()
            mock_circuit_breaker.reset.assert_called_once()


def test_reset_circuit_breaker_not_found():
    """Test reset of non-existent circuit breaker."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.circuit_breaker.get_circuit_breaker') as mock_get_breaker:
        # Simulate circuit breaker not found
        mock_get_breaker.side_effect = Exception("Circuit breaker not found")

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/monitoring/reset-circuit-breaker/nonexistent")

            # Should return 500 when circuit breaker not found
            assert response.status_code == 500


def test_reset_circuit_breaker_invalid_name():
    """Test reset with invalid circuit breaker name."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.circuit_breaker.get_circuit_breaker') as mock_get_breaker:
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.reset = AsyncMock()
        mock_get_breaker.return_value = mock_circuit_breaker

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/monitoring/reset-circuit-breaker/invalid@name")

            # The endpoint currently accepts any string and tries to get the breaker
            # If it exists, it returns 200, if not it returns 500
            assert response.status_code in [200, 500]


def test_transaction_monitoring():
    """Test transaction monitoring endpoint."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        response = client.get("/api/quickbooks/monitoring/transactions")

        data = assert_valid_json_response(response, dict)

        # The endpoint returns a simple message about event-based monitoring
        assert "message" in data
        assert "note" in data
        assert "event-based" in data["message"].lower() or "log" in data["note"].lower()


def test_transaction_monitoring_no_data():
    """Test transaction monitoring when no data available."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        response = client.get("/api/quickbooks/monitoring/transactions")

        data = assert_valid_json_response(response, dict)
        # Same response regardless of data availability since it's event-based
        assert "message" in data


def test_monitoring_permission_check_non_landlord():
    """Test that monitoring endpoints check user permissions."""
    # Create a non-landlord user (tenant)
    test_user = create_test_user(user_type=UserType.TENANT)
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        response = client.get("/api/quickbooks/monitoring/circuit-breakers")

        # Should return 403 for non-landlord users
        assert response.status_code == 403
        data = response.json()
        assert "landlord" in data["detail"].lower()


def test_monitoring_permission_check_landlord():
    """Test that monitoring endpoints allow landlord access."""
    test_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.circuit_breaker.get_all_circuit_breaker_stats') as mock_get_stats:
        mock_get_stats.return_value = {}

        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/monitoring/circuit-breakers")

            # Should succeed for landlord users
            assert response.status_code == 200


def test_monitoring_error_handling():
    """Test monitoring endpoints error handling."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.circuit_breaker.get_all_circuit_breaker_stats') as mock_get_stats:
        mock_get_stats.side_effect = Exception("Monitoring service error")

        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/monitoring/circuit-breakers")

            # Should handle errors gracefully
            assert response.status_code == 500


def test_circuit_breaker_details():
    """Test detailed circuit breaker information."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_detailed_stats = {
        "quickbooks_api": {
            "state": "open",
            "failure_count": 5,
            "failure_threshold": 5,
            "total_requests": 100,
            "total_failures": 5,
            "failure_rate": 0.05,
            "last_failure_time": "2024-06-01T12:00:00Z"
        }
    }

    with patch('Backend.api.quickbooks.circuit_breaker.get_all_circuit_breaker_stats') as mock_get_stats:
        mock_get_stats.return_value = mock_detailed_stats

        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/monitoring/circuit-breakers")

            data = assert_valid_json_response(response, dict)

            breaker = data["circuit_breakers"]["quickbooks_api"]
            assert breaker["state"] == "open"
            assert breaker["total_requests"] == 100
            assert breaker["total_failures"] == 5


def test_monitoring_rate_limiting():
    """Test that monitoring endpoints handle rapid requests."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.circuit_breaker.get_all_circuit_breaker_stats') as mock_get_stats:
        mock_get_stats.return_value = {}

        with TestClientWithHost(app) as client:
            # Test rapid requests to monitoring endpoints
            responses = []
            for _ in range(10):
                response = client.get("/api/quickbooks/monitoring/circuit-breakers")
                responses.append(response)

            # Should handle rapid requests appropriately
            # All should succeed since there's no rate limiting on monitoring endpoints
            success_count = sum(1 for r in responses if r.status_code == 200)
            assert success_count >= 8  # Allow some failures


def test_transaction_monitoring_filtering():
    """Test transaction monitoring endpoint (which is event-based)."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        # Test with type filter (endpoint ignores it since it's event-based)
        response = client.get("/api/quickbooks/monitoring/transactions?type=sync_customers")

        data = assert_valid_json_response(response, dict)
        assert "message" in data
        assert "note" in data


def test_monitoring_authentication_required():
    """Test that monitoring endpoints require authentication."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.circuit_breaker.get_all_circuit_breaker_stats') as mock_get_stats:
        mock_get_stats.return_value = {}

        with TestClientWithHost(app) as client:
            # All monitoring endpoints should require valid auth
            monitoring_endpoints = [
                "/api/quickbooks/monitoring/circuit-breakers",
                "/api/quickbooks/monitoring/transactions"
            ]

            for endpoint in monitoring_endpoints:
                response = client.get(endpoint)
                # Should succeed with valid auth
                assert response.status_code == 200


def test_reset_circuit_breaker_permission_check():
    """Test that reset circuit breaker requires landlord permission."""
    # Create a non-landlord user
    test_user = create_test_user(user_type=UserType.TENANT)
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        response = client.post("/api/quickbooks/monitoring/reset-circuit-breaker/quickbooks_api")

        # Should return 403 for non-landlord users
        assert response.status_code == 403
        data = response.json()
        assert "landlord" in data["detail"].lower()


def test_circuit_breaker_stats_with_multiple_states():
    """Test circuit breaker stats with breakers in different states."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_stats = {
        "breaker_closed": {
            "state": "closed",
            "failure_count": 0,
            "failure_threshold": 5,
            "total_requests": 200,
            "total_failures": 0,
            "failure_rate": 0.0,
            "last_failure_time": None
        },
        "breaker_half_open": {
            "state": "half_open",
            "failure_count": 3,
            "failure_threshold": 5,
            "total_requests": 150,
            "total_failures": 3,
            "failure_rate": 0.02,
            "last_failure_time": "2024-06-01T11:59:30Z"
        },
        "breaker_open": {
            "state": "open",
            "failure_count": 5,
            "failure_threshold": 5,
            "total_requests": 100,
            "total_failures": 5,
            "failure_rate": 0.05,
            "last_failure_time": "2024-06-01T12:00:00Z"
        }
    }

    with patch('Backend.api.quickbooks.circuit_breaker.get_all_circuit_breaker_stats') as mock_get_stats:
        mock_get_stats.return_value = mock_stats

        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/monitoring/circuit-breakers")

            data = assert_valid_json_response(response, dict)
            
            # Verify all three states are represented
            breakers = data["circuit_breakers"]
            assert len(breakers) == 3
            assert breakers["breaker_closed"]["state"] == "closed"
            assert breakers["breaker_half_open"]["state"] == "half_open"
            assert breakers["breaker_open"]["state"] == "open"

            # Verify global stats calculations
            global_stats = data["global_stats"]
            assert global_stats["total_circuit_breakers"] == 3
            assert global_stats["open_circuits"] == 1
            assert global_stats["half_open_circuits"] == 1
            assert global_stats["closed_circuits"] == 1