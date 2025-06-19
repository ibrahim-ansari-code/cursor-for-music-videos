"""
Unit tests for GET operations in the properties API endpoint.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, UTC
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.properties.router import get_property, get_properties
from Backend.api.properties.schemas import PropertyDetailResponse_Standalone
from Backend.models.property import Property, PropertyUnit
from Backend.models.user import User
from Backend.models.enums import PropertyStatus
from Backend.models.property import PropertyType


# =============================================================================
# GET PROPERTY TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_property_owner_success(mocker):
    """Test successful property retrieval by owner with status derivation."""
    # Arrange
    property_id = 123
    owner_id = uuid4()
    now = datetime.now(UTC)

    # Mock current_user (owner)
    current_user = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    # Mock property owner (same as current_user)
    property_owner = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    # Mock tenant
    tenant = MagicMock()
    tenant.id = 10
    tenant.first_name = "Tenant"
    tenant.last_name = "Smith"
    tenant.email = "tenant@example.com"

    # Mock units
    unit1 = MagicMock(spec=PropertyUnit)
    unit1.id = 1
    unit1.name = "Unit 1"
    unit1.description = "Nice unit"
    unit1.size = 55.5
    unit1.monthly_rent = Decimal("1200.00")
    unit1.is_rented = True
    unit1.bedrooms = 2
    unit1.bathrooms = 1.5
    unit1.floor = 1
    unit1.created_at = now
    unit1.updated_at = now
    unit1.tenant = tenant

    unit2 = MagicMock(spec=PropertyUnit)
    unit2.id = 2
    unit2.name = "Unit 2"
    unit2.description = "Another unit"
    unit2.size = 45.0
    unit2.monthly_rent = Decimal("1000.00")
    unit2.is_rented = False
    unit2.bedrooms = 1
    unit2.bathrooms = 1.0
    unit2.floor = 2
    unit2.created_at = now
    unit2.updated_at = now
    unit2.tenant = None

    # Mock property ORM object
    property_orm = MagicMock(spec=Property)
    property_orm.id = property_id
    property_orm.name = "Test Property"
    property_orm.address = "123 Main St"
    property_orm.city = "Testville"
    property_orm.province = "TestState"
    property_orm.postal_code = "T3S7C0"
    property_orm.property_type = PropertyType.RESIDENTIAL
    property_orm.description = "A test property"
    property_orm.year_built = 2000
    property_orm.status = PropertyStatus.ACTIVE
    property_orm.user_id = owner_id
    property_orm.created_at = now
    property_orm.updated_at = now
    property_orm.owner = property_owner
    property_orm.units = [unit1, unit2]

    # Mock session and query execution
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result

    # Patch dependencies
    mocker.patch("Backend.api.auth.get_current_user", return_value=current_user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)

    # Act
    response = await get_property(
        property_id=property_id,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.id == property_id
    assert response.name == "Test Property"
    assert response.owner is not None
    assert response.owner.id == owner_id
    assert response.owner.email == "owner@example.com"
    assert response.units is not None
    assert len(response.units) == 2

    # Check unit 1 (with tenant)
    unit_resp1 = next(u for u in response.units if u.id == 1)
    assert unit_resp1.name == "Unit 1"
    assert unit_resp1.is_rented is True
    assert unit_resp1.tenant is not None
    assert unit_resp1.tenant.id == 10
    assert unit_resp1.tenant.first_name == "Tenant"
    assert unit_resp1.tenant.last_name == "Smith"
    assert unit_resp1.tenant.email == "tenant@example.com"

    # Check unit 2 (no tenant)
    unit_resp2 = next(u for u in response.units if u.id == 2)
    assert unit_resp2.name == "Unit 2"
    assert unit_resp2.is_rented is False
    assert unit_resp2.tenant is None

    # Status should be 'PARTIALLY_RENTED' (since one unit is rented, one is not)
    assert response.status == PropertyStatus.PARTIALLY_RENTED


@pytest.mark.asyncio
async def test_get_property_admin_can_view_any_property(mocker):
    """Test that admin can view properties they don't own."""
    # Arrange
    property_id = 456
    owner_id = uuid4()
    admin_id = uuid4()
    now = datetime.now(UTC)

    admin_user = User(
        id=admin_id,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        is_admin=True,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="ADMIN"
    )

    property_owner = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Property",
        last_name="Owner",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    property_orm = MagicMock(spec=Property)
    property_orm.id = property_id
    property_orm.name = "Someone Else's Property"
    property_orm.user_id = owner_id  # Different from admin_id
    property_orm.owner = property_owner
    property_orm.units = []
    property_orm.status = PropertyStatus.ACTIVE
    property_orm.address = "456 Other St"
    property_orm.city = "Other City"
    property_orm.province = "Other Province"
    property_orm.postal_code = "O1H2R3"
    property_orm.property_type = PropertyType.COMMERCIAL
    property_orm.description = "Not admin's property"
    property_orm.year_built = 2010
    property_orm.created_at = now
    property_orm.updated_at = now

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result

    # Act
    response = await get_property(
        property_id=property_id,
        current_user=admin_user,
        session=mock_session
    )

    # Assert - Admin should be able to view the property
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.id == property_id
    assert response.owner is not None
    assert response.owner.id == owner_id


