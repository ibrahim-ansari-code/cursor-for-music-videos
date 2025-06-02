"""
Datetime and timezone utilities for consistent handling across the API.

This module provides utilities for proper timezone handling:
- Business date fields (payment_date, expense_date, etc.) -> timezone-aware (UTC)
- Audit date fields (created_at, updated_at) -> naive (server time)
"""

from datetime import UTC, date, datetime, time
from typing import Tuple, cast


def ensure_utc_aware(dt: datetime | None) -> datetime | None:
    """
    Ensures a datetime is timezone-aware in UTC.

    Args:
        dt: Input datetime (can be naive or timezone-aware)

    Returns:
        UTC timezone-aware datetime, or None if input was None
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
    Returns current datetime as naive UTC (for audit fields).

    Returns:
        Current UTC datetime (naive - no timezone info)
    """
    return datetime.now(UTC).replace(tzinfo=None)


def date_to_utc_range(start_date: date, end_date: date) -> Tuple[datetime, datetime]:
    """
    Converts date range to UTC timezone-aware datetime range for business date queries.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        Tuple of (start_datetime_utc, end_datetime_utc) as timezone-aware datetimes
    """
    start_datetime = datetime.combine(start_date, time.min, tzinfo=UTC)
    end_datetime = datetime.combine(end_date, time.max, tzinfo=UTC)
    return start_datetime, end_datetime


def date_to_naive_range(start_date: date, end_date: date) -> Tuple[datetime, datetime]:
    """
    Converts date range to naive datetime range for audit date queries.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        Tuple of (start_datetime, end_datetime) as naive datetimes
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
    Creates a naive datetime for audit fields (created_at, updated_at).

    Returns:
        Naive UTC datetime for audit trail
    """
    return naive_utc_now()
