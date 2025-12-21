"""Stripe Webhook Event Handlers"""
import logging

import stripe
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlmodel import col

from Backend.api.billing.helpers import sync_subscription_from_stripe
from Backend.api.billing.webhook_tasks import (
    send_subscription_created_email,
    send_payment_succeeded_email,
    send_payment_failed_email,
    send_trial_ending_email,
    log_billing_audit_background
)

# Import tenant portal seat subscription handlers
from Backend.api.tenant_portal_seats.webhook_handlers import (
    handle_seat_subscription_created,
    handle_seat_subscription_updated,
    handle_seat_subscription_deleted
)

logger = logging.getLogger(__name__)


async def handle_subscription_created(event: stripe.Event, session: AsyncSession, background_tasks: BackgroundTasks):
    """Handle customer.subscription.created event"""
    subscription_obj = event.data.object

    logger.info(f"Processing subscription.created | sub_id={subscription_obj['id']}")

    # Check if this is a tenant portal seat subscription (not platform subscription)
    if subscription_obj.get('metadata', {}).get('product_type') == 'tenant_portal_seat_subscription':
        logger.info(f"Routing to seat subscription handler | sub_id={subscription_obj['id']}")
        await handle_seat_subscription_created(subscription_obj, session)
        return

    # SYNCHRONOUS: Critical subscription sync (must complete before responding to Stripe)
    subscription = await sync_subscription_from_stripe(
        subscription_obj['id'],
        session,
        stripe_sub_data=dict(subscription_obj)
    )
    
    # Get user and plan details for background tasks
    from Backend.models.user import User
    user_result = await session.execute(
        select(User).where(col(User.id) == subscription.user_id)
    )
    user = user_result.scalar_one()
    
    from Backend.models.billing import SubscriptionPlan
    plan_result = await session.execute(
        select(SubscriptionPlan).where(col(SubscriptionPlan.id) == subscription.plan_id)
    )
    plan = plan_result.scalar_one()
    
    # BACKGROUND: Send welcome email (non-blocking)
    background_tasks.add_task(
        send_subscription_created_email,
        user_email=user.email,
        user_first_name=user.first_name,
        user_last_name=user.last_name,
        plan_name=plan.name,
        plan_amount=float(plan.amount),
        plan_currency=plan.currency,
        subscription_id=str(subscription.id),
        trial_start=subscription.trial_start,
        trial_end=subscription.trial_end,
        event_id=event.id
    )
    
    # BACKGROUND: Log audit (non-blocking)
    background_tasks.add_task(
        log_billing_audit_background,
        action="subscription_created",
        actor="stripe_webhook",
        user_id=str(subscription.user_id),
        subscription_id=str(subscription.id),
        description=f"Subscription created with {subscription.status} status",
        audit_metadata={"stripe_subscription_id": subscription_obj['id']},
        stripe_event_id=event.id
    )
    
    logger.info(f"Subscription created | sub_id={subscription.id} | status={subscription.status}")


async def handle_subscription_updated(event: stripe.Event, session: AsyncSession, background_tasks: BackgroundTasks):
    """Handle customer.subscription.updated event"""
    subscription_obj = event.data.object

    logger.info(f"Processing subscription.updated | sub_id={subscription_obj['id']}")

    # Check if this is a tenant portal seat subscription (not platform subscription)
    if subscription_obj.get('metadata', {}).get('product_type') == 'tenant_portal_seat_subscription':
        logger.info(f"Routing to seat subscription handler | sub_id={subscription_obj['id']}")
        await handle_seat_subscription_updated(subscription_obj, session)
        return

    # SYNCHRONOUS: Critical subscription sync
    subscription = await sync_subscription_from_stripe(
        subscription_obj['id'],
        session,
        stripe_sub_data=dict(subscription_obj)
    )
    
    # BACKGROUND: Log audit (non-blocking)
    background_tasks.add_task(
        log_billing_audit_background,
        action="subscription_updated",
        actor="stripe_webhook",
        user_id=str(subscription.user_id),
        subscription_id=str(subscription.id),
        description=f"Subscription updated to {subscription.status} status",
        audit_metadata={
            "stripe_subscription_id": subscription_obj['id'],
            "cancel_at_period_end": subscription.cancel_at_period_end
        },
        stripe_event_id=event.id
    )
    
    logger.info(f"Subscription updated | sub_id={subscription.id} | status={subscription.status}")


