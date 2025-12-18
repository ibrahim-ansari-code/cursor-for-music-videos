"""
Rent Payments Router

FastAPI endpoints for rent payment operations.
"""

import logging
import secrets
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from Backend.api.auth.dependencies import get_current_user
from Backend.config import settings
from Backend.database import get_session
from Backend.models.user import User

from . import connect_service, service, refund_service
from .autopay_service import AutopayService
from .schemas import (
    # Connect (Landlord)
    ConnectOnboardingResponse,
    ConnectRefreshLinkResponse,
    ConnectDashboardLinkResponse,
    ConnectStatusResponse,
    # Payment Methods (Tenant)
    SetupIntentResponse,
    PaymentMethodCreate,
    PaymentMethodResponse,
    PaymentMethodListResponse,
    # Balance (Tenant)
    TenantBalanceResponse,
    # Fees
    FeeScheduleResponse,
    FeeScheduleItem,
    # Payments (Tenant)
    PaymentRequest,
    PaymentIntentResponse,
    TransactionResponse,
    TransactionListResponse,
    # Autopay (Tenant)
    AutopayEnrollRequest,
    AutopayStatusResponse,
    # Refunds & Disputes (Landlord)
    RefundCreateRequest,
    RefundResponse,
    RefundListResponse,
    DisputeResponse,
    DisputeListResponse,
)
from .constants import (
    PLATFORM_FEES_CENTS,
    PAYMENT_METHOD_DISPLAY_NAMES,
)

router = APIRouter(prefix="/rent-payments", tags=["Rent Payments"])
logger = logging.getLogger(__name__)


# =============================================================================
# Connect Endpoints (Landlords)
# =============================================================================

