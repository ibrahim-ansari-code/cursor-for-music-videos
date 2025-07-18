"""
Unit tests for the PropertyService class and service layer logic.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, UTC
from decimal import Decimal

from Backend.api.properties.service import PropertyService
from Backend.api.properties.schemas import PropertyDetailResponse_Standalone
from Backend.models.property import Property, PropertyUnit, PropertyType
from Backend.models.user import User
from Backend.models.enums import PropertyStatus


# =============================================================================
# SERVICE LAYER TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_property_service_derive_status_logic():
    """Test the status derivation logic directly."""
    now = datetime.now(UTC)
    
    # Test 1: No units - should keep original status
    property_no_units = MagicMock(spec=Property)
    property_no_units.status = PropertyStatus.ACTIVE
    property_no_units.units = []
    
    status = PropertyService._derive_property_status(property_no_units)
    assert status == PropertyStatus.ACTIVE
    
    # Test 2: All units vacant - should be VACANT
    unit1 = MagicMock(spec=PropertyUnit)
    unit1.is_rented = False
    unit2 = MagicMock(spec=PropertyUnit)
    unit2.is_rented = False
    
    property_all_vacant = MagicMock(spec=Property)
    property_all_vacant.status = PropertyStatus.ACTIVE
    property_all_vacant.units = [unit1, unit2]
    
    status = PropertyService._derive_property_status(property_all_vacant)
    assert status == PropertyStatus.VACANT
    
    # Test 3: All units rented - should be RENTED
    unit3 = MagicMock(spec=PropertyUnit)
    unit3.is_rented = True
    unit4 = MagicMock(spec=PropertyUnit)
    unit4.is_rented = True
    
    property_all_rented = MagicMock(spec=Property)
    property_all_rented.status = PropertyStatus.ACTIVE
    property_all_rented.units = [unit3, unit4]
    
    status = PropertyService._derive_property_status(property_all_rented)
    assert status == PropertyStatus.RENTED
    
    # Test 4: Mixed occupancy - should be PARTIALLY_RENTED
    property_mixed = MagicMock(spec=Property)
    property_mixed.status = PropertyStatus.ACTIVE
    property_mixed.units = [unit1, unit3]  # One vacant, one rented
    
    status = PropertyService._derive_property_status(property_mixed)
    assert status == PropertyStatus.PARTIALLY_RENTED


@pytest.mark.asyncio
async def test_property_service_error_handling_in_unit_serialization(mocker):
    """Test that unit serialization errors are handled gracefully."""
    # Arrange
    property_id = 123
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
    
    # Mock unit that will fail validation
    # We'll patch UnitResponse.model_validate to raise an exception for this specific unit
    bad_unit = MagicMock(spec=PropertyUnit)
    bad_unit.id = 1
    bad_unit.name = "Bad Unit"
    bad_unit.monthly_rent = "invalid_decimal"  # This will be caught by calculate_property_stats
    bad_unit.is_rented = False
    bad_unit.description = None
    bad_unit.size = None
    bad_unit.bedrooms = None
    bad_unit.bathrooms = None
    bad_unit.floor = None
    bad_unit.tenant_id = None
    bad_unit.tenant = None
    bad_unit.property_id = property_id
    bad_unit.created_at = now
    bad_unit.updated_at = now
    
    property_orm = MagicMock(spec=Property)
    property_orm.id = property_id
    property_orm.user_id = owner_id
    property_orm.owner = current_user
    property_orm.units = [bad_unit]
    property_orm.status = PropertyStatus.ACTIVE
    property_orm.name = "Test Property"
    property_orm.address = "123 Test St"
    property_orm.city = "Test City"
    property_orm.province = "Test Province"
    property_orm.postal_code = "12345"
    property_orm.property_type = PropertyType.RESIDENTIAL
    property_orm.description = "Test"
    property_orm.year_built = 2020
    property_orm.created_at = now
    property_orm.updated_at = now

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = property_orm
    mock_session.execute.return_value = mock_result
    
    # Mock logger to verify error is logged
    mock_logger = mocker.patch("Backend.api.properties.service.logger")
    
    # Patch UnitResponse.model_validate to fail for our bad unit
    original_validate = mocker.patch("Backend.api.properties.schemas.UnitResponse.model_validate")
    def mock_validate(obj):
        if hasattr(obj, 'id') and obj.id == 1:  # Our bad unit
            raise ValueError("Unit validation failed")
        # For any other unit, return a mock response
        mock_response = MagicMock()
        for attr in ['id', 'property_id', 'name', 'description', 'size', 
                     'monthly_rent', 'is_rented', 'bedrooms', 'bathrooms', 
                     'floor', 'tenant', 'created_at', 'updated_at']:
            setattr(mock_response, attr, getattr(obj, attr, None))
        return mock_response
    original_validate.side_effect = mock_validate

    # Act
    response = await PropertyService.get_property(property_id, current_user, mock_session)

    # Assert - Should handle error gracefully and skip bad unit
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert len(response.units) == 0  # Bad unit was skipped
    mock_logger.error.assert_called()  # Error was logged
    # The warning about invalid monthly_rent won't be logged because
    # the unit fails validation before reaching the stats calculation


@pytest.mark.asyncio
async def test_property_service_derive_status_edge_cases():
    """Test edge cases for status derivation logic."""
    # Test with None status
    property_none_status = MagicMock(spec=Property)
    property_none_status.status = None
    property_none_status.units = []
    
    status = PropertyService._derive_property_status(property_none_status)
    assert status == PropertyStatus.ACTIVE  # Should default to ACTIVE
    
    # Test with empty units list
    property_empty_units = MagicMock(spec=Property)
    property_empty_units.status = PropertyStatus.INACTIVE
    property_empty_units.units = []
    
    status = PropertyService._derive_property_status(property_empty_units)
    assert status == PropertyStatus.INACTIVE  # Should keep original status
    
    # Test with single vacant unit
    single_unit = MagicMock(spec=PropertyUnit)
    single_unit.is_rented = False
    
    property_single_vacant = MagicMock(spec=Property)
    property_single_vacant.status = PropertyStatus.ACTIVE
    property_single_vacant.units = [single_unit]
    
    status = PropertyService._derive_property_status(property_single_vacant)
    assert status == PropertyStatus.VACANT
    
    # Test with single rented unit
    single_rented_unit = MagicMock(spec=PropertyUnit)
    single_rented_unit.is_rented = True
    
    property_single_rented = MagicMock(spec=Property)
    property_single_rented.status = PropertyStatus.ACTIVE
    property_single_rented.units = [single_rented_unit]
    
    status = PropertyService._derive_property_status(property_single_rented)
    assert status == PropertyStatus.RENTED


@pytest.mark.asyncio
async def test_property_service_derive_status_with_different_statuses():
    """Test status derivation with different initial property statuses."""
    # Test DRAFT property with units
    unit_vacant = MagicMock(spec=PropertyUnit)
    unit_vacant.is_rented = False
    
    property_draft = MagicMock(spec=Property)
    property_draft.status = PropertyStatus.DRAFT
    property_draft.units = [unit_vacant]
    
    status = PropertyService._derive_property_status(property_draft)
    assert status == PropertyStatus.VACANT  # Should derive based on units
    
    # Test ARCHIVED property with mixed units
    unit_rented = MagicMock(spec=PropertyUnit)
    unit_rented.is_rented = True
    
    property_archived = MagicMock(spec=Property)
    property_archived.status = PropertyStatus.ARCHIVED
    property_archived.units = [unit_vacant, unit_rented]
    
    status = PropertyService._derive_property_status(property_archived)
    assert status == PropertyStatus.PARTIALLY_RENTED  # Should derive based on units
    
    # Test INACTIVE property with no units
    property_inactive = MagicMock(spec=Property)
    property_inactive.status = PropertyStatus.INACTIVE
    property_inactive.units = []
    
    status = PropertyService._derive_property_status(property_inactive)
    assert status == PropertyStatus.INACTIVE  # Should keep original when no units


@pytest.mark.asyncio
async def test_property_service_multiple_units_percentage_calculation():
    """Test status derivation with various percentages of occupied units."""
    # Create units
    vacant_units = [MagicMock(spec=PropertyUnit, is_rented=False) for _ in range(5)]
    rented_units = [MagicMock(spec=PropertyUnit, is_rented=True) for _ in range(5)]
    
    # Test 0% occupied (all vacant)
    property_0_percent = MagicMock(spec=Property)
    property_0_percent.status = PropertyStatus.ACTIVE
    property_0_percent.units = vacant_units[:5]  # 5 vacant units
    
    status = PropertyService._derive_property_status(property_0_percent)
    assert status == PropertyStatus.VACANT
    
    # Test 20% occupied
    property_20_percent = MagicMock(spec=Property)
    property_20_percent.status = PropertyStatus.ACTIVE
    property_20_percent.units = rented_units[:1] + vacant_units[:4]  # 1 rented, 4 vacant
    
    status = PropertyService._derive_property_status(property_20_percent)
    assert status == PropertyStatus.PARTIALLY_RENTED
    
    # Test 50% occupied
    property_50_percent = MagicMock(spec=Property)
    property_50_percent.status = PropertyStatus.ACTIVE
    property_50_percent.units = rented_units[:2] + vacant_units[:2]  # 2 rented, 2 vacant
    
    status = PropertyService._derive_property_status(property_50_percent)
    assert status == PropertyStatus.PARTIALLY_RENTED
    
    # Test 80% occupied
    property_80_percent = MagicMock(spec=Property)
    property_80_percent.status = PropertyStatus.ACTIVE
    property_80_percent.units = rented_units[:4] + vacant_units[:1]  # 4 rented, 1 vacant
    
    status = PropertyService._derive_property_status(property_80_percent)
    assert status == PropertyStatus.PARTIALLY_RENTED
    
    # Test 100% occupied (all rented)
    property_100_percent = MagicMock(spec=Property)
    property_100_percent.status = PropertyStatus.ACTIVE
    property_100_percent.units = rented_units[:5]  # 5 rented units
    
    status = PropertyService._derive_property_status(property_100_percent)
    assert status == PropertyStatus.RENTED


def test_unit_sorting_logic_with_none_ids():
    """Test the unit sorting logic handles None IDs correctly."""
    # Create simple objects to test the sorting logic
    class MockUnit:
        def __init__(self, id, name):
            self.id = id
            self.name = name
    
    units = [
        MockUnit(3, "Unit 3"),
        MockUnit(None, "Unit None"),
        MockUnit(1, "Unit 1"),
        MockUnit(2, "Unit 2"),
        MockUnit(None, "Unit None 2"),
    ]
    
    # Apply the same sorting logic used in the service
    sorted_units = sorted(units, key=lambda x: x.id or 0)
    
    # Assert the order is correct: None IDs (treated as 0) come first
    assert sorted_units[0].id is None
    assert sorted_units[0].name == "Unit None"
    assert sorted_units[1].id is None
    assert sorted_units[1].name == "Unit None 2"
    assert sorted_units[2].id == 1
    assert sorted_units[3].id == 2
    assert sorted_units[4].id == 3 