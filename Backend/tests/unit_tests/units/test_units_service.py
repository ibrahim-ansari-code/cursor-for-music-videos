"""
Unit tests for the Units service layer.

These tests focus on business logic, database interactions, and service-level
functionality without involving the HTTP layer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic import ValidationError

from Backend.api.units.service import UnitService
from Backend.api.units.schemas import (
    UnitCreate, UnitUpdate, UnitCreateResponse, UnitResponse,
    BulkUnitCreate, BulkUnitCreateResponse, UnitSearchFilters
)
from Backend.models.property import Property, PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.models.lease import Lease, LeaseStatus

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    # Setup common mock behaviors
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.is_admin = False
    user.is_active = True
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "admin@example.com"
    user.is_admin = True
    user.is_active = True
    return user


@pytest.fixture
def mock_property(mock_user):
    """Create a mock property."""
    property_obj = MagicMock(spec=Property)
    property_obj.id = 1
    property_obj.name = "Test Property"
    property_obj.user_id = mock_user.id
    property_obj.units = []
    return property_obj


@pytest.fixture
def mock_unit(mock_property):
    """Create a mock unit."""
    unit = MagicMock(spec=PropertyUnit)
    unit.id = 1
    unit.property_id = mock_property.id
    unit.property = mock_property
    unit.name = "Unit A"
    unit.description = "Test unit"
    unit.size = 1000.0
    unit.monthly_rent = Decimal("1500.00")
    unit.is_rented = False
    unit.bedrooms = 2
    unit.bathrooms = 1.5
    unit.floor = 1
    unit.tenant_id = None
    unit.tenant = None
    unit.created_at = datetime.now(timezone.utc)
    unit.updated_at = datetime.now(timezone.utc)
    return unit


@pytest.fixture
def mock_tenant():
    """Create a mock tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = 1
    tenant.first_name = "John"
    tenant.last_name = "Doe"
    tenant.email = "john.doe@example.com"
    return tenant


def create_mock_unit(unit_id, name, property_id=1):
    """Helper to create a mock unit with proper attributes."""
    unit = MagicMock(spec=PropertyUnit)
    unit.id = unit_id
    unit.property_id = property_id
    unit.name = name
    unit.description = f"Description for {name}"
    unit.size = 1000.0
    unit.monthly_rent = Decimal("1500.00")
    unit.is_rented = False
    unit.bedrooms = 2
    unit.bathrooms = 1.5
    unit.floor = 1
    unit.tenant_id = None
    unit.tenant = None
    unit.created_at = datetime.now(timezone.utc)
    unit.updated_at = datetime.now(timezone.utc)
    
    # Mock property
    unit.property = MagicMock()
    unit.property.id = property_id
    unit.property.user_id = uuid4()
    
    return unit


def create_properly_configured_unit(unit_id, name, property_id=1, tenant=None):
    """Helper to create a fully configured mock unit that will pass Pydantic validation."""
    unit = MagicMock(spec=PropertyUnit)
    
    # Set all basic attributes as real values, not MagicMocks
    unit.id = unit_id
    unit.property_id = property_id
    unit.name = name
    unit.description = f"Description for {name}"
    unit.size = 1000.0
    unit.monthly_rent = Decimal("1500.00")
    unit.is_rented = tenant is not None
    unit.bedrooms = 2
    unit.bathrooms = 1.5
    unit.floor = 1
    unit.tenant_id = tenant.id if tenant else None
    unit.tenant = tenant
    unit.created_at = datetime.now(timezone.utc)
    unit.updated_at = datetime.now(timezone.utc)
    
    # Mock property with real values
    unit.property = MagicMock()
    unit.property.id = property_id
    unit.property.user_id = uuid4()
    unit.property.name = "Test Property"
    
    return unit


