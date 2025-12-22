"""Payment Intent webhook event handlers"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from Backend.models.rent_payment_transaction import (
    RentPaymentTransaction,
    RentPaymentTransactionStatus,
)
from Backend.utils.datetime_utils import utc_now
from .helpers import get_transaction_by_pi_id, create_ledger_payment

logger = logging.getLogger(__name__)


async def handle_payment_intent_succeeded(
    payment_intent: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle successful payment."""
    pi_id = payment_intent.get("id")
    if not pi_id:
        logger.warning("PaymentIntent missing ID")
        return
    
    transaction = await get_transaction_by_pi_id(pi_id, session)
    if not transaction:
        logger.warning(f"No transaction found for PaymentIntent {pi_id}")
        return
    
    # Update transaction status
    transaction.status = RentPaymentTransactionStatus.SUCCEEDED
    transaction.succeeded_at = utc_now()
    transaction.updated_at = utc_now()

    # NOTE: payment_method_details is NOT on PaymentIntent - it's on the Charge object.
    # The charge.succeeded webhook handler extracts last4/bank_name from charge.payment_method_details.
    # We don't extract payment method details here as they won't be available.
    session.add(transaction)
    
    # Create corresponding Payment record for landlord's ledger
    await create_ledger_payment(transaction, session)
    
    await session.commit()
    
    logger.info(
        f"Payment succeeded | "
        f"transaction_id={transaction.id} | "
        f"pi_id={pi_id} | "
        f"amount=${transaction.amount_cents / 100:.2f}"
    )


async def handle_payment_intent_failed(
    payment_intent: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle failed payment."""
    pi_id = payment_intent.get("id")
    if not pi_id:
        return
    
    transaction = await get_transaction_by_pi_id(pi_id, session)
    if not transaction:
        logger.warning(f"No transaction found for PaymentIntent {pi_id}")
        return
    
    # Get error details
    last_error = payment_intent.get("last_payment_error", {})
    
    transaction.status = RentPaymentTransactionStatus.FAILED
    transaction.failed_at = utc_now()
    transaction.failure_code = last_error.get("code")
    transaction.failure_message = last_error.get("message")
    transaction.updated_at = utc_now()
    
    session.add(transaction)
    await session.commit()
    
    logger.info(
        f"Payment failed | "
        f"transaction_id={transaction.id} | "
        f"pi_id={pi_id} | "
        f"code={transaction.failure_code}"
    )


async def handle_payment_intent_canceled(
    payment_intent: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle canceled payment."""
    pi_id = payment_intent.get("id")
    if not pi_id:
        return
    
    transaction = await get_transaction_by_pi_id(pi_id, session)
    if not transaction:
        return
    
    transaction.status = RentPaymentTransactionStatus.CANCELED
    transaction.updated_at = utc_now()
    
    session.add(transaction)
    await session.commit()
    
    logger.info(f"Payment canceled | transaction_id={transaction.id} | pi_id={pi_id}")


async def handle_payment_intent_processing(
    payment_intent: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle payment in processing state (common for bank transfers)."""
    pi_id = payment_intent.get("id")
    if not pi_id:
        return
    
    transaction = await get_transaction_by_pi_id(pi_id, session)
    if not transaction:
        return
    
    transaction.status = RentPaymentTransactionStatus.PROCESSING
    transaction.authorized_at = utc_now()
    transaction.updated_at = utc_now()
    
    session.add(transaction)
    await session.commit()
    
    logger.info(f"Payment processing | transaction_id={transaction.id} | pi_id={pi_id}")


async def handle_payment_intent_requires_action(
    payment_intent: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle payment requiring additional action (3DS, etc.)."""
    pi_id = payment_intent.get("id")
    if not pi_id:
        return
    
    transaction = await get_transaction_by_pi_id(pi_id, session)
    if not transaction:
        return
    
    transaction.status = RentPaymentTransactionStatus.REQUIRES_ACTION
    transaction.updated_at = utc_now()
    
    session.add(transaction)
    await session.commit()
    
    logger.info(f"Payment requires action | transaction_id={transaction.id} | pi_id={pi_id}")


async def handle_payment_intent_amount_capturable_updated(
    payment_intent: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle partial authorization updates."""
    pi_id = payment_intent.get("id")
    if not pi_id:
        return
    
    transaction = await get_transaction_by_pi_id(pi_id, session)
    if not transaction:
        return
    
    # Log the capturable amount for monitoring
    amount_capturable = payment_intent.get("amount_capturable", 0)
    logger.info(
        f"Payment amount capturable updated | "
        f"transaction_id={transaction.id} | "
        f"pi_id={pi_id} | "
        f"capturable=${amount_capturable / 100:.2f}"
    )
    
    # Note: We don't change transaction status here, just log for visibility


async def handle_payment_intent_partially_funded(
    payment_intent: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle partially funded payments (common for ACSS debit installments)."""
    pi_id = payment_intent.get("id")
    if not pi_id:
        return
    
    transaction = await get_transaction_by_pi_id(pi_id, session)
    if not transaction:
        return
    
    amount_received = payment_intent.get("amount_received", 0)
    amount_total = payment_intent.get("amount", 0)
    
    logger.info(
        f"Payment partially funded | "
        f"transaction_id={transaction.id} | "
        f"pi_id={pi_id} | "
        f"received=${amount_received / 100:.2f} / ${amount_total / 100:.2f}"
    )
    
    # Keep status as processing until fully funded
    if transaction.status == RentPaymentTransactionStatus.PENDING:
        transaction.status = RentPaymentTransactionStatus.PROCESSING
        transaction.updated_at = utc_now()
        session.add(transaction)
        await session.commit()

