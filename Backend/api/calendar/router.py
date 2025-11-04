"""
Calendar API Router

RESTful API endpoints for calendar functionality:
- GET /api/calendar/events - Get unified calendar events
- POST /api/calendar/reminders - Create custom reminder
- GET /api/calendar/reminders/{id} - Get specific reminder
- PATCH /api/calendar/reminders/{id} - Update reminder
- DELETE /api/calendar/reminders/{id} - Delete reminder
"""
import logging
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta, timezone
from uuid import UUID

from Backend.database import get_session
from Backend.api.auth.dependencies import get_current_user
from Backend.models.user import User
from Backend.models.calendar import CalendarEventType, CalendarEventStatus
from .schemas import (
    CalendarFilters,
    CalendarEventsListResponse,
    CalendarEventResponse,
    CustomReminderCreate,
    CustomReminderUpdate,
    CustomReminderResponse
)
from .service import CalendarService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar"])


# ============================================================================
# CALENDAR EVENTS
# ============================================================================

@router.get("/events", response_model=CalendarEventsListResponse)
async def get_calendar_events(
    from_date: Optional[datetime] = Query(
        None,
        description="Start date for calendar range (defaults to today)"
    ),
    to_date: Optional[datetime] = Query(
        None,
        description="End date for calendar range (defaults to +30 days)"
    ),
    property_id: Optional[int] = Query(
        None,
        description="Filter by specific property ID"
    ),
    unit_id: Optional[int] = Query(
        None,
        description="Filter by specific unit ID"
    ),
    tenant_id: Optional[int] = Query(
        None,
        description="Filter by specific tenant ID"
    ),
    event_type: Optional[CalendarEventType] = Query(
        None,
        description="Filter by event type"
    ),
    status: Optional[CalendarEventStatus] = Query(
        None,
        description="Filter by event status"
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get unified calendar events from all sources.
    
    Retrieves events from:
    - Invoices (due dates)
    - Leases (start/end dates)
    - Maintenance (scheduled dates)
    - Properties (insurance/mortgage expiries)
    - Custom Reminders (user-created)
    
    Events are computed on-demand from source tables and unified into
    a single sorted list.
    """
    logger.info(f"Calendar events requested by user {current_user.id}")
    
    # Default date range: today to +30 days
    if not from_date:
        from_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if not to_date:
        to_date = from_date + timedelta(days=30)
    
    # Validate date range
    if to_date < from_date:
        raise HTTPException(
            status_code=400,
            detail="to_date must be after from_date"
        )
    
    # Limit range to prevent excessive queries
    max_range_days = 365
    if (to_date - from_date).days > max_range_days:
        raise HTTPException(
            status_code=400,
            detail=f"Date range cannot exceed {max_range_days} days"
        )
    
    filters = CalendarFilters(
        from_date=from_date,
        to_date=to_date,
        property_id=property_id,
        unit_id=unit_id,
        tenant_id=tenant_id,
        event_type=event_type,
        status=status
    )
    
    service = CalendarService(session)
    
    try:
        result = await service.get_events(current_user.id, filters)
        logger.info(f"Returned {result.total} calendar events")
        return result
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch calendar events"
        )


# ============================================================================
# CUSTOM REMINDERS
# ============================================================================

@router.post("/reminders", response_model=CustomReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_reminder(
    reminder: CustomReminderCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a custom calendar reminder.
    
    Custom reminders are user-created events that can be associated with
    properties, units, or tenants.
    """
    logger.info(f"Creating custom reminder for user {current_user.id}")
    
    service = CalendarService(session)
    
    try:
        result = await service.create_custom_reminder(current_user.id, reminder)
        logger.info(f"Created custom reminder {result.id}")
        return result
    except Exception as e:
        logger.error(f"Error creating custom reminder: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create custom reminder"
        )


@router.get("/reminders/{reminder_id}", response_model=CustomReminderResponse)
async def get_custom_reminder(
    reminder_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific custom reminder by ID"""
    logger.info(f"Fetching custom reminder {reminder_id} for user {current_user.id}")
    
    service = CalendarService(session)
    reminder = await service.get_custom_reminder(reminder_id, current_user.id)
    
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom reminder not found"
        )
    
    return reminder


@router.patch("/reminders/{reminder_id}", response_model=CustomReminderResponse)
async def update_custom_reminder(
    reminder_id: UUID,
    update: CustomReminderUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update a custom reminder.
    
    Can be used to:
    - Edit reminder details
    - Mark as completed
    - Reschedule (snooze)
    """
    logger.info(f"Updating custom reminder {reminder_id} for user {current_user.id}")
    
    service = CalendarService(session)
    
    try:
        result = await service.update_custom_reminder(reminder_id, current_user.id, update)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom reminder not found"
            )
        
        logger.info(f"Updated custom reminder {reminder_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating custom reminder: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update custom reminder"
        )


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_reminder(
    reminder_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a custom reminder"""
    logger.info(f"Deleting custom reminder {reminder_id} for user {current_user.id}")
    
    service = CalendarService(session)
    
    try:
        deleted = await service.delete_custom_reminder(reminder_id, current_user.id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom reminder not found"
            )
        
        logger.info(f"Deleted custom reminder {reminder_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting custom reminder: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete custom reminder"
        )


# ============================================================================
# QUICK ACTIONS (Future Enhancement)
# ============================================================================

# @router.post("/events/{event_id}/actions/{action}")
# async def execute_quick_action(
#     event_id: str,
#     action: str,
#     session: AsyncSession = Depends(get_session),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Execute a quick action on a calendar event.
#     
#     Examples:
#     - send_invoice
#     - record_payment
#     - mark_complete
#     - start_renewal
#     
#     This would dispatch to the appropriate service based on event source type.
#     """
#     # TODO: Implement quick actions dispatcher
#     pass

