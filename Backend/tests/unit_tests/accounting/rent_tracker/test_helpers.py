"""
Unit tests for rent tracker helper functions.
"""
import pytest
from unittest.mock import MagicMock
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

from Backend.api.accounting.rent_tracker.helpers import (
    calculate_month_bounds,
    determine_rent_status,
    get_tenant_display_name,
    get_property_display_name,
    get_unit_display_name,
    calculate_collection_rate,
    calculate_rent_due_date
)
from Backend.api.accounting.rent_tracker.schemas import RentStatus


# =============================================================================
# calculate_month_bounds TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_calculate_month_bounds_current_month():
    """Test calculating bounds for current month when no month/year provided."""
    start, end = calculate_month_bounds(None, None)
    
    # Should use current month/year
    now = date.today()
    expected_start = date(now.year, now.month, 1)
    
    # Calculate last day of month
    if now.month == 12:
        expected_end = date(now.year + 1, 1, 1) - timedelta(days=1)
    else:
        expected_end = date(now.year, now.month + 1, 1) - timedelta(days=1)
    
    assert start.month == expected_start.month
    assert start.year == expected_start.year
    assert start.day == 1
    assert end.month == expected_end.month
    assert end.year == expected_end.year


@pytest.mark.asyncio
async def test_calculate_month_bounds_specific_month():
    """Test calculating bounds for specific month and year."""
    start, end = calculate_month_bounds(3, 2024)
    
    assert start == date(2024, 3, 1)
    assert end == date(2024, 3, 31)


@pytest.mark.asyncio
async def test_calculate_month_bounds_february_leap_year():
    """Test calculating bounds for February in leap year."""
    start, end = calculate_month_bounds(2, 2024)
    
    assert start == date(2024, 2, 1)
    assert end == date(2024, 2, 29)  # 2024 is leap year


@pytest.mark.asyncio
async def test_calculate_month_bounds_february_non_leap_year():
    """Test calculating bounds for February in non-leap year."""
    start, end = calculate_month_bounds(2, 2023)
    
    assert start == date(2023, 2, 1)
    assert end == date(2023, 2, 28)  # 2023 is not leap year


@pytest.mark.asyncio
async def test_calculate_month_bounds_december():
    """Test calculating bounds for December."""
    start, end = calculate_month_bounds(12, 2024)
    
    assert start == date(2024, 12, 1)
    assert end == date(2024, 12, 31)


# =============================================================================
# determine_rent_status TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_determine_rent_status_paid():
    """Test rent status determination for fully paid rent."""
    due_date = date(2024, 1, 1)
    current_date = date(2024, 1, 15)
    monthly_rent = Decimal("1500.00")
    amount_paid = Decimal("1500.00")
    
    status, days_overdue = determine_rent_status(monthly_rent, amount_paid, due_date, current_date)
    
    assert status == RentStatus.PAID
    assert days_overdue is None


@pytest.mark.asyncio
async def test_determine_rent_status_partial():
    """Test rent status determination for partially paid rent."""
    due_date = date(2024, 1, 1)
    current_date = date(2024, 1, 15)  # After due date
    monthly_rent = Decimal("1500.00")
    amount_paid = Decimal("800.00")
    
    status, days_overdue = determine_rent_status(monthly_rent, amount_paid, due_date, current_date)
    
    assert status == RentStatus.PARTIAL
    assert days_overdue == 14  # 14 days overdue


@pytest.mark.asyncio
async def test_determine_rent_status_due():
    """Test rent status determination for unpaid rent before due date."""
    due_date = date(2024, 1, 15)
    current_date = date(2024, 1, 10)  # Before due date
    monthly_rent = Decimal("1500.00")
    amount_paid = Decimal("0.00")
    
    status, days_overdue = determine_rent_status(monthly_rent, amount_paid, due_date, current_date)
    
    assert status == RentStatus.DUE
    assert days_overdue is None


