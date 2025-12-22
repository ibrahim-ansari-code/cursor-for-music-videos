"""
Rent Payments Schemas

Pydantic models for rent payment API request/response validation.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import (
    MINIMUM_PAYMENT_CENTS,
    MAXIMUM_PAYMENT_CENTS,
    PaymentMethodType,
)


# =============================================================================
# Connect (Landlord Onboarding) Schemas
# =============================================================================

class ConnectOnboardingResponse(BaseModel):
    """Response after initiating Connect onboarding."""
    account_id: str = Field(..., description="Stripe account ID (acct_xxx)")
    onboarding_url: str = Field(..., description="URL to redirect landlord for onboarding")
    expires_at: datetime = Field(..., description="When the onboarding link expires")


class ConnectRefreshLinkResponse(BaseModel):
    """Response for refreshing an expired onboarding link."""
    onboarding_url: str
    expires_at: datetime


class ConnectDashboardLinkResponse(BaseModel):
    """Response for Express Dashboard login link."""
    dashboard_url: str
    expires_at: datetime


class ConnectStatusResponse(BaseModel):
    """Landlord's Connect account status."""
    is_connected: bool
    account_id: str | None = None
    
    # Onboarding status
    charges_enabled: bool = False
    payouts_enabled: bool = False
    details_submitted: bool = False
    
    # Computed status
    onboarding_status: str = "not_started"
    
    # Requirements and restrictions
    needs_action: bool = False
    disabled_reason: str | None = None
    requirements_currently_due: list[str] = []
    requirements_past_due: list[str] = []
    requirements_eventually_due: list[str] = []
    
    # Account info
    business_type: str | None = None
    country: str | None = None
    default_currency: str | None = None

    # Payment method preferences
    accepted_payment_methods: list[str] = Field(
        default_factory=lambda: ["card", "acss_debit"],
        description="Payment methods accepted by landlord: 'card', 'acss_debit'"
    )

    model_config = ConfigDict(from_attributes=True)


class UpdatePaymentPreferencesRequest(BaseModel):
    """Request to update landlord's payment method preferences."""
    accepted_payment_methods: list[str] = Field(
        ...,
        min_length=1,
        description="Payment methods to accept: 'card' (Credit/Debit - $8 fee), 'acss_debit' (PAD Bank Transfer - $3 fee)"
    )

    @field_validator('accepted_payment_methods')
    @classmethod
    def validate_payment_methods(cls, v: list[str]) -> list[str]:
        """Validate that only allowed payment methods are specified."""
        allowed = {"card", "acss_debit"}
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"Invalid payment methods: {invalid}. Allowed: {allowed}")
        if not v:
            raise ValueError("At least one payment method must be enabled")
        return list(set(v))  # Remove duplicates


class UpdatePaymentPreferencesResponse(BaseModel):
    """Response after updating payment method preferences."""
    accepted_payment_methods: list[str]
    message: str = "Payment preferences updated successfully"


# =============================================================================
# Payment Method Schemas
# =============================================================================

class SetupIntentResponse(BaseModel):
    """Response after creating a SetupIntent for adding payment method."""
    client_secret: str = Field(..., description="Client secret for Stripe.js")
    setup_intent_id: str = Field(..., description="SetupIntent ID (seti_xxx)")


class PaymentMethodCreate(BaseModel):
    """Request to save a payment method after Stripe confirmation."""
    stripe_payment_method_id: str = Field(..., description="Payment method ID from Stripe (pm_xxx)")
    set_as_default: bool = Field(False, description="Whether to set as default payment method")


class PaymentMethodResponse(BaseModel):
    """Saved payment method details."""
    id: UUID
    payment_method_type: str = Field(..., description="acss_debit or card")
    last_four: str | None = Field(None, description="Last 4 digits")
    
    # Bank account fields
    bank_name: str | None = None
    institution_number: str | None = None
    
    # Card fields
    brand: str | None = None
    exp_month: int | None = None
    exp_year: int | None = None
    
    # Status
    is_default: bool = False
    is_verified: bool = False
    is_usable: bool = True
    
    # Display
    display_name: str = Field(..., description="Human-readable name for UI")
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PaymentMethodListResponse(BaseModel):
    """List of tenant's payment methods."""
    items: list[PaymentMethodResponse]
    default_id: UUID | None = Field(None, description="ID of default payment method")


# =============================================================================
# Tenant Balance Schemas
# =============================================================================

