"""
Notification System Models

Defines SQLModel models for the notification system:
- Notification: Individual notifications for users
- NotificationPreference: User preferences for notification delivery
- NotificationDeliveryLog: Tracks delivery status for analytics

"""
from datetime import datetime, time
from typing import TYPE_CHECKING, List
from uuid import UUID as PythonUUID

import sqlalchemy as sa
from sqlalchemy import Column, Text, ARRAY, Time, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlmodel import Field, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.user import User


class Notification(SQLModel, table=True):
    """
    Individual notification for a user.
    
    Supports multi-channel delivery (in-app, email, SMS) with flexible metadata
    and grouping capabilities for notification bundling.
    """
    __tablename__ = "notifications"  # type: ignore
    
    # Primary Key
    id: PythonUUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True)
    )
    
    # User Reference
    user_id: PythonUUID = Field(
        foreign_key="users.id"
    )
    
    # Notification Content
    type: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Type: rent_reminder, payment_received, lease_expiring, maintenance_update, new_application, system_update"
    )
    title: str = Field(sa_column=Column(Text, nullable=False))
    message: str = Field(sa_column=Column(Text, nullable=False))
    link: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Deep link to relevant page (e.g., '/tenants/123')"
    )
    
    # Actor Information (who triggered this notification)
    actor_id: PythonUUID | None = Field(
        default=None,
        foreign_key="users.id"
    )
    actor_name: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    actor_avatar_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    
    # Context & Metadata
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column('metadata', JSONB, nullable=False, server_default='{}'),
        description="Flexible metadata: {property_id, tenant_id, amount, etc.}"
    )
    
    # Status
    is_read: bool = Field(default=False, nullable=False)
    is_archived: bool = Field(default=False, nullable=False)
    read_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True)
    )
    
    # Priority & Delivery
    priority: str = Field(
        default="normal",
        sa_column=Column(Text, nullable=False),
        description="Priority: urgent, high, normal, low"
    )
    delivery_channels: List[str] = Field(
        default_factory=lambda: ["in_app"],
        sa_column=Column(ARRAY(Text), nullable=False),
        description="Channels: ['in_app', 'email', 'sms']"
    )
    
    # Grouping for notification bundling
    group_key: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Used to group related notifications (e.g., 'rent_reminders_2024_10')"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(sa.DateTime(timezone=True), nullable=False)
    )
    expires_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True),
        description="Auto-delete after this timestamp"
    )


class NotificationPreference(SQLModel, table=True):
    """
    User notification preferences with granular per-type, per-channel control.
    
    Stores preferences as JSONB for flexibility:
    {
        "rent_reminder": {"enabled": true, "channels": ["in_app", "email"], "frequency": "immediate"},
        ...
    }
    """
    __tablename__ = "notification_preferences"  # type: ignore
    
    # Primary Key
    id: PythonUUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True)
    )
    
    # User Reference (unique - one preference record per user)
    user_id: PythonUUID = Field(
        unique=True,
        foreign_key="users.id"
    )
    
    # Global Toggle
    enabled: bool = Field(default=True, nullable=False)
    
    # Per-Type Preferences (JSONB for flexibility)
    preferences: dict = Field(
        default_factory=lambda: {
            "rent_reminder": {"enabled": True, "channels": ["in_app", "email"], "frequency": "immediate"},
            "payment_received": {"enabled": True, "channels": ["in_app", "email"], "frequency": "immediate"},
            "lease_expiring": {"enabled": True, "channels": ["in_app", "email"], "frequency": "immediate"},
            "maintenance_update": {"enabled": True, "channels": ["in_app", "email"], "frequency": "immediate"},
            "new_application": {"enabled": False, "channels": ["in_app"], "frequency": "immediate"},
            "system_update": {"enabled": False, "channels": ["in_app"], "frequency": "immediate"}
        },
        sa_column=Column(JSONB, nullable=False),
        description="Per-type settings: {type: {enabled, channels, frequency}}"
    )
    
    # Digest Settings
    email_digest_frequency: str = Field(
        default="immediate",
        sa_column=Column(Text, nullable=False),
        description="Frequency: immediate, hourly, daily, weekly, never"
    )
    email_digest_time: time = Field(
        default=time(8, 0, 0),
        sa_column=Column(Time, nullable=False),
        description="Time to send daily/weekly digests"
    )
    timezone: str = Field(
        default="America/Toronto",
        sa_column=Column(Text, nullable=False)
    )
    
    # Do Not Disturb (future feature)
    quiet_hours_enabled: bool = Field(default=False, nullable=False)
    quiet_hours_start: time | None = Field(default=None, sa_column=Column(Time, nullable=True))
    quiet_hours_end: time | None = Field(default=None, sa_column=Column(Time, nullable=True))
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(sa.DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(sa.DateTime(timezone=True), nullable=False)
    )


class NotificationDeliveryLog(SQLModel, table=True):
    """
    Tracks notification delivery status for analytics and debugging.
    
    Stores delivery attempts, status, and email-specific tracking data
    (opens, clicks, bounces).
    """
    __tablename__ = "notification_delivery_log"  # type: ignore
    
    # Primary Key
    id: PythonUUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True)
    )
    
    # References
    notification_id: PythonUUID = Field(
        foreign_key="notifications.id"
    )
    user_id: PythonUUID = Field(
        foreign_key="users.id"
    )
    
    # Delivery Details
    channel: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Channel: in_app, email, sms"
    )
    status: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Status: pending, sent, delivered, failed, bounced"
    )
    
    # Email-specific fields
    email_provider: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Email provider: supabase, sendgrid, postmark, etc."
    )
    email_message_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    email_opened_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True)
    )
    email_clicked_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True)
    )
    
    # Error Handling
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    retry_count: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(sa.DateTime(timezone=True), nullable=False)
    )
    sent_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True)
    )
    delivered_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True)
    )

