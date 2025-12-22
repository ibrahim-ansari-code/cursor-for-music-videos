"""Refund webhook event handlers and notifications"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from Backend.models.rent_payment_transaction import (
    RentPaymentTransaction,
    RentPaymentTransactionStatus,
)
from Backend.models.rent_payment_refund import RentPaymentRefund, RefundStatus
from Backend.models.accounting.payment import Payment
from Backend.models.accounting.common import PaymentStatus
from Backend.utils.datetime_utils import utc_now
from Backend.api.notifications.email_templates import (
    BrikliEmailTemplate,
    EmailSection,
    EmailMetadataRow,
    EmailNotice,
    EmailCTA,
)
from Backend.api.notifications.sendgrid_service import SendGridService

logger = logging.getLogger(__name__)


async def handle_refund_created(
    refund: dict[str, Any],
    session: AsyncSession,
) -> None:
    """
    Handle refund creation.

    For card refunds, Stripe processes them synchronously so the refund.created
    event often arrives with status='succeeded' already. We need to update
    our local record accordingly.
    """
    refund_id = refund.get("id")
    charge_id = refund.get("charge")
    refund_status = refund.get("status")

    # Find our local refund record
    refund_record = await session.scalar(
        select(RentPaymentRefund)
        .where(col(RentPaymentRefund.stripe_refund_id) == refund_id)
        .options(selectinload(getattr(RentPaymentRefund, "transaction")))
    )

    if not refund_record:
        logger.warning(f"No local refund record found for {refund_id}")
        return

    # If refund already succeeded, update our local status
    if refund_status == "succeeded" and refund_record.status == RefundStatus.PENDING:
        refund_record.status = RefundStatus.SUCCEEDED
        refund_record.succeeded_at = utc_now()
        refund_record.updated_at = utc_now()
        session.add(refund_record)

        # Update transaction status based on total refunded amount
        # Must eagerly load refunds to avoid lazy-load error in async context
        transaction = await session.scalar(
            select(RentPaymentTransaction)
            .where(col(RentPaymentTransaction.id) == refund_record.transaction_id)
            .options(selectinload(getattr(RentPaymentTransaction, "refunds")))
        )
        if transaction:
            total_refunded = transaction.total_refunded_cents
            is_full_refund = total_refunded >= transaction.amount_cents

            if is_full_refund:
                transaction.status = RentPaymentTransactionStatus.REFUNDED
                transaction.refunded_at = utc_now()
            elif total_refunded > 0:
                transaction.status = RentPaymentTransactionStatus.PARTIALLY_REFUNDED
            session.add(transaction)

            # Update ledger payment to match refund status
            if transaction.payment_id:
                payment = await session.get(Payment, transaction.payment_id)
                if payment:
                    if is_full_refund:
                        payment.status = PaymentStatus.REFUNDED
                    elif total_refunded > 0:
                        payment.status = PaymentStatus.PARTIALLY_REFUNDED
                    payment.updated_at = utc_now()
                    session.add(payment)

        await session.commit()
        total_refunded_display = f"${total_refunded/100:.2f}" if transaction else "N/A"
        is_full_refund_display = str(is_full_refund) if transaction else "N/A"
        logger.info(
            f"Refund succeeded via refund.created | "
            f"refund_id={refund_id} | "
            f"amount=${refund_record.amount_cents/100:.2f} | "
            f"total_refunded={total_refunded_display} | "
            f"is_full_refund={is_full_refund_display}"
        )

        # Send notification
        if refund_record.transaction:
            await _send_refund_notification(refund_record, session)
    else:
        logger.info(f"Refund created | refund_id={refund_id} | status={refund_status}")


async def handle_refund_updated(
    refund: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle refund status updates."""
    refund_id = refund.get("id")
    refund_status = refund.get("status")
    
    refund_record = await session.scalar(
        select(RentPaymentRefund)
        .where(col(RentPaymentRefund.stripe_refund_id) == refund_id)
        .options(selectinload(getattr(RentPaymentRefund, "transaction")))
    )
    
    if not refund_record:
        logger.warning(f"No refund record found for {refund_id}")
        return
    
    # Update status
    if refund_status == "succeeded":
        refund_record.status = RefundStatus.SUCCEEDED
        refund_record.succeeded_at = utc_now()

        # Update transaction status based on total refunded amount
        # Must eagerly load refunds to avoid lazy-load error in async context
        transaction = await session.scalar(
            select(RentPaymentTransaction)
            .where(col(RentPaymentTransaction.id) == refund_record.transaction_id)
            .options(selectinload(getattr(RentPaymentTransaction, "refunds")))
        )
        if transaction:
            total_refunded = transaction.total_refunded_cents
            is_full_refund = total_refunded >= transaction.amount_cents

            if is_full_refund:
                transaction.status = RentPaymentTransactionStatus.REFUNDED
                transaction.refunded_at = utc_now()
            elif total_refunded > 0:
                transaction.status = RentPaymentTransactionStatus.PARTIALLY_REFUNDED
            session.add(transaction)

            # Update ledger payment to match refund status
            if transaction.payment_id:
                payment = await session.get(Payment, transaction.payment_id)
                if payment:
                    if is_full_refund:
                        payment.status = PaymentStatus.REFUNDED
                    elif total_refunded > 0:
                        payment.status = PaymentStatus.PARTIALLY_REFUNDED
                    payment.updated_at = utc_now()
                    session.add(payment)

    elif refund_status == "failed":
        refund_record.status = RefundStatus.FAILED
        refund_record.failed_at = utc_now()
        refund_record.failure_reason = refund.get("failure_reason")

    refund_record.updated_at = utc_now()
    session.add(refund_record)
    await session.commit()

    logger.info(
        f"Refund updated | "
        f"refund_id={refund_id} | "
        f"status={refund_status}"
    )

    # NOTE: We intentionally do NOT send notification here.
    # Notifications are sent from handle_refund_created to avoid duplicates.
    # For card refunds, refund.created arrives with status=succeeded,
    # and then refund.updated + charge.refund.updated also arrive.
    # Sending from all three would result in 3 emails.


