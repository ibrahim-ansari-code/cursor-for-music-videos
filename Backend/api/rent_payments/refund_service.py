"""
Refund Service for Rent Payments

Handles refund and dispute processing for rent payment transactions.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select
import stripe
import sentry_sdk

from Backend.api.stripe.client import get_stripe_client
from Backend.models.accounting.payment import Payment
from Backend.models.accounting.common import PaymentStatus
from Backend.models.rent_payment_transaction import RentPaymentTransaction, RentPaymentTransactionStatus
from Backend.models.rent_payment_refund import RentPaymentRefund, RefundStatus, RefundReason
from Backend.models.rent_payment_dispute import RentPaymentDispute, DisputeStatus
from Backend.models.user import User
from Backend.utils.datetime_utils import utc_now

from .schemas import (
    RefundCreateRequest,
    RefundResponse,
    RefundListResponse,
    DisputeResponse,
    DisputeListResponse,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Refund Operations
# =============================================================================

async def create_refund(
    user: User,
    data: RefundCreateRequest,
    session: AsyncSession,
) -> RefundResponse:
    """
    Issue a refund for a rent payment transaction.
    
    Only landlords can issue refunds for transactions on their properties.
    Refunds can be partial or full.
    
    Args:
        user: The landlord user issuing the refund
        data: Refund request details
        session: Database session
        
    Returns:
        RefundResponse with refund details
    """
    # Validate transaction_id is set (should always be set by router)
    if not data.transaction_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction ID is required"
        )
    
    # Load transaction with relationships
    transaction = await session.scalar(
        select(RentPaymentTransaction)
        .where(col(RentPaymentTransaction.id) == data.transaction_id)
        .options(
            selectinload(getattr(RentPaymentTransaction, "lease")),
            selectinload(getattr(RentPaymentTransaction, "refunds")),
        )
    )
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Verify landlord owns this transaction
    if transaction.landlord_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only refund transactions for your properties"
        )
    
    # Verify transaction is in a refundable state
    if transaction.status != RentPaymentTransactionStatus.SUCCEEDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot refund transaction with status: {transaction.status}"
        )
    
    if not transaction.stripe_charge_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction has no charge ID - cannot refund"
        )
    
    # Calculate available refund amount, including pending refunds
    total_refunded = sum(
        r.amount_cents for r in transaction.refunds if r.status != RefundStatus.FAILED
    )
    max_refundable = transaction.amount_cents - total_refunded
    
    if data.amount_cents > max_refundable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund amount (${data.amount_cents/100:.2f}) exceeds available amount (${max_refundable/100:.2f})"
        )
    
    # Get the connected account (landlord's Stripe account)
    from Backend.models.stripe_connected_account import StripeConnectedAccount
    
    connected_account = await session.scalar(
        select(StripeConnectedAccount).where(
            col(StripeConnectedAccount.user_id) == transaction.landlord_user_id
        )
    )
    
    if not connected_account or not connected_account.stripe_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Landlord's Stripe account not found - cannot process refund"
        )
    
    # Create local refund record first to generate a stable idempotency key
    refund = RentPaymentRefund(
        transaction_id=transaction.id,
        stripe_refund_id=None,  # Will be set after Stripe call
        stripe_charge_id=transaction.stripe_charge_id,
        amount_cents=data.amount_cents,
        currency=transaction.currency,
        reason=data.reason,
        notes=data.notes,
        status=RefundStatus.PENDING,
        application_fee_refunded_cents=None,  # Platform fee is non-refundable
        initiated_by_user_id=user.id,
    )

    session.add(refund)
    await session.flush()  # Assigns UUID without committing

    # Create refund via Stripe (on the connected account)
    try:
        stripe_client = get_stripe_client()

        # Use refund UUID as idempotency key - stable across all retries
        idempotency_key = str(refund.id)

        refund_params = {
            "charge": transaction.stripe_charge_id,
            "amount": data.amount_cents,
            "reason": data.reason if data.reason in {"duplicate", "fraudulent", "requested_by_customer"} else None,
            "metadata": {
                "transaction_id": str(transaction.id),
                "tenant_id": str(transaction.tenant_id),
                "lease_id": str(transaction.lease_id),
                "initiated_by": str(user.id),
                "refund_id": str(refund.id),
                "platform": "brikli",
            },
        }

        # Platform fee is non-refundable (covers payment processing costs)
        # The refund_application_fee parameter is kept for API compatibility but always ignored
        # Brikli's flat fee ($3-$8) is not refunded as it covers services already rendered

        # CRITICAL: Pass stripe_account as a separate parameter (not in params dict)
        stripe_refund = await stripe_client.refunds.create(
            **refund_params,
            stripe_account=connected_account.stripe_account_id,
            idempotency_key=idempotency_key,
        )

        # Update refund record with Stripe details
        refund.stripe_refund_id = stripe_refund.id
        await session.commit()

    except stripe.InvalidRequestError as e:
        logger.error(f"Stripe refund failed | error={e}")

        # Mark refund as failed in database
        refund.status = RefundStatus.FAILED
        refund.failure_reason = str(e)
        refund.failed_at = utc_now()
        await session.commit()

        # Track in Sentry for monitoring
        sentry_sdk.capture_exception(
            e,
            tags={
                "component": "refund_processing",
                "failure_type": "invalid_request",
                "transaction_id": str(transaction.id),
                "landlord_id": str(user.id),
                "refund_id": str(refund.id),
            },
            contexts={
                "refund": {
                    "transaction_id": str(transaction.id),
                    "refund_id": str(refund.id),
                    "refund_amount": data.amount_cents / 100,
                    "original_amount": transaction.amount_dollars,
                    "reason": data.reason,
                }
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund failed: {str(e)}"
        )
    except stripe.StripeError as e:
        logger.error(f"Stripe error during refund | error={e}")

        # Mark refund as failed in database
        refund.status = RefundStatus.FAILED
        refund.failure_reason = str(e)
        refund.failed_at = utc_now()
        await session.commit()

        # Track in Sentry
        sentry_sdk.capture_exception(
            e,
            tags={
                "component": "refund_processing",
                "failure_type": "stripe_error",
                "transaction_id": str(transaction.id),
                "landlord_id": str(user.id),
                "refund_id": str(refund.id),
            },
            contexts={
                "refund": {
                    "transaction_id": str(transaction.id),
                    "refund_id": str(refund.id),
                    "refund_amount": data.amount_cents / 100,
                    "original_amount": transaction.amount_dollars,
                    "reason": data.reason,
                }
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process refund. Please try again."
        )

    await session.refresh(refund)
    
    logger.info(
        f"Refund created | "
        f"refund_id={refund.id} | "
        f"transaction_id={transaction.id} | "
        f"stripe_refund_id={stripe_refund.id} | "
        f"amount=${data.amount_cents/100:.2f} | "
        f"reason={data.reason}"
    )
    
    return await _build_refund_response(refund, session)


async def get_refund(
    user: User,
    refund_id: UUID,
    session: AsyncSession,
) -> RefundResponse:
    """Get refund details."""
    refund = await session.scalar(
        select(RentPaymentRefund)
        .where(col(RentPaymentRefund.id) == refund_id)
        .options(
            selectinload(getattr(RentPaymentRefund, "transaction")),
            selectinload(getattr(RentPaymentRefund, "initiated_by")),
        )
    )
    
    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )
    
    # Verify user has access (landlord who initiated or owns the property)
    if not refund.transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found for refund"
        )
    
    if refund.initiated_by_user_id != user.id and refund.transaction.landlord_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this refund"
        )
    
    return await _build_refund_response(refund, session)


async def list_refunds(
    user: User,
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    transaction_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
) -> RefundListResponse:
    """
    List refunds for the landlord's properties.
    
    Args:
        user: Landlord user
        session: Database session
        limit: Maximum number of refunds to return
        offset: Number of refunds to skip
        transaction_id: Optional filter for specific transaction
        status_filter: Optional filter by status
        
    Returns:
        RefundListResponse with paginated refunds
    """
    # Build query
    query = (
        select(RentPaymentRefund)
        .join(RentPaymentTransaction, col(RentPaymentRefund.transaction_id) == col(RentPaymentTransaction.id))
        .where(col(RentPaymentTransaction.landlord_user_id) == user.id)
        .options(
            selectinload(getattr(RentPaymentRefund, "transaction")),
            selectinload(getattr(RentPaymentRefund, "initiated_by")),
        )
        .order_by(col(RentPaymentRefund.created_at).desc())
    )
    
    # Apply filters
    if transaction_id:
        query = query.where(col(RentPaymentRefund.transaction_id) == transaction_id)
    
    if status_filter:
        # Validate that status_filter is a valid RefundStatus constant
        valid_statuses = {
            RefundStatus.PENDING,
            RefundStatus.PROCESSING,
            RefundStatus.SUCCEEDED,
            RefundStatus.FAILED,
            RefundStatus.CANCELED
        }
        if status_filter not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid refund status filter: {status_filter}"
            )
        query = query.where(col(RentPaymentRefund.status) == status_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0
    
    # Get paginated results
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    refunds = list(result.scalars().all())
    
    # Build responses
    refund_responses = []
    for refund in refunds:
        refund_responses.append(await _build_refund_response(refund, session))
    
    return RefundListResponse(
        items=refund_responses,
        total=total,
        has_more=(offset + len(refunds)) < total,
    )


# =============================================================================
# Dispute Operations
# =============================================================================

async def get_dispute(
    user: User,
    dispute_id: UUID,
    session: AsyncSession,
) -> DisputeResponse:
    """Get dispute details."""
    dispute = await session.scalar(
        select(RentPaymentDispute)
        .where(col(RentPaymentDispute.id) == dispute_id)
        .options(selectinload(getattr(RentPaymentDispute, "transaction")))
    )
    
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found"
        )
    
    # Verify user owns this dispute (landlord)
    if not dispute.transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found for dispute"
        )
    
    if dispute.transaction.landlord_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this dispute"
        )
    
    return _build_dispute_response(dispute)


async def list_disputes(
    user: User,
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    needs_attention_only: bool = False,
) -> DisputeListResponse:
    """
    List disputes for the landlord's properties.
    
    Args:
        user: Landlord user
        session: Database session
        limit: Maximum number of disputes to return
        offset: Number of disputes to skip
        status_filter: Optional filter by status
        needs_attention_only: If True, only return disputes needing action
        
    Returns:
        DisputeListResponse with paginated disputes
    """
    # Build query
    query = (
        select(RentPaymentDispute)
        .join(RentPaymentTransaction, col(RentPaymentDispute.transaction_id) == col(RentPaymentTransaction.id))
        .where(col(RentPaymentTransaction.landlord_user_id) == user.id)
        .options(selectinload(getattr(RentPaymentDispute, "transaction")))
        .order_by(col(RentPaymentDispute.created_at).desc())
    )
    
    # Apply filters
    if status_filter:
        query = query.where(col(RentPaymentDispute.status) == status_filter)
    
    if needs_attention_only:
        query = query.where(
            and_(
                col(RentPaymentDispute.status).in_([
                    DisputeStatus.WARNING_NEEDS_RESPONSE,
                    DisputeStatus.NEEDS_RESPONSE
                ]),
                col(RentPaymentDispute.evidence_submitted) == False
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0
    
    # Get active disputes count
    active_query = (
        select(func.count())
        .select_from(RentPaymentDispute)
        .join(RentPaymentTransaction, col(RentPaymentDispute.transaction_id) == col(RentPaymentTransaction.id))
        .where(
            and_(
                col(RentPaymentTransaction.landlord_user_id) == user.id,
                col(RentPaymentDispute.status).in_([
                    DisputeStatus.WARNING_NEEDS_RESPONSE,
                    DisputeStatus.NEEDS_RESPONSE
                ]),
                col(RentPaymentDispute.evidence_submitted) == False
            )
        )
    )
    active_disputes = await session.scalar(active_query) or 0
    
    # Get paginated results
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    disputes = list(result.scalars().all())
    
    # Build responses
    dispute_responses = [_build_dispute_response(d) for d in disputes]
    
    return DisputeListResponse(
        items=dispute_responses,
        total=total,
        has_more=(offset + len(disputes)) < total,
        active_disputes=active_disputes,
    )


# =============================================================================
# Helper Functions
# =============================================================================

async def _build_refund_response(
    refund: RentPaymentRefund,
    session: AsyncSession,
) -> RefundResponse:
    """Build RefundResponse from model."""
    # Get initiator name
    initiator_name = None
    if refund.initiated_by:
        user = refund.initiated_by
        if user.first_name or user.last_name:
            initiator_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    
    # Calculate application fee refunded in dollars
    app_fee_refunded_dollars = None
    if refund.application_fee_refunded_cents is not None:
        app_fee_refunded_dollars = Decimal(refund.application_fee_refunded_cents) / 100
    
    return RefundResponse(
        id=refund.id,
        transaction_id=refund.transaction_id,
        stripe_refund_id=refund.stripe_refund_id,
        stripe_charge_id=refund.stripe_charge_id,
        amount_cents=refund.amount_cents,
        amount=Decimal(str(refund.amount_dollars)),
        currency=refund.currency,
        application_fee_refunded_cents=refund.application_fee_refunded_cents,
        application_fee_refunded=app_fee_refunded_dollars,
        status=refund.status,
        reason=refund.reason,
        notes=refund.notes,
        failure_reason=refund.failure_reason,
        initiated_by_user_id=refund.initiated_by_user_id,
        initiated_by_name=initiator_name,
        created_at=refund.created_at,
        succeeded_at=refund.succeeded_at,
        failed_at=refund.failed_at,
    )


def _build_dispute_response(dispute: RentPaymentDispute) -> DisputeResponse:
    """Build DisputeResponse from model."""
    # Calculate days until due
    days_until_due = None
    if dispute.evidence_due_by:
        delta = dispute.evidence_due_by - datetime.now(timezone.utc)
        days_until_due = max(0, delta.days)
    
    return DisputeResponse(
        id=dispute.id,
        transaction_id=dispute.transaction_id,
        stripe_dispute_id=dispute.stripe_dispute_id,
        stripe_charge_id=dispute.stripe_charge_id,
        amount_cents=dispute.amount_cents,
        amount=Decimal(str(dispute.amount_cents / 100)),
        currency=dispute.currency,
        status=dispute.status,
        reason=dispute.reason,
        evidence_due_by=dispute.evidence_due_by,
        evidence_submitted=dispute.evidence_submitted,
        evidence_submitted_at=dispute.evidence_submitted_at,
        is_charge_refundable=dispute.is_charge_refundable,
        created_at=dispute.created_at,
        closed_at=dispute.closed_at,
        landlord_notified=dispute.landlord_notified,
        landlord_notified_at=dispute.landlord_notified_at,
        needs_attention=dispute.needs_attention,
        days_until_due=days_until_due,
    )