class TenantBalanceResponse(BaseModel):
    """Current balance for a tenant's lease."""
    lease_id: int
    property_name: str
    unit_name: str | None = None
    
    # Balance info
    current_balance_cents: int = Field(..., description="Amount due in cents")
    current_balance: Decimal = Field(..., description="Amount due in dollars")
    currency: str = "cad"
    
    # Due date
    due_date: datetime | None = Field(None, description="When payment is due")
    rent_due_day: int = Field(..., description="Day of month rent is due (1-28)")
    
    # Monthly rent
    monthly_rent_cents: int
    monthly_rent: Decimal
    
    # Status
    is_past_due: bool = False
    days_overdue: int = 0
    
    # Landlord info for display
    landlord_name: str
    landlord_accepts_online_payments: bool = Field(
        ..., 
        description="Whether landlord has completed Connect onboarding"
    )


# =============================================================================
# Fee Preview Schemas
# =============================================================================

class FeeScheduleItem(BaseModel):
    """Fee for a specific payment method."""
    payment_method_type: str
    display_name: str
    fee_cents: int
    fee_display: str


class FeeScheduleResponse(BaseModel):
    """Platform fee schedule by payment method."""
    fees: list[FeeScheduleItem]
    currency: str = "cad"


# =============================================================================
# Payment Schemas
# =============================================================================

class PaymentRequest(BaseModel):
    """Request to initiate a rent payment."""
    lease_id: int = Field(..., description="Lease to pay rent for")
    amount_cents: int = Field(..., description="Amount to pay in cents")
    payment_method_id: UUID | None = Field(
        None, 
        description="Saved payment method ID (optional - can use new method)"
    )
    save_payment_method: bool = Field(
        False, 
        description="Whether to save the payment method for future use"
    )

    @field_validator("amount_cents")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v < MINIMUM_PAYMENT_CENTS:
            raise ValueError(f"Amount must be at least ${MINIMUM_PAYMENT_CENTS / 100:.2f}")
        if v > MAXIMUM_PAYMENT_CENTS:
            raise ValueError(f"Amount cannot exceed ${MAXIMUM_PAYMENT_CENTS / 100:.2f}")
        return v


class PaymentIntentResponse(BaseModel):
    """Response after creating a PaymentIntent."""
    transaction_id: UUID = Field(..., description="Internal transaction ID")
    client_secret: str = Field(..., description="Client secret for Stripe.js confirmation")
    payment_intent_id: str = Field(..., description="PaymentIntent ID (pi_xxx)")
    stripe_account_id: str = Field(..., description="Connected Stripe account ID for Elements")
    
    # Amounts
    amount_cents: int
    amount: Decimal = Field(..., description="Amount in dollars")
    application_fee_cents: int = Field(..., description="Platform fee in cents")
    application_fee: Decimal = Field(..., description="Platform fee in dollars")
    currency: str = "cad"
    
    # Status
    status: str = Field(..., description="PaymentIntent status")
    requires_action: bool = Field(False, description="Whether additional action is needed (3DS, etc.)")


class TransactionResponse(BaseModel):
    """Rent payment transaction details."""
    id: UUID
    lease_id: int
    tenant_id: int
    
    # Stripe info
    stripe_payment_intent_id: str | None = None
    stripe_charge_id: str | None = None
    receipt_url: str | None = Field(None, description="Stripe receipt URL for successful payments")
    
    # Amounts
    amount_cents: int
    amount: Decimal
    application_fee_cents: int
    application_fee: Decimal
    currency: str = "cad"
    
    # Status
    status: str
    failure_code: str | None = None
    failure_message: str | None = None
    
    # Payment method
    payment_method_type: str | None = None
    payment_method_last_four: str | None = None
    payment_method_bank_name: str | None = None
    
    # Display
    display_status: str = Field(..., description="Human-readable status for UI")
    
    # Timestamps
    initiated_at: datetime
    succeeded_at: datetime | None = None
    failed_at: datetime | None = None
    created_at: datetime
    
    # Related info (for display)
    property_name: str | None = None
    landlord_name: str | None = None
    
    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    """Paginated list of transactions."""
    items: list[TransactionResponse]
    total: int
    has_more: bool


# =============================================================================
# Autopay Schemas
# =============================================================================

class AutopayEnrollRequest(BaseModel):
    """Request to enroll in autopay."""
    lease_id: int
    payment_method_id: UUID = Field(..., description="Payment method to use for autopay")
    amount_cents: int | None = Field(
        None, 
        description="Amount to pay (defaults to monthly rent if not specified)"
    )