async def handle_refund_failed(
    refund: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle refund failure."""
    refund_id = refund.get("id")
    failure_reason = refund.get("failure_reason")
    
    refund_record = await session.scalar(
        select(RentPaymentRefund)
        .where(col(RentPaymentRefund.stripe_refund_id) == refund_id)
        .options(selectinload(getattr(RentPaymentRefund, "transaction")))
    )
    
    if not refund_record:
        logger.warning(f"No refund record found for {refund_id}")
        return
    
    refund_record.status = RefundStatus.FAILED
    refund_record.failed_at = utc_now()
    refund_record.failure_reason = failure_reason
    refund_record.updated_at = utc_now()
    
    session.add(refund_record)
    await session.commit()
    
    logger.error(
        f"Refund failed | "
        f"refund_id={refund_id} | "
        f"reason={failure_reason}"
    )
    
    # Send notification to landlord about failure
    if refund_record.transaction:
        await _send_refund_failure_notification(refund_record, session)


# =============================================================================
# Notification Helpers
# =============================================================================

async def _send_refund_notification(
    refund: RentPaymentRefund,
    session: AsyncSession,
) -> None:
    """Send refund confirmation email to tenant."""
    try:
        # Load transaction with tenant
        transaction = await session.get(
            RentPaymentTransaction,
            refund.transaction_id,
            options=[
                selectinload(getattr(RentPaymentTransaction, "tenant")),
                selectinload(getattr(RentPaymentTransaction, "lease")),
            ]
        )
        
        if not transaction or not transaction.tenant:
            logger.warning(f"Cannot send refund notification - tenant not found for refund {refund.id}")
            return
        
        tenant = transaction.tenant
        tenant_email = tenant.email
        tenant_name = tenant.first_name or "Tenant"
        
        if not tenant_email:
            logger.warning(f"Cannot send refund notification - no email for tenant {tenant.id}")
            return
        
        # Build email
        refund_amount = f"${refund.amount_cents / 100:.2f}"
        
        html_content = BrikliEmailTemplate.create_email(
            title="Refund Processed",
            greeting=f"Hi {tenant_name},",
            sections=[
                EmailSection(
                    text=f"A refund of {refund_amount} CAD has been processed for your rent payment.",
                    is_bold=False
                ),
                EmailSection(
                    text="The refund will appear in your account within 5-10 business days, depending on your bank.",
                    is_bold=False
                ),
            ],
            metadata=[
                EmailMetadataRow(label="Refund Amount", value=refund_amount, emoji="💰"),
                EmailMetadataRow(label="Reason", value=refund.reason.replace("_", " ").title(), emoji="📋"),
                EmailMetadataRow(label="Date", value=refund.created_at.strftime("%B %d, %Y"), emoji="📅"),
            ],
            notice=EmailNotice(
                emoji="✅",
                title="Refund Confirmed",
                message=f"Your refund of {refund_amount} has been successfully processed.",
                color="#10b981",  # green
                bg_color="#d1fae5"  # green-100
            ),
            footer_note="If you have questions about this refund, please contact your landlord or Brikli support."
        )
        
        sendgrid_service = SendGridService()
        await sendgrid_service.send_raw_email(
            to_email=tenant_email,
            to_name=tenant_name,
            subject=f"Refund Processed - {refund_amount}",
            html_content=html_content
        )
        
        logger.info(f"Refund notification sent | refund_id={refund.id} | tenant_email={tenant_email}")
        
    except Exception as e:
        logger.error(f"Failed to send refund notification | refund_id={refund.id} | error={e}")


async def _send_refund_failure_notification(
    refund: RentPaymentRefund,
    session: AsyncSession,
) -> None:
    """Send refund failure notification to landlord."""
    try:
        # Load transaction with landlord
        transaction = await session.get(
            RentPaymentTransaction,
            refund.transaction_id,
            options=[selectinload(getattr(RentPaymentTransaction, "landlord"))]
        )
        
        if not transaction or not transaction.landlord:
            logger.warning(f"Cannot send refund failure notification - landlord not found for refund {refund.id}")
            return
        
        landlord = transaction.landlord
        landlord_email = landlord.email
        landlord_name = landlord.first_name or "Landlord"
        
        if not landlord_email:
            logger.warning(f"Cannot send refund failure notification - no email for landlord {landlord.id}")
            return
        
        # Build email
        refund_amount = f"${refund.amount_cents / 100:.2f}"
        failure_reason = refund.failure_reason or "Unknown error"
        
        html_content = BrikliEmailTemplate.create_email(
            title="Refund Failed",
            greeting=f"Hi {landlord_name},",
            sections=[
                EmailSection(
                    text=f"A refund of {refund_amount} CAD could not be processed.",
                    is_bold=True
                ),
                EmailSection(
                    text=f"Reason: {failure_reason}",
                    is_bold=False
                ),
                EmailSection(
                    text="Please contact Brikli support to resolve this issue and reissue the refund.",
                    is_bold=False
                ),
            ],
            metadata=[
                EmailMetadataRow(label="Refund Amount", value=refund_amount, emoji="💰"),
                EmailMetadataRow(label="Transaction ID", value=str(refund.transaction_id), emoji="🔖"),
                EmailMetadataRow(label="Date", value=refund.created_at.strftime("%B %d, %Y"), emoji="📅"),
            ],
            notice=EmailNotice(
                emoji="⚠️",
                title="Action Required",
                message="This refund requires your attention. Please contact support.",
                color="#ef4444",  # red
                bg_color="#fee2e2"  # red-100
            ),
            cta=EmailCTA(
                text="Contact Support",
                url="https://app.brikli.com/support"
            ),
            footer_note="Refunds typically fail due to insufficient funds or expired payment methods."
        )
        
        sendgrid_service = SendGridService()
        await sendgrid_service.send_raw_email(
            to_email=landlord_email,
            to_name=landlord_name,
            subject=f"Refund Failed - {refund_amount}",
            html_content=html_content
        )
        
        logger.info(f"Refund failure notification sent | refund_id={refund.id} | landlord_email={landlord_email}")
        
    except Exception as e:
        logger.error(f"Failed to send refund failure notification | refund_id={refund.id} | error={e}")