@router.post(
    "/connect/onboard",
    response_model=ConnectOnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Connect onboarding",
    description="Create a Stripe Express account and return the onboarding URL",
)
async def create_connect_account(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ConnectOnboardingResponse:
    """
    Start Stripe Connect onboarding for a landlord.
    
    Returns a URL to redirect the landlord to Stripe for identity
    verification and bank account setup.
    """
    return await connect_service.create_connected_account(user, session)


@router.get(
    "/connect/status",
    response_model=ConnectStatusResponse,
    summary="Get Connect status",
    description="Check the landlord's Stripe Connect account status",
)
async def get_connect_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ConnectStatusResponse:
    """
    Get the Connect account status for the current landlord.
    """
    return await connect_service.get_connect_status(user, session)


@router.post(
    "/connect/refresh-link",
    response_model=ConnectRefreshLinkResponse,
    summary="Refresh onboarding link",
    description="Generate a new onboarding link for an incomplete account",
)
async def refresh_connect_link(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ConnectRefreshLinkResponse:
    """
    Generate a new onboarding link if the previous one expired.
    """
    return await connect_service.create_refresh_link(user, session)


@router.post(
    "/connect/dashboard-link",
    response_model=ConnectDashboardLinkResponse,
    summary="Get dashboard link",
    description="Generate a login link to the Stripe Express Dashboard",
)
async def get_dashboard_link(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ConnectDashboardLinkResponse:
    """
    Get a link to the Stripe Express Dashboard for the landlord.
    
    Allows them to view payouts, update bank info, etc.
    """
    return await connect_service.create_dashboard_link(user, session)


# =============================================================================
# Fee Schedule (Public)
# =============================================================================

@router.get(
    "/fees",
    response_model=FeeScheduleResponse,
    summary="Get fee schedule",
    description="Get platform fees by payment method type",
)
async def get_fee_schedule() -> FeeScheduleResponse:
    """
    Get the platform fee schedule.
    
    Fees vary by payment method:
    - Bank Transfer (PAD): $3.00
    - Credit/Debit Card: $8.00
    """
    fees = [
        FeeScheduleItem(
            payment_method_type=pm_type,
            display_name=PAYMENT_METHOD_DISPLAY_NAMES.get(pm_type, pm_type),
            fee_cents=fee_cents,
            fee_display=f"${fee_cents / 100:.2f}",
        )
        for pm_type, fee_cents in PLATFORM_FEES_CENTS.items()
    ]
    
    return FeeScheduleResponse(fees=fees)


# =============================================================================
# Payment Method Endpoints (Tenants)
# =============================================================================

@router.post(
    "/payment-methods/setup-intent",
    response_model=SetupIntentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create SetupIntent",
    description="Create a SetupIntent for adding a new payment method",
)
async def create_setup_intent(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SetupIntentResponse:
    """
    Create a Stripe SetupIntent for collecting payment method details.
    
    Returns a client_secret to use with Stripe.js Elements.
    """
    return await service.create_setup_intent(user, session)


@router.post(
    "/payment-methods",
    response_model=PaymentMethodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save payment method",
    description="Save a payment method after Stripe confirmation",
)
async def save_payment_method(
    data: PaymentMethodCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaymentMethodResponse:
    """
    Save a payment method after it's been confirmed with Stripe.
    
    Call this after the SetupIntent is confirmed on the frontend.
    """
    return await service.save_payment_method(user, data, session)


@router.get(
    "/payment-methods",
    response_model=PaymentMethodListResponse,
    summary="List payment methods",
    description="Get all saved payment methods for the tenant",
)
async def list_payment_methods(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaymentMethodListResponse:
    """
    List all saved payment methods for the current tenant.
    """
    return await service.list_payment_methods(user, session)


@router.delete(
    "/payment-methods/{payment_method_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete payment method",
    description="Remove a saved payment method",
)
async def delete_payment_method(
    payment_method_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a saved payment method.
    
    Cannot delete a method used by active autopay.
    """
    await service.delete_payment_method(user, payment_method_id, session)


@router.post(
    "/payment-methods/{payment_method_id}/set-default",
    response_model=PaymentMethodResponse,
    summary="Set default payment method",
    description="Set a payment method as the default",
)
async def set_default_payment_method(
    payment_method_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaymentMethodResponse:
    """
    Set a payment method as the default for future payments.
    """
    return await service.set_default_payment_method(user, payment_method_id, session)


# =============================================================================
# Balance Endpoints (Tenants)
# =============================================================================

@router.get(
    "/balance",
    response_model=TenantBalanceResponse,
    summary="Get current balance",
    description="Get the current rent balance for the tenant's active lease",
)
async def get_balance(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TenantBalanceResponse:
    """
    Get the current balance and due date for the tenant's lease.
    """
    return await service.get_tenant_balance(user, session)


# =============================================================================
# Payment Endpoints (Tenants)
# =============================================================================

@router.post(
    "/payments",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create payment",
    description="Create a rent payment (returns client_secret for confirmation)",
)
async def create_payment(
    data: PaymentRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaymentIntentResponse:
    """
    Create a rent payment via Stripe Connect Direct Charges.
    
    Returns a client_secret to use with Stripe.js for payment confirmation.
    The payment goes directly to the landlord's Stripe account with
    a 2% platform fee collected by Brikli.
    """
    return await service.create_payment(user, data, session)


@router.get(
    "/transactions",
    response_model=TransactionListResponse,
    summary="List transactions",
    description="Get payment transaction history",
)
async def list_transactions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TransactionListResponse:
    """
    List payment transactions for the current tenant.
    """
    return await service.list_transactions(user, session, limit, offset)


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction",
    description="Get details of a specific transaction",
)
async def get_transaction(
    transaction_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    """
    Get details of a specific payment transaction.
    """
    return await service.get_transaction(user, transaction_id, session)


# =============================================================================
# Autopay Endpoints (Tenants)
# =============================================================================

@router.post(
    "/autopay/enroll",
    response_model=AutopayStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll in autopay",
    description="Set up automatic monthly rent payments",
)
async def enroll_autopay(
    data: AutopayEnrollRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AutopayStatusResponse:
    """
    Enroll in autopay for automatic rent payments.
    
    Payments will be processed the day before rent is due.
    """
    return await service.enroll_autopay(user, data, session)


@router.get(
    "/autopay/{lease_id}",
    response_model=AutopayStatusResponse,
    summary="Get autopay status",
    description="Get autopay enrollment status for a lease",
)
async def get_autopay_status(
    lease_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AutopayStatusResponse:
    """
    Get the autopay enrollment status for a specific lease.
    """
    return await service.get_autopay_status(user, lease_id, session)


@router.delete(
    "/autopay/{lease_id}",
    response_model=AutopayStatusResponse,
    summary="Cancel autopay",
    description="Cancel autopay enrollment",
)
async def cancel_autopay(
    lease_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AutopayStatusResponse:
    """
    Cancel autopay enrollment for a lease.
    """
    return await service.cancel_autopay(user, lease_id, session)


# =============================================================================
# Refund Endpoints (Landlords)
# =============================================================================

@router.post(
    "/transactions/{transaction_id_or_pi}/refund",
    response_model=RefundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue refund",
    description="Issue a full or partial refund for a rent payment",
)
async def create_refund(
    transaction_id_or_pi: str,
    data: RefundCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RefundResponse:
    """
    Issue a refund for a rent payment transaction.
    
    Accepts either:
    - Database transaction UUID (e.g., 123e4567-e89b-12d3-a456-426614174000)
    - Stripe PaymentIntent ID (e.g., pi_3SfFLz3GT40zOq8I09erYBvw)
    
    Only landlords can issue refunds for transactions on their properties.
    Refunds can be partial or full. Platform fee is non-refundable.
    """
    # Check if it's a UUID or Stripe PI ID
    try:
        # Try parsing as UUID
        transaction_uuid = UUID(transaction_id_or_pi)
        data.transaction_id = transaction_uuid
    except ValueError:
        # It's a Stripe PaymentIntent ID, look up the transaction
        from sqlmodel import select, col
        from Backend.models.rent_payment_transaction import RentPaymentTransaction
        
        transaction = await session.scalar(
            select(RentPaymentTransaction).where(
                col(RentPaymentTransaction.stripe_payment_intent_id) == transaction_id_or_pi
            )
        )
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction not found for PaymentIntent: {transaction_id_or_pi}"
            )
        
        data.transaction_id = transaction.id
    
    return await refund_service.create_refund(user, data, session)


@router.get(
    "/refunds",
    response_model=RefundListResponse,
    summary="List refunds",
    description="Get all refunds for the landlord's properties",
)
async def list_refunds(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of refunds to return"),
    offset: int = Query(0, ge=0, description="Number of refunds to skip"),
    transaction_id: UUID | None = Query(None, description="Filter by transaction ID"),
    status: str | None = Query(None, description="Filter by status"),
) -> RefundListResponse:
    """
    List all refunds for the landlord's properties.
    
    Supports pagination and filtering by transaction or status.
    """
    return await refund_service.list_refunds(
        user, session, limit, offset, transaction_id, status
    )


@router.get(
    "/refunds/{refund_id}",
    response_model=RefundResponse,
    summary="Get refund",
    description="Get details of a specific refund",
)
async def get_refund(
    refund_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RefundResponse:
    """
    Get refund details by ID.
    """
    return await refund_service.get_refund(user, refund_id, session)


# =============================================================================
# Dispute Endpoints (Landlords)
# =============================================================================

@router.get(
    "/disputes",
    response_model=DisputeListResponse,
    summary="List disputes",
    description="Get all disputes for the landlord's properties",
)
async def list_disputes(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of disputes to return"),
    offset: int = Query(0, ge=0, description="Number of disputes to skip"),
    status: str | None = Query(None, description="Filter by status"),
    needs_attention_only: bool = Query(False, description="Only show disputes needing action"),
) -> DisputeListResponse:
    """
    List all disputes for the landlord's properties.
    
    Supports filtering to show only disputes that need attention (evidence submission).
    """
    return await refund_service.list_disputes(
        user, session, limit, offset, status, needs_attention_only
    )


@router.get(
    "/disputes/{dispute_id}",
    response_model=DisputeResponse,
    summary="Get dispute",
    description="Get details of a specific dispute",
)
async def get_dispute(
    dispute_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DisputeResponse:
    """
    Get dispute details by ID.
    """
    return await refund_service.get_dispute(user, dispute_id, session)


# =============================================================================
# Internal Scheduled Job Endpoints (Called by pg_cron)
# =============================================================================

@router.post("/scheduled/process-autopay", include_in_schema=False)
async def trigger_autopay_processing(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    [Internal] Scheduled job endpoint for processing daily autopay.
    
    Called by pg_cron daily to process all autopay enrollments that are due.
    Handles payment creation, retries, and notifications.
    
    Authentication: Requires X-Internal-API-Key header.
    """
    # Verify internal API key
    api_key = request.headers.get('X-Internal-API-Key')
    if not api_key or not secrets.compare_digest(api_key, settings.INTERNAL_CRON_API_KEY):
        logger.warning("Unauthorized autopay processing trigger attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    logger.info("🔄 Starting scheduled autopay processing via cron")
    try:
        result = await AutopayService.process_daily_autopay(session)
        logger.info(f"✅ Autopay processing complete: {result}")
        return result
    except Exception as e:
        logger.exception("Failed to process autopay")
        # The service itself handles per-enrollment errors.
        # This exception is for catastrophic failures.
        raise HTTPException(status_code=500, detail=f"Catastrophic failure in autopay processing: {type(e).__name__}")
