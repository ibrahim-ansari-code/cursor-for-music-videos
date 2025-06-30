"""
Unit tests for the units lease GET endpoint using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.leases.schemas import LeaseResponse
from Backend.models.lease import LeaseStatus
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.user import User
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

def create_mock_tenant(tenant_id=1, **kwargs):
    """Helper function to create a mock tenant."""
    now = datetime.now(timezone.utc)
    mock_tenant = MagicMock(spec=Tenant)
    mock_tenant.id = tenant_id
    mock_tenant.first_name = kwargs.get('first_name', 'John')
    mock_tenant.last_name = kwargs.get('last_name', 'Doe')
    mock_tenant.email = kwargs.get('email', 'john.doe@example.com')
    mock_tenant.phone = kwargs.get('phone', '555-1234')
    mock_tenant.created_at = kwargs.get('created_at', now)
    mock_tenant.updated_at = kwargs.get('updated_at', now)
    return mock_tenant

def create_mock_property(property_id=1, **kwargs):
    """Helper function to create a mock property."""
    now = datetime.now(timezone.utc)
    mock_property = MagicMock(spec=Property)
    mock_property.id = property_id
    mock_property.name = kwargs.get('name', 'Test Property')
    mock_property.address = kwargs.get('address', '123 Main St')
    mock_property.city = kwargs.get('city', 'Test City')
    mock_property.province = kwargs.get('province', 'Test Province')
    mock_property.postal_code = kwargs.get('postal_code', '12345')
    mock_property.created_at = kwargs.get('created_at', now)
    mock_property.updated_at = kwargs.get('updated_at', now)
    return mock_property

# =============================================================================
# GET UNIT LEASE TESTS
# =============================================================================

def test_get_unit_lease_success():
    """Test successful retrieval of a unit's active lease."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    lease_id = 1
    property_id = 1
    tenant_id = 1
    
    # Create mock tenant and property
    mock_tenant = create_mock_tenant(tenant_id)
    mock_property = create_mock_property(property_id)
    
    # Create mock lease response
    now = datetime.now(timezone.utc)
    mock_lease = LeaseResponse(
        id=lease_id,
        tenant_id=tenant_id,
        property_id=property_id,
        unit_id=unit_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        monthly_rent=Decimal("1500.00"),
        security_deposit=Decimal("1500.00"),
        status=LeaseStatus.ACTIVE,
        is_renewable=True,
        auto_renew=False,
        rent_due_day=1,
        late_fee_amount=Decimal("50.00"),
        late_fee_after_days=5,
        special_terms="No pets allowed",
        created_at=now,
        updated_at=now,
        tenant=mock_tenant,
        property=mock_property
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.get_unit_lease', new_callable=AsyncMock) as mock_get_lease:
        mock_get_lease.return_value = mock_lease
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/units/{unit_id}/lease",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == lease_id
        assert response_data["unit_id"] == unit_id
        assert response_data["property_id"] == property_id
        assert response_data["tenant_id"] == tenant_id
        assert response_data["status"] == "ACTIVE"
        assert response_data["monthly_rent"] == "1500.00"
        assert response_data["start_date"] == "2024-01-01"
        assert response_data["end_date"] == "2024-12-31"
        
        # Verify service was called correctly
        mock_get_lease.assert_called_once_with(unit_id, mock_session, fake_user)

def test_get_unit_lease_not_found():
    """Test getting lease for a unit that doesn't exist."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 999
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.get_unit_lease', new_callable=AsyncMock) as mock_get_lease:
        mock_get_lease.side_effect = HTTPException(status_code=404, detail="Unit not found")
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/units/{unit_id}/lease",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Unit not found"

def test_get_unit_lease_no_active_lease():
    """Test getting lease for a unit with no active lease."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.get_unit_lease', new_callable=AsyncMock) as mock_get_lease:
        mock_get_lease.side_effect = HTTPException(
            status_code=404, 
            detail="No active lease found for this unit"
        )
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/units/{unit_id}/lease",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "No active lease found for this unit"

def test_get_unit_lease_forbidden():
    """Test getting lease for a unit the user doesn't have permission to access."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.get_unit_lease', new_callable=AsyncMock) as mock_get_lease:
        mock_get_lease.side_effect = HTTPException(
            status_code=403, 
            detail="You don't have permission to access this unit"
        )
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/units/{unit_id}/lease",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 403
        assert response.json()["detail"] == "You don't have permission to access this unit"

def test_get_unit_lease_unauthorized():
    """Test getting unit lease without authentication."""
    # Arrange
    unit_id = 1
    
    # Act
    client = TestClientWithHost(app)
    response = client.get(f"/api/units/{unit_id}/lease")
    
    # Assert - Accept either 401 or 403 as both indicate lack of proper auth
    assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"

def test_get_unit_lease_server_error():
    """Test handling of unexpected server errors."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise generic exception
    with patch('Backend.api.units.service.UnitService.get_unit_lease', new_callable=AsyncMock) as mock_get_lease:
        mock_get_lease.side_effect = Exception("Database connection error")
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/units/{unit_id}/lease",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 500
        assert "An unexpected error occurred" in response.json()["detail"]