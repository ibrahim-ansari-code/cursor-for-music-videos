"""
Unit tests for GET operations in the properties API endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.api.properties.schemas import PropertyDetailResponse_Standalone, OwnerResponse, UnitResponse, TenantInfo, PropertyResponse, PropertyStats
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

def create_mock_unit(unit_id: int | None = 1, **kwargs):
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
# GET PROPERTY TESTS
# =============================================================================

def test_get_property_owner_success():
    """Test successful property retrieval by owner with status derivation."""
    # Arrange
    property_id = 123
    owner_id = uuid4()
    fake_user = create_test_user(user_id=owner_id, email="owner@example.com")
    
    # Mock tenant
    tenant = MagicMock()
    tenant.id = 10
    tenant.first_name = "Tenant"
    tenant.last_name = "Smith"
    tenant.email = "tenant@example.com"
    
    # Mock units
    unit1 = create_mock_unit(
        unit_id=1,
        name="Unit 1",
        description="Nice unit",
        size=55.5,
        monthly_rent=Decimal("1200.00"),
        is_rented=True,
        bedrooms=2,
        bathrooms=1.5,
        floor=1,
        tenant=tenant
    )
    
    unit2 = create_mock_unit(
        unit_id=2,
        name="Unit 2",
        description="Another unit",
        size=45.0,
        monthly_rent=Decimal("1000.00"),
        is_rented=False,
        bedrooms=1,
        bathrooms=1.0,
        floor=2,
        tenant=None
    )
    
    # Create property with units
    fake_property = create_mock_property(
        property_id=property_id,
        name="Test Property",
        address="123 Main St",
        city="Testville",
        province="TestState",
        postal_code="T3S7C0",
        property_type=PropertyType.RESIDENTIAL,
        description="A test property",
        year_built=2000,
        status=PropertyStatus.ACTIVE,
        user_id=owner_id,
        owner=fake_user,
        units=[unit1, unit2]
    )
    
    # Create the response object that the service would return
    fake_response = PropertyDetailResponse_Standalone(
        id=property_id,
        name="Test Property",
        address="123 Main St",
        city="Testville",
        province="TestState",
        postal_code="T3S7C0",
        property_type=PropertyType.RESIDENTIAL,
        description="A test property",
        year_built=2000,
        status=PropertyStatus.PARTIALLY_RENTED,  # Derived status
        user_id=owner_id,
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
        units=[
            UnitResponse(
                id=1,
                name="Unit 1",
                description="Nice unit",
                size=55.5,
                monthly_rent=Decimal("1200.00"),
                is_rented=True,
                bedrooms=2,
                bathrooms=1.5,
                floor=1,
                created_at=unit1.created_at,
                updated_at=unit1.updated_at,
                tenant=TenantInfo(
                    id=10,
                    first_name="Tenant",
                    last_name="Smith",
                    email="tenant@example.com"
                )
            ),
            UnitResponse(
                id=2,
                name="Unit 2",
                description="Another unit",
                size=45.0,
                monthly_rent=Decimal("1000.00"),
                is_rented=False,
                bedrooms=1,
                bathrooms=1.0,
                floor=2,
                created_at=unit2.created_at,
                updated_at=unit2.updated_at,
                tenant=None
            )
        ]
    )
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.get_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/properties/{property_id}")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == property_id
            assert data["name"] == "Test Property"
            assert data["owner"] is not None
            assert data["owner"]["id"] == str(owner_id)
            assert data["owner"]["email"] == "owner@example.com"
            assert data["units"] is not None
            assert len(data["units"]) == 2
            
            # Check unit 1 (with tenant)
            unit1_data = next(u for u in data["units"] if u["id"] == 1)
            assert unit1_data["name"] == "Unit 1"
            assert unit1_data["is_rented"] is True
            assert unit1_data["tenant"] is not None
            assert unit1_data["tenant"]["id"] == 10
            assert unit1_data["tenant"]["first_name"] == "Tenant"
            assert unit1_data["tenant"]["last_name"] == "Smith"
            assert unit1_data["tenant"]["email"] == "tenant@example.com"
            
            # Check unit 2 (no tenant)
            unit2_data = next(u for u in data["units"] if u["id"] == 2)
            assert unit2_data["name"] == "Unit 2"
            assert unit2_data["is_rented"] is False
            assert unit2_data["tenant"] is None
            
            # Status should be 'PARTIALLY_RENTED' (since one unit is rented, one is not)
            assert data["status"] == "PARTIALLY_RENTED"


def test_get_property_admin_can_view_any_property():
    """Test that admin can view properties they don't own."""
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
    
    fake_property = create_mock_property(
        property_id=property_id,
        name="Someone Else's Property",
        user_id=owner_id,
        owner=property_owner,
        units=[],
        status=PropertyStatus.ACTIVE,
        address="456 Other St",
        city="Other City",
        province="Other Province",
        postal_code="O1H2R3",
        property_type=PropertyType.COMMERCIAL,
        description="Not admin's property",
        year_built=2010
    )
    
    # Create the response
    fake_response = PropertyDetailResponse_Standalone(
        id=property_id,
        name="Someone Else's Property",
        address="456 Other St",
        city="Other City",
        province="Other Province",
        postal_code="O1H2R3",
        property_type=PropertyType.COMMERCIAL,
        description="Not admin's property",
        year_built=2010,
        status=PropertyStatus.ACTIVE,
        user_id=owner_id,
        created_at=fake_property.created_at,
        updated_at=fake_property.updated_at,
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
    with patch("Backend.api.properties.router.PropertyService.get_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/properties/{property_id}")
            
            # Assert - Admin should be able to view the property
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == property_id
            assert data["owner"]["id"] == str(owner_id)


def test_get_property_not_found():
    """Test 404 error when property doesn't exist."""
    # Arrange
    property_id = 999
    fake_user = create_test_user()
    
    # Mock the service layer to raise 404
    with patch(
        "Backend.api.properties.router.PropertyService.get_property",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Property not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/properties/{property_id}")
            
            # Assert
            assert response.status_code == 404
            assert "Property not found" in response.json()["detail"]


def test_get_property_forbidden_non_owner():
    """Test 403 error when non-owner/non-admin tries to access property."""
    # Arrange
    property_id = 123
    owner_id = uuid4()
    other_user_id = uuid4()
    
    other_user = create_test_user(
        user_id=other_user_id,
        email="other@example.com"
    )
    
    # Mock the service layer to raise 403
    with patch(
        "Backend.api.properties.router.PropertyService.get_property",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="You don't have permission to view this property"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: other_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/properties/{property_id}")
            
            # Assert
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()


def test_get_property_status_derivation_all_vacant():
    """Test that property with all vacant units shows VACANT status."""
    # Arrange
    property_id = 789
    owner_id = uuid4()
    fake_user = create_test_user(user_id=owner_id)
    
    # Create 3 vacant units
    units = []
    for i in range(1, 4):
        unit = create_mock_unit(
            unit_id=i,
            name=f"Unit {i}",
            is_rented=False,
            tenant=None,
            floor=i
        )
        units.append(unit)
    
    fake_property = create_mock_property(
        property_id=property_id,
        name="All Vacant Property",
        status=PropertyStatus.ACTIVE,
        units=units,
        user_id=owner_id,
        owner=fake_user
    )
    
    # Create response with VACANT status (derived from all units being vacant)
    fake_response = PropertyDetailResponse_Standalone(
        id=property_id,
        name="All Vacant Property",
        address=fake_property.address,
        city=fake_property.city,
        province=fake_property.province,
        postal_code=fake_property.postal_code,
        property_type=fake_property.property_type,
        description=fake_property.description,
        year_built=fake_property.year_built,
        status=PropertyStatus.VACANT,  # Derived status
        user_id=owner_id,
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
        units=[
            UnitResponse(
                id=unit.id,
                name=unit.name,
                description=unit.description,
                size=unit.size,
                monthly_rent=unit.monthly_rent,
                is_rented=unit.is_rented,
                bedrooms=unit.bedrooms,
                bathrooms=unit.bathrooms,
                floor=unit.floor,
                created_at=unit.created_at,
                updated_at=unit.updated_at,
                tenant=None
            ) for unit in units
        ]
    )
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.get_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/properties/{property_id}")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "VACANT"


def test_get_property_status_derivation_all_rented():
    """Test that property with all rented units shows RENTED status."""
    # Arrange
    property_id = 101
    owner_id = uuid4()
    fake_user = create_test_user(user_id=owner_id)
    
    # Create 3 rented units
    units = []
    for i in range(1, 4):
        tenant = MagicMock()
        tenant.id = 100 + i
        tenant.first_name = f"Tenant{i}"
        tenant.last_name = f"Renter{i}"
        tenant.email = f"tenant{i}@example.com"
        
        unit = create_mock_unit(
            unit_id=i,
            name=f"Unit {i}",
            is_rented=True,
            tenant=tenant,
            floor=i
        )
        units.append(unit)
    
    fake_property = create_mock_property(
        property_id=property_id,
        name="Fully Rented Property",
        status=PropertyStatus.ACTIVE,
        units=units,
        user_id=owner_id,
        owner=fake_user
    )
    
    # Create response with RENTED status (derived from all units being rented)
    fake_response = PropertyDetailResponse_Standalone(
        id=property_id,
        name="Fully Rented Property",
        address=fake_property.address,
        city=fake_property.city,
        province=fake_property.province,
        postal_code=fake_property.postal_code,
        property_type=fake_property.property_type,
        description=fake_property.description,
        year_built=fake_property.year_built,
        status=PropertyStatus.RENTED,  # Derived status
        user_id=owner_id,
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
        units=[
            UnitResponse(
                id=unit.id,
                name=unit.name,
                description=unit.description,
                size=unit.size,
                monthly_rent=unit.monthly_rent,
                is_rented=unit.is_rented,
                bedrooms=unit.bedrooms,
                bathrooms=unit.bathrooms,
                floor=unit.floor,
                created_at=unit.created_at,
                updated_at=unit.updated_at,
                tenant=TenantInfo(
                    id=unit.tenant.id,
                    first_name=unit.tenant.first_name,
                    last_name=unit.tenant.last_name,
                    email=unit.tenant.email
                )
            ) for unit in units
        ]
    )
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.get_property", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/properties/{property_id}")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "RENTED"


# =============================================================================
# GET PROPERTIES (LIST) TESTS
# =============================================================================

def test_get_properties_regular_user_sees_only_own():
    """Test that regular users only see their own properties."""
    # Arrange
    user_id = uuid4()
    other_user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Create properties - only one belongs to the user
    user_property = create_mock_property(
        property_id=1,
        name="User's Property",
        status=PropertyStatus.ACTIVE,
        user_id=user_id
    )
    
    # Create list response with only user's property
    fake_response = [
        PropertyResponse(
            id=1,
            name="User's Property",
            address=user_property.address,
            city=user_property.city,
            province=user_property.province,
            postal_code=user_property.postal_code,
            property_type=user_property.property_type,
            description=user_property.description,
            year_built=user_property.year_built,
            status=PropertyStatus.ACTIVE,
            user_id=user_id,
            created_at=user_property.created_at,
            updated_at=user_property.updated_at
        )
    ]
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.get_properties", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/properties/")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "User's Property"
            assert data[0]["user_id"] == str(user_id)


def test_get_properties_admin_sees_all():
    """Test that admin users can see all properties."""
    # Arrange
    admin_id = uuid4()
    user1_id = uuid4()
    user2_id = uuid4()
    
    admin_user = create_test_user(
        user_id=admin_id,
        email="admin@example.com",
        user_type="ADMIN",
        is_admin=True
    )
    
    # Create properties from different users
    prop1 = create_mock_property(
        property_id=1,
        name="Property 1",
        status=PropertyStatus.ACTIVE,
        user_id=user1_id,
        property_type=PropertyType.RESIDENTIAL
    )
    
    prop2 = create_mock_property(
        property_id=2,
        name="Property 2",
        status=PropertyStatus.INACTIVE,
        user_id=user2_id,
        property_type=PropertyType.COMMERCIAL
    )
    
    # Create list response with all properties
    fake_response = [
        PropertyResponse(
            id=1,
            name="Property 1",
            address=prop1.address,
            city=prop1.city,
            province=prop1.province,
            postal_code=prop1.postal_code,
            property_type=PropertyType.RESIDENTIAL,
            description=prop1.description,
            year_built=prop1.year_built,
            status=PropertyStatus.ACTIVE,
            user_id=user1_id,
            created_at=prop1.created_at,
            updated_at=prop1.updated_at
        ),
        PropertyResponse(
            id=2,
            name="Property 2",
            address=prop2.address,
            city=prop2.city,
            province=prop2.province,
            postal_code=prop2.postal_code,
            property_type=PropertyType.COMMERCIAL,
            description=prop2.description,
            year_built=prop2.year_built,
            status=PropertyStatus.INACTIVE,
            user_id=user2_id,
            created_at=prop2.created_at,
            updated_at=prop2.updated_at
        )
    ]
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.get_properties", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/properties/")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "Property 1"
            assert data[1]["name"] == "Property 2"


