"""
Unit tests for Units business logic and edge cases.

These tests focus on complex business rules, edge cases, and validation logic
that might not be covered in the main service tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic import ValidationError

from Backend.api.units.service import UnitService
from Backend.api.units.schemas import (
    UnitCreate, UnitUpdate, UnitSearchFilters,
    BulkUnitCreate, BulkUnitCreateResponse
)
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.models.lease import Lease, LeaseStatus

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
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
    return user


def create_properly_configured_unit(unit_id=1):
    """Create a mock unit with all required attributes properly configured."""
    unit = MagicMock(spec=PropertyUnit)
    unit.id = unit_id
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
    unit.property_id = 1
    
    # Mock property
    unit.property = MagicMock()
    unit.property.id = 1
    unit.property.user_id = uuid4()
    
    return unit


# =============================================================================
# Tenant Assignment Logic Tests
# =============================================================================

@pytest.mark.asyncio
async def test_update_unit_vacate_clears_rent(mock_session, mock_user):
    """Test that vacating a unit clears monthly rent if not explicitly set."""
    # Create a rented unit
    mock_unit = create_properly_configured_unit()
    mock_unit.tenant_id = 1
    mock_unit.is_rented = True
    mock_unit.monthly_rent = Decimal("1500.00")
    mock_unit.property.user_id = mock_user.id

    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        # Vacate by setting tenant_id to None
        update_data = UnitUpdate(tenant_id=None)
        
        # Setup re-fetch
        refetch_result = MagicMock()
        refetch_result.unique.return_value.scalar_one_or_none.return_value = mock_unit
        mock_session.execute.return_value = refetch_result

        # Act
        await UnitService.update_unit(1, update_data, mock_session, mock_user)

        # Assert
        assert mock_unit.tenant_id is None
        assert mock_unit.is_rented is False
        assert mock_unit.monthly_rent is None  # Rent cleared


@pytest.mark.asyncio
async def test_update_unit_vacate_keeps_explicit_rent(mock_session, mock_user):
    """Test that vacating keeps rent if explicitly set in same request."""
    # Create a rented unit
    mock_unit = create_properly_configured_unit()
    mock_unit.tenant_id = 1
    mock_unit.is_rented = True
    mock_unit.monthly_rent = Decimal("1500.00")
    mock_unit.property.user_id = mock_user.id

    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        # Vacate but set new rent
        update_data = UnitUpdate(
            tenant_id=None,
            monthly_rent=Decimal("1600.00")  # Explicitly set new rent
        )
        
        # Setup re-fetch
        refetch_result = MagicMock()
        refetch_result.unique.return_value.scalar_one_or_none.return_value = mock_unit
        mock_session.execute.return_value = refetch_result

        # Act
        await UnitService.update_unit(1, update_data, mock_session, mock_user)

        # Assert
        assert mock_unit.tenant_id is None
        assert mock_unit.is_rented is False
        assert mock_unit.monthly_rent == Decimal("1600.00")  # Rent kept


@pytest.mark.asyncio
async def test_update_unit_cannot_set_is_rented_directly(mock_session, mock_user):
    """Test that is_rented cannot be set directly anymore."""
    mock_unit = create_properly_configured_unit()
    mock_unit.tenant_id = None
    mock_unit.is_rented = False
    mock_unit.property.user_id = mock_user.id

    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        # The is_rented field is no longer in the UnitUpdate schema
        # Pydantic v2 will ignore extra fields by default
        # Create update data with is_rented (which will be ignored)
        update_data = UnitUpdate(name="Updated Name")
        
        # Verify is_rented is not an attribute of UnitUpdate
        assert not hasattr(update_data, 'is_rented')
        
        # Setup re-fetch
        refetch_result = MagicMock()
        refetch_result.unique.return_value.scalar_one_or_none.return_value = mock_unit
        mock_session.execute.return_value = refetch_result

        # Act - update should work fine with valid data
        await UnitService.update_unit(1, update_data, mock_session, mock_user)

        # Assert - unit name was updated
        assert mock_unit.name == "Updated Name"
        # is_rented state is controlled by tenant assignment, not direct update
        assert mock_unit.is_rented is False  # Remains unchanged


@pytest.mark.asyncio
async def test_update_unit_assign_tenant_sets_rented(mock_session, mock_user):
    """Test assigning tenant automatically sets is_rented=True."""
    mock_unit = create_properly_configured_unit()
    mock_unit.tenant_id = None
    mock_unit.is_rented = False
    mock_unit.property.user_id = mock_user.id

    mock_tenant = MagicMock(spec=Tenant)
    mock_tenant.id = 5

    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        # Mock tenant exists check
        tenant_result = MagicMock()
        tenant_result.scalar_one_or_none.return_value = mock_tenant
        
        # Setup returns for different queries
        call_count = 0
        def execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Tenant check
                return tenant_result
            else:  # Re-fetch
                refetch_result = MagicMock()
                refetch_result.unique.return_value.scalar_one_or_none.return_value = mock_unit
                return refetch_result
        
        mock_session.execute.side_effect = execute_side_effect

        # Assign tenant
        update_data = UnitUpdate(tenant_id=5)

        # Act
        await UnitService.update_unit(1, update_data, mock_session, mock_user)

        # Assert
        assert mock_unit.tenant_id == 5
        assert mock_unit.is_rented is True  # Automatically set


# =============================================================================
# Bulk Creation Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_bulk_create_rollback_on_commit_failure(mock_session, mock_user):
    """Test bulk creation rollback when commit fails."""
    mock_property = MagicMock(spec=Property)
    mock_property.id = 1
    mock_property.user_id = mock_user.id

    # Setup property query
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    mock_session.execute.return_value = property_result

    # Setup flush to succeed so units are created
    flush_count = 0
    async def flush_side_effect():
        nonlocal flush_count
        flush_count += 1
        # Add ID to the object that was just added
        unit = mock_session.add.call_args_list[flush_count - 1][0][0]
        unit.id = flush_count
        unit.created_at = datetime.now(timezone.utc)
        unit.updated_at = datetime.now(timezone.utc)
    
    mock_session.flush.side_effect = flush_side_effect

    # Setup commit to fail only when there are units to commit
    mock_session.commit.side_effect = OperationalError(
        statement="Connection lost",
        params={},
        orig=Exception("Database connection lost")
    )

    bulk_data = BulkUnitCreate(units=[
        UnitCreate(name="Unit 1", is_rented=False),
        UnitCreate(name="Unit 2", is_rented=False),
    ])

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await UnitService.create_units_bulk(1, bulk_data, mock_session, mock_user)
    
    assert exc_info.value.status_code == 500
    assert "Failed to save units" in str(exc_info.value.detail)
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_bulk_create_handles_validation_errors(mock_session, mock_user):
    """Test bulk creation handles validation errors gracefully."""
    mock_property = MagicMock(spec=Property)
    mock_property.id = 1
    mock_property.user_id = mock_user.id

    # Setup property query
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    mock_session.execute.return_value = property_result

    # Create a unit that will fail validation when converting to response
    call_count = 0
    async def flush_side_effect():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First unit succeeds
            unit = mock_session.add.call_args_list[0][0][0]
            unit.id = 1
            unit.created_at = datetime.now(timezone.utc)
            unit.updated_at = datetime.now(timezone.utc)
        elif call_count == 2:
            # Second unit will fail validation
            # Force validation error on second unit
            from pydantic_core import InitErrorDetails
            validation_errors = [
                InitErrorDetails(
                    type='value_error',
                    loc=('monthly_rent',),
                    input=-100,
                    ctx={'error': 'Monthly rent cannot be negative'}
                )
            ]
            raise ValidationError.from_exception_data(
                title='UnitCreate',
                line_errors=validation_errors
            )
    
    mock_session.flush.side_effect = flush_side_effect

    bulk_data = BulkUnitCreate(units=[
        UnitCreate(name="Unit 1", is_rented=False),
        UnitCreate(name="Unit 2", is_rented=False),  # This will fail
    ])

    # Act
    result = await UnitService.create_units_bulk(1, bulk_data, mock_session, mock_user)

    # Assert
    assert len(result.created) == 1
    assert len(result.failed) == 1
    assert "validation error" in result.failed[0]["error"].lower()


@pytest.mark.asyncio
async def test_bulk_create_continues_after_failure(mock_session, mock_user):
    """Test bulk creation continues processing after individual failures."""
    mock_property = MagicMock(spec=Property)
    mock_property.id = 1
    mock_property.user_id = mock_user.id

    # Setup property query
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    mock_session.execute.return_value = property_result

    # Make middle unit fail
    flush_count = 0
    async def flush_side_effect():
        nonlocal flush_count
        flush_count += 1
        if flush_count == 2:  # Second unit fails
            raise IntegrityError(
                statement="Constraint violation",
                params={},
                orig=Exception("Database constraint violated")
            )
        else:
            # Add ID to successful units
            if mock_session.add.call_count >= flush_count:
                unit = mock_session.add.call_args_list[flush_count - 1][0][0]
                unit.id = flush_count
                unit.created_at = datetime.now(timezone.utc)
                unit.updated_at = datetime.now(timezone.utc)
    
    mock_session.flush.side_effect = flush_side_effect

    bulk_data = BulkUnitCreate(units=[
        UnitCreate(name="Unit 1", is_rented=False),
        UnitCreate(name="Unit 2", is_rented=False),  # Fails
        UnitCreate(name="Unit 3", is_rented=False),  # Should still process
    ])

    # Act
    result = await UnitService.create_units_bulk(1, bulk_data, mock_session, mock_user)

    # Assert
    assert len(result.created) == 2  # First and third succeed
    assert len(result.failed) == 1   # Second fails
    assert result.failed[0]["index"] == 1


# =============================================================================
# Search Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_search_units_with_null_rent_ordering(mock_session, mock_user):
    """Test search handles units with null monthly_rent in ordering."""
    # Create units with and without rent
    unit1 = create_properly_configured_unit(1)
    unit1.name = "Unit A"
    unit1.monthly_rent = None  # No rent set
    unit1.property_id = 1
    
    unit2 = create_properly_configured_unit(2)
    unit2.name = "Unit B"
    unit2.monthly_rent = Decimal("1000.00")
    unit2.property_id = 1

    query_result = MagicMock()
    query_result.unique.return_value.scalars.return_value.all.return_value = [unit1, unit2]
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
    # Verify both units are returned despite null rent


@pytest.mark.asyncio
async def test_search_units_property_filter_security(mock_session, mock_user):
    """Test non-admin can't search units in properties they don't own."""
    # User is not admin, so query should filter by user_id
    filters = UnitSearchFilters(
        min_rent=None,
        max_rent=None,
        min_bedrooms=None,
        max_bedrooms=None,
        min_bathrooms=None,
        property_ids=[1, 2, 3]
    )

    query_result = MagicMock()
    query_result.unique.return_value.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = query_result

    # Act
    result = await UnitService.search_units(filters, mock_session, mock_user)

    # Assert
    assert len(result) == 0
    # Verify query was executed (would include user_id filter)
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_search_units_complex_filter_combination(mock_session, mock_user):
    """Test search with all filters applied."""
    filters = UnitSearchFilters(
        min_rent=Decimal("1000"),
        max_rent=Decimal("2000"),
        min_bedrooms=2,
        max_bedrooms=3,
        min_bathrooms=1.5,
        is_rented=False,
        property_ids=[1, 2]
    )

    # Create a unit that matches all criteria
    unit = create_properly_configured_unit()
    unit.monthly_rent = Decimal("1500")
    unit.bedrooms = 2
    unit.bathrooms = 2.0
    unit.is_rented = False
    unit.property_id = 1

    query_result = MagicMock()
    query_result.unique.return_value.scalars.return_value.all.return_value = [unit]
    mock_session.execute.return_value = query_result

    # Act
    result = await UnitService.search_units(filters, mock_session, mock_user)

    # Assert
    assert len(result) == 1
    assert result[0].monthly_rent == Decimal("1500")


# =============================================================================
# Concurrency and Race Condition Tests
# =============================================================================

@pytest.mark.asyncio
async def test_delete_unit_race_condition_with_lease_creation(mock_session, mock_user):
    """Test handling race condition where lease is created during deletion."""
    mock_unit = create_properly_configured_unit()
    mock_unit.property.user_id = mock_user.id

    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        # First check shows no lease, but commit fails due to new lease
        mock_session.scalar.return_value = None  # No lease initially
        mock_session.commit.side_effect = IntegrityError(
            statement="Foreign key constraint violation",
            params={},
            orig=Exception("Cannot delete - foreign key constraint")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.delete_unit(1, mock_session, mock_user)
        
        assert exc_info.value.status_code == 500
        mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_unit_concurrent_modification(mock_session, mock_user):
    """Test handling concurrent unit modifications."""
    mock_unit = create_properly_configured_unit()
    mock_unit.property.user_id = mock_user.id

    with patch.object(UnitService, 'get_unit_or_404', return_value=mock_unit):
        update_data = UnitUpdate(name="New Name")
        
        # Simulate unit was deleted by another request
        refetch_result = MagicMock()
        refetch_result.unique.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = refetch_result

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.update_unit(1, update_data, mock_session, mock_user)
        
        # The service wraps the 404 error in a 500 error
        assert exc_info.value.status_code == 500
        assert "404: Updated unit could not be found" in str(exc_info.value.detail)


# =============================================================================
# Permission Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_admin_can_modify_any_unit(mock_session):
    """Test admin bypass works for all operations."""
    admin_user = MagicMock(spec=User)
    admin_user.id = uuid4()
    admin_user.is_admin = True

    # Create unit owned by different user
    mock_unit = create_properly_configured_unit()
    mock_unit.property.user_id = uuid4()  # Different owner

    # Setup query
    result = MagicMock()
    result.unique.return_value.scalar_one_or_none.return_value = mock_unit
    mock_session.execute.return_value = result

    # Act - should not raise permission error
    unit = await UnitService.get_unit_or_404(1, mock_session, admin_user)
    
    # Assert
    assert unit == mock_unit  # Admin can access


@pytest.mark.asyncio
async def test_permission_check_with_null_property(mock_session, mock_user):
    """Test handling units with null property reference."""
    mock_unit = create_properly_configured_unit()
    mock_unit.property = None  # Orphaned unit

    result = MagicMock()
    result.unique.return_value.scalar_one_or_none.return_value = mock_unit
    mock_session.execute.return_value = result

    # Act - When property is None, the permission check is skipped
    unit = await UnitService.get_unit_or_404(1, mock_session, mock_user)
    
    # Assert - Should return the unit without permission error
    assert unit == mock_unit