async def handle_subscription_deleted(event: stripe.Event, session: AsyncSession, background_tasks: BackgroundTasks):
    """Handle customer.subscription.deleted event"""
    subscription_obj = event.data.object

    logger.info(f"Processing subscription.deleted | sub_id={subscription_obj['id']}")

    # Check if this is a tenant portal seat subscription (not platform subscription)
    if subscription_obj.get('metadata', {}).get('product_type') == 'tenant_portal_seat_subscription':
        logger.info(f"Routing to seat subscription handler | sub_id={subscription_obj['id']}")
        await handle_seat_subscription_deleted(subscription_obj, session)
        return

    # SYNCHRONOUS: Critical subscription sync (mark as canceled/ended)
    subscription = await sync_subscription_from_stripe(
        subscription_obj['id'],
        session,
        stripe_sub_data=dict(subscription_obj)
    )
    
    # BACKGROUND: Log audit (non-blocking)
    background_tasks.add_task(
        log_billing_audit_background,
        action="subscription_deleted",
        actor="stripe_webhook",
        user_id=str(subscription.user_id),
        subscription_id=str(subscription.id),
        description="Subscription ended",
        audit_metadata={"stripe_subscription_id": subscription_obj['id']},
        stripe_event_id=event.id
    )
    
    logger.info(f"Subscription deleted | sub_id={subscription.id}")


async def handle_payment_succeeded(event: stripe.Event, session: AsyncSession, background_tasks: BackgroundTasks):
    """Handle invoice.payment_succeeded event"""
    invoice = event.data.object
    
    logger.info(f"Processing payment_succeeded | invoice_id={invoice['id']}")
    
    # SYNCHRONOUS: Get subscription and sync
    subscription_id = invoice.get('subscription')
    if subscription_id:
        subscription = await sync_subscription_from_stripe(subscription_id, session)
        
        # Get user and plan details for background tasks
        from Backend.models.user import User
        user_result = await session.execute(
            select(User).where(col(User.id) == subscription.user_id)
        )
        user = user_result.scalar_one()
        
        from Backend.models.billing import SubscriptionPlan
        plan_result = await session.execute(
            select(SubscriptionPlan).where(col(SubscriptionPlan.id) == subscription.plan_id)
        )
        plan = plan_result.scalar_one()
        
        # Only send payment success email if amount > 0 (skip trial invoices)
        if invoice['amount_paid'] > 0:
            # BACKGROUND: Send payment success email (non-blocking)
            background_tasks.add_task(
                send_payment_succeeded_email,
                user_email=user.email,
                user_first_name=user.first_name,
                user_last_name=user.last_name,
                plan_name=plan.name,
                amount_paid=invoice['amount_paid'] / 100,
                currency=invoice['currency'],
                invoice_id=invoice['number'] or invoice['id'],
                invoice_pdf_url=invoice.get('invoice_pdf', invoice.get('hosted_invoice_url', '')),
                next_payment_date=subscription.current_period_end,
                subscription_id=str(subscription.id),
                stripe_invoice_id=invoice['id'],
                event_id=event.id
            )
            
            # BACKGROUND: Log audit (non-blocking)
            background_tasks.add_task(
                log_billing_audit_background,
                action="payment_succeeded",
                actor="stripe_webhook",
                user_id=str(subscription.user_id),
                subscription_id=str(subscription.id),
                description=f"Payment succeeded for ${invoice['amount_paid'] / 100:.2f}",
                audit_metadata={
                    "invoice_id": invoice['id'],
                    "amount_paid": invoice['amount_paid'],
                    "currency": invoice['currency']
                },
                amount=invoice['amount_paid'] / 100,
                currency=invoice['currency'].upper(),
                stripe_event_id=event.id
            )
            
            logger.info(f"Payment succeeded | sub_id={subscription.id} | amount={invoice['amount_paid']/100}")


