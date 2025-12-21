"""
Stripe Subscription Service for Tenant Portal Seats

Handles Stripe Checkout creation for $3/seat/month recurring subscriptions.
Integrates with existing billing infrastructure.
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col
from fastapi import HTTPException

from Backend.models.tenant_portal_seat_subscription import TenantPortalSeatSubscription
from Backend.api.billing.helpers import get_or_create_stripe_customer
from Backend.api.stripe.client import get_stripe_client
from Backend.models.user import User
# Stripe Price ID for $3/seat/month (created in Stripe Dashboard)
# Product: "Tenant Portal Seat" - $3.00/month recurring
# Created: 2024-12-20
TENANT_PORTAL_SEAT_PRICE_ID = "price_1SgKUWKoVREUyxXN7a1RR2Lr"


class SeatSubscriptionService:
    """Service for managing Stripe subscriptions for tenant portal seats"""

    @staticmethod
    async def create_subscription_checkout(
        landlord_user_id: UUID,
        quantity: int,
        success_url: str,
        cancel_url: str,
        session: AsyncSession
    ) -> dict:
        """
        Create Stripe Checkout session for seat subscription.

        Flow:
        1. Get or create Stripe customer (from existing billing infrastructure)
        2. Create Checkout session for recurring subscription
        3. User completes payment in Stripe
        4. Webhook handles subscription creation and updates seat limit
        """
        # Get or create Stripe customer (reuse existing billing infrastructure

        # Fetch user object
        user = await session.get(User, landlord_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        customer_id = await get_or_create_stripe_customer(user, session)

        # Create Checkout session for subscription
        stripe_client = get_stripe_client()

        checkout_session = await stripe_client.checkout_sessions.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{
                "price": TENANT_PORTAL_SEAT_PRICE_ID,  # $3/seat/month recurring price
                "quantity": quantity
            }],
            metadata={
                "landlord_user_id": str(landlord_user_id),
                "product_type": "tenant_portal_seat_subscription"  # Used in webhook routing
            },
            success_url=success_url,
            cancel_url=cancel_url,
            subscription_data={
                "metadata": {
                    "landlord_user_id": str(landlord_user_id),
                    "product_type": "tenant_portal_seat_subscription"
                }
            },
            allow_promotion_codes=True
        )

        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        }

    @staticmethod
    async def update_subscription_quantity(
        landlord_user_id: UUID,
        new_quantity: int,
        session: AsyncSession
    ) -> None:
        """
        Update existing seat subscription quantity.

        Allows landlords to scale up/down their seat count.
        Stripe handles prorated billing automatically.
        """
        # Get active subscription
        sub_query = select(TenantPortalSeatSubscription).where(
            col(TenantPortalSeatSubscription.landlord_user_id) == landlord_user_id,
            col(TenantPortalSeatSubscription.status) == "active"
        )
        subscription = await session.scalar(sub_query)

        if not subscription:
            raise HTTPException(
                status_code=404,
                detail="No active seat subscription found"
            )

        # Get subscription item ID from Stripe using async client
        stripe_client = get_stripe_client()
        stripe_sub = await stripe_client.subscriptions.retrieve(
            subscription.stripe_subscription_id
        )

        if not stripe_sub.items.data:
            raise HTTPException(
                status_code=500,
                detail="Subscription has no items"
            )

        # Update quantity (Stripe handles proration)
        await stripe_client.subscriptions.modify(
            subscription.stripe_subscription_id,
            items=[{
                "id": stripe_sub.items.data[0].id,
                "quantity": new_quantity
            }],
            proration_behavior="always_invoice"  # Bill immediately for changes
        )

        # Local record will be updated via webhook (customer.subscription.updated)

    @staticmethod
    async def cancel_subscription(
        landlord_user_id: UUID,
        session: AsyncSession,
        immediately: bool = False
    ) -> None:
        """
        Cancel seat subscription.

        Args:
            immediately: If True, cancel now. If False, cancel at period end.
        """
        # Get active subscription
        sub_query = select(TenantPortalSeatSubscription).where(
            col(TenantPortalSeatSubscription.landlord_user_id) == landlord_user_id,
            col(TenantPortalSeatSubscription.status) == "active"
        )
        subscription = await session.scalar(sub_query)

        if not subscription:
            raise HTTPException(
                status_code=404,
                detail="No active seat subscription found"
            )

        stripe_client = get_stripe_client()

        if immediately:
            # Cancel immediately
            await stripe_client.subscriptions.cancel(
                subscription.stripe_subscription_id
            )
        else:
            # Cancel at period end (default)
            await stripe_client.subscriptions.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )

        # Local record will be updated via webhook
