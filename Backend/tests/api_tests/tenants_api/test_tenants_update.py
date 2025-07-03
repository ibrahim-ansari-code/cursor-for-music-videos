"""
Unit tests for the tenant UPDATE service functions using hybrid API testing pattern.
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
# UPDATE TESTS - update_tenant
# =============================================================================

def test_update_tenant_success():
    # Arrange
    tenant_id = 42
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    new_property_id = 100

    # Existing tenant ORM object
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="OldFirst",
        last_name="OldLast",
        email="old@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=50,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Prepare update data
    tenant_update = {
        "first_name": "NewFirst",
        "last_name": "NewLast",
        "phone": "555-123-4567",
        "email": "new@example.com",
        "current_property_id": new_property_id
    }

    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.create_audit_datetime") as mock_audit_datetime:
        
        mock_check_permission.return_value = mock_tenant
        
        # Mock session
        mock_session = AsyncMock()
        # Mock session.scalar to simulate property ownership check (property exists and is owned by landlord)
        mock_session.scalar = AsyncMock(return_value=True)
        mock_session.add = MagicMock()  # session.add() is synchronous
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Mock create_audit_datetime to return a fixed datetime
        mock_update_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_audit_datetime.return_value = mock_update_time
        
        # Mock TenantResponse.model_validate
        with patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_validate:
            mock_response = TenantResponse(
                id=tenant_id,
                tenant_type=TenantType.INDIVIDUAL,
                first_name="NewFirst",
                last_name="NewLast",
                phone="555-123-4567",
                email="new@example.com",
                status=TenantStatus.ACTIVE,
                created_at=mock_tenant.created_at,
                updated_at=mock_update_time,
                current_property_id=new_property_id,
                unit=None,
                property=None,
            )
            mock_validate.return_value = [mock_response]
            
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                # Act
                response = client.patch(f"/api/tenants/{tenant_id}", json=tenant_update)

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == tenant_id
            assert data["first_name"] == "NewFirst"
            assert data["last_name"] == "NewLast"
            assert data["phone"] == "555-123-4567"
            assert data["email"] == "new@example.com"
            assert data["current_property_id"] == new_property_id


def test_partial_update_tenant():
    # Arrange
    tenant_id = 2
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    # Existing tenant ORM object
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="OldFirst",
        last_name="OldLast",
        email="old@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=10,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Prepare update data (only last_name is updated)
    tenant_update = {
        "last_name": "NewLast"
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.create_audit_datetime") as mock_audit_datetime:
        
        mock_check_permission.return_value = mock_tenant
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() is synchronous
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Mock create_audit_datetime to return a fixed datetime
        mock_update_time = datetime(2024, 6, 2, 15, 0, 0, tzinfo=timezone.utc)
        mock_audit_datetime.return_value = mock_update_time
        
        # Mock TenantResponse.model_validate
        with patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_validate:
            mock_response = TenantResponse(
                id=tenant_id,
                tenant_type=TenantType.INDIVIDUAL,
                first_name="OldFirst",
                last_name="NewLast",
                phone="555-000-0000",
                email="old@example.com",
                status=TenantStatus.ACTIVE,
                created_at=mock_tenant.created_at,
                updated_at=mock_update_time,
                current_property_id=10,
                unit=None,
                property=None,
            )
            mock_validate.return_value = [mock_response]
            
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                # Act
                response = client.patch(f"/api/tenants/{tenant_id}", json=tenant_update)

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == tenant_id
            assert data["first_name"] == "OldFirst"
            assert data["last_name"] == "NewLast"
            assert data["phone"] == "555-000-0000"
            assert data["email"] == "old@example.com"
            mock_session.add.assert_called_once_with(mock_tenant)
            mock_session.commit.assert_awaited_once()
            mock_session.refresh.assert_awaited_once_with(mock_tenant)


def test_non_privileged_user_update_forbidden():
    # Arrange
    tenant_id = 77
    mock_user = create_test_user(email="unauthorized@example.com", user_type=UserType.TENANT.value)
    
    tenant_update = {
        "first_name": "Should",
        "last_name": "Fail",
        "email": "should.fail@example.com"
    }

    # Mock check_tenant_permission to raise 403 Forbidden
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this tenant"
        )
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.patch(f"/api/tenants/{tenant_id}", json=tenant_update)

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["detail"]


def test_landlord_updates_tenant_info_without_property_change():
    # Arrange
    tenant_id = 123
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    # Existing tenant ORM object (property assignment unchanged)
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="OldFirst",
        last_name="OldLast",
        email="old@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=10,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Prepare update data (no property change)
    tenant_update = {
        "first_name": "NewFirst",
        "last_name": "NewLast",
        "phone": "555-123-4567",
        "email": "new@example.com",
        "current_property_id": 10
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.create_audit_datetime") as mock_audit_datetime:
        
        mock_check_permission.return_value = mock_tenant
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() is synchronous
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Mock create_audit_datetime to return a fixed datetime
        mock_update_time = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        mock_audit_datetime.return_value = mock_update_time
        
        # Mock TenantResponse.model_validate
        with patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_validate:
            mock_response = TenantResponse(
                id=tenant_id,
                tenant_type=TenantType.INDIVIDUAL,
                first_name="NewFirst",
                last_name="NewLast",
                phone="555-123-4567",
                email="new@example.com",
                status=TenantStatus.ACTIVE,
                created_at=mock_tenant.created_at,
                updated_at=mock_update_time,
                current_property_id=10,
                unit=None,
                property=None,
            )
            mock_validate.return_value = [mock_response]
            
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                # Act
                response = client.patch(f"/api/tenants/{tenant_id}", json=tenant_update)

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == tenant_id
            assert data["first_name"] == "NewFirst"
            assert data["last_name"] == "NewLast"
            assert data["phone"] == "555-123-4567"
            assert data["email"] == "new@example.com"
            assert data["current_property_id"] == 10
            mock_session.add.assert_called_once_with(mock_tenant)
            mock_session.commit.assert_awaited_once()
            mock_session.refresh.assert_awaited_once_with(mock_tenant)


def test_landlord_assigns_unowned_property_forbidden():
    # Arrange
    tenant_id = 1
    landlord_id = uuid4()
    unowned_property_id = 999
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    # Existing tenant ORM object
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=10,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Prepare update data with a property the landlord does not own
    tenant_update = {
        "current_property_id": unowned_property_id
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant
        
        # Mock session
        mock_session = AsyncMock()
        # Mock session.scalar to simulate property does not exist or is not owned by landlord
        mock_session.scalar = AsyncMock(return_value=False)
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.patch(f"/api/tenants/{tenant_id}", json=tenant_update)

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "do not own" in response.json()["detail"]


def test_tenant_not_found():
    """Test updating a non-existent tenant."""
    # Arrange
    tenant_id = 999
    mock_user = create_test_user(email="landlord@example.com")
    
    tenant_update = {
        "first_name": "Should",
        "last_name": "NotExist"
    }
    
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
            response = client.patch(f"/api/tenants/{tenant_id}", json=tenant_update)

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Tenant not found" in response.json()["detail"]


def test_update_tenant_server_error():
    """Test handling of unexpected server errors during update."""
    # Arrange
    tenant_id = 100
    mock_user = create_test_user(email="landlord@example.com")
    
    # Existing tenant
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Error",
        last_name="Test",
        email="error.test@example.com",
        phone="555-666-7777",
        status=TenantStatus.ACTIVE,
        landlord_id=mock_user.id,
        current_property_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    tenant_update = {
        "first_name": "Updated"
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.create_audit_datetime") as mock_audit_datetime:
        
        mock_check_permission.return_value = mock_tenant
        mock_audit_datetime.side_effect = Exception("Database connection error")
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.patch(f"/api/tenants/{tenant_id}", json=tenant_update)

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to update tenant" in response.json()["detail"]
        mock_session.rollback.assert_awaited_once()


def test_update_tenant_to_company_type():
    # Arrange
    tenant_id = 50
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    mock_tenant = Tenant(
        id=tenant_id,
        first_name="IndividualFirst",
        last_name="IndividualLast",
        email="individual@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        tenant_type=TenantType.INDIVIDUAL,
        landlord_id=landlord_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    tenant_update = {
        "tenant_type": "Company",
        "company_name": "New Company LLC",
        "contact_person": "New Contact",
        "first_name": None,
        "last_name": None
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant
        
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        with patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = [TenantResponse(
                id=tenant_id,
                tenant_type=TenantType.COMPANY,
                company_name="New Company LLC",
                contact_person="New Contact",
                email="individual@example.com",
                status=TenantStatus.ACTIVE,
                created_at=mock_tenant.created_at,
                updated_at=datetime.now(timezone.utc),
                phone=None,
                first_name=None,
                last_name=None,
                current_property_id=None,
                unit=None,
                property=None,
                leases=[]
            )]
            
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                response = client.patch(f"/api/tenants/{tenant_id}", json=tenant_update)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["tenant_type"] == "Company"
            assert data["company_name"] == "New Company LLC"
            assert data.get("first_name") is None
            assert data.get("last_name") is None


def test_update_company_tenant_contact_person():
    # Arrange
    tenant_id = 51
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    mock_tenant = Tenant(
        id=tenant_id,
        tenant_type=TenantType.COMPANY,
        company_name="Tech Corp",
        contact_person="Old Contact",
        email="contact@techcorp.com",
        landlord_id=landlord_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    tenant_update = {
        "contact_person": "Updated Contact Name"
    }

    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant
        
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = [TenantResponse(
                id=tenant_id,
                tenant_type=TenantType.COMPANY,
                company_name="Tech Corp",
                contact_person="Updated Contact Name",
                email="contact@techcorp.com",
                status=TenantStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                phone=None,
                first_name=None,
                last_name=None,
                current_property_id=None,
                unit=None,
                property=None,
                leases=[]
            )]
            
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                response = client.patch(f"/api/tenants/{tenant_id}", json=tenant_update)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["contact_person"] == "Updated Contact Name"
            assert data["company_name"] == "Tech Corp"
