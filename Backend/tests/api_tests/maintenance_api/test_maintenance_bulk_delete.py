"""
Unit tests for BULK DELETE operations in the maintenance API endpoint using hybrid API testing pattern.
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
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def create_test_user(user_id=None, email="test@example.com", user_type=UserType.LANDLORD, is_admin=False):
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
        created_at=now,
        updated_at=now,
        is_email_verified=True,
    )


# =============================================================================
# BULK DELETE MAINTENANCE REQUEST TESTS
# =============================================================================

def test_bulk_delete_maintenance_requests_success_owner():
    """Test successful bulk deletion by property owner."""
    request_ids = [101, 102, 103]
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, email="owner@example.com")

    with patch(
        "Backend.api.maintenance.router.MaintenanceService.bulk_delete_maintenance_requests",
        new=AsyncMock(return_value=None),
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.request(
                "DELETE",
                "/api/maintenance/requests/bulk",
                json={"request_ids": request_ids},
            )

            assert response.status_code == 204
            assert response.content == b""


def test_bulk_delete_maintenance_requests_success_admin():
    """Test that admin can bulk delete any maintenance requests."""
    request_ids = [201, 202]
    admin_user = create_test_user(
        user_id=uuid4(),
        email="admin@example.com",
        user_type=UserType.ADMIN,
        is_admin=True,
    )

    with patch(
        "Backend.api.maintenance.router.MaintenanceService.bulk_delete_maintenance_requests",
        new=AsyncMock(return_value=None),
    ):
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.request(
                "DELETE",
                "/api/maintenance/requests/bulk",
                json={"request_ids": request_ids},
            )

            assert response.status_code == 204
            assert response.content == b""


def test_bulk_delete_maintenance_requests_empty_list():
    """Test that empty list results in 204 (no-op)."""
    fake_user = create_test_user(user_id=uuid4())

    with patch(
        "Backend.api.maintenance.router.MaintenanceService.bulk_delete_maintenance_requests",
        new=AsyncMock(return_value=None),
    ) as mocked_bulk_delete:
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.request(
                "DELETE",
                "/api/maintenance/requests/bulk",
                json={"request_ids": []},
            )

            assert response.status_code == 204
            # Service may still be called, but returns immediately; assert call happened with [] if desired
            mocked_bulk_delete.assert_awaited_once()


def test_bulk_delete_maintenance_requests_not_found_or_unauthorized():
    """Test 404 when some IDs are missing or unauthorized (service-level 404)."""
    request_ids = [301, 302, 999]  # include a non-existent/unauthorized id
    fake_user = create_test_user(user_id=uuid4())

    with patch(
        "Backend.api.maintenance.router.MaintenanceService.bulk_delete_maintenance_requests",
        new=AsyncMock(
            side_effect=HTTPException(
                status_code=404,
                detail="One or more maintenance requests not found or you do not have permission to delete them.",
            )
        ),
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.request(
                "DELETE",
                "/api/maintenance/requests/bulk",
                json={"request_ids": request_ids},
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower() or "permission" in response.json()["detail"].lower()


def test_bulk_delete_maintenance_requests_database_error():
    """Test error handling for unexpected exceptions during bulk deletion."""
    request_ids = [401, 402]
    fake_user = create_test_user(user_id=uuid4())

    with patch(
        "Backend.api.maintenance.router.MaintenanceService.bulk_delete_maintenance_requests",
        new=AsyncMock(side_effect=Exception("Database connection failed")),
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.request(
                "DELETE",
                "/api/maintenance/requests/bulk",
                json={"request_ids": request_ids},
            )

            assert response.status_code == 500
            assert "Failed to bulk delete maintenance requests" in response.json()["detail"]


def test_bulk_delete_maintenance_requests_invalid_body():
    """Test 422 when payload is invalid."""
    fake_user = create_test_user(user_id=uuid4())

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        # Missing body
        response_missing = client.delete("/api/maintenance/requests/bulk")
        assert response_missing.status_code == 422

        # Wrong type for request_ids
        response_wrong_type = client.request(
            "DELETE",
            "/api/maintenance/requests/bulk",
            json={"request_ids": "not-a-list"},
        )
        assert response_wrong_type.status_code == 422


def test_bulk_delete_maintenance_requests_verify_logging():
    """Test that bulk deletion success path returns 204 (logging would occur in service)."""
    request_ids = [501, 502, 503]
    fake_user = create_test_user(user_id=uuid4())

    with patch(
        "Backend.api.maintenance.router.MaintenanceService.bulk_delete_maintenance_requests",
        new=AsyncMock(return_value=None),
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.request(
                "DELETE",
                "/api/maintenance/requests/bulk",
                json={"request_ids": request_ids},
            )

            assert response.status_code == 204
            # In a real scenario, we would verify logger interactions; here we assert the API outcome.