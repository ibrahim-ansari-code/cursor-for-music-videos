"""
Calendar API Schemas

Pydantic schemas for calendar API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from Backend.models.calendar import CalendarEventType, CalendarEventStatus, CalendarEventPriority


# ============================================================================
# FILTERS
# ============================================================================

class CalendarFilters(BaseModel):
    """Filters for calendar event queries"""
    from_date: datetime
    to_date: datetime
    property_id: Optional[int] = None
    unit_id: Optional[int] = None
    tenant_id: Optional[int] = None
    event_type: Optional[CalendarEventType] = None
    status: Optional[CalendarEventStatus] = None


# ============================================================================
# CUSTOM REMINDERS
# ============================================================================

class CustomReminderBase(BaseModel):
    """Base fields for custom reminders"""
    title: str = Field(..., max_length=255, description="Reminder title")
    description: Optional[str] = Field(None, description="Optional description")
    reminder_date: datetime = Field(..., description="When the reminder is due")
    all_day: bool = Field(default=False, description="All-day event flag")
    notify_before_hours: int = Field(default=24, ge=0, le=168, description="Notify X hours before (0-168)")
    
    # Optional associations
    property_id: Optional[int] = Field(None, description="Associated property ID")
    unit_id: Optional[int] = Field(None, description="Associated unit ID")
    tenant_id: Optional[int] = Field(None, description="Associated tenant ID")


class CustomReminderCreate(CustomReminderBase):
    """Schema for creating a custom reminder"""
    pass


class CustomReminderUpdate(BaseModel):
    """Schema for updating a custom reminder"""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    reminder_date: Optional[datetime] = None
    all_day: Optional[bool] = None
    notify_before_hours: Optional[int] = Field(None, ge=0, le=168)
    is_completed: Optional[bool] = None
    property_id: Optional[int] = None
    unit_id: Optional[int] = None
    tenant_id: Optional[int] = None


class CustomReminderResponse(CustomReminderBase):
    """Schema for custom reminder responses"""
    id: UUID
    user_id: UUID
    is_completed: bool
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# CALENDAR EVENTS
# ============================================================================

class RelatedEntity(BaseModel):
    """Related entity chip for UI display"""
    type: str  # "property", "tenant", "unit", "lease"
    id: int
    name: str


class CalendarEventResponse(BaseModel):
    """Unified calendar event response"""
    # Identity
    id: str
    type: CalendarEventType
    
    # Content
    title: str
    description: Optional[str]
    
    # Temporal
    start_at: datetime
    end_at: Optional[datetime]
    all_day: bool
    
    # Status
    status: CalendarEventStatus
    priority: CalendarEventPriority
    color: str
    
    # Associations
    property_id: Optional[int]
    property_name: Optional[str]
    unit_id: Optional[int]
    tenant_id: Optional[int]
    tenant_name: Optional[str]
    lease_id: Optional[int]
    
    # Source
    source_type: str
    source_id: int | str
    
    # UI helpers
    quick_actions: List[str]
    related_entities: List[RelatedEntity] = Field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=lambda: {})
    
    class Config:
        from_attributes = True


class CalendarEventsListResponse(BaseModel):
    """Paginated list of calendar events"""
    events: List[CalendarEventResponse]
    total: int
    from_date: datetime
    to_date: datetime


# ============================================================================
# QUICK ACTIONS
# ============================================================================

class QuickActionRequest(BaseModel):
    """Request to execute a quick action on an event"""
    action: str  # "send_invoice", "record_payment", "mark_complete", etc.
    metadata: Dict[str, Any] = Field(default_factory=lambda: {})


class QuickActionResponse(BaseModel):
    """Response after executing a quick action"""
    success: bool
    message: str
    updated_event: Optional[CalendarEventResponse] = None