@pytest.mark.asyncio
async def test_determine_rent_status_overdue():
    """Test rent status determination for overdue rent."""
    due_date = date(2024, 1, 1)
    current_date = date(2024, 1, 15)  # 14 days after due date
    monthly_rent = Decimal("1500.00")
    amount_paid = Decimal("0.00")
    
    status, days_overdue = determine_rent_status(monthly_rent, amount_paid, due_date, current_date)
    
    assert status == RentStatus.OVERDUE
    assert days_overdue == 14


@pytest.mark.asyncio
async def test_determine_rent_status_overdue_partial():
    """Test rent status determination for overdue partial payment."""
    due_date = date(2024, 1, 1)
    current_date = date(2024, 1, 10)  # 9 days after due date
    monthly_rent = Decimal("1500.00")
    amount_paid = Decimal("500.00")  # Partial payment
    
    status, days_overdue = determine_rent_status(monthly_rent, amount_paid, due_date, current_date)
    
    assert status == RentStatus.PARTIAL  # Partial payment gets PARTIAL status even when overdue
    assert days_overdue == 9


@pytest.mark.asyncio
async def test_determine_rent_status_partial_before_due():
    """Test rent status determination for partial payment before due date."""
    due_date = date(2024, 1, 15)
    current_date = date(2024, 1, 10)  # Before due date
    monthly_rent = Decimal("1500.00")
    amount_paid = Decimal("500.00")  # Partial payment
    
    status, days_overdue = determine_rent_status(monthly_rent, amount_paid, due_date, current_date)
    
    assert status == RentStatus.PARTIAL
    assert days_overdue is None


# =============================================================================
# get_tenant_display_name TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_tenant_display_name_with_tenant():
    """Test getting tenant display name when tenant exists."""
    mock_tenant = MagicMock()
    mock_tenant.first_name = "John"
    mock_tenant.last_name = "Doe"
    
    result = get_tenant_display_name(mock_tenant)
    
    assert result == "John Doe"


@pytest.mark.asyncio
async def test_get_tenant_display_name_no_tenant():
    """Test getting tenant display name when tenant is None."""
    result = get_tenant_display_name(None)
    
    assert result == "Unknown Tenant"


@pytest.mark.asyncio
async def test_get_tenant_display_name_missing_attributes():
    """Test getting tenant display name when tenant has missing attributes."""
    mock_tenant = MagicMock()
    mock_tenant.first_name = None
    mock_tenant.last_name = "Doe"
    mock_tenant.email = "john.doe@example.com"
    
    result = get_tenant_display_name(mock_tenant)
    
    assert result == "john.doe@example.com"  # Falls back to email


# =============================================================================
# get_property_display_name TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_property_display_name_with_property():
    """Test getting property display name when property exists."""
    mock_lease = MagicMock()
    mock_lease.property.name = "Sunset Apartments"
    
    result = get_property_display_name(mock_lease)
    
    assert result == "Sunset Apartments"


@pytest.mark.asyncio
async def test_get_property_display_name_no_property():
    """Test getting property display name when property is None."""
    mock_lease = MagicMock()
    mock_lease.property = None
    mock_lease.property_id = 123
    
    result = get_property_display_name(mock_lease)
    
    assert result == "Property #123"


@pytest.mark.asyncio
async def test_get_property_display_name_no_name():
    """Test getting property display name when property has no name."""
    mock_lease = MagicMock()
    mock_lease.property.name = None
    mock_lease.property_id = 456
    
    result = get_property_display_name(mock_lease)
    
    assert result == "Property #456"


# =============================================================================
# get_unit_display_name TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_unit_display_name_with_unit():
    """Test getting unit display name when unit exists."""
    mock_unit = MagicMock()
    mock_unit.name = "Unit 101"
    
    result = get_unit_display_name(mock_unit)
    
    assert result == "Unit 101"


@pytest.mark.asyncio
async def test_get_unit_display_name_no_unit():
    """Test getting unit display name when unit is None."""
    result = get_unit_display_name(None)
    
    assert result is None


