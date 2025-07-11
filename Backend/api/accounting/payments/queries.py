"""Database query builders and filters for the payments module."""
import asyncio
import logging
from datetime import date
from typing import Iterable, Set
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from Backend.models.accounting.common import PaymentStatus
from Backend.models.accounting.payment import Payment
from Backend.models.enums import UserType
from Backend.models.lease import Lease
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.utils.datetime_utils import date_to_utc_range


logger = logging.getLogger(__name__)


# === Helper Functions for Payment Queries ===
async def get_month_payments(session: AsyncSession, lease_id: int, month_date: date) -> bool:
    """
    Checks if any payment exists for a given lease within the specified month.

    Args:
        session: Async database session.
        lease_id: The ID of the lease to check payments for.
        month_date: A date within the month to check.

    Returns:
        True if at least one payment exists for the lease in the specified month, otherwise False.
    """
    month_start = month_date.replace(day=1)
    if month_start.month == 12:
        month_end = month_start.replace(
            year=month_start.year + 1, month=1, day=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1, day=1)

    query = select(col(Payment.id)).where(
        and_(
            col(Payment.lease_id) == lease_id,
            col(Payment.payment_date) >= month_start,
            col(Payment.payment_date) < month_end
        )
    ).limit(1)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


# === Unified Payment Query Builder ===
async def build_payments_query(
    session: AsyncSession,
    current_user: User,
    lease_id: int | None = None,
    property_id: int | None = None,
    tenant_id: int | None = None,
    payment_status: PaymentStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> Select:
    """
    Builds a comprehensive payment query with role-based filtering and common filters.

    This unified function replaces the previous chain of query builders, providing a single
    entry point for constructing payment queries based on user role and filter criteria.

    Args:
        session: Database session (needed for tenant profile lookup)
        current_user: The user making the request
        lease_id: Optional filter by lease ID
        property_id: Optional filter by property ID
        tenant_id: Optional filter by tenant ID
        payment_status: Optional filter by payment status
        start_date: Optional filter for payments on or after this date
        end_date: Optional filter for payments on or before this date

    Returns:
        A SQLAlchemy Select query ready for execution

    Raises:
        HTTPException: For authorization errors (tenant access violations)
    """
    # Start with base query including eager loading
    query = select(Payment).options(
        selectinload(getattr(Payment, "lease")).options(
            selectinload(getattr(Lease, "property")),
            selectinload(getattr(Lease, "tenant"))
        )
    )

    # Apply common filters (lease, status, dates)
    filters = []

    if lease_id:
        filters.append(col(Payment.lease_id) == lease_id)
    if payment_status:
        filters.append(col(Payment.status) == payment_status)
    if start_date:
        start_datetime, _ = date_to_utc_range(start_date, start_date)
        filters.append(col(Payment.payment_date) >= start_datetime)
    if end_date:
        _, end_datetime = date_to_utc_range(end_date, end_date)
        filters.append(col(Payment.payment_date) <= end_datetime)

    # Apply role-based filtering
    if current_user.user_type == UserType.TENANT:
        # Tenant-specific logic
        tenant_query = select(Tenant).where(
            col(Tenant.user_id) == current_user.id)
        user_tenant = await session.scalar(tenant_query)

        if not user_tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenant profile found for user. Access denied."
            )

        if tenant_id and tenant_id != user_tenant.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access payments for other tenants."
            )

        if property_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenants cannot filter payments by property."
            )

        filters.append(col(Payment.tenant_id) == user_tenant.id)

    elif current_user.user_type == UserType.LANDLORD:
        # Landlord-specific logic using subquery for owned leases
        owned_leases_query = (
            select(Lease.id)
            .join(Property)
            .where(Property.user_id == current_user.id)
        )

        if property_id:
            owned_leases_query = owned_leases_query.where(
                Property.id == property_id)

        # Use inner join to exclude orphaned payments
        owned = owned_leases_query.subquery()
        query = query.join(owned, owned.c.id == Payment.lease_id)

        if tenant_id:
            filters.append(col(Payment.tenant_id) == tenant_id)

    elif current_user.is_admin:
        # Admin-specific logic
        if property_id:
            query = query.join(getattr(Payment, "lease"), isouter=True).join(
                getattr(Lease, "property"), isouter=True
            )
            filters.append(col(Property.id) == property_id)

        if tenant_id:
            filters.append(col(Payment.tenant_id) == tenant_id)
    else:
        # Unknown user type - raise exception instead of silently returning empty results
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unknown user type '{current_user.user_type}' - access denied"
        )

    # Apply all collected filters
    if filters:
        query = query.where(and_(*filters))

    return query


# === Orphaned Payment Detection Functions ===
def get_user_id_from_direct_relationship(payment: Payment) -> UUID | None:
    """Strategy 1: Get user ID from the direct payment -> lease -> property -> user relationship."""
    if payment.lease and payment.lease.property and payment.lease.property.user_id:
        return payment.lease.property.user_id
    return None


async def get_user_id_from_lease_query(payment: Payment, session: AsyncSession) -> UUID | None:
    """Strategy 2: If lease relationship is broken, query for the lease directly."""
    if not payment.lease_id:
        return None
    try:
        lease_query = select(Lease).options(
            selectinload(getattr(Lease, "property"))
        ).where(col(Lease.id) == payment.lease_id)
        lease_result = await session.execute(lease_query)
        lease_obj = lease_result.scalar_one_or_none()
        if lease_obj and lease_obj.property:
            return lease_obj.property.user_id
    except Exception:
        logger.exception(
            "Error during direct lease query in orphan check for payment %s", payment.id)
    return None


