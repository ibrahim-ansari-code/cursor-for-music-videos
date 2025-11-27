"""Stripe Webhook Utility Functions"""
import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.models.billing import StripeEventLog, BillingAuditLog

logger = logging.getLogger(__name__)


async def log_stripe_event(
    event: stripe.Event,
    session: AsyncSession,
    processed: bool = False,
    error: str | None = None
) -> StripeEventLog:
    """
    Log Stripe webhook event for audit trail and idempotency.
    
    Args:
        event: Stripe event object
        session: Database session
        processed: Whether event was successfully processed
        error: Error message if processing failed
        
    Returns:
        StripeEventLog record
    """
    event_log = StripeEventLog(
        stripe_event_id=event.id,
        event_type=event.type,
        api_version=event.api_version,
        event_data=event.to_dict(),
        processed=processed,
        processed_at=datetime.now(timezone.utc) if processed else None,
        processing_error=error,
        stripe_request_id=getattr(event.request, 'id', None) if event.request else None
    )
    
    session.add(event_log)
    await session.commit()
    await session.refresh(event_log)
    
    return event_log


async def log_billing_audit(
    action: str,
    actor: str,
    session: AsyncSession,
    user_id: str | None = None,
    subscription_id: str | None = None,
    description: str | None = None,
    audit_metadata: dict | None = None,
    amount: float | None = None,
    currency: str | None = None,
    stripe_event_id: str | None = None
):
    """
    Log business-level billing audit event.
    
    Args:
        action: Action performed (subscription_created, payment_succeeded, etc.)
        actor: Who/what initiated (system, user, stripe_webhook)
        session: Database session
        user_id: User UUID (optional)
        subscription_id: Subscription UUID (optional)
        description: Human-readable description
        audit_metadata: Additional context
        amount: Financial amount (optional)
        currency: Currency code (optional)
        stripe_event_id: Link to stripe_event_logs
    """
    audit_log = BillingAuditLog(
        user_id=user_id,
        subscription_id=subscription_id,
        action=action,
        actor=actor,
        description=description,
        audit_metadata=audit_metadata or {},
        amount=amount,
        currency=currency,
        stripe_event_id=stripe_event_id
    )
    
    session.add(audit_log)
    await session.commit()


