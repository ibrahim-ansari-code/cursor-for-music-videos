# Import the base models that don't have circular dependencies first
from Backend.models.enums import UserType

# Import supporting models
from Backend.models.accounting import Payment, Invoice, Expense
from Backend.models.message import Message, Conversation, ConversationParticipant

# Import the enum classes
from Backend.models.tenant import TenantStatus
from Backend.models.property import PropertyStatus
from Backend.models.lease import LeaseStatus

# Import link tables first 
from Backend.models.tenant import TenantUnitLink
from Backend.models.property import PropertyVendorLink

# Import user model first since other models depend on it
from Backend.models.user import User

# Import the main models with circular dependencies in the correct order
# Import Tenant first since Lease depends on it having a leases property
from Backend.models.tenant import Tenant
from Backend.models.lease import Lease, LeaseDocument
from Backend.models.property import Property, PropertyUnit
from Backend.models.vendor import Vendor, VendorDocument

# Import the setup functions
from Backend.models.tenant import setup_relationships

# Initialize models to resolve circular dependencies
def initialize_models():
    """Initialize all models in the correct order and setup their relationships."""
    # Start by registering models to ensure all classes are loaded
    from sqlalchemy.orm import configure_mappers
    
    # Set up tenant relationships which will recursively set up other relationships
    setup_relationships()
    
    # Finally configure all mappers to resolve any remaining circular dependencies
    configure_mappers()

# Run the initialization function
initialize_models() 