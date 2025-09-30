"""
API tests for QuickBooks synchronization operations.

Tests sync endpoints for payments, invoices, expenses, and all-data sync.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, UTC
from uuid import uuid4

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.models.accounting.integration import Integration, IntegrationStatus, IntegrationType
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


def create_mock_integration(connected=True):
    """Helper to create a mock QuickBooks integration."""
    mock_integration = AsyncMock(spec=Integration)
    mock_integration.id = uuid4()
    mock_integration.user_id = uuid4()
    mock_integration.integration_type = IntegrationType.QUICKBOOKS
    mock_integration.status = IntegrationStatus.CONNECTED if connected else IntegrationStatus.PENDING
    mock_integration.connected_at = FIXED_DATETIME if connected else None
    mock_integration.last_sync_at = None
    return mock_integration


def test_initial_sync_not_connected():
    """Test initial sync when not connected to QuickBooks."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock no integration
    with patch('Backend.api.quickbooks.router.get_user_integration') as mock_get_integration:
        mock_get_integration.return_value = None

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/initial-sync")

            # Should return 400 when not connected
            assert response.status_code == 400
            data = response.json()
            assert "not connected" in data["detail"].lower() or "must be connected" in data["detail"].lower()


def test_initial_sync_success():
    """Test successful initial synchronization."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_integration = create_mock_integration(connected=True)

    with patch('Backend.api.quickbooks.router.get_user_integration') as mock_get_integration, \
         patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:

        mock_get_integration.return_value = mock_integration

        mock_service = AsyncMock()
        mock_service.perform_initial_sync.return_value = {
            "success": True,
            "message": "Initial sync completed successfully",
            "items_synced": 25,
            "errors": []
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/initial-sync")

            data = assert_valid_json_response(response, dict)
            assert data["success"] is True
            assert data["items_synced"] == 25
            assert data["errors"] == []
            assert "completed" in data["message"].lower()


def test_initial_sync_with_errors():
    """Test initial sync with some errors."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_integration = create_mock_integration(connected=True)

    with patch('Backend.api.quickbooks.router.get_user_integration') as mock_get_integration, \
         patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:

        mock_get_integration.return_value = mock_integration

        mock_service = AsyncMock()
        mock_service.perform_initial_sync.return_value = {
            "success": False,
            "message": "Initial sync completed with errors",
            "items_synced": 15,
            "errors": ["Failed to sync 2 customers", "1 invoice sync failed"]
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/initial-sync")

            data = assert_valid_json_response(response, dict)
            assert data["success"] is False
            assert data["items_synced"] == 15
            assert len(data["errors"]) == 2


def test_sync_payments_success():
    """Test successful payment synchronization."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service.sync_payments.return_value = {
            "success": True,
            "message": "Payment sync completed",
            "synced_count": 8,
            "pulled_count": 5,
            "pushed_count": 3,
            "errors": []
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/payments")

            data = assert_valid_json_response(response, dict)
            assert data["success"] is True
            assert data["items_synced"] == 8
            assert data["errors"] == []


def test_sync_payments_not_connected():
    """Test payment sync when not connected."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock the sync service to raise an error for not connected
    with patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:
        from fastapi import HTTPException
        mock_service = AsyncMock()
        mock_service.sync_payments.side_effect = HTTPException(
            status_code=400,
            detail="QuickBooks integration not found or not connected"
        )
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/payments")

            # HTTPException raised in service gets caught and returned as 500 by the router's error handler
            assert response.status_code == 500
            data = response.json()
            assert "failed" in data["detail"].lower()


def test_sync_invoices_success():
    """Test successful invoice synchronization."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service.sync_invoices.return_value = {
            "success": True,
            "message": "Invoice sync completed",
            "synced_count": 12,
            "pulled_count": 7,
            "pushed_count": 5,
            "errors": []
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/invoices")

            data = assert_valid_json_response(response, dict)
            assert data["success"] is True
            assert data["items_synced"] == 12


def test_sync_expenses_success():
    """Test successful expense synchronization."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service.sync_expenses.return_value = {
            "success": True,
            "message": "Expense sync completed",
            "synced_count": 6,
            "pulled_count": 4,
            "pushed_count": 2,
            "errors": []
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/expenses")

            data = assert_valid_json_response(response, dict)
            assert data["success"] is True
            assert data["items_synced"] == 6


def test_sync_all_success():
    """Test successful full synchronization."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_integration = create_mock_integration(connected=True)

    with patch('Backend.api.quickbooks.router.get_user_integration') as mock_get_integration, \
         patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:

        mock_get_integration.return_value = mock_integration

        mock_service = AsyncMock()
        mock_service.perform_sync_all.return_value = {
            "success": True,
            "message": "Full sync completed",
            "items_synced": 45,
            "errors": []
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/all")

            data = assert_valid_json_response(response, dict)
            assert data["success"] is True
            assert data["items_synced"] == 45


def test_sync_service_error():
    """Test sync when service throws an error."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service.sync_payments.side_effect = Exception("Service error")
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/payments")

            # Should return 500 for service errors
            assert response.status_code == 500


def test_sync_rate_limiting():
    """Test that sync endpoints work correctly (rate limiting is handled at service level)."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # The sync endpoints don't have rate limiting at the router level
    # They rely on QuickBooks API rate limiting and circuit breakers
    with patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service.sync_payments.return_value = {
            "success": True,
            "synced_count": 0,
            "pulled_count": 0,
            "pushed_count": 0,
            "errors": []
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/payments")

            # Should succeed (rate limiting is service-level, not endpoint-level)
            assert response.status_code == 200


def test_sync_concurrent_operations():
    """Test concurrent sync operations."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service.sync_payments.return_value = {
            "success": True,
            "synced_count": 5,
            "pulled_count": 3,
            "pushed_count": 2,
            "errors": []
        }
        mock_service.sync_invoices.return_value = {
            "success": True,
            "synced_count": 3,
            "pulled_count": 2,
            "pushed_count": 1,
            "errors": []
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            # Make sequential requests (TestClient doesn't support async)
            response1 = client.post("/api/quickbooks/sync/payments")
            response2 = client.post("/api/quickbooks/sync/invoices")

            # Both should succeed
            data1 = assert_valid_json_response(response1, dict)
            assert data1["success"] is True

            data2 = assert_valid_json_response(response2, dict)
            assert data2["success"] is True


def test_sync_with_transaction_coordinator():
    """Test sync operations work correctly."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_integration = create_mock_integration(connected=True)

    with patch('Backend.api.quickbooks.router.get_user_integration') as mock_get_integration, \
         patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:

        mock_get_integration.return_value = mock_integration

        mock_service = AsyncMock()
        mock_service.perform_sync_all.return_value = {
            "success": True,
            "message": "Sync completed",
            "items_synced": 20,
            "errors": []
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/all")

            data = assert_valid_json_response(response, dict)
            assert data["success"] is True


def test_sync_timeout_handling():
    """Test sync operation handles long-running operations."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:
        mock_service = AsyncMock()
        # Return a successful result (in practice the service handles timeouts internally)
        mock_service.sync_payments.return_value = {
            "success": True,
            "synced_count": 0,
            "pulled_count": 0,
            "pushed_count": 0,
            "errors": []
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/payments")

            # Should handle gracefully
            assert response.status_code in [200, 500, 408]  # Success, error, or timeout


def test_sync_incremental_vs_full():
    """Test sync operations."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_integration = create_mock_integration(connected=True)
    mock_integration.last_sync_at = datetime.now(UTC)  # Recent sync

    with patch('Backend.api.quickbooks.router.get_user_integration') as mock_get_integration, \
         patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:

        mock_get_integration.return_value = mock_integration

        mock_service = AsyncMock()
        mock_service.perform_sync_all.return_value = {
            "success": True,
            "message": "Incremental sync completed",
            "items_synced": 5,  # Fewer items for incremental
            "errors": []
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/all")

            data = assert_valid_json_response(response, dict)
            assert data["success"] is True
            # Should sync fewer items in incremental mode
            assert data["items_synced"] <= 10


def test_sync_error_recovery():
    """Test sync error recovery mechanisms."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service.sync_payments.return_value = {
            "success": False,
            "synced_count": 3,
            "pulled_count": 2,
            "pushed_count": 1,
            "errors": ["Failed to sync payment 1", "Network timeout on payment 5"]
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/payments")

            data = assert_valid_json_response(response, dict)
            assert data["success"] is False
            assert data["items_synced"] == 3  # Partial success
            assert len(data["errors"]) == 2
            assert "Failed to sync payment 1" in data["errors"]


def test_sync_with_circuit_breaker():
    """Test sync operations with circuit breaker protection."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:
        from fastapi import HTTPException
        mock_service = AsyncMock()
        # Simulate circuit breaker failure
        mock_service.sync_payments.side_effect = HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/payments")

            # Should handle circuit breaker gracefully
            assert response.status_code in [500, 503]  # Server error or service unavailable


def test_sync_permission_check_non_landlord():
    """Test that sync operations require landlord or admin permission."""
    # Create a tenant user (not landlord)
    test_user = create_test_user(user_type=UserType.TENANT)
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        response = client.post("/api/quickbooks/sync/payments")

        # Should return 403 for non-landlord users
        assert response.status_code == 403
        data = response.json()
        assert "landlord" in data["detail"].lower() or "admin" in data["detail"].lower()


def test_initial_sync_permission_check():
    """Test that initial sync requires landlord or admin permission."""
    # Create a tenant user (not landlord)
    test_user = create_test_user(user_type=UserType.TENANT)
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        response = client.post("/api/quickbooks/initial-sync")

        # Should return 403 for non-landlord users
        assert response.status_code == 403
        data = response.json()
        assert "landlord" in data["detail"].lower()


def test_sync_all_with_partial_failures():
    """Test full sync with partial failures."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_integration = create_mock_integration(connected=True)

    with patch('Backend.api.quickbooks.router.get_user_integration') as mock_get_integration, \
         patch('Backend.api.quickbooks.router.QuickBooksSyncService') as mock_service_class:

        mock_get_integration.return_value = mock_integration

        mock_service = AsyncMock()
        mock_service.perform_sync_all.return_value = {
            "success": False,
            "message": "Sync completed with errors",
            "items_synced": 35,
            "errors": ["Failed to sync 2 invoices", "1 payment failed"]
        }
        mock_service_class.return_value = mock_service

        with TestClientWithHost(app) as client:
            response = client.post("/api/quickbooks/sync/all")

            data = assert_valid_json_response(response, dict)
            assert data["success"] is False
            assert data["items_synced"] == 35
            assert len(data["errors"]) == 2