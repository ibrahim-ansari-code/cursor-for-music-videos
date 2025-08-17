"""
Unit tests for rent tracker schemas and validation.
"""
import pytest
from decimal import Decimal
from datetime import date
from pydantic import ValidationError

from Backend.api.accounting.rent_tracker.schemas import (
    RentTrackingEntry,
    RentTrackerSummary,
    RentTrackerFilter,
    RentStatus
)


# =============================================================================
# RentTrackingEntry TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_rent_tracking_entry_valid():
    """Test creating valid RentTrackingEntry."""
    entry = RentTrackingEntry(
        lease_id=1,
        tenant_id=2,
        tenant_name="John Doe",
        property_name="Sunset Apartments",
        unit_name="Unit 101",
        monthly_rent=Decimal("1500.00"),
        amount_paid=Decimal("1500.00"),
        remaining_due=Decimal("0.00"),
        status=RentStatus.PAID,
        due_date=date(2024, 1, 1),
        last_payment_date=date(2024, 1, 1),
        days_overdue=None
    )
    
    assert entry.lease_id == 1
    assert entry.tenant_name == "John Doe"
    assert entry.monthly_rent == Decimal("1500.00")
    assert entry.status == RentStatus.PAID


@pytest.mark.asyncio
async def test_rent_tracking_entry_negative_amounts():
    """Test RentTrackingEntry validation with negative amounts."""
    with pytest.raises(ValidationError) as exc_info:
        RentTrackingEntry(
            lease_id=1,
            tenant_id=2,
            tenant_name="John Doe",
            property_name="Sunset Apartments",
            monthly_rent=Decimal("-100.00"),  # Negative amount
            amount_paid=Decimal("0.00"),
            remaining_due=Decimal("0.00"),
            status=RentStatus.DUE
        )
    
    errors = exc_info.value.errors()
    assert any("Monetary amounts must be non-negative" in str(error["msg"]) for error in errors)


@pytest.mark.asyncio
async def test_rent_tracking_entry_negative_days_overdue():
    """Test RentTrackingEntry validation with negative days overdue."""
    with pytest.raises(ValidationError) as exc_info:
        RentTrackingEntry(
            lease_id=1,
            tenant_id=2,
            tenant_name="John Doe",
            property_name="Sunset Apartments",
            monthly_rent=Decimal("1500.00"),
            amount_paid=Decimal("0.00"),
            remaining_due=Decimal("1500.00"),
            status=RentStatus.OVERDUE,
            days_overdue=-5  # Negative days
        )
    
    errors = exc_info.value.errors()
    assert any("Days overdue must be non-negative" in str(error["msg"]) for error in errors)


@pytest.mark.asyncio
async def test_rent_tracking_entry_optional_fields():
    """Test RentTrackingEntry with optional fields as None."""
    entry = RentTrackingEntry(
        lease_id=1,
        tenant_id=None,  # Optional
        tenant_name="John Doe",
        property_name="Sunset Apartments",
        unit_name=None,  # Optional
        monthly_rent=Decimal("1500.00"),
        amount_paid=Decimal("0.00"),
        remaining_due=Decimal("1500.00"),
        status=RentStatus.DUE,
        due_date=None,  # Optional
        last_payment_date=None,  # Optional
        days_overdue=None  # Optional
    )
    
    assert entry.tenant_id is None
    assert entry.unit_name is None
    assert entry.due_date is None
    assert entry.last_payment_date is None
    assert entry.days_overdue is None


# =============================================================================
# RentTrackerSummary TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_rent_tracker_summary_valid():
    """Test creating valid RentTrackerSummary."""
    summary = RentTrackerSummary(
        total_units=10,
        total_expected=Decimal("15000.00"),
        total_collected=Decimal("12000.00"),
        total_outstanding=Decimal("3000.00"),
        units_paid=7,
        units_partial=2,
        units_due=1,
        units_overdue=0,
        collection_rate=Decimal("80.00")
    )
    
    assert summary.total_units == 10
    assert summary.total_expected == Decimal("15000.00")
    assert summary.collection_rate == Decimal("80.00")


@pytest.mark.asyncio
async def test_rent_tracker_summary_negative_amounts():
    """Test RentTrackerSummary validation with negative amounts."""
    with pytest.raises(ValidationError) as exc_info:
        RentTrackerSummary(
            total_units=10,
            total_expected=Decimal("-1000.00"),  # Negative amount
            total_collected=Decimal("0.00"),
            total_outstanding=Decimal("0.00"),
            units_paid=0,
            units_partial=0,
            units_due=0,
            units_overdue=0,
            collection_rate=Decimal("0.00")
        )
    
    errors = exc_info.value.errors()
    assert any("Monetary amounts must be non-negative" in str(error["msg"]) for error in errors)


