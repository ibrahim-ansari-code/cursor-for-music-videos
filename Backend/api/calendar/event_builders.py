"""
Calendar Event Builders

Functions that build CalendarEvent objects from various source tables.
This is the core of the "virtual calendar" approach - events are computed
on-demand rather than stored in a projection table.
"""
from sqlmodel import select, and_, or_, col
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime, timezone

from Backend.models.calendar import (
    CalendarEvent,
    CalendarEventType,
    CalendarEventPriority,
    CustomReminder
)
from Backend.models.accounting.invoice import Invoice
from Backend.models.accounting.common import PaymentStatus
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.maintenance import MaintenanceRequest, MaintenanceStatus
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from .helpers import (
    compute_event_status,
    compute_event_color,
    get_quick_actions,
    format_event_title,
    days_until
)
from .schemas import CalendarFilters


def _get_tenant_name(tenant) -> str:
    """Helper to get tenant name from Tenant model"""
    if not tenant:
        return "Unknown Tenant"
    if tenant.company_name:
        return tenant.company_name
    if tenant.first_name or tenant.last_name:
        return f"{tenant.first_name or ''} {tenant.last_name or ''}".strip()
    return "Unknown Tenant"


async def build_invoice_events(
    session: AsyncSession,
    property_ids: List[int],
    from_date: datetime,
    to_date: datetime,
    filters: CalendarFilters
) -> List[CalendarEvent]:
    """Build calendar events from invoices"""
    
    query = (
        select(Invoice)
        .options(
            selectinload(getattr(Invoice, "property")),
            selectinload(getattr(Invoice, "tenant"))
        )
        .where(
            and_(
                col(Invoice.property_id).in_(property_ids),
                col(Invoice.due_date) >= from_date,
                col(Invoice.due_date) <= to_date
            )
        )
    )
    
    # Apply filters
    if filters.tenant_id:
        query = query.where(col(Invoice.tenant_id) == filters.tenant_id)
    
    result = await session.execute(query)
    invoices = result.scalars().all()
    
    events = []
    for invoice in invoices:
        is_completed = invoice.status == PaymentStatus.PAID
        status = compute_event_status(invoice.due_date, is_completed, CalendarEventType.INVOICE_DUE)
        
        # Skip if status filter doesn't match
        if filters.status and status != filters.status:
            continue
        
        property_name = invoice.property.name if invoice.property else "Unknown Property"
        tenant_name = _get_tenant_name(invoice.tenant)
        
        event = CalendarEvent(
            id=f"invoice_{invoice.id}",
            type=CalendarEventType.INVOICE_DUE,
            title=f"Invoice #{invoice.invoice_number} Due",
            description=invoice.description,
            start_at=invoice.due_date,
            end_at=None,
            all_day=True,
            status=status,
            priority=CalendarEventPriority.HIGH if invoice.amount > 1000 else CalendarEventPriority.MEDIUM,
            property_id=invoice.property_id,
            property_name=property_name,
            unit_id=None,
            tenant_id=invoice.tenant_id,
            tenant_name=tenant_name,
            lease_id=None,
            source_type="invoice",
            source_id=str(invoice.id) if invoice.id else "unknown",
            color=compute_event_color(status),
            quick_actions=get_quick_actions(CalendarEventType.INVOICE_DUE, invoice.status),
            metadata={
                "amount": float(invoice.amount),
                "invoice_number": invoice.invoice_number,
                "status": invoice.status.value,
                "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None
            }
        )
        events.append(event)
    
    return events