# =============================================================================
# get_unit_or_404 Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_unit_or_404_success(mock_session, mock_user, mock_unit):
    """Test successful unit retrieval."""
    # Setup mock query result
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = mock_unit
    mock_session.execute.return_value = mock_result

    # Act
    result = await UnitService.get_unit_or_404(1, mock_session, mock_user)

    # Assert
    assert result == mock_unit
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_unit_or_404_not_found(mock_session, mock_user):
    """Test unit not found raises 404."""
    # Setup mock query result
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await UnitService.get_unit_or_404(999, mock_session, mock_user)
    
    assert exc_info.value.status_code == 404
    assert "Unit not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_unit_or_404_forbidden(mock_session, mock_user, mock_unit):
    """Test unit access forbidden for non-owner."""
    # Setup unit with different owner
    other_user_id = uuid4()
    mock_unit.property.user_id = other_user_id

    # Setup mock query result
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = mock_unit
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await UnitService.get_unit_or_404(1, mock_session, mock_user)
    
    assert exc_info.value.status_code == 403
    assert "permission" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_unit_or_404_admin_bypass(mock_session, mock_admin_user, mock_unit):
    """Test admin can access any unit."""
    # Setup unit with different owner
    other_user_id = uuid4()
    mock_unit.property.user_id = other_user_id

    # Setup mock query result
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = mock_unit
    mock_session.execute.return_value = mock_result

    # Act
    result = await UnitService.get_unit_or_404(1, mock_session, mock_admin_user)

    # Assert
    assert result == mock_unit  # Admin can access


# =============================================================================
# create_unit Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_unit_success(mock_session, mock_user, mock_property):
    """Test successful unit creation."""
    # Setup property query
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    mock_session.execute.return_value = property_result

    # Mock the refresh to add required fields
    def refresh_side_effect(obj):
        obj.id = 1
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
    
    mock_session.refresh.side_effect = refresh_side_effect

    # Unit data
    unit_data = UnitCreate(
        name="New Unit",
        description="A new unit",
        size=1200.0,
        monthly_rent=Decimal("1600.00"),
        is_rented=False,
        bedrooms=2,
        bathrooms=2.0,
        floor=1
    )

    # Act
    result = await UnitService.create_unit(1, unit_data, mock_session, mock_user)

    # Assert
    assert isinstance(result, UnitCreateResponse)
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_unit_property_not_found(mock_session, mock_user):
    """Test unit creation fails when property doesn't exist."""
    # Setup property query to return None
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = property_result

    unit_data = UnitCreate(name="New Unit", is_rented=False)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await UnitService.create_unit(999, unit_data, mock_session, mock_user)
    
    assert exc_info.value.status_code == 404
    assert "Property not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_unit_forbidden(mock_session, mock_user, mock_property):
    """Test unit creation forbidden for non-owner."""
    # Setup property with different owner
    mock_property.user_id = uuid4()
    
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    mock_session.execute.return_value = property_result

    unit_data = UnitCreate(name="New Unit", is_rented=False)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await UnitService.create_unit(1, unit_data, mock_session, mock_user)
    
    assert exc_info.value.status_code == 403
    assert "permission" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_unit_database_error(mock_session, mock_user, mock_property):
    """Test unit creation handles database errors."""
    # Setup property query
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    mock_session.execute.return_value = property_result

    # Setup commit to raise error
    mock_session.commit.side_effect = IntegrityError(
        statement="INSERT INTO property_units ...",
        params={},
        orig=Exception("Database constraint violated")
    )

    unit_data = UnitCreate(name="New Unit", is_rented=False)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await UnitService.create_unit(1, unit_data, mock_session, mock_user)
    
    assert exc_info.value.status_code == 500
    mock_session.rollback.assert_called_once()


# =============================================================================
# update_unit Tests
# =============================================================================