@pytest.mark.asyncio
async def test_get_unit_display_name_no_number():
    """Test getting unit display name when unit has no name."""
    mock_unit = MagicMock()
    mock_unit.name = None
    mock_unit.id = 123
    
    result = get_unit_display_name(mock_unit)
    
    assert result == "Unit #123"


# =============================================================================
# calculate_collection_rate TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_calculate_collection_rate_full_collection():
    """Test collection rate calculation for 100% collection."""
    total_expected = Decimal("1500.00")
    total_collected = Decimal("1500.00")
    
    rate = calculate_collection_rate(total_expected, total_collected)
    
    assert rate == Decimal("100.00")


@pytest.mark.asyncio
async def test_calculate_collection_rate_partial_collection():
    """Test collection rate calculation for partial collection."""
    total_expected = Decimal("1500.00")
    total_collected = Decimal("1200.00")
    
    rate = calculate_collection_rate(total_expected, total_collected)
    
    assert rate == Decimal("80.00")


@pytest.mark.asyncio
async def test_calculate_collection_rate_no_collection():
    """Test collection rate calculation for zero collection."""
    total_expected = Decimal("1500.00")
    total_collected = Decimal("0.00")
    
    rate = calculate_collection_rate(total_expected, total_collected)
    
    assert rate == Decimal("0.00")


@pytest.mark.asyncio
async def test_calculate_collection_rate_zero_expected():
    """Test collection rate calculation when no rent is expected."""
    total_expected = Decimal("0.00")
    total_collected = Decimal("0.00")
    
    rate = calculate_collection_rate(total_expected, total_collected)
    
    assert rate == Decimal("0.00")


@pytest.mark.asyncio
async def test_calculate_collection_rate_over_collection():
    """Test collection rate calculation when collected exceeds expected."""
    total_expected = Decimal("1500.00")
    total_collected = Decimal("1600.00")  # Over-payment
    
    rate = calculate_collection_rate(total_expected, total_collected)
    
    assert rate == Decimal("106.67")  # Doesn't cap at 100%


# =============================================================================
# calculate_rent_due_date TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_calculate_rent_due_date_default():
    """Test rent due date calculation with default due day."""
    mock_lease = MagicMock()
    mock_lease.rent_due_day = None  # Should default to 1st
    
    due_date = calculate_rent_due_date(mock_lease, 3, 2024)
    
    assert due_date == date(2024, 3, 1)


@pytest.mark.asyncio
async def test_calculate_rent_due_date_specific_day():
    """Test rent due date calculation with specific due day."""
    mock_lease = MagicMock()
    mock_lease.rent_due_day = 15
    
    due_date = calculate_rent_due_date(mock_lease, 3, 2024)
    
    assert due_date == date(2024, 3, 15)


@pytest.mark.asyncio
async def test_calculate_rent_due_date_end_of_month():
    """Test rent due date calculation for end of month due day."""
    mock_lease = MagicMock()
    mock_lease.rent_due_day = 31
    
    # February only has 28/29 days
    due_date = calculate_rent_due_date(mock_lease, 2, 2024)
    
    assert due_date == date(2024, 2, 29)  # 2024 is leap year


@pytest.mark.asyncio
async def test_calculate_rent_due_date_february_non_leap():
    """Test rent due date calculation for February in non-leap year."""
    mock_lease = MagicMock()
    mock_lease.rent_due_day = 30
    
    due_date = calculate_rent_due_date(mock_lease, 2, 2023)
    
    assert due_date == date(2023, 2, 28)  # 2023 is not leap year


@pytest.mark.asyncio
async def test_calculate_rent_due_date_invalid_day():
    """Test rent due date calculation with invalid due day."""
    mock_lease = MagicMock()
    mock_lease.rent_due_day = 32  # Invalid day
    
    due_date = calculate_rent_due_date(mock_lease, 3, 2024)
    
    assert due_date == date(2024, 3, 31)  # Should use last day of month