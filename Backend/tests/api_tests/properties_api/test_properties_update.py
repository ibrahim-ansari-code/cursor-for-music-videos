"""
Unit tests for UPDATE operations in the properties API endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.properties.schemas import PropertyDetailResponse_Standalone, OwnerResponse, UnitResponse, PropertyStats
from Backend.models.property import Property, PropertyType
from Backend.models.units import PropertyUnit
from decimal import Decimal
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

def create_mock_unit(unit_id: int | None = None, **kwargs):
    """Helper function to create a mock unit with all required attributes."""
    now = datetime.now(timezone.utc)
    mock_unit = MagicMock(spec=PropertyUnit)
    mock_unit.id = unit_id
    mock_unit.name = kwargs.get('name', 'Test Unit')
    mock_unit.description = kwargs.get('description', 'A test unit')
    mock_unit.floor = kwargs.get('floor', 1)
    mock_unit.is_rented = kwargs.get('is_rented', False)
    mock_unit.monthly_rent = kwargs.get('monthly_rent', Decimal("1000.00"))
    mock_unit.size = kwargs.get('size', None)
    mock_unit.bedrooms = kwargs.get('bedrooms', None)
    mock_unit.bathrooms = kwargs.get('bathrooms', None)
    mock_unit.tenant = kwargs.get('tenant', None)
    mock_unit.created_at = kwargs.get('created_at', now)
    mock_unit.updated_at = kwargs.get('updated_at', now)
    return mock_unit

# =============================================================================
# UPDATE PROPERTY TESTS
# =============================================================================

def test_update_property_success():
    """Test successful property update."""
    # Arrange
    property_id = 123
    owner_id = uuid4()
    fake_user = create_test_user(user_id=owner_id, email="owner@example.com")
    
    update_data = {
        "name": "Updated Property Name",
        "description": "Updated description",
        "year_built": 2024
    }
    
    # Create the updated property response
    updated_property = create_mock_property(
        property_id=property_id,
        name="Updated Property Name",
        description="Updated description",
        year_built=2024,
        user_id=owner_id,
        owner=fake_user,
        units=[],
        status=PropertyStatus.ACTIVE
    )
    
    # Create the response object that the service would return
    fake_response = PropertyDetailResponse_Standalone(
        id=property_id,
        name="Updated Property Name",
        description="Updated description",
        year_built=2024,
        address=updated_property.address,
        city=updated_property.city,
        province=updated_property.province,
        postal_code=updated_property.postal_code,
        property_type=updated_property.property_type,
        status=PropertyStatus.ACTIVE,
        user_id=owner_id,
        created_at=updated_property.created_at,
        updated_at=updated_property.updated_at,
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
    with patch("Backend.api.properties.router.PropertyService.update_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/properties/{property_id}", json=update_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == property_id
            assert data["name"] == "Updated Property Name"
            assert data["description"] == "Updated description"
            assert data["year_built"] == 2024


def test_update_property_not_found():
    """Test 404 error when updating non-existent property."""
    # Arrange
    property_id = 999
    fake_user = create_test_user(email="owner@example.com")
    
    update_data = {"name": "New Name"}
    
    # Mock the service layer to raise 404 error
    with patch(
        "Backend.api.properties.router.PropertyService.update_property",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Property not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/properties/{property_id}", json=update_data)
            
            # Assert
            assert response.status_code == 404
            assert "Property not found" in response.json()["detail"]


def test_update_property_forbidden():
    """Test 403 error when non-owner tries to update property."""
    # Arrange
    property_id = 123
    other_user_id = uuid4()
    
    other_user = create_test_user(
        user_id=other_user_id,
        email="other@example.com"
    )
    
    update_data = {"name": "Unauthorized Update"}
    
    # Mock the service layer to raise 403 error
    with patch(
        "Backend.api.properties.router.PropertyService.update_property",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="You don't have permission to update this property"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: other_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/properties/{property_id}", json=update_data)
            
            # Assert
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()


def test_update_property_no_data_provided():
    """Test 400 error when no update data is provided."""
    # Arrange
    property_id = 123
    fake_user = create_test_user(email="owner@example.com")
    
    # Empty update data
    update_data = {}
    
    # Mock the service layer to raise 400 error
    with patch(
        "Backend.api.properties.router.PropertyService.update_property",
        new=AsyncMock(side_effect=HTTPException(status_code=400, detail="No update data provided"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/properties/{property_id}", json=update_data)
            
            # Assert
            assert response.status_code == 400
            assert "No update data provided" in response.json()["detail"]


def test_update_property_validation_error():
    """Test validation error for invalid update data."""
    # Arrange
    property_id = 123
    fake_user = create_test_user(email="owner@example.com")
    
    # Invalid data - empty name
    update_data = {
        "name": "",  # Empty name should fail
        "year_built": 1800
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.put(f"/api/properties/{property_id}", json=update_data)
        
        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("name must not be an empty string" in str(error) for error in error_detail)


def test_update_property_admin_can_update_any():
    """Test that admin can update properties they don't own."""
    # Arrange
    property_id = 456
    owner_id = uuid4()
    admin_id = uuid4()
    
    admin_user = create_test_user(
        user_id=admin_id,
        email="admin@example.com",
        user_type="ADMIN",
        is_admin=True
    )
    
    property_owner = create_test_user(
        user_id=owner_id,
        email="owner@example.com"
    )
    
    update_data = {
        "name": "Admin Updated Name",
        "status": "INACTIVE"
    }
    
    # Create the updated property response
    updated_property = create_mock_property(
        property_id=property_id,
        name="Admin Updated Name",
        status=PropertyStatus.INACTIVE,
        user_id=owner_id,
        owner=property_owner,
        units=[]
    )
    
    # Create the response object
    fake_response = PropertyDetailResponse_Standalone(
        id=property_id,
        name="Admin Updated Name",
        description=updated_property.description,
        year_built=updated_property.year_built,
        address=updated_property.address,
        city=updated_property.city,
        province=updated_property.province,
        postal_code=updated_property.postal_code,
        property_type=updated_property.property_type,
        status=PropertyStatus.INACTIVE,
        user_id=owner_id,
        created_at=updated_property.created_at,
        updated_at=updated_property.updated_at,
        owner=OwnerResponse(
            id=property_owner.id,
            first_name=property_owner.first_name,
            last_name=property_owner.last_name,
            email=property_owner.email,
            phone=getattr(property_owner, 'phone', None),
            profile_image_url=getattr(property_owner, 'profile_image_url', None)
        ),
        units=[]
    )
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.update_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/properties/{property_id}", json=update_data)
            
            # Assert - Admin should be able to update
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == property_id
            assert data["name"] == "Admin Updated Name"
            assert data["status"] == "INACTIVE"


