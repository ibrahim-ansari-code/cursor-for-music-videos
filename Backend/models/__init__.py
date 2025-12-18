# Import all models to ensure they are registered with SQLModel/SQLAlchemy
# before any relationship mapping or configuration occurs.
from . import enums

# Import accounting models first to ensure they're available for relationships
from . import accounting

# Then import other models
from . import user
from . import property
from . import units
from . import ownership_entity
from . import tenant
from . import tenant_documents
from . import tenant_portal_invitation
from . import lease
from . import maintenance
from . import vendor
from . import reports
from . import agent
from . import notification
from . import calendar

# Rent payment models (Stripe Connect)
from . import stripe_connected_account
from . import tenant_payment_method
from . import rent_payment_transaction
from . import rent_autopay_enrollment
from . import rent_payment_refund
from . import rent_payment_dispute
from . import rent_payment_webhook_log

# Industry standard: Initialize models to resolve circular dependencies
def initialize_models():
    """
    Configures SQLAlchemy mappers after all models have been imported.
    
    This is the industry standard approach for resolving circular dependencies
    in complex model hierarchies with joined table inheritance.
    """
    try:
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        print("✅ SQLAlchemy mappers configured successfully.")
    except Exception as e:
        print(f"❌ Error configuring SQLAlchemy mappers: {e}")
        raise

# Auto-initialize when models module is imported  
initialize_models()


# SQLModel and Enum imports from local model files
from .user import User
from .property import Property, PropertyType # PropertyType is in property.py
from .units import PropertyUnit # PropertyUnit is now in units.py
from .ownership_entity import OwnershipEntity, EntityType
from .lease import Lease, LeaseDocument, LeaseStatus
from .tenant import Tenant, TenantStatus # TenantStatus is in tenant.py
from .tenant_documents import TenantDocument
from .maintenance import MaintenanceRequest, MaintenancePriority, MaintenanceStatus
from .vendor import Vendor, UserVendor

# Accounting models & enums from the 'accounting' subdirectory
from .accounting.common import PaymentStatus, IntegrationStatus, IntegrationType
from .accounting.payment import Payment, PaymentMethod
from .accounting.payment_allocation import PaymentAllocation
from .accounting.invoice import Invoice
from .accounting.invoice_tax_detail import InvoiceTaxDetail
from .accounting.expense import Expense, ExpenseTaxDetail
from .accounting.integration import Integration
from .accounting.quickbooks_integration import QuickBooksIntegration

# General Enums from enums.py
from .enums import UserType, PropertyStatus # PropertyStatus is in enums.py

# Report-related Pydantic models from reports.py (These are data structures, not API schemas for CRUD)
# If these are purely for API responses, they might not belong here, but keeping if they model complex data types used internally.
from .reports import ReportResponse, MonthlyChartData, ReportSummary, FinancialTableRow, IncomeByProperty

# Agent models
from .agent import UserAgentThread

# Notification models
from .notification import Notification, NotificationPreference, NotificationDeliveryLog

# Calendar models
from .calendar import CustomReminder, CalendarEventType, CalendarEventStatus, CalendarEventPriority

# Tenant Portal models
from .tenant_portal_invitation import TenantPortalInvitation, InvitationStatus

# Rent Payment models (Stripe Connect)
from .stripe_connected_account import StripeConnectedAccount
from .tenant_payment_method import TenantPaymentMethod
from .rent_payment_transaction import RentPaymentTransaction, RentPaymentTransactionStatus
from .rent_autopay_enrollment import RentAutopayEnrollment
from .rent_payment_refund import RentPaymentRefund, RefundStatus, RefundReason
from .rent_payment_dispute import RentPaymentDispute, DisputeStatus, DisputeReason
from .rent_payment_webhook_log import RentPaymentWebhookLog

__all__ = [
    # Accounting models & enums
    "Expense",
    "ExpenseTaxDetail",
    "FinancialTableRow",
    "IncomeByProperty",
    "Integration",
    "QuickBooksIntegration",
    "IntegrationStatus",
    "IntegrationType",
    "Invoice",
    "InvoiceTaxDetail",
    "Lease",
    "LeaseDocument",
    "LeaseStatus",
    "MaintenancePriority",
    "MaintenanceRequest",
    "MaintenanceStatus",
    "MonthlyChartData",
    "OwnershipEntity",
    "EntityType",
    "Payment",
    "PaymentAllocation",
    "PaymentMethod",
    "PaymentStatus",
    "Property",
    "PropertyStatus",
    "PropertyType",
    "PropertyUnit",
    "ReportResponse",
    "ReportSummary",
    "Tenant",
    "TenantDocument",
    "TenantStatus",
    "User",
    "UserAgentThread",
    "UserType",
    # Vendor models
    "Vendor",
    "UserVendor",
    # Notification models
    "Notification",
    "NotificationPreference",
    "NotificationDeliveryLog",
    # Calendar models & enums
    "CustomReminder",
    "CalendarEventType",
    "CalendarEventStatus",
    "CalendarEventPriority",
    # Tenant Portal models
    "TenantPortalInvitation",
    "InvitationStatus",
    # Rent Payment models (Stripe Connect)
    "StripeConnectedAccount",
    "TenantPaymentMethod",
    "RentPaymentTransaction",
    "RentPaymentTransactionStatus",
    "RentAutopayEnrollment",
    "RentPaymentRefund",
    "RefundStatus",
    "RefundReason",
    "RentPaymentDispute",
    "DisputeStatus",
    "DisputeReason",
    "RentPaymentWebhookLog",
]

