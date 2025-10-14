"""
Unit tests for the tenant GET service functions using hybrid API testing pattern.
"""
from datetime import datetime, timezone
import pytest
from fastapi import status, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.tenants.schemas import TenantResponse
from Backend.models.tenant import TenantStatus, Tenant
from Backend.models.enums import TenantType
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
# GET TESTS - get_tenant and get_tenants
# =============================================================================

def test_get_tenant_success():
    # Arrange
    tenant_id = 123
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="test@example.com")
    
    # Create a proper mock tenant with landlord_id matching the user
    mock_tenant_orm = Tenant(
        id=tenant_id,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone=None,
        status=TenantStatus.ACTIVE,
        landlord_id=user_id,  # This is crucial - must match current_user.id
        current_property_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    mock_tenant_response = TenantResponse(
        id=tenant_id,
        tenant_type=TenantType.INDIVIDUAL,
        first_name="John",
        last_name="Doe",
        phone=None,
        email="john.doe@example.com",
        status=TenantStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        current_property_id=None,
        unit=None,
        property=None,
    )

    # Mock the service functions
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
        
        mock_check_permission.return_value = mock_tenant_orm
        mock_enrich.return_value = [mock_tenant_response]
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/tenants/{tenant_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == tenant_id
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["email"] == "john.doe@example.com"
        assert "leases" in data
        assert isinstance(data["leases"], list)


def test_get_tenant_by_id_success():
    # Arrange
    tenant_id = 202
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord2@example.com")

    # Mock tenant ORM and response
    mock_tenant_orm = Tenant(
        id=tenant_id,
        first_name="Sam",
        last_name="Smith",
        email="sam.smith@example.com",
        phone="555-2222",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=10,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    mock_tenant_response = TenantResponse(
        id=tenant_id,
        tenant_type=TenantType.INDIVIDUAL,
        first_name="Sam",
        last_name="Smith",
        phone="555-2222",
        email="sam.smith@example.com",
        status=TenantStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        current_property_id=10,
        unit=None,
        property=None,
    )

    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
        
        mock_check_permission.return_value = mock_tenant_orm
        mock_enrich.return_value = [mock_tenant_response]
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/tenants/{tenant_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == tenant_id
        assert data["first_name"] == "Sam"
        assert data["last_name"] == "Smith"
        assert data["email"] == "sam.smith@example.com"
        assert data["current_property_id"] == 10
        assert "leases" in data
        assert isinstance(data["leases"], list)


def test_get_tenants_landlord_scope():
    # Arrange
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    # Mock ORM tenants (only those assigned to landlord's properties)
    tenant1 = Tenant(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="1234567890",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=10,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    tenant2 = Tenant(
        id=2,
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@example.com",
        phone="0987654321",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=20,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    tenants_orm = [tenant1, tenant2]

    # Mock the query builder to return a query object
    mock_query = MagicMock()
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query

    # Patch build_filtered_tenants_query to return our mock_query
    with patch("Backend.api.tenants.router.build_filtered_tenants_query") as mock_build_query, \
         patch("Backend.api.tenants.router.build_unassigned_tenants_query"), \
         patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
        
        mock_build_query.return_value = mock_query
        
        # Mock session.execute to return an object with scalars().all()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = tenants_orm
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Patch enrich_tenants_with_details to return TenantResponse objects
        tenant_response1 = TenantResponse(
            id=1,
            tenant_type=TenantType.INDIVIDUAL,
            first_name="John",
            last_name="Doe",
            phone="1234567890",
            email="john.doe@example.com",
            status=TenantStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            current_property_id=10,
            unit=None,
            property=None,
        )
        tenant_response2 = TenantResponse(
            id=2,
            tenant_type=TenantType.INDIVIDUAL,
            first_name="Jane",
            last_name="Smith",
            phone="0987654321",
            email="jane.smith@example.com",
            status=TenantStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            current_property_id=20,
            unit=None,
            property=None,
        )
        mock_enrich.return_value = [tenant_response1, tenant_response2]
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/tenants/")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert all(isinstance(t, dict) for t in data)
        assert {t["id"] for t in data} == {1, 2}
        assert all(t["status"] == TenantStatus.ACTIVE.value for t in data)
        assert all(t["current_property_id"] in [10, 20] for t in data)
        assert all("leases" in t and isinstance(t["leases"], list) for t in data)


def test_get_tenant_not_found():
    # Arrange
    tenant_id = 999
    mock_user = create_test_user(email="test@example.com")

    # Mock check_tenant_permission to raise 404 (tenant not found)
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
            response = client.get(f"/api/tenants/{tenant_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Tenant not found" in response.json()["detail"]


def test_get_tenants_as_tenant_user_forbidden():
    """Test that tenant users cannot list tenants."""
    # Arrange
    mock_user = create_test_user(email="tenant@example.com", user_type=UserType.TENANT.value)
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        # Act
        response = client.get("/api/tenants/")

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Not authorized to list tenants" in response.json()["detail"]


def test_get_tenants_with_filters():
    """Test getting tenants with various filters."""
    # Arrange
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    # Mock empty result
    mock_query = MagicMock()
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query

    with patch("Backend.api.tenants.router.build_filtered_tenants_query") as mock_build_query, \
         patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
        
        mock_build_query.return_value = mock_query
        
        # Mock session.execute to return empty result
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        mock_enrich.return_value = []
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act - test with various query parameters
            response = client.get(
                "/api/tenants/",
                params={
                    "status_filter": "Active",
                    "search": "john",
                    "property_id": 10,
                    "skip": 10,
                    "limit": 50
                }
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0  # Empty result
        
        # Verify the query builder was called with correct parameters
        mock_build_query.assert_called_once_with(
            mock_user,
            TenantStatus.ACTIVE,
            "john",
            10
        )


def test_get_unassigned_tenants():
    """Test getting only unassigned tenants."""
    # Arrange
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    # Mock query for unassigned tenants
    mock_query = MagicMock()
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query

    with patch("Backend.api.tenants.router.build_unassigned_tenants_query") as mock_build_unassigned, \
         patch("Backend.api.tenants.router.build_filtered_tenants_query"), \
         patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
        
        mock_build_unassigned.return_value = mock_query
        
        # Mock session.execute
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        mock_enrich.return_value = []
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/tenants/?unassigned_only=true")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        # Verify unassigned query builder was called
        mock_build_unassigned.assert_called_once_with(mock_user, None)


def test_search_tenants_by_company_name():
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    search_term = "Innovate"
    
    mock_query = MagicMock()
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query

    # Patch build_filtered_tenants_query to check the search term
    with patch("Backend.api.tenants.router.build_filtered_tenants_query") as mock_build_query:
        mock_build_query.return_value = mock_query
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            client.get(f"/api/tenants/?search={search_term}")

        # Assert that the query builder was called with the correct search term
        mock_build_query.assert_called_once()
        call_args, _ = mock_build_query.call_args
        assert call_args[2] == search_term


# =============================================================================
# GET TENANT METRICS TESTS - covers router.py:514,521,527
# =============================================================================

def test_get_tenant_metrics_success():
    """Test successfully retrieving tenant metrics - covers router.py:514,521,527"""
    # Arrange
    tenant_id = 1
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)

    # Mock tenant ORM
    mock_tenant_orm = Tenant(
        id=tenant_id,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone=None,
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant_orm

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/tenants/{tenant_id}/metrics")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify metrics response structure
        assert "payment_performance" in data
        assert "open_balance" in data
        assert "ticket_resolution" in data
        assert "upcoming_events" in data
        
        # Verify payment performance structure
        assert data["payment_performance"]["rate"] is None
        assert data["payment_performance"]["status"] == "no_data"
        
        # Verify open balance structure
        assert data["open_balance"]["total_balance"] == "0"
        assert data["open_balance"]["is_overdue"] is False


def test_get_tenant_metrics_tenant_not_found():
    """Test getting metrics for non-existent tenant"""
    # Arrange
    tenant_id = 999
    mock_user = create_test_user()

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
            response = client.get(f"/api/tenants/{tenant_id}/metrics")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Tenant not found" in response.json()["detail"]


def test_get_tenant_metrics_forbidden():
    """Test getting metrics without permission"""
    # Arrange
    tenant_id = 1
    mock_user = create_test_user(email="unauthorized@example.com")

    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this tenant"
        )

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/tenants/{tenant_id}/metrics")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["detail"]
