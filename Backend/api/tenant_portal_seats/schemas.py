"""
Pydantic schemas for Tenant Portal Seats API
"""
from urllib.parse import urlparse
from pydantic import BaseModel, HttpUrl, field_validator

from Backend.config import settings

# Allowed redirect URL hosts for Stripe Checkout
# Prevents open redirect attacks by allowlisting trusted domains
ALLOWED_REDIRECT_HOSTS = {
    "app.brikli.com",      # Landlord portal
    "tenant.brikli.com",   # Tenant portal
    "localhost",
    "127.0.0.1",
}


class SeatAvailabilityResponse(BaseModel):
    """Response schema for seat availability endpoint"""
    limit: int
    used: int
    available: int
    free_seats: int
    purchased_seats: int


class SeatSubscriptionRequest(BaseModel):
    """Request schema for creating seat subscription"""
    quantity: int
    success_url: str
    cancel_url: str

    @field_validator('success_url', 'cancel_url')
    @classmethod
    def validate_redirect_url(cls, v: str) -> str:
        """
        Validate redirect URLs are from allowed hosts to prevent open redirect attacks.
        """
        try:
            parsed = urlparse(v)
            host = parsed.hostname or ""

            # In development, allow any localhost URL
            if settings.ENVIRONMENT == "development":
                if host in ("localhost", "127.0.0.1") or host.endswith(".localhost"):
                    return v

            # Check against allowlist
            if host not in ALLOWED_REDIRECT_HOSTS:
                raise ValueError(f"Redirect URL host '{host}' is not allowed")

            return v
        except Exception as e:
            raise ValueError(f"Invalid redirect URL: {e}")


class CheckoutSessionResponse(BaseModel):
    """Response schema for Stripe Checkout session creation"""
    checkout_url: str
    session_id: str


class UpdateSubscriptionQuantityRequest(BaseModel):
    """Request schema for updating subscription quantity"""
    new_quantity: int
