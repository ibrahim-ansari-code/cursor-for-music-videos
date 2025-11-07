# Accounting models package
"""
Accounting models for property management system.

This package contains models for:
- Payments and payment processing
- Invoices and billing
- Expenses and expense tracking
- Third-party integrations (QuickBooks, Xero, etc.)
"""

from .common import PaymentStatus, IntegrationStatus, IntegrationType
from .payment import Payment, PaymentMethod
from .payment_allocation import PaymentAllocation
from .invoice import Invoice
from .invoice_tax_detail import InvoiceTaxDetail
from .expense import Expense, ExpenseTaxDetail
from .integration import Integration
from .quickbooks_integration import QuickBooksIntegration

__all__ = [
    "PaymentStatus",
    "IntegrationStatus",
    "IntegrationType",
    "Payment",
    "PaymentMethod",
    "PaymentAllocation",
    "Invoice",
    "InvoiceTaxDetail",
    "Expense",
    "ExpenseTaxDetail",
    "Integration",
    "QuickBooksIntegration",
] 

# Industry standard: Explicit model imports to ensure proper registration order
# Import order matters for joined table inheritance patterns
try:
    from . import integration  # Base table first
    from . import quickbooks_integration  # Then extension tables
except ImportError as e:
    import logging
    logging.getLogger(__name__).error(f"Failed to import accounting models: {e}")
    raise
