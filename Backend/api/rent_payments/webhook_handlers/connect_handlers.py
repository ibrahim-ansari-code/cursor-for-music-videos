"""Stripe Connect webhook event handlers"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from Backend.models.stripe_connected_account import StripeConnectedAccount
from Backend.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


async def handle_account_updated(
    account: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle Connect account updates (verification status, capabilities, etc.)."""
    account_id = account.get("id")
    
    if not account_id:
        return
    
    connected_account = await session.scalar(
        select(StripeConnectedAccount).where(
            col(StripeConnectedAccount.stripe_account_id) == account_id
        )
    )
    
    if not connected_account:
        logger.warning(f"No connected account found for {account_id}")
        return
    
    # Update status fields
    charges_enabled = account.get("charges_enabled", False)
    payouts_enabled = account.get("payouts_enabled", False)
    details_submitted = account.get("details_submitted", False)
    
    # Check if just became fully onboarded
    was_onboarded = connected_account.is_fully_onboarded
    
    connected_account.charges_enabled = charges_enabled
    connected_account.payouts_enabled = payouts_enabled
    connected_account.details_submitted = details_submitted
    connected_account.business_type = account.get("business_type")
    
    # Extract requirements and restrictions
    requirements = account.get("requirements", {})
    connected_account.requirements_currently_due = requirements.get("currently_due", [])
    connected_account.requirements_past_due = requirements.get("past_due", [])
    connected_account.requirements_eventually_due = requirements.get("eventually_due", [])
    connected_account.disabled_reason = requirements.get("disabled_reason")
    
    # Mark onboarding complete if charges just became enabled
    if charges_enabled and not was_onboarded and not connected_account.onboarding_completed_at:
        connected_account.onboarding_completed_at = utc_now()
        logger.info(f"Connect onboarding completed | account_id={account_id}")
    
    connected_account.updated_at = utc_now()
    
    session.add(connected_account)
    await session.commit()
    
    # Log requirements if any are needed
    if connected_account.needs_action:
        logger.warning(
            f"Connect account needs action | "
            f"account_id={account_id} | "
            f"currently_due={len(connected_account.requirements_currently_due)} | "
            f"past_due={len(connected_account.requirements_past_due)} | "
            f"disabled_reason={connected_account.disabled_reason}"
        )
    
    logger.info(
        f"Connect account updated | "
        f"account_id={account_id} | "
        f"charges_enabled={charges_enabled} | "
        f"payouts_enabled={payouts_enabled}"
    )

