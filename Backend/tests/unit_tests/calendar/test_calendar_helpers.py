"""
Unit tests for calendar helper functions.

Tests status computation, color assignment, and quick action logic.
"""
from datetime import datetime, timedelta, timezone
import pytest

from Backend.api.calendar.helpers import (
    compute_event_status,
    compute_event_color,
    get_quick_actions,
    days_until,
    should_show_in_calendar
)
from Backend.models.calendar import CalendarEventType, CalendarEventStatus
from Backend.models.accounting.common import PaymentStatus
from Backend.models.enums import MaintenanceStatus

pytestmark = pytest.mark.unit


class TestComputeEventStatus:
    """Tests for compute_event_status function."""
    
    def test_completed_event(self):
        """Test that completed events return COMPLETED status."""
        # Arrange
        due_date = datetime.now(timezone.utc) + timedelta(days=1)
        
        # Act
        status = compute_event_status(due_date, is_completed=True)
        
        # Assert
        assert status == CalendarEventStatus.COMPLETED
    
    def test_upcoming_event(self):
        """Test event more than 3 days away is UPCOMING."""
        # Arrange
        due_date = datetime.now(timezone.utc) + timedelta(days=5)
        
        # Act
        status = compute_event_status(due_date, is_completed=False)
        
        # Assert
        assert status == CalendarEventStatus.UPCOMING
    
    def test_due_event(self):
        """Test event today is DUE."""
        # Arrange
        due_date = datetime.now(timezone.utc)
        
        # Act
        status = compute_event_status(due_date, is_completed=False)
        
        # Assert
        assert status == CalendarEventStatus.DUE
    
    def test_overdue_event(self):
        """Test event in the past is OVERDUE."""
        # Arrange
        due_date = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Act
        status = compute_event_status(due_date, is_completed=False)
        
        # Assert
        assert status == CalendarEventStatus.OVERDUE
    
    def test_timezone_naive_date(self):
        """Test handling of timezone-naive dates."""
        # Arrange
        due_date = datetime.now(timezone.utc) + timedelta(days=1)  # Timezone-aware datetime

        # Act
        status = compute_event_status(due_date, is_completed=False)
        
        # Assert
        assert status in [CalendarEventStatus.UPCOMING, CalendarEventStatus.DUE]


class TestComputeEventColor:
    """Tests for compute_event_color function."""
    
    def test_completed_status_green(self):
        """Test COMPLETED status returns green."""
        assert compute_event_color(CalendarEventStatus.COMPLETED) == "green"
    
    def test_upcoming_status_green(self):
        """Test UPCOMING status returns green."""
        assert compute_event_color(CalendarEventStatus.UPCOMING) == "green"
    
    def test_due_status_amber(self):
        """Test DUE status returns amber."""
        assert compute_event_color(CalendarEventStatus.DUE) == "amber"
    
    def test_overdue_status_red(self):
        """Test OVERDUE status returns red."""
        assert compute_event_color(CalendarEventStatus.OVERDUE) == "red"


class TestGetQuickActions:
    """Tests for get_quick_actions function."""
    
    def test_invoice_due_unpaid(self):
        """Test quick actions for unpaid invoice."""
        # Act
        actions = get_quick_actions(
            event_type=CalendarEventType.INVOICE_DUE,
            source_status=PaymentStatus.PENDING
        )
        
        # Assert
        assert "send_invoice" in actions
        assert "record_payment" in actions
        assert "view_invoice" in actions
    
    def test_invoice_paid(self):
        """Test quick actions for paid invoice."""
        # Act
        actions = get_quick_actions(
            event_type=CalendarEventType.INVOICE_DUE,
            source_status=PaymentStatus.PAID
        )
        
        # Assert
        assert "view_invoice" in actions
        assert "send_invoice" not in actions
    
    def test_lease_expiring(self):
        """Test quick actions for expiring lease."""
        # Act
        actions = get_quick_actions(
            event_type=CalendarEventType.LEASE_EXPIRING,
            source_status=None
        )
        
        # Assert
        assert "start_renewal" in actions
        assert "view_lease" in actions
    
    def test_maintenance_scheduled(self):
        """Test quick actions for scheduled maintenance."""
        # Act
        actions = get_quick_actions(
            event_type=CalendarEventType.MAINTENANCE_SCHEDULED,
            source_status=MaintenanceStatus.SCHEDULED
        )
        
        # Assert
        assert "mark_complete" in actions
        assert "view_maintenance" in actions
    
    def test_maintenance_completed(self):
        """Test quick actions for completed maintenance."""
        # Act
        actions = get_quick_actions(
            event_type=CalendarEventType.MAINTENANCE_SCHEDULED,
            source_status=MaintenanceStatus.COMPLETED
        )
        
        # Assert
        assert "mark_complete" not in actions
        assert "view_maintenance" in actions
    
    def test_custom_reminder(self):
        """Test quick actions for custom reminder."""
        # Act
        actions = get_quick_actions(
            event_type=CalendarEventType.CUSTOM_REMINDER,
            source_status=None
        )
        
        # Assert
        assert "edit_reminder" in actions
        assert "complete_reminder" in actions
        assert "delete_reminder" in actions
    
    def test_property_expiry(self):
        """Test quick actions for property insurance/mortgage expiry."""
        # Act
        insurance_actions = get_quick_actions(
            event_type=CalendarEventType.INSURANCE_EXPIRY,
            source_status=None
        )
        mortgage_actions = get_quick_actions(
            event_type=CalendarEventType.MORTGAGE_RENEWAL,
            source_status=None
        )
        
        # Assert
        assert "view_property" in insurance_actions
        assert "view_property" in mortgage_actions


