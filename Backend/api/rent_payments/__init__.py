"""
Rent Payments API Module

Enables tenants to pay rent directly to landlords via Stripe Connect.
Uses Direct Charges - money flows directly from tenant to landlord,
with Brikli collecting a 2% application fee.

Submodules:
- router: FastAPI endpoints
- schemas: Pydantic request/response models
- service: Core payment business logic
- connect_service: Stripe Connect landlord onboarding
- webhooks: Stripe webhook handlers
- constants: Fee rates, status enums
"""

from .router import router

__all__ = ["router"]
