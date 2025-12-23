"""
Rent Payment Service

Core business logic for tenant rent payments via Stripe Connect Direct Charges.
"""

import logging
from calendar import monthrange
from datetime import datetime, date
from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select
import stripe

from Backend.api.stripe.client import get_stripe_client
from Backend.config import settings
from Backend.models.accounting.common import PaymentStatus
from Backend.models.accounting.payment import Payment, PaymentMethod as PaymentMethodEnum
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.models.stripe_connected_account import StripeConnectedAccount
from Backend.models.tenant_payment_method import TenantPaymentMethod
from Backend.models.rent_payment_transaction import (
    RentPaymentTransaction,
    RentPaymentTransactionStatus,
)
from Backend.models.rent_autopay_enrollment import RentAutopayEnrollment
from Backend.models.rent_payment_refund import RentPaymentRefund, RefundStatus, RefundReason
from Backend.models.rent_payment_dispute import RentPaymentDispute, DisputeStatus
from Backend.utils.datetime_utils import utc_now

from .constants import (
    calculate_application_fee_cents,
    DEFAULT_CURRENCY,
    MINIMUM_PAYMENT_CENTS,
    PAD_MANDATE_TEXT,
    PaymentMethodType,
)
from .schemas import (
    TenantBalanceResponse,
    SetupIntentResponse,
    PaymentMethodCreate,
    PaymentMethodResponse,
    PaymentMethodListResponse,
    PaymentRequest,
    RefundCreateRequest,
    RefundResponse,
    RefundListResponse,
    DisputeResponse,
    DisputeListResponse,
    PaymentIntentResponse,
    TransactionResponse,
    TransactionListResponse,
    AutopayEnrollRequest,
    AutopayUpdateRequest,
    AutopayStatusResponse,
)
from .connect_service import get_connected_account_for_landlord

logger = logging.getLogger(__name__)


# =============================================================================
# Tenant Balance
# =============================================================================

async def get_tenant_balance(
    user: User,
    session: AsyncSession,
) -> TenantBalanceResponse:
    """
    Get the current balance for a tenant's active lease.
    
    Args:
        user: The tenant user
        session: Database session
        
    Returns:
        TenantBalanceResponse with balance details
    """
    # Get tenant record
    tenant = await _get_tenant_for_user(user, session)
    
    # Get active lease with property info
    lease_query = (
        select(Lease)
        .options(
            selectinload(getattr(Lease, "property")).selectinload(getattr(Property, "owner")),
            selectinload(getattr(Lease, "unit")),
        )
        .where(
            col(Lease.tenant_id) == tenant.id,
            col(Lease.status) == LeaseStatus.ACTIVE,
        )
    )
    
    lease = await session.scalar(lease_query)
    
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active lease found"
        )
    
    # Calculate due date for this month

    today = date.today()
    due_day = lease.rent_due_day or 1

    # Get actual number of days in this month
    days_in_month = monthrange(today.year, today.month)[1]

    # Use the lease's due_day, capped to days in this month
    actual_due_day = min(due_day, days_in_month)

    due_date = datetime(today.year, today.month, actual_due_day, tzinfo=utc_now().tzinfo)
    
    # Calculate total rent due and total paid over the lease lifetime
    from Backend.utils.datetime_utils import months_between
    
    lease_start_date = lease.start_date
    
    # Calculate total rent accrued since lease start
    # Add 1 because the start month counts as a full month
    num_months = months_between(lease_start_date, today) + 1
    total_rent_due_cents = int(lease.monthly_rent * 100) * num_months
    
    # Calculate all payments made for this lease
    total_payments_query = select(func.coalesce(func.sum(RentPaymentTransaction.amount_cents), 0)).where(
        and_(
            col(RentPaymentTransaction.lease_id) == lease.id,
            col(RentPaymentTransaction.status) == RentPaymentTransactionStatus.SUCCEEDED,
        )
    )
    total_paid_cents = await session.scalar(total_payments_query) or 0
    
    # Calculate total refunds issued
    total_refunds_query = (
        select(func.coalesce(func.sum(RentPaymentRefund.amount_cents), 0))
        .join(RentPaymentTransaction, col(RentPaymentRefund.transaction_id) == col(RentPaymentTransaction.id))
        .where(
            and_(
                col(RentPaymentTransaction.lease_id) == lease.id,
                col(RentPaymentRefund.status) == RefundStatus.SUCCEEDED,
            )
        )
    )
    total_refunded_cents = await session.scalar(total_refunds_query) or 0
    
    # Net payments = total payments - total refunds
    net_paid_cents = total_paid_cents - total_refunded_cents
    
    # Calculate current balance (total rent due - net payments)
    monthly_rent_cents = int(lease.monthly_rent * 100)
    current_balance_cents = max(0, total_rent_due_cents - int(net_paid_cents))
    
    logger.info(
        f"Balance calculation | "
        f"lease_id={lease.id} | "
        f"lease_start={lease_start_date} | "
        f"months_elapsed={num_months} | "
        f"total_due=${total_rent_due_cents/100:.2f} | "
        f"total_paid=${total_paid_cents/100:.2f} | "
        f"total_refunded=${total_refunded_cents/100:.2f} | "
        f"net_paid=${net_paid_cents/100:.2f} | "
        f"balance=${current_balance_cents/100:.2f}"
    )
    
    # Check if past due
    is_past_due = today > due_date.date() if due_date else False
    days_overdue = (today - due_date.date()).days if is_past_due else 0
    
    # Check if landlord accepts online payments
    landlord_accepts = await _landlord_accepts_online_payments(
        str(lease.property.user_id), session
    ) if lease.property else False
    
    # Get landlord name
    landlord_name = "Your Landlord"
    if lease.property and lease.property.owner:
        owner = lease.property.owner
        if owner.first_name or owner.last_name:
            landlord_name = f"{owner.first_name or ''} {owner.last_name or ''}".strip()
    
    return TenantBalanceResponse(
        lease_id=lease.id,  # type: ignore[arg-type]
        property_name=lease.property.name if lease.property else "Unknown Property",
        unit_name=lease.unit.name if lease.unit else None,
        current_balance_cents=current_balance_cents,
        current_balance=Decimal(current_balance_cents) / 100,
        currency=DEFAULT_CURRENCY,
        due_date=due_date,
        rent_due_day=due_day,
        monthly_rent_cents=monthly_rent_cents,
        monthly_rent=Decimal(monthly_rent_cents) / 100,
        is_past_due=is_past_due,
        days_overdue=days_overdue,
        landlord_name=landlord_name,
        landlord_accepts_online_payments=landlord_accepts,
    )


