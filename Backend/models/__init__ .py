# Import all models to make them available for SQLModel metadata creation
from backend.models.user import User, UserType
from backend.models.property import Property, PropertyUnit
from backend.models.lease import Lease, LeaseStatus, LeaseDocument
from backend.models.vendor import Vendor, VendorDocument, VendorStatus
from backend.models.accounting import Payment, Invoice, Expense, PaymentStatus
from backend.models.message import Message, Conversation, MessageType

# For type hinting
__all__ = [
    "User", "UserType",
    "Property", "PropertyUnit",
    "Lease", "LeaseStatus", "LeaseDocument",
    "Vendor", "VendorDocument", "VendorStatus",
    "Payment", "Invoice", "Expense", "PaymentStatus",
    "Message", "Conversation", "MessageType",
]
