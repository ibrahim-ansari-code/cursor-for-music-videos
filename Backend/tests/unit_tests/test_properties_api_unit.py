"""
Unit tests for the properties API endpoint.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, UTC
from decimal import Decimal
from pydantic import ValidationError

from fastapi import HTTPException, status

from Backend.api.properties import get_property, get_properties, create_property, PropertyCreate
from Backend.models.property import Property, PropertyUnit
from Backend.models.user import User
from Backend.models.enums import PropertyStatus
from Backend.api.properties import PropertyDetailResponse_Standalone


@pytest.mark.asyncio
async def test_get_property_owner_success(mocker):
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
    property_orm.property_type = "residential"
    property_orm.description = "A test property"
    property_orm.year_built = 2000
    property_orm.status = "ACTIVE"
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
    assert response.status == "PARTIALLY_RENTED"


@pytest.mark.asyncio
async def test_create_property_with_units_success(mocker):
    # Arrange
    property_id = 456
    owner_id = uuid4()
    now = datetime.now(UTC)

    # Mock current_user (owner)
    current_user = User(
        id=owner_id,
        email="owner2@example.com",
        first_name="Owner2",
        last_name="User2",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    # Mock property owner (same as current_user)
    property_owner = User(
        id=owner_id,
        email="owner2@example.com",
        first_name="Owner2",
        last_name="User2",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    # Mock tenants
    tenant1 = MagicMock()
    tenant1.id = 21
    tenant1.first_name = "Alice"
    tenant1.last_name = "Johnson"
    tenant1.email = "alice@example.com"

    tenant2 = MagicMock()
    tenant2.id = 22
    tenant2.first_name = "Bob"
    tenant2.last_name = "Lee"
    tenant2.email = "bob@example.com"

    # Mock units
    unit1 = MagicMock(spec=PropertyUnit)
    unit1.id = 11
    unit1.name = "Unit A"
    unit1.description = "First unit"
    unit1.size = 60.0
    unit1.monthly_rent = Decimal("1500.00")
    unit1.is_rented = True
    unit1.bedrooms = 2
    unit1.bathrooms = 2.0
    unit1.floor = 1
    unit1.created_at = now
    unit1.updated_at = now
    unit1.tenant = tenant1

    unit2 = MagicMock(spec=PropertyUnit)
    unit2.id = 12
    unit2.name = "Unit B"
    unit2.description = "Second unit"
    unit2.size = 70.0
    unit2.monthly_rent = Decimal("1700.00")
    unit2.is_rented = True
    unit2.bedrooms = 3
    unit2.bathrooms = 2.5
    unit2.floor = 2
    unit2.created_at = now
    unit2.updated_at = now
    unit2.tenant = tenant2

    # Mock property ORM object
    property_orm = MagicMock(spec=Property)
    property_orm.id = property_id
    property_orm.name = "Multi-Unit Property"
    property_orm.address = "456 Elm St"
    property_orm.city = "Unitville"
    property_orm.province = "ProvinceX"
    property_orm.postal_code = "U1N1T2"
    property_orm.property_type = "apartment"
    property_orm.description = "A property with multiple units"
    property_orm.year_built = 2010
    property_orm.status = "ACTIVE"
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
    assert response.name == "Multi-Unit Property"
    assert response.owner is not None
    assert response.owner.id == owner_id
    assert response.owner.email == "owner2@example.com"
    assert response.units is not None
    assert len(response.units) == 2

    # Check unit 1
    unit_resp1 = next(u for u in response.units if u.id == 11)
    assert unit_resp1.name == "Unit A"
    assert unit_resp1.is_rented is True
    assert unit_resp1.tenant is not None
    assert unit_resp1.tenant.id == 21
    assert unit_resp1.tenant.first_name == "Alice"
    assert unit_resp1.tenant.last_name == "Johnson"
    assert unit_resp1.tenant.email == "alice@example.com"

    # Check unit 2
    unit_resp2 = next(u for u in response.units if u.id == 12)
    assert unit_resp2.name == "Unit B"
    assert unit_resp2.is_rented is True
    assert unit_resp2.tenant is not None
    assert unit_resp2.tenant.id == 22
    assert unit_resp2.tenant.first_name == "Bob"
    assert unit_resp2.tenant.last_name == "Lee"
    assert unit_resp2.tenant.email == "bob@example.com"

    # Status should be 'RENTED' (since all units are rented)
    assert response.status == "RENTED"


@pytest.mark.asyncio
async def test_update_property_admin_success(mocker):
    # Arrange
    property_id = 789
    owner_id = uuid4()
    admin_id = uuid4()
    now = datetime.now(UTC)

    # Mock current_user (admin)
    current_user = User(
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

    # Mock property owner
    property_owner = User(
        id=owner_id,
        email="owner3@example.com",
        first_name="Owner3",
        last_name="User3",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    # Mock property ORM object with updated fields
    property_orm = MagicMock(spec=Property)
    property_orm.id = property_id
    property_orm.name = "Updated Property Name"
    property_orm.address = "789 Oak St"
    property_orm.city = "Adminville"
    property_orm.province = "ProvinceY"
    property_orm.postal_code = "A1D2M3"
    property_orm.property_type = "condo"
    property_orm.description = "Updated description"
    property_orm.year_built = 2015
    property_orm.status = "INACTIVE"
    property_orm.user_id = owner_id
    property_orm.created_at = now
    property_orm.updated_at = now
    property_orm.owner = property_owner
    property_orm.units = []

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
    assert response.name == "Updated Property Name"
    assert response.address == "789 Oak St"
    assert response.city == "Adminville"
    assert response.province == "ProvinceY"
    assert response.postal_code == "A1D2M3"
    assert response.property_type == "condo"
    assert response.description == "Updated description"
    assert response.year_built == 2015
    assert response.status == "INACTIVE"
    assert response.owner is not None
    assert response.owner.id == owner_id
    assert response.owner.email == "owner3@example.com"
    assert response.units == []


@pytest.mark.asyncio
async def test_get_property_not_found(mocker):
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

    # Patch dependencies
    mocker.patch("Backend.api.auth.get_current_user", return_value=current_user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)

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
async def test_delete_property_with_active_leases(mocker):
    # This test is not applicable for get_property endpoint, but included for completeness.
    # The get_property endpoint does not handle deletion or lease logic.
    # We'll assert that attempting to "delete" via get_property does not raise 400.
    property_id = 321
    user_id = uuid4()
    now = datetime.now(UTC)

    current_user = User(
        id=user_id,
        email="user2@example.com",
        first_name="Test2",
        last_name="User2",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    # Mock property ORM object with active leases (irrelevant for get_property)
    property_orm = MagicMock(spec=Property)
    property_orm.id = property_id
    property_orm.name = "Property With Lease"
    property_orm.user_id = user_id
    property_orm.status = "ACTIVE"
    property_orm.owner = current_user
    property_orm.units = []
    property_orm.created_at = now
    property_orm.updated_at = now
    property_orm.address = "Somewhere"
    property_orm.city = "City"
    property_orm.province = "Province"
    property_orm.postal_code = "00000"
    property_orm.property_type = "house"
    property_orm.description = "desc"
    property_orm.year_built = 2020

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.api.auth.get_current_user", return_value=current_user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)

    # Act
    response = await get_property(
        property_id=property_id,
        current_user=current_user,
        session=mock_session
    )

    # Assert: Should succeed, not raise 400
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.id == property_id


@pytest.mark.asyncio
async def test_create_property_without_units_success(mocker):
    # Arrange
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

    # PropertyCreate input with no units
    property_data = PropertyCreate(
        name="No Units Property",
        address="789 NoUnit Ave",
        city="Unitless City",
        province="NoProvince",
        postal_code="N0U1T5",
        property_type="house",
        description="A property without units",
        year_built=2022,
        status=PropertyStatus.ACTIVE,
        units=None
    )

    # Mock the Property ORM object to be returned after creation
    property_orm = MagicMock(spec=Property)
    property_orm.id = 1001
    property_orm.name = property_data.name
    property_orm.address = property_data.address
    property_orm.city = property_data.city
    property_orm.province = property_data.province
    property_orm.postal_code = property_data.postal_code
    property_orm.property_type = property_data.property_type
    property_orm.description = property_data.description
    property_orm.year_built = property_data.year_built
    property_orm.status = property_data.status
    property_orm.user_id = owner_id
    property_orm.created_at = now
    property_orm.updated_at = now
    property_orm.owner = current_user
    property_orm.units = []

    # Mock session and query execution
    mock_session = AsyncMock()
    # session.add, commit, refresh are async, so just awaitable mocks
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    # The select query after creation
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result

    # Patch dependencies
    mocker.patch("Backend.api.auth.get_current_user", return_value=current_user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)
    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act
    response = await create_property(
        property_data=property_data,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.id == property_orm.id
    assert response.name == property_data.name
    assert response.address == property_data.address
    assert response.city == property_data.city
    assert response.province == property_data.province
    assert response.postal_code == property_data.postal_code
    assert response.property_type == property_data.property_type
    assert response.description == property_data.description
    assert response.year_built == property_data.year_built
    assert response.status == property_data.status
    assert response.owner is not None
    assert response.owner.id == owner_id
    assert response.units == []


@pytest.mark.asyncio
async def test_admin_get_all_properties_no_filters(mocker):
    # Arrange
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
    # Mock two properties, owned by different users
    prop1 = MagicMock(spec=Property)
    prop1.id = 1
    prop1.name = "Admin Prop 1"
    prop1.status = PropertyStatus.ACTIVE
    prop1.property_type = "house"
    prop1.user_id = uuid4()
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
    prop2.name = "Admin Prop 2"
    prop2.status = PropertyStatus.INACTIVE
    prop2.property_type = "apartment"
    prop2.user_id = uuid4()
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

    mocker.patch("Backend.api.auth.get_current_user", return_value=admin_user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)

    # Act
    result = await get_properties(
        status_filter=None,
        property_type=None,
        current_user=admin_user,
        session=mock_session
    )

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].name == "Admin Prop 1"
    assert result[1].name == "Admin Prop 2"
    assert result[0].status == PropertyStatus.ACTIVE
    assert result[1].status == PropertyStatus.INACTIVE


@pytest.mark.asyncio
async def test_regular_user_get_own_properties_with_filters(mocker):
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
    # Only one property matches both filters and user
    prop = MagicMock(spec=Property)
    prop.id = 10
    prop.name = "User's Prop"
    prop.status = PropertyStatus.DRAFT
    prop.property_type = "condo"
    prop.user_id = user_id
    prop.address = "UserAddr"
    prop.city = "UserCity"
    prop.province = "UserProv"
    prop.postal_code = "33333"
    prop.description = "desc"
    prop.year_built = 2010
    prop.created_at = now
    prop.updated_at = now

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [prop]
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.api.auth.get_current_user", return_value=user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)

    # Act
    result = await get_properties(
        status_filter=PropertyStatus.DRAFT,
        property_type="condo",
        current_user=user,
        session=mock_session
    )

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].user_id == user_id
    assert result[0].status == PropertyStatus.DRAFT
    assert result[0].property_type == "condo"


@pytest.mark.asyncio
async def test_properties_with_null_status_default_to_active(mocker):
    # Arrange
    user_id = uuid4()
    now = datetime.now(UTC)
    user = User(
        id=user_id,
        email="user2@example.com",
        first_name="User2",
        last_name="Test2",
        is_admin=True,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="ADMIN"
    )
    prop_null_status = MagicMock(spec=Property)
    prop_null_status.id = 20
    prop_null_status.name = "Null Status Prop"
    prop_null_status.status = None
    prop_null_status.property_type = "villa"
    prop_null_status.user_id = user_id
    prop_null_status.address = "Addr"
    prop_null_status.city = "City"
    prop_null_status.province = "Prov"
    prop_null_status.postal_code = "44444"
    prop_null_status.description = "desc"
    prop_null_status.year_built = 2015
    prop_null_status.created_at = now
    prop_null_status.updated_at = now

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [prop_null_status]
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.api.auth.get_current_user", return_value=user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)

    # Act
    result = await get_properties(
        status_filter=None,
        property_type=None,
        current_user=user,
        session=mock_session
    )

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].status == PropertyStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_properties_no_results_with_filters(mocker):
    # Arrange
    user_id = uuid4()
    now = datetime.now(UTC)
    user = User(
        id=user_id,
        email="user3@example.com",
        first_name="User3",
        last_name="Test3",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.api.auth.get_current_user", return_value=user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)

    # Act
    result = await get_properties(
        status_filter=PropertyStatus.ARCHIVED,
        property_type="castle",
        current_user=user,
        session=mock_session
    )

    # Assert
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_properties_database_error(mocker):
    # Arrange
    user_id = uuid4()
    now = datetime.now(UTC)
    user = User(
        id=user_id,
        email="user4@example.com",
        first_name="User4",
        last_name="Test4",
        is_admin=True,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="ADMIN"
    )
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("DB error")

    mocker.patch("Backend.api.auth.get_current_user", return_value=user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)

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


@pytest.mark.asyncio
async def test_get_properties_unauthenticated_access(mocker):
    """
    Simulates an unauthenticated user trying to access the endpoint.
    FastAPI's dependency injection would normally handle this before the function is called.
    """
    # Arrange
    mocker.patch("Backend.api.auth.get_current_user",
                 side_effect=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"))
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        # This simulates the framework trying to resolve the dependency
        from Backend.api.auth import get_current_user
        await get_current_user()

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_update_property_no_data_provided(mocker):
    # This test is not applicable for get_property endpoint, but included for completeness.
    # The get_property endpoint does not handle updates or require update data.
    # We'll assert that calling get_property does not raise 400 for missing update data.
    property_id = 654
    user_id = uuid4()
    now = datetime.now(UTC)

    current_user = User(
        id=user_id,
        email="user3@example.com",
        first_name="Test3",
        last_name="User3",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    property_orm = MagicMock(spec=Property)
    property_orm.id = property_id
    property_orm.name = "No Update Data Property"
    property_orm.user_id = user_id
    property_orm.status = "ACTIVE"
    property_orm.owner = current_user
    property_orm.units = []
    property_orm.created_at = now
    property_orm.updated_at = now
    property_orm.address = "No Update"
    property_orm.city = "NoUpdateCity"
    property_orm.province = "NoUpdateProvince"
    property_orm.postal_code = "11111"
    property_orm.property_type = "villa"
    property_orm.description = "desc"
    property_orm.year_built = 2018

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.api.auth.get_current_user", return_value=current_user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)

    # Act
    response = await get_property(
        property_id=property_id,
        current_user=current_user,
        session=mock_session
    )

    # Assert: Should succeed, not raise 400
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.id == property_id


@pytest.mark.asyncio
async def test_create_property_with_units_detailed_success(mocker):
    # Arrange
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
    property_data = PropertyCreate(
        name="Test Property",
        address="123 Main St",
        city="Testville",
        province="TestState",
        postal_code="T3S7C0",
        property_type="residential",
        description="A test property",
        year_built=2000,
        status=PropertyStatus.ACTIVE,
        units=["101", "102", "201"]
    )

    # Mock ORM property and units
    property_orm = MagicMock(spec=Property)
    property_orm.id = 1
    property_orm.name = property_data.name
    property_orm.address = property_data.address
    property_orm.city = property_data.city
    property_orm.province = property_data.province
    property_orm.postal_code = property_data.postal_code
    property_orm.property_type = property_data.property_type
    property_orm.description = property_data.description
    property_orm.year_built = property_data.year_built
    property_orm.status = property_data.status
    property_orm.user_id = owner_id
    property_orm.created_at = now
    property_orm.updated_at = now
    property_orm.owner = current_user

    # Mock units
    units = []
    if property_data.units:
        for idx, unit_name in enumerate(property_data.units, start=1):
            unit = MagicMock(spec=PropertyUnit)
            unit.id = idx
            unit.name = unit_name
            unit.floor = int(unit_name[0]) if unit_name[0].isdigit() else 0
            unit.is_rented = False
            unit.created_at = now
            unit.updated_at = now
            unit.description = ""
            unit.monthly_rent = None
            unit.tenant = None
            units.append(unit)
    property_orm.units = units

    # Mock session and query execution
    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.api.auth.get_current_user", return_value=current_user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)
    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act
    response = await create_property(
        property_data=property_data,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.name == property_data.name
    assert response.owner is not None
    assert response.owner.id == owner_id
    assert len(response.units) == 3
    if property_data.units:
        assert {u.name for u in response.units} == set(property_data.units)
    for unit in response.units:
        assert unit.is_rented is False
        assert unit.floor == int(unit.name[0]) if unit.name[0].isdigit() else 0


@pytest.mark.asyncio
async def test_create_property_missing_required_fields():
    # Missing required field 'name' should raise a validation error
    with pytest.raises(ValidationError):
        PropertyCreate(
            name="",
            address="123 Main St",
            city="Testville",
            province="TestState",
            postal_code="T3S7C0",
            property_type="residential",
            description="A test property",
            year_built=2000,
            status=PropertyStatus.ACTIVE,
            units=None
        )


@pytest.mark.asyncio
async def test_create_property_database_commit_failure(mocker):
    # Arrange
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
    property_data = PropertyCreate(
        name="Fail Property",
        address="123 Main St",
        city="Testville",
        province="TestState",
        postal_code="T3S7C0",
        property_type="residential",
        description="A test property",
        year_built=2000,
        status=PropertyStatus.ACTIVE,
        units=None
    )

    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock(side_effect=Exception("DB commit failed"))
    mock_session.refresh = AsyncMock()
    mock_session.rollback = AsyncMock()
    mocker.patch("Backend.api.auth.get_current_user", return_value=current_user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)
    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_property(
            property_data=property_data,
            current_user=current_user,
            session=mock_session
        )
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to create property" in str(exc_info.value.detail)
    mock_session.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_create_property_response_structure(mocker):
    # Arrange
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
    property_data = PropertyCreate(
        name="Test Property",
        address="123 Main St",
        city="Testville",
        province="TestState",
        postal_code="T3S7C0",
        property_type="residential",
        description="A test property",
        year_built=2000,
        status=PropertyStatus.ACTIVE,
        units=["101", "102"]
    )

    # Mock ORM property and units
    property_orm = MagicMock(spec=Property)
    property_orm.id = 1
    property_orm.name = property_data.name
    property_orm.address = property_data.address
    property_orm.city = property_data.city
    property_orm.province = property_data.province
    property_orm.postal_code = property_data.postal_code
    property_orm.property_type = property_data.property_type
    property_orm.description = property_data.description
    property_orm.year_built = property_data.year_built
    property_orm.status = property_data.status
    property_orm.user_id = owner_id
    property_orm.created_at = now
    property_orm.updated_at = now
    property_orm.owner = current_user

    # Mock units
    units = []
    if property_data.units:
        for idx, unit_name in enumerate(property_data.units, start=1):
            unit = MagicMock(spec=PropertyUnit)
            unit.id = idx
            unit.name = unit_name
            unit.floor = int(unit_name[0]) if unit_name[0].isdigit() else 0
            unit.is_rented = False
            unit.created_at = now
            unit.updated_at = now
            unit.description = ""
            unit.monthly_rent = None
            unit.tenant = None
            units.append(unit)
        property_orm.units = units

    # Mock session and query execution
    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.api.auth.get_current_user", return_value=current_user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)
    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act
    response = await create_property(
        property_data=property_data,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.owner is not None
    assert response.owner.id == owner_id
    assert response.owner.email == "owner@example.com"
    assert isinstance(response.units, list)
    assert len(response.units) == 2
    if property_data.units:
        for unit_resp, unit_name in zip(response.units, property_data.units):
            assert unit_resp.name == unit_name
            assert hasattr(unit_resp, "is_rented")
            assert hasattr(unit_resp, "floor")


@pytest.mark.asyncio
async def test_unit_floor_assignment_from_name(mocker):
    """
    Units are assigned correct floor numbers based on unit names.
    """
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
    # Unit names: some start with digits, some do not
    unit_names = ["101", "201", "A1", "B2", "3C", "004", "Penthouse"]
    expected_floors = [1, 2, 0, 0, 3, 0, 0]

    property_data = PropertyCreate(
        name="Floor Test Property",
        address="123 Main St",
        city="Testville",
        province="TestState",
        postal_code="T3S7C0",
        property_type="residential",
        description="Testing floor assignment",
        year_built=2023,
        status=PropertyStatus.ACTIVE,
        units=unit_names
    )

    # Mock ORM property and units
    property_orm = MagicMock()
    property_orm.id = 42
    property_orm.name = property_data.name
    property_orm.address = property_data.address
    property_orm.city = property_data.city
    property_orm.province = property_data.province
    property_orm.postal_code = property_data.postal_code
    property_orm.property_type = property_data.property_type
    property_orm.description = property_data.description
    property_orm.year_built = property_data.year_built
    property_orm.status = property_data.status
    property_orm.user_id = owner_id
    property_orm.created_at = now
    property_orm.updated_at = now
    property_orm.owner = current_user

    # Create units with expected floor assignments
    units = []
    for idx, (unit_name, expected_floor) in enumerate(zip(unit_names, expected_floors), start=1):
        unit = MagicMock(spec=PropertyUnit)
        unit.id = idx
        unit.name = unit_name
        unit.floor = expected_floor
        unit.is_rented = False
        unit.created_at = now
        unit.updated_at = now
        unit.description = ""
        unit.monthly_rent = None
        unit.tenant = None
        units.append(unit)
    property_orm.units = units

    # Mock session and query execution
    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.api.auth.get_current_user", return_value=current_user)
    mocker.patch("Backend.database.get_session", return_value=mock_session)
    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act
    response = await create_property(
        property_data=property_data,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert len(response.units) == len(unit_names)
    for unit_resp, unit_name, expected_floor in zip(response.units, unit_names, expected_floors):
        assert unit_resp.name == unit_name
        assert unit_resp.floor == expected_floor