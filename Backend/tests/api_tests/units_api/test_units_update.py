"""
Unit tests for the units update service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.units.schemas import UnitResponse, UnitUpdate, TenantInfo
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
# UPDATE UNIT TESTS
# =============================================================================

def test_update_unit_success():
    """Test successful unit update with all fields."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    property_id = 1
    
    update_data = {
        "name": "Updated Unit A",
        "description": "Updated description",
        "size": 1300.0,
        "monthly_rent": "1600.00",
        "is_rented": True,
        "bedrooms": 3,
        "bathrooms": 2.0,
        "floor": 2,
        "tenant_id": 1
    }
    
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
        name="Updated Unit A",
        description="Updated description",
        size=1300.0,
        monthly_rent=Decimal("1600.00"),
        is_rented=True,
        bedrooms=3,
        bathrooms=2.0,
        floor=2,
        tenant=tenant_info,
        created_at=now,
        updated_at=now
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.update_unit', new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.put(
            f"/api/units/{unit_id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == unit_id
        assert response_data["name"] == "Updated Unit A"
        assert response_data["description"] == "Updated description"
        assert response_data["size"] == 1300.0
        assert response_data["monthly_rent"] == "1600.00"
        assert response_data["is_rented"] is True
        assert response_data["bedrooms"] == 3
        assert response_data["bathrooms"] == 2.0
        assert response_data["floor"] == 2
        assert response_data["tenant"]["id"] == 1
        
        # Verify service was called correctly
        mock_update.assert_called_once()
        args = mock_update.call_args[0]
        assert args[0] == unit_id
        assert isinstance(args[1], UnitUpdate)
        assert args[2] == mock_session
        assert args[3] == fake_user