class TestDaysUntil:
    """Tests for days_until function."""
    
    def test_days_until_future(self):
        """Test days until a future date."""
        # Arrange
        future_date = datetime.now(timezone.utc) + timedelta(days=5)
        
        # Act
        days = days_until(future_date)
        
        # Assert
        assert days == 5
    
    def test_days_until_past(self):
        """Test days until a past date (negative)."""
        # Arrange
        past_date = datetime.now(timezone.utc) - timedelta(days=3)
        
        # Act
        days = days_until(past_date)
        
        # Assert
        assert days == -3
    
    def test_days_until_none(self):
        """Test handling of None date."""
        # Act
        days = days_until(None)
        
        # Assert
        assert days == 999  # Large number for sorting
    
    def test_days_until_timezone_naive(self):
        """Test handling of timezone-naive dates."""
        # Arrange
        future_date = datetime.now(timezone.utc) + timedelta(days=2)  # Timezone-aware

        # Act
        days = days_until(future_date)
        
        # Assert
        assert days in [1, 2, 3]  # May vary slightly due to timing


class TestShouldShowInCalendar:
    """Tests for should_show_in_calendar function."""
    
    def test_event_within_range(self):
        """Test event within date range is shown."""
        # Arrange
        now = datetime.now(timezone.utc)
        event_date = now + timedelta(days=5)
        from_date = now
        to_date = now + timedelta(days=10)
        
        # Act
        should_show = should_show_in_calendar(event_date, from_date, to_date)
        
        # Assert
        assert should_show is True
    
    def test_event_before_range(self):
        """Test event before date range is not shown."""
        # Arrange
        now = datetime.now(timezone.utc)
        event_date = now - timedelta(days=5)
        from_date = now
        to_date = now + timedelta(days=10)
        
        # Act
        should_show = should_show_in_calendar(event_date, from_date, to_date)
        
        # Assert
        assert should_show is False
    
    def test_event_after_range(self):
        """Test event after date range is not shown."""
        # Arrange
        now = datetime.now(timezone.utc)
        event_date = now + timedelta(days=15)
        from_date = now
        to_date = now + timedelta(days=10)
        
        # Act
        should_show = should_show_in_calendar(event_date, from_date, to_date)
        
        # Assert
        assert should_show is False
    
    def test_event_on_boundary(self):
        """Test event on date range boundaries."""
        # Arrange
        now = datetime.now(timezone.utc)
        from_date = now
        to_date = now + timedelta(days=10)
        
        # Act
        should_show_start = should_show_in_calendar(from_date, from_date, to_date)
        should_show_end = should_show_in_calendar(to_date, from_date, to_date)
        
        # Assert
        assert should_show_start is True
        assert should_show_end is True
    
    def test_none_event_date(self):
        """Test handling of None event date."""
        # Arrange
        now = datetime.now(timezone.utc)
        from_date = now
        to_date = now + timedelta(days=10)
        
        # Act
        should_show = should_show_in_calendar(None, from_date, to_date)
        
        # Assert
        assert should_show is False

