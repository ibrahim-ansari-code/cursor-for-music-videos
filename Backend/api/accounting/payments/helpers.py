"""Helper utilities for the payments module - small, stateless utility functions."""
import logging
from uuid import UUID

from fastapi import HTTPException, status

from Backend.models.accounting.payment import Payment, PaymentMethod
from Backend.models.tenant import Tenant
from Backend.models.user import User
from .schemas import PaymentResponse


logger = logging.getLogger(__name__)


def get_payment_method_enum(payment_method_value: PaymentMethod | str | None) -> PaymentMethod:
    """
    Converts a string or enum value to a PaymentMethod enum, defaulting to OTHER if input is None or invalid.
    
    Raises:
        HTTPException: If the input cannot be converted to a valid PaymentMethod.
    """
    if isinstance(payment_method_value, PaymentMethod):
        return payment_method_value
    if not payment_method_value:
        return PaymentMethod.OTHER
    try:
        # Handle being passed an enum *name* instead of value
        if isinstance(payment_method_value, str):
            # Trim whitespace and convert to uppercase for consistent matching
            normalized_value = payment_method_value.strip().upper()
            try:
                return PaymentMethod[normalized_value]
            except KeyError:
                # Fall through to try PaymentMethod(payment_method_value)
                pass
        return PaymentMethod(payment_method_value)
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment_method '{payment_method_value}'."
        ) from e


def get_tenant_display_name(tenant: Tenant | None) -> str:
    """
    Returns a formatted display name for a tenant, using their full name if available, or a fallback identifier if not.
    
    If the tenant is None, returns "Unknown Tenant". If the tenant has a first name, returns "FirstName LastName". Otherwise, returns "Tenant #<id>".
    """
    if not tenant:
        return "Unknown Tenant"
    if tenant.first_name:
        return f"{tenant.first_name} {tenant.last_name}".strip()
    return f"Tenant #{tenant.id}"


def check_payment_ownership(payment: Payment, current_user: User) -> bool:
    """
    Determines whether the current user has permission to modify the specified payment.
    
    Admin users are always granted access. For non-admin users, access is allowed only if the user owns the property associated with the payment's lease and all related entities exist.
    
    Returns:
        True if the user can modify the payment; otherwise, False.
    """
    if current_user.is_admin:
        return True
    
    # Check for relationship existence before accessing attributes
    if not (payment.lease and payment.lease.property):
        return False

    # A landlord owns the payment if they own the associated property
    return payment.lease.property.user_id == current_user.id


def build_payment_response_from_orm(payment_orm: Payment) -> PaymentResponse | None:
    """
    Constructs a PaymentResponse object from a Payment ORM instance, including tenant and property display names.
    
    Returns:
        A PaymentResponse with populated fields, or None if the payment has no ID.
    """
    if payment_orm.id is None or payment_orm.lease_id is None:
        return None
    
    tenant_name = get_tenant_display_name(payment_orm.lease.tenant if payment_orm.lease else None)
    property_name = payment_orm.lease.property.name if payment_orm.lease and payment_orm.lease.property else "Unknown Property"
    
    return PaymentResponse(
        id=payment_orm.id,
        lease_id=payment_orm.lease_id,
        tenant_id=payment_orm.tenant_id,
        amount=payment_orm.amount,
        payment_date=payment_orm.payment_date,
        payment_method=get_payment_method_enum(payment_orm.payment_method),
        status=payment_orm.status,
        transaction_reference=payment_orm.transaction_reference,
        description=payment_orm.description,
        receipt_url=payment_orm.receipt_url,
        created_at=payment_orm.created_at,
        updated_at=payment_orm.updated_at,
        tenant_name=tenant_name,
        property_name=property_name
    )