async def get_user_id_from_tenant_query(payment: Payment, session: AsyncSession) -> UUID | None:
    """Strategy 3: If tenant_id is available, find the user through tenant's other leases."""
    if not payment.tenant_id:
        return None
    try:
        tenant_property_query = select(Property.user_id).join(
            Lease, col(Lease.property_id) == col(Property.id)
        ).where(col(Lease.tenant_id) == payment.tenant_id).distinct()
        property_user_ids = (await session.execute(tenant_property_query)).scalars().all()
        if len(property_user_ids) == 1:
            return property_user_ids[0]
    except Exception:
        logger.exception(
            "Error during tenant property user lookup in orphan check for payment %s", payment.id)
    return None


async def get_affected_user_ids_concurrently(payments: Iterable[Payment], session: AsyncSession) -> Set[UUID]:
    """Aggregates unique user IDs from a list of orphaned payments using multiple strategies, running DB queries concurrently."""
    affected_user_ids: Set[UUID] = set()

    # First pass: Handle synchronous checks
    remaining_payments = []
    for payment in payments:
        user_id = get_user_id_from_direct_relationship(payment)
        if user_id:
            affected_user_ids.add(user_id)
        else:
            remaining_payments.append(payment)

    # Second pass: Create concurrent tasks for DB-bound checks
    tasks = []
    for payment in remaining_payments:
        tasks.append(get_user_id_from_lease_query(payment, session))
        tasks.append(get_user_id_from_tenant_query(payment, session))

    # Run all tasks concurrently and process results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, UUID):
            affected_user_ids.add(result)
        elif result is not None:
            logger.error(
                "An unexpected error occurred during concurrent user ID fetching: %s", result)

    return affected_user_ids


def log_orphan_report(orphaned_count: int, users_with_orphans_count: int, orphaned_ids_list: list[str], current_user: User | None = None) -> None:
    """Logs a formatted report about orphaned payments for single-user or global scans."""
    log_context = f"for user {current_user.id}" if current_user else f"across {users_with_orphans_count} user(s)"

    log_level = logging.ERROR if orphaned_count > 10 else logging.WARNING
    message_prefix = "Critical data integrity issue" if log_level == logging.ERROR else "Data integrity alert"

    logger.log(
        log_level,
        "%s: Found %d unique orphaned lease-related payment(s) %s. "
        "Payment IDs: %s. These payments reference lease_id but have broken lease/property relationships "
        "and will not appear in landlord queries. Consider data cleanup.",
        message_prefix, orphaned_count, log_context, ", ".join(
            orphaned_ids_list[:10])
    )


async def check_for_orphaned_payments(session: AsyncSession, current_user: User, run_for_all_users: bool = False) -> dict:
    """
    Checks for payments that reference a lease but have missing or broken lease or property relationships.

    This function identifies "orphaned" payments—those with a lease_id but lacking a valid lease or property association. Payments without a lease_id are not considered orphaned. Returns a report indicating whether orphaned payments exist, the total count, the number of affected users, and up to 10 orphaned payment IDs. Handles both single-user and global scans based on the `run_for_all_users` flag. Logs warnings or errors if orphaned payments are found.
    """
    try:
        # Define base conditions for orphaned payments
        conditions = [
            col(Payment.lease_id).is_not(None),
            or_(
                col(Lease.id).is_(None),
                and_(
                    col(Lease.id).is_not(None),
                    col(Lease.property_id).is_not(None),
                    col(Property.id).is_(None)
                )
            )
        ]

        # Conditionally add the ownership filter
        if not run_for_all_users:
            conditions.append(
                or_(
                    col(Property.user_id) == current_user.id,
                    col(Property.user_id).is_(None)
                )
            )

        # Build the final query
        orphaned_query = select(Payment).outerjoin(
            getattr(Payment, "lease")
        ).outerjoin(
            getattr(Lease, "property")
        ).where(and_(*conditions))

        payments = (await session.execute(orphaned_query)).scalars().all()
        unique_payment_ids = {p.id for p in payments if p.id is not None}
        orphaned_count = len(unique_payment_ids)

        if orphaned_count > 0:
            orphaned_ids_list = [str(pid) for pid in unique_payment_ids]
            users_with_orphans_count = 1

            if run_for_all_users:
                affected_user_ids = await get_affected_user_ids_concurrently(payments, session)
                users_with_orphans_count = len(affected_user_ids)
                log_orphan_report(
                    orphaned_count, users_with_orphans_count, orphaned_ids_list)
            else:
                log_orphan_report(orphaned_count, 1,
                                 orphaned_ids_list, current_user)

            return {
                "orphaned_payments": True,
                "total_orphaned_count": orphaned_count,
                "users_with_orphans": users_with_orphans_count,
                "orphaned_payment_ids": orphaned_ids_list[:10]
            }

    except Exception as e:
        # Don't let monitoring failures break the main query
        logger.exception(
            "Error during orphaned payment monitoring for user %s: %s", current_user.id, e)

    # Default return if no orphans or an error occurred
    return {
        "orphaned_payments": False,
        "total_orphaned_count": 0,
        "users_with_orphans": 0,
        "orphaned_payment_ids": []
    }