# =============================================================================
# Payment Methods
# =============================================================================

async def create_setup_intent(
    user: User,
    session: AsyncSession,
) -> SetupIntentResponse:
    """
    Create a SetupIntent for adding a new payment method.
    
    The client uses this to collect payment details via Stripe Elements.
    
    Args:
        user: The tenant user
        session: Database session
        
    Returns:
        SetupIntentResponse with client secret for Stripe.js
    """
    tenant = await _get_tenant_for_user(user, session)
    
    # Get active lease to find landlord's connected account
    lease = await _get_active_lease_for_tenant(tenant.id, session)  # type: ignore[arg-type]
    if not lease or not lease.property:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active lease found"
        )
    
    # Get landlord's connected account
    connected_account = await get_connected_account_for_landlord(
        str(lease.property.user_id), session
    )
    
    if not connected_account or not connected_account.is_fully_onboarded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your landlord has not set up online payments yet"
        )
    
    try:
        stripe_client = get_stripe_client()
        
        # Generate idempotency key to prevent duplicate SetupIntents on retry
        # Stable within 5-minute window to allow retries
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        idempotency_key = f"setup-intent-{tenant.id}-{timestamp}"
        
        # Use the landlord's configured accepted_payment_methods
        accepted_methods = connected_account.accepted_payment_methods or ["card", "acss_debit"]

        # Build payment method options only for methods that are enabled
        payment_method_options = {}
        if "acss_debit" in accepted_methods:
            payment_method_options["acss_debit"] = {
                "currency": "cad",
                "mandate_options": {
                    "payment_schedule": "sporadic",
                    "transaction_type": "personal",
                },
                "verification_method": "automatic",
            }

        # Create SetupIntent on the connected account
        setup_intent = await stripe_client.setup_intents.create(
            payment_method_types=accepted_methods,
            payment_method_options=payment_method_options if payment_method_options else None,
            metadata={
                "tenant_id": str(tenant.id),
                "user_id": str(user.id),
            },
            idempotency_key=idempotency_key,
        )
        
        return SetupIntentResponse(
            client_secret=setup_intent.client_secret,
            setup_intent_id=setup_intent.id,
        )
        
    except stripe.StripeError as e:
        logger.error(f"Stripe error creating SetupIntent: {e}")
        
        # Provide more descriptive error messages
        error_message = "Failed to initialize payment method setup"
        
        if isinstance(e, stripe.InvalidRequestError):
            error_str = str(e)
            if "not set up" in error_str.lower():
                error_message = "Online payments are not available. Your landlord needs to complete payment setup."
            elif "account" in error_str.lower():
                error_message = "Payment setup is temporarily unavailable. Please try again later."
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_message
        )


