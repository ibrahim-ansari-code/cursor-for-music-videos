"""
Calendar Helper Functions

Utility functions for computing event status, colors, quick actions, etc.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from Backend.models.calendar import CalendarEventStatus, CalendarEventType
from Backend.models.accounting.common import PaymentStatus
from Backend.models.enums import MaintenanceStatus


def compute_event_status(
    due_date: datetime,
    is_completed: bool = False,
    event_type: Optional[CalendarEventType] = None
) -> CalendarEventStatus:
    """
    Compute calendar event status based on due date and completion.
    
    Args:
        due_date: When the event is due
        is_completed: Whether the underlying source is completed
        event_type: Type of event (some types auto-complete after date)
        
    Returns:
        CalendarEventStatus enum value
    """
    if is_completed:
        return CalendarEventStatus.COMPLETED
    
    now = datetime.now(timezone.utc)
    
    # Make due_date timezone-aware for comparison if it's timezone-naive
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
    
    # Calculate days until due
    days_until = (due_date.date() - now.date()).days
    
    if days_until < 0:
        return CalendarEventStatus.OVERDUE
    elif days_until == 0:
        return CalendarEventStatus.DUE
    else:
        return CalendarEventStatus.UPCOMING


def compute_event_color(status: CalendarEventStatus) -> str:
    """
    Get color code for calendar event based on status.
    
    Args:
        status: CalendarEventStatus
        
    Returns:
        Color string: "green", "amber", or "red"
    """
    color_map = {
        CalendarEventStatus.UPCOMING: "green",
        CalendarEventStatus.DUE: "amber",
        CalendarEventStatus.OVERDUE: "red",
        CalendarEventStatus.COMPLETED: "green",
    }
    return color_map.get(status, "green")


def get_quick_actions(
    event_type: CalendarEventType,
    source_status: Optional[str | PaymentStatus | MaintenanceStatus] = None
) -> List[str]:
    """
    Determine available quick actions for an event.
    
    Args:
        event_type: Type of calendar event
        source_status: Status of the underlying source record
        
    Returns:
        List of action identifiers
    """
    actions = []
    
    if event_type == CalendarEventType.INVOICE_DUE:
        if source_status != PaymentStatus.PAID:
            actions.extend(["send_invoice", "record_payment"])
        actions.append("view_invoice")
    
    elif event_type == CalendarEventType.RENT_DUE:
        actions.extend(["generate_invoice", "record_payment", "view_lease"])
    
    elif event_type == CalendarEventType.LEASE_EXPIRING:
        actions.extend(["start_renewal", "generate_notice", "view_lease"])
    
    elif event_type == CalendarEventType.LEASE_START:
        actions.extend(["view_lease", "view_tenant"])
    
    elif event_type == CalendarEventType.MAINTENANCE_SCHEDULED:
        if source_status != MaintenanceStatus.COMPLETED:
            actions.extend(["notify_vendor", "reschedule", "mark_complete"])
        actions.append("view_maintenance")
    
    elif event_type in [CalendarEventType.INSURANCE_EXPIRY, CalendarEventType.MORTGAGE_RENEWAL]:
        actions.extend(["view_property", "add_reminder"])
    
    elif event_type == CalendarEventType.CUSTOM_REMINDER:
        actions.extend(["mark_complete", "snooze", "edit", "delete"])
    
    return actions


def format_event_title(
    event_type: CalendarEventType,
    entity_name: str,
    amount: Optional[float] = None,
    additional_info: Optional[str] = None
) -> str:
    """
    Format a user-friendly event title.
    
    Args:
        event_type: Type of event
        entity_name: Name of primary entity (property, tenant, etc.)
        amount: Optional monetary amount
        additional_info: Additional context
        
    Returns:
        Formatted title string
    """
    if event_type == CalendarEventType.INVOICE_DUE:
        if amount:
            return f"Invoice Due - {entity_name} (${amount:,.2f})"
        return f"Invoice Due - {entity_name}"
    
    elif event_type == CalendarEventType.RENT_DUE:
        if amount:
            return f"Rent Due - {entity_name} (${amount:,.2f})"
        return f"Rent Due - {entity_name}"
    
    elif event_type == CalendarEventType.LEASE_START:
        return f"Lease Start - {entity_name}"
    
    elif event_type == CalendarEventType.LEASE_EXPIRING:
        if additional_info:
            return f"Lease Expiring in {additional_info} - {entity_name}"
        return f"Lease Expiring - {entity_name}"
    
    elif event_type == CalendarEventType.MAINTENANCE_SCHEDULED:
        return f"Maintenance: {entity_name}"
    
    elif event_type == CalendarEventType.INSURANCE_EXPIRY:
        return f"Insurance Expiry - {entity_name}"
    
    elif event_type == CalendarEventType.MORTGAGE_RENEWAL:
        return f"Mortgage Renewal - {entity_name}"
    
    return entity_name


def days_until(target_date: datetime | None) -> int:
    """
    Calculate days until a target date.
    
    Args:
        target_date: Target date (can be None)
        
    Returns:
        Number of days until target (negative if past)
    """
    if not target_date:
        return 999  # Large number for "no date set"
    
    now = datetime.now(timezone.utc)
    
    # Make target_date timezone-aware for comparison if it's timezone-naive
    if target_date.tzinfo is None:
        target_date = target_date.replace(tzinfo=timezone.utc)
    
    return (target_date.date() - now.date()).days


def should_show_in_calendar(
    event_date: datetime | None,
    from_date: datetime,
    to_date: datetime
) -> bool:
    """
    Check if an event falls within the requested date range.
    
    Args:
        event_date: Date of the event
        from_date: Start of range
        to_date: End of range
        
    Returns:
        True if event should be included
    """
    if not event_date:
        return False
    
    # Handle timezone-aware dates
    if event_date.tzinfo is not None:
        event_date = event_date.replace(tzinfo=None)
    if from_date.tzinfo is not None:
        from_date = from_date.replace(tzinfo=None)
    if to_date.tzinfo is not None:
        to_date = to_date.replace(tzinfo=None)
    
    return from_date <= event_date <= to_date

