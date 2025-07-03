"""
Unit tests for the tenant CREATE service functions using hybrid API testing pattern.
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
from Backend.models.tenant import TenantStatus
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
# CREATE TESTS - create_tenant
# =============================================================================

def test_create_tenant_success():
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    tenant_data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice.smith@example.com",
        "phone": "1234567890",
        "status": "Active",
        "current_property_id": None,
        "user_id": None,
        "full_name": None,
    }
    
    # Create mock tenant response
    mock_tenant = MagicMock()
    mock_tenant.id = 1
    mock_tenant.first_name = "Alice"
    mock_tenant.last_name = "Smith"
    mock_tenant.email = "alice.smith@example.com"
    mock_tenant.phone = "1234567890"
    mock_tenant.status = TenantStatus.ACTIVE
    mock_tenant.created_at = datetime.now(timezone.utc)
    mock_tenant.updated_at = datetime.now(timezone.utc)
    mock_tenant.current_property_id = None

    # Mock all the service functions that create_tenant calls
    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
         patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save:
        
        mock_determine_landlord.return_value = mock_user.id
        mock_create_save.return_value = mock_tenant
        
        # Mock session methods
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # Mock enrich_tenants_with_details to return a properly formatted response
        with patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = [TenantResponse(
                id=1,
                tenant_type=TenantType.INDIVIDUAL,
                first_name="Alice",
                last_name="Smith",
                phone="1234567890",
                email="alice.smith@example.com",
                status=TenantStatus.ACTIVE,
                created_at=mock_tenant.created_at,
                updated_at=mock_tenant.updated_at,
                current_property_id=None,
                unit=None,
                property=None,
                leases=[]
            )]
            
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                # Act
                response = client.post("/api/tenants/", json=tenant_data)

            # Assert
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["first_name"] == "Alice"
            assert data["last_name"] == "Smith"
            assert data["email"] == "alice.smith@example.com"
            assert data["status"] == TenantStatus.ACTIVE.value


def test_create_tenant_duplicate_email():
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    tenant_data = {
        "first_name": "Bob",
        "last_name": "Smith",
        "email": "bob.smith@example.com",
        "phone": "555-123-4567",
        "status": "Active",
        "current_property_id": None,
        "user_id": None,
        "full_name": None,
    }

    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
         patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save:
        
        mock_determine_landlord.return_value = mock_user.id
        # Simulate create_and_save_tenant raising HTTPException for duplicate email
        mock_create_save.side_effect = HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tenant with this email address already exists.",
        )
        
        # Mock session methods
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/tenants/", json=tenant_data)

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]


def test_create_tenant_as_tenant_user_forbidden():
    """Test that tenant users cannot create tenants."""
    # Arrange
    mock_user = create_test_user(email="tenant@example.com", user_type=UserType.TENANT.value)
    tenant_data = {
        "first_name": "Should",
        "last_name": "Fail",
        "email": "should.fail@example.com",
        "phone": "555-000-0000",
        "status": "Active",
    }
    
    # Mock _validate_user_permissions to raise HTTPException
    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock) as mock_validate:
        mock_validate.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create tenants"
        )
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/tenants/", json=tenant_data)

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["detail"]


def test_create_tenant_with_property_assignment():
    """Test creating a tenant with property assignment."""
    # Arrange
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    property_id = 100
    
    tenant_data = {
        "first_name": "Charlie",
        "last_name": "Brown",
        "email": "charlie.brown@example.com",
        "phone": "555-111-2222",
        "status": "Active",
        "current_property_id": property_id,
    }
    
    # Create mock tenant with property assignment
    mock_tenant = MagicMock()
    mock_tenant.id = 2
    mock_tenant.first_name = "Charlie"
    mock_tenant.last_name = "Brown"
    mock_tenant.email = "charlie.brown@example.com"
    mock_tenant.phone = "555-111-2222"
    mock_tenant.status = TenantStatus.ACTIVE
    mock_tenant.created_at = datetime.now(timezone.utc)
    mock_tenant.updated_at = datetime.now(timezone.utc)
    mock_tenant.current_property_id = property_id

    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
         patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save:
        
        mock_determine_landlord.return_value = landlord_id
        mock_create_save.return_value = mock_tenant
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # Mock enrich_tenants_with_details to return a properly formatted response
        with patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = [TenantResponse(
                id=2,
                tenant_type=TenantType.INDIVIDUAL,
                first_name="Charlie",
                last_name="Brown",
                phone="555-111-2222",
                email="charlie.brown@example.com",
                status=TenantStatus.ACTIVE,
                created_at=mock_tenant.created_at,
                updated_at=mock_tenant.updated_at,
                current_property_id=property_id,
                unit=None,
                property=None,
                leases=[]
            )]
            
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                # Act
                response = client.post("/api/tenants/", json=tenant_data)

            # Assert
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["first_name"] == "Charlie"
            assert data["last_name"] == "Brown"
            assert data["current_property_id"] == property_id


def test_create_tenant_invalid_property_assignment():
    """Test creating a tenant with invalid property assignment."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    
    tenant_data = {
        "first_name": "David",
        "last_name": "Jones",
        "email": "david.jones@example.com",
        "phone": "555-333-4444",
        "status": "Active",
        "current_property_id": 999,  # Non-existent property
    }
    
    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
         patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock) as mock_validate_property:
        
        mock_determine_landlord.return_value = mock_user.id
        # Simulate property validation failure
        mock_validate_property.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign tenant to a property you do not own"
        )
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/tenants/", json=tenant_data)

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "property you do not own" in response.json()["detail"]


