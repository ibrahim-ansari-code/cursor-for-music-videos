import logging
from datetime import date, timedelta
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlmodel import col

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.accounting.payment import Payment
from Backend.models.accounting.common import PaymentStatus
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.user import User
from Backend.models.property import Property

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/rent-tracker",
    tags=["rent-tracker"],
)

# Rent status enum


class RentStatus(str, Enum):
    PAID = "PAID"
    PARTIAL = "PARTIAL"
    DUE = "DUE"

# API models


class RentTrackingEntry(BaseModel):
    lease_id: int
    tenant_name: str
    property_name: str
    monthly_rent: float
    amount_paid: float
    remaining_due: float
    status: RentStatus

    class Config:
        from_attributes = True

# Helper functions for rent tracker


async def _calculate_payments_for_lease(
    session: AsyncSession,
    lease_id: int,
    month_start: date,
    month_end: date
) -> float:
    """Calculate total payments made for a lease in the given month."""
    payments_query = select(func.coalesce(func.sum(Payment.amount), 0.0)).where(
        and_(
            col(Payment.lease_id) == lease_id,
            col(Payment.payment_date) >= month_start,
            col(Payment.payment_date) <= month_end,
            col(Payment.status).in_(
                [PaymentStatus.PAID, PaymentStatus.PARTIAL])
        )
    )

    payment_result = await session.execute(payments_query)
    return payment_result.scalar() or 0.0


def _determine_rent_status(monthly_rent: float, amount_paid: float) -> RentStatus:
    """Determine rent status based on monthly rent and amount paid."""
    remaining_due = monthly_rent - amount_paid

    if remaining_due <= 0:
        return RentStatus.PAID
    if amount_paid > 0:
        return RentStatus.PARTIAL
    return RentStatus.DUE


def _get_tenant_name(lease: Lease) -> str:
    """Extract tenant name from lease, with fallback for missing data."""
    if not lease.tenant:
        return "Unknown Tenant"

    if lease.tenant.first_name:
        return f"{lease.tenant.first_name} {lease.tenant.last_name or ''}".strip()

    return f"Tenant #{lease.tenant_id}"


def _get_property_name(lease: Lease) -> str:
    """Extract property name from lease, with fallback for missing data."""
    if lease.property:
        return lease.property.name
    return "Unknown Property"


async def _create_rent_tracking_entry(
    session: AsyncSession,
    lease: Lease,
    month_start: date,
    month_end: date
) -> RentTrackingEntry | None:
    """Create a rent tracking entry for a single lease."""
    # Ensure lease.id is not None before processing
    if lease.id is None:
        logger.warning(
            "Skipping rent tracking entry for a lease with no ID. Lease details: %s", lease)
        return None

    # Calculate payments for this lease in the current month
    amount_paid = await _calculate_payments_for_lease(session, lease.id, month_start, month_end)

    # Calculate remaining due and determine status
    remaining_due = lease.monthly_rent - amount_paid
    rent_payment_status = _determine_rent_status(
        lease.monthly_rent, amount_paid)

    # Get names with fallbacks
    tenant_name = _get_tenant_name(lease)
    property_name = _get_property_name(lease)

    # Create rent tracking entry
    return RentTrackingEntry(
        lease_id=lease.id,
        tenant_name=tenant_name,
        property_name=property_name,
        monthly_rent=float(lease.monthly_rent),
        amount_paid=float(amount_paid),
        remaining_due=float(remaining_due),
        status=rent_payment_status
    )


@router.get("/", response_model=list[RentTrackingEntry])
async def get_rent_tracker(
    month: int | None = None,
    year: int | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[RentTrackingEntry]:
    """
    Retrieves the rent payment status for all active leases for a specified month.

    Only users with "ADMIN" or "LANDLORD" roles can access this endpoint. For
    each active lease overlapping the given month, the function aggregates
    payments, calculates the remaining due, and determines the rent status
    (PAID, PARTIAL, or DUE). Tenant and property names are included when
    available.

    Args:
        month (int | None): The month (1-12) for which to retrieve rent
            tracking data. Defaults to the current month if not provided.
        year (int | None): The year for which to retrieve rent tracking data.
            Defaults to the current year if not provided.

    Returns:
        list[RentTrackingEntry]: A list of RentTrackingEntry objects, each
            representing the rent payment status for an active lease in the
            specified month.

    Raises:
        HTTPException: If the user is not authorized or if an internal error
            occurs during processing.
    """
    # Convert user_type to uppercase string for case-insensitive comparison
    user_type = current_user.user_type.upper() if isinstance(
        current_user.user_type, str) else current_user.user_type

    if user_type not in ["ADMIN", "LANDLORD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view rent tracker"
        )

    try:
        # Get current month if not specified
        today = date.today()
        if month is None:
            month = today.month
        if year is None:
            year = today.year

        # Calculate month start and end
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        logger.info("Getting rent tracker for period: %s to %s",
                    month_start, month_end)

        # Get all active leases with related tenant and property information
        # IMPORTANT: Filter by current user's properties to prevent data leakage
        query = select(Lease).join(
            Property, col(Lease.property_id) == col(Property.id)
        ).where(
            and_(
                col(Property.user_id) == current_user.id,  # Filter by current user's properties
                col(Lease.start_date) <= month_end,
                or_(col(Lease.end_date) >= month_start,
                    col(Lease.end_date).is_(None)),
                col(Lease.status) == LeaseStatus.ACTIVE
            )
        ).options(
            selectinload(getattr(Lease, "property")),
            selectinload(getattr(Lease, "tenant"))
        )

        result = await session.execute(query)
        active_leases = result.scalars().all()

        logger.info("Found %d active leases", len(active_leases))

        # Process leases sequentially to avoid AsyncSession concurrency issues
        rent_tracker_entries = []
        for lease in active_leases:
            entry = await _create_rent_tracking_entry(session, lease, month_start, month_end)
            if entry is not None:
                rent_tracker_entries.append(entry)

        logger.info("Generated %d rent tracker entries",
                    len(rent_tracker_entries))
        return rent_tracker_entries

    except HTTPException:
        raise  # Re-raise HTTP exceptions to preserve status codes
    except Exception as e:
        logger.error("Failed to get rent tracker: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rent tracker: {str(e)}"
        ) from e
