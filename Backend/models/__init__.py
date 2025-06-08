# Import all models to ensure they are registered with SQLModel/SQLAlchemy
# before any relationship mapping or configuration occurs.
from . import enums

# Import accounting models first to ensure they're available for relationships
from . import accounting

# Then import other models
from . import user
from . import property
from . import tenant
from . import lease
from . import maintenance
from . import reports

# Initialize models to resolve circular dependencies if needed
def initialize_models():
    """
    Configures SQLAlchemy mappers after all models have been imported.
    
    This function ensures that all model relationships and mappings are properly set up,
    resolving any circular dependencies before the ORM is used.
    """
    try:
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        print("SQLAlchemy mappers configured successfully.")
    except Exception as e:
        print(f"Error configuring SQLAlchemy mappers: {e}")
        raise


# SQLModel and Enum imports from local model files
from .user import User
from .property import Property, PropertyUnit, PropertyType # PropertyType is in property.py
from .lease import Lease, LeaseDocument, LeaseStatus
from .tenant import Tenant, TenantStatus # TenantStatus is in tenant.py
from .maintenance import MaintenanceRequest, MaintenancePriority, MaintenanceStatus

# Accounting models & enums from the 'accounting' subdirectory
from .accounting.common import PaymentStatus, IntegrationStatus, IntegrationType
from .accounting.payment import Payment, PaymentMethod
from .accounting.invoice import Invoice
from .accounting.expense import Expense, ExpenseTaxDetail
from .accounting.integration import Integration

# General Enums from enums.py
from .enums import UserType, PropertyStatus # PropertyStatus is in enums.py

# Report-related Pydantic models from reports.py (These are data structures, not API schemas for CRUD)
# If these are purely for API responses, they might not belong here, but keeping if they model complex data types used internally.
from .reports import ReportResponse, MonthlyChartData, ReportSummary, FinancialTableRow, IncomeByProperty

__all__ = [
     # User models
     "User",
 
    # Maintenance models & enums  
    "MaintenanceRequest", "MaintenancePriority", "MaintenanceStatus",

     # Property models & enums
     "Property", "PropertyUnit", "PropertyType",

    # Lease models & enums
    "Lease", "LeaseDocument", "LeaseStatus",

    # Tenant models & enums
    "Tenant", "TenantStatus",

    # Accounting models & enums
    "PaymentStatus", "Payment", "PaymentMethod",
    "Invoice",
    "Expense", "ExpenseTaxDetail",
    "Integration", "IntegrationStatus", "IntegrationType",

    # General Enums
    "UserType", "PropertyStatus",

    # Report data structures (if considered core models)
    "ReportResponse", "MonthlyChartData", "ReportSummary", "FinancialTableRow", "IncomeByProperty"
]
