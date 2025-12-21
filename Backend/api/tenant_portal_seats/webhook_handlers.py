"""
Webhook Handlers for Tenant Portal Seat Subscriptions

Handles Stripe subscription events (created, updated, deleted) and updates
the user's seat limit accordingly.

Integration Point: Called from Backend/api/billing/router.py webhook handler.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlmodel import select, col

from Backend.models.tenant_portal_seat_subscription import TenantPortalSeatSubscription
from Backend.api.tenant_portal_seats.service import SeatManagementService

logger = logging.getLogger(__name__)


async def handle_seat_subscription_created(
    subscription: dict,  # Webhook data comes as dict, not Stripe object
    session: AsyncSession
) -> None:
    """
    Handle new seat subscription creation (customer.subscription.created).

    Flow:
    1. Webhook fires when Stripe Checkout completes
    2. Create local subscription record
    3. Update user's seat limit (2 free + quantity)
    4. Landlord can now invite more tenants
    """
    metadata = subscription.get("metadata", {})

    # Verify this is a seat subscription (not platform subscription)
    if metadata.get("product_type") != "tenant_portal_seat_subscription":
        return

    landlord_user_id = metadata.get("landlord_user_id")
    if not landlord_user_id:
        logger.error(f"Missing landlord_user_id in subscription {subscription['id']}")
        raise ValueError("Missing landlord_user_id in subscription metadata")

    # Extract subscription details
    items_data = subscription.get("items", {}).get("data", [])
    if not items_data:
        logger.error(f"Subscription {subscription['id']} has no items")
        raise ValueError("Subscription has no items")

    quantity = items_data[0]["quantity"]
    price_id = items_data[0]["price"]["id"]

    logger.info(
        f"Creating seat subscription record | "
        f"landlord={landlord_user_id} | "
        f"stripe_sub={subscription['id']} | "
        f"quantity={quantity}"
    )

    try:
        # Create local subscription record
        # Per Stripe API docs: current_period_start/end are at subscription level
        # Source: https://docs.stripe.com/api/subscriptions/object

        sub_id = subscription.get("id")
        status = subscription.get("status")

        # Get period dates from subscription level (where they actually live per Stripe docs)
        period_start = subscription.get("current_period_start")
        period_end = subscription.get("current_period_end")

        if period_start is None or period_end is None:
            logger.error(f"Cannot determine period dates for subscription {sub_id}")
            raise ValueError("Missing period dates in subscription data")

        seat_sub = TenantPortalSeatSubscription(
            landlord_user_id=landlord_user_id,
            stripe_subscription_id=sub_id,
            stripe_price_id=price_id,
            quantity=quantity,
            status=status,
            current_period_start=datetime.fromtimestamp(period_start, tz=timezone.utc),
            current_period_end=datetime.fromtimestamp(period_end, tz=timezone.utc)
        )
        session.add(seat_sub)
        await session.flush()  # Assigns ID without committing

        # Update user's seat limit (2 free + purchased)
        await SeatManagementService.update_seat_limit_from_subscription(
            landlord_user_id=landlord_user_id,
            subscription=seat_sub,
            session=session
        )

        await session.commit()

        logger.info(
            f"Seat subscription created successfully | "
            f"landlord={landlord_user_id} | "
            f"new_limit={2 + quantity}"
        )

    except IntegrityError:
        # Subscription already exists (webhook replay) - idempotent success
        logger.warning(f"Subscription {subscription['id']} already exists (webhook replay)")
        await session.rollback()
        return


async def handle_seat_subscription_updated(
    subscription: dict,  # Webhook data comes as dict, not Stripe object
    session: AsyncSession
) -> None:
    """
    Handle seat subscription updates (customer.subscription.updated).

    Triggered when:
    - Quantity changed (landlord scales up/down)
    - Status changed (active → past_due, etc.)
    - Period renewed
    """
    # Find local subscription record
    sub_query = select(TenantPortalSeatSubscription).where(
        col(TenantPortalSeatSubscription.stripe_subscription_id) == subscription["id"]
    )
    seat_sub = await session.scalar(sub_query)

    if not seat_sub:
        # Subscription not found locally - create it (webhook out of order)
        logger.warning(
            f"Subscription {subscription['id']} not found locally, creating from update event"
        )
        await handle_seat_subscription_created(subscription, session)
        return

    # Extract updated details
    items_data = subscription.get("items", {}).get("data", [])
    if not items_data:
        logger.error(f"Subscription {subscription['id']} has no items")
        return

    quantity = items_data[0]["quantity"]

    logger.info(
        f"Updating seat subscription | "
        f"landlord={seat_sub.landlord_user_id} | "
        f"stripe_sub={subscription['id']} | "
        f"old_quantity={seat_sub.quantity} | "
        f"new_quantity={quantity} | "
        f"old_status={seat_sub.status} | "
        f"new_status={subscription['status']}"
    )

    # Update local record
    seat_sub.quantity = quantity
    status = subscription.get("status")
    seat_sub.status = status

    # Get period dates from subscription level (per Stripe API docs)
    period_start = subscription.get("current_period_start")
    period_end = subscription.get("current_period_end")

    if period_start and period_end:
        seat_sub.current_period_start = datetime.fromtimestamp(period_start, tz=timezone.utc)
        seat_sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

    seat_sub.updated_at = datetime.now(timezone.utc)
    session.add(seat_sub)

    # Update user's seat limit (only if subscription is active)
    if status == "active":
        await SeatManagementService.update_seat_limit_from_subscription(
            landlord_user_id=seat_sub.landlord_user_id,
            subscription=seat_sub,
            session=session
        )
    elif status in ("canceled", "past_due", "unpaid"):
        # Reset to free tier if subscription inactive
        logger.warning(
            f"Subscription {subscription.get('id') or subscription['id']} is {status}, "
            f"resetting landlord {seat_sub.landlord_user_id} to free tier"
        )
        await SeatManagementService.reset_seat_limit_to_free_tier(
            landlord_user_id=seat_sub.landlord_user_id,
            session=session
        )

    await session.commit()


async def handle_seat_subscription_deleted(
    subscription: dict,  # Webhook data comes as dict, not Stripe object
    session: AsyncSession
) -> None:
    """
    Handle seat subscription cancellation (customer.subscription.deleted).

    GitHub approach: Reset to free tier, but existing portal tenants keep access.
    Only NEW invitations will be blocked until subscription renewed.
    """
    # Find local subscription record
    sub_query = select(TenantPortalSeatSubscription).where(
        col(TenantPortalSeatSubscription.stripe_subscription_id) == subscription["id"]
    )
    seat_sub = await session.scalar(sub_query)

    if not seat_sub:
        logger.warning(f"Subscription {subscription['id']} not found for deletion")
        return

    logger.info(
        f"Deleting seat subscription | "
        f"landlord={seat_sub.landlord_user_id} | "
        f"stripe_sub={subscription['id']}"
    )

    # Update status to canceled
    seat_sub.status = "canceled"
    seat_sub.updated_at = datetime.now(timezone.utc)
    session.add(seat_sub)

    # Reset user's seat limit to free tier (2 seats)
    # GitHub-style: Existing portal tenants keep access, but can't invite more
    await SeatManagementService.reset_seat_limit_to_free_tier(
        landlord_user_id=seat_sub.landlord_user_id,
        session=session
    )

    await session.commit()

    logger.info(
        f"Seat subscription deleted | "
        f"landlord={seat_sub.landlord_user_id} | "
        f"reset to free tier (2 seats)"
    )