@pytest.mark.asyncio
async def test_get_property_not_found(mocker):
    """Test 404 error when property doesn't exist."""
    # Arrange
    property_id = 999
    user_id = uuid4()
    now = datetime.now(UTC)

    current_user = User(
        id=user_id,
        email="user@example.com",
        first_name="Test",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    # Mock session and query execution to return None
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_property(
            property_id=property_id,
            current_user=current_user,
            session=mock_session
        )
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Property not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_property_forbidden_non_owner(mocker):
    """Test 403 error when non-owner/non-admin tries to access property."""
    # Arrange
    property_id = 123
    owner_id = uuid4()
    other_user_id = uuid4()
    now = datetime.now(UTC)

    other_user = User(
        id=other_user_id,
        email="other@example.com",
        first_name="Other",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    property_orm = MagicMock(spec=Property)
    property_orm.id = property_id
    property_orm.user_id = owner_id  # Different from other_user_id
    property_orm.owner = MagicMock()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_property(
            property_id=property_id,
            current_user=other_user,
        session=mock_session
    )
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "permission" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_get_property_status_derivation_all_vacant(mocker):
    """Test that property with all vacant units shows VACANT status."""
    # Arrange
    property_id = 789
    owner_id = uuid4()
    now = datetime.now(UTC)

    current_user = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    # Create 3 vacant units
    units = []
    for i in range(1, 4):
        unit = MagicMock(spec=PropertyUnit)
        unit.id = i
        unit.name = f"Unit {i}"
        unit.is_rented = False
        unit.tenant = None
        unit.description = ""
        unit.size = 50.0
        unit.monthly_rent = Decimal("1000.00")
        unit.bedrooms = 1
        unit.bathrooms = 1.0
        unit.floor = i
        unit.created_at = now
        unit.updated_at = now
        units.append(unit)

    property_orm = MagicMock(spec=Property)
    property_orm.id = property_id
    property_orm.name = "All Vacant Property"
    property_orm.status = PropertyStatus.ACTIVE  # Stored status
    property_orm.units = units
    property_orm.user_id = owner_id
    property_orm.owner = current_user
    property_orm.address = "789 Vacant St"
    property_orm.city = "Empty City"
    property_orm.province = "Vacancy Province"
    property_orm.postal_code = "V0C0N7"
    property_orm.property_type = PropertyType.RESIDENTIAL
    property_orm.description = "All units vacant"
    property_orm.year_built = 2020
    property_orm.created_at = now
    property_orm.updated_at = now

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result

    # Act
    response = await get_property(
        property_id=property_id,
        current_user=current_user,
            session=mock_session
        )

    # Assert
    assert response.status == PropertyStatus.VACANT


@pytest.mark.asyncio
async def test_get_property_status_derivation_all_rented(mocker):
    """Test that property with all rented units shows RENTED status."""
    # Arrange
    property_id = 101
    owner_id = uuid4()
    now = datetime.now(UTC)

    current_user = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    # Create 3 rented units
    units = []
    for i in range(1, 4):
        unit = MagicMock(spec=PropertyUnit)
        unit.id = i
        unit.name = f"Unit {i}"
        unit.is_rented = True
        unit.tenant = MagicMock()
        unit.tenant.id = 100 + i
        unit.tenant.first_name = f"Tenant{i}"
        unit.tenant.last_name = f"Renter{i}"
        unit.tenant.email = f"tenant{i}@example.com"
        unit.description = ""
        unit.size = 50.0
        unit.monthly_rent = Decimal("1000.00")
        unit.bedrooms = 1
        unit.bathrooms = 1.0
        unit.floor = i
        unit.created_at = now
        unit.updated_at = now
        units.append(unit)

    property_orm = MagicMock(spec=Property)
    property_orm.id = property_id
    property_orm.name = "Fully Rented Property"
    property_orm.status = PropertyStatus.ACTIVE  # Stored status
    property_orm.units = units
    property_orm.user_id = owner_id
    property_orm.owner = current_user
    property_orm.address = "101 Full St"
    property_orm.city = "Occupied City"
    property_orm.province = "Rental Province"
    property_orm.postal_code = "R3N73D"
    property_orm.property_type = PropertyType.RESIDENTIAL
    property_orm.description = "All units rented"
    property_orm.year_built = 2019
    property_orm.created_at = now
    property_orm.updated_at = now

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result

    # Act
    response = await get_property(
        property_id=property_id,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert response.status == PropertyStatus.RENTED


# =============================================================================
# GET PROPERTIES (LIST) TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_properties_regular_user_sees_only_own(mocker):
    """Test that regular users only see their own properties."""
    # Arrange
    user_id = uuid4()
    other_user_id = uuid4()
    now = datetime.now(UTC)
    
    user = User(
        id=user_id,
        email="user@example.com",
        first_name="User",
        last_name="Test",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )
    
    # Create properties - only one belongs to the user
    user_property = MagicMock(spec=Property)
    user_property.id = 1
    user_property.name = "User's Property"
    user_property.status = PropertyStatus.ACTIVE
    user_property.user_id = user_id
    
    other_property = MagicMock(spec=Property)
    other_property.id = 2
    other_property.name = "Other's Property"
    other_property.status = PropertyStatus.ACTIVE
    other_property.user_id = other_user_id
    
    # Mock will return only user's property
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [user_property]
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_properties(
        status_filter=None,
        property_type=None,
        current_user=user,
        session=mock_session
    )
    
    # Assert
    assert len(result) == 1
    assert result[0].name == "User's Property"
    assert result[0].user_id == user_id


@pytest.mark.asyncio
async def test_get_properties_admin_sees_all(mocker):
    """Test that admin users can see all properties."""
    # Arrange
    admin_id = uuid4()
    user1_id = uuid4()
    user2_id = uuid4()
    now = datetime.now(UTC)
    
    admin_user = User(
        id=admin_id,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        is_admin=True,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="ADMIN"
    )
    
    # Create properties from different users
    prop1 = MagicMock(spec=Property)
    prop1.id = 1
    prop1.name = "Property 1"
    prop1.status = PropertyStatus.ACTIVE
    prop1.user_id = user1_id
    prop1.property_type = PropertyType.RESIDENTIAL
    prop1.address = "Addr1"
    prop1.city = "City1"
    prop1.province = "Prov1"
    prop1.postal_code = "11111"
    prop1.description = "desc1"
    prop1.year_built = 2001
    prop1.created_at = now
    prop1.updated_at = now
    
    prop2 = MagicMock(spec=Property)
    prop2.id = 2
    prop2.name = "Property 2"
    prop2.status = PropertyStatus.INACTIVE
    prop2.user_id = user2_id
    prop2.property_type = PropertyType.COMMERCIAL
    prop2.address = "Addr2"
    prop2.city = "City2"
    prop2.province = "Prov2"
    prop2.postal_code = "22222"
    prop2.description = "desc2"
    prop2.year_built = 2002
    prop2.created_at = now
    prop2.updated_at = now
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [prop1, prop2]
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_properties(
        status_filter=None,
        property_type=None,
        current_user=admin_user,
        session=mock_session
    )
    
    # Assert
    assert len(result) == 2
    assert result[0].name == "Property 1"
    assert result[1].name == "Property 2"


@pytest.mark.asyncio
async def test_get_properties_with_filters(mocker):
    """Test property filtering by status and type."""
    # Arrange
    user_id = uuid4()
    now = datetime.now(UTC)
    
    user = User(
        id=user_id,
        email="user@example.com",
        first_name="User",
        last_name="Test",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )
    
    # Only properties matching filters should be returned
    matching_prop = MagicMock(spec=Property)
    matching_prop.id = 1
    matching_prop.name = "Matching Property"
    matching_prop.status = PropertyStatus.DRAFT
    matching_prop.property_type = PropertyType.COMMERCIAL
    matching_prop.user_id = user_id
    matching_prop.address = "Match St"
    matching_prop.city = "Match City"
    matching_prop.province = "Match Province"
    matching_prop.postal_code = "M0T0C1"
    matching_prop.description = "Matches filters"
    matching_prop.year_built = 2020
    matching_prop.created_at = now
    matching_prop.updated_at = now
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [matching_prop]
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_properties(
        status_filter=PropertyStatus.DRAFT,
        property_type=PropertyType.COMMERCIAL,
        current_user=user,
        session=mock_session
    )
    
    # Assert
    assert len(result) == 1
    assert result[0].status == PropertyStatus.DRAFT
    assert result[0].property_type == PropertyType.COMMERCIAL


@pytest.mark.asyncio
async def test_get_properties_null_status_defaults_to_active(mocker):
    """Test that properties with null status default to ACTIVE."""
    # Arrange
    user_id = uuid4()
    now = datetime.now(UTC)
    
    user = User(
        id=user_id,
        email="user@example.com",
        first_name="User",
        last_name="Test",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )
    
    prop_with_null_status = MagicMock(spec=Property)
    prop_with_null_status.id = 1
    prop_with_null_status.name = "Null Status Property"
    prop_with_null_status.status = None  # Null status
    prop_with_null_status.user_id = user_id
    prop_with_null_status.property_type = PropertyType.RESIDENTIAL
    prop_with_null_status.address = "Null St"
    prop_with_null_status.city = "Null City"
    prop_with_null_status.province = "Null Province"
    prop_with_null_status.postal_code = "N0L0L0"
    prop_with_null_status.description = "Has null status"
    prop_with_null_status.year_built = 2021
    prop_with_null_status.created_at = now
    prop_with_null_status.updated_at = now
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [prop_with_null_status]
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_properties(
        status_filter=None,
        property_type=None,
        current_user=user,
        session=mock_session
    )
    
    # Assert
    assert len(result) == 1
    assert result[0].status == PropertyStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_properties_database_error(mocker):
    """Test error handling for database exceptions."""
    # Arrange
    user_id = uuid4()
    now = datetime.now(UTC)
    
    user = User(
        id=user_id,
        email="user@example.com",
        first_name="User",
        last_name="Test",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )
    
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Database connection error")
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_properties(
            status_filter=None,
            property_type=None,
            current_user=user,
            session=mock_session
        )
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to fetch properties" in str(exc_info.value.detail) 