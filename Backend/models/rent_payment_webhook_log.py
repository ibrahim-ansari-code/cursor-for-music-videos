"""Rent Payment Webhook Event Log SQLModel"""
from datetime import datetime
from typing import Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, TIMESTAMP
from sqlmodel import Field, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime


class RentPaymentWebhookLog(SQLModel, table=True):
    """
    Stripe webhook event log for rent payment webhooks (idempotent processing).
    
    Stores all incoming Stripe webhook events to:
    1. Prevent duplicate processing (check stripe_event_id before processing)
    2. Provide audit trail for debugging and compliance
    3. Support manual replay if needed
    4. Track processing errors for alerting
    5. Enable analytics on webhook processing performance
    
    This is critical for financial operations as Stripe may retry webhooks,
    and we must ensure each event is processed exactly once.
    """
    __tablename__ = "rent_payment_webhook_logs"
    
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
        description="Event type: payment_intent.succeeded, charge.refunded, etc."
    )
    api_version: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50), nullable=True),
        description="Stripe API version used for this event"
    )
    
    # Event payload (full Stripe event object for replay/debugging)
    event_data: dict = Field(
        sa_column=Column(JSONB, nullable=False),
        description="Full Stripe event object for replay/debugging"
    )
    
    # Processing state
    processed: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
        description="Whether event was successfully processed"
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
        description="When event was successfully processed"
    )
    processing_error: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Error message if processing failed"
    )
    
    # Request tracking for Stripe support correlation
    stripe_request_id: Optional[str] = Field(
        default=None,
        sa_column=Column(String(255), nullable=True),
        description="Stripe-Request-Id header for support correlation"
    )
    
    # Connected account tracking (for Connect events)
    stripe_account_id: Optional[str] = Field(
        default=None,
        sa_column=Column(String(255), nullable=True),
        description="Stripe Connect account ID if event is from connected account"
    )
    
    # Audit
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column("created_at", nullable=False, server_default="NOW()")
    )
    
    class Config:
        arbitrary_types_allowed = True