async def save_payment_method(
    user: User,
    data: PaymentMethodCreate,
    session: AsyncSession,
) -> PaymentMethodResponse:
    """
    Save a payment method after Stripe confirmation.
    
    Args:
        user: The tenant user
        data: Payment method details from Stripe
        session: Database session
        
    Returns:
        PaymentMethodResponse with saved method details
    """
    tenant = await _get_tenant_for_user(user, session)
    
    # Fetch payment method details from Stripe
    try:
        stripe_client = get_stripe_client()
        pm = await stripe_client.payment_methods.retrieve(data.stripe_payment_method_id)
        
        # Determine type and extract details
        pm_type = pm.type
        last_four = None
        bank_name = None
        institution_number = None
        brand = None
        exp_month = None
        exp_year = None
        is_verified = True  # Cards are always verified
        
        if pm_type == "card" and pm.card:
            last_four = pm.card.last4
            brand = pm.card.brand
            exp_month = pm.card.exp_month
            exp_year = pm.card.exp_year
        elif pm_type == "acss_debit" and pm.acss_debit:
            last_four = pm.acss_debit.last4
            bank_name = pm.acss_debit.bank_name
            institution_number = pm.acss_debit.institution_number
            # PAD requires asynchronous verification.
            # The status will be updated via webhooks.
            is_verified = False
        
        # Check if this payment method already exists
        existing = await session.scalar(
            select(TenantPaymentMethod).where(
                col(TenantPaymentMethod.stripe_payment_method_id) == data.stripe_payment_method_id
            )
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This payment method is already saved"
            )
        
        # If setting as default, unset other defaults
        if data.set_as_default:
            await _unset_default_payment_method(tenant.id, session)  # type: ignore[arg-type]
        
        # Create record
        payment_method = TenantPaymentMethod(
            tenant_id=tenant.id,  # type: ignore[arg-type]
            stripe_payment_method_id=data.stripe_payment_method_id,
            payment_method_type=pm_type,
            last_four=last_four,
            bank_name=bank_name,
            institution_number=institution_number,
            brand=brand,
            exp_month=exp_month,
            exp_year=exp_year,
            is_default=data.set_as_default,
            is_verified=is_verified,
        )
        
        session.add(payment_method)
        await session.commit()
        await session.refresh(payment_method)
        
        logger.info(
            f"Saved payment method | "
            f"tenant_id={tenant.id} | "
            f"type={pm_type} | "
            f"pm_id={payment_method.id}"
        )
        
        return _build_payment_method_response(payment_method)
        
    except stripe.StripeError as e:
        logger.error(f"Stripe error retrieving payment method: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify payment method"
        )


async def list_payment_methods(
    user: User,
    session: AsyncSession,
) -> PaymentMethodListResponse:
    """
    List all saved payment methods for a tenant.
    
    Args:
        user: The tenant user
        session: Database session
        
    Returns:
        PaymentMethodListResponse with list of methods
    """
    tenant = await _get_tenant_for_user(user, session)
    
    result = await session.execute(
        select(TenantPaymentMethod)
        .where(col(TenantPaymentMethod.tenant_id) == tenant.id)
        .order_by(col(TenantPaymentMethod.is_default).desc(), col(TenantPaymentMethod.created_at).desc())
    )
    methods = result.scalars().all()
    
    default_id = None
    items = []
    for method in methods:
        if method.is_default:
            default_id = method.id
        items.append(_build_payment_method_response(method))
    
    return PaymentMethodListResponse(items=items, default_id=default_id)


async def delete_payment_method(
    user: User,
    payment_method_id: UUID,
    session: AsyncSession,
) -> None:
    """
    Delete a saved payment method.
    
    Args:
        user: The tenant user
        payment_method_id: ID of payment method to delete
        session: Database session
    """
    tenant = await _get_tenant_for_user(user, session)
    
    method = await session.scalar(
        select(TenantPaymentMethod).where(
        col(TenantPaymentMethod.id) == payment_method_id,
        col(TenantPaymentMethod.tenant_id) == tenant.id,
    )
    )
    
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    # Check if used by active autopay
    autopay = await session.scalar(
        select(RentAutopayEnrollment).where(
            col(RentAutopayEnrollment.payment_method_id) == payment_method_id,
            col(RentAutopayEnrollment.tenant_id) == tenant.id,
            col(RentAutopayEnrollment.is_active) == True,  # noqa: E712
        )
    )
    
    if autopay:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete payment method used by active autopay. Disable autopay first."
        )
    
    # Detach from Stripe
    try:
        stripe_client = get_stripe_client()
        await stripe_client.payment_methods.detach(method.stripe_payment_method_id)
    except stripe.StripeError as e:
        logger.warning(f"Failed to detach payment method from Stripe: {e}")
        # Continue with deletion anyway
    
    await session.delete(method)
    await session.commit()
    
    logger.info(f"Deleted payment method | tenant_id={tenant.id} | pm_id={payment_method_id}")