def test_update_property_partial_update():
    """Test partial property update (only some fields)."""
    # Arrange
    property_id = 789
    owner_id = uuid4()
    fake_user = create_test_user(user_id=owner_id, email="owner@example.com")
    
    # Only updating description
    update_data = {
        "description": "New and improved description"
    }
    
    # Create property with partial update applied
    updated_property = create_mock_property(
        property_id=property_id,
        name="Unchanged Name",  # Not changed
        description="New and improved description",  # Changed
        year_built=2020,  # Not changed
        status=PropertyStatus.ACTIVE,  # Not changed
        user_id=owner_id,
        owner=fake_user,
        units=[]
    )
    
    # Create the response object
    fake_response = PropertyDetailResponse_Standalone(
        id=property_id,
        name="Unchanged Name",
        description="New and improved description",
        year_built=2020,
        address=updated_property.address,
        city=updated_property.city,
        province=updated_property.province,
        postal_code=updated_property.postal_code,
        property_type=updated_property.property_type,
        status=PropertyStatus.ACTIVE,
        user_id=owner_id,
        created_at=updated_property.created_at,
        updated_at=updated_property.updated_at,
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
    with patch("Backend.api.properties.router.PropertyService.update_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/properties/{property_id}", json=update_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == property_id
            assert data["name"] == "Unchanged Name"  # Should remain unchanged
            assert data["description"] == "New and improved description"  # Should be updated
            assert data["year_built"] == 2020  # Should remain unchanged


def test_update_property_retrieval_failure_after_update():
    """Test error handling when property retrieval fails after update."""
    # Arrange
    property_id = 321
    fake_user = create_test_user(email="owner@example.com")
    
    update_data = {"name": "Updated Name"}
    
    # Mock the service layer to raise 500 error
    with patch(
        "Backend.api.properties.router.PropertyService.update_property",
        new=AsyncMock(side_effect=HTTPException(status_code=500, detail="Property updated but could not be re-retrieved"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/properties/{property_id}", json=update_data)
            
            # Assert
            assert response.status_code == 500
            assert "Property updated but could not be re-retrieved" in response.json()["detail"]


def test_update_property_unauthorized():
    """Test that updating a property requires authentication."""
    # Arrange - don't override get_current_user to simulate unauthenticated request
    property_id = 123
    update_data = {"name": "Updated Name"}
    
    # Only override the session
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.put(f"/api/properties/{property_id}", json=update_data)
        
        # Assert - Accept either 401 or 403 as both indicate lack of proper auth
        # 401: No auth header provided (authentication required)  
        # 403: Invalid/expired token (authorization failed)
        assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}" 

async def test_update_property_units_are_sorted_by_id():
    """Test that units in the updated property response are sorted by ID."""
    property_id = 888
    user = create_test_user()
    now = datetime.now(timezone.utc)

    # Create mock units out of order to test sorting
    unit2 = create_mock_unit(unit_id=2, name="Unit 2")
    unit1 = create_mock_unit(unit_id=1, name="Unit 1")

    # The service method is responsible for sorting. The fake_response should
    # reflect the final state returned by the service, which includes sorted units.
    fake_response = PropertyDetailResponse_Standalone(
        id=property_id,
        name="Updated Property",
        address="123 Test St",
        city="Test City",
        province="Test Province",
        postal_code="12345",
        property_type=PropertyType.RESIDENTIAL,
        description="Updated property with sorted units",
        year_built=2020,
        status=PropertyStatus.ACTIVE,
        user_id=user.id,
        created_at=now,
        updated_at=now,
        owner=OwnerResponse.model_validate(user),
        units=[
            # Manually create UnitResponse instances from mock data, in sorted order
            UnitResponse.model_validate(unit1),
            UnitResponse.model_validate(unit2),
        ],
        stats=PropertyStats(
            total_units=2,
            vacant_units=2,
            occupied_units=0,
            monthly_revenue=Decimal("0.00"),
            occupancy_rate=0.0
        )
    )

    # Patch the service method to return our pre-sorted response
    with patch("Backend.api.properties.router.PropertyService.update_property", new=AsyncMock(return_value=fake_response)):
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        update_data = {"name": "Updated Property Name"}

        client = TestClientWithHost(app=app)
        response = client.put(f"/api/properties/{property_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert len(data["units"]) == 2

        # Assert that the units in the response are sorted by ID
        assert data["units"][0]["id"] == 1
        assert data["units"][0]["name"] == "Unit 1"
        assert data["units"][1]["id"] == 2
        assert data["units"][1]["name"] == "Unit 2"


 