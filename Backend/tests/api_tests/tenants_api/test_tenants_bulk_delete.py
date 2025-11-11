"""
Unit tests for the tenant BULK DELETE endpoint/service using the same hybrid
API testing pattern as single delete tests.
"""
from datetime import datetime, timezone
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.models.tenant import Tenant, TenantStatus
from Backend.models.lease import Lease, LeaseStatus
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
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )


class MockScalarResult:
    """Mimics SQLAlchemy Result for .scalars().all() usage."""

    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


def _tenant(tenant_id: int, landlord_id):
    return Tenant(
        id=tenant_id,
        first_name=f"First{tenant_id}",
        last_name=f"Last{tenant_id}",
        email=f"tenant{tenant_id}@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


def _lease(lease_id: int, tenant_id: int, status=LeaseStatus.EXPIRED):
    """Helper function to create a mock Lease object."""
    from decimal import Decimal
    from datetime import date
    
    return Lease(
        id=lease_id,
        tenant_id=tenant_id,
        property_id=1,
        unit_id=1,
        start_date=date(2020, 1, 1),
        end_date=date(2021, 1, 1),
        monthly_rent=Decimal("1000.00"),
        security_deposit=Decimal("2000.00"),
        status=status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


def _bulk_delete(client: TestClient, ids: list[int]):
    return client.request("DELETE", "/api/tenants/delete-bulk", json={"tenant_ids": ids})


def test_bulk_delete_success():
    # Arrange
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    t1 = _tenant(1, landlord_id)
    t2 = _tenant(2, landlord_id)

    # Mock session
    mock_session = AsyncMock()
    # First execute -> tenants list; Second execute -> active lease tenant ids; Third execute -> non-active leases
    mock_session.execute = AsyncMock(side_effect=[
        MockScalarResult([t1, t2]),
        MockScalarResult([]),  # No active leases
        MockScalarResult([]),  # No non-active leases
    ])
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        # Act
        response = _bulk_delete(client, [1, 2])

    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # Verify bulk SQL delete was executed (not individual ORM deletes)
    # Execute calls: 1) fetch tenants, 2) check active leases, 3) check & delete non-active leases + bulk delete tenants
    assert mock_session.execute.await_count >= 3
    # Should NOT use individual session.delete() calls (tenants use SQL bulk delete)
    assert not hasattr(mock_session.delete, 'await_count') or mock_session.delete.await_count == 0
    mock_session.commit.assert_awaited_once()


def test_bulk_delete_with_active_leases():
    # Arrange
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    t1 = _tenant(10, landlord_id)
    t2 = _tenant(20, landlord_id)

    mock_session = AsyncMock()
    # First execute -> tenants list; Second execute -> active lease tenant ids
    # Third query won't be reached because exception is raised when active leases are found
    mock_session.execute = AsyncMock(side_effect=[
        MockScalarResult([t1, t2]),
        MockScalarResult([10]),  # tenant 10 has active lease
    ])

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        # Act
        response = _bulk_delete(client, [10, 20])

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "active leases" in response.json()["detail"]
    # No deletions or commit
    assert not getattr(mock_session.delete, "await_count", 0)
    assert not getattr(mock_session.commit, "await_count", 0)


def test_bulk_delete_not_found_or_unauthorized():
    # Arrange
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    # Only one tenant found from DB, but request asks two -> triggers 404
    only_one = _tenant(100, landlord_id)

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[
        MockScalarResult([only_one]),
    ])

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        response = _bulk_delete(client, [100, 200])

    assert response.status_code == status.HTTP_404_NOT_FOUND
    # No further actions
    assert not getattr(mock_session.delete, "await_count", 0)
    assert not getattr(mock_session.commit, "await_count", 0)


def test_bulk_delete_empty_list_noop():
    # Arrange
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        # Act
        response = _bulk_delete(client, [])

    # Assert
    # Router now validates empty lists and returns 400
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "No tenant IDs provided" in response.json()["detail"]
    mock_session.execute.assert_not_awaited()
    assert not getattr(mock_session.commit, "await_count", 0)


def test_bulk_delete_integrity_error_returns_400():
    # Arrange
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    t1 = _tenant(7, landlord_id)
    t2 = _tenant(8, landlord_id)

    mock_session = AsyncMock()
    # First execute -> tenants list; Second execute -> active lease tenant ids; Third execute -> non-active leases
    mock_session.execute = AsyncMock(side_effect=[
        MockScalarResult([t1, t2]),
        MockScalarResult([]),  # No active leases
        MockScalarResult([]),  # No non-active leases
    ])
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("fk")))
    mock_session.rollback = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        response = _bulk_delete(client, [7, 8])

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Could not delete tenants" in response.json()["detail"]
    mock_session.rollback.assert_awaited_once()


def test_bulk_delete_unexpected_error_returns_500():
    # Arrange
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    t1 = _tenant(70, landlord_id)
    t2 = _tenant(80, landlord_id)

    mock_session = AsyncMock()
    # First execute -> tenants list; Second execute -> active lease tenant ids; Third execute -> non-active leases
    mock_session.execute = AsyncMock(side_effect=[
        MockScalarResult([t1, t2]),
        MockScalarResult([]),  # No active leases
        MockScalarResult([]),  # No non-active leases
    ])
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock(side_effect=Exception("boom"))
    mock_session.rollback = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        response = _bulk_delete(client, [70, 80])

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unexpected error" in response.json()["detail"].lower()
    mock_session.rollback.assert_awaited_once()


def test_bulk_delete_as_admin_success():
    # Arrange
    admin_user = create_test_user(email="admin@example.com", user_type=UserType.LANDLORD.value, is_admin=True)

    t1 = _tenant(901, uuid4())
    t2 = _tenant(902, uuid4())

    mock_session = AsyncMock()
    # First execute -> tenants list; Second execute -> active lease tenant ids; Third execute -> non-active leases
    mock_session.execute = AsyncMock(side_effect=[
        MockScalarResult([t1, t2]),
        MockScalarResult([]),  # No active leases
        MockScalarResult([]),  # No non-active leases
    ])
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        response = _bulk_delete(client, [901, 902])

    assert response.status_code == status.HTTP_204_NO_CONTENT
    # Verify bulk SQL delete was executed (not individual ORM deletes)
    # Execute calls: 1) fetch tenants, 2) check active leases, 3) check & delete non-active leases + bulk delete tenants
    assert mock_session.execute.await_count >= 3
    # Should NOT use individual session.delete() calls (tenants use SQL bulk delete)
    assert not hasattr(mock_session.delete, 'await_count') or mock_session.delete.await_count == 0
    mock_session.commit.assert_awaited_once()


