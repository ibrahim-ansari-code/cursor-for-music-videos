"""
Unit tests for the tenant DELETE service functions using hybrid API testing pattern.
"""
from datetime import datetime, timezone
import pytest
from fastapi import status, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.models.tenant import Tenant, TenantStatus
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

# =============================================================================
# DELETE TESTS - delete_tenant
# =============================================================================

def test_delete_tenant_success():
    # Arrange
    tenant_id = 101
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    # Mock check_tenant_permission to return a tenant ORM object
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="555-111-1111",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant
        
        # Mock session
        mock_session = AsyncMock()
        # Mock session.scalar to simulate no active leases
        mock_session.scalar = AsyncMock(return_value=None)
        # Mock session.delete and session.commit
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}")

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""
        mock_session.delete.assert_awaited_once_with(mock_tenant)
        mock_session.commit.assert_awaited_once()


def test_delete_tenant_with_active_leases():
    # Arrange
    tenant_id = 555
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    # Mock check_tenant_permission to return a tenant ORM object
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Active",
        last_name="Lease",
        email="active.lease@example.com",
        phone="555-999-9999",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant
        
        # Mock session
        mock_session = AsyncMock()
        # Mock session.scalar to simulate active lease exists
        mock_session.scalar = AsyncMock(return_value=True)
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}")

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "active leases" in response.json()["detail"]


def test_commit_called_on_successful_deletion():
    # Arrange
    tenant_id = 123
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Test",
        last_name="Tenant",
        email="test.tenant@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}")

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_session.commit.assert_awaited_once()


def test_landlord_can_delete_own_tenant_without_active_leases():
    # Arrange
    tenant_id = 10
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Test",
        last_name="Tenant",
        email="test.tenant@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}")

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_session.delete.assert_awaited_once_with(mock_tenant)
        mock_session.commit.assert_awaited_once()


def test_database_error_returns_500_on_deletion():
    # Arrange
    tenant_id = 20
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Error",
        last_name="Tenant",
        email="error.tenant@example.com",
        phone="555-1111",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock(side_effect=Exception("DB error"))
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to delete tenant" in response.json()["detail"]
        mock_session.rollback.assert_awaited_once()


def test_session_rollback_on_deletion_exception():
    # Arrange
    tenant_id = 30
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Rollback",
        last_name="Tenant",
        email="rollback.tenant@example.com",
        phone="555-2222",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock(side_effect=Exception("Simulated error"))
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_session.rollback.assert_awaited_once()



def test_delete_tenant_as_tenant_user_forbidden():
    """Test that tenant users cannot delete tenants."""
    # Arrange
    tenant_id = 50
    mock_user = create_test_user(email="tenant@example.com", user_type=UserType.TENANT.value)
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        # Act
        response = client.delete(f"/api/tenants/{tenant_id}")

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Not authorized to delete tenants" in response.json()["detail"]


def test_delete_tenant_not_found():
    """Test deleting a non-existent tenant."""
    # Arrange
    tenant_id = 999
    mock_user = create_test_user(email="landlord@example.com")
    
    # Mock check_tenant_permission to raise 404
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Tenant not found" in response.json()["detail"]


def test_delete_tenant_no_permission():
    """Test deleting a tenant the user doesn't have permission to delete."""
    # Arrange
    tenant_id = 60
    mock_user = create_test_user(email="other.landlord@example.com")
    
    # Mock check_tenant_permission to raise 403
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this tenant"
        )
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["detail"]