async def build_lease_events(
    session: AsyncSession,
    property_ids: List[int],
    from_date: datetime,
    to_date: datetime,
    filters: CalendarFilters
) -> List[CalendarEvent]:
    """
    Build calendar events from leases.
    Creates two events per lease: start and expiring.
    """
    
    query = (
        select(Lease)
        .options(
            selectinload(getattr(Lease, "property")),
            selectinload(getattr(Lease, "tenant"))
        )
        .where(
            and_(
                col(Lease.property_id).in_(property_ids),
                col(Lease.status) == LeaseStatus.ACTIVE,
                or_(
                    and_(col(Lease.start_date) >= from_date.date(), col(Lease.start_date) <= to_date.date()),
                    and_(col(Lease.end_date) >= from_date.date(), col(Lease.end_date) <= to_date.date())
                )
            )
        )
    )
    
    # Apply filters
    if filters.tenant_id:
        query = query.where(col(Lease.tenant_id) == filters.tenant_id)
    
    result = await session.execute(query)
    leases = result.scalars().all()
    
    events = []
    
    for lease in leases:
        property_name = lease.property.name if lease.property else "Unknown Property"
        tenant_name = _get_tenant_name(lease.tenant)
        
        # Lease Start Event
        if from_date.date() <= lease.start_date <= to_date.date():
            # Only show if upcoming or recently started
            start_datetime = datetime.combine(lease.start_date, datetime.min.time(), tzinfo=timezone.utc)
            is_past = start_datetime < datetime.now(timezone.utc)
            
            if not is_past or days_until(start_datetime) >= -7:  # Show for 7 days after start
                status = compute_event_status(start_datetime, is_past, CalendarEventType.LEASE_START)
                
                if not filters.status or status == filters.status:
                    event = CalendarEvent(
                        id=f"lease_start_{lease.id}",
                        type=CalendarEventType.LEASE_START,
                        title=f"Lease Start - {tenant_name}",
                        description=f"Lease begins at {property_name}",
                        start_at=start_datetime,
                        end_at=None,
                        all_day=True,
                        status=status,
                        priority=CalendarEventPriority.MEDIUM,
                        property_id=lease.property_id,
                        property_name=property_name,
                        unit_id=lease.unit_id,
                        tenant_id=lease.tenant_id,
                        tenant_name=tenant_name,
                        lease_id=lease.id,
                        source_type="lease",
                        source_id=str(lease.id) if lease.id else "unknown",
                        color=compute_event_color(status),
                        quick_actions=get_quick_actions(CalendarEventType.LEASE_START),
                        metadata={
                            "lease_id": lease.id,
                            "monthly_rent": float(lease.monthly_rent),
                            "end_date": lease.end_date.isoformat()
                        }
                    )
                    events.append(event)
        
        # Lease Expiring Event
        if from_date.date() <= lease.end_date <= to_date.date():
            end_datetime = datetime.combine(lease.end_date, datetime.min.time(), tzinfo=timezone.utc)
            is_past = end_datetime < datetime.now(timezone.utc)
            status = compute_event_status(end_datetime, is_past, CalendarEventType.LEASE_EXPIRING)
            
            if not filters.status or status == filters.status:
                days_left = days_until(end_datetime)
                days_info = f"{days_left} days" if days_left > 0 else "Expired"
                
                event = CalendarEvent(
                    id=f"lease_expiring_{lease.id}",
                    type=CalendarEventType.LEASE_EXPIRING,
                    title=format_event_title(
                        CalendarEventType.LEASE_EXPIRING,
                        tenant_name,
                        additional_info=days_info
                    ),
                    description=f"Lease at {property_name} expires. Consider renewal.",
                    start_at=end_datetime,
                    end_at=None,
                    all_day=True,
                    status=status,
                    priority=CalendarEventPriority.HIGH,
                    property_id=lease.property_id,
                    property_name=property_name,
                unit_id=lease.unit_id,
                tenant_id=lease.tenant_id,
                tenant_name=tenant_name,
                lease_id=lease.id,
                source_type="lease",
                source_id=str(lease.id) if lease.id else "unknown",
                color=compute_event_color(status),
                    quick_actions=get_quick_actions(CalendarEventType.LEASE_EXPIRING),
                    metadata={
                        "lease_id": lease.id,
                        "monthly_rent": float(lease.monthly_rent),
                        "start_date": lease.start_date.isoformat(),
                        "is_renewable": lease.is_renewable,
                        "auto_renew": lease.auto_renew
                    }
                )
                events.append(event)
    
    return events


