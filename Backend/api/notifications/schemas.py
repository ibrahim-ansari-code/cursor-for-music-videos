"""
Notification API Schemas

Pydantic models for request/response validation in the notification API.
"""
from datetime import datetime, time
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ========================================================================
# NOTIFICATION SCHEMAS
# ========================================================================

class NotificationMetadata(BaseModel):
    """Flexible metadata for notifications"""
    property_id: Optional[int] = None
    tenant_id: Optional[int] = None
    unit_id: Optional[int] = None
    amount: Optional[float] = None
    lease_id: Optional[int] = None
    maintenance_id: Optional[int] = None
    payment_id: Optional[int] = None
    invoice_id: Optional[int] = None
    
    class Config:
        extra = "allow"  # Allow additional fields


class NotificationResponse(BaseModel):
    """Response model for a single notification"""
    id: UUID
    user_id: UUID
    type: str
    title: str
    message: str
    link: Optional[str] = None
    
    # Actor information
    actor_id: Optional[UUID] = None
    actor_name: Optional[str] = None
    actor_avatar_url: Optional[str] = None
    
    # Status
    is_read: bool
    is_archived: bool
    read_at: Optional[datetime] = None
    
    # Priority & delivery
    priority: str
    delivery_channels: List[str]
    
    # Metadata & grouping
    metadata_: Dict[str, Any]
    group_key: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Paginated list of notifications"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    limit: int
    offset: int


class UnreadCountResponse(BaseModel):
    """Response with unread notification count"""
    unread_count: int


class MarkAsReadRequest(BaseModel):
    """Request to mark notification(s) as read"""
    notification_ids: Optional[List[UUID]] = Field(
        default=None,
        description="List of notification IDs to mark as read. If None, marks all as read."
    )


class MarkAsReadResponse(BaseModel):
    """Response after marking notifications as read"""
    success: bool
    marked_count: int
    message: str


class NotificationCreateRequest(BaseModel):
    """Request to create a notification (internal use, admin only)"""
    user_id: UUID
    type: str
    title: str
    message: str
    link: Optional[str] = None
    priority: str = "normal"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    group_key: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = [
            'rent_reminder', 'payment_received', 'lease_expiring',
            'maintenance_update', 'maintenance_request_new', 'new_application', 'system_update'
        ]
        if v not in valid_types:
            raise ValueError(f"Invalid notification type. Must be one of: {', '.join(valid_types)}")
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str) -> str:
        valid_priorities = ['urgent', 'high', 'normal', 'low']
        if v not in valid_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
        return v


# ========================================================================
# NOTIFICATION PREFERENCE SCHEMAS
# ========================================================================

class NotificationTypePreference(BaseModel):
    """Preference for a single notification type"""
    enabled: bool = True
    channels: List[str] = Field(default_factory=lambda: ["in_app", "email"])
    frequency: str = "immediate"
    
    @field_validator('channels')
    @classmethod
    def validate_channels(cls, v: List[str]) -> List[str]:
        valid_channels = ['in_app', 'email', 'sms']
        for channel in v:
            if channel not in valid_channels:
                raise ValueError(f"Invalid channel '{channel}'. Must be one of: {', '.join(valid_channels)}")
        return v
    
    @field_validator('frequency')
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        valid_frequencies = ['immediate', 'hourly', 'daily', 'weekly', 'never']
        if v not in valid_frequencies:
            raise ValueError(f"Invalid frequency. Must be one of: {', '.join(valid_frequencies)}")
        return v


class NotificationPreferencesDict(BaseModel):
    """Complete preferences for all notification types"""
    rent_reminder: NotificationTypePreference = Field(
        default_factory=lambda: NotificationTypePreference(enabled=True, channels=["in_app", "email"])
    )
    payment_received: NotificationTypePreference = Field(
        default_factory=lambda: NotificationTypePreference(enabled=True, channels=["in_app", "email"])
    )
    lease_expiring: NotificationTypePreference = Field(
        default_factory=lambda: NotificationTypePreference(enabled=True, channels=["in_app", "email"])
    )
    maintenance_update: NotificationTypePreference = Field(
        default_factory=lambda: NotificationTypePreference(enabled=True, channels=["in_app", "email"])
    )
    new_application: NotificationTypePreference = Field(
        default_factory=lambda: NotificationTypePreference(enabled=False, channels=["in_app"])
    )
    system_update: NotificationTypePreference = Field(
        default_factory=lambda: NotificationTypePreference(enabled=False, channels=["in_app"])
    )


class NotificationPreferenceResponse(BaseModel):
    """Response model for notification preferences"""
    id: UUID
    user_id: UUID
    enabled: bool
    preferences: Dict[str, Any]  # Will contain NotificationTypePreference data
    email_digest_frequency: str
    email_digest_time: time
    timezone: str
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationPreferenceUpdateRequest(BaseModel):
    """Request to update notification preferences"""
    enabled: Optional[bool] = None
    preferences: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Per-type preferences: {type: {enabled, channels, frequency}}"
    )
    email_digest_frequency: Optional[str] = None
    email_digest_time: Optional[time] = None
    timezone: Optional[str] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None
    
    @field_validator('email_digest_frequency')
    @classmethod
    def validate_digest_frequency(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_frequencies = ['immediate', 'hourly', 'daily', 'weekly', 'never']
        if v not in valid_frequencies:
            raise ValueError(f"Invalid digest frequency. Must be one of: {', '.join(valid_frequencies)}")
        return v


class NotificationPreferenceUpdateResponse(BaseModel):
    """Response after updating preferences"""
    success: bool
    message: str
    preferences: NotificationPreferenceResponse


# ========================================================================
# TEST EMAIL SCHEMA
# ========================================================================

class TestNotificationRequest(BaseModel):
    """Request to send a test in-app notification"""
    notification_type: str = "system_update"
    
    @field_validator('notification_type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = [
            'rent_reminder', 'payment_received', 'lease_expiring',
            'maintenance_update', 'maintenance_request_new', 'new_application', 'system_update'
        ]
        if v not in valid_types:
            raise ValueError(f"Invalid notification type. Must be one of: {', '.join(valid_types)}")
        return v


class TestNotificationResponse(BaseModel):
    """Response after sending test notification"""
    success: bool
    message: str
    notification_id: str


class TestEmailRequest(BaseModel):
    """Request to send a test email notification"""
    notification_type: str = "system_update"
    
    @field_validator('notification_type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = [
            'rent_reminder', 'payment_received', 'lease_expiring',
            'maintenance_update', 'maintenance_request_new', 'new_application', 'system_update'
        ]
        if v not in valid_types:
            raise ValueError(f"Invalid notification type. Must be one of: {', '.join(valid_types)}")
        return v


class TestEmailResponse(BaseModel):
    """Response after sending test email"""
    success: bool
    message: str
    email_sent_to: str

