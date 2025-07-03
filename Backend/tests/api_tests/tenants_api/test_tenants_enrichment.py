"""
API tests for tenant enrichment functionality and edge cases.

These tests specifically cover the enrichment process and error handling
to prevent regression of the bugs we fixed.
"""
import pytest
from datetime import datetime, timezone
from fastapi import status, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType, TenantType
from Backend.api.tenants.schemas import TenantResponse
from Backend.models.tenant import TenantStatus
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


def test_create_tenant_enrichment_failure():
    """Test that create_tenant handles enrichment failure gracefully and returns proper error."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    tenant_data = {
        "tenant_type": "Individual",
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "phone": "1234567890",
        "status": "Active",
    }
    
    # Create mock tenant
    mock_tenant = MagicMock()
    mock_tenant.id = 999
    mock_tenant.first_name = "Test"
    mock_tenant.last_name = "User"
    mock_tenant.email = "test@example.com"
    mock_tenant.phone = "1234567890"
    mock_tenant.status = TenantStatus.ACTIVE
    mock_tenant.created_at = datetime.now(timezone.utc)
    mock_tenant.updated_at = datetime.now(timezone.utc)

    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
         patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save, \
         patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
        
        mock_determine_landlord.return_value = mock_user.id
        mock_create_save.return_value = mock_tenant
        
        # Mock enrichment to return empty list (failure case)
        mock_enrich.return_value = []
        
        # Mock session
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
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert f"Failed to retrieve created tenant details for tenant ID {mock_tenant.id}" in response.json()["detail"]
        mock_session.rollback.assert_awaited_once()


def test_update_tenant_enrichment_failure():
    """Test that update_tenant handles enrichment failure gracefully and returns proper error."""
    # Arrange
    tenant_id = 123
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    # Existing tenant ORM object
    mock_tenant = MagicMock()
    mock_tenant.id = tenant_id
    mock_tenant.first_name = "OldFirst"
    mock_tenant.last_name = "OldLast"
    mock_tenant.email = "old@example.com"
    mock_tenant.phone = "555-000-0000"
    mock_tenant.status = TenantStatus.ACTIVE
    mock_tenant.landlord_id = landlord_id
    mock_tenant.current_property_id = 10
    mock_tenant.created_at = datetime.now(timezone.utc)
    mock_tenant.updated_at = datetime.now(timezone.utc)
    
    tenant_update = {
        "first_name": "NewFirst",
        "last_name": "NewLast",
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.create_audit_datetime") as mock_audit_datetime, \
         patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
        
        mock_check_permission.return_value = mock_tenant
        mock_audit_datetime.return_value = datetime.now(timezone.utc)
        
        # Mock enrichment to return empty list (failure case)
        mock_enrich.return_value = []
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.patch(f"/api/tenants/{tenant_id}", json=tenant_update)

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert f"Failed to retrieve updated tenant details for tenant ID {tenant_id}" in response.json()["detail"]
        # Note: rollback is not called in update because the error happens after commit


def test_create_individual_tenant_excludes_company_fields():
    """Test that creating an individual tenant properly excludes company fields."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    tenant_data = {
        "tenant_type": "Individual",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "1234567890",
        "status": "Active",
        # Don't send company fields at all for individual tenants
    }
    
    # Create mock tenant
    mock_tenant = MagicMock()
    mock_tenant.id = 1
    mock_tenant.tenant_type = TenantType.INDIVIDUAL
    mock_tenant.first_name = "John"
    mock_tenant.last_name = "Doe"
    mock_tenant.email = "john.doe@example.com"
    mock_tenant.company_name = None
    mock_tenant.contact_person = None
    mock_tenant.created_at = datetime.now(timezone.utc)
    mock_tenant.updated_at = datetime.now(timezone.utc)

    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
         patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save, \
         patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
        
        mock_determine_landlord.return_value = mock_user.id
        mock_create_save.return_value = mock_tenant
        
        # Mock successful enrichment
        mock_enrich.return_value = [TenantResponse(
            id=1,
            tenant_type=TenantType.INDIVIDUAL,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890",
            status=TenantStatus.ACTIVE,
            created_at=mock_tenant.created_at,
            updated_at=mock_tenant.updated_at,
            company_name=None,
            contact_person=None,
            current_property_id=None,
            unit=None,
            property=None,
            leases=[]
        )]
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/tenants/", json=tenant_data)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["company_name"] is None
        assert data["contact_person"] is None