async def build_maintenance_events(
    session: AsyncSession,
    property_ids: List[int],
    from_date: datetime,
    to_date: datetime,
    filters: CalendarFilters
) -> List[CalendarEvent]:
    """Build calendar events from maintenance requests"""
    
    query = (
        select(MaintenanceRequest)
        .options(
            selectinload(getattr(MaintenanceRequest, "property")),
            selectinload(getattr(MaintenanceRequest, "tenant"))
        )
        .where(
            and_(
                col(MaintenanceRequest.property_id).in_(property_ids),
                col(MaintenanceRequest.scheduled_date).isnot(None),
                col(MaintenanceRequest.scheduled_date) >= from_date.date(),
                col(MaintenanceRequest.scheduled_date) <= to_date.date()
            )
        )
    )
    
    # Apply filters
    if filters.tenant_id:
        query = query.where(col(MaintenanceRequest.tenant_id) == filters.tenant_id)
    
    result = await session.execute(query)
    maintenance_requests = result.scalars().all()
    
    events = []
    for request in maintenance_requests:
        if not request.scheduled_date:
            continue
        scheduled_datetime = datetime.combine(request.scheduled_date, datetime.min.time(), tzinfo=timezone.utc)
        is_completed = request.status == MaintenanceStatus.COMPLETED
        status = compute_event_status(scheduled_datetime, is_completed, CalendarEventType.MAINTENANCE_SCHEDULED)
        
        # Skip if status filter doesn't match
        if filters.status and status != filters.status:
            continue
        
        property_name = request.property.name if request.property else "Unknown Property"
        tenant_name = _get_tenant_name(request.tenant)
        
        # Determine priority based on maintenance priority
        priority_map = {
            "LOW": CalendarEventPriority.LOW,
            "MEDIUM": CalendarEventPriority.MEDIUM,
            "HIGH": CalendarEventPriority.HIGH,
            "EMERGENCY": CalendarEventPriority.HIGH
        }
        priority = priority_map.get(request.priority.value, CalendarEventPriority.MEDIUM)
        
        event = CalendarEvent(
            id=f"maintenance_{request.id}",
            type=CalendarEventType.MAINTENANCE_SCHEDULED,
            title=f"Maintenance: {request.issue_title}",
            description=request.description,
            start_at=scheduled_datetime,
            end_at=None,
            all_day=True,
            status=status,
            priority=priority,
            property_id=request.property_id,
            property_name=property_name,
            unit_id=request.unit_id,
            tenant_id=request.tenant_id,
            tenant_name=tenant_name,
            lease_id=None,
            source_type="maintenance",
            source_id=str(request.id) if request.id else "unknown",
            color=compute_event_color(status),
            quick_actions=get_quick_actions(CalendarEventType.MAINTENANCE_SCHEDULED, request.status),
            metadata={
                "issue_title": request.issue_title,
                "priority": request.priority.value,
                "status": request.status.value,
                "assigned_to": request.assigned_to,
                "estimated_cost": float(request.estimated_cost) if request.estimated_cost else None
            }
        )
        events.append(event)
    
    return events


