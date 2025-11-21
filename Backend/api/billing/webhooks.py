"""Stripe Webhook Endpoint"""
import logging
from datetime import datetime, timezone

import stripe
from stripe import SignatureVerificationError
from fastapi import APIRouter, Request, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlmodel import col

from Backend.config import settings
from Backend.database import get_session
from Backend.models.billing import StripeEventLog
from Backend.api.billing.webhook_utils import log_stripe_event
from Backend.api.billing.webhook_handlers import (
    handle_subscription_created,
    handle_subscription_updated,
    handle_subscription_deleted,
    handle_payment_succeeded,
    handle_payment_failed,
    handle_trial_will_end
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing-webhooks"])


@router.post("/webhook")
async def stripe_webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """
    Handle Stripe webhook events with optimized background task processing.
    
    Industry-standard implementation:
    1. Verify webhook signature (prevent spoofing)
    2. Check for duplicate events (idempotency)
    3. Process event based on type (critical ops synchronous)
    4. Offload emails/audit logs to background tasks
    5. Respond to Stripe within 2s to avoid retries
    
    Events handled:
    - customer.subscription.created: New subscription
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription ended
    - invoice.payment_succeeded: Payment successful
    - invoice.payment_failed: Payment failed
    - customer.subscription.trial_will_end: Trial ending soon (3 days)
    
    Performance:
    - Critical subscription updates: Synchronous (<1s)
    - Email delivery: Background task (non-blocking)
    - Audit logging: Background task (non-blocking)
    
    Security:
    - Signature verification prevents unauthorized events
    - Event deduplication prevents double-processing
    - All events logged for audit
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    if not sig_header:
        logger.error("Missing Stripe-Signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header"
        )
    
    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Check for duplicate event (idempotency) with race condition handling
    result = await session.execute(
        select(StripeEventLog).where(col(StripeEventLog.stripe_event_id) == event.id)
    )
    existing_log = result.scalar_one_or_none()
    
    if existing_log:
        logger.info(f"Event {event.id} already processed, skipping")
        return {"received": True, "duplicate": True}
    
    # Attempt to log the event first to handle race conditions atomically
    from sqlalchemy.exc import IntegrityError
    
    try:
        await log_stripe_event(event, session, processed=False)
    except IntegrityError:
        # This block executes if the event ID already exists due to a race condition.
        # The unique constraint on `stripe_event_id` prevents duplicate entries.
        await session.rollback()  # Rollback the failed transaction
        logger.warning(
            f"Duplicate event {event.id} detected during concurrent processing. Skipping."
        )
        return {"received": True, "duplicate": True}
    
    logger.info(f"Received Stripe webhook | type={event.type} | id={event.id}")
    
    # Process event based on type
    try:
        if event.type == 'customer.subscription.created':
            await handle_subscription_created(event, session, background_tasks)
        elif event.type == 'customer.subscription.updated':
            await handle_subscription_updated(event, session, background_tasks)
        elif event.type == 'customer.subscription.deleted':
            await handle_subscription_deleted(event, session, background_tasks)
        elif event.type == 'invoice.payment_succeeded':
            await handle_payment_succeeded(event, session, background_tasks)
        elif event.type == 'invoice.payment_failed':
            await handle_payment_failed(event, session, background_tasks)
        elif event.type == 'customer.subscription.trial_will_end':
            await handle_trial_will_end(event, session, background_tasks)
        else:
            logger.info(f"Unhandled event type: {event.type}")
        
        # Mark event as processed
        # If the event was already processed and we're seeing it again (e.g., after a retry),
        # we can log and skip. This check is now a secondary safeguard.
        result = await session.execute(
            select(StripeEventLog).where(
                col(StripeEventLog.stripe_event_id) == event.id,
                col(StripeEventLog.processed).is_(True)
            )
        )
        already_processed = result.scalar_one_or_none()
        
        if already_processed:
            logger.info(f"Event {event.id} already marked as processed, skipping update")
            return {"received": True, "duplicate": True}
        
        # Update the event log to mark as processed
        result = await session.execute(
            select(StripeEventLog).where(col(StripeEventLog.stripe_event_id) == event.id)
        )
        event_log = result.scalar_one()
        event_log.processed = True
        event_log.processed_at = datetime.now(timezone.utc)
        session.add(event_log)
        await session.commit()
        
        return {"received": True}
        
    except Exception as e:
        logger.error(f"Error processing webhook event {event.id}: {e}", exc_info=True)
        
        # Log error in event log
        result = await session.execute(
            select(StripeEventLog).where(col(StripeEventLog.stripe_event_id) == event.id)
        )
        event_log = result.scalar_one()
        event_log.processing_error = str(e)
        session.add(event_log)
        await session.commit()
        
        # Raise an HTTPException to signal a server-side error.
        # This allows monitoring tools to catch the failure and triggers
        # Stripe's automatic retry mechanism, which is safe due to
        # the idempotent design of the webhook handler.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook event {event.id}"
        )