def test_create_tenant_server_error():
    """Test handling of unexpected server errors."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    
    tenant_data = {
        "first_name": "Error",
        "last_name": "Test",
        "email": "error.test@example.com",
        "phone": "555-555-5555",
        "status": "Active",
    }
    
    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
         patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save:
        
        mock_determine_landlord.return_value = mock_user.id
        # Simulate unexpected error
        mock_create_save.side_effect = Exception("Database connection error")
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/tenants/", json=tenant_data)

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "unexpected error" in response.json()["detail"]
        mock_session.rollback.assert_awaited_once()


def test_create_company_tenant_success():
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    tenant_data = {
        "tenant_type": "Company",
        "company_name": "Innovate Inc.",
        "contact_person": "Jane Doe",
        "email": "contact@innovate.com",
        "phone": "9876543210",
        "status": "Active",
    }
    
    mock_tenant = MagicMock()
    mock_tenant.id = 3
    mock_tenant.tenant_type = TenantType.COMPANY
    mock_tenant.company_name = "Innovate Inc."
    mock_tenant.contact_person = "Jane Doe"
    mock_tenant.email = "contact@innovate.com"
    mock_tenant.phone = "9876543210"
    mock_tenant.status = TenantStatus.ACTIVE
    mock_tenant.created_at = datetime.now(timezone.utc)
    mock_tenant.updated_at = datetime.now(timezone.utc)
    mock_tenant.current_property_id = None

    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
         patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save:
        
        mock_determine_landlord.return_value = mock_user.id
        mock_create_save.return_value = mock_tenant
        
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        
        with patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = [TenantResponse(
                id=3,
                tenant_type=TenantType.COMPANY,
                company_name="Innovate Inc.",
                contact_person="Jane Doe",
                email="contact@innovate.com",
                phone="9876543210",
                status=TenantStatus.ACTIVE,
                created_at=mock_tenant.created_at,
                updated_at=mock_tenant.updated_at,
                current_property_id=None,
                unit=None,
                property=None,
                leases=[]
            )]
            
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                response = client.post("/api/tenants/", json=tenant_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["tenant_type"] == "Company"
            assert data["company_name"] == "Innovate Inc."
            assert data["contact_person"] == "Jane Doe"


def test_create_company_tenant_missing_company_name():
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    tenant_data = {
        "tenant_type": "Company",
        "contact_person": "John Smith",
        "email": "john.s@example.com",
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        response = client.post("/api/tenants/", json=tenant_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "Company name is required for company tenants" in str(data["detail"])


def test_create_tenant_optional_phone():
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    tenant_data = {
        "first_name": "NoPhone",
        "last_name": "User",
        "email": "nophone@example.com",
        "status": "Active",
    }
    
    mock_tenant = MagicMock()
    mock_tenant.id = 4
    mock_tenant.first_name = "NoPhone"
    mock_tenant.last_name = "User"
    mock_tenant.email = "nophone@example.com"
    mock_tenant.phone = None
    mock_tenant.status = TenantStatus.ACTIVE
    mock_tenant.created_at = datetime.now(timezone.utc)
    mock_tenant.updated_at = datetime.now(timezone.utc)

    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
         patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save:
        
        mock_determine_landlord.return_value = mock_user.id
        mock_create_save.return_value = mock_tenant
        
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        
        with patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = [TenantResponse(
                id=4,
                tenant_type=TenantType.INDIVIDUAL,
                first_name="NoPhone",
                last_name="User",
                email="nophone@example.com",
                status=TenantStatus.ACTIVE,
                created_at=mock_tenant.created_at,
                updated_at=mock_tenant.updated_at,
                phone=None,
                current_property_id=None,
                unit=None,
                property=None,
                leases=[]
            )]
            
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                response = client.post("/api/tenants/", json=tenant_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["first_name"] == "NoPhone"
            assert data["phone"] is None
