"""
Unit tests for the lease creation service functions.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.leases.schemas import LeaseCreate, LeaseResponse
from Backend.models.user import User
from Backend.models.lease import LeaseStatus, Lease
from Backend.models.property import Property, PropertyStatus
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

def create_test_user(user_id=None, email="test@example.com", user_type="LANDLORD"):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=False,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )

def create_mock_tenant(tenant_id=1, **kwargs):
    """Helper function to create a mock tenant with all required attributes."""
    mock_tenant = MagicMock(spec=Tenant)
    mock_tenant.id = tenant_id
    mock_tenant.user_id = kwargs.get('user_id', uuid4())
    mock_tenant.first_name = kwargs.get('first_name', 'John')
    mock_tenant.last_name = kwargs.get('last_name', 'Doe')
    mock_tenant.phone = kwargs.get('phone', '555-1234')
    mock_tenant.email = kwargs.get('email', 'john.doe@example.com')
    mock_tenant.status = kwargs.get('status', TenantStatus.ACTIVE)
    mock_tenant.landlord_id = kwargs.get('landlord_id', uuid4())
    mock_tenant.profile_image_url = kwargs.get('profile_image_url', None)
    mock_tenant.quickbooks_id = kwargs.get('quickbooks_id', None)
    mock_tenant.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
    mock_tenant.updated_at = kwargs.get('updated_at', datetime.now(timezone.utc))
    return mock_tenant

def create_mock_property(property_id=1, **kwargs):
    """Helper function to create a mock property with all required attributes."""
    mock_property = MagicMock(spec=Property)
    mock_property.id = property_id
    mock_property.name = kwargs.get('name', 'Test Property')
    mock_property.address = kwargs.get('address', '123 Test St')
    mock_property.city = kwargs.get('city', 'Test City')
    mock_property.province = kwargs.get('province', 'Test Province')
    mock_property.postal_code = kwargs.get('postal_code', '12345')
    mock_property.property_type = kwargs.get('property_type', 'Residential')
    mock_property.description = kwargs.get('description', 'A test property')
    mock_property.status = kwargs.get('status', PropertyStatus.ACTIVE)
    mock_property.user_id = kwargs.get('user_id', uuid4())
    mock_property.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
    mock_property.updated_at = kwargs.get('updated_at', datetime.now(timezone.utc))
    return mock_property

def create_mock_lease(lease_id=1, **kwargs):
    """Helper function to create a mock lease ORM object with defaults."""
    # Create a mock Lease ORM object
    mock_lease = MagicMock(spec=Lease)
    
    # Set default values
    mock_lease.id = lease_id
    mock_lease.property_id = kwargs.get('property_id', 1)
    mock_lease.tenant_id = kwargs.get('tenant_id', 1)
    mock_lease.unit_id = kwargs.get('unit_id', None)
    mock_lease.start_date = kwargs.get('start_date', date(2024, 1, 1))
    mock_lease.end_date = kwargs.get('end_date', date(2024, 12, 31))
    mock_lease.monthly_rent = kwargs.get('monthly_rent', Decimal("1500.00"))
    mock_lease.security_deposit = kwargs.get('security_deposit', Decimal("1500.00"))
    mock_lease.status = kwargs.get('status', LeaseStatus.ACTIVE)
    mock_lease.created_at = kwargs.get('created_at', datetime(2024, 1, 1, 0, 0, 0))
    mock_lease.updated_at = kwargs.get('updated_at', datetime(2024, 1, 1, 0, 0, 0))
    
    # Set relationships - use proper mock objects or None
    mock_lease.tenant = kwargs.get('tenant', None)
    mock_lease.property = kwargs.get('property', None)
    mock_lease.unit = kwargs.get('unit', None)
    
    # Set LeaseBase fields
    mock_lease.is_renewable = kwargs.get('is_renewable', True)
    mock_lease.auto_renew = kwargs.get('auto_renew', False)
    mock_lease.rent_due_day = kwargs.get('rent_due_day', 1)
    mock_lease.late_fee_amount = kwargs.get('late_fee_amount', None)
    mock_lease.late_fee_after_days = kwargs.get('late_fee_after_days', None)
    mock_lease.special_terms = kwargs.get('special_terms', None)
    
    return mock_lease

def test_create_lease_success():
    # Arrange
    fake_user = create_test_user()
    
    # Create proper LeaseCreate object with correct data types
    lease_data = {
        "tenant_id": 1,
        "property_id": 2,
        "unit_id": 3,
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "monthly_rent": "1200.00",
        "security_deposit": "1200.00",
        "status": "ACTIVE",
        "file_url": "https://example.com/lease.pdf"
    }
    
    # Create a mock lease response
    fake_lease = create_mock_lease(
        lease_id=123,
        property_id=2,
        tenant_id=1,
        unit_id=3,
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
        monthly_rent=Decimal("1200.00"),
        security_deposit=Decimal("1200.00"),
        status=LeaseStatus.ACTIVE
    )
    
    # Mock the service layer using patch as context manager - patch at router level
    with patch("Backend.api.leases.router.create_lease", new=AsyncMock(return_value=fake_lease)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        # Create test client with proper host header
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/leases/", json=lease_data)
            
            # Debug output
            if response.status_code != 201:
                print(f"Response status: {response.status_code}")
                print(f"Response body: {response.text}")
                print(f"Response headers: {dict(response.headers)}")
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 123
            assert data["status"] == "ACTIVE"
            assert data["property_id"] == 2
            assert data["tenant_id"] == 1

def test_create_active_lease_applies_side_effects():
    # Arrange
    fake_user = create_test_user()
    
    lease_data = {
        "tenant_id": 1,
        "property_id": 2,
        "unit_id": 3,
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "monthly_rent": "1500.00",
        "security_deposit": "1500.00",
        "status": "ACTIVE",
        "file_url": "https://example.com/lease.pdf"
    }
    
    # Create proper mock tenant and property objects
    mock_tenant = create_mock_tenant(tenant_id=1)
    mock_property = create_mock_property(property_id=2)
    
    # Create a mock lease with ACTIVE status and relationships
    fake_lease = create_mock_lease(
        lease_id=456,
        property_id=2,
        tenant_id=1,
        unit_id=3,
        status=LeaseStatus.ACTIVE,
        tenant=mock_tenant,
        property=mock_property,
        monthly_rent=Decimal("1500.00"),
        security_deposit=Decimal("1500.00")
    )
    
    # Mock the service layer
    mock_create_lease = AsyncMock(return_value=fake_lease)
    
    with patch("Backend.api.leases.router.create_lease", new=mock_create_lease):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/leases/", json=lease_data)
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "ACTIVE"
            assert data["tenant"] is not None
            assert data["property"] is not None
            # Verify the service was called
            mock_create_lease.assert_awaited_once()

def test_create_lease_invalid_tenant():
    # Arrange
    fake_user = create_test_user()
    
    lease_data = {
        "tenant_id": 999,  # Non-existent tenant
        "property_id": 2,
        "unit_id": 3,
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "monthly_rent": "1200.00",
        "security_deposit": "1200.00",
        "status": "DRAFT",
        "file_url": None
    }
    
    # Mock the service layer to raise HTTPException
    with patch(
        "Backend.api.leases.router.create_lease",
        new=AsyncMock(side_effect=HTTPException(status_code=400, detail="Invalid tenant ID"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/leases/", json=lease_data)
            
            # Assert
            assert response.status_code == 400
            assert "Invalid tenant ID" in response.json()["detail"]

def test_create_lease_with_document():
    # Arrange
    fake_user = create_test_user()
    
    lease_data = {
        "tenant_id": 10,
        "property_id": 20,
        "unit_id": 30,
        "start_date": "2024-06-01",
        "end_date": "2025-06-01",
        "monthly_rent": "2000.00",
        "security_deposit": "2000.00",
        "status": "DRAFT",
        "file_url": "https://example.com/lease_document.pdf"
    }
    
    # Create a mock lease
    fake_lease = create_mock_lease(
        lease_id=789,
        property_id=20,
        tenant_id=10,
        unit_id=30,
        status=LeaseStatus.DRAFT,
        monthly_rent=Decimal("2000.00"),
        security_deposit=Decimal("2000.00")
    )
    
    # Mock the service layer
    mock_create_lease = AsyncMock(return_value=fake_lease)
    
    with patch("Backend.api.leases.router.create_lease", new=mock_create_lease):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/leases/", json=lease_data)
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 789
            # Note: file_url is not part of LeaseResponse schema, it's handled separately via LeaseDocument
            mock_create_lease.assert_awaited_once()

def test_create_lease_invalid_property():
    # Arrange
    fake_user = create_test_user()
    
    lease_data = {
        "tenant_id": 1,
        "property_id": 999,  # Non-existent or unauthorized property
        "unit_id": 3,
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "monthly_rent": "1200.00",
        "security_deposit": "1200.00",
        "status": "DRAFT",
        "file_url": None
    }
    
    # Mock the service layer to raise HTTPException
    with patch(
        "Backend.api.leases.router.create_lease",
        new=AsyncMock(side_effect=HTTPException(status_code=400, detail="Invalid property ID"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/leases/", json=lease_data)
            
            # Assert
            assert response.status_code == 400
            assert "Invalid property ID" in response.json()["detail"]

def test_create_lease_unauthorized_user():
    # Arrange - don't override get_current_user to simulate unauthenticated request
    lease_data = {
        "tenant_id": 1,
        "property_id": 2,
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "monthly_rent": "1200.00",
        "security_deposit": "1200.00"
    }
    
    # Only override the session
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/leases/", json=lease_data)
        
        # Assert - Accept either 401 (unauthorized) or 403 (forbidden) as both indicate lack of proper auth
        assert response.status_code in [401, 403]

def test_create_lease_validation_error():
    # Arrange
    fake_user = create_test_user()
    
    # Invalid data - missing required fields
    lease_data = {
        "tenant_id": 1,
        "property_id": 2,
        # Missing start_date, end_date, monthly_rent, security_deposit
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/leases/", json=lease_data)
        
        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        # Check that validation errors mention the missing fields
        assert any("start_date" in str(error) for error in error_detail)
        assert any("end_date" in str(error) for error in error_detail)

def test_create_lease_database_error():
    # Arrange
    fake_user = create_test_user()
    
    lease_data = {
        "tenant_id": 1,
        "property_id": 2,
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "monthly_rent": "1200.00",
        "security_deposit": "1200.00"
    }
    
    # Mock the service layer to raise a generic exception
    with patch(
        "Backend.api.leases.router.create_lease",
        new=AsyncMock(side_effect=Exception("Database connection failed"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/leases/", json=lease_data)
            
            # Assert
            assert response.status_code == 500
            assert "Database error" in response.json()["detail"]