from typing import Optional, List
from datetime import date, datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    LATE = "late"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    REFUNDED = "refunded"

class Payment(SQLModel, table=True):
    """Payment model for rent payments from tenants"""
    
    __tablename__ = "payments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    payment_date: datetime
    payment_method: str  # credit_card, bank_transfer, cash, etc.
    status: PaymentStatus
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None
    
    # Foreign keys
    lease_id: int = Field(foreign_key="leases.id")
    tenant_id: int = Field(foreign_key="users.id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    lease: "Lease" = Relationship(back_populates="payments")
    tenant: "User" = Relationship()

class Invoice(SQLModel, table=True):
    """Invoice model for billing tenants or other parties"""
    
    __tablename__ = "invoices"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_number: str
    amount: float
    description: str
    issue_date: date
    due_date: date
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    
    # Foreign keys
    property_id: Optional[int] = Field(default=None, foreign_key="properties.id")
    tenant_id: int = Field(foreign_key="users.id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    property: Optional["Property"] = Relationship()
    tenant: "User" = Relationship()

class Expense(SQLModel, table=True):
    """Expense model for property-related expenses"""
    
    __tablename__ = "expenses"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    category: str  # maintenance, utilities, taxes, insurance, etc.
    description: str
    expense_date: date
    receipt_url: Optional[str] = None
    
    # Foreign keys
    property_id: int = Field(foreign_key="properties.id")
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendors.id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    property: "Property" = Relationship(back_populates="expenses")
    vendor: Optional["Vendor"] = Relationship()