async def handle_payment_failed(event: stripe.Event, session: AsyncSession, background_tasks: BackgroundTasks):
    """Handle invoice.payment_failed event"""
    invoice = event.data.object
    
    logger.error(f"Processing payment_failed | invoice_id={invoice['id']}")
    
    # SYNCHRONOUS: Get subscription and sync
    subscription_id = invoice.get('subscription')
    if subscription_id:
        subscription = await sync_subscription_from_stripe(subscription_id, session)
        
        # Get user and plan details for background tasks
        from Backend.models.user import User
        user_result = await session.execute(
            select(User).where(col(User.id) == subscription.user_id)
        )
        user = user_result.scalar_one()
        
        from Backend.models.billing import SubscriptionPlan
        plan_result = await session.execute(
            select(SubscriptionPlan).where(col(SubscriptionPlan.id) == subscription.plan_id)
        )
        plan = plan_result.scalar_one()
        
        # BACKGROUND: Send payment failed email (non-blocking)
        background_tasks.add_task(
            send_payment_failed_email,
            user_email=user.email,
            user_first_name=user.first_name,
            user_last_name=user.last_name,
            plan_name=plan.name,
            amount_due=invoice['amount_due'] / 100,
            currency=invoice['currency'],
            attempt_count=invoice.get('attempt_count', 1),
            invoice_url=invoice.get('hosted_invoice_url', ''),
            subscription_id=str(subscription.id),
            stripe_invoice_id=invoice['id'],
            event_id=event.id
        )
        
        # BACKGROUND: Log audit (non-blocking)
        background_tasks.add_task(
            log_billing_audit_background,
            action="payment_failed",
            actor="stripe_webhook",
            user_id=str(subscription.user_id),
            subscription_id=str(subscription.id),
            description=f"Payment failed for ${invoice['amount_due'] / 100:.2f}",
            audit_metadata={
                "invoice_id": invoice['id'],
                "amount_due": invoice['amount_due'],
                "currency": invoice['currency'],
                "attempt_count": invoice['attempt_count']
            },
            amount=invoice['amount_due'] / 100,
            currency=invoice['currency'].upper(),
            stripe_event_id=event.id
        )
        
        logger.error(f"Payment failed | sub_id={subscription.id} | amount={invoice['amount_due']/100}")


async def handle_trial_will_end(event: stripe.Event, session: AsyncSession, background_tasks: BackgroundTasks):
    """Handle customer.subscription.trial_will_end event (3 days before)"""
    subscription_obj = event.data.object
    
    logger.info(f"Processing trial_will_end | sub_id={subscription_obj['id']}")
    
    # SYNCHRONOUS: Sync subscription
    subscription = await sync_subscription_from_stripe(subscription_obj['id'], session)
    
    # Get user and plan details for background tasks
    from Backend.models.user import User
    user_result = await session.execute(
        select(User).where(col(User.id) == subscription.user_id)
    )
    user = user_result.scalar_one()
    
    from Backend.models.billing import SubscriptionPlan
    plan_result = await session.execute(
        select(SubscriptionPlan).where(col(SubscriptionPlan.id) == subscription.plan_id)
    )
    plan = plan_result.scalar_one()
    
    # BACKGROUND: Send trial ending email (non-blocking)
    background_tasks.add_task(
        send_trial_ending_email,
        user_email=user.email,
        user_first_name=user.first_name,
        user_last_name=user.last_name,
        plan_name=plan.name,
        plan_amount=float(plan.amount),
        plan_currency=plan.currency,
        days_remaining=3,
        subscription_id=str(subscription.id),
        event_id=event.id
    )
    
    # BACKGROUND: Log audit (non-blocking)
    background_tasks.add_task(
        log_billing_audit_background,
        action="trial_will_end",
        actor="stripe_webhook",
        user_id=str(subscription.user_id),
        subscription_id=str(subscription.id),
        description="Trial ending in 3 days",
        audit_metadata={"stripe_subscription_id": subscription_obj['id']},
        stripe_event_id=event.id
    )
    
    logger.info(f"Trial ending soon | sub_id={subscription.id}")

