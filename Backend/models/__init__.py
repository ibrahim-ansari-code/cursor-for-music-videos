# Import the base models that don't have circular dependencies first
from Backend.models.enums import UserType

# We need to import model classes in a specific order to avoid circular references
# First, import only enums, which doesn't have dependencies
from Backend.models.tenant import TenantStatus
from Backend.models.property import PropertyStatus
from Backend.models.lease import LeaseStatus
from Backend.models.accounting import PaymentStatus, PaymentMethod

# Import the user model first since other models depend on it
from Backend.models.user import User, setup_user_relationships

# Import link tables which typically have fewer dependencies 
from Backend.models.tenant import TenantUnitLink
from Backend.models.property import PropertyVendorLink

# Import the main models in the correct order to avoid circular references
from Backend.models.tenant import Tenant, setup_relationships
from Backend.models.property import Property, PropertyUnit, setup_property_relationships
from Backend.models.lease import Lease, LeaseDocument, LeaseCreate
from Backend.models.vendor import Vendor, VendorDocument, VendorStatus

# Now we can safely import models that reference the above
from Backend.models.accounting import Payment, Invoice, Expense
from Backend.models.message import Message, Conversation, ConversationParticipant, MessageType

# Initialize models to resolve circular dependencies
def initialize_models():
    """Initialize all models in the correct order and setup their relationships."""
    # Start by registering models to ensure all classes are loaded
    from sqlalchemy.orm import configure_mappers
    
    # Set up relationships in the correct order
    setup_user_relationships()
    setup_property_relationships()
    setup_relationships()
    
    # Finally configure all mappers to resolve any remaining circular dependencies
    configure_mappers()

# Run the initialization function
initialize_models() 