@pytest.mark.asyncio
async def test_update_unit_success(mock_session, mock_user, mock_unit):
    """Test successful unit update."""
    # Mock get_unit_or_404
    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        # Update data
        update_data = UnitUpdate(
            name="Updated Unit",
            monthly_rent=Decimal("1800.00")
        )

        # Setup re-fetch query
        refetch_result = MagicMock()
        refetch_result.unique.return_value.scalar_one_or_none.return_value = mock_unit
        mock_session.execute.return_value = refetch_result

        # Act
        result = await UnitService.update_unit(1, update_data, mock_session, mock_user)

        # Assert
        assert mock_unit.name == "Updated Unit"
        assert mock_unit.monthly_rent == Decimal("1800.00")
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_unit_no_data(mock_session, mock_user, mock_unit):
    """Test update fails with no data provided."""
    # Mock get_unit_or_404
    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        update_data = UnitUpdate()  # No fields set

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.update_unit(1, update_data, mock_session, mock_user)
        
        assert exc_info.value.status_code == 400
        assert "No update data provided" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_update_unit_remove_tenant(mock_session, mock_user, mock_unit):
    """Test removing a tenant from a unit."""
    # Setup unit as rented
    mock_unit.tenant_id = 1
    mock_unit.is_rented = True
    mock_unit.monthly_rent = Decimal("1500.00")

    # Mock get_unit_or_404
    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        update_data = UnitUpdate(tenant_id=None)

        # Setup re-fetch query
        refetch_result = MagicMock()
        refetch_result.unique.return_value.scalar_one_or_none.return_value = mock_unit
        mock_session.execute.return_value = refetch_result

        # Act
        result = await UnitService.update_unit(1, update_data, mock_session, mock_user)

        # Assert
        assert mock_unit.tenant_id is None
        assert mock_unit.is_rented is False
        assert mock_unit.monthly_rent is None  # Should be cleared


@pytest.mark.asyncio
async def test_update_unit_tenant_not_found(mock_session, mock_user, mock_unit):
    """Test update fails when tenant doesn't exist."""
    # Mock get_unit_or_404
    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        # Mock tenant query to return None
        tenant_result = MagicMock()
        tenant_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = tenant_result

        update_data = UnitUpdate(tenant_id=999)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.update_unit(1, update_data, mock_session, mock_user)
        
        assert exc_info.value.status_code == 404
        assert "Tenant with ID 999 not found" in str(exc_info.value.detail)


# =============================================================================
# delete_unit Tests
# =============================================================================

@pytest.mark.asyncio
async def test_delete_unit_success(mock_session, mock_user, mock_unit):
    """Test successful unit deletion."""
    # Mock get_unit_or_404
    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        # Mock lease check query
        mock_session.scalar.return_value = None  # No active lease

        # Act
        await UnitService.delete_unit(1, mock_session, mock_user)

        # Assert
        mock_session.delete.assert_called_once_with(mock_unit)
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_unit_with_active_lease(mock_session, mock_user, mock_unit):
    """Test deletion fails when unit has active lease."""
    # Mock get_unit_or_404
    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        # Mock lease check to return active lease ID
        mock_session.scalar.return_value = 1  # Active lease exists

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.delete_unit(1, mock_session, mock_user)
        
        assert exc_info.value.status_code == 400
        assert "Cannot delete unit with an active lease" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_delete_unit_database_error(mock_session, mock_user, mock_unit):
    """Test deletion handles database errors."""
    # Mock get_unit_or_404
    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        # Mock lease check
        mock_session.scalar.return_value = None
        
        # Setup commit to raise error
        mock_session.commit.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.delete_unit(1, mock_session, mock_user)
        
        assert exc_info.value.status_code == 500
        mock_session.rollback.assert_called_once()


# =============================================================================
# get_unit Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_unit_success(mock_session, mock_user, mock_unit):
    """Test successful single unit retrieval."""
    # Mock get_unit_or_404
    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        # Act
        result = await UnitService.get_unit(1, mock_session, mock_user)

        # Assert
        assert isinstance(result, UnitResponse)
        assert result.id == mock_unit.id
        assert result.name == mock_unit.name


# =============================================================================
# get_units_for_property Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_units_for_property_success(mock_session, mock_user, mock_property):
    """Test successful retrieval of units for a property."""
    # Setup property query
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    
    # Setup units query
    mock_units = [
        create_mock_unit(1, "Unit A"),
        create_mock_unit(2, "Unit B"),
    ]
    units_result = MagicMock()
    units_result.unique.return_value.scalars.return_value.all.return_value = mock_units
    
    # Different results for different queries
    mock_session.execute.side_effect = [property_result, units_result]

    # Act
    result = await UnitService.get_units_for_property(1, mock_session, mock_user)

    # Assert
    assert len(result) == 2
    assert all(isinstance(unit, UnitResponse) for unit in result)


