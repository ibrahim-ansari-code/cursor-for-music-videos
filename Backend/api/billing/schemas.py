"""Billing API Schemas - Pydantic models for requests and responses"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Response Schemas
# ============================================================================

class SubscriptionPlanResponse(BaseModel):
    """Subscription plan details for display"""
    id: UUID
    name: str
    description: Optional[str]
    amount: Decimal = Field(description="Price in CAD")
    currency: str
    interval: str  # month, year
    interval_count: int
    trial_period_days: Optional[int]
    features: list[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class SubscriptionStatusResponse(BaseModel):
    """Current subscription status for user"""
    has_active_subscription: bool
    subscription_status: Optional[str] = None  # active, canceled, past_due, trialing, etc.
    subscription_tier: str = Field(default="free")  # free, premium
    
    # Period information
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    
    # Trial information
    trial_active: bool = False
    trial_ends_at: Optional[datetime] = None
    trial_days_remaining: Optional[int] = None
    
    # Cancellation information
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    
    # Plan details
    subscription_details: Optional[SubscriptionPlanResponse] = None
    
    class Config:
        from_attributes = True


class CheckoutSessionResponse(BaseModel):
    """Stripe Checkout Session URL for subscription"""
    checkout_url: str
    session_id: str


class CustomerPortalResponse(BaseModel):
    """Stripe Customer Portal URL for subscription management"""
    portal_url: str


# ============================================================================
# Request Schemas
# ============================================================================

class CreateCheckoutSessionRequest(BaseModel):
    """Request to create a Stripe Checkout Session"""
    price_id: Optional[str] = Field(
        default=None,
        description="Stripe Price ID (optional, defaults to platform price)"
    )
    success_url: Optional[str] = Field(
        default=None,
        description="URL to redirect after successful checkout"
    )
    cancel_url: Optional[str] = Field(
        default=None,
        description="URL to redirect if user cancels"
    )


class CreateCustomerPortalRequest(BaseModel):
    """Request to create Stripe Customer Portal session"""
    return_url: Optional[str] = Field(
        default=None,
        description="URL to return to after portal session"
    )

