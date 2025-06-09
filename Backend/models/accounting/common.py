from enum import Enum

class PaymentStatus(str, Enum):
    """Defines the possible statuses for a payment record."""
    PENDING = "Pending"
    PAID = "Paid"
    PARTIAL = "Partial"
    OVERDUE = "Overdue"
    CANCELLED = "Cancelled"
    REFUNDED = "Refunded"

class IntegrationStatus(str, Enum):
    """Represents the connection status of a third-party integration."""
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    ERROR = "Error"
    PENDING = "Pending"

class IntegrationType(str, Enum):
    """Specifies the type of third-party accounting integration."""
    QUICKBOOKS = "QuickBooks"
    XERO = "Xero"
    SAGE = "Sage"
    NETSUITE = "NetSuite"
