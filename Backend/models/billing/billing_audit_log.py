"""Billing Audit Log SQLModel"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, String, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlmodel import Field, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime


class BillingAuditLog(SQLModel, table=True):
    """
    Business-level audit trail for billing operations.
    
    Separate from stripe_event_logs to provide business-level visibility into:
    - Subscription lifecycle events
    - Payment success/failures
    - User actions (upgrades, cancellations)
    - System-initiated actions (trial expirations, dunning)
    """
    __tablename__ = "billing_audit_logs"
    __table_args__ = {"schema": "billing"}
    
    id: PythonUUID = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    
    # Foreign keys (nullable to handle deleted records)
    user_id: Optional[PythonUUID] = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    )
    subscription_id: Optional[PythonUUID] = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("billing.user_subscriptions.id", ondelete="SET NULL"),
            nullable=True
        )
    )
    
    # Action tracking
    action: str = Field(
        max_length=100,
        description="Action: subscription_created, payment_succeeded, subscription_canceled, trial_started, etc."
    )
    actor: Optional[str] = Field(
        default=None,
        max_length=50,
        sa_column=Column(String(50), nullable=True),
        description="Who initiated: system, user, admin, stripe_webhook"
    )
    
    # Context
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True)
    )
    audit_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True, server_default="'{}'::jsonb"),
        description="Additional context data for the audit log entry"
    )
    
    # Financial tracking (for reconciliation)
    amount: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(10, 2), nullable=True),
        description="Amount in CAD"
    )
    currency: Optional[str] = Field(
        default=None,
        max_length=3,
        sa_column=Column(String(3), nullable=True)
    )
    
    # Link to Stripe event if applicable
    stripe_event_id: Optional[str] = Field(
        default=None,
        max_length=255,
        sa_column=Column(String(255), nullable=True),
        description="Link to stripe_event_logs.stripe_event_id"
    )
    
    # Audit timestamp
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column("created_at", nullable=False, server_default="NOW()")
    )
    
    class Config:
        arbitrary_types_allowed = True

