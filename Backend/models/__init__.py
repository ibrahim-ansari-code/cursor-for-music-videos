# Import the base models that don't have circular dependencies first
from Backend.models.enums import UserType

# Import enums first
from Backend.models.tenant import TenantStatus
from Backend.models.property import PropertyStatus
from Backend.models.lease import LeaseStatus
from Backend.models.accounting import PaymentStatus, PaymentMethod

# Import models in a logical order. 
# User is often foundational.
from Backend.models.user import User

# Import link tables next
from Backend.models.tenant import TenantUnitLink
from Backend.models.property import PropertyVendorLink

# Import main entity models
from Backend.models.tenant import Tenant
from Backend.models.property import Property, PropertyUnit
from Backend.models.lease import Lease, LeaseDocument, LeaseCreate
from Backend.models.vendor import Vendor, VendorDocument, VendorStatus

# Import models that reference the above
from Backend.models.accounting import Payment, Invoice, Expense

# Initialize models to resolve circular dependencies if needed
def initialize_models():
    """Configure mappers after all models are imported."""
    try:
        from sqlalchemy.orm import configure_mappers
        # Configure all mappers to resolve relationships defined within classes
        configure_mappers()
        print("SQLAlchemy mappers configured successfully.")
    except Exception as e:
        print(f"Error configuring SQLAlchemy mappers: {e}")
        # Optionally re-raise or handle the error
        raise

# Run the initialization function
initialize_models() 