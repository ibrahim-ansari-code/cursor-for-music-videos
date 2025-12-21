"""
Tenant Portal Seat Subscription Model

Tracks recurring Stripe subscriptions for tenant portal seats ($3/seat/month).
Each subscription adds seats to the landlord's tenant_portal_seat_limit.

GitHub-Style Architecture:
- This table tracks subscription metadata only
- Actual seat usage is calculated in real-time: COUNT(tenants WHERE user_id IS NOT NULL)
- No separate "seats_used" counter that can drift out of sync
"""
from datetime import datetime, timezone
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import Field, SQLModel
from uuid import UUID, uuid4


class TenantPortalSeatSubscription(SQLModel, table=True):
    """Tracks recurring Stripe subscriptions for tenant portal seats"""
    __tablename__ = "tenant_portal_seat_subscriptions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    landlord_user_id: UUID = Field(foreign_key="users.id", index=True)
    stripe_subscription_id: str = Field(unique=True, index=True)
    stripe_price_id: str = Field(description="Stripe Price ID for $3/seat/month")
    quantity: int = Field(description="Number of seats subscribed", gt=0)
    status: str = Field(
        description="Subscription status: active, canceled, past_due, etc."
    )
    current_period_start: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    current_period_end: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
