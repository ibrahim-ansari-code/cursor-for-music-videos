"""
Datetime and timezone utilities for consistent handling across the API.

This module provides utilities for proper timezone handling:
- Business date fields (payment_date, expense_date, etc.) -> timezone-aware (UTC)
- Audit date fields (created_at, updated_at) -> timezone-aware (UTC)

All datetime fields should be timezone-aware to avoid ambiguity and ensure
consistent behavior across different deployments and timezones.
"""

from datetime import UTC, date, datetime, time
from typing import cast
from fastapi import HTTPException, status


def ensure_utc_aware(dt: datetime | None) -> datetime | None:
    """
    Converts a datetime to a UTC timezone-aware datetime.
    
    If the input is naive, it is assumed to be in UTC and the UTC timezone is set. If the input is already timezone-aware, it is converted to UTC. Returns None if the input is None.
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # Naive datetime - assume it's already in UTC
        return dt.replace(tzinfo=UTC)
    else:
        # Timezone-aware - convert to UTC
        return dt.astimezone(UTC)


def utc_now() -> datetime:
    """
    Returns current datetime in UTC timezone.

    Returns:
        Current UTC datetime (timezone-aware)
    """
    return datetime.now(UTC)


def naive_utc_now() -> datetime:
    """
    Returns the current UTC datetime as a naive datetime object.
    
    This function provides the current time in UTC without any timezone information attached.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def date_to_utc_range(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """
    Converts a date range into a tuple of UTC timezone-aware datetimes representing the full span of each day.
    
    Args:
        start_date: The inclusive start date of the range.
        end_date: The inclusive end date of the range.
    
    Returns:
        A tuple containing the UTC-aware datetime at the start of start_date and the end of end_date.
    """
    start_datetime = datetime.combine(start_date, time.min, tzinfo=UTC)
    end_datetime = datetime.combine(end_date, time.max, tzinfo=UTC)
    return start_datetime, end_datetime


def date_to_naive_range(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """
    Converts a date range into a tuple of naive datetimes representing the full span of each day.
    
    The returned tuple contains the earliest possible time on the start date and the latest possible time on the end date, both as naive (timezone-unaware) datetime objects.
    """
    start_datetime = datetime.combine(start_date, time.min)
    end_datetime = datetime.combine(end_date, time.max)
    return start_datetime, end_datetime


def validate_business_datetime(dt: datetime) -> datetime:
    """
    Validates and ensures a business datetime is properly timezone-aware.

    Used for payment_date, expense_date, issue_date, due_date fields.

    Args:
        dt: Input datetime from API request

    Returns:
        UTC timezone-aware datetime ready for database storage
    """
    # Since dt is not None, ensure_utc_aware will return datetime
    return cast(datetime, ensure_utc_aware(dt))


def create_audit_datetime() -> datetime:
    """
    Creates and returns a timezone-aware UTC datetime for audit purposes.
    
    Returns:
        A datetime object representing the current time in UTC with timezone awareness.
    """
    return utc_now()


def validate_date_range(start_date: date | None, end_date: date | None) -> None:
    """
    Checks that the start date is not after the end date, raising an HTTP 400 error if invalid.
    
    Raises:
        HTTPException: If start_date is after end_date, with status 400.
    """
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be after end date."
        )