def test_update_unit_partial():
    """Test partial unit update (only some fields)."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    property_id = 1
    
    update_data = {
        "monthly_rent": "1800.00",
        "is_rented": True
    }
    
    # Create mock response
    now = datetime.now(timezone.utc)
    mock_response = UnitResponse(
        id=unit_id,
        property_id=property_id,
        name="Unit A",  # Unchanged
        description="Original description",  # Unchanged
        size=1200.5,  # Unchanged
        monthly_rent=Decimal("1800.00"),  # Updated
        is_rented=True,  # Updated
        bedrooms=2,  # Unchanged
        bathrooms=1.5,  # Unchanged
        floor=1,  # Unchanged
        tenant=None,
        created_at=now,
        updated_at=now
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.update_unit', new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.put(
            f"/api/units/{unit_id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["monthly_rent"] == "1800.00"
        assert response_data["is_rented"] is True
        # Other fields remain unchanged
        assert response_data["name"] == "Unit A"
        assert response_data["description"] == "Original description"

def test_update_unit_assign_tenant():
    """Test updating unit to assign a tenant."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    property_id = 1
    tenant_id = 5
    
    update_data = {
        "tenant_id": tenant_id,
        "is_rented": True,
        "monthly_rent": "2000.00"
    }
    
    # Create mock tenant
    mock_tenant = create_mock_tenant(tenant_id=tenant_id)
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
        description="Nice unit",
        size=1200.5,
        monthly_rent=Decimal("2000.00"),
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
    with patch('Backend.api.units.service.UnitService.update_unit', new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.put(
            f"/api/units/{unit_id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["tenant"]["id"] == tenant_id
        assert response_data["is_rented"] is True
        assert response_data["monthly_rent"] == "2000.00"

def test_update_unit_remove_tenant():
    """Test updating unit to remove tenant (vacate)."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    property_id = 1
    
    update_data = {
        "tenant_id": None,
        "is_rented": False
    }
    
    # Create mock response
    now = datetime.now(timezone.utc)
    mock_response = UnitResponse(
        id=unit_id,
        property_id=property_id,
        name="Unit A",
        description="Nice unit",
        size=1200.5,
        monthly_rent=None,  # Cleared when vacated
        is_rented=False,
        bedrooms=2,
        bathrooms=1.5,
        floor=1,
        tenant=None,  # No tenant
        created_at=now,
        updated_at=now
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.update_unit', new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.put(
            f"/api/units/{unit_id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["tenant"] is None
        assert response_data["is_rented"] is False
        assert response_data["monthly_rent"] is None

def test_update_unit_not_found():
    """Test updating a unit that doesn't exist."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 999
    
    update_data = {
        "name": "Updated Name"
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.update_unit', new_callable=AsyncMock) as mock_update:
        mock_update.side_effect = HTTPException(status_code=404, detail="Unit not found")
        
        # Act
        client = TestClientWithHost(app)
        response = client.put(
            f"/api/units/{unit_id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Unit not found"

def test_update_unit_forbidden():
    """Test updating a unit the user doesn't have permission to update."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    update_data = {
        "name": "Updated Name"
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.update_unit', new_callable=AsyncMock) as mock_update:
        mock_update.side_effect = HTTPException(
            status_code=403, 
            detail="You don't have permission to access this unit"
        )
        
        # Act
        client = TestClientWithHost(app)
        response = client.put(
            f"/api/units/{unit_id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 403
        assert response.json()["detail"] == "You don't have permission to access this unit"

def test_update_unit_tenant_not_found():
    """Test updating unit with non-existent tenant ID."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    update_data = {
        "tenant_id": 999  # Non-existent tenant
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.update_unit', new_callable=AsyncMock) as mock_update:
        mock_update.side_effect = HTTPException(
            status_code=404, 
            detail="Tenant with ID 999 not found"
        )
        
        # Act
        client = TestClientWithHost(app)
        response = client.put(
            f"/api/units/{unit_id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Tenant with ID 999 not found"

def test_update_unit_no_data():
    """Test updating unit with no update data."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    update_data = {}  # Empty update
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.update_unit', new_callable=AsyncMock) as mock_update:
        mock_update.side_effect = HTTPException(
            status_code=400, 
            detail="No update data provided"
        )
        
        # Act
        client = TestClientWithHost(app)
        response = client.put(
            f"/api/units/{unit_id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "No update data provided"

def test_update_unit_unauthorized():
    """Test updating unit without authentication."""
    # Arrange
    unit_id = 1
    update_data = {"name": "Updated Name"}
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/units/{unit_id}",
        json=update_data
        # No authorization header
    )
    
    # Assert - Accept either 401 or 403 as both indicate lack of proper auth
    assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"

def test_update_unit_admin_can_update_any():
    """Test that admin users can update any unit."""
    # Arrange
    fake_admin = create_test_user(is_admin=True)
    unit_id = 1
    property_id = 1
    
    update_data = {
        "name": "Admin Updated Unit"
    }
    
    # Create mock response
    now = datetime.now(timezone.utc)
    mock_response = UnitResponse(
        id=unit_id,
        property_id=property_id,
        name="Admin Updated Unit",
        description="Nice unit",
        size=1200.5,
        monthly_rent=Decimal("1500.00"),
        is_rented=False,
        bedrooms=2,
        bathrooms=1.5,
        floor=1,
        tenant=None,
        created_at=now,
        updated_at=now
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_admin
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.update_unit', new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.put(
            f"/api/units/{unit_id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == "Admin Updated Unit"

def test_update_unit_with_invalid_rent():
    """Test updating unit with negative rent fails validation."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    update_data = {
        "monthly_rent": "-500.00"  # Negative rent should fail
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/units/{unit_id}",
        json=update_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422  # Validation error
    assert "Value error, Monthly rent cannot be negative" in str(response.json())

def test_update_unit_with_invalid_size():
    """Test updating unit with invalid size fails validation."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    update_data = {
        "size": 0  # Zero size should fail
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/units/{unit_id}",
        json=update_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422  # Validation error
    assert "Value error, Size must be greater than 0" in str(response.json())

def test_update_unit_with_invalid_bedrooms():
    """Test updating unit with negative bedrooms fails validation."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    update_data = {
        "bedrooms": -1  # Negative bedrooms should fail
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.put(
        f"/api/units/{unit_id}",
        json=update_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422  # Validation error
    assert "Value error, Bedrooms cannot be negative" in str(response.json())