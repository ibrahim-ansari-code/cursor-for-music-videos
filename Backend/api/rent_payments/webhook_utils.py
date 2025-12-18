"""Rent Payment Webhook Utility Functions"""
import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from Backend.models.rent_payment_webhook_log import RentPaymentWebhookLog

logger = logging.getLogger(__name__)


async def log_webhook_event(
    event: stripe.Event,
    session: AsyncSession,
    processed: bool = False,
    error: str | None = None,
    stripe_account_id: str | None = None,
) -> RentPaymentWebhookLog:
    """
    Log Stripe rent payment webhook event for audit trail and idempotency.
    
    This function creates a record of every webhook event received, enabling:
    - Idempotent processing (check if event already processed)
    - Audit trail for compliance and debugging
    - Error tracking for monitoring
    - Manual replay if needed
    
    Args:
        event: Stripe event object
        session: Database session
        processed: Whether event was successfully processed
        error: Error message if processing failed
        stripe_account_id: Connected account ID if applicable
        
    Returns:
        RentPaymentWebhookLog record
        
    Raises:
        sqlalchemy.exc.IntegrityError: If event_id already exists (duplicate)
    """
    event_log = RentPaymentWebhookLog(
        stripe_event_id=event.id,
        event_type=event.type,
        api_version=event.api_version,
        event_data=event.to_dict(),
        processed=processed,
        processed_at=datetime.now(timezone.utc) if processed else None,
        processing_error=error,
        stripe_request_id=getattr(event.request, 'id', None) if event.request else None,
        stripe_account_id=stripe_account_id,
    )
    
    session.add(event_log)
    await session.commit()
    await session.refresh(event_log)
    
    logger.debug(
        f"Logged webhook event | "
        f"event_id={event.id} | "
        f"type={event.type} | "
        f"processed={processed}"
    )
    
    return event_log


async def update_webhook_event_status(
    event_id: str,
    session: AsyncSession,
    processed: bool,
    error: str | None = None,
) -> RentPaymentWebhookLog | None:
    """
    Update the processing status of a webhook event.
    
    Used to mark an event as processed after successful handling,
    or to record an error if processing failed.
    
    Args:
        event_id: Stripe event ID (evt_xxx)
        session: Database session
        processed: Whether event was successfully processed
        error: Error message if processing failed
        
    Returns:
        Updated RentPaymentWebhookLog record, or None if not found
    """
    result = await session.execute(
        select(RentPaymentWebhookLog).where(
            col(RentPaymentWebhookLog.stripe_event_id) == event_id
        )
    )
    event_log = result.scalar_one_or_none()
    
    if not event_log:
        logger.warning(f"Webhook event log not found for event_id={event_id}")
        return None
    
    event_log.processed = processed
    event_log.processed_at = datetime.now(timezone.utc) if processed else None
    event_log.processing_error = error
    
    session.add(event_log)
    await session.commit()
    await session.refresh(event_log)
    
    logger.debug(
        f"Updated webhook event status | "
        f"event_id={event_id} | "
        f"processed={processed}"
    )
    
    return event_log


async def check_event_already_processed(
    event_id: str,
    session: AsyncSession,
) -> bool:
    """
    Check if a webhook event has already been processed.
    
    This is the core idempotency check - before processing any webhook,
    we check if we've already handled this exact event ID.
    
    Args:
        event_id: Stripe event ID (evt_xxx)
        session: Database session
        
    Returns:
        True if event was already processed, False otherwise
    """
    result = await session.execute(
        select(RentPaymentWebhookLog).where(
            col(RentPaymentWebhookLog.stripe_event_id) == event_id
        )
    )
    existing_log = result.scalar_one_or_none()
    
    if existing_log:
        logger.info(
            f"Event already logged | "
            f"event_id={event_id} | "
            f"type={existing_log.event_type} | "
            f"processed={existing_log.processed} | "
            f"created_at={existing_log.created_at}"
        )
        return True
    
    return False

