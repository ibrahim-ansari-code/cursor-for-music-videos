"""Subscription Plan SQLModel"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, Numeric, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlmodel import Field, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime


class SubscriptionPlan(SQLModel, table=True):
    """
    Subscription plans available to users.
    
    Stores product/price mappings from Stripe to enable flexible pricing
    without code changes. Used to drive billing UI and subscription creation.
    """
    __tablename__ = "subscription_plans"
    __table_args__ = {"schema": "billing"}
    
    id: PythonUUID = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    
    # Plan details
    name: str = Field(max_length=100)  # "Brikli Premium"
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    
    # Stripe references
    stripe_product_id: str = Field(
        unique=True,
        max_length=255,
        description="Stripe Product ID (prod_xxx)"
    )
    stripe_price_id: str = Field(
        unique=True,
        max_length=255,
        description="Stripe Price ID (price_xxx)"
    )
    
    # Pricing
    amount: Decimal = Field(
        sa_column=Column(Numeric(10, 2), nullable=False),
        description="Price in CAD (e.g., 99.99)"
    )
    currency: str = Field(default="CAD", max_length=3)
    interval: str = Field(
        max_length=20,
        description="Billing interval: day, week, month, year"
    )
    interval_count: int = Field(
        default=1,
        sa_column=Column(Integer, nullable=False, server_default="1")
    )
    
    # Trial configuration
    trial_period_days: Optional[int] = Field(
        default=14,
        sa_column=Column(Integer, nullable=True, server_default="14"),
        description="14-day free trial"
    )
    
    # Status
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default="true")
    )
    
    # Features (for UI display)
    features: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True, server_default="'[]'::jsonb"),
        description="JSON array of feature strings for display"
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