async def set_default_payment_method(
    user: User,
    payment_method_id: UUID,
    session: AsyncSession,
) -> PaymentMethodResponse:
    """
    Set a payment method as the default.
    
    Args:
        user: The tenant user
        payment_method_id: ID of payment method to set as default
        session: Database session
        
    Returns:
        PaymentMethodResponse with updated method
    """
    tenant = await _get_tenant_for_user(user, session)
    
    method = await session.scalar(
        select(TenantPaymentMethod).where(
        col(TenantPaymentMethod.id) == payment_method_id,
        col(TenantPaymentMethod.tenant_id) == tenant.id,
    )
    )
    
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    # Unset other defaults
    await _unset_default_payment_method(tenant.id, session)  # type: ignore[arg-type]
    
    # Set this as default
    method.is_default = True
    method.updated_at = utc_now()
    session.add(method)
    await session.commit()
    await session.refresh(method)
    
    return _build_payment_method_response(method)


# =============================================================================
# Payments
# =============================================================================

async def create_payment(
    user: User,
    data: PaymentRequest,
    session: AsyncSession,
) -> PaymentIntentResponse:
    """
    Create a rent payment via Stripe Connect Direct Charges.
    
    This creates a PaymentIntent on the landlord's connected account,
    with an application fee going to Brikli.
    
    Args:
        user: The tenant user
        data: Payment request details
        session: Database session
        
    Returns:
        PaymentIntentResponse with client secret for confirmation
    """
    tenant = await _get_tenant_for_user(user, session)
    
    # Validate lease
    lease = await _get_lease_by_id(data.lease_id, session)
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lease not found"
        )
    
    if lease.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only pay rent for your own lease"
        )
    
    if lease.status != LeaseStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot pay rent for inactive lease"
        )
    
    # Get landlord's connected account
    landlord_user_id = str(lease.property.user_id) if lease.property else None
    if not landlord_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lease property not found"
        )
    
    connected_account = await get_connected_account_for_landlord(landlord_user_id, session)
    
    if not connected_account or not connected_account.is_fully_onboarded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your landlord has not set up online payments"
        )
    
    # Get payment method (required for fee calculation)
    payment_method_stripe_id = None
    payment_method_type = "card"  # Default to higher fee if unknown
    
    if data.payment_method_id:
        pm = await session.scalar(
            select(TenantPaymentMethod).where(
            col(TenantPaymentMethod.id) == data.payment_method_id,
            col(TenantPaymentMethod.tenant_id) == tenant.id,
        )
        )
        if not pm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment method not found"
            )
        if not pm.is_usable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment method cannot be used"
            )
        payment_method_stripe_id = pm.stripe_payment_method_id
        payment_method_type = pm.payment_method_type
    
    # Calculate application fee based on payment method type
    # PAD (acss_debit): $3.00 | Card: $8.00
    application_fee_cents = calculate_application_fee_cents(
        data.amount_cents, 
        payment_method_type
    )
    
    # Generate descriptive payment description
    from datetime import datetime, timezone
    from Backend.models.enums import TenantType
    
    current_month_year = datetime.now(timezone.utc).strftime("%b %Y")
    
    # Handle both individual and company tenants
    if tenant.tenant_type == TenantType.COMPANY and tenant.company_name:
        tenant_display_name = tenant.company_name
    elif tenant.first_name and tenant.last_name:
        tenant_display_name = f"{tenant.first_name} {tenant.last_name}"
    else:
        tenant_display_name = f"Tenant #{tenant.id}"
    
    payment_description = f"{current_month_year} Rent Payment from {tenant_display_name}"
    
    try:
        stripe_client = get_stripe_client()
        
        # Generate idempotency key to prevent duplicate charges on retry
        # Stable within 5-minute window for same lease + amount
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        idempotency_key = f"rent-payment-{data.lease_id}-{data.amount_cents}-{timestamp}"
        
        # Create PaymentIntent on the connected account (Direct Charge)
        # Use the landlord's configured accepted_payment_methods
        # This allows landlords to control which methods they accept (different fees apply)
        accepted_methods = connected_account.accepted_payment_methods

        # Validate at least one payment method is enabled. Fallback for None.
        if not accepted_methods:
            # If the list is explicitly empty, it's a configuration error.
            if accepted_methods is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No payment methods are enabled for this landlord"
                )
            # If the field is None (e.g., older records), apply default.
            accepted_methods = ["card", "acss_debit"]

        pi_params = {
            "amount": data.amount_cents,
            "currency": DEFAULT_CURRENCY,
            "application_fee_amount": application_fee_cents,
            "payment_method_types": accepted_methods,
            "description": payment_description,
            "metadata": {
                "tenant_id": str(tenant.id),
                "tenant_name": tenant_display_name,
                "lease_id": str(data.lease_id),
                "platform": "brikli",
            },
            "stripe_account": connected_account.stripe_account_id,
            "idempotency_key": idempotency_key,
        }

        # Attach payment method if provided
        if payment_method_stripe_id:
            pi_params["payment_method"] = payment_method_stripe_id

        # Configure ACSS debit mandate options (applies when that method is selected)
        pi_params["payment_method_options"] = {
            "acss_debit": {
                "mandate_options": {
                    "payment_schedule": "sporadic",
                    "transaction_type": "personal",
                },
                "verification_method": "automatic",
            }
        }
        
        payment_intent = await stripe_client.payment_intents.create(**pi_params)
        
        # Create transaction record
        transaction = RentPaymentTransaction(
            lease_id=data.lease_id,
            tenant_id=tenant.id,  # type: ignore[arg-type]
            landlord_user_id=UUID(landlord_user_id),
            connected_account_id=connected_account.id,
            payment_method_id=data.payment_method_id,
            stripe_payment_intent_id=payment_intent.id,
            amount_cents=data.amount_cents,
            application_fee_cents=application_fee_cents,
            currency=DEFAULT_CURRENCY,
            status=RentPaymentTransactionStatus.PENDING,
        )
        
        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)
        
        logger.info(
            f"Created rent payment | "
            f"tenant_id={tenant.id} | "
            f"lease_id={data.lease_id} | "
            f"amount=${data.amount_cents / 100:.2f} | "
            f"pi_id={payment_intent.id}"
        )
        
        return PaymentIntentResponse(
            transaction_id=transaction.id,  # type: ignore[arg-type]
            client_secret=payment_intent.client_secret,
            payment_intent_id=payment_intent.id,
            stripe_account_id=connected_account.stripe_account_id,
            amount_cents=data.amount_cents,
            amount=Decimal(data.amount_cents) / 100,
            application_fee_cents=application_fee_cents,
            application_fee=Decimal(application_fee_cents) / 100,
            currency=DEFAULT_CURRENCY,
            status=payment_intent.status,
            requires_action=payment_intent.status == "requires_action",
        )
        
    except stripe.StripeError as e:
        logger.error(f"Stripe error creating payment: {e}")
        
        # Provide more descriptive error messages based on error type
        error_message = "Failed to create payment. Please try again."
        
        if isinstance(e, stripe.InvalidRequestError):
            error_str = str(e)
            
            # Check for amount limit errors
            if "does not support payment amounts greater than" in error_str:
                # Extract the limit if possible
                if "acss_debit" in error_str or "PAD" in error_str:
                    error_message = (
                        "Payment amount exceeds the limit for bank transfers. "
                        "Please try a smaller amount or use a credit/debit card instead."
                    )
                else:
                    error_message = (
                        "Payment amount exceeds the allowed limit. "
                        "Please try a smaller amount."
                    )
            # Check for account not ready
            elif "not set up" in error_str.lower() or "not available" in error_str.lower():
                error_message = "Online payments are not available at this time. Please contact your landlord."
            # Check for payment method errors
            elif "payment method" in error_str.lower():
                error_message = "There was an issue with your payment method. Please try a different one."
            else:
                # Use the Stripe error message if it's user-friendly
                error_message = f"Payment failed: {e.user_message or error_str}"
        
        elif isinstance(e, stripe.CardError):
            # Card-specific errors (declined, insufficient funds, etc.)
            error_message = f"Card error: {e.user_message or 'Your card was declined. Please try a different payment method.'}"
        
        elif isinstance(e, stripe.AuthenticationError):
            error_message = "Payment service authentication error. Please contact support."
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_message
    )


