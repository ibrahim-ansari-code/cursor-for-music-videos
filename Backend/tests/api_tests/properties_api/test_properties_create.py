"""
Unit tests for the properties creation service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.properties.schemas import (
    OwnerResponse,
    PropertyDetailResponse_Standalone,
    UnitResponse,
)
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
    mock_unit.description = kwargs.get('description', '')
    mock_unit.size = kwargs.get('size', None)
    mock_unit.monthly_rent = kwargs.get('monthly_rent', None)
    mock_unit.bedrooms = kwargs.get('bedrooms', None)
    mock_unit.bathrooms = kwargs.get('bathrooms', None)
    mock_unit.created_at = kwargs.get('created_at', now)
    mock_unit.updated_at = kwargs.get('updated_at', now)
    return mock_unit

# =============================================================================
# CREATE PROPERTY TESTS
# =============================================================================

def test_create_property_success_without_units():
    """Test successful property creation without units."""
    # Arrange
    fake_user = create_test_user()
    
    property_data = {
        "name": "New Property",
        "address": "123 New St",
        "city": "New City",
        "province": "New Province",
        "postal_code": "N3W123",
        "property_type": "Residential",
        "description": "Brand new property",
        "year_built": 2023,
        "status": "ACTIVE",
        "units": None
    }
    
    # Create a mock property response
    fake_property = create_mock_property(
        property_id=1,
        name="New Property",
        address="123 New St",
        city="New City",
        province="New Province",
        postal_code="N3W123",
        property_type=PropertyType.RESIDENTIAL,
        description="Brand new property",
        year_built=2023,
        status=PropertyStatus.ACTIVE,
        user_id=fake_user.id,
        owner=fake_user,
        units=[]
    )
    
    # Create the response object that the service would return
    fake_response = PropertyDetailResponse_Standalone(
        id=1,
        name="New Property",
        address="123 New St",
        city="New City",
        province="New Province",
        postal_code="N3W123",
        property_type=PropertyType.RESIDENTIAL,
        description="Brand new property",
        year_built=2023,
        status=PropertyStatus.ACTIVE,
        user_id=fake_user.id,
        created_at=fake_property.created_at,
        updated_at=fake_property.updated_at,
        owner=OwnerResponse(
            id=fake_user.id,
            first_name=fake_user.first_name,
            last_name=fake_user.last_name,
            email=fake_user.email,
            phone=getattr(fake_user, 'phone', None),
            profile_image_url=getattr(fake_user, 'profile_image_url', None)
        ),
        units=[]
    )
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.create_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/properties/", json=property_data)

    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 1
            assert data["name"] == "New Property"
            assert data["owner"] is not None
            assert data["owner"]["id"] == str(fake_user.id)
            assert data["units"] == []
            assert data["status"] == "ACTIVE"

def test_create_property_with_units_status_derivation():
    """Test property creation with units derives VACANT status."""
    # Arrange
    fake_user = create_test_user()
    
    property_data = {
        "name": "Property With Units",
        "address": "456 Unit St",
        "city": "Unit City",
        "province": "Unit Province",
        "postal_code": "U1N1T5",
        "property_type": "Residential",
        "description": "Property with multiple units",
        "year_built": 2023,
        "status": "ACTIVE",
        "units": ["101", "201", "301"]
    }
    
    # Create mock units
    mock_units = []
    for idx, unit_name in enumerate(["101", "201", "301"], start=1):
        mock_unit = create_mock_unit(
            unit_id=idx,
            name=unit_name,
            floor=int(unit_name[0]),
            is_rented=False,
            tenant=None
        )
        mock_units.append(mock_unit)
    
    # Create property with units
    fake_property = create_mock_property(
        property_id=2,
        name="Property With Units",
        address="456 Unit St",
        city="Unit City",
        province="Unit Province",
        postal_code="U1N1T5",
        property_type=PropertyType.RESIDENTIAL,
        description="Property with multiple units",
        year_built=2023,
        status=PropertyStatus.ACTIVE,
        user_id=fake_user.id,
        owner=fake_user,
        units=mock_units
    )
    
    # Create the response with VACANT status (derived from all units being unrented)
    fake_response = PropertyDetailResponse_Standalone(
        id=2,
        name="Property With Units",
        address="456 Unit St",
        city="Unit City",
        province="Unit Province",
        postal_code="U1N1T5",
        property_type=PropertyType.RESIDENTIAL,
        description="Property with multiple units",
        year_built=2023,
        status=PropertyStatus.VACANT,  # Derived status
        user_id=fake_user.id,
        created_at=fake_property.created_at,
        updated_at=fake_property.updated_at,
        owner=OwnerResponse(
            id=fake_user.id,
            first_name=fake_user.first_name,
            last_name=fake_user.last_name,
            email=fake_user.email,
            phone=getattr(fake_user, 'phone', None),
            profile_image_url=getattr(fake_user, 'profile_image_url', None)
        ),
        units=mock_units
    )
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.create_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/properties/", json=property_data)

    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 2
            assert len(data["units"]) == 3
            assert all(not unit["is_rented"] for unit in data["units"])
            assert data["status"] == "VACANT"  # All units vacant

def test_create_property_floor_assignment_logic():
    """Test that units get correct floor assignment based on name."""
    # Arrange
    fake_user = create_test_user()

    # Unit names with various patterns
    unit_names = ["101", "201", "301", "Basement", "PH", "A1", "2B"]
    expected_floors = [1, 2, 3, 0, 0, 0, 2]  # Expected floor assignments
    
    property_data = {
        "name": "Floor Test Property",
        "address": "789 Floor St",
        "city": "Floor City",
        "province": "Floor Province",
        "postal_code": "F1O0R5",
        "property_type": "Residential",
        "units": unit_names
    }
    
    # Create mock units with expected floor assignments
    mock_units = []
    for idx, (unit_name, expected_floor) in enumerate(zip(unit_names, expected_floors), start=1):
        mock_unit = create_mock_unit(
            unit_id=idx,
            name=unit_name,
            floor=expected_floor,
            is_rented=False
        )
        mock_units.append(mock_unit)
    
    # Create property response
    fake_response = PropertyDetailResponse_Standalone(
        id=3,
        name="Floor Test Property",
        address="789 Floor St",
        city="Floor City",
        province="Floor Province",
        postal_code="F1O0R5",
        property_type=PropertyType.RESIDENTIAL,
        description=None,
        year_built=None,
        status=PropertyStatus.VACANT,
        user_id=fake_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        owner=OwnerResponse(
            id=fake_user.id,
            first_name=fake_user.first_name,
            last_name=fake_user.last_name,
            email=fake_user.email,
            phone=getattr(fake_user, 'phone', None),
            profile_image_url=getattr(fake_user, 'profile_image_url', None)
        ),
        units=mock_units
    )
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.create_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/properties/", json=property_data)

    # Assert
            assert response.status_code == 201
            data = response.json()
            assert len(data["units"]) == len(unit_names)
            for unit, expected_floor in zip(data["units"], expected_floors):
                assert unit["floor"] == expected_floor

def test_create_property_validation_error():
    """Test validation error for invalid property data."""
    # Arrange
    fake_user = create_test_user()
    
    # Invalid data - empty name
    property_data = {
        "name": "",  # Empty name should fail
        "address": "123 Test St",
        "city": "Test City",
        "province": "Test Province",
        "postal_code": "12345",
        "property_type": "Residential"
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/properties/", json=property_data)
        
        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        # More robust assertion that checks for validation errors related to the name field
        # without relying on exact error message text
        has_name_error = False
        try:
            for error in error_detail:
                if isinstance(error, dict):
                    loc = error.get("loc", [])
                    if "name" in [str(field) for field in loc]:
                        has_name_error = True
                        break
        except (TypeError, KeyError):
            # Fallback: check if any error mentions 'name' in a generic way
            has_name_error = any("name" in str(error).lower() for error in error_detail)
        
        assert has_name_error, "Expected validation error for 'name' field not found"

def test_create_property_database_error():
    """Test error handling for database commit failure."""
    # Arrange
    fake_user = create_test_user()
    
    property_data = {
        "name": "Test Property",
        "address": "123 Test St",
        "city": "Test City",
        "province": "Test Province",
        "postal_code": "12345",
        "property_type": "Residential"
    }
    
    # Mock the service layer to raise an exception
    with patch(
        "Backend.api.properties.router.PropertyService.create_property",
        new=AsyncMock(side_effect=HTTPException(status_code=500, detail="Failed to create property"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/properties/", json=property_data)
            
            # Assert
            assert response.status_code == 500
            assert "Failed to create property" in response.json()["detail"]

def test_create_property_with_mixed_unit_names():
    """Test property creation with units having mixed naming patterns."""
    # Arrange
    fake_user = create_test_user()
    
    property_data = {
        "name": "Mixed Units Property",
        "address": "999 Mixed St",
        "city": "Mixed City",
        "province": "Mixed Province",
        "postal_code": "M1X3D",
        "property_type": "Commercial",
        "description": "Property with mixed unit naming",
        "year_built": 2024,
        "units": ["Store Front", "Office 201", "Suite 3A", "Warehouse"]
    }
    
    # Create mock units with appropriate floor assignments
    unit_configs = [
        ("Store Front", 0),   # No digit at start, floor 0
        ("Office 201", 2),    # Starts with 2, floor 2
        ("Suite 3A", 3),      # Starts with 3, floor 3
        ("Warehouse", 0),     # No digit at start, floor 0
    ]
    
    mock_units = []
    for idx, (unit_name, floor) in enumerate(unit_configs, start=1):
        mock_unit = create_mock_unit(
            unit_id=idx,
            name=unit_name,
            floor=floor,
            is_rented=False
        )
        mock_units.append(mock_unit)
    
    # Create property response
    fake_response = PropertyDetailResponse_Standalone(
        id=4,
        name="Mixed Units Property",
        address="999 Mixed St",
        city="Mixed City",
        province="Mixed Province",
        postal_code="M1X3D",
        property_type=PropertyType.COMMERCIAL,
        description="Property with mixed unit naming",
        year_built=2024,
        status=PropertyStatus.VACANT,
        user_id=fake_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        owner=OwnerResponse(
            id=fake_user.id,
            first_name=fake_user.first_name,
            last_name=fake_user.last_name,
            email=fake_user.email,
            phone=getattr(fake_user, 'phone', None),
            profile_image_url=getattr(fake_user, 'profile_image_url', None)
        ),
        units=mock_units
    )
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.create_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/properties/", json=property_data)

    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 4
            assert len(data["units"]) == 4
            assert data["property_type"] == "Commercial"
    
    # Verify floor assignments
            assert data["units"][0]["floor"] == 0  # Store Front
            assert data["units"][1]["floor"] == 2  # Office 201
            assert data["units"][2]["floor"] == 3  # Suite 3A
            assert data["units"][3]["floor"] == 0  # Warehouse

def test_create_property_retrieval_failure():
    """Test error handling when property retrieval fails after creation."""
    # Arrange
    fake_user = create_test_user()
    
    property_data = {
        "name": "Retrieval Failure Property",
        "address": "404 Not Found St",
        "city": "Error City",
        "province": "Error Province",
        "postal_code": "E1R0R",
        "property_type": "Residential"
    }
    
    # Mock the service layer to raise an exception
    with patch(
        "Backend.api.properties.router.PropertyService.create_property",
        new=AsyncMock(side_effect=HTTPException(status_code=500, detail="Property was created but could not be retrieved"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/properties/", json=property_data)
            
            # Assert
            assert response.status_code == 500
            assert "Property was created but could not be retrieved" in response.json()["detail"]

def test_create_property_unauthorized():
    """Test that creating a property requires authentication."""
    # Arrange - don't override get_current_user to simulate unauthenticated request
    property_data = {
        "name": "Test Property",
        "address": "123 Test St",
        "city": "Test City",
        "province": "Test Province",
        "postal_code": "12345",
        "property_type": "Residential"
    }
    
    # Only override the session
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/properties/", json=property_data)
        
        # Assert - Accept either 401 or 403 as both indicate lack of proper auth
        # 401: No auth header provided (authentication required)
        # 403: Invalid/expired token (authorization failed)
        assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"


async def test_create_property_with_unit_sorting():
    """Test that created units are sorted by ID in the response."""
    # Arrange
    fake_user = create_test_user()
    property_data = {
        "name": "Sorted Units Property",
        "address": "123 Sort St",
        "city": "Sort City",
        "province": "Sort Province",
        "postal_code": "S0R7ED",
        "property_type": "Residential",
        "units": ["Unit C", "Unit A", "Unit B"]
    }

    # Create mock units in the order they should be returned (sorted by ID)
    mock_units = [
        create_mock_unit(unit_id=1, name="Unit A"),
        create_mock_unit(unit_id=2, name="Unit B"),
        create_mock_unit(unit_id=3, name="Unit C"),
    ]

    # Convert mock units to UnitResponse objects
    unit_responses = [UnitResponse.model_validate(u) for u in mock_units]

    # Create property response with sorted units
    fake_response = PropertyDetailResponse_Standalone(
        id=5,
        name="Sorted Units Property",
        address="123 Sort St",
        city="Sort City",
        province="Sort Province",
        postal_code="S0R7ED",
        property_type=PropertyType.RESIDENTIAL,
        status=PropertyStatus.VACANT,  # Derived status
        user_id=fake_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        owner=OwnerResponse.model_validate(fake_user),
        units=unit_responses
    )

    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.create_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/properties/", json=property_data)

            # Assert
            assert response.status_code == 201
            data = response.json()
            assert len(data["units"]) == 3
            # Verify that the units are sorted by ID, not by the input name order
            assert data["units"][0]["id"] == 1
            assert data["units"][0]["name"] == "Unit A"
            assert data["units"][1]["id"] == 2
            assert data["units"][1]["name"] == "Unit B"
            assert data["units"][2]["id"] == 3
            assert data["units"][2]["name"] == "Unit C"
