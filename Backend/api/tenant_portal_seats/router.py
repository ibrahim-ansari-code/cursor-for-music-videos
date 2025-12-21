"""
Tenant Portal Seats API Router

Endpoints for managing seat-based licensing for the tenant portal.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.database import get_session
from Backend.api.auth.dependencies import get_current_user
from Backend.models.user import User
from Backend.api.tenant_portal_seats.service import SeatManagementService
from Backend.api.tenant_portal_seats.stripe_service import SeatSubscriptionService
from Backend.api.tenant_portal_seats.schemas import (
    SeatAvailabilityResponse,
    SeatSubscriptionRequest,
    CheckoutSessionResponse,
    UpdateSubscriptionQuantityRequest
)

router = APIRouter(prefix="/tenant-portal-seats", tags=["Tenant Portal Seats"])


@router.get("/availability", response_model=SeatAvailabilityResponse)
async def get_seat_availability(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get current seat availability for the authenticated landlord.

    Returns real-time seat usage (GitHub-style):
    - limit: Total seats (2 free + purchased)
    - used: COUNT(tenants WHERE user_id IS NOT NULL)
    - available: limit - used
    """
    return await SeatManagementService.get_seat_availability(user.id, session)


@router.post("/subscribe", response_model=CheckoutSessionResponse)
async def subscribe_to_seats(
    request: SeatSubscriptionRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create Stripe Checkout session to subscribe to additional seats.

    Flow:
    1. User requests N seats at $3/month each
    2. Redirect to Stripe Checkout
    3. After payment, webhook updates seat limit
    4. User can invite more tenants
    """
    if request.quantity < 1:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be at least 1"
        )

    if request.quantity > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 seats per subscription. Contact support for larger plans."
        )

    checkout_data = await SeatSubscriptionService.create_subscription_checkout(
        landlord_user_id=user.id,
        quantity=request.quantity,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        session=session
    )

    return checkout_data


@router.patch("/subscription/quantity")
async def update_subscription_quantity(
    request: UpdateSubscriptionQuantityRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update the quantity of an existing seat subscription.

    Allows scaling up/down. Stripe handles prorated billing.
    """
    if request.new_quantity < 1:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be at least 1"
        )

    await SeatSubscriptionService.update_subscription_quantity(
        landlord_user_id=user.id,
        new_quantity=request.new_quantity,
        session=session
    )

    return {"message": "Subscription quantity updated successfully"}


@router.delete("/subscription")
async def cancel_subscription(
    immediately: bool = False,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Cancel seat subscription.

    Args:
        immediately: If true, cancel now. If false, cancel at period end.

    Note: Existing portal tenants keep access (GitHub-style graceful degradation),
    but new invitations will be blocked once seats run out.
    """
    await SeatSubscriptionService.cancel_subscription(
        landlord_user_id=user.id,
        session=session,
        immediately=immediately
    )

    return {
        "message": "Subscription canceled" + (" immediately" if immediately else " at period end")
    }