async def get_transaction(
    user: User,
    transaction_id: UUID,
    session: AsyncSession,
) -> TransactionResponse:
    """
    Get details of a specific transaction.
    
    Args:
        user: The tenant user
        transaction_id: Transaction ID
        session: Database session
        
    Returns:
        TransactionResponse with transaction details
    """
    tenant = await _get_tenant_for_user(user, session)
    
    transaction = await session.scalar(
        select(RentPaymentTransaction)
        .options(selectinload(getattr(RentPaymentTransaction, "lease")))
        .where(
            col(RentPaymentTransaction.id) == transaction_id,
            col(RentPaymentTransaction.tenant_id) == tenant.id,
        )
    )
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return _build_transaction_response(transaction)


async def list_transactions(
    user: User,
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0,
) -> TransactionListResponse:
    """
    List transactions for a tenant.
    
    Args:
        user: The tenant user
        session: Database session
        limit: Max results to return
        offset: Pagination offset
        
    Returns:
        TransactionListResponse with paginated transactions
    """
    tenant = await _get_tenant_for_user(user, session)
    
    # Get total count
    count_query = select(func.count(col(RentPaymentTransaction.id))).where(
        col(RentPaymentTransaction.tenant_id) == tenant.id
    )
    total = await session.scalar(count_query) or 0
    
    # Get paginated results
    result = await session.execute(
        select(RentPaymentTransaction)
        .options(
            selectinload(getattr(RentPaymentTransaction, "lease"))
            .selectinload(getattr(Lease, "property"))
        )
        .where(col(RentPaymentTransaction.tenant_id) == tenant.id)
        .order_by(col(RentPaymentTransaction.created_at).desc())
        .offset(offset)
        .limit(limit + 1)  # Fetch one extra to check has_more
    )
    transactions = list(result.scalars().all())
    
    has_more = len(transactions) > limit
    items = [_build_transaction_response(t) for t in transactions[:limit]]
    
    return TransactionListResponse(
        items=items,
        total=total,
        has_more=has_more,
        )