@pytest.mark.asyncio
async def test_get_units_for_property_with_pagination(mock_session, mock_user, mock_property):
    """Test retrieval with pagination."""
    # Setup property query
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    
    # Setup units query
    mock_units = [create_mock_unit(1, "Unit A")]
    units_result = MagicMock()
    units_result.unique.return_value.scalars.return_value.all.return_value = mock_units
    
    mock_session.execute.side_effect = [property_result, units_result]

    # Act
    result = await UnitService.get_units_for_property(1, mock_session, mock_user, skip=10, limit=5)

    # Assert
    assert len(result) == 1
    # Verify query was built with pagination
    assert mock_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_get_units_for_property_not_found(mock_session, mock_user):
    """Test retrieval fails when property doesn't exist."""
    # Setup property query to return None
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = property_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await UnitService.get_units_for_property(999, mock_session, mock_user)
    
    assert exc_info.value.status_code == 404
    assert "Property not found" in str(exc_info.value.detail)


# =============================================================================
# create_units_bulk Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_units_bulk_success(mock_session, mock_user, mock_property):
    """Test successful bulk unit creation."""
    # Setup property query
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    mock_session.execute.return_value = property_result

    # Mock flush to add IDs
    flush_count = 0
    async def flush_side_effect():
        nonlocal flush_count
        flush_count += 1
        # Add ID to the object that was just added
        if mock_session.add.call_count >= flush_count:
            last_call = mock_session.add.call_args_list[flush_count - 1]
            unit = last_call[0][0]
            unit.id = flush_count
            unit.created_at = datetime.now(timezone.utc)
            unit.updated_at = datetime.now(timezone.utc)
    
    mock_session.flush.side_effect = flush_side_effect

    # Bulk data
    bulk_data = BulkUnitCreate(units=[
        UnitCreate(name="Unit 1", is_rented=False),
        UnitCreate(name="Unit 2", is_rented=False),
    ])

    # Act
    result = await UnitService.create_units_bulk(1, bulk_data, mock_session, mock_user)

    # Assert
    assert isinstance(result, BulkUnitCreateResponse)
    assert len(result.created) == 2
    assert len(result.failed) == 0
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_units_bulk_partial_failure(mock_session, mock_user, mock_property):
    """Test bulk creation with some failures."""
    # Setup property query
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    mock_session.execute.return_value = property_result

    # Setup flush to fail on second unit
    flush_call_count = 0
    async def flush_side_effect():
        nonlocal flush_call_count
        flush_call_count += 1
        if flush_call_count == 2:
            raise IntegrityError(
                statement="INSERT INTO property_units ...",
                params={},
                orig=Exception("Duplicate unit name")
            )
        else:
            # Add ID to successful units
            if mock_session.add.call_count >= flush_call_count:
                last_call = mock_session.add.call_args_list[flush_call_count - 1]
                unit = last_call[0][0]
                unit.id = flush_call_count
                unit.created_at = datetime.now(timezone.utc)
                unit.updated_at = datetime.now(timezone.utc)
    
    mock_session.flush.side_effect = flush_side_effect

    # Bulk data
    bulk_data = BulkUnitCreate(units=[
        UnitCreate(name="Unit 1", is_rented=False),
        UnitCreate(name="Unit 1", is_rented=False),  # Duplicate
    ])

    # Act
    result = await UnitService.create_units_bulk(1, bulk_data, mock_session, mock_user)

    # Assert
    assert len(result.created) == 1
    assert len(result.failed) == 1
    assert result.failed[0]["index"] == 1
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_units_bulk_all_fail(mock_session, mock_user, mock_property):
    """Test bulk creation when all units fail."""
    # Setup property query
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    mock_session.execute.return_value = property_result

    # Setup flush to always fail
    mock_session.flush.side_effect = Exception("Database error")

    # Bulk data
    bulk_data = BulkUnitCreate(units=[
        UnitCreate(name="Unit 1", is_rented=False),
        UnitCreate(name="Unit 2", is_rented=False),
    ])

    # Act
    result = await UnitService.create_units_bulk(1, bulk_data, mock_session, mock_user)

    # Assert
    assert len(result.created) == 0
    assert len(result.failed) == 2
    mock_session.commit.assert_not_called()  # Should not commit if all failed


