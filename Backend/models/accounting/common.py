from enum import Enum

class PaymentStatus(str, Enum):
    PENDING = "Pending"
    PAID = "Paid"
    PARTIAL = "Partial"
    OVERDUE = "Overdue"
    CANCELLED = "Cancelled"
    REFUNDED = "Refunded"

class IntegrationStatus(str, Enum):
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    ERROR = "Error"
    PENDING = "Pending"

class IntegrationType(str, Enum):
    QUICKBOOKS = "QuickBooks"
    XERO = "Xero"
    SAGE = "Sage"
    NETSUITE = "NetSuite"