# =============================================================================
# Autopay
# =============================================================================

async def enroll_autopay(
    user: User,
    data: AutopayEnrollRequest,
    session: AsyncSession,
) -> AutopayStatusResponse:
    """
    Enroll in autopay for a lease.
    
    Args:
        user: The tenant user
        data: Autopay enrollment request
        session: Database session
        
    Returns:
        AutopayStatusResponse with enrollment status
    """
    tenant = await _get_tenant_for_user(user, session)
    
    # Validate lease
    lease = await _get_lease_by_id(data.lease_id, session)
    if not lease or lease.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lease not found"
        )
    
    # Validate payment method
    pm = await session.scalar(
        select(TenantPaymentMethod).where(
        col(TenantPaymentMethod.id) == data.payment_method_id,
        col(TenantPaymentMethod.tenant_id) == tenant.id,
    )
    )
    
    if not pm or not pm.is_usable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unusable payment method"
        )
    
    # Get or create enrollment
    enrollment = await session.scalar(
        select(RentAutopayEnrollment).where(
        col(RentAutopayEnrollment.lease_id) == data.lease_id
    )
    )
    
    # Determine amount
    amount_cents = data.amount_cents or int(lease.monthly_rent * 100)
    
    # Calculate next scheduled date using AutopayService's proper date calculation
    from .autopay_service import AutopayService
    from datetime import date
    next_scheduled = AutopayService._calculate_next_autopay_date(
        rent_due_day=lease.rent_due_day or 1,
        from_date=date.today()
    )
    
    if enrollment:
        # Update existing
        enrollment.payment_method_id = data.payment_method_id
        enrollment.amount_cents = amount_cents
        enrollment.is_active = True
        enrollment.canceled_at = None
        enrollment.paused_at = None
        enrollment.next_scheduled_at = next_scheduled
        if not enrollment.enrolled_at:
            enrollment.enrolled_at = utc_now()
        enrollment.updated_at = utc_now()
    else:
        # Create new
        enrollment = RentAutopayEnrollment(
            lease_id=data.lease_id,
            tenant_id=tenant.id,  # type: ignore[arg-type]
            payment_method_id=data.payment_method_id,
            is_active=True,
            amount_cents=amount_cents,
            enrolled_at=utc_now(),
            next_scheduled_at=next_scheduled,
        )
    
    session.add(enrollment)
    await session.commit()
    await session.refresh(enrollment)
    
    logger.info(f"Enrolled autopay | tenant_id={tenant.id} | lease_id={data.lease_id}")
    
    return await get_autopay_status(user, data.lease_id, session)


async def get_autopay_status(
    user: User,
    lease_id: int,
    session: AsyncSession,
) -> AutopayStatusResponse:
    """
    Get autopay enrollment status for a lease.
    
    Args:
        user: The tenant user
        lease_id: Lease ID
        session: Database session
        
    Returns:
        AutopayStatusResponse with enrollment details
    """
    tenant = await _get_tenant_for_user(user, session)
    
    enrollment = await session.scalar(
        select(RentAutopayEnrollment)
        .options(selectinload(getattr(RentAutopayEnrollment, "payment_method")))
        .where(
            col(RentAutopayEnrollment.lease_id) == lease_id,
            col(RentAutopayEnrollment.tenant_id) == tenant.id,
        )
    )
    
    if not enrollment:
        return AutopayStatusResponse(
            lease_id=lease_id,
            is_enrolled=False,
            status="not_enrolled",
        )
    
    pm_response = None
    if enrollment.payment_method:
        pm_response = _build_payment_method_response(enrollment.payment_method)
    
    return AutopayStatusResponse(
        lease_id=lease_id,
        is_enrolled=True,
        is_active=enrollment.is_active,
        status=enrollment.status,
        amount_cents=enrollment.amount_cents,
        amount=enrollment.amount_dollars,
        payment_method=pm_response,
        next_scheduled_at=enrollment.next_scheduled_at,
        last_success_at=enrollment.last_success_at,
        last_failure_reason=enrollment.last_failure_reason,
        enrolled_at=enrollment.enrolled_at,
    )