class AutopayUpdateRequest(BaseModel):
    """Request to update autopay settings."""
    payment_method_id: UUID | None = Field(None, description="New payment method")
    amount_cents: int | None = Field(None, description="New amount in cents")
    is_active: bool | None = Field(None, description="Enable/disable autopay")


class AutopayStatusResponse(BaseModel):
    """Autopay enrollment status."""
    lease_id: int
    is_enrolled: bool = False
    
    # If enrolled
    is_active: bool = False
    status: str = Field("not_enrolled", description="not_enrolled, active, paused, canceled")
    
    amount_cents: int | None = None
    amount: Decimal | None = None
    
    payment_method: PaymentMethodResponse | None = None
    
    next_scheduled_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_reason: str | None = None
    
    enrolled_at: datetime | None = None
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Webhook Schemas
# =============================================================================

class WebhookEventResponse(BaseModel):
    """Response after processing webhook."""
    received: bool = True
    event_id: str
    event_type: str
    processed: bool = False
    duplicate: bool = False
    error: str | None = None


# =============================================================================
# Error Schemas
# =============================================================================

class PaymentErrorResponse(BaseModel):
    """Error response for payment failures."""
    error_code: str
    error_message: str
    transaction_id: UUID | None = None
    is_retryable: bool = False
    suggested_action: str | None = None


# =============================================================================
# Refund Schemas
# =============================================================================

class RefundCreateRequest(BaseModel):
    """Request to issue a refund for a rent payment."""
    transaction_id: UUID | None = Field(None, description="Transaction UUID (set automatically from path)")
    amount_cents: int = Field(..., description="Amount to refund in cents")
    reason: str = Field(..., description="Reason for refund")
    notes: str | None = Field(None, description="Additional notes")
    refund_application_fee: bool = Field(
        False,
        description="Whether to refund the Brikli platform fee (always false - non-refundable)",
        frozen=True,
    )
    
    @field_validator("amount_cents")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Refund amount must be positive")
        if v > 1000000000:  # $10M sanity check
            raise ValueError("Refund amount exceeds maximum")
        return v
    
    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        valid_reasons = {
            "duplicate", "fraudulent", "requested_by_customer",
            "rent_adjustment", "lease_cancellation", "overpayment", "other"
        }
        if v not in valid_reasons:
            raise ValueError(f"Invalid reason. Must be one of: {', '.join(valid_reasons)}")
        return v


class RefundResponse(BaseModel):
    """Refund details."""
    id: UUID
    transaction_id: UUID
    stripe_refund_id: str
    stripe_charge_id: str
    
    # Amounts
    amount_cents: int
    amount: Decimal
    currency: str = "cad"
    application_fee_refunded_cents: int | None = None
    application_fee_refunded: Decimal | None = None
    
    # Status and reason
    status: str
    reason: str
    notes: str | None = None
    failure_reason: str | None = None
    
    # Who initiated
    initiated_by_user_id: UUID
    initiated_by_name: str | None = None
    
    # Timestamps
    created_at: datetime
    succeeded_at: datetime | None = None
    failed_at: datetime | None = None
    
    model_config = ConfigDict(from_attributes=True)


class RefundListResponse(BaseModel):
    """Paginated list of refunds."""
    items: list[RefundResponse]
    total: int
    has_more: bool


# =============================================================================
# Dispute Schemas
# =============================================================================

class DisputeResponse(BaseModel):
    """Dispute details."""
    id: UUID
    transaction_id: UUID
    stripe_dispute_id: str
    stripe_charge_id: str
    
    # Amounts
    amount_cents: int
    amount: Decimal
    currency: str = "cad"
    
    # Status and reason
    status: str
    reason: str
    
    # Evidence
    evidence_due_by: datetime | None = None
    evidence_submitted: bool = False
    evidence_submitted_at: datetime | None = None
    
    # Refundability
    is_charge_refundable: bool = True
    
    # Timestamps
    created_at: datetime
    closed_at: datetime | None = None
    
    # Notification status
    landlord_notified: bool = False
    landlord_notified_at: datetime | None = None
    
    # Derived fields for UI
    needs_attention: bool = Field(..., description="Whether landlord action is needed")
    days_until_due: int | None = Field(None, description="Days remaining to submit evidence")
    
    model_config = ConfigDict(from_attributes=True)


class DisputeListResponse(BaseModel):
    """Paginated list of disputes."""
    items: list[DisputeResponse]
    total: int
    has_more: bool
    active_disputes: int = Field(..., description="Count of disputes needing attention")
