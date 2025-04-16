import logging
from typing import List, Optional
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func, text
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from decimal import Decimal
from enum import Enum

from Backend.database import get_session
from Backend.models.accounting import Payment, PaymentStatus
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.api.auth import get_current_user

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

@router.get("/", response_model=List[RentTrackingEntry])
async def get_rent_tracker(
    month: Optional[int] = None,
    year: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get monthly rent tracking status for all active leases"""
    # Convert user_type to uppercase string for case-insensitive comparison
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    
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
        
        logger.info(f"Getting rent tracker for period: {month_start} to {month_end}")
        
        # Get all active leases with related tenant and property information
        query = select(Lease).where(
            and_(
                Lease.start_date <= month_end,
                or_(Lease.end_date >= month_start, Lease.end_date.is_(None)),
                Lease.status == LeaseStatus.ACTIVE
            )
        ).options(
            selectinload(Lease.property),
            selectinload(Lease.tenant)
        )
        
        result = await session.execute(query)
        active_leases = result.scalars().all()
        
        logger.info(f"Found {len(active_leases)} active leases")
        
        rent_tracker_entries = []
        
        for lease in active_leases:
            # Get payments for this lease in the current month
            payments_query = select(func.coalesce(func.sum(Payment.amount), 0.0)).where(
                and_(
                    Payment.lease_id == lease.id,
                    Payment.payment_date >= month_start,
                    Payment.payment_date <= month_end,
                    Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL])
                )
            )
            
            payment_result = await session.execute(payments_query)
            amount_paid = payment_result.scalar()
            
            # Calculate remaining due and determine status
            remaining_due = lease.monthly_rent - amount_paid
            
            if remaining_due <= 0:
                status = RentStatus.PAID
            elif amount_paid > 0:
                status = RentStatus.PARTIAL
            else:
                status = RentStatus.DUE
            
            # Get tenant name
            tenant_name = "Unknown Tenant"
            if lease.tenant:
                if hasattr(lease.tenant, 'full_name') and lease.tenant.full_name:
                    tenant_name = lease.tenant.full_name
                elif hasattr(lease.tenant, 'first_name') and lease.tenant.first_name:
                    tenant_name = f"{lease.tenant.first_name} {lease.tenant.last_name or ''}"
                else:
                    tenant_name = f"Tenant #{lease.tenant_id}"
            
            # Get property name
            property_name = "Unknown Property"
            if lease.property:
                property_name = lease.property.name
            
            # Create rent tracking entry
            rent_tracker_entry = RentTrackingEntry(
                lease_id=lease.id,
                tenant_name=tenant_name,
                property_name=property_name,
                monthly_rent=float(lease.monthly_rent),
                amount_paid=float(amount_paid),
                remaining_due=float(remaining_due),
                status=status
            )
            
            rent_tracker_entries.append(rent_tracker_entry)
        
        logger.info(f"Generated {len(rent_tracker_entries)} rent tracker entries")
        return rent_tracker_entries
        
    except Exception as e:
        logger.error(f"Failed to get rent tracker: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rent tracker: {str(e)}"
        ) 