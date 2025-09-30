# Import all models to ensure they are registered with SQLModel/SQLAlchemy
# before any relationship mapping or configuration occurs.
from . import enums

# Import accounting models first to ensure they're available for relationships
from . import accounting

# Then import other models
from . import user
from . import property
from . import units
from . import tenant
from . import lease
from . import maintenance
from . import reports
from . import agent

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
from .lease import Lease, LeaseDocument, LeaseStatus
from .tenant import Tenant, TenantStatus # TenantStatus is in tenant.py
from .maintenance import MaintenanceRequest, MaintenancePriority, MaintenanceStatus

# Accounting models & enums from the 'accounting' subdirectory
from .accounting.common import PaymentStatus, IntegrationStatus, IntegrationType
from .accounting.payment import Payment, PaymentMethod
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
    "Payment",
    "PaymentMethod",
    "PaymentStatus",
    "Property",
    "PropertyStatus",
    "PropertyType",
    "PropertyUnit",
    "ReportResponse",
    "ReportSummary",
    "Tenant",
    "TenantStatus",
    "User",
    "UserAgentThread",
    "UserType",
]

