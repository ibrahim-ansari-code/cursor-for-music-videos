"""
Unit tests for the units creation service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.units.schemas import UnitCreateResponse, UnitCreate
from Backend.models.property import Property, PropertyType
from Backend.models.units import PropertyUnit
from Backend.models.user import User
from Backend.models.enums import PropertyStatus
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

def create_mock_property(property_id=1, **kwargs):
    """Helper function to create a mock property with all required attributes."""
    now = datetime.now(timezone.utc)
    mock_property = MagicMock(spec=Property)
    mock_property.id = property_id
    mock_property.name = kwargs.get('name', 'Test Property')
    mock_property.address = kwargs.get('address', '123 Test St')
    mock_property.city = kwargs.get('city', 'Test City')
    mock_property.province = kwargs.get('province', 'Test Province')
    mock_property.postal_code = kwargs.get('postal_code', '12345')
    mock_property.property_type = kwargs.get('property_type', PropertyType.RESIDENTIAL)
    mock_property.description = kwargs.get('description', 'A test property')
    mock_property.year_built = kwargs.get('year_built', 2020)
    mock_property.status = kwargs.get('status', PropertyStatus.ACTIVE)
    mock_property.user_id = kwargs.get('user_id', uuid4())
    mock_property.created_at = kwargs.get('created_at', now)
    mock_property.updated_at = kwargs.get('updated_at', now)
    mock_property.owner = kwargs.get('owner', None)
    mock_property.units = kwargs.get('units', [])
    return mock_property

def create_mock_unit(unit_id=1, **kwargs):
    """Helper function to create a mock property unit."""
    now = datetime.now(timezone.utc)
    mock_unit = MagicMock(spec=PropertyUnit)
    mock_unit.id = unit_id
    mock_unit.name = kwargs.get('name', 'Unit 1')
    mock_unit.floor = kwargs.get('floor', 1)
    mock_unit.is_rented = kwargs.get('is_rented', False)
    mock_unit.tenant = kwargs.get('tenant', None)
    mock_unit.tenant_id = kwargs.get('tenant_id', None)
    mock_unit.property_id = kwargs.get('property_id', 1)
    mock_unit.description = kwargs.get('description', '')
    mock_unit.size = kwargs.get('size', None)
    mock_unit.monthly_rent = kwargs.get('monthly_rent', None)
    mock_unit.bedrooms = kwargs.get('bedrooms', None)
    mock_unit.bathrooms = kwargs.get('bathrooms', None)
    mock_unit.created_at = kwargs.get('created_at', now)
    mock_unit.updated_at = kwargs.get('updated_at', now)
    return mock_unit

# =============================================================================
# CREATE UNIT TESTS
# =============================================================================

def test_create_unit_success():
    """Test successful unit creation."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    unit_data = {
        "name": "Unit A",
        "description": "A nice unit",
        "size": 1200.5,
        "monthly_rent": "1500.00",
        "is_rented": False,
        "bedrooms": 2,
        "bathrooms": 1.5,
        "floor": 1
    }
    
    # Mock the created unit
    created_unit = create_mock_unit(
        unit_id=1,
        property_id=property_id,
        name="Unit A",
        description="A nice unit",
        size=1200.5,
        monthly_rent=Decimal("1500.00"),
        is_rented=False,
        bedrooms=2,
        bathrooms=1.5,
        floor=1
    )
    
    mock_response = UnitCreateResponse(
        id=1,
        property_id=property_id,
        name="Unit A",
        description="A nice unit",
        size=1200.5,
        monthly_rent=Decimal("1500.00"),
        is_rented=False,
        bedrooms=2,
        bathrooms=1.5,
        floor=1,
        created_at=created_unit.created_at,
        updated_at=created_unit.updated_at
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.create_unit', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            f"/api/properties/{property_id}/units",
            json=unit_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["id"] == 1
        assert response_data["property_id"] == property_id
        assert response_data["name"] == "Unit A"
        assert response_data["description"] == "A nice unit"
        assert response_data["size"] == 1200.5
        assert response_data["monthly_rent"] == "1500.00"
        assert response_data["is_rented"] is False
        assert response_data["bedrooms"] == 2
        assert response_data["bathrooms"] == 1.5
        assert response_data["floor"] == 1
        
        # Verify service was called correctly
        mock_create.assert_called_once()
        args = mock_create.call_args[0]
        assert args[0] == property_id
        assert isinstance(args[1], UnitCreate)
        assert args[2] == mock_session
        assert args[3] == fake_user

def test_create_unit_property_not_found():
    """Test unit creation when property does not exist."""
    # Arrange
    fake_user = create_test_user()
    property_id = 999
    
    unit_data = {
        "name": "Unit A",
        "is_rented": False
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.create_unit', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = HTTPException(status_code=404, detail="Property not found")
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            f"/api/properties/{property_id}/units",
            json=unit_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Property not found"

def test_create_unit_forbidden():
    """Test unit creation when user doesn't own the property."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    unit_data = {
        "name": "Unit A",
        "is_rented": False
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.create_unit', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = HTTPException(
            status_code=403, 
            detail="You don't have permission to add units to this property"
        )
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            f"/api/properties/{property_id}/units",
            json=unit_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 403
        assert response.json()["detail"] == "You don't have permission to add units to this property"

def test_create_unit_minimal_data():
    """Test unit creation with minimal required data."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    unit_data = {
        "name": "Unit B",
        "is_rented": False
    }
    
    # Mock the created unit
    created_unit = create_mock_unit(
        unit_id=2,
        property_id=property_id,
        name="Unit B",
        is_rented=False
    )
    
    mock_response = UnitCreateResponse(
        id=2,
        property_id=property_id,
        name="Unit B",
        description=None,
        size=None,
        monthly_rent=None,
        is_rented=False,
        bedrooms=None,
        bathrooms=None,
        floor=None,
        created_at=created_unit.created_at,
        updated_at=created_unit.updated_at
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.create_unit', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            f"/api/properties/{property_id}/units",
            json=unit_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["id"] == 2
        assert response_data["name"] == "Unit B"
        assert response_data["description"] is None
        assert response_data["size"] is None
        assert response_data["monthly_rent"] is None

def test_create_unit_invalid_data():
    """Test unit creation with invalid data."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    unit_data = {
        "name": "",  # Empty name should fail validation
        "is_rented": False
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/properties/{property_id}/units",
        json=unit_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422  # Validation error

def test_create_unit_unauthorized():
    """Test unit creation without authentication."""
    # Arrange
    property_id = 1
    unit_data = {
        "name": "Unit A",
        "is_rented": False
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/properties/{property_id}/units",
        json=unit_data
        # No authorization header
    )
    
    # Assert - Accept either 401 or 403 as both indicate lack of proper auth
    # 401: No auth header provided (authentication required)
    # 403: Invalid/expired token (authorization failed)
    assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"

def test_create_unit_admin_can_create_for_any_property():
    """Test that admin users can create units for any property."""
    # Arrange
    fake_admin = create_test_user(is_admin=True)
    property_id = 1
    
    unit_data = {
        "name": "Admin Unit",
        "is_rented": False
    }
    
    # Mock the created unit
    created_unit = create_mock_unit(
        unit_id=3,
        property_id=property_id,
        name="Admin Unit",
        is_rented=False
    )
    
    mock_response = UnitCreateResponse(
        id=3,
        property_id=property_id,
        name="Admin Unit",
        description=None,
        size=None,
        monthly_rent=None,
        is_rented=False,
        bedrooms=None,
        bathrooms=None,
        floor=None,
        created_at=created_unit.created_at,
        updated_at=created_unit.updated_at
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_admin
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.create_unit', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            f"/api/properties/{property_id}/units",
            json=unit_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["id"] == 3
        assert response_data["name"] == "Admin Unit"

# =============================================================================
# BULK CREATE UNIT TESTS
# =============================================================================

def test_create_units_bulk_success():
    """Test successful bulk unit creation."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    bulk_data = {
        "units": [
            {
                "name": "Unit 101",
                "description": "First floor unit",
                "size": 1000.0,
                "monthly_rent": "1200.00",
                "is_rented": False,
                "bedrooms": 2,
                "bathrooms": 1.0,
                "floor": 1
            },
            {
                "name": "Unit 201",
                "description": "Second floor unit",
                "size": 1100.0,
                "monthly_rent": "1300.00",
                "is_rented": False,
                "bedrooms": 2,
                "bathrooms": 1.5,
                "floor": 2
            },
            {
                "name": "Unit 301",
                "description": "Third floor unit",
                "size": 1200.0,
                "monthly_rent": "1400.00",
                "is_rented": False,
                "bedrooms": 3,
                "bathrooms": 2.0,
                "floor": 3
            }
        ]
    }
    
    # Mock the created units
    from Backend.api.units.schemas import BulkUnitCreateResponse
    mock_response = BulkUnitCreateResponse(
        created=[
            UnitCreateResponse(
                id=1,
                property_id=property_id,
                name="Unit 101",
                description="First floor unit",
                size=1000.0,
                monthly_rent=Decimal("1200.00"),
                is_rented=False,
                bedrooms=2,
                bathrooms=1.0,
                floor=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            UnitCreateResponse(
                id=2,
                property_id=property_id,
                name="Unit 201",
                description="Second floor unit",
                size=1100.0,
                monthly_rent=Decimal("1300.00"),
                is_rented=False,
                bedrooms=2,
                bathrooms=1.5,
                floor=2,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            UnitCreateResponse(
                id=3,
                property_id=property_id,
                name="Unit 301",
                description="Third floor unit",
                size=1200.0,
                monthly_rent=Decimal("1400.00"),
                is_rented=False,
                bedrooms=3,
                bathrooms=2.0,
                floor=3,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ],
        failed=[]
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.create_units_bulk', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            f"/api/properties/{property_id}/units/bulk",
            json=bulk_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert len(response_data["created"]) == 3
        assert len(response_data["failed"]) == 0
        
        # Verify first unit
        assert response_data["created"][0]["name"] == "Unit 101"
        assert response_data["created"][0]["monthly_rent"] == "1200.00"
        
        # Verify second unit
        assert response_data["created"][1]["name"] == "Unit 201"
        assert response_data["created"][1]["monthly_rent"] == "1300.00"
        
        # Verify third unit
        assert response_data["created"][2]["name"] == "Unit 301"
        assert response_data["created"][2]["monthly_rent"] == "1400.00"

def test_create_units_bulk_partial_success():
    """Test bulk unit creation with some failures at service level."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    # All units pass basic validation but some fail at service level
    bulk_data = {
        "units": [
            {
                "name": "Unit A",
                "is_rented": False
            },
            {
                "name": "Unit B",  # Valid name
                "is_rented": False
            },
            {
                "name": "Unit C",
                "monthly_rent": "100.00",  # Valid rent
                "is_rented": False
            }
        ]
    }
    
    # Mock response with 1 success and 2 failures
    from Backend.api.units.schemas import BulkUnitCreateResponse
    mock_response = BulkUnitCreateResponse(
        created=[
            UnitCreateResponse(
                id=1,
                property_id=property_id,
                name="Unit A",
                description=None,
                size=None,
                monthly_rent=None,
                is_rented=False,
                bedrooms=None,
                bathrooms=None,
                floor=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ],
        failed=[
            {
                "index": 1,
                "data": {"name": "Unit B", "is_rented": False},
                "error": "Database error: duplicate unit name"
            },
            {
                "index": 2,
                "data": {"name": "Unit C", "monthly_rent": "100.00", "is_rented": False},
                "error": "Database error: unit limit exceeded for property"
            }
        ]
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.create_units_bulk', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            f"/api/properties/{property_id}/units/bulk",
            json=bulk_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert len(response_data["created"]) == 1
        assert len(response_data["failed"]) == 2
        
        # Verify successful unit
        assert response_data["created"][0]["name"] == "Unit A"
        
        # Verify failures
        assert response_data["failed"][0]["index"] == 1
        assert "duplicate" in response_data["failed"][0]["error"]
        assert response_data["failed"][1]["index"] == 2
        assert "limit exceeded" in response_data["failed"][1]["error"]

def test_create_units_bulk_empty_list():
    """Test bulk unit creation with empty unit list."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    bulk_data = {
        "units": []  # Empty list should fail validation
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/properties/{property_id}/units/bulk",
        json=bulk_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422  # Validation error
    response_data = response.json()
    # Verify the specific validation error message for empty list
    assert "at least 1 item" in str(response_data) or "ensure this value has at least 1 item" in str(response_data)

def test_create_units_bulk_too_many_units():
    """Test bulk unit creation with more than 100 units."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    # Create 101 units (exceeds max limit of 100)
    bulk_data = {
        "units": [{"name": f"Unit {i}", "is_rented": False} for i in range(101)]
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/properties/{property_id}/units/bulk",
        json=bulk_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422  # Validation error

def test_create_units_bulk_unauthorized():
    """Test bulk unit creation without authentication."""
    # Arrange
    property_id = 1
    bulk_data = {
        "units": [{"name": "Unit A", "is_rented": False}]
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/properties/{property_id}/units/bulk",
        json=bulk_data
        # No authorization header
    )
    
    # Assert
    assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"

def test_create_units_bulk_validation_errors():
    """Test bulk unit creation with validation errors."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    bulk_data = {
        "units": [
            {
                "name": "",  # Empty name - validation error
                "is_rented": False
            }
        ]
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/properties/{property_id}/units/bulk",
        json=bulk_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422  # Validation error at API level

def test_create_unit_with_negative_rent():
    """Test creating a unit with negative rent fails validation."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    unit_data = {
        "name": "Unit A",
        "monthly_rent": "-500.00",  # Negative rent
        "is_rented": False
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/properties/{property_id}/units",
        json=unit_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422
    assert "Monthly rent cannot be negative" in str(response.json())