def test_create_company_tenant_excludes_individual_fields():
    """Test that creating a company tenant properly excludes individual name fields."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    tenant_data = {
        "tenant_type": "Company",
        "company_name": "Tech Corp",
        "contact_person": "Jane Smith",
        "email": "contact@techcorp.com",
        "phone": "9876543210",
        "status": "Active",
        # Don't send individual name fields at all for company tenants
    }
    
    # Create mock tenant
    mock_tenant = MagicMock()
    mock_tenant.id = 2
    mock_tenant.tenant_type = TenantType.COMPANY
    mock_tenant.company_name = "Tech Corp"
    mock_tenant.contact_person = "Jane Smith"
    mock_tenant.email = "contact@techcorp.com"
    mock_tenant.first_name = None
    mock_tenant.last_name = None
    mock_tenant.created_at = datetime.now(timezone.utc)
    mock_tenant.updated_at = datetime.now(timezone.utc)

    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
         patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
         patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save, \
         patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
        
        mock_determine_landlord.return_value = mock_user.id
        mock_create_save.return_value = mock_tenant
        
        # Mock successful enrichment
        mock_enrich.return_value = [TenantResponse(
            id=2,
            tenant_type=TenantType.COMPANY,
            company_name="Tech Corp",
            contact_person="Jane Smith",
            email="contact@techcorp.com",
            phone="9876543210",
            status=TenantStatus.ACTIVE,
            created_at=mock_tenant.created_at,
            updated_at=mock_tenant.updated_at,
            first_name=None,
            last_name=None,
            current_property_id=None,
            unit=None,
            property=None,
            leases=[]
        )]
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/tenants/", json=tenant_data)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["company_name"] == "Tech Corp"
        assert data["contact_person"] == "Jane Smith"
        assert data["first_name"] is None
        assert data["last_name"] is None


def test_update_tenant_preserves_current_property_id():
    """Test that updating a tenant preserves the current_property_id field."""
    # Arrange
    tenant_id = 456
    property_id = 789
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    # Existing tenant with property assignment
    mock_tenant = MagicMock()
    mock_tenant.id = tenant_id
    mock_tenant.first_name = "OldFirst"
    mock_tenant.last_name = "OldLast"
    mock_tenant.email = "old@example.com"
    mock_tenant.current_property_id = property_id
    mock_tenant.landlord_id = landlord_id
    
    tenant_update = {
        "first_name": "NewFirst",
        "last_name": "NewLast",
        "current_property_id": property_id  # Explicitly preserving the property
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.create_audit_datetime"), \
         patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
        
        mock_check_permission.return_value = mock_tenant
        
        # Mock successful enrichment
        mock_enrich.return_value = [TenantResponse(
            id=tenant_id,
            tenant_type=TenantType.INDIVIDUAL,
            first_name="NewFirst",
            last_name="NewLast",
            email="old@example.com",
            status=TenantStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            current_property_id=property_id,  # Property preserved
            phone=None,
            company_name=None,
            contact_person=None,
            unit=None,
            property=None,
            leases=[]
        )]
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        # Property exists check should pass
        mock_session.scalar = AsyncMock(return_value=True)
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            # Act
            response = client.patch(f"/api/tenants/{tenant_id}", json=tenant_update)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["current_property_id"] == property_id


def test_frontend_sends_empty_strings_validation_error():
    """Test that backend properly validates when frontend sends empty strings (before our fix)."""
    # This test documents the validation behavior that prompted our frontend fix
    mock_user = create_test_user(email="landlord@example.com")
    
    # Simulate what the frontend was sending before our fix
    tenant_data = {
        "tenant_type": "Individual",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "company_name": "",  # Empty string instead of null/omitted
        "contact_person": "",  # Empty string instead of null/omitted
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/tenants/", json=tenant_data)

    # Assert - This should fail validation
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_detail = response.json()["detail"]
    assert any("Name fields cannot be empty if provided" in str(err) for err in error_detail)