# =============================================================================
# search_units Tests
# =============================================================================

@pytest.mark.asyncio
async def test_search_units_no_filters(mock_session, mock_user):
    """Test searching units without filters."""
    # Setup query result
    mock_units = [
        create_mock_unit(1, "Unit A"),
        create_mock_unit(2, "Unit B"),
    ]
    query_result = MagicMock()
    query_result.unique.return_value.scalars.return_value.all.return_value = mock_units
    mock_session.execute.return_value = query_result

    filters = UnitSearchFilters(
        min_rent=None,
        max_rent=None,
        min_bedrooms=None,
        max_bedrooms=None,
        min_bathrooms=None
    )

    # Act
    result = await UnitService.search_units(filters, mock_session, mock_user)

    # Assert
    assert len(result) == 2
    assert all(isinstance(unit, UnitResponse) for unit in result)


@pytest.mark.asyncio
async def test_search_units_with_rent_filter(mock_session, mock_user):
    """Test searching units with rent range filter."""
    # Setup query result
    mock_unit = create_mock_unit(1, "Unit A")
    mock_unit.monthly_rent = Decimal("1500.00")
    
    query_result = MagicMock()
    query_result.unique.return_value.scalars.return_value.all.return_value = [mock_unit]
    mock_session.execute.return_value = query_result

    filters = UnitSearchFilters(
        min_rent=Decimal("1000"),
        max_rent=Decimal("2000"),
        min_bedrooms=None,
        max_bedrooms=None,
        min_bathrooms=None
    )

    # Act
    result = await UnitService.search_units(filters, mock_session, mock_user)

    # Assert
    assert len(result) == 1
    assert result[0].monthly_rent == Decimal("1500.00")


@pytest.mark.asyncio
async def test_search_units_admin_sees_all(mock_session, mock_admin_user):
    """Test admin users can search all units."""
    # Setup query result with units from different properties
    mock_units = [
        create_mock_unit(1, "Unit A", property_id=1),
        create_mock_unit(2, "Unit B", property_id=2),
        create_mock_unit(3, "Unit C", property_id=3),
    ]
    query_result = MagicMock()
    query_result.unique.return_value.scalars.return_value.all.return_value = mock_units
    mock_session.execute.return_value = query_result

    filters = UnitSearchFilters(
        min_rent=None,
        max_rent=None,
        min_bedrooms=None,
        max_bedrooms=None,
        min_bathrooms=None
    )

    # Act
    result = await UnitService.search_units(filters, mock_session, mock_admin_user)

    # Assert
    assert len(result) == 3  # Admin sees all units


@pytest.mark.asyncio
async def test_search_units_complex_filters(mock_session, mock_user):
    """Test searching with multiple filters."""
    # Setup query result
    mock_unit = create_mock_unit(1, "Unit A")
    mock_unit.monthly_rent = Decimal("1500.00")
    mock_unit.bedrooms = 2
    mock_unit.bathrooms = 1.5
    mock_unit.is_rented = False
    
    query_result = MagicMock()
    query_result.unique.return_value.scalars.return_value.all.return_value = [mock_unit]
    mock_session.execute.return_value = query_result

    filters = UnitSearchFilters(
        min_rent=Decimal("1000"),
        max_rent=Decimal("2000"),
        min_bedrooms=2,
        max_bedrooms=None,
        min_bathrooms=1.5,
        is_rented=False
    )

    # Act
    result = await UnitService.search_units(filters, mock_session, mock_user)

    # Assert
    assert len(result) == 1
    unit = result[0]
    assert unit.monthly_rent == Decimal("1500.00")
    assert unit.bedrooms == 2
    assert unit.bathrooms == 1.5
    assert unit.is_rented is False


