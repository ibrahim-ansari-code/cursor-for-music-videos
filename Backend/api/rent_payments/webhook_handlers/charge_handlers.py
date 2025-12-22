"""Charge webhook event handlers"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from Backend.models.rent_payment_transaction import (
    RentPaymentTransaction,
    RentPaymentTransactionStatus,
)
from Backend.models.accounting.payment import Payment, PaymentMethod as PaymentMethodEnum
from Backend.models.accounting.common import PaymentStatus
from Backend.api.rent_payments.constants import PaymentMethodType
from Backend.utils.datetime_utils import utc_now
from .helpers import get_transaction_by_pi_id

logger = logging.getLogger(__name__)


# Map Stripe payment method types to our PaymentMethod enum
STRIPE_TO_PAYMENT_METHOD: dict[str, PaymentMethodEnum] = {
    PaymentMethodType.CARD.value: PaymentMethodEnum.CREDIT_CARD,
    PaymentMethodType.ACSS_DEBIT.value: PaymentMethodEnum.BANK_TRANSFER,
    "ach_debit": PaymentMethodEnum.BANK_TRANSFER,
    "us_bank_account": PaymentMethodEnum.BANK_TRANSFER,
}


async def handle_charge_succeeded(
    charge: dict[str, Any],
    session: AsyncSession,
) -> None:
    """
    Handle successful charge - store charge ID and payment method details.

    The Charge object contains payment_method_details which has the actual
    payment method type (card, acss_debit, etc.) that we need to display correctly.
    """
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

    # Extract payment method details from the Charge object
    # Structure: charge.payment_method_details.type = "card" | "acss_debit" | etc.
    # This is the ONLY place where last4 is available - NOT on PaymentIntent
    pm_details = charge.get("payment_method_details") or {}
    pm_type = pm_details.get("type")  # e.g., "card", "acss_debit"

    if pm_type:
        transaction.payment_method_type = pm_type

        # Extract additional details based on payment method type
        type_details = pm_details.get(pm_type) or {}

        if pm_type == "card":
            last4 = type_details.get("last4")
            if last4:
                transaction.payment_method_last_four = last4
            else:
                logger.warning(
                    f"Card payment missing last4 | "
                    f"charge_id={charge_id} | "
                    f"type_details_keys={list(type_details.keys())}"
                )
        elif pm_type == "acss_debit":
            last4 = type_details.get("last4")
            bank_name = type_details.get("bank_name")
            if last4:
                transaction.payment_method_last_four = last4
            else:
                logger.warning(
                    f"ACSS debit payment missing last4 | "
                    f"charge_id={charge_id}"
                )
            if bank_name:
                transaction.payment_method_bank_name = bank_name

        logger.info(
            f"Extracted payment method | "
            f"transaction_id={transaction.id} | "
            f"type={pm_type} | "
            f"last4={transaction.payment_method_last_four or 'NOT_FOUND'}"
        )
    else:
        logger.warning(
            f"Charge missing payment_method_details.type | "
            f"charge_id={charge_id} | "
            f"pm_details_keys={list(pm_details.keys()) if pm_details else 'EMPTY'}"
        )

    # Update the linked ledger payment's payment_method if it exists
    if pm_type and transaction.payment_id:
        payment = await session.get(Payment, transaction.payment_id)
        if payment:
            new_payment_method = STRIPE_TO_PAYMENT_METHOD.get(pm_type, PaymentMethodEnum.OTHER)
            if payment.payment_method != new_payment_method:
                payment.payment_method = new_payment_method
                payment.updated_at = utc_now()
                session.add(payment)
                logger.info(
                    f"Updated ledger payment method | "
                    f"payment_id={payment.id} | "
                    f"method={new_payment_method.value}"
                )

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

    # Determine refund status based on amount
    amount_refunded = charge.get("amount_refunded", 0)
    is_full_refund = amount_refunded >= transaction.amount_cents

    if is_full_refund:
        transaction.status = RentPaymentTransactionStatus.REFUNDED
        transaction.refunded_at = utc_now()
    elif amount_refunded > 0:
        transaction.status = RentPaymentTransactionStatus.PARTIALLY_REFUNDED

    transaction.updated_at = utc_now()
    session.add(transaction)

    # Update ledger payment if exists - match the refund status
    if transaction.payment_id:
        payment = await session.get(Payment, transaction.payment_id)
        if payment:
            if is_full_refund:
                payment.status = PaymentStatus.REFUNDED
            elif amount_refunded > 0:
                payment.status = PaymentStatus.PARTIALLY_REFUNDED
            payment.updated_at = utc_now()
            session.add(payment)

    await session.commit()

    logger.info(
        f"Payment refunded | "
        f"transaction_id={transaction.id} | "
        f"charge_id={charge_id} | "
        f"amount_refunded={amount_refunded} | "
        f"is_full_refund={is_full_refund}"
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

