"""
Helper functions for rent tracker operations.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from Backend.models.lease import Lease
from Backend.models.tenant import Tenant
from Backend.models.units import PropertyUnit

from .schemas import RentStatus


logger = logging.getLogger(__name__)


def calculate_month_bounds(month: Optional[int] = None, year: Optional[int] = None) -> tuple[date, date]:
    """
    Calculate the start and end dates for a given month.
    
    Args:
        month: Month number (1-12). Defaults to current month if None.
        year: Year. Defaults to current year if None.
        
    Returns:
        Tuple of (month_start, month_end) dates
    """
    today = date.today()
    
    if month is None:
        month = today.month
    if year is None:
        year = today.year
        
    # Calculate month start
    month_start = date(year, month, 1)
    
    # Calculate month end (last day of the month)
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)
        
    return month_start, month_end


def determine_rent_status(
    monthly_rent: Decimal, 
    amount_paid: Decimal,
    due_date: Optional[date] = None,
    current_date: Optional[date] = None
) -> tuple[RentStatus, Optional[int]]:
    """
    Determine rent payment status based on amounts and dates.
    
    Args:
        monthly_rent: Expected monthly rent amount
        amount_paid: Amount actually paid
        due_date: Due date for the rent payment
        current_date: Current date for overdue calculation (defaults to today)
        
    Returns:
        Tuple of (status, days_overdue)
    """
    if current_date is None:
        current_date = date.today()
        
    remaining_due = monthly_rent - amount_paid
    days_overdue = None
    
    # Fully paid
    if remaining_due <= 0:
        return RentStatus.PAID, None
    
    # Check if overdue
    if due_date and current_date > due_date:
        days_overdue = (current_date - due_date).days
        if amount_paid > 0:
            return RentStatus.PARTIAL, days_overdue
        else:
            return RentStatus.OVERDUE, days_overdue
    
    # Not overdue yet
    if amount_paid > 0:
        return RentStatus.PARTIAL, None
    else:
        return RentStatus.DUE, None


def get_tenant_display_name(tenant: Optional[Tenant]) -> str:
    """
    Get a display name for a tenant with fallback for missing data.
    
    Args:
        tenant: Tenant object or None
        
    Returns:
        Formatted tenant name or fallback string
    """
    if not tenant:
        return "Unknown Tenant"
    
    # Try to build full name
    if tenant.first_name:
        full_name = tenant.first_name
        if tenant.last_name:
            full_name += f" {tenant.last_name}"
        return full_name.strip()
    
    # Fallback to email if available
    if hasattr(tenant, 'email') and tenant.email:
        return tenant.email
    
    # Last resort - use ID
    if hasattr(tenant, 'id') and tenant.id:
        return f"Tenant #{tenant.id}"
    
    return "Unknown Tenant"


def get_property_display_name(lease: Lease) -> str:
    """
    Get a display name for a property from a lease.
    
    Args:
        lease: Lease object containing property information
        
    Returns:
        Property name or fallback string
    """
    if lease.property and hasattr(lease.property, 'name') and lease.property.name:
        return lease.property.name
    return f"Property #{lease.property_id}" if lease.property_id else "Unknown Property"


def get_unit_display_name(unit: Optional[PropertyUnit]) -> Optional[str]:
    """
    Get a display name for a unit.
    
    Args:
        unit: PropertyUnit object or None
        
    Returns:
        Unit name/number or None if no unit
    """
    if not unit:
        return None
    
    if hasattr(unit, 'name') and unit.name:
        return unit.name
    
    if hasattr(unit, 'id') and unit.id:
        return f"Unit #{unit.id}"
    
    return None


def calculate_collection_rate(total_expected: Decimal, total_collected: Decimal) -> Decimal:
    """
    Calculate the collection rate as a percentage.
    
    Args:
        total_expected: Total expected rent amount
        total_collected: Total collected rent amount
        
    Returns:
        Collection rate as a decimal percentage (0-100)
    """
    if total_expected <= 0:
        return Decimal("0.00")
    
    rate = (total_collected / total_expected) * 100
    # Round to 2 decimal places
    return rate.quantize(Decimal("0.01"))


def calculate_rent_due_date(lease: Lease, month: int, year: int) -> Optional[date]:
    """
    Calculate the rent due date for a specific month based on lease terms.
    
    Args:
        lease: Lease object
        month: Month number (1-12)
        year: Year
        
    Returns:
        Due date for the rent payment or None if not determinable
    """
    # Default to the 1st of the month if no specific due day is set
    due_day = getattr(lease, 'rent_due_day', 1) or 1
    
    try:
        # Handle months with fewer days than the due day
        # (e.g., due on 31st but month only has 30 days)
        if due_day > 28:  # Potentially problematic days
            month_start, month_end = calculate_month_bounds(month, year)
            last_day = month_end.day
            if due_day > last_day:
                due_day = last_day
        
        return date(year, month, due_day)
    except ValueError as e:
        logger.warning(f"Error calculating due date for lease {lease.id}: {e}")
        # Fallback to first of the month
        return date(year, month, 1)