# =============================================================================
# GET UNIT LEASE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_unit_lease_success(mock_session, mock_user):
    """Test successfully getting an active lease for a unit."""
    unit_id = 1
    property_id = 1
    
    # Create mock unit
    mock_unit = create_mock_unit(unit_id, "Unit A", property_id=property_id)
    mock_unit.property.user_id = mock_user.id
    
    # Create a mock lease response object
    mock_lease_response = MagicMock()
    mock_lease_response.id = 1
    mock_lease_response.unit_id = unit_id
    mock_lease_response.property_id = property_id
    mock_lease_response.tenant_id = 1
    mock_lease_response.status = LeaseStatus.ACTIVE
    mock_lease_response.monthly_rent = Decimal("1500.00")
    mock_lease_response.start_date = datetime.now(timezone.utc).date()
    mock_lease_response.end_date = datetime.now(timezone.utc).date()
    
    # Setup get_unit_or_404 to return the mock unit
    with patch.object(UnitService, 'get_unit_or_404', new_callable=AsyncMock) as mock_get_unit:
        mock_get_unit.return_value = mock_unit
        
        # Mock the LeaseResponse.model_validate to return our mock lease response
        with patch('Backend.api.leases.schemas.LeaseResponse.model_validate') as mock_validate:
            mock_validate.return_value = mock_lease_response
            
            # Setup lease query
            lease_query_result = MagicMock()
            # Create a mock lease object with the required attributes
            mock_lease = MagicMock()
            mock_lease.id = 1
            mock_lease.unit_id = unit_id
            mock_lease.status = LeaseStatus.ACTIVE
            lease_query_result.unique.return_value.scalar_one_or_none.return_value = mock_lease
            mock_session.execute.return_value = lease_query_result
            
            # Act
            result = await UnitService.get_unit_lease(unit_id, mock_session, mock_user)
            
            # Assert
            assert result == mock_lease_response
            assert result.id == 1
            assert result.unit_id == unit_id
            assert result.status == LeaseStatus.ACTIVE
            mock_get_unit.assert_called_once_with(unit_id, mock_session, mock_user)
            mock_session.execute.assert_called_once()
            mock_validate.assert_called_once_with(mock_lease)


@pytest.mark.asyncio
async def test_get_unit_lease_no_active_lease(mock_session, mock_user):
    """Test getting lease for a unit with no active lease."""
    unit_id = 1
    property_id = 1
    
    # Create mock unit
    mock_unit = create_mock_unit(unit_id, "Unit A", property_id=property_id)
    mock_unit.property.user_id = mock_user.id
    
    # Setup get_unit_or_404 to return the mock unit
    with patch.object(UnitService, 'get_unit_or_404', new_callable=AsyncMock) as mock_get_unit:
        mock_get_unit.return_value = mock_unit
        
        # Setup lease query to return None (no active lease)
        lease_query_result = MagicMock()
        lease_query_result.unique.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = lease_query_result
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.get_unit_lease(unit_id, mock_session, mock_user)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "No active lease found for this unit"
        mock_get_unit.assert_called_once_with(unit_id, mock_session, mock_user)


@pytest.mark.asyncio
async def test_get_unit_lease_unit_not_found(mock_session, mock_user):
    """Test getting lease for a unit that doesn't exist."""
    unit_id = 999
    
    # Setup get_unit_or_404 to raise HTTPException
    with patch.object(UnitService, 'get_unit_or_404', new_callable=AsyncMock) as mock_get_unit:
        mock_get_unit.side_effect = HTTPException(
            status_code=404,
            detail="Unit not found"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.get_unit_lease(unit_id, mock_session, mock_user)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Unit not found"
        mock_get_unit.assert_called_once_with(unit_id, mock_session, mock_user)


@pytest.mark.asyncio
async def test_get_unit_lease_no_permission(mock_session, mock_user):
    """Test getting lease for a unit the user doesn't have permission to access."""
    unit_id = 1
    
    # Setup get_unit_or_404 to raise HTTPException for permission
    with patch.object(UnitService, 'get_unit_or_404', new_callable=AsyncMock) as mock_get_unit:
        mock_get_unit.side_effect = HTTPException(
            status_code=403,
            detail="You don't have permission to access this unit"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.get_unit_lease(unit_id, mock_session, mock_user)
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "You don't have permission to access this unit"
        mock_get_unit.assert_called_once_with(unit_id, mock_session, mock_user) 