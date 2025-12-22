"""
Stripe Webhook Handlers for Rent Payments

Handles webhook events for:
- PaymentIntent status changes (succeeded, failed, etc.)
- Connect account updates
- Charge events (refunds, disputes)

This module provides the webhook endpoints and routes events to domain-specific handlers.
Handler implementations are organized in the webhook_handlers/ subdirectory.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import stripe
import sentry_sdk

from Backend.config import settings
from Backend.database import get_session
from Backend.api.rent_payments.webhook_utils import (
    log_webhook_event,
    update_webhook_event_status,
    check_event_already_processed,
)

# Import modular webhook handlers
from .webhook_handlers import (
    # Payment Intent handlers
    handle_payment_intent_succeeded,
    handle_payment_intent_failed,
    handle_payment_intent_canceled,
    handle_payment_intent_processing,
    handle_payment_intent_requires_action,
    handle_payment_intent_amount_capturable_updated,
    handle_payment_intent_partially_funded,
    # Charge handlers
    handle_charge_succeeded,
    handle_charge_failed,
    handle_charge_pending,
    handle_charge_expired,
    handle_charge_refunded,
    handle_charge_updated,
    # Dispute handlers
    handle_dispute_created,
    handle_dispute_updated,
    handle_dispute_closed,
    handle_dispute_funds_withdrawn,
    handle_dispute_funds_reinstated,
    # Refund handlers
    handle_refund_created,
    handle_refund_updated,
    handle_refund_failed,
    # Payment Method handlers
    handle_payment_method_attached,
    handle_payment_method_updated,
    handle_payment_method_detached,
    handle_setup_intent_succeeded,
    # Connect handlers
    handle_account_updated,
)

from .schemas import WebhookEventResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Stripe Webhooks"])


# =============================================================================
# Webhook Endpoints
# =============================================================================

@router.post(
    "/stripe/rent-payments",
    response_model=WebhookEventResponse,
    summary="Stripe rent payment webhooks",
    description="Handle Stripe webhooks for rent payment events",
)
async def handle_rent_payment_webhook(request: Request) -> WebhookEventResponse:
    """
    Handle Stripe webhook events for rent payments with idempotent processing.
    
    This endpoint receives events for:
    - payment_intent.* (succeeded, failed, canceled, processing, etc.)
    - charge.* (succeeded, failed, pending, expired, refunded, updated)
    - charge.dispute.* (created, updated, closed, funds_withdrawn, funds_reinstated)
    - refund.* (created, updated, failed)
    - payment_method.* (attached, updated, detached)
    - setup_intent.succeeded
    
    Idempotency:
    - Each event is logged with a unique stripe_event_id
    - Duplicate events are detected and skipped
    - Race conditions are handled via database unique constraint
    """
    # Get the raw body for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature header"
        )
    
    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_RENT_PAYMENT_WEBHOOK_SECRET,
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    
    logger.info(f"Received webhook | event_id={event.id} | type={event.type}")
    
    # Get database session
    async for session in get_session():
        try:
            # Check for duplicate event (idempotency)
            already_processed = await check_event_already_processed(event.id, session)
            
            if already_processed:
                logger.info(
                    f"✅ Duplicate event detected, skipping | "
                    f"event_id={event.id} | "
                    f"type={event.type}"
                )
                return WebhookEventResponse(
                    event_id=event.id,
                    event_type=event.type,
                    processed=True,
                    duplicate=True,
                )
            
            # Log the event atomically to claim it (prevents race conditions)
            from sqlalchemy.exc import IntegrityError
            
            try:
                await log_webhook_event(
                    event,
                    session,
                    processed=False,  # Will update after processing
                    stripe_account_id=event.account if hasattr(event, 'account') else None,
                )
            except IntegrityError:
                # Race condition: Another request logged this event between our check and insert
                await session.rollback()
                logger.warning(
                    f"⚠️ Race condition detected during event logging | "
                    f"event_id={event.id} | "
                    f"type={event.type} | "
                    f"Another webhook handler claimed this event first"
                )
                return WebhookEventResponse(
                    event_id=event.id,
                    event_type=event.type,
                    processed=True,
                    duplicate=True,
                )
            
            # Process the event
            processed = await _process_event(event, session)
            
            # Update event log status
            await update_webhook_event_status(
                event.id,
                session,
                processed=processed,
                error=None if processed else "Event handler returned False",
            )
            
            logger.info(
                f"✅ Webhook processed | "
                f"event_id={event.id} | "
                f"type={event.type} | "
                f"processed={processed}"
            )
            
            return WebhookEventResponse(
                event_id=event.id,
                event_type=event.type,
                processed=processed,
            )
            
        except Exception as e:
            # Log the error to webhook event log
            try:
                await update_webhook_event_status(
                    event.id,
                    session,
                    processed=False,
                    error=str(e),
                )
            except Exception as log_error:
                logger.error(f"Failed to update event log with error: {log_error}")
            
            # Capture in Sentry for alerting
            sentry_sdk.capture_exception(
                e,
                tags={
                    "component": "rent_payment_webhook",
                    "event_type": event.type,
                    "event_id": event.id,
                    "webhook_type": "rent_payments",
                },
                contexts={
                    "webhook": {
                        "event_id": event.id,
                        "event_type": event.type,
                        "api_version": event.api_version if hasattr(event, 'api_version') else None,
                    }
                },
            )
            
            logger.error(
                f"❌ Error processing webhook | "
                f"event_id={event.id} | "
                f"type={event.type} | "
                f"error={e}",
                exc_info=True,
            )
            
            return WebhookEventResponse(
                event_id=event.id,
                event_type=event.type,
                processed=False,
                error=str(e),
            )
    
    # Fallback if session generator yields nothing (shouldn't happen)
    return WebhookEventResponse(
        event_id=event.id,
        event_type=event.type,
        processed=False,
        error="No database session available",
    )


@router.post(
    "/stripe/connect",
    response_model=WebhookEventResponse,
    summary="Stripe Connect webhooks",
    description="Handle Stripe Connect account update events",
)
async def handle_connect_webhook(request: Request) -> WebhookEventResponse:
    """
    Handle Stripe Connect webhook events with idempotent processing.
    
    Receives events for connected account status changes (account.updated).
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature header"
        )
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_CONNECT_WEBHOOK_SECRET,
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    
    logger.info(f"Received Connect webhook | event_id={event.id} | type={event.type}")
    
    async for session in get_session():
        try:
            # Check for duplicate event
            already_processed = await check_event_already_processed(event.id, session)
            
            if already_processed:
                logger.info(f"✅ Duplicate Connect event, skipping | event_id={event.id}")
                return WebhookEventResponse(
                    event_id=event.id,
                    event_type=event.type,
                    processed=True,
                    duplicate=True,
                )
            
            # Log event atomically
            from sqlalchemy.exc import IntegrityError
            
            try:
                await log_webhook_event(
                    event,
                    session,
                    processed=False,
                    stripe_account_id=event.account if hasattr(event, 'account') else None,
                )
            except IntegrityError:
                await session.rollback()
                logger.warning(f"⚠️ Race condition on Connect webhook | event_id={event.id}")
                return WebhookEventResponse(
                    event_id=event.id,
                    event_type=event.type,
                    processed=True,
                    duplicate=True,
                )
            
            # Process event
            processed = await _process_connect_event(event, session)
            
            # Update status
            await update_webhook_event_status(
                event.id,
                session,
                processed=processed,
                error=None if processed else "Handler returned False",
            )
            
            return WebhookEventResponse(
                event_id=event.id,
                event_type=event.type,
                processed=processed,
            )
            
        except Exception as e:
            try:
                await update_webhook_event_status(event.id, session, processed=False, error=str(e))
            except Exception as log_error:
                logger.error(f"Failed to log error: {log_error}")
            
            # Capture in Sentry
            sentry_sdk.capture_exception(
                e,
                tags={
                    "component": "rent_payment_webhook",
                    "event_type": event.type,
                    "event_id": event.id,
                    "webhook_type": "connect",
                },
                contexts={
                    "webhook": {
                        "event_id": event.id,
                        "event_type": event.type,
                        "account_id": event.account if hasattr(event, 'account') else None,
                    }
                },
            )
            
            logger.error(f"❌ Error processing Connect webhook | event_id={event.id} | error={e}", exc_info=True)
            return WebhookEventResponse(
                event_id=event.id,
                event_type=event.type,
                processed=False,
                error=str(e),
            )
    
    # Fallback if session generator yields nothing (shouldn't happen)
    return WebhookEventResponse(
        event_id=event.id,
        event_type=event.type,
        processed=False,
        error="No database session available",
    )


