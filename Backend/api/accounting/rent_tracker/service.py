"""
Service layer for rent tracker business logic.
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col

from Backend.models.accounting.payment import Payment
from Backend.models.accounting.common import PaymentStatus
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.user import User
from Backend.models.enums import UserType

from .schemas import (
    RentTrackingEntry,
    RentTrackerSummary,
    RentStatus,
    RentTrackerFilter
)
from .helpers import (
    calculate_month_bounds,
    determine_rent_status,
    get_tenant_display_name,
    get_property_display_name,
    get_unit_display_name,
    calculate_collection_rate,
    calculate_rent_due_date
)


logger = logging.getLogger(__name__)


class RentTrackerService:
    """Service class for rent tracking operations."""
    
    @staticmethod
    async def get_rent_tracker(
        *,
        session: AsyncSession,
        current_user: User,
        filters: RentTrackerFilter
    ) -> List[RentTrackingEntry]:
        """
        Get rent tracking entries for the specified filters.
        
        Args:
            session: Database session
            current_user: Current authenticated user
            filters: Filter parameters for the query
            
        Returns:
            List of rent tracking entries
            
        Raises:
            HTTPException: If user is not authorized or database error occurs
        """
        # Check authorization
        if not RentTrackerService._check_authorization(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view rent tracker"
            )
        
        try:
            # Calculate date range
            month_start, month_end = calculate_month_bounds(filters.month, filters.year)
            
            logger.info("Getting rent tracker for period: %s to %s", month_start, month_end)
            
            # Get active leases with optimized query
            leases = await RentTrackerService._get_active_leases(
                session=session,
                current_user=current_user,
                property_id=filters.property_id,
                month_start=month_start,
                month_end=month_end
            )
            
            logger.info("Found %d active leases", len(leases))
            
            # Process leases and create tracking entries
            entries = []
            for lease in leases:
                entry = await RentTrackerService._create_tracking_entry(
                    session=session,
                    lease=lease,
                    month_start=month_start,
                    month_end=month_end,
                    filters=filters
                )
                if entry and (filters.status is None or entry.status == filters.status):
                    entries.append(entry)
            
            # Add vacant units if requested
            if filters.include_vacant:
                vacant_entries = await RentTrackerService._get_vacant_unit_entries(
                    session=session,
                    current_user=current_user,
                    property_id=filters.property_id,
                    month_start=month_start,
                    month_end=month_end,
                    existing_entries=entries
                )
                # Filter vacant entries by status if specified
                for entry in vacant_entries:
                    if filters.status is None or entry.status == filters.status:
                        entries.append(entry)
            
            logger.info("Generated %d rent tracker entries", len(entries))
            
            # Sort entries by status priority (OVERDUE first) and then by property/unit
            entries.sort(key=lambda x: (
                0 if x.status == RentStatus.OVERDUE else
                1 if x.status == RentStatus.DUE else
                2 if x.status == RentStatus.PARTIAL else 3,
                x.property_name,
                x.unit_name or ""
            ))
            
            return entries
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get rent tracker: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get rent tracker: {str(e)}"
            )
    
    @staticmethod
    async def get_rent_tracker_summary(
        *,
        session: AsyncSession,
        current_user: User,
        filters: RentTrackerFilter
    ) -> RentTrackerSummary:
        """
        Get summary statistics for rent tracking.
        
        Args:
            session: Database session
            current_user: Current authenticated user
            filters: Filter parameters for the query
            
        Returns:
            Rent tracker summary with statistics
            
        Raises:
            HTTPException: If user is not authorized or database error occurs
        """
        # Check authorization
        if not RentTrackerService._check_authorization(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view rent tracker summary"
            )
        
        try:
            # Calculate date range
            month_start, month_end = calculate_month_bounds(filters.month, filters.year)
            
            logger.info("Getting rent tracker summary for period: %s to %s", month_start, month_end)
            
            # Get active leases with aggregated data
            summary_data = await RentTrackerService._get_summary_aggregation(
                session=session,
                current_user=current_user,
                property_id=filters.property_id,
                month_start=month_start,
                month_end=month_end
            )
            
            return summary_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get rent tracker summary: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get rent tracker summary: {str(e)}"
            )
    
    @staticmethod
    def _check_authorization(current_user: User) -> bool:
        """
        Check if user is authorized to access rent tracker.
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            True if authorized, False otherwise
        """
        # Admin users have full access
        if current_user.is_admin:
            return True
        
        # Landlord users can access their own rent tracking data
        return current_user.user_type == UserType.LANDLORD
    
    @staticmethod
    async def _get_active_leases(
        session: AsyncSession,
        current_user: User,
        property_id: Optional[int],
        month_start: date,
        month_end: date
    ) -> List[Lease]:
        """
        Get active leases for the specified period with optimized loading.
        
        Args:
            session: Database session
            current_user: Current user
            property_id: Optional property filter
            month_start: Start of the period
            month_end: End of the period
            
        Returns:
            List of active leases with relationships loaded
        """
        # Build query conditions
        conditions = [
            col(Lease.start_date) <= month_end,
            or_(
                col(Lease.end_date) >= month_start,
                col(Lease.end_date).is_(None)
            ),
            col(Lease.status) == LeaseStatus.ACTIVE
        ]
        
        # Add property filter if specified
        if property_id is not None:
            conditions.append(col(Lease.property_id) == property_id)
        
        # Filter by user's properties (non-admin users)
        if not current_user.is_admin:
            # Join with Property to filter by user ownership
            query = (
                select(Lease)
                .join(Property, col(Lease.property_id) == col(Property.id))
                .where(
                    and_(
                        col(Property.user_id) == current_user.id,
                        *conditions
                    )
                )
            )
        else:
            # Admin can see all leases
            query = select(Lease).where(and_(*conditions))
        
        # Eagerly load relationships to avoid N+1 queries
        # Use getattr() to dynamically access relationship attributes for forward reference compatibility
        query = query.options(
            selectinload(getattr(Lease, "property")),
            selectinload(getattr(Lease, "tenant")),
            selectinload(getattr(Lease, "unit"))
        )
        
        result = await session.execute(query)
        return list(result.scalars())
    
    @staticmethod
    async def _create_tracking_entry(
        session: AsyncSession,
        lease: Lease,
        month_start: date,
        month_end: date,
        filters: RentTrackerFilter
    ) -> Optional[RentTrackingEntry]:
        """
        Create a rent tracking entry for a single lease.
        
        Args:
            session: Database session
            lease: Lease to create entry for
            month_start: Start of the tracking period
            month_end: End of the tracking period
            filters: Filter parameters
            
        Returns:
            RentTrackingEntry or None if lease should be skipped
        """
        # Skip leases without IDs
        if lease.id is None:
            logger.warning("Skipping lease with no ID: %s", lease)
            return None
        
        # Calculate payments for this lease
        amount_paid = await RentTrackerService._calculate_lease_payments(
            session=session,
            lease_id=lease.id,
            month_start=month_start,
            month_end=month_end
        )
        
        # Get the last payment date
        last_payment_date = await RentTrackerService._get_last_payment_date(
            session=session,
            lease_id=lease.id,
            month_start=month_start,
            month_end=month_end
        )
        
        # Calculate due date and status
        due_date = calculate_rent_due_date(lease, month_start.month, month_start.year)
        rent_status, days_overdue = determine_rent_status(
            monthly_rent=lease.monthly_rent,
            amount_paid=amount_paid,
            due_date=due_date,
            current_date=date.today()
        )
        
        # Calculate remaining due
        remaining_due = max(Decimal("0"), lease.monthly_rent - amount_paid)
        
        # Get display names
        tenant_name = get_tenant_display_name(lease.tenant)
        property_name = get_property_display_name(lease)
        unit_name = get_unit_display_name(lease.unit)
        
        return RentTrackingEntry(
            lease_id=lease.id,
            tenant_id=lease.tenant_id if lease.tenant_id else None,
            tenant_name=tenant_name,
            property_name=property_name,
            unit_name=unit_name,
            monthly_rent=lease.monthly_rent,
            amount_paid=amount_paid,
            remaining_due=remaining_due,
            status=rent_status,
            due_date=due_date,
            last_payment_date=last_payment_date,
            days_overdue=days_overdue
        )
    
    @staticmethod
    async def _calculate_lease_payments(
        session: AsyncSession,
        lease_id: int,
        month_start: date,
        month_end: date
    ) -> Decimal:
        """
        Calculate total payments for a lease in the specified period.
        
        Args:
            session: Database session
            lease_id: ID of the lease
            month_start: Start of the period
            month_end: End of the period
            
        Returns:
            Total payment amount
        """
        query = select(func.coalesce(func.sum(Payment.amount), Decimal("0.0"))).where(
            and_(
                col(Payment.lease_id) == lease_id,
                col(Payment.payment_date) >= month_start,
                col(Payment.payment_date) <= month_end,
                col(Payment.status).in_([PaymentStatus.PAID, PaymentStatus.PARTIAL])
            )
        )
        
        result = await session.execute(query)
        return result.scalar() or Decimal("0.0")
    
    @staticmethod
    async def _get_last_payment_date(
        session: AsyncSession,
        lease_id: int,
        month_start: date,
        month_end: date
    ) -> Optional[date]:
        """
        Get the date of the most recent payment for a lease.
        
        Args:
            session: Database session
            lease_id: ID of the lease
            month_start: Start of the period
            month_end: End of the period
            
        Returns:
            Date of last payment or None
        """
        query = select(func.max(Payment.payment_date)).where(
            and_(
                col(Payment.lease_id) == lease_id,
                col(Payment.payment_date) >= month_start,
                col(Payment.payment_date) <= month_end,
                col(Payment.status).in_([PaymentStatus.PAID, PaymentStatus.PARTIAL])
            )
        )
        
        result = await session.execute(query)
        return result.scalar()
    
    @staticmethod
    async def _get_summary_aggregation(
        session: AsyncSession,
        current_user: User,
        property_id: Optional[int],
        month_start: date,
        month_end: date
    ) -> RentTrackerSummary:
        """
        Get summary statistics using database aggregation for better performance.
        
        Args:
            session: Database session
            current_user: Current user
            property_id: Optional property filter
            month_start: Start of the period
            month_end: End of the period
            
        Returns:
            RentTrackerSummary with aggregated statistics
        """
        # Get active leases for the period
        leases = await RentTrackerService._get_active_leases(
            session=session,
            current_user=current_user,
            property_id=property_id,
            month_start=month_start,
            month_end=month_end
        )
        
        if not leases:
            # Return empty summary if no leases found
            return RentTrackerSummary(
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
        
        # Extract lease IDs for payment aggregation
        lease_ids = [lease.id for lease in leases if lease.id is not None]
        
        # Aggregate payment data for all leases in one query
        if lease_ids:
            payment_query = (
                select(
                    col(Payment.lease_id),
                    func.coalesce(func.sum(Payment.amount), Decimal("0.0")).label("total_paid")
                )
                .where(
                    and_(
                        col(Payment.lease_id).in_(lease_ids),
                        col(Payment.payment_date) >= month_start,
                        col(Payment.payment_date) <= month_end,
                        col(Payment.status).in_([PaymentStatus.PAID, PaymentStatus.PARTIAL])
                    )
                )
                .group_by(col(Payment.lease_id))
            )
            
            result = await session.execute(payment_query)
            payment_data = {row.lease_id: row.total_paid for row in result}
        else:
            payment_data = {}
        
        # Calculate summary statistics
        total_units = len(leases)
        total_expected = Decimal("0.00")
        total_collected = Decimal("0.00")
        units_paid = 0
        units_partial = 0
        units_due = 0
        units_overdue = 0
        
        current_date = date.today()
        
        for lease in leases:
            if lease.id is None:
                continue
                
            monthly_rent = lease.monthly_rent
            amount_paid = payment_data.get(lease.id, Decimal("0.00"))
            
            total_expected += monthly_rent
            total_collected += amount_paid
            
            # Calculate due date and determine status
            due_date = calculate_rent_due_date(lease, month_start.month, month_start.year)
            rent_status, _ = determine_rent_status(
                monthly_rent=monthly_rent,
                amount_paid=amount_paid,
                due_date=due_date,
                current_date=current_date
            )
            
            # Count units by status
            if rent_status == RentStatus.PAID:
                units_paid += 1
            elif rent_status == RentStatus.PARTIAL:
                units_partial += 1
            elif rent_status == RentStatus.DUE:
                units_due += 1
            elif rent_status == RentStatus.OVERDUE:
                units_overdue += 1
        
        total_outstanding = total_expected - total_collected
        collection_rate = calculate_collection_rate(total_expected, total_collected)
        
        return RentTrackerSummary(
            total_units=total_units,
            total_expected=total_expected,
            total_collected=total_collected,
            total_outstanding=total_outstanding,
            units_paid=units_paid,
            units_partial=units_partial,
            units_due=units_due,
            units_overdue=units_overdue,
            collection_rate=collection_rate
        )
    
    @staticmethod
    async def _get_vacant_unit_entries(
        session: AsyncSession,
        current_user: User,
        property_id: Optional[int],
        month_start: date,
        month_end: date,
        existing_entries: List[RentTrackingEntry]
    ) -> List[RentTrackingEntry]:
        """
        Get tracking entries for vacant units (units without active leases for the period).
        
        Args:
            session: Database session
            current_user: Current user
            property_id: Optional property filter
            month_start: Start of the period
            month_end: End of the period
            existing_entries: Already processed entries to avoid duplicates
            
        Returns:
            List of vacant unit tracking entries
        """
        # Get unit IDs that already have entries (occupied units)
        occupied_unit_ids = {
            entry.unit_name for entry in existing_entries 
            if entry.unit_name is not None
        }
        
        # Build query for all property units
        query = (
            select(PropertyUnit, Property)
            .join(Property, col(PropertyUnit.property_id) == col(Property.id))
        )
        
        # Add property filter if specified
        if property_id is not None:
            query = query.where(col(PropertyUnit.property_id) == property_id)
        
        # Filter by user's properties (non-admin users)
        if not current_user.is_admin:
            query = query.where(col(Property.user_id) == current_user.id)
        
        result = await session.execute(query)
        all_units = result.fetchall()
        
        vacant_entries = []
        for unit_row in all_units:
            unit, property_obj = unit_row
            
            # Skip if unit already has an entry (occupied)
            unit_identifier = unit.unit_number or f"Unit {unit.id}"
            if unit_identifier in occupied_unit_ids:
                continue
            
            # Check if unit has an active lease for this period
            lease_check = await session.execute(
                select(Lease)
                .where(
                    col(Lease.unit_id) == unit.id,
                    col(Lease.start_date) <= month_end,
                    or_(
                        col(Lease.end_date) >= month_start,
                        col(Lease.end_date).is_(None)
                    ),
                    col(Lease.status) == LeaseStatus.ACTIVE
                )
            )
            
            if lease_check.fetchone():
                # Unit has an active lease, skip
                continue
            
            # Create vacant unit entry
            vacant_entry = RentTrackingEntry(
                lease_id=0,  # No lease for vacant unit
                tenant_id=None,
                tenant_name="Vacant",
                property_name=property_obj.name,
                unit_name=unit_identifier,
                monthly_rent=unit.rent_amount or Decimal("0.00"),
                amount_paid=Decimal("0.00"),
                remaining_due=unit.rent_amount or Decimal("0.00"),
                status=RentStatus.DUE,  # Vacant units are considered DUE
                due_date=month_start,  # Due at start of period
                last_payment_date=None,
                days_overdue=None
            )
            
            vacant_entries.append(vacant_entry)
        
        return vacant_entries