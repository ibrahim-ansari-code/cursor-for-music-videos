"""Billing service - Business logic for subscription management"""
import logging
from typing import Optional
from uuid import UUID

import stripe
from stripe import StripeError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlmodel import col

from Backend.api.stripe.client import get_stripe_client
from Backend.config import settings
from Backend.models.user import User
from Backend.models.billing import SubscriptionPlan, UserSubscription
from Backend.api.billing.schemas import (
    SubscriptionStatusResponse,
    CheckoutSessionResponse,
    CustomerPortalResponse,
    SubscriptionPlanResponse,
)
from Backend.api.billing.helpers import (
    get_or_create_stripe_customer,
    get_platform_price,
    get_user_subscription,
    calculate_days_left_in_trial,
    is_subscription_active,
    sync_subscription_from_stripe,
)

logger = logging.getLogger(__name__)


class BillingService:
    """Service layer for billing operations"""
    
    @staticmethod
    async def get_subscription_plans(session: AsyncSession) -> list[SubscriptionPlanResponse]:
        """
        Get available active subscription plans.
        """
        result = await session.execute(
            select(SubscriptionPlan)
            .where(col(SubscriptionPlan.is_active).is_(True))
            .order_by(col(SubscriptionPlan.amount))
        )
        plans = result.scalars().all()
        return [SubscriptionPlanResponse.model_validate(plan) for plan in plans]

    @staticmethod
    async def get_subscription_status(
        user: User,
        session: AsyncSession
    ) -> SubscriptionStatusResponse:
        """
        Get user's current subscription status.
        
        Returns comprehensive status including:
        - Subscription state
        - Trial information
        - Cancellation status
        - Plan details
        
        Args:
            user: Current user
            session: Database session
            
        Returns:
            SubscriptionStatusResponse with all subscription details
        """
        # Get user's subscription
        subscription = await get_user_subscription(user.id, session)
        
        if not subscription:
            # No subscription - free tier
            return SubscriptionStatusResponse(
                has_active_subscription=False,
                subscription_status="none",
                subscription_tier="free"
            )
        
        # Get plan details
        result = await session.execute(
            select(SubscriptionPlan).where(col(SubscriptionPlan.id) == subscription.plan_id)
        )
        plan = result.scalar_one_or_none()
        
        # Calculate trial days remaining
        days_left = None
        is_trialing = subscription.status == 'trialing'
        if is_trialing and subscription.trial_end:
            days_left = calculate_days_left_in_trial(subscription.trial_end)
        
        return SubscriptionStatusResponse(
            has_active_subscription=is_subscription_active(subscription),
            subscription_status=subscription.status,
            subscription_tier="premium" if is_subscription_active(subscription) else "free",
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            trial_active=is_trialing,
            trial_ends_at=subscription.trial_end,
            trial_days_remaining=days_left,
            cancel_at_period_end=subscription.cancel_at_period_end,
            canceled_at=subscription.canceled_at,
            subscription_details=SubscriptionPlanResponse.model_validate(plan) if plan else None
        )
    
    @staticmethod
    async def create_checkout_session(
        user: User,
        success_url: Optional[str],
        cancel_url: Optional[str],
        session: AsyncSession
    ) -> CheckoutSessionResponse:
        """
        Create Stripe Checkout Session for subscription.
        
        Flow:
        1. Check for existing active subscriptions (prevent duplicates)
        2. Get/create Stripe customer for user
        3. Get platform price
        4. Create Checkout Session with 14-day trial
        5. Return checkout URL
        
        Args:
            user: Current user
            success_url: URL to redirect after successful checkout
            cancel_url: URL to redirect if user cancels
            session: Database session
            
        Returns:
            CheckoutSessionResponse with checkout URL
            
        Raises:
            ValueError: If price not configured or user already has active subscription
            StripeError: If Stripe API fails
        """
        try:
            # DUPLICATE PREVENTION: Check if user already has an active subscription
            existing_sub = await get_user_subscription(user.id, session)
            if existing_sub and is_subscription_active(existing_sub):
                logger.warning(
                    f"User {user.id} attempted to create duplicate subscription | "
                    f"existing_sub={existing_sub.id} | status={existing_sub.status}"
                )
                raise ValueError(
                    "You already have an active subscription. "
                    "Please manage your existing subscription in the billing portal."
                )
            
            # Get or create Stripe customer
            customer_id = await get_or_create_stripe_customer(user, session)
            
            # Get platform price
            plan = await get_platform_price(session)
            
            # Default URLs
            if not success_url:
                success_url = f"{settings.FRONTEND_URL}/settings?tab=billing&success=true"
            if not cancel_url:
                cancel_url = f"{settings.FRONTEND_URL}/settings?tab=billing&canceled=true"
            
            # Create Checkout Session
            stripe_client = get_stripe_client()
            checkout_session = await stripe_client.checkout_sessions.create(
                customer=customer_id,
                mode='subscription',
                line_items=[{
                    'price': plan.stripe_price_id,
                    'quantity': 1,
                }],
                subscription_data={
                    'trial_period_days': plan.trial_period_days or 14,
                    'metadata': {
                        'user_id': str(user.id),
                        'plan_id': str(plan.id),
                    }
                },
                success_url=success_url,
                cancel_url=cancel_url,
                allow_promotion_codes=True,  # Enable promo codes
                billing_address_collection='required',  # Collect billing address
                metadata={
                    'user_id': str(user.id),
                    'user_email': user.email,
                }
            )
            
            logger.info(
                f"Created checkout session | "
                f"user_id={user.id} | "
                f"session_id={checkout_session.id}"
            )
            
            return CheckoutSessionResponse(
                checkout_url=checkout_session.url,
                session_id=checkout_session.id
            )
            
        except StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise
    
    @staticmethod
    async def create_customer_portal_session(
        user: User,
        return_url: Optional[str],
        session: AsyncSession
    ) -> CustomerPortalResponse:
        """
        Create Stripe Customer Portal session for subscription management.
        
        The Customer Portal allows users to:
        - View invoices and payment history
        - Update payment methods
        - Cancel subscription
        - Update billing details
        
        Args:
            user: Current user
            return_url: URL to return to after portal session
            session: Database session
            
        Returns:
            CustomerPortalResponse with portal URL
            
        Raises:
            ValueError: If user has no Stripe customer ID
            StripeError: If Stripe API fails
        """
        try:
            # Ensure user has Stripe customer ID
            if not user.stripe_customer_id:
                customer_id = await get_or_create_stripe_customer(user, session)
            else:
                customer_id = user.stripe_customer_id
            
            # Default return URL
            if not return_url:
                return_url = f"{settings.FRONTEND_URL}/settings?tab=billing"
            
            # Create portal session
            stripe_client = get_stripe_client()
            portal_session = await stripe_client.billing_portal_sessions.create(
                customer=customer_id,
                return_url=return_url
            )
            
            logger.info(
                f"Created portal session | "
                f"user_id={user.id} | "
                f"customer_id={customer_id}"
            )
            
            return CustomerPortalResponse(
                portal_url=portal_session.url
            )
            
        except StripeError as e:
            logger.error(f"Stripe error creating portal session: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating portal session: {e}")
            raise
    
    @staticmethod
    async def cancel_subscription(
        user: User,
        session: AsyncSession,
        immediately: bool = False
    ) -> SubscriptionStatusResponse:
        """
        Cancel user's subscription.
        
        Args:
            user: Current user
            session: Database session
            immediately: If True, cancel immediately. If False, cancel at period end.
            
        Returns:
            Updated SubscriptionStatusResponse
            
        Raises:
            ValueError: If user has no subscription
            StripeError: If Stripe API fails
        """
        subscription = await get_user_subscription(user.id, session)
        
        if not subscription:
            raise ValueError("No active subscription to cancel")
        
        try:
            stripe_client = get_stripe_client()
            if immediately:
                # Cancel immediately
                await stripe_client.subscriptions.cancel(subscription.stripe_subscription_id)
                logger.info(f"Immediately canceled subscription | sub_id={subscription.id}")
            else:
                # Cancel at period end (user retains access)
                await stripe_client.subscriptions.update(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                logger.info(f"Scheduled cancellation | sub_id={subscription.id}")
            
            # Sync from Stripe to get the latest state immediately
            await sync_subscription_from_stripe(subscription.stripe_subscription_id, session)
            
            # Return the updated status from our database
            return await BillingService.get_subscription_status(user, session)
            
        except StripeError as e:
            logger.error(f"Stripe error canceling subscription: {e}")
            raise
        except Exception as e:
            logger.error(f"Error canceling subscription: {e}")
            raise
    
    @staticmethod
    async def resume_subscription(
        user: User,
        session: AsyncSession
    ) -> SubscriptionStatusResponse:
        """
        Resume a subscription that was canceled but hasn't ended yet.
        
        Args:
            user: Current user
            session: Database session
            
        Returns:
            Updated SubscriptionStatusResponse
            
        Raises:
            ValueError: If user has no subscription or can't resume
            StripeError: If Stripe API fails
        """
        subscription = await get_user_subscription(user.id, session)
        
        if not subscription:
            raise ValueError("No subscription found")
        
        if not subscription.cancel_at_period_end:
            raise ValueError("Subscription is not scheduled for cancellation")
        
        try:
            # Remove cancellation
            stripe_client = get_stripe_client()
            await stripe_client.subscriptions.update(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False
            )
            
            logger.info(f"Resumed subscription | sub_id={subscription.id}")
            
            # Sync from Stripe to get the latest state immediately
            await sync_subscription_from_stripe(subscription.stripe_subscription_id, session)
            
            # Return the updated status from our database
            return await BillingService.get_subscription_status(user, session)
            
        except StripeError as e:
            logger.error(f"Stripe error resuming subscription: {e}")
            raise
        except Exception as e:
            logger.error(f"Error resuming subscription: {e}")
            raise

