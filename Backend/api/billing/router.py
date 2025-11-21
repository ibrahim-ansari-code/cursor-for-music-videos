"""Billing API Router"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.database import get_session
from Backend.models.user import User
from Backend.api.auth.dependencies import get_current_user, get_current_user_no_subscription_check
from Backend.api.billing.schemas import (
    SubscriptionStatusResponse,
    CheckoutSessionResponse,
    CustomerPortalResponse,
    CreateCheckoutSessionRequest,
    CreateCustomerPortalRequest,
    SubscriptionPlanResponse,
)
from Backend.api.billing.service import BillingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[SubscriptionPlanResponse])
async def get_subscription_plans(
    current_user: User = Depends(get_current_user_no_subscription_check),
    session: AsyncSession = Depends(get_session)
):
    """
    Get available subscription plans.
    """
    try:
        return await BillingService.get_subscription_plans(session)
    except Exception as e:
        logger.error(f"Error getting subscription plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription plans"
        )


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: User = Depends(get_current_user_no_subscription_check),
    session: AsyncSession = Depends(get_session)
):
    """
    Get current user's subscription status.
    
    Returns comprehensive subscription information including:
    - Subscription state (active, trialing, canceled, etc.)
    - Trial information and days remaining
    - Current billing period
    - Plan details
    
    Used by:
    - Settings/Billing tab to display current status
    - Subscription guards to check access
    - UI components to show trial banners
    """
    try:
        return await BillingService.get_subscription_status(current_user, session)
    except Exception as e:
        logger.error(f"Error getting subscription status for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription status"
        )


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    current_user: User = Depends(get_current_user_no_subscription_check),
    session: AsyncSession = Depends(get_session)
):
    """
    Create Stripe Checkout Session for subscription purchase.
    
    Initiates the subscription flow:
    1. Creates/retrieves Stripe customer
    2. Generates Checkout Session with 14-day trial
    3. Returns checkout URL for frontend redirect
    
    Frontend should redirect user to checkout_url.
    After successful checkout, Stripe redirects to success_url.
    
    Trial: First 14 days are free, then $99.99 CAD/month
    """
    try:
        return await BillingService.create_checkout_session(
            user=current_user,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            session=session
        )
    except ValueError as e:
        logger.warning(f"Invalid checkout request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating checkout session for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )


@router.post("/customer-portal", response_model=CustomerPortalResponse)
async def create_customer_portal_session(
    request: CreateCustomerPortalRequest,
    current_user: User = Depends(get_current_user_no_subscription_check),
    session: AsyncSession = Depends(get_session)
):
    """
    Create Stripe Customer Portal session for subscription management.
    
    The Customer Portal allows users to:
    - View invoices and payment history
    - Update payment methods
    - Cancel subscription
    - Download receipts
    - Update billing address
    
    Frontend should redirect user to portal_url.
    After portal session, Stripe redirects to return_url.
    """
    try:
        return await BillingService.create_customer_portal_session(
            user=current_user,
            return_url=request.return_url,
            session=session
        )
    except ValueError as e:
        logger.warning(f"Invalid portal request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating portal session for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create customer portal session"
        )


@router.post("/cancel", response_model=SubscriptionStatusResponse)
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Cancel subscription at period end.
    
    User retains access until the end of their current billing period.
    Can be resumed before period end using /resume endpoint.
    """
    try:
        return await BillingService.cancel_subscription(
            user=current_user,
            session=session,
            immediately=False
        )
    except ValueError as e:
        logger.warning(f"Invalid cancel request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error canceling subscription for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )


@router.post("/resume", response_model=SubscriptionStatusResponse)
async def resume_subscription(
    current_user: User = Depends(get_current_user_no_subscription_check),
    session: AsyncSession = Depends(get_session)
):
    """
    Resume a canceled subscription before it ends.
    
    Only works if subscription is scheduled for cancellation
    but hasn't ended yet (cancel_at_period_end = true).
    """
    try:
        return await BillingService.resume_subscription(
            user=current_user,
            session=session
        )
    except ValueError as e:
        logger.warning(f"Invalid resume request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error resuming subscription for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume subscription"
        )

