"""
Unit tests for the units GET endpoints using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.units.schemas import UnitResponse, TenantInfo
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

# =============================================================================
# GET SINGLE UNIT TESTS
# =============================================================================

def test_get_unit_success():
    """Test successful retrieval of a single unit."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    property_id = 1
    
    # Create mock tenant
    mock_tenant = create_mock_tenant()
    tenant_info = TenantInfo(
        id=mock_tenant.id,
        first_name=mock_tenant.first_name,
        last_name=mock_tenant.last_name,
        email=mock_tenant.email
    )
    
    # Create mock response
    now = datetime.now(timezone.utc)
    mock_response = UnitResponse(
        id=unit_id,
        property_id=property_id,
        name="Unit A",
        description="A nice unit",
        size=1200.5,
        monthly_rent=Decimal("1500.00"),
        is_rented=True,
        bedrooms=2,
        bathrooms=1.5,
        floor=1,
        tenant=tenant_info,
        created_at=now,
        updated_at=now
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.get_unit', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/units/{unit_id}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == unit_id
        assert response_data["property_id"] == property_id
        assert response_data["name"] == "Unit A"
        assert response_data["description"] == "A nice unit"
        assert response_data["size"] == 1200.5
        assert response_data["monthly_rent"] == "1500.00"
        assert response_data["is_rented"] is True
        assert response_data["bedrooms"] == 2
        assert response_data["bathrooms"] == 1.5
        assert response_data["floor"] == 1
        assert response_data["tenant"]["id"] == mock_tenant.id
        assert response_data["tenant"]["first_name"] == "John"
        assert response_data["tenant"]["last_name"] == "Doe"
        assert response_data["tenant"]["email"] == "john.doe@example.com"
        
        # Verify service was called correctly
        mock_get.assert_called_once_with(unit_id, mock_session, fake_user)

def test_get_unit_not_found():
    """Test getting a unit that doesn't exist."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 999
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.get_unit', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = HTTPException(status_code=404, detail="Unit not found")
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/units/{unit_id}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Unit not found"

def test_get_unit_forbidden():
    """Test getting a unit the user doesn't have permission to access."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.get_unit', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = HTTPException(
            status_code=403, 
            detail="You don't have permission to access this unit"
        )
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/units/{unit_id}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 403
        assert response.json()["detail"] == "You don't have permission to access this unit"

def test_get_unit_without_tenant():
    """Test getting a vacant unit (no tenant)."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    property_id = 1
    
    # Create mock response without tenant
    now = datetime.now(timezone.utc)
    mock_response = UnitResponse(
        id=unit_id,
        property_id=property_id,
        name="Unit B",
        description=None,
        size=None,
        monthly_rent=None,
        is_rented=False,
        bedrooms=1,
        bathrooms=1.0,
        floor=2,
        tenant=None,
        created_at=now,
        updated_at=now
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.get_unit', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/units/{unit_id}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["tenant"] is None
        assert response_data["is_rented"] is False

# =============================================================================
# GET UNITS FOR PROPERTY TESTS
# =============================================================================

def test_get_units_for_property_success():
    """Test successful retrieval of all units for a property."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    # Create mock tenants
    tenant1 = TenantInfo(id=1, first_name="John", last_name="Doe", email="john@example.com")
    tenant2 = TenantInfo(id=2, first_name="Jane", last_name="Smith", email="jane@example.com")
    
    # Create mock units
    now = datetime.now(timezone.utc)
    units = [
        UnitResponse(
            id=1,
            property_id=property_id,
            name="Unit A",
            description="First unit",
            size=1000.0,
            monthly_rent=Decimal("1200.00"),
            is_rented=True,
            bedrooms=2,
            bathrooms=1.0,
            floor=1,
            tenant=tenant1,
            created_at=now,
            updated_at=now
        ),
        UnitResponse(
            id=2,
            property_id=property_id,
            name="Unit B",
            description="Second unit",
            size=1100.0,
            monthly_rent=Decimal("1300.00"),
            is_rented=True,
            bedrooms=3,
            bathrooms=2.0,
            floor=2,
            tenant=tenant2,
            created_at=now,
            updated_at=now
        ),
        UnitResponse(
            id=3,
            property_id=property_id,
            name="Unit C",
            description="Third unit",
            size=900.0,
            monthly_rent=None,
            is_rented=False,
            bedrooms=1,
            bathrooms=1.0,
            floor=3,
            tenant=None,
            created_at=now,
            updated_at=now
        )
    ]
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.get_units_for_property', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = units
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/properties/{property_id}/units",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 3
        
        # Check first unit
        assert response_data[0]["id"] == 1
        assert response_data[0]["name"] == "Unit A"
        assert response_data[0]["is_rented"] is True
        assert response_data[0]["tenant"]["first_name"] == "John"
        
        # Check second unit
        assert response_data[1]["id"] == 2
        assert response_data[1]["name"] == "Unit B"
        assert response_data[1]["is_rented"] is True
        assert response_data[1]["tenant"]["first_name"] == "Jane"
        
        # Check third unit (vacant)
        assert response_data[2]["id"] == 3
        assert response_data[2]["name"] == "Unit C"
        assert response_data[2]["is_rented"] is False
        assert response_data[2]["tenant"] is None
        
        # Verify service was called correctly with default pagination
        mock_get.assert_called_once_with(property_id, mock_session, fake_user, 0, 100)

def test_get_units_for_property_empty():
    """Test getting units for a property with no units."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to return empty list
    with patch('Backend.api.units.service.UnitService.get_units_for_property', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/properties/{property_id}/units",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json() == []

def test_get_units_for_property_not_found():
    """Test getting units for a property that doesn't exist."""
    # Arrange
    fake_user = create_test_user()
    property_id = 999
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.get_units_for_property', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = HTTPException(status_code=404, detail="Property not found")
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/properties/{property_id}/units",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Property not found"

def test_get_units_for_property_forbidden():
    """Test getting units for a property the user doesn't own."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.get_units_for_property', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = HTTPException(
            status_code=403, 
            detail="You don't have permission to view units for this property"
        )
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/properties/{property_id}/units",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 403
        assert response.json()["detail"] == "You don't have permission to view units for this property"

def test_get_units_unauthorized():
    """Test getting units without authentication."""
    # Arrange
    property_id = 1
    
    # Act
    client = TestClientWithHost(app)
    response = client.get(f"/api/properties/{property_id}/units")
    
    # Assert - Accept either 401 or 403 as both indicate lack of proper auth
    assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"

def test_get_unit_unauthorized():
    """Test getting a single unit without authentication."""
    # Arrange
    unit_id = 1
    
    # Act
    client = TestClientWithHost(app)
    response = client.get(f"/api/units/{unit_id}")
    
    # Assert - Accept either 401 or 403 as both indicate lack of proper auth
    assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"

def test_get_units_for_property_with_pagination():
    """Test getting units with custom pagination parameters."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    skip = 10
    limit = 50
    
    # Create mock units (we'll return empty list to simulate skip)
    units = []
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.get_units_for_property', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = units
        
        # Act
        client = TestClientWithHost(app)
        response = client.get(
            f"/api/properties/{property_id}/units?skip={skip}&limit={limit}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json() == []
        
        # Verify service was called with custom pagination
        mock_get.assert_called_once_with(property_id, mock_session, fake_user, skip, limit)