"""Billing helpers - Stripe integration utilities"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlmodel import col

from Backend.api.stripe.client import get_stripe_client
from Backend.config import settings
from Backend.models.user import User
from Backend.models.billing import SubscriptionPlan, UserSubscription

logger = logging.getLogger(__name__)


async def get_or_create_stripe_customer(
    user: User,
    session: AsyncSession
) -> str:
    """
    Get existing Stripe customer ID or create new customer.
    
    Args:
        user: User to get/create Stripe customer for
        session: Database session
        
    Returns:
        Stripe customer ID (cus_xxx)
    """
    # Check if user already has Stripe customer ID
    if user.stripe_customer_id:
        return user.stripe_customer_id
    
    # Create new Stripe customer
    try:
        stripe_client = get_stripe_client()
        customer = await stripe_client.customers.create(
            email=user.email,
            name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            metadata={
                "user_id": str(user.id),
                "user_type": user.user_type
            }
        )
        
        # Update user with Stripe customer ID
        user.stripe_customer_id = customer.id
        session.add(user)
        await session.commit()
        
        logger.info(
            f"Created Stripe customer | "
            f"user_id={user.id} | "
            f"customer_id={customer.id}"
        )
        
        return customer.id
        
    except Exception as e:
        logger.error(f"Failed to create Stripe customer for user {user.id}: {e}")
        raise


async def get_platform_price(session: AsyncSession) -> SubscriptionPlan:
    """
    Get the platform subscription plan from database.
    
    Args:
        session: Database session to use for the query
    
    Returns:
        SubscriptionPlan for Brikli Premium
        
    Raises:
        ValueError: If platform price not configured
    """
    result = await session.execute(
        select(SubscriptionPlan)
        .where(
            col(SubscriptionPlan.is_active) == True,
            col(SubscriptionPlan.currency) == "CAD"
        )
        .limit(1)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise ValueError(
            "Platform subscription plan not configured. "
            "Run billing setup to create the plan."
        )
    
    return plan


async def get_user_subscription(
    user_id: UUID,
    session: AsyncSession
) -> Optional[UserSubscription]:
    """
    Get user's active subscription.
    
    Prioritizes active/trialing subscriptions over canceled ones.
    Returns the most recent active subscription, or if none exist,
    the most recent subscription record.
    
    Args:
        user_id: User ID
        session: Database session
        
    Returns:
        UserSubscription or None if no subscription
    """
    # First, try to get an active or trialing subscription
    result = await session.execute(
        select(UserSubscription)
        .where(
            col(UserSubscription.user_id) == user_id,
            col(UserSubscription.status).in_(['active', 'trialing'])
        )
        .order_by(col(UserSubscription.created_at).desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()
    
    # If no active subscription, fall back to most recent (for historical data)
    if not subscription:
        result = await session.execute(
            select(UserSubscription)
            .where(col(UserSubscription.user_id) == user_id)
            .order_by(col(UserSubscription.created_at).desc())
            .limit(1)
        )
        subscription = result.scalar_one_or_none()
    
    return subscription


def calculate_days_left_in_trial(trial_end: Optional[datetime]) -> Optional[int]:
    """
    Calculate days remaining in trial period.
    
    Args:
        trial_end: Trial end datetime (timezone-aware)
        
    Returns:
        Number of days left, or None if not in trial
    """
    if not trial_end:
        return None
    
    now = datetime.now(timezone.utc)
    
    # Ensure trial_end is timezone-aware
    if trial_end.tzinfo is None:
        trial_end = trial_end.replace(tzinfo=timezone.utc)
    
    if trial_end <= now:
        return 0
    
    delta = trial_end - now
    return max(0, delta.days)


def is_subscription_active(subscription: Optional[UserSubscription]) -> bool:
    """
    Check if subscription grants access.
    
    Active states:
    - active: Subscription is paid and active
    - trialing: In trial period
    
    Args:
        subscription: UserSubscription or None
        
    Returns:
        True if subscription grants access, False otherwise
    """
    if not subscription:
        return False
    
    return subscription.status in ['active', 'trialing']


async def sync_subscription_from_stripe(
    stripe_subscription_id: str,
    session: AsyncSession,
    stripe_sub_data: dict | None = None
) -> UserSubscription:
    """
    Fetch subscription from Stripe and sync to database.
    
    Used for:
    - Initial subscription creation
    - Manual sync/refresh
    - Webhook processing
    
    Args:
        stripe_subscription_id: Stripe subscription ID (sub_xxx)
        session: Database session
        stripe_sub_data: Optional pre-fetched subscription data (from webhook events)
        
    Returns:
        Updated UserSubscription
        
    Raises:
        ValueError: If subscription not found or user not found
    """
    try:
        # Use provided data or fetch from Stripe
        if stripe_sub_data:
            # Data already provided (from webhook), use it directly
            stripe_sub = stripe_sub_data
        else:
            # Fetch from Stripe API
            stripe_client = get_stripe_client()
            stripe_sub_obj = await stripe_client.subscriptions.retrieve(stripe_subscription_id)
            
            # Convert to dict for consistent access
            stripe_sub = dict(stripe_sub_obj)
        
        # Find user by customer ID
        user_result = await session.execute(
            select(User).where(col(User.stripe_customer_id) == stripe_sub['customer'])
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User not found for Stripe customer {stripe_sub['customer']}")
        
        # Find plan by price ID
        # Access the price ID from the subscription items
        subscription_items = stripe_sub['items']['data']
        if not subscription_items:
            raise ValueError(f"No subscription items found for subscription {stripe_subscription_id}")
        
        price_id = subscription_items[0]['price']['id']
        
        plan_result = await session.execute(
            select(SubscriptionPlan).where(
                col(SubscriptionPlan.stripe_price_id) == price_id
            )
        )
        plan = plan_result.scalar_one_or_none()
        
        if not plan:
            raise ValueError(f"Plan not found for Stripe price {price_id}")
        
        # Check if subscription exists in DB
        subscription_result = await session.execute(
            select(UserSubscription).where(
                col(UserSubscription.stripe_subscription_id) == stripe_subscription_id
            )
        )
        existing_subscription = subscription_result.scalar_one_or_none()
        
        # Build metadata dict from Stripe
        metadata_dict: dict = dict(stripe_sub['metadata']) if stripe_sub.get('metadata') else {}
        
        # Create or update subscription
        if not existing_subscription:
            # Safe access for period dates (fallback for trial-only payloads)
            start_ts = stripe_sub.get('current_period_start') or stripe_sub.get('trial_start') or stripe_sub.get('created')
            end_ts = stripe_sub.get('current_period_end') or stripe_sub.get('trial_end')
            
            if not start_ts or not end_ts:
                # Should not happen for valid subscriptions, but log if it does
                raise ValueError(f"Missing period dates for subscription {stripe_sub['id']}")

            new_subscription = UserSubscription(
                user_id=user.id,
                plan_id=plan.id,
                stripe_customer_id=stripe_sub['customer'],
                stripe_subscription_id=stripe_sub['id'],
                status=stripe_sub['status'],
                current_period_start=datetime.fromtimestamp(start_ts, tz=timezone.utc),
                current_period_end=datetime.fromtimestamp(end_ts, tz=timezone.utc),
                trial_start=datetime.fromtimestamp(stripe_sub['trial_start'], tz=timezone.utc) if stripe_sub.get('trial_start') else None,
                trial_end=datetime.fromtimestamp(stripe_sub['trial_end'], tz=timezone.utc) if stripe_sub.get('trial_end') else None,
                cancel_at_period_end=stripe_sub['cancel_at_period_end'],
                canceled_at=datetime.fromtimestamp(stripe_sub['canceled_at'], tz=timezone.utc) if stripe_sub.get('canceled_at') else None,
                ended_at=datetime.fromtimestamp(stripe_sub['ended_at'], tz=timezone.utc) if stripe_sub.get('ended_at') else None,
                subscription_metadata=metadata_dict
            )
            session.add(new_subscription)
            await session.commit()
            await session.refresh(new_subscription)
            
            logger.info(
                f"Created new subscription from Stripe | "
                f"sub_id={new_subscription.id} | "
                f"status={new_subscription.status}"
            )
            
            return new_subscription
        else:
            # Safe access for period dates (fallback for trial-only payloads)
            start_ts = stripe_sub.get('current_period_start') or stripe_sub.get('trial_start') or stripe_sub.get('created')
            end_ts = stripe_sub.get('current_period_end') or stripe_sub.get('trial_end')

            # Update existing subscription (type narrowing: we know it's not None here)
            updated_subscription: UserSubscription = existing_subscription
            updated_subscription.status = stripe_sub['status']
            updated_subscription.current_period_start = datetime.fromtimestamp(start_ts, tz=timezone.utc) if start_ts else updated_subscription.current_period_start
            updated_subscription.current_period_end = datetime.fromtimestamp(end_ts, tz=timezone.utc) if end_ts else updated_subscription.current_period_end
            updated_subscription.trial_start = datetime.fromtimestamp(stripe_sub['trial_start'], tz=timezone.utc) if stripe_sub.get('trial_start') else None
            updated_subscription.trial_end = datetime.fromtimestamp(stripe_sub['trial_end'], tz=timezone.utc) if stripe_sub.get('trial_end') else None
            updated_subscription.cancel_at_period_end = stripe_sub['cancel_at_period_end']
            updated_subscription.canceled_at = datetime.fromtimestamp(stripe_sub['canceled_at'], tz=timezone.utc) if stripe_sub.get('canceled_at') else None
            updated_subscription.ended_at = datetime.fromtimestamp(stripe_sub['ended_at'], tz=timezone.utc) if stripe_sub.get('ended_at') else None
            updated_subscription.subscription_metadata = metadata_dict
            
            session.add(updated_subscription)
            await session.commit()
            await session.refresh(updated_subscription)
            
            logger.info(
                f"Updated subscription from Stripe | "
                f"sub_id={updated_subscription.id} | "
                f"status={updated_subscription.status}"
            )
            
            return updated_subscription
        
    except Exception as e:
        logger.error(f"Failed to sync subscription {stripe_subscription_id}: {e}")
        raise

