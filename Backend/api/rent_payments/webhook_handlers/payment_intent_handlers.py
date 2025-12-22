"""Payment Intent webhook event handlers"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from Backend.models.rent_payment_transaction import (
    RentPaymentTransaction,
    RentPaymentTransactionStatus,
)
from Backend.models.tenant import Tenant
from Backend.utils.datetime_utils import utc_now
from .helpers import get_transaction_by_pi_id, create_ledger_payment

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


async def _send_tenant_payment_notification(
    transaction: RentPaymentTransaction,
    session: AsyncSession,
) -> None:
    """
    Send payment confirmation notification to tenant.

    Notifies the tenant that their rent payment was successfully processed.
    Respects user notification preferences for in-app and email delivery.
    """
    try:
        # Get tenant to find their user_id
        tenant = await session.get(Tenant, transaction.tenant_id)
        if not tenant or not tenant.user_id:
            logger.warning(
                f"Cannot send tenant payment notification - tenant or user_id not found | "
                f"tenant_id={transaction.tenant_id}"
            )
            return

        from Backend.api.notifications.service import NotificationService

        # Format amount for display
        amount_display = f"${transaction.amount_cents / 100:,.2f}"

        # Build payment method description
        payment_method_desc = ""
        if transaction.payment_method_type == "card":
            payment_method_desc = f"card ending in {transaction.payment_method_last_four}" if transaction.payment_method_last_four else "card"
        elif transaction.payment_method_type == "acss_debit":
            if transaction.payment_method_bank_name and transaction.payment_method_last_four:
                payment_method_desc = f"{transaction.payment_method_bank_name} account ending in {transaction.payment_method_last_four}"
            elif transaction.payment_method_last_four:
                payment_method_desc = f"bank account ending in {transaction.payment_method_last_four}"
            else:
                payment_method_desc = "bank account"

        message = f"Your rent payment of {amount_display} has been successfully processed"
        if payment_method_desc:
            message += f" via {payment_method_desc}"
        message += "."

        await NotificationService.create_notification(
            user_id=tenant.user_id,
            type="payment_received",
            title="Payment Confirmed",
            message=message,
            session=session,
            link="/payments",
            priority="normal",
            metadata={
                "transaction_id": str(transaction.id),
                "lease_id": str(transaction.lease_id),
                "amount_cents": str(transaction.amount_cents),
                "payment_method_type": transaction.payment_method_type,
                "receipt_url": transaction.receipt_url,
            },
        )

        logger.info(
            f"Sent tenant payment_received notification | "
            f"tenant_id={transaction.tenant_id} | "
            f"user_id={tenant.user_id} | "
            f"amount={amount_display}"
        )

    except Exception as e:
        # Don't fail the webhook if notification fails
        logger.error(
            f"Failed to send tenant payment notification for transaction {transaction.id}: {e}",
            exc_info=True,
        )


async def _send_landlord_payment_notification(
    transaction: RentPaymentTransaction,
    session: AsyncSession,
) -> None:
    """
    Send payment received notification to landlord.

    Notifies the landlord that a tenant has submitted a rent payment.
    Respects user notification preferences for in-app and email delivery.
    """
    try:
        if not transaction.landlord_user_id:
            logger.warning(
                f"Cannot send landlord payment notification - landlord_user_id not found | "
                f"transaction_id={transaction.id}"
            )
            return

        # Get tenant name for the notification message
        tenant = await session.get(Tenant, transaction.tenant_id)
        tenant_name = "A tenant"
        if tenant:
            if tenant.first_name and tenant.last_name:
                tenant_name = f"{tenant.first_name} {tenant.last_name}"
            elif tenant.first_name:
                tenant_name = tenant.first_name

        from Backend.api.notifications.service import NotificationService

        # Format amount for display
        amount_display = f"${transaction.amount_cents / 100:,.2f}"

        # Build payment method description
        payment_method_desc = ""
        if transaction.payment_method_type == "card":
            payment_method_desc = "card"
        elif transaction.payment_method_type == "acss_debit":
            payment_method_desc = "bank transfer"

        message = f"{tenant_name} has submitted a rent payment of {amount_display}"
        if payment_method_desc:
            message += f" via {payment_method_desc}"
        message += "."

        await NotificationService.create_notification(
            user_id=transaction.landlord_user_id,
            type="payment_received",
            title="Payment Received",
            message=message,
            session=session,
            link="/accounting/payments",
            priority="normal",
            metadata={
                "transaction_id": str(transaction.id),
                "lease_id": str(transaction.lease_id),
                "tenant_id": str(transaction.tenant_id),
                "amount_cents": str(transaction.amount_cents),
                "payment_method_type": transaction.payment_method_type,
            },
        )

        logger.info(
            f"Sent landlord payment_received notification | "
            f"landlord_user_id={transaction.landlord_user_id} | "
            f"tenant_id={transaction.tenant_id} | "
            f"amount={amount_display}"
        )

    except Exception as e:
        # Don't fail the webhook if notification fails
        logger.error(
            f"Failed to send landlord payment notification for transaction {transaction.id}: {e}",
            exc_info=True,
        )


# =============================================================================
# Webhook Handlers
# =============================================================================


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

    # Send payment notifications to tenant and landlord
    await _send_tenant_payment_notification(transaction, session)
    await _send_landlord_payment_notification(transaction, session)


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