async def cancel_autopay(
    user: User,
    lease_id: int,
    session: AsyncSession,
) -> AutopayStatusResponse:
    """
    Cancel autopay enrollment.
    
    Args:
        user: The tenant user
        lease_id: Lease ID
        session: Database session
        
    Returns:
        AutopayStatusResponse with updated status
    """
    tenant = await _get_tenant_for_user(user, session)
    
    enrollment = await session.scalar(
        select(RentAutopayEnrollment).where(
            col(RentAutopayEnrollment.lease_id) == lease_id,
            col(RentAutopayEnrollment.tenant_id) == tenant.id,
        )
    )
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Autopay enrollment not found"
        )
    
    enrollment.is_active = False
    enrollment.canceled_at = utc_now()
    enrollment.next_scheduled_at = None
    enrollment.updated_at = utc_now()
    
    session.add(enrollment)
    await session.commit()
    
    logger.info(f"Canceled autopay | tenant_id={tenant.id} | lease_id={lease_id}")
    
    return await get_autopay_status(user, lease_id, session)


# =============================================================================
# Internal Helpers
# =============================================================================

async def _get_tenant_for_user(user: User, session: AsyncSession) -> Tenant:
    """Get tenant record for a user."""
    if user.user_type != UserType.TENANT:
            raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenants can access this resource"
        )
    
    tenant = await session.scalar(
        select(Tenant).where(col(Tenant.user_id) == user.id)
            )
        
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant profile not found"
        )
    
    return tenant


async def _get_active_lease_for_tenant(
    tenant_id: int,
    session: AsyncSession,
) -> Lease | None:
    """Get active lease for a tenant with property loaded."""
    return await session.scalar(
        select(Lease)
        .options(selectinload(getattr(Lease, "property")))
        .where(
            col(Lease.tenant_id) == tenant_id,
            col(Lease.status) == LeaseStatus.ACTIVE,
        )
    )


async def _get_lease_by_id(lease_id: int, session: AsyncSession) -> Lease | None:
    """Get lease by ID with property loaded."""
    return await session.scalar(
        select(Lease)
        .options(selectinload(getattr(Lease, "property")))
        .where(col(Lease.id) == lease_id)
    )


async def _landlord_accepts_online_payments(
    landlord_user_id: str,
    session: AsyncSession,
) -> bool:
    """Check if landlord has completed Connect onboarding."""
    account = await get_connected_account_for_landlord(landlord_user_id, session)
    return account is not None and account.is_fully_onboarded


async def _unset_default_payment_method(tenant_id: int, session: AsyncSession) -> None:
    """Unset default flag on all payment methods for a tenant."""
    result = await session.execute(
        select(TenantPaymentMethod).where(
            col(TenantPaymentMethod.tenant_id) == tenant_id,
            col(TenantPaymentMethod.is_default) == True,  # noqa: E712
        )
    )
    for pm in result.scalars():
        pm.is_default = False
        pm.updated_at = utc_now()
        session.add(pm)


def _build_payment_method_response(pm: TenantPaymentMethod) -> PaymentMethodResponse:
    """Build PaymentMethodResponse from model."""
    return PaymentMethodResponse(
        id=pm.id,  # type: ignore[arg-type]
        payment_method_type=pm.payment_method_type,
        last_four=pm.last_four,
        bank_name=pm.bank_name,
        institution_number=pm.institution_number,
        brand=pm.brand,
        exp_month=pm.exp_month,
        exp_year=pm.exp_year,
        is_default=pm.is_default,
        is_verified=pm.is_verified,
        is_usable=pm.is_usable,
        display_name=pm.display_name,
        created_at=pm.created_at,
    )


