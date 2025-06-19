"""
Unit tests for CREATE operations in the properties API endpoint.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, UTC
from pydantic import ValidationError

from fastapi import HTTPException, status

from Backend.api.properties.router import create_property
from Backend.api.properties.schemas import PropertyCreate, PropertyDetailResponse_Standalone
from Backend.models.property import Property, PropertyUnit
from Backend.models.user import User
from Backend.models.enums import PropertyStatus
from Backend.models.property import PropertyType


# =============================================================================
# CREATE PROPERTY TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_create_property_success_without_units(mocker):
    """Test successful property creation without units."""
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
        name="New Property",
        address="123 New St",
        city="New City",
        province="New Province",
        postal_code="N3W123",
        property_type=PropertyType.RESIDENTIAL,
        description="Brand new property",
        year_built=2023,
        status=PropertyStatus.ACTIVE,
        units=None
    )
    
    # Mock the created property
    created_property = MagicMock(spec=Property)
    created_property.id = 1
    created_property.name = property_data.name
    created_property.address = property_data.address
    created_property.city = property_data.city
    created_property.province = property_data.province
    created_property.postal_code = property_data.postal_code
    created_property.property_type = property_data.property_type
    created_property.description = property_data.description
    created_property.year_built = property_data.year_built
    created_property.status = property_data.status
    created_property.user_id = owner_id
    created_property.created_at = now
    created_property.updated_at = now
    created_property.owner = current_user
    created_property.units = []

    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = created_property
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act
    response = await create_property(
        property_data=property_data,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.id == 1
    assert response.name == "New Property"
    assert response.owner is not None
    assert response.owner.id == owner_id
    assert response.units == []
    assert response.status == PropertyStatus.ACTIVE  # No units, so keeps original status

@pytest.mark.asyncio
async def test_create_property_with_units_status_derivation(mocker):
    """Test property creation with units derives VACANT status."""
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
        name="Property With Units",
        address="456 Unit St",
        city="Unit City",
        province="Unit Province",
        postal_code="U1N1T5",
        property_type=PropertyType.RESIDENTIAL,
        description="Property with multiple units",
        year_built=2023,
        status=PropertyStatus.ACTIVE,  # Will be overridden by derivation
        units=["101", "201", "301"]
    )

    # Mock units
    units = []
    for idx, unit_name in enumerate(property_data.units or [], start=1):
        unit = MagicMock(spec=PropertyUnit)
        unit.id = idx
        unit.name = unit_name
        unit.floor = int(unit_name[0])  # Extract floor from unit name
        unit.is_rented = False  # All vacant
        unit.tenant = None
        unit.description = ""
        unit.size = None
        unit.monthly_rent = None
        unit.bedrooms = None
        unit.bathrooms = None
        unit.created_at = now
        unit.updated_at = now
        units.append(unit)
    
    # Mock the created property
    created_property = MagicMock(spec=Property)
    created_property.id = 2
    created_property.name = property_data.name
    created_property.address = property_data.address
    created_property.city = property_data.city
    created_property.province = property_data.province
    created_property.postal_code = property_data.postal_code
    created_property.property_type = property_data.property_type
    created_property.description = property_data.description
    created_property.year_built = property_data.year_built
    created_property.status = property_data.status
    created_property.user_id = owner_id
    created_property.created_at = now
    created_property.updated_at = now
    created_property.owner = current_user
    created_property.units = units
    
    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = created_property
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act
    response = await create_property(
        property_data=property_data,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.id == 2
    assert len(response.units) == 3
    assert all(not unit.is_rented for unit in response.units)
    assert response.status == PropertyStatus.VACANT  # All units vacant


@pytest.mark.asyncio
async def test_create_property_floor_assignment_logic(mocker):
    """Test that units get correct floor assignment based on name."""
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

    # Unit names with various patterns
    unit_names = ["101", "201", "301", "Basement", "PH", "A1", "2B"]
    expected_floors = [1, 2, 3, 0, 0, 0, 2]  # Expected floor assignments
    
    property_data = PropertyCreate(
        name="Floor Test Property",
        address="789 Floor St",
        city="Floor City",
        province="Floor Province",
        postal_code="F1O0R5",
        property_type=PropertyType.RESIDENTIAL,
        units=unit_names
    )
    
    # Mock units with expected floor assignments
    units = []
    for idx, (unit_name, expected_floor) in enumerate(zip(unit_names, expected_floors), start=1):
        unit = MagicMock(spec=PropertyUnit)
        unit.id = idx
        unit.name = unit_name
        unit.floor = expected_floor
        unit.is_rented = False
        unit.tenant = None
        unit.description = ""
        unit.size = None
        unit.monthly_rent = None
        unit.bedrooms = None
        unit.bathrooms = None
        unit.created_at = now
        unit.updated_at = now
        units.append(unit)
    
    created_property = MagicMock(spec=Property)
    created_property.id = 3
    created_property.name = property_data.name
    created_property.units = units
    created_property.owner = current_user
    created_property.user_id = owner_id
    created_property.status = PropertyStatus.ACTIVE
    created_property.address = property_data.address
    created_property.city = property_data.city
    created_property.province = property_data.province
    created_property.postal_code = property_data.postal_code
    created_property.property_type = property_data.property_type
    created_property.description = property_data.description
    created_property.year_built = property_data.year_built
    created_property.created_at = now
    created_property.updated_at = now
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = created_property
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act
    response = await create_property(
        property_data=property_data,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert len(response.units) == len(unit_names)
    for unit, expected_floor in zip(response.units, expected_floors):
        assert unit.floor == expected_floor


@pytest.mark.asyncio
async def test_create_property_validation_error():
    """Test validation error for invalid property data."""
    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        PropertyCreate(
            name="",  # Empty name should fail
            address="123 Test St",
            city="Test City",
            province="Test Province",
            postal_code="12345",
            property_type=PropertyType.RESIDENTIAL
        )
    
    errors = exc_info.value.errors()
    assert any("name must not be empty" in str(error) for error in errors)


@pytest.mark.asyncio
async def test_create_property_database_error(mocker):
    """Test error handling for database commit failure."""
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
        address="123 Test St",
        city="Test City",
        province="Test Province",
        postal_code="12345",
        property_type=PropertyType.RESIDENTIAL
    )

    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock(side_effect=Exception("Database error"))
    mock_session.rollback = AsyncMock()
    
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
async def test_create_property_with_mixed_unit_names(mocker):
    """Test property creation with units having mixed naming patterns."""
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
        name="Mixed Units Property",
        address="999 Mixed St",
        city="Mixed City",
        province="Mixed Province",
        postal_code="M1X3D",
        property_type=PropertyType.COMMERCIAL,
        description="Property with mixed unit naming",
        year_built=2024,
        units=["Store Front", "Office 201", "Suite 3A", "Warehouse"]
    )

    # Mock units with appropriate floor assignments
    units = []
    unit_configs = [
        ("Store Front", 0),   # No digit at start, floor 0
        ("Office 201", 2),    # Starts with 2, floor 2
        ("Suite 3A", 3),      # Starts with 3, floor 3
        ("Warehouse", 0),     # No digit at start, floor 0
    ]
    
    for idx, (unit_name, floor) in enumerate(unit_configs, start=1):
        unit = MagicMock(spec=PropertyUnit)
        unit.id = idx
        unit.name = unit_name
        unit.floor = floor
        unit.is_rented = False
        unit.tenant = None
        unit.description = ""
        unit.size = None
        unit.monthly_rent = None
        unit.bedrooms = None
        unit.bathrooms = None
        unit.created_at = now
        unit.updated_at = now
        units.append(unit)
    
    created_property = MagicMock(spec=Property)
    created_property.id = 4
    created_property.name = property_data.name
    created_property.address = property_data.address
    created_property.city = property_data.city
    created_property.province = property_data.province
    created_property.postal_code = property_data.postal_code
    created_property.property_type = property_data.property_type
    created_property.description = property_data.description
    created_property.year_built = property_data.year_built
    created_property.status = property_data.status
    created_property.user_id = owner_id
    created_property.created_at = now
    created_property.updated_at = now
    created_property.owner = current_user
    created_property.units = units
    
    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = created_property
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act
    response = await create_property(
        property_data=property_data,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.id == 4
    assert len(response.units) == 4
    assert response.property_type == PropertyType.COMMERCIAL
    
    # Verify floor assignments
    assert response.units[0].floor == 0  # Store Front
    assert response.units[1].floor == 2  # Office 201
    assert response.units[2].floor == 3  # Suite 3A
    assert response.units[3].floor == 0  # Warehouse


@pytest.mark.asyncio
async def test_create_property_retrieval_failure(mocker):
    """Test error handling when property retrieval fails after creation."""
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
        name="Retrieval Failure Property",
        address="404 Not Found St",
        city="Error City",
        province="Error Province",
        postal_code="E1R0R",
        property_type=PropertyType.RESIDENTIAL
    )

    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    # Mock retrieval to return None (property not found after creation)
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_property(
            property_data=property_data,
            current_user=current_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Property was created but could not be retrieved" in str(exc_info.value.detail) 