"""
Rent Payment Constants

Fee rates, limits, and configuration for the rent payment system.
"""

from decimal import Decimal
from enum import Enum


# =============================================================================
# Platform Fee Configuration (Flat Fee by Payment Method)
# =============================================================================

# Flat fees in cents by payment method type
# PAD (bank transfer) is cheaper for us, so we pass savings to landlords
PLATFORM_FEES_CENTS: dict[str, int] = {
    "acss_debit": 300,  # $3.00 CAD - Canadian Pre-authorized Debit (PAD)
    "card": 800,        # $8.00 CAD - Credit/Debit cards
}

# Display names for payment method types
PAYMENT_METHOD_DISPLAY_NAMES: dict[str, str] = {
    "acss_debit": "Bank Transfer (PAD)",
    "card": "Credit/Debit Card",
}

# Default fee if payment method type is unknown (shouldn't happen)
DEFAULT_PLATFORM_FEE_CENTS = 800  # $8.00 CAD


def calculate_application_fee_cents(
    amount_cents: int,
    payment_method_type: str | None = None,
) -> int:
    """
    Calculate the platform application fee in cents.
    
    Flat fee based on payment method:
    - PAD (acss_debit): $3.00
    - Card: $8.00
    
    Args:
        amount_cents: Payment amount in cents (unused, kept for API compatibility)
        payment_method_type: The payment method type (acss_debit, card)
        
    Returns:
        Application fee in cents (flat fee based on method)
    """
    if payment_method_type and payment_method_type in PLATFORM_FEES_CENTS:
        return PLATFORM_FEES_CENTS[payment_method_type]
    
    return DEFAULT_PLATFORM_FEE_CENTS


def get_fee_display(payment_method_type: str | None = None) -> str:
    """
    Get human-readable fee for display to users.
    
    Args:
        payment_method_type: The payment method type
        
    Returns:
        Formatted fee string (e.g., "$3.00")
    """
    fee_cents = calculate_application_fee_cents(0, payment_method_type)
    return f"${fee_cents / 100:.2f}"


# =============================================================================
# Currency Configuration
# =============================================================================

# Default currency for Canadian payments
DEFAULT_CURRENCY = "cad"

# Supported currencies
SUPPORTED_CURRENCIES = {"cad"}


# =============================================================================
# Stripe Connect Configuration
# =============================================================================

# Account type for landlords
CONNECT_ACCOUNT_TYPE = "express"

# Default country for Connect accounts
CONNECT_DEFAULT_COUNTRY = "CA"

# Capabilities to request for Express accounts
CONNECT_CAPABILITIES = {
    "card_payments": {"requested": True},
    "transfers": {"requested": True},
    "acss_debit_payments": {"requested": True},  # Canadian PAD
}

# Business types
class BusinessType(str, Enum):
    """Stripe business types for Connect accounts."""
    INDIVIDUAL = "individual"
    COMPANY = "company"


# =============================================================================
# Payment Method Types
# =============================================================================

class PaymentMethodType(str, Enum):
    """Supported payment method types."""
    ACSS_DEBIT = "acss_debit"  # Canadian Pre-authorized Debit
    CARD = "card"


# =============================================================================
# Transaction Limits
# =============================================================================

# Minimum payment amount in cents ($1.00)
MINIMUM_PAYMENT_CENTS = 100

# Maximum payment amount in cents ($50,000.00)
MAXIMUM_PAYMENT_CENTS = 5_000_000


# =============================================================================
# Autopay Configuration
# =============================================================================

# Default max retries for failed autopay
DEFAULT_AUTOPAY_MAX_RETRIES = 3

# Days between retry attempts
RETRY_INTERVAL_DAYS = 2

# Days before due date to process autopay
AUTOPAY_PROCESS_DAYS_BEFORE = 1


# =============================================================================
# PAD (Pre-authorized Debit) Configuration
# =============================================================================

# PAD mandate text required for Canadian regulations
PAD_MANDATE_TEXT = """
By providing your bank account information and confirming this payment, you authorize 
{landlord_name} and Stripe, our payment service provider, to debit your account for 
the amount specified. You understand that this authorization will remain in effect 
until you cancel it by contacting your landlord, and you agree to notify your financial 
institution of any changes to this authorization.

You have certain recourse rights if any debit does not comply with this agreement. 
For example, you have the right to receive reimbursement for any debit that is not 
authorized or is not consistent with this PAD Agreement. To obtain more information 
on your recourse rights, contact your financial institution or visit www.payments.ca.
"""
