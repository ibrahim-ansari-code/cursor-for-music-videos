"""Charge webhook event handlers"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from Backend.models.rent_payment_transaction import (
    RentPaymentTransaction,
    RentPaymentTransactionStatus,
)
from Backend.models.accounting.payment import Payment
from Backend.models.accounting.common import PaymentStatus
from Backend.utils.datetime_utils import utc_now
from .helpers import get_transaction_by_pi_id

logger = logging.getLogger(__name__)


async def handle_charge_succeeded(
    charge: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle successful charge - store charge ID for receipt lookup."""
    charge_id = charge.get("id")
    payment_intent_id = charge.get("payment_intent")
    
    if not payment_intent_id:
        return
    
    # Find transaction by PaymentIntent ID
    transaction = await get_transaction_by_pi_id(payment_intent_id, session)
    if not transaction:
        return
    
    # Store charge ID so charge.updated can find this transaction
    transaction.stripe_charge_id = charge_id
    transaction.updated_at = utc_now()
    
    session.add(transaction)
    await session.commit()
    
    logger.info(
        f"Stored charge ID | "
        f"transaction_id={transaction.id} | "
        f"charge_id={charge_id}"
    )


async def handle_charge_failed(
    charge: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle failed charge (distinct from payment_intent.payment_failed)."""
    charge_id = charge.get("id")
    payment_intent_id = charge.get("payment_intent")
    
    if not payment_intent_id:
        return
    
    transaction = await get_transaction_by_pi_id(payment_intent_id, session)
    if not transaction:
        logger.warning(f"No transaction found for failed charge {charge_id}")
        return
    
    # Get failure details
    failure_code = charge.get("failure_code")
    failure_message = charge.get("failure_message")
    
    transaction.status = RentPaymentTransactionStatus.FAILED
    transaction.failed_at = utc_now()
    transaction.failure_code = failure_code
    transaction.failure_message = failure_message
    transaction.stripe_charge_id = charge_id
    transaction.updated_at = utc_now()
    
    session.add(transaction)
    await session.commit()
    
    logger.warning(
        f"Charge failed | "
        f"transaction_id={transaction.id} | "
        f"charge_id={charge_id} | "
        f"code={failure_code}"
    )


async def handle_charge_pending(
    charge: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle pending charge (common for bank transfers)."""
    charge_id = charge.get("id")
    payment_intent_id = charge.get("payment_intent")
    
    if not payment_intent_id:
        return
    
    transaction = await get_transaction_by_pi_id(payment_intent_id, session)
    if not transaction:
        return
    
    # Store charge ID and update to processing if not already
    transaction.stripe_charge_id = charge_id
    if transaction.status == RentPaymentTransactionStatus.PENDING:
        transaction.status = RentPaymentTransactionStatus.PROCESSING
    transaction.updated_at = utc_now()
    
    session.add(transaction)
    await session.commit()
    
    logger.info(f"Charge pending | transaction_id={transaction.id} | charge_id={charge_id}")


async def handle_charge_expired(
    charge: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle expired charge authorization."""
    charge_id = charge.get("id")
    payment_intent_id = charge.get("payment_intent")
    
    if not payment_intent_id:
        return
    
    transaction = await get_transaction_by_pi_id(payment_intent_id, session)
    if not transaction:
        return
    
    # Mark as failed due to expiration
    transaction.status = RentPaymentTransactionStatus.FAILED
    transaction.failed_at = utc_now()
    transaction.failure_code = "charge_expired"
    transaction.failure_message = "Payment authorization expired"
    transaction.stripe_charge_id = charge_id
    transaction.updated_at = utc_now()
    
    session.add(transaction)
    await session.commit()
    
    logger.warning(
        f"Charge expired | "
        f"transaction_id={transaction.id} | "
        f"charge_id={charge_id}"
    )


async def handle_charge_refunded(
    charge: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle refunded charge."""
    charge_id = charge.get("id")
    
    # Find transaction by charge ID
    transaction = await session.scalar(
        select(RentPaymentTransaction).where(
        col(RentPaymentTransaction.stripe_charge_id) == charge_id
    )
    )
    
    if not transaction:
        logger.warning(f"No transaction found for charge {charge_id}")
        return
    
    # Check if fully refunded
    amount_refunded = charge.get("amount_refunded", 0)
    if amount_refunded >= transaction.amount_cents:
        transaction.status = RentPaymentTransactionStatus.REFUNDED
        transaction.refunded_at = utc_now()
    
    transaction.updated_at = utc_now()
    
    session.add(transaction)
    
    # Update ledger payment if exists
    if transaction.payment_id:
        payment = await session.get(Payment, transaction.payment_id)
        if payment:
            payment.status = PaymentStatus.REFUNDED
            payment.updated_at = utc_now()
            session.add(payment)
    
    await session.commit()
    
    logger.info(
        f"Payment refunded | "
        f"transaction_id={transaction.id} | "
        f"charge_id={charge_id}"
    )


async def handle_charge_updated(
    charge: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle updated charge to capture receipt URL."""
    charge_id = charge.get("id")
    receipt_url = charge.get("receipt_url")
    
    if not charge_id or not receipt_url:
        return
    
    # Find transaction by charge ID
    transaction = await session.scalar(
        select(RentPaymentTransaction).where(
            col(RentPaymentTransaction.stripe_charge_id) == charge_id
        )
    )
    
    if not transaction or transaction.receipt_url:
        return
    
    # Update receipt_url on transaction
    transaction.receipt_url = receipt_url
    transaction.updated_at = utc_now()
    session.add(transaction)
    
    # Also update the ledger payment if it exists
    if transaction.payment_id:
        payment = await session.get(Payment, transaction.payment_id)
        if payment and not payment.receipt_url:
            payment.receipt_url = receipt_url
            payment.updated_at = utc_now()
            session.add(payment)
    
    await session.commit()
    
    logger.info(
        f"Updated receipt URL | "
        f"transaction_id={transaction.id} | "
        f"charge_id={charge_id}"
    )