async def build_property_expiry_events(
    session: AsyncSession,
    property_ids: List[int],
    from_date: datetime,
    to_date: datetime,
    filters: CalendarFilters
) -> List[CalendarEvent]:
    """Build calendar events from property expiry dates (insurance, mortgage)"""
    
    query = (
        select(Property)
        .where(
            and_(
                col(Property.id).in_(property_ids),
                or_(
                    and_(
                        col(Property.insurance_expiry_date).isnot(None),
                        col(Property.insurance_expiry_date) >= from_date.date(),
                        col(Property.insurance_expiry_date) <= to_date.date()
                    ),
                    and_(
                        col(Property.mortgage_renewal_date).isnot(None),
                        col(Property.mortgage_renewal_date) >= from_date.date(),
                        col(Property.mortgage_renewal_date) <= to_date.date()
                    )
                )
            )
        )
    )
    
    result = await session.execute(query)
    properties = result.scalars().all()
    
    events = []
    
    for property_obj in properties:
        # Insurance Expiry Event
        if property_obj.insurance_expiry_date:
            if from_date.date() <= property_obj.insurance_expiry_date <= to_date.date():
                expiry_datetime = datetime.combine(property_obj.insurance_expiry_date, datetime.min.time(), tzinfo=timezone.utc)
                is_past = expiry_datetime < datetime.now(timezone.utc)
                status = compute_event_status(expiry_datetime, is_past, CalendarEventType.INSURANCE_EXPIRY)
                
                if not filters.status or status == filters.status:
                    event = CalendarEvent(
                        id=f"insurance_{property_obj.id}",
                        type=CalendarEventType.INSURANCE_EXPIRY,
                        title=f"Insurance Expiry - {property_obj.name}",
                        description=f"Property insurance expires. Renew before {property_obj.insurance_expiry_date.strftime('%B %d, %Y')}",
                        start_at=expiry_datetime,
                        end_at=None,
                        all_day=True,
                        status=status,
                        priority=CalendarEventPriority.HIGH,
                        property_id=property_obj.id,
                        property_name=property_obj.name,
                        unit_id=None,
                        tenant_id=None,
                        tenant_name=None,
                        lease_id=None,
                        source_type="property",
                        source_id=str(property_obj.id) if property_obj.id else "unknown",
                        color=compute_event_color(status),
                        quick_actions=get_quick_actions(CalendarEventType.INSURANCE_EXPIRY),
                        metadata={
                            "property_type": property_obj.property_type,
                            "address": property_obj.address
                        }
                    )
                    events.append(event)
        
        # Mortgage Renewal Event
        if property_obj.mortgage_renewal_date:
            if from_date.date() <= property_obj.mortgage_renewal_date <= to_date.date():
                renewal_datetime = datetime.combine(property_obj.mortgage_renewal_date, datetime.min.time(), tzinfo=timezone.utc)
                is_past = renewal_datetime < datetime.now(timezone.utc)
                status = compute_event_status(renewal_datetime, is_past, CalendarEventType.MORTGAGE_RENEWAL)
                
                if not filters.status or status == filters.status:
                    event = CalendarEvent(
                        id=f"mortgage_{property_obj.id}",
                        type=CalendarEventType.MORTGAGE_RENEWAL,
                        title=f"Mortgage Renewal - {property_obj.name}",
                        description=f"Mortgage renewal date. Review terms and rates.",
                        start_at=renewal_datetime,
                        end_at=None,
                        all_day=True,
                        status=status,
                        priority=CalendarEventPriority.HIGH,
                        property_id=property_obj.id,
                        property_name=property_obj.name,
                        unit_id=None,
                        tenant_id=None,
                        tenant_name=None,
                        lease_id=None,
                        source_type="property",
                        source_id=str(property_obj.id) if property_obj.id else "unknown",
                        color=compute_event_color(status),
                        quick_actions=get_quick_actions(CalendarEventType.MORTGAGE_RENEWAL),
                        metadata={
                            "property_type": property_obj.property_type,
                            "address": property_obj.address
                        }
                    )
                    events.append(event)
    
    return events


async def build_custom_reminder_events(
    session: AsyncSession,
    user_id,
    from_date: datetime,
    to_date: datetime,
    filters: CalendarFilters
) -> List[CalendarEvent]:
    """Build calendar events from custom reminders"""
    
    query = (
        select(CustomReminder)
        .where(
            and_(
                col(CustomReminder.user_id) == user_id,
                col(CustomReminder.reminder_date) >= from_date,
                col(CustomReminder.reminder_date) <= to_date
            )
        )
    )
    
    # Apply property filter if specified
    if filters.property_id:
        query = query.where(col(CustomReminder.property_id) == filters.property_id)
    
    # Apply tenant filter if specified
    if filters.tenant_id:
        query = query.where(col(CustomReminder.tenant_id) == filters.tenant_id)
    
    result = await session.execute(query)
    reminders = result.scalars().all()
    
    events = []
    for reminder in reminders:
        status = compute_event_status(reminder.reminder_date, reminder.is_completed, CalendarEventType.CUSTOM_REMINDER)
        
        # Skip if status filter doesn't match
        if filters.status and status != filters.status:
            continue
        
        event = CalendarEvent(
            id=f"reminder_{reminder.id}",
            type=CalendarEventType.CUSTOM_REMINDER,
            title=reminder.title,
            description=reminder.description,
            start_at=reminder.reminder_date,
            end_at=None,
            all_day=reminder.all_day,
            status=status,
            priority=CalendarEventPriority.MEDIUM,
            property_id=reminder.property_id,
            property_name=None,  # Could load if needed
            unit_id=reminder.unit_id,
            tenant_id=reminder.tenant_id,
            tenant_name=None,  # Could load if needed
            lease_id=None,
            source_type="custom",
            source_id=str(reminder.id),
            color=compute_event_color(status),
            quick_actions=get_quick_actions(CalendarEventType.CUSTOM_REMINDER, reminder.is_completed),
            metadata={
                "notify_before_hours": reminder.notify_before_hours,
                "completed_at": reminder.completed_at.isoformat() if reminder.completed_at else None
            }
        )
        events.append(event)
    
    return events

