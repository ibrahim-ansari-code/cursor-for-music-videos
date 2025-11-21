"""Stripe Event Log SQLModel"""
from datetime import datetime
from typing import Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, TIMESTAMP
from sqlmodel import Field, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime


class StripeEventLog(SQLModel, table=True):
    """
    Stripe webhook event log for idempotent processing.
    
    Stores all incoming Stripe webhook events to:
    1. Prevent duplicate processing (check stripe_event_id before processing)
    2. Provide audit trail for debugging
    3. Support manual replay if needed
    4. Track processing errors for alerting
    """
    __tablename__ = "stripe_event_logs"
    __table_args__ = {"schema": "billing"}
    
    id: PythonUUID = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    
    # Stripe event identification
    stripe_event_id: str = Field(
        unique=True,
        max_length=255,
        description="Stripe event ID (evt_xxx) - used for deduplication"
    )
    event_type: str = Field(
        max_length=100,
        description="Event type: customer.subscription.created, invoice.payment_succeeded, etc."
    )
    api_version: Optional[str] = Field(
        default=None,
        max_length=50,
        sa_column=Column(String(50), nullable=True)
    )
    
    # Event payload (full Stripe event object)
    event_data: dict = Field(
        sa_column=Column(JSONB, nullable=False),
        description="Full Stripe event object for replay/debugging"
    )
    
    # Processing state
    processed: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false")
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    processing_error: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True)
    )
    
    # Request tracking for Stripe support
    stripe_request_id: Optional[str] = Field(
        default=None,
        max_length=255,
        sa_column=Column(String(255), nullable=True),
        description="Stripe-Request-Id header for support correlation"
    )
    
    # Audit
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column("created_at", nullable=False, server_default="NOW()")
    )
    
    class Config:
        arbitrary_types_allowed = True