# =============================================================================
# Event Processors
# =============================================================================

async def _process_event(event: stripe.Event, session: AsyncSession) -> bool:
    """
    Route and process a Stripe event.
    
    Returns True if event was processed, False if skipped.
    """
    handlers = {
        # Payment Intent events
        "payment_intent.succeeded": handle_payment_intent_succeeded,
        "payment_intent.payment_failed": handle_payment_intent_failed,
        "payment_intent.canceled": handle_payment_intent_canceled,
        "payment_intent.processing": handle_payment_intent_processing,
        "payment_intent.requires_action": handle_payment_intent_requires_action,
        "payment_intent.amount_capturable_updated": handle_payment_intent_amount_capturable_updated,
        "payment_intent.partially_funded": handle_payment_intent_partially_funded,
        
        # Charge events
        "charge.succeeded": handle_charge_succeeded,
        "charge.failed": handle_charge_failed,
        "charge.pending": handle_charge_pending,
        "charge.expired": handle_charge_expired,
        "charge.refunded": handle_charge_refunded,
        "charge.updated": handle_charge_updated,
        
        # Dispute events
        "charge.dispute.created": handle_dispute_created,
        "charge.dispute.updated": handle_dispute_updated,
        "charge.dispute.closed": handle_dispute_closed,
        "charge.dispute.funds_withdrawn": handle_dispute_funds_withdrawn,
        "charge.dispute.funds_reinstated": handle_dispute_funds_reinstated,
        
        # Refund events
        "refund.created": handle_refund_created,
        "refund.updated": handle_refund_updated,
        "refund.failed": handle_refund_failed,
        "charge.refund.updated": handle_refund_updated,  # Alias for refund.updated
        
        # Payment Method events
        "payment_method.attached": handle_payment_method_attached,
        "payment_method.updated": handle_payment_method_updated,
        "payment_method.detached": handle_payment_method_detached,
        
        # Setup Intent events
        "setup_intent.succeeded": handle_setup_intent_succeeded,
    }
    
    handler = handlers.get(event.type)
    if handler:
        await handler(event.data.object, session)
        return True
    
    logger.debug(f"Unhandled event type: {event.type}")
    return False
    

async def _process_connect_event(event: stripe.Event, session: AsyncSession) -> bool:
    """
    Process Connect-specific events.
    """
    handlers = {
        "account.updated": handle_account_updated,
    }
    
    handler = handlers.get(event.type)
    if handler:
        await handler(event.data.object, session)
        return True
    
    return False
