"""Shared helper functions for webhook handlers"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from sqlmodel import col, select

from Backend.models.rent_payment_transaction import RentPaymentTransaction
from Backend.models.accounting.payment import Payment, PaymentMethod as PaymentMethodEnum
from Backend.models.accounting.common import PaymentStatus
from Backend.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


async def get_transaction_by_pi_id(
    pi_id: str,
    session: AsyncSession,
) -> RentPaymentTransaction | None:
    """Get transaction by PaymentIntent ID."""
    return await session.scalar(
        select(RentPaymentTransaction).where(
            col(RentPaymentTransaction.stripe_payment_intent_id) == pi_id
        )
    )


async def create_ledger_payment(
    transaction: RentPaymentTransaction,
    session: AsyncSession,
) -> None:
    """
    Create a Payment record in the landlord's accounting ledger (idempotent).
    
    This integrates online rent payments into the main accounting system,
    making them visible in PaymentsTab alongside manual entries and QuickBooks sync.
    
    Handles race conditions when multiple webhooks arrive simultaneously.
    """
    try:
        # First, try to find existing payment using SELECT FOR UPDATE to lock the row
        # This prevents duplicate creation when multiple webhooks arrive at once
        existing = await session.scalar(
            select(Payment).where(
                or_(
                    col(Payment.id) == transaction.payment_id,
                    col(Payment.stripe_payment_intent_id) == transaction.stripe_payment_intent_id
                )
            ).with_for_update(skip_locked=False)  # Wait for lock, don't skip
        )
        
        if existing:
            # Payment already exists - ensure transaction is linked
            if transaction.payment_id != existing.id:
                logger.info(
                    f"Linking existing payment to transaction | "
                    f"payment_id={existing.id} | "
                    f"transaction_id={transaction.id}"
                )
                transaction.payment_id = existing.id
                transaction.updated_at = utc_now()
                session.add(transaction)
                await session.commit()
            return
        
        # No existing payment found - create new one
        # Map payment method type to accounting enum
        from Backend.api.rent_payments.constants import PaymentMethodType
        
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
            payment_date=transaction.succeeded_at or transaction.created_at,
            status=PaymentStatus.PAID,
            payment_method=payment_method,
            description=f"Online rent payment - {transaction.payment_method_type or 'Stripe'}",
            transaction_reference=transaction.stripe_charge_id or transaction.stripe_payment_intent_id,
            receipt_url=transaction.receipt_url,
            lease_id=transaction.lease_id,
            tenant_id=transaction.tenant_id,
            user_id=transaction.landlord_user_id,
            stripe_payment_intent_id=transaction.stripe_payment_intent_id,
            created_at=transaction.succeeded_at or utc_now(),
            updated_at=utc_now(),
        )
        
        session.add(payment)
        
        try:
            await session.flush()  # Get the payment ID
            
            # Link payment back to transaction
            transaction.payment_id = payment.id
            transaction.updated_at = utc_now()
            session.add(transaction)
            
            await session.commit()
            
            logger.info(
                f"✅ Created payment ledger entry | "
                f"payment_id={payment.id} | "
                f"transaction_id={transaction.id} | "
                f"amount=${transaction.amount_dollars} | "
                f"tenant_id={transaction.tenant_id}"
            )
            
        except IntegrityError as ie:
            # Race condition: Another webhook created the payment between our check and insert
            await session.rollback()
            
            logger.warning(
                f"⚠️ Race condition detected during ledger creation for transaction {transaction.id}, "
                f"fetching winner..."
            )
            
            # Fetch the payment that won the race
            winner = await session.scalar(
                select(Payment).where(
                    col(Payment.stripe_payment_intent_id) == transaction.stripe_payment_intent_id
                )
            )
            
            if winner:
                # Link to the winner
                transaction.payment_id = winner.id
                transaction.updated_at = utc_now()
                session.add(transaction)
                await session.commit()
                
                logger.info(
                    f"✅ Linked to existing payment (race resolved) | "
                    f"payment_id={winner.id} | "
                    f"transaction_id={transaction.id}"
                )
            else:
                # Unexpected: IntegrityError but can't find the conflicting payment
                logger.error(
                    f"❌ IntegrityError but no conflicting payment found for "
                    f"transaction {transaction.id} | "
                    f"pi_id={transaction.stripe_payment_intent_id}"
                )
                raise ie
    
    except Exception as e:
        logger.error(
            f"Unexpected error creating ledger entry for transaction {transaction.id}: {e}",
            exc_info=True,
        )

