"""
Seat Management Service

GitHub-style seat management with real-time counting:
- Seats used = COUNT(tenants WHERE user_id IS NOT NULL) - calculated on every call
- No separate counter to increment/decrement
- Impossible for counts to drift out of sync
- Transaction-safe with PostgreSQL isolation
"""
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col
from fastapi import HTTPException

from Backend.models.user import User
from Backend.models.tenant import Tenant
from Backend.models.tenant_portal_seat_subscription import TenantPortalSeatSubscription

# Pricing: $3/seat/month
SEAT_PRICE_CENTS = 300  # $3.00
FREE_SEATS_WITH_SUBSCRIPTION = 2


class SeatManagementService:
    """Service for managing tenant portal seats with GitHub-style real-time counting"""

    @staticmethod
    async def get_seat_availability(landlord_user_id: UUID, session: AsyncSession) -> dict:
        """
        Get current seat usage for a landlord.

        Uses real-time counting (no cached counters):
        - limit: From users.tenant_portal_seat_limit
        - used: COUNT(tenants WHERE landlord_id = X AND user_id IS NOT NULL)
        - available: limit - used

        This is the GitHub approach - always accurate, no drift possible.
        """
        user = await session.get(User, landlord_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Real-time count of active portal tenants (GitHub-style)
        used_seats_query = select(func.count()).select_from(Tenant).where(
            col(Tenant.landlord_id) == landlord_user_id,
            col(Tenant.user_id).is_not(None)  # Portal access = user_id is set
        )
        used_seats = await session.scalar(used_seats_query) or 0

        # Seat limit from user record (2 free + any purchased subscriptions)
        seat_limit = user.tenant_portal_seat_limit

        return {
            "limit": seat_limit,
            "used": used_seats,
            "available": max(0, seat_limit - used_seats),
            "free_seats": FREE_SEATS_WITH_SUBSCRIPTION,
            "purchased_seats": max(0, seat_limit - FREE_SEATS_WITH_SUBSCRIPTION)
        }

    @staticmethod
    async def has_available_seats(landlord_user_id: UUID, session: AsyncSession) -> bool:
        """
        Check if landlord has available seats.

        Used for optional warnings (NOT enforcement - GitHub allows over-limit temporarily).
        """
        availability = await SeatManagementService.get_seat_availability(landlord_user_id, session)
        return availability["available"] > 0

    @staticmethod
    async def update_seat_limit_from_subscription(
        landlord_user_id: UUID,
        subscription: TenantPortalSeatSubscription,
        session: AsyncSession
    ) -> None:
        """
        Update user's seat limit based on active subscription.

        Called from webhook handlers when subscription is created/updated.
        Formula: limit = 2 free seats + subscription.quantity
        """
        user = await session.get(User, landlord_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Calculate new limit: 2 free + purchased seats
        new_limit = FREE_SEATS_WITH_SUBSCRIPTION + subscription.quantity

        user.tenant_portal_seat_limit = new_limit
        session.add(user)

    @staticmethod
    async def calculate_required_seats(landlord_user_id: UUID, session: AsyncSession) -> int:
        """
        Calculate number of seats needed for current tenants.

        Returns 0 if within limit, otherwise returns deficit.
        Used for UX messaging when showing subscription modal.
        """
        availability = await SeatManagementService.get_seat_availability(landlord_user_id, session)
        if availability["used"] <= availability["limit"]:
            return 0  # No additional seats needed

        return availability["used"] - availability["limit"]

    @staticmethod
    async def reset_seat_limit_to_free_tier(landlord_user_id: UUID, session: AsyncSession) -> None:
        """
        Reset user's seat limit to free tier (2 seats).

        Called when subscription is canceled.
        GitHub approach: existing portal tenants keep access (graceful degradation),
        but NEW invitations will be blocked until subscription renewed or tenants removed.
        """
        user = await session.get(User, landlord_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.tenant_portal_seat_limit = FREE_SEATS_WITH_SUBSCRIPTION
        session.add(user)
