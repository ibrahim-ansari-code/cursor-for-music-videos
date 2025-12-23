"""Dispute webhook event handlers and notifications"""

import logging
from typing import Any

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from Backend.models.rent_payment_transaction import (
    RentPaymentTransaction,
    RentPaymentTransactionStatus,
)
from Backend.models.rent_payment_dispute import RentPaymentDispute, DisputeStatus
from Backend.models.lease import Lease
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


async def handle_dispute_created(
    dispute: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle charge dispute (chargeback) - CREATE the dispute record."""
    dispute_id = dispute.get("id")
    charge_id = dispute.get("charge")
    
    if not dispute_id or not charge_id:
        logger.error("Dispute missing ID or charge ID")
        return
    
    # Check if dispute already exists (idempotency)
    existing = await session.scalar(
        select(RentPaymentDispute).where(
            col(RentPaymentDispute.stripe_dispute_id) == dispute_id
        )
    )
    
    if existing:
        logger.debug(f"Dispute {dispute_id} already exists")
        return
    
    # Find transaction with relationships
    transaction = await session.scalar(
        select(RentPaymentTransaction)
        .options(
            selectinload(getattr(RentPaymentTransaction, "landlord")),
            selectinload(getattr(RentPaymentTransaction, "lease"))
            .selectinload(getattr(Lease, "property")),
            selectinload(getattr(RentPaymentTransaction, "tenant"))
        )
        .where(col(RentPaymentTransaction.stripe_charge_id) == charge_id)
    )
    
    if not transaction:
        logger.error(f"No transaction found for disputed charge {charge_id}")
        return
    
    # Parse evidence deadline
    evidence_details = dispute.get("evidence_details", {})
    evidence_due_by = None
    if evidence_details.get("due_by"):
        try:
            from datetime import datetime, timezone
            evidence_due_by = datetime.fromtimestamp(
                evidence_details["due_by"],
                tz=timezone.utc
            )
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse evidence due date: {e}")
    
    # Create dispute record
    dispute_record = RentPaymentDispute(
        transaction_id=transaction.id,
        stripe_dispute_id=dispute_id,
        stripe_charge_id=charge_id,
        amount_cents=dispute.get("amount", 0),
        currency=dispute.get("currency", "cad"),
        reason=dispute.get("reason", "general"),
        status=dispute.get("status", DisputeStatus.NEEDS_RESPONSE),
        evidence_due_by=evidence_due_by,
        is_charge_refundable=dispute.get("is_charge_refundable", True),
    )
    
    logger.warning(
        f"🚨 Dispute created and recorded | "
        f"dispute_id={dispute_id} | "
        f"transaction_id={transaction.id} | "
        f"charge_id={charge_id} | "
        f"reason={dispute_record.reason} | "
        f"amount=${dispute_record.amount_dollars:.2f} | "
        f"status={dispute_record.status}"
    )
    
    # Track in Sentry for alerting (HIGH PRIORITY)
    sentry_sdk.capture_message(
        f"🚨 Dispute Created: ${dispute_record.amount_dollars:.2f} - {dispute_record.reason}",
        level="warning",
        tags={
            "component": "rent_payment_dispute",
            "dispute_reason": dispute_record.reason,
            "dispute_status": dispute_record.status,
            "transaction_id": str(transaction.id),
            "landlord_id": str(transaction.landlord_user_id),
        },
        contexts={
            "dispute": {
                "dispute_id": dispute_id,
                "amount": dispute_record.amount_dollars,
                "reason": dispute_record.reason,
                "evidence_due_by": str(evidence_due_by) if evidence_due_by else None,
                "days_until_deadline": (evidence_due_by - utc_now()).days if evidence_due_by else None,
            },
            "transaction": {
                "id": str(transaction.id),
                "charge_id": charge_id,
                "amount": transaction.amount_dollars,
                "tenant_id": str(transaction.tenant_id),
            }
        },
    )
    
    # Send urgent notification to landlord before committing the dispute record
    await _send_dispute_notification(dispute_record, transaction, session)
    
    session.add(dispute_record)
    await session.commit()
    await session.refresh(dispute_record)


async def handle_dispute_updated(
    dispute: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle dispute status updates."""
    dispute_id = dispute.get("id")
    
    dispute_record = await session.scalar(
        select(RentPaymentDispute).where(
            col(RentPaymentDispute.stripe_dispute_id) == dispute_id
        )
    )
    
    if not dispute_record:
        logger.warning(f"No dispute record found for {dispute_id}")
        return
    
    # Update status - map Stripe status to our constants
    status_str = dispute.get("status")
    if status_str:
        # Map Stripe dispute statuses to our internal constants
        stripe_status_map = {
            "warning_needs_response": DisputeStatus.WARNING_NEEDS_RESPONSE,
            "warning_under_review": DisputeStatus.WARNING_UNDER_REVIEW,
            "warning_closed": DisputeStatus.WARNING_CLOSED,
            "needs_response": DisputeStatus.NEEDS_RESPONSE,
            "under_review": DisputeStatus.UNDER_REVIEW,
            "charge_refunded": DisputeStatus.CHARGE_REFUNDED,
            "won": DisputeStatus.WON,
            "lost": DisputeStatus.LOST,
        }
        
        if status_str in stripe_status_map:
            dispute_record.status = stripe_status_map[status_str]
        else:
            logger.warning(f"Unknown dispute status from Stripe: {status_str}")
            # Keep existing status if unrecognized
    dispute_record.is_charge_refundable = dispute.get("is_charge_refundable", True)
    dispute_record.updated_at = utc_now()
    
    session.add(dispute_record)
    await session.commit()
    
    logger.info(
        f"Dispute updated | "
        f"dispute_id={dispute_id} | "
        f"status={dispute_record.status}"
    )


async def handle_dispute_closed(
    dispute: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle dispute closure."""
    dispute_id = dispute.get("id")
    
    dispute_record = await session.scalar(
        select(RentPaymentDispute).where(
            col(RentPaymentDispute.stripe_dispute_id) == dispute_id
        )
    )
    
    if not dispute_record:
        logger.warning(f"No dispute record found for {dispute_id}")
        return
    
    # Update closure
    dispute_record.status = dispute.get("status", DisputeStatus.LOST)
    dispute_record.closed_at = utc_now()
    dispute_record.updated_at = utc_now()
    
    session.add(dispute_record)
    await session.commit()
    
    logger.info(
        f"Dispute closed | "
        f"dispute_id={dispute_id} | "
        f"status={dispute_record.status}"
    )
    
    # Send notification to landlord about outcome
    await _send_dispute_outcome_notification(dispute_record, session)


async def handle_dispute_funds_withdrawn(
    dispute: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle funds withdrawn due to lost dispute."""
    dispute_id = dispute.get("id")
    charge_id = dispute.get("charge")
    
    # Find transaction
    transaction = await session.scalar(
        select(RentPaymentTransaction).where(
            col(RentPaymentTransaction.stripe_charge_id) == charge_id
        )
    )
    
    if not transaction:
        logger.warning(f"No transaction found for charge {charge_id}")
        return
    
    # Update transaction status if fully disputed
    if dispute.get("amount", 0) >= transaction.amount_cents:
        transaction.status = RentPaymentTransactionStatus.REFUNDED
        transaction.refunded_at = utc_now()
    
    transaction.updated_at = utc_now()
    session.add(transaction)
    await session.commit()
    
    logger.warning(
        f"Dispute funds withdrawn | "
        f"transaction_id={transaction.id} | "
        f"dispute_id={dispute_id} | "
        f"amount=${dispute.get('amount', 0) / 100:.2f}"
    )
    
    # Notification handled by dispute_closed event


async def handle_dispute_funds_reinstated(
    dispute: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle funds reinstated after winning dispute."""
    dispute_id = dispute.get("id")
    
    logger.info(
        f"Dispute funds reinstated | "
        f"dispute_id={dispute_id}"
    )
    
    # Notification handled by dispute_closed event


# =============================================================================
# Notification Helpers
# =============================================================================

async def _send_dispute_notification(
    dispute: RentPaymentDispute,
    transaction: RentPaymentTransaction,
    session: AsyncSession,
) -> None:
    """Send urgent dispute notification to landlord when dispute is created."""
    try:
        if not transaction.landlord:
            logger.warning(f"Cannot send dispute notification - landlord not found for dispute {dispute.id}")
            return
        
        landlord = transaction.landlord
        landlord_email = landlord.email
        landlord_name = landlord.first_name or "Landlord"
        
        if not landlord_email:
            logger.warning(f"Cannot send dispute notification - no email for landlord {landlord.id}")
            return
        
        dispute_amount = f"${dispute.amount_cents / 100:.2f}"
        
        # Calculate days until evidence is due
        days_until_due = None
        if dispute.evidence_due_by:
            from datetime import datetime, timezone
            delta = dispute.evidence_due_by - datetime.now(timezone.utc)
            days_until_due = max(0, delta.days)
        
        # Build notification sections
        sections = [
            EmailSection(
                text=f"Hi {landlord_name},",
                is_bold=False
            ),
            EmailSection(
                text=f"⚠️ URGENT: A dispute (chargeback) has been filed against a rent payment of {dispute_amount} CAD.",
                is_bold=True
            ),
            EmailSection(
                text="A tenant has disputed a charge through their bank or card issuer. You need to respond with evidence to contest this dispute.",
                is_bold=False
            ),
        ]
        
        # Add evidence deadline if available
        if days_until_due is not None and dispute.evidence_due_by:
            deadline_text = dispute.evidence_due_by.strftime("%B %d, %Y at %I:%M %p UTC")
            sections.append(
                EmailSection(
                    text=f"⏰ You have {days_until_due} days to submit evidence (deadline: {deadline_text}).",
                    is_bold=True
                )
            )
        
        sections.append(
            EmailSection(
                text="To contest this dispute, log in to your Stripe Dashboard to submit evidence such as lease agreements, payment receipts, and correspondence with the tenant.",
                is_bold=False
            )
        )
        
        # Metadata
        metadata = [
            EmailMetadataRow(label="Dispute Amount", value=dispute_amount, emoji="💰"),
            EmailMetadataRow(label="Reason", value=dispute.reason.replace("_", " ").title(), emoji="📋"),
            EmailMetadataRow(label="Status", value=dispute.status.replace("_", " ").title(), emoji="⚠️"),
        ]
        
        if days_until_due is not None:
            metadata.append(
                EmailMetadataRow(label="Days to Respond", value=str(days_until_due), emoji="⏰")
            )
        
        html_content = BrikliEmailTemplate.create_email(
            title="🚨 Payment Dispute Filed",
            greeting="",  # Already in sections
            sections=sections,
            metadata=metadata,
            notice=EmailNotice(
                emoji="🚨",
                title="Urgent Action Required",
                message=f"A dispute has been filed for {dispute_amount}. Submit evidence to contest it.",
                color="#dc2626",  # red
                bg_color="#fee2e2"  # red-100
            ),
            cta=EmailCTA(
                text="View in Stripe Dashboard",
                url=f"https://dashboard.stripe.com/disputes/{dispute.stripe_dispute_id}"
            ),
            footer_note="If you do not respond by the deadline, the dispute will automatically be decided in favor of the tenant and funds will be returned."
        )
        
        sendgrid_service = SendGridService()
        await sendgrid_service.send_raw_email(
            to_email=landlord_email,
            to_name=landlord_name,
            subject=f"🚨 URGENT: Payment Dispute Filed - {dispute_amount}",
            html_content=html_content
        )
        
        # Mark as notified. The caller is responsible for the commit.
        dispute.landlord_notified = True
        dispute.landlord_notified_at = utc_now()
        session.add(dispute)
        # The commit is removed from here to be handled by the calling function.
        
        logger.info(
            f"📧 Urgent dispute notification sent | "
            f"dispute_id={dispute.id} | "
            f"landlord_email={landlord_email}"
        )
        
    except Exception as e:
        logger.error(f"Failed to send dispute notification | dispute_id={dispute.id} | error={e}")


async def _send_dispute_outcome_notification(
    dispute: RentPaymentDispute,
    session: AsyncSession,
) -> None:
    """Send dispute outcome notification to landlord."""
    try:
        # Load transaction with landlord
        transaction = await session.get(
            RentPaymentTransaction,
            dispute.transaction_id,
            options=[selectinload(getattr(RentPaymentTransaction, "landlord"))]
        )
        
        if not transaction or not transaction.landlord:
            logger.warning(f"Cannot send dispute outcome notification - landlord not found for dispute {dispute.id}")
            return
        
        landlord = transaction.landlord
        landlord_email = landlord.email
        landlord_name = landlord.first_name or "Landlord"
        
        if not landlord_email:
            logger.warning(f"Cannot send dispute outcome notification - no email for landlord {landlord.id}")
            return
        
        # Determine outcome
        is_won = dispute.status == DisputeStatus.WON
        dispute_amount = f"${dispute.amount_cents / 100:.2f}"
        
        if is_won:
            title = "Dispute Won"
            emoji = "🎉"
            message = f"You won the dispute for {dispute_amount}. Funds have been reinstated."
            color = "#10b981"  # green
            bg_color = "#d1fae5"  # green-100
            sections = [
                EmailSection(
                    text=f"Good news! You have won the dispute for {dispute_amount} CAD.",
                    is_bold=True
                ),
                EmailSection(
                    text="The disputed funds have been reinstated to your account.",
                    is_bold=False
                ),
            ]
        else:
            title = "Dispute Lost"
            emoji = "❌"
            message = f"The dispute for {dispute_amount} was decided in favor of the tenant."
            color = "#ef4444"  # red
            bg_color = "#fee2e2"  # red-100
            sections = [
                EmailSection(
                    text=f"Unfortunately, the dispute for {dispute_amount} CAD was decided in favor of the tenant.",
                    is_bold=True
                ),
                EmailSection(
                    text="The funds have been returned to the tenant's account.",
                    is_bold=False
                ),
                EmailSection(
                    text="If you believe this decision was incorrect, please contact Brikli support.",
                    is_bold=False
                ),
            ]
        
        html_content = BrikliEmailTemplate.create_email(
            title=title,
            greeting=f"Hi {landlord_name},",
            sections=sections,
            metadata=[
                EmailMetadataRow(label="Dispute Amount", value=dispute_amount, emoji="💰"),
                EmailMetadataRow(label="Reason", value=dispute.reason.replace("_", " ").title(), emoji="📋"),
                EmailMetadataRow(label="Closed Date", value=dispute.closed_at.strftime("%B %d, %Y") if dispute.closed_at else "N/A", emoji="📅"),
            ],
            notice=EmailNotice(
                emoji=emoji,
                title=title,
                message=message,
                color=color,
                bg_color=bg_color
            ),
            footer_note="For questions about this dispute, please contact Brikli support."
        )
        
        sendgrid_service = SendGridService()
        await sendgrid_service.send_raw_email(
            to_email=landlord_email,
            to_name=landlord_name,
            subject=f"Dispute {title} - {dispute_amount}",
            html_content=html_content
        )
        
        logger.info(f"Dispute outcome notification sent | dispute_id={dispute.id} | landlord_email={landlord_email} | won={is_won}")
        
    except Exception as e:
        logger.error(f"Failed to send dispute outcome notification | dispute_id={dispute.id} | error={e}")

