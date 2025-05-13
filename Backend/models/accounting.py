from typing import Optional, List, TYPE_CHECKING
from datetime import date, datetime
from uuid import UUID
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, ForeignKey, Float, Date, Enum as PgEnum

# Use TYPE_CHECKING to prevent circular imports at runtime
if TYPE_CHECKING:
    from Backend.models.lease import Lease
    from Backend.models.property import Property
    from Backend.models.user import User

class PaymentStatus(str, Enum):
    PENDING = "Pending"
    PAID = "Paid"
    OVERDUE = "Overdue"
    CANCELLED = "Cancelled"
    REFUNDED = "Refunded"

class PaymentMethod(str, Enum):
    CREDIT_CARD = "Credit Card"
    BANK_TRANSFER = "Bank Transfer"
    CASH = "Cash"
    CHECK = "Check"
    OTHER = "Other"

class Payment(SQLModel, table=True):
    """Payment model for rent payments from tenants"""
    
    __tablename__ = "payments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float = Field(sa_column=Column(Float, nullable=False))
    payment_date: date = Field(sa_column=Column(Date, nullable=False))
    status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        sa_column=Column(PgEnum(PaymentStatus, name="paymentstatus", create_constraint=True))
    )
    description: Optional[str] = None
    
    # Foreign keys
    lease_id: int = Field(foreign_key="leases.id")
    tenant_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    )
    
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
    tenant_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    )
    
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
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    property: "Property" = Relationship(back_populates="expenses")