def _build_transaction_response(t: RentPaymentTransaction) -> TransactionResponse:
    """Build TransactionResponse from model."""
    # Get display status
    status_display = {
        RentPaymentTransactionStatus.PENDING: "Pending",
        RentPaymentTransactionStatus.REQUIRES_ACTION: "Action Required",
        RentPaymentTransactionStatus.PROCESSING: "Processing",
        RentPaymentTransactionStatus.SUCCEEDED: "Paid",
        RentPaymentTransactionStatus.FAILED: "Failed",
        RentPaymentTransactionStatus.CANCELED: "Canceled",
        RentPaymentTransactionStatus.REFUNDED: "Refunded",
    }.get(t.status, t.status.title())
    
    return TransactionResponse(
        id=t.id,
        lease_id=t.lease_id,
        tenant_id=t.tenant_id,
        stripe_payment_intent_id=t.stripe_payment_intent_id,
        stripe_charge_id=t.stripe_charge_id,
        receipt_url=t.receipt_url,
        amount_cents=t.amount_cents,
        amount=t.amount_dollars,
        application_fee_cents=t.application_fee_cents,
        application_fee=t.application_fee_dollars,
        currency=t.currency,
        status=t.status,
        failure_code=t.failure_code,
        failure_message=t.failure_message,
        payment_method_type=t.payment_method_type,
        payment_method_last_four=t.payment_method_last_four,
        payment_method_bank_name=t.payment_method_bank_name,
        display_status=status_display,
        initiated_at=t.initiated_at,
        succeeded_at=t.succeeded_at,
        failed_at=t.failed_at,
        created_at=t.created_at,
        property_name=t.lease.property.name if t.lease and t.lease.property else None,
        landlord_name=None,  # TODO: Add landlord name
    )




# =============================================================================
# Accounting Ledger Integration
# =============================================================================

async def create_payment_ledger_entry(
    transaction: RentPaymentTransaction,
    session: AsyncSession,
) -> Payment:
    """
    Create a Payment record in the main accounting ledger for a successful transaction.
    
    This integrates online rent payments into the landlord's unified payment ledger,
    allowing them to see Stripe payments alongside manual entries and QuickBooks sync.
    
    Args:
        transaction: The successful RentPaymentTransaction
        session: Database session
        
    Returns:
        The created Payment record
        
    Raises:
        HTTPException: If transaction is not successful or payment already exists
    """
    # Validate transaction is successful
    if not transaction.is_successful:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create ledger entry for non-successful transaction (status: {transaction.status})",
        )
    
    # Check if ledger entry already exists
    if transaction.payment_id is not None:
        logger.warning(
            f"Ledger entry already exists for transaction {transaction.id} | "
            f"payment_id={transaction.payment_id}"
        )
        existing_payment = await session.get(Payment, transaction.payment_id)
        if existing_payment:
            return existing_payment
    
    # Check for duplicate by stripe_payment_intent_id
    existing = await session.scalar(
        select(Payment).where(
            col(Payment.stripe_payment_intent_id) == transaction.stripe_payment_intent_id
        )
    )
    if existing:
        logger.warning(
            f"Payment ledger entry already exists for PaymentIntent {transaction.stripe_payment_intent_id}"
        )
        # Link it to the transaction if not already linked
        if transaction.payment_id != existing.id:
            transaction.payment_id = existing.id
            transaction.updated_at = utc_now()
            session.add(transaction)
        await session.commit()
        return existing

    # Enforce succeeded_at timestamp for successful transactions
    if not transaction.succeeded_at:
        logger.error(
            f"Cannot create ledger entry for transaction {transaction.id}: "
            f"is_successful is True but succeeded_at is None."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inconsistent transaction state: missing success timestamp."
        )

    # Map payment method type to accounting enum
    payment_method_map: dict[str, PaymentMethodEnum] = {
        PaymentMethodType.ACSS_DEBIT.value: PaymentMethodEnum.BANK_TRANSFER,
        PaymentMethodType.CARD.value: PaymentMethodEnum.CREDIT_CARD,
    }
    payment_method = payment_method_map.get(
        transaction.payment_method_type or "",  
        PaymentMethodEnum.OTHER
    )
    
    # Create payment record
    payment = Payment(
        amount=transaction.amount_dollars,
        payment_date=transaction.succeeded_at,
        status=PaymentStatus.PAID,  # Transaction is successful, so payment is paid
        payment_method=payment_method,
        description=f"Online rent payment - {transaction.payment_method_type or 'Stripe'}",
        transaction_reference=transaction.stripe_charge_id or transaction.stripe_payment_intent_id,
        receipt_url=transaction.receipt_url,
        lease_id=transaction.lease_id,
        tenant_id=transaction.tenant_id,
        user_id=transaction.landlord_user_id,
        stripe_payment_intent_id=transaction.stripe_payment_intent_id,
        created_at=transaction.succeeded_at,
        updated_at=utc_now(),
    )
    
    session.add(payment)
    await session.flush()  # Get the payment ID
    
    # Link payment back to transaction
    transaction.payment_id = payment.id
    transaction.updated_at = utc_now()
    session.add(transaction)
    
    await session.commit()
    await session.refresh(payment)
    
    logger.info(
        f"Created payment ledger entry | "
        f"payment_id={payment.id} | "
        f"transaction_id={transaction.id} | "
        f"amount=${transaction.amount_dollars} | "
        f"tenant_id={transaction.tenant_id}"
    )
    
    return payment