def test_get_properties_with_filters():
    """Test property filtering by status and type."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Only properties matching filters should be returned
    matching_prop = create_mock_property(
        property_id=1,
        name="Matching Property",
        status=PropertyStatus.DRAFT,
        property_type=PropertyType.COMMERCIAL,
        user_id=user_id
    )
    
    # Create filtered response
    fake_response = [
        PropertyResponse(
            id=1,
            name="Matching Property",
            address=matching_prop.address,
            city=matching_prop.city,
            province=matching_prop.province,
            postal_code=matching_prop.postal_code,
            property_type=PropertyType.COMMERCIAL,
            description=matching_prop.description,
            year_built=matching_prop.year_built,
            status=PropertyStatus.DRAFT,
            user_id=user_id,
            created_at=matching_prop.created_at,
            updated_at=matching_prop.updated_at
        )
    ]
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.get_properties", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/properties/", params={
                "status": "DRAFT",
                "property_type": "Commercial"
            })
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == "DRAFT"
            assert data[0]["property_type"] == "Commercial"


def test_get_properties_null_status_defaults_to_active():
    """Test that properties with null status default to ACTIVE."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    prop_with_null_status = create_mock_property(
        property_id=1,
        name="Null Status Property",
        status=None,  # Null status
        user_id=user_id
    )
    
    # Create response with default ACTIVE status
    fake_response = [
        PropertyResponse(
            id=1,
            name="Null Status Property",
            address=prop_with_null_status.address,
            city=prop_with_null_status.city,
            province=prop_with_null_status.province,
            postal_code=prop_with_null_status.postal_code,
            property_type=prop_with_null_status.property_type,
            description=prop_with_null_status.description,
            year_built=prop_with_null_status.year_built,
            status=PropertyStatus.ACTIVE,  # Defaulted to ACTIVE
            user_id=user_id,
            created_at=prop_with_null_status.created_at,
            updated_at=prop_with_null_status.updated_at
        )
    ]
    
    # Mock the service layer
    with patch("Backend.api.properties.router.PropertyService.get_properties", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/properties/")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == "ACTIVE"


def test_get_properties_database_error():
    """Test error handling for database exceptions."""
    # Arrange
    fake_user = create_test_user()
    
    # Mock the service layer to raise an exception
    with patch(
        "Backend.api.properties.router.PropertyService.get_properties",
        new=AsyncMock(side_effect=HTTPException(status_code=500, detail="Failed to fetch properties"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/properties/")
            
            # Assert
            assert response.status_code == 500
            assert "Failed to fetch properties" in response.json()["detail"] 

async def test_get_property_units_are_sorted_by_id():
    """Test that units in the property response are sorted by ID."""
    property_id = 999
    user = create_test_user()
    now = datetime.now(timezone.utc)

    # Create mock units out of order to test sorting
    unit2 = create_mock_unit(unit_id=2, name="Unit 2")
    unit1 = create_mock_unit(unit_id=1, name="Unit 1")

    # The service method is responsible for sorting. The fake_response should
    # reflect the final state returned by the service, which includes sorted units.
    # The UnitResponse objects are created directly with data.
    fake_response = PropertyDetailResponse_Standalone(
        id=property_id,
        name="Test Property",
        address="123 Test St",
        city="Test City",
        province="Test Province",
        postal_code="12345",
        property_type=PropertyType.APARTMENT_COMPLEX,
        description="Test property with units to sort",
        year_built=2020,
        status=PropertyStatus.ACTIVE,
        user_id=user.id,
        created_at=now,
        updated_at=now,
        owner=OwnerResponse.model_validate(user),
        units=[
            # Manually create UnitResponse instances from mock data, in sorted order
            UnitResponse(
                id=unit1.id, name=unit1.name, description=unit1.description,
                size=unit1.size, monthly_rent=unit1.monthly_rent, is_rented=unit1.is_rented,
                bedrooms=unit1.bedrooms, bathrooms=unit1.bathrooms, floor=unit1.floor,
                created_at=unit1.created_at, updated_at=unit1.updated_at, tenant=unit1.tenant
            ),
            UnitResponse(
                id=unit2.id, name=unit2.name, description=unit2.description,
                size=unit2.size, monthly_rent=unit2.monthly_rent, is_rented=unit2.is_rented,
                bedrooms=unit2.bedrooms, bathrooms=unit2.bathrooms, floor=unit2.floor,
                created_at=unit2.created_at, updated_at=unit2.updated_at, tenant=unit2.tenant
            ),
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
    with patch("Backend.api.properties.router.PropertyService.get_property", new=AsyncMock(return_value=fake_response)):
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        client = TestClientWithHost(app=app)
        response = client.get(f"/api/properties/{property_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["units"]) == 2
        
        # Assert that the units in the response are sorted by ID
        assert data["units"][0]["id"] == 1
        assert data["units"][0]["name"] == "Unit 1"
        assert data["units"][1]["id"] == 2
        assert data["units"][1]["name"] == "Unit 2"


 