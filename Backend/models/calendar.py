"""
Calendar Models

Defines models for the Calendar feature:
- CustomReminder: User-created calendar reminders
- CalendarEvent: Dataclass for unified calendar event representation
- Enums for event types, status, priority
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from enum import Enum
from uuid import UUID as PythonUUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import SQLModel, Field, Relationship


# ============================================================================
# ENUMS
# ============================================================================

class CalendarEventType(str, Enum):
    """Types of calendar events from various sources"""
    RENT_DUE = "rent_due"
    INVOICE_DUE = "invoice_due"
    LEASE_START = "lease_start"
    LEASE_EXPIRING = "lease_expiring"
    MAINTENANCE_SCHEDULED = "maintenance_scheduled"
    INSURANCE_EXPIRY = "insurance_expiry"
    MORTGAGE_RENEWAL = "mortgage_renewal"
    CUSTOM_REMINDER = "custom_reminder"


class CalendarEventStatus(str, Enum):
    """Computed status based on dates and completion"""
    UPCOMING = "upcoming"  # Future event
    DUE = "due"  # Due today
    OVERDUE = "overdue"  # Past due and not completed
    COMPLETED = "completed"  # Resolved/completed


class CalendarEventPriority(str, Enum):
    """Event priority level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================================
# DATABASE MODEL
# ============================================================================

class CustomReminder(SQLModel, table=True):
    """
    User-created calendar reminders.
    
    This is the only calendar-specific table - all other events are
    computed from existing source tables (invoices, leases, etc.)
    """
    __tablename__ = "custom_reminders"
    
    # Primary key
    id: PythonUUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()")
        )
    )
    
    # Owner
    user_id: PythonUUID = Field(foreign_key="users.id")
    
    # Content
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None)
    
    # Temporal
    reminder_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    all_day: bool = Field(default=False)
    
    # Optional associations
    property_id: Optional[int] = Field(default=None, foreign_key="properties.id")
    unit_id: Optional[int] = Field(
        default=None,
        foreign_key="property_units.id"
    )
    tenant_id: Optional[int] = Field(
        default=None,
        foreign_key="tenants.id"
    )
    
    # Status
    is_completed: bool = Field(default=False, index=True)
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    
    # Notifications
    notify_before_hours: int = Field(default=24)
    notified_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Timestamp when notification was sent (prevents duplicates)"
    )
    notification_id: Optional[PythonUUID] = Field(
        default=None,
        foreign_key="notifications.id",
        description="Reference to created notification record"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    
    # Relationships
    if TYPE_CHECKING:
        from Backend.models.user import User
        from Backend.models.property import Property
        from Backend.models.units import PropertyUnit
        from Backend.models.tenant import Tenant
        from Backend.models.notification import Notification
    
    user: Optional["User"] = Relationship(back_populates="custom_reminders")
    property: Optional["Property"] = Relationship()
    unit: Optional["PropertyUnit"] = Relationship()
    tenant: Optional["Tenant"] = Relationship()
    notification: Optional["Notification"] = Relationship()


# ============================================================================
# DATACLASS (NOT A DATABASE TABLE)
# ============================================================================

@dataclass
class CalendarEvent:
    """
    Unified calendar event representation.
    
    This is NOT a database table - it's a runtime dataclass built from
    various source tables (invoices, leases, maintenance, custom_reminders).
    
    Each event has a composite ID like "invoice_123" or "lease_start_456"
    to identify the source.
    """
    # Identity
    id: str  # Format: "{source_type}_{source_id}" e.g., "invoice_123"
    type: CalendarEventType
    
    # Content
    title: str
    description: Optional[str]
    
    # Temporal
    start_at: datetime
    end_at: Optional[datetime]
    all_day: bool
    
    # Status (computed at runtime)
    status: CalendarEventStatus
    priority: CalendarEventPriority
    
    # Associations (nullable)
    property_id: Optional[int]
    property_name: Optional[str]  # Denormalized for display
    unit_id: Optional[int]
    tenant_id: Optional[int]
    tenant_name: Optional[str]  # Denormalized for display
    lease_id: Optional[int]
    
    # Source tracking
    source_type: str  # "invoice", "lease", "maintenance", "property", "custom"
    source_id: int | str  # ID in the source table
    
    # UI helpers (computed)
    color: str  # "green", "amber", "red" based on status
    quick_actions: List[str]  # e.g., ["send_invoice", "record_payment"]
    
    # Metadata (flexible JSON for type-specific data)
    metadata: Dict[str, Any] = field(default_factory=dict)

