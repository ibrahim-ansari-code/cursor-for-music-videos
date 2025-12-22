"""
Stripe Connect Service

Handles landlord onboarding to Stripe Connect Express accounts.
Landlords use these accounts to receive rent payments directly from tenants.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select
import stripe

from Backend.api.stripe.client import get_stripe_client
from Backend.config import settings
from Backend.models.stripe_connected_account import StripeConnectedAccount
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.utils.datetime_utils import utc_now

from .constants import (
    CONNECT_ACCOUNT_TYPE,
    CONNECT_DEFAULT_COUNTRY,
    CONNECT_CAPABILITIES,
)
from .schemas import (
    ConnectOnboardingResponse,
    ConnectRefreshLinkResponse,
    ConnectDashboardLinkResponse,
    ConnectStatusResponse,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Account Creation
# =============================================================================

async def create_connected_account(
    user: User,
    session: AsyncSession,
) -> ConnectOnboardingResponse:
    """
    Create a Stripe Express account for a landlord and return onboarding link.
    
    This initiates the Connect onboarding flow. The landlord will be redirected
    to Stripe to complete identity verification and bank account setup.
    
    Args:
        user: The landlord user
        session: Database session
        
    Returns:
        ConnectOnboardingResponse with account ID and onboarding URL
        
    Raises:
        HTTPException: If user is not a landlord or already has an account
    """
    # Validate user is a landlord
    if user.user_type != UserType.LANDLORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only landlords can set up payment accounts"
        )
    
    # Check if account already exists
    existing = await session.scalar(
        select(StripeConnectedAccount).where(
            col(StripeConnectedAccount.user_id) == user.id
        )
    )
    
    if existing:
        # Account exists - return new onboarding link if not complete
        if existing.is_fully_onboarded:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment account is already set up and active"
            )
        
        # Generate new link for incomplete account
        return await _create_account_link(existing, session)
    
    # Create new Express account
    try:
        stripe_client = get_stripe_client()
        
        # Build account creation params
        account_params: dict[str, object] = {
            "type": CONNECT_ACCOUNT_TYPE,
            "country": CONNECT_DEFAULT_COUNTRY,
            "email": user.email,
            "capabilities": CONNECT_CAPABILITIES,
            "metadata": {
                "user_id": str(user.id),
                "platform": "brikli",
            },
        }
        
        # Only include business_profile URL if it's a valid public URL
        # Stripe rejects localhost URLs
        business_profile: dict[str, str] = {
            "mcc": "6513",  # Real estate agents and managers - rent
        }
        frontend_url = settings.FRONTEND_URL
        if frontend_url and frontend_url.startswith("https://") and "localhost" not in frontend_url:
            business_profile["url"] = frontend_url
        
        account_params["business_profile"] = business_profile
        
        # Prefill info if available
        if user.first_name or user.last_name:
            individual: dict[str, str] = {}
            if user.first_name:
                individual["first_name"] = user.first_name
            if user.last_name:
                individual["last_name"] = user.last_name
            if user.email:
                individual["email"] = user.email
            account_params["individual"] = individual
            # Stripe requires business_type when individual params are provided
            account_params["business_type"] = "individual"
        
        # Create account via Stripe
        account = await stripe_client.accounts.create(**account_params)
        
        logger.info(
            f"Created Stripe Connect account | "
            f"user_id={user.id} | "
            f"account_id={account.id}"
        )
        
        # Save to database
        connected_account = StripeConnectedAccount(
            user_id=user.id,
            stripe_account_id=account.id,
            country=CONNECT_DEFAULT_COUNTRY,
            default_currency="cad",
        )
        
        session.add(connected_account)
        await session.commit()
        await session.refresh(connected_account)
        
        # Generate onboarding link
        return await _create_account_link(connected_account, session)
        
    except stripe.StripeError as e:
        logger.error(f"Stripe error creating Connect account: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create payment account. Please try again."
        )


async def _create_account_link(
    connected_account: StripeConnectedAccount,
    session: AsyncSession,
) -> ConnectOnboardingResponse:
    """
    Generate an Account Link for Connect onboarding.
    
    Args:
        connected_account: The database record
        session: Database session
        
    Returns:
        ConnectOnboardingResponse with onboarding URL
    """
    try:
        stripe_client = get_stripe_client()
        
        # URLs for redirect after onboarding
        return_url = f"{settings.FRONTEND_URL}/settings?tab=payouts&status=success"
        refresh_url = f"{settings.FRONTEND_URL}/settings?tab=payouts&status=refresh"
        
        account_link = await stripe_client.account_links.create(
            account=connected_account.stripe_account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
            collect="eventually_due",  # Collect all requirements
        )
        
        # Account link expires after a short time (typically ~5 minutes)
        # Stripe doesn't return exact expiry, use 5 minutes as estimate
        from datetime import timedelta
        expires_at = utc_now() + timedelta(minutes=5)
        
        return ConnectOnboardingResponse(
            account_id=connected_account.stripe_account_id,
            onboarding_url=account_link.url,
            expires_at=expires_at,
        )
        
    except stripe.StripeError as e:
        logger.error(f"Stripe error creating account link: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate onboarding link. Please try again."
        )


# =============================================================================
# Account Status
# =============================================================================

async def get_connect_status(
    user: User,
    session: AsyncSession,
) -> ConnectStatusResponse:
    """
    Get the Connect account status for a landlord.
    
    Args:
        user: The landlord user
        session: Database session
        
    Returns:
        ConnectStatusResponse with account status details
    """
    # Get database record
    connected_account = await session.scalar(
        select(StripeConnectedAccount).where(
            col(StripeConnectedAccount.user_id) == user.id
        )
    )
    
    if not connected_account:
        return ConnectStatusResponse(
            is_connected=False,
            onboarding_status="not_started",
        )
    
    # Fetch latest status from Stripe
    try:
        stripe_client = get_stripe_client()
        account = await stripe_client.accounts.retrieve(
            connected_account.stripe_account_id
        )
        
        # Update our cache
        connected_account.charges_enabled = account.charges_enabled
        connected_account.payouts_enabled = account.payouts_enabled
        connected_account.details_submitted = account.details_submitted
        connected_account.business_type = account.business_type
        
        # Extract requirements and restrictions
        requirements = account.get("requirements", {})
        connected_account.requirements_currently_due = requirements.get("currently_due", [])
        connected_account.requirements_past_due = requirements.get("past_due", [])
        connected_account.requirements_eventually_due = requirements.get("eventually_due", [])
        connected_account.disabled_reason = requirements.get("disabled_reason")
        
        # Mark onboarding complete if charges enabled for first time
        if account.charges_enabled and not connected_account.onboarding_completed_at:
            connected_account.onboarding_completed_at = utc_now()
        
        connected_account.updated_at = utc_now()
        session.add(connected_account)
        await session.commit()
        
        return ConnectStatusResponse(
            is_connected=True,
            account_id=connected_account.stripe_account_id,
            charges_enabled=account.charges_enabled,
            payouts_enabled=account.payouts_enabled,
            details_submitted=account.details_submitted,
            onboarding_status=connected_account.onboarding_status,
            needs_action=connected_account.needs_action,
            disabled_reason=connected_account.disabled_reason,
            requirements_currently_due=connected_account.requirements_currently_due,
            requirements_past_due=connected_account.requirements_past_due,
            requirements_eventually_due=connected_account.requirements_eventually_due,
            business_type=account.business_type,
            country=connected_account.country,
            default_currency=connected_account.default_currency,
            accepted_payment_methods=connected_account.accepted_payment_methods or ["card", "acss_debit"],
        )

    except stripe.StripeError as e:
        logger.error(f"Stripe error fetching account status: {e}")
        # Return cached data on Stripe error
        return ConnectStatusResponse(
            is_connected=True,
            account_id=connected_account.stripe_account_id,
            charges_enabled=connected_account.charges_enabled,
            payouts_enabled=connected_account.payouts_enabled,
            details_submitted=connected_account.details_submitted,
            onboarding_status=connected_account.onboarding_status,
            needs_action=connected_account.needs_action,
            disabled_reason=connected_account.disabled_reason,
            requirements_currently_due=connected_account.requirements_currently_due,
            requirements_past_due=connected_account.requirements_past_due,
            requirements_eventually_due=connected_account.requirements_eventually_due,
            business_type=connected_account.business_type,
            country=connected_account.country,
            default_currency=connected_account.default_currency,
            accepted_payment_methods=connected_account.accepted_payment_methods or ["card", "acss_debit"],
        )


# =============================================================================
# Account Links
# =============================================================================

async def create_refresh_link(
    user: User,
    session: AsyncSession,
) -> ConnectRefreshLinkResponse:
    """
    Generate a new onboarding link for an existing incomplete account.
    
    Args:
        user: The landlord user
        session: Database session
        
    Returns:
        ConnectRefreshLinkResponse with new onboarding URL
    """
    connected_account = await session.scalar(
        select(StripeConnectedAccount).where(
            col(StripeConnectedAccount.user_id) == user.id
        )
    )
    
    if not connected_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No payment account found. Please start the setup process."
        )
    
    if connected_account.is_fully_onboarded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is already fully set up."
        )
    
    response = await _create_account_link(connected_account, session)
    
    return ConnectRefreshLinkResponse(
        onboarding_url=response.onboarding_url,
        expires_at=response.expires_at,
    )


async def create_dashboard_link(
    user: User,
    session: AsyncSession,
) -> ConnectDashboardLinkResponse:
    """
    Generate a login link to the Stripe Express Dashboard.
    
    Allows landlords to view their payout schedule, update bank info, etc.
    
    Args:
        user: The landlord user
        session: Database session
        
    Returns:
        ConnectDashboardLinkResponse with dashboard URL
    """
    connected_account = await session.scalar(
        select(StripeConnectedAccount).where(
            col(StripeConnectedAccount.user_id) == user.id
        )
    )
    
    if not connected_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No payment account found."
        )
    
    try:
        stripe_client = get_stripe_client()
        
        login_link = await stripe_client.accounts.create_login_link(
            connected_account.stripe_account_id
        )
        
        # Login links expire after a short time
        from datetime import timedelta
        expires_at = utc_now() + timedelta(minutes=5)
        
        return ConnectDashboardLinkResponse(
            dashboard_url=login_link.url,
            expires_at=expires_at,
        )
        
    except stripe.StripeError as e:
        logger.error(f"Stripe error creating login link: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate dashboard link. Please try again."
        )


# =============================================================================
# Internal Helpers
# =============================================================================

async def get_connected_account_for_landlord(
    landlord_user_id: str,
    session: AsyncSession,
) -> StripeConnectedAccount | None:
    """
    Get the Connect account for a landlord by their user ID.
    
    Used internally when processing payments.
    
    Args:
        landlord_user_id: The landlord's user UUID
        session: Database session
        
    Returns:
        StripeConnectedAccount or None if not found
    """
    from uuid import UUID
    return await session.scalar(
        select(StripeConnectedAccount).where(
            col(StripeConnectedAccount.user_id) == UUID(landlord_user_id)
        )
    )


async def landlord_can_accept_payments(
    landlord_user_id: str,
    session: AsyncSession,
) -> bool:
    """
    Check if a landlord can accept online payments.

    Args:
        landlord_user_id: The landlord's user UUID
        session: Database session

    Returns:
        True if landlord has a fully onboarded Connect account
    """
    account = await get_connected_account_for_landlord(landlord_user_id, session)
    return account is not None and account.is_fully_onboarded


async def update_payment_preferences(
    user: "User",
    accepted_payment_methods: list[str],
    session: AsyncSession,
) -> StripeConnectedAccount:
    """
    Update a landlord's payment method preferences.

    Args:
        user: The landlord user
        accepted_payment_methods: List of payment methods to accept ('card', 'acss_debit')
        session: Database session

    Returns:
        Updated StripeConnectedAccount

    Raises:
        HTTPException: If no connected account found
    """
    from Backend.utils.datetime_utils import utc_now

    account = await get_connected_account_for_landlord(str(user.id), session)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No connected account found. Please complete Stripe onboarding first."
        )

    account.accepted_payment_methods = accepted_payment_methods
    account.updated_at = utc_now()

    session.add(account)
    await session.commit()
    await session.refresh(account)

    logger.info(
        f"Updated payment preferences | "
        f"user_id={user.id} | "
        f"accepted_methods={accepted_payment_methods}"
    )

    return account
