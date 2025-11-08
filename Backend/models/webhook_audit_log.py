"""
Webhook audit log model for tracking webhook events.

This model stores all webhook requests for audit, monitoring, and debugging purposes.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime


class WebhookAuditLog(SQLModel, table=True):
    """
    Audit log for all webhook requests.
    
    Tracks webhook events for monitoring, debugging, and security auditing.
    Stores both successful and failed webhook attempts.
    """
    
    __tablename__ = "webhook_audit_logs"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Webhook identification
    webhook_type: str = Field(index=True)  # e.g., "user_sync"
    event_type: str = Field(index=True)  # e.g., "INSERT", "UPDATE"
    
    # Request details
    source_ip: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    
    # Payload information
    table_name: str  # e.g., "auth.users"
    record_id: Optional[str] = Field(default=None, index=True)  # User ID or record ID
    record_email: Optional[str] = Field(default=None, index=True)  # Email for user webhooks
    
    # Processing results
    success: bool = Field(default=True, index=True)
    action_taken: Optional[str] = Field(default=None)  # e.g., "created", "updated", "linked", "idempotent"
    error_message: Optional[str] = Field(default=None)
    error_type: Optional[str] = Field(default=None)
    
    # Performance tracking
    processing_time_ms: Optional[float] = Field(default=None)  # Processing duration in milliseconds
    
    # Audit trail
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), index=True, nullable=False)
    )
    
    # Optional: Store full payload for debugging (be careful with PII)
    # payload_snapshot: Optional[str] = Field(default=None)  # JSON string of payload
    
    def __repr__(self) -> str:
        return (
            f"WebhookAuditLog(id={self.id}, type={self.webhook_type}, "
            f"event={self.event_type}, success={self.success}, "
            f"created_at={self.created_at})"
        )

