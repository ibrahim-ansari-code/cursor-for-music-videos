"""User Subscription SQLModel"""
from datetime import datetime
from typing import Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, TIMESTAMP
from sqlmodel import Field, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime


class UserSubscription(SQLModel, table=True):
    """
    User subscription records synced from Stripe.
    
    This is the source of truth for user subscription status, updated by Stripe webhooks.
    Denormalized fields on users table are cached from this table for quick access checks.
    """
    __tablename__ = "user_subscriptions"
    __table_args__ = {"schema": "billing"}
    
    id: PythonUUID = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    
    # Foreign keys
    user_id: PythonUUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    )
    plan_id: PythonUUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("billing.subscription_plans.id"), nullable=False)
    )
    
    # Stripe references
    stripe_customer_id: str = Field(
        max_length=255,
        description="Stripe Customer ID (cus_xxx)"
    )
    stripe_subscription_id: str = Field(
        unique=True,
        max_length=255,
        description="Stripe Subscription ID (sub_xxx)"
    )
    
    # Subscription status (source of truth from Stripe)
    status: str = Field(
        max_length=50,
        description="Stripe subscription status: active, canceled, past_due, trialing, incomplete, incomplete_expired, unpaid"
    )
    
    # Billing periods
    current_period_start: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    current_period_end: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    
    # Trial tracking
    trial_start: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    trial_end: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
        description="14-day trial end date"
    )
    
    # Cancellation tracking
    cancel_at_period_end: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
        description="If true, user retains access until current_period_end"
    )
    canceled_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    ended_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    
    # Metadata for extensibility (using alias to avoid SQLModel.metadata conflict)
    subscription_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True, server_default="'{}'::jsonb"),
        description="Custom metadata from Stripe subscription"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column("created_at", nullable=False, server_default="NOW()")
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column("updated_at", nullable=False, server_default="NOW()")
    )
    
    class Config:
        arbitrary_types_allowed = True