@pytest.mark.asyncio
async def test_rent_tracker_summary_negative_units():
    """Test RentTrackerSummary validation with negative unit counts."""
    with pytest.raises(ValidationError) as exc_info:
        RentTrackerSummary(
            total_units=-1,  # Negative count
            total_expected=Decimal("0.00"),
            total_collected=Decimal("0.00"),
            total_outstanding=Decimal("0.00"),
            units_paid=0,
            units_partial=0,
            units_due=0,
            units_overdue=0,
            collection_rate=Decimal("0.00")
        )
    
    errors = exc_info.value.errors()
    assert any("Unit counts must be non-negative" in str(error["msg"]) for error in errors)


@pytest.mark.asyncio
async def test_rent_tracker_summary_invalid_collection_rate():
    """Test RentTrackerSummary validation with invalid collection rate."""
    # Test rate > 100
    with pytest.raises(ValidationError) as exc_info:
        RentTrackerSummary(
            total_units=1,
            total_expected=Decimal("1000.00"),
            total_collected=Decimal("1000.00"),
            total_outstanding=Decimal("0.00"),
            units_paid=1,
            units_partial=0,
            units_due=0,
            units_overdue=0,
            collection_rate=Decimal("150.00")  # > 100%
        )
    
    errors = exc_info.value.errors()
    assert any("Collection rate must be between 0 and 100" in str(error["msg"]) for error in errors)
    
    # Test rate < 0
    with pytest.raises(ValidationError) as exc_info:
        RentTrackerSummary(
            total_units=1,
            total_expected=Decimal("1000.00"),
            total_collected=Decimal("0.00"),
            total_outstanding=Decimal("1000.00"),
            units_paid=0,
            units_partial=0,
            units_due=1,
            units_overdue=0,
            collection_rate=Decimal("-10.00")  # < 0%
        )
    
    errors = exc_info.value.errors()
    assert any("Collection rate must be between 0 and 100" in str(error["msg"]) for error in errors)


@pytest.mark.asyncio
async def test_rent_tracker_summary_zero_values():
    """Test RentTrackerSummary with all zero values."""
    summary = RentTrackerSummary(
        total_units=0,
        total_expected=Decimal("0.00"),
        total_collected=Decimal("0.00"),
        total_outstanding=Decimal("0.00"),
        units_paid=0,
        units_partial=0,
        units_due=0,
        units_overdue=0,
        collection_rate=Decimal("0.00")
    )
    
    assert summary.total_units == 0
    assert summary.collection_rate == Decimal("0.00")


# =============================================================================
# RentTrackerFilter TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_rent_tracker_filter_default():
    """Test RentTrackerFilter with default values."""
    filter_obj = RentTrackerFilter()
    
    assert filter_obj.month is None
    assert filter_obj.year is None
    assert filter_obj.property_id is None
    assert filter_obj.status is None
    assert filter_obj.include_vacant is False


@pytest.mark.asyncio
async def test_rent_tracker_filter_with_values():
    """Test RentTrackerFilter with specific values."""
    filter_obj = RentTrackerFilter(
        month=3,
        year=2024,
        property_id=123,
        status=RentStatus.OVERDUE,
        include_vacant=True
    )
    
    assert filter_obj.month == 3
    assert filter_obj.year == 2024
    assert filter_obj.property_id == 123
    assert filter_obj.status == RentStatus.OVERDUE
    assert filter_obj.include_vacant is True


# =============================================================================
# RentStatus ENUM TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_rent_status_enum_values():
    """Test RentStatus enum values."""
    assert RentStatus.PAID == "PAID"
    assert RentStatus.PARTIAL == "PARTIAL"
    assert RentStatus.DUE == "DUE"
    assert RentStatus.OVERDUE == "OVERDUE"


@pytest.mark.asyncio
async def test_rent_status_enum_membership():
    """Test RentStatus enum membership."""
    assert hasattr(RentStatus, 'PAID')
    assert hasattr(RentStatus, 'PARTIAL')
    assert hasattr(RentStatus, 'DUE')
    assert hasattr(RentStatus, 'OVERDUE')
    assert not hasattr(RentStatus, 'INVALID')


@pytest.mark.asyncio
async def test_rent_status_in_schema():
    """Test using RentStatus enum in schema validation."""
    # Valid status
    entry = RentTrackingEntry(
        lease_id=1,
        tenant_name="John Doe",
        property_name="Test Property",
        monthly_rent=Decimal("1500.00"),
        amount_paid=Decimal("1500.00"),
        remaining_due=Decimal("0.00"),
        status=RentStatus.PAID
    )
    assert entry.status == RentStatus.PAID
    
    # Invalid status should raise validation error
    with pytest.raises(ValidationError):
        RentTrackingEntry(
            lease_id=1,
            tenant_name="John Doe",
            property_name="Test Property",
            monthly_rent=Decimal("1500.00"),
            amount_paid=Decimal("0.00"),
            remaining_due=Decimal("1500.00"),
            status="INVALID_STATUS"  # Invalid status
        )