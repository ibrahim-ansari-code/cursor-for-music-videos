from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy import Enum as PgEnum
from sqlalchemy import Float, String
from sqlmodel import Column, Field, ForeignKey, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime, utc_now

# Use TYPE_CHECKING to prevent circular imports at runtime
if TYPE_CHECKING:
    from Backend.models.lease import Lease
    from Backend.models.property import Property
    from Backend.models.user import User


class PaymentStatus(str, Enum):
    PENDING = "Pending"
    PAID = "Paid"
    PARTIAL = "Partial"
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

    __tablename__ = "payments"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    amount: float = Field(sa_column=Column(Float, nullable=False))
    payment_date: datetime = Field(
        default_factory=utc_now,  # Business date - timezone-aware
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        sa_column=Column(PgEnum(PaymentStatus, name="paymentstatus",
                         create_constraint=True, values_callable=lambda x: [e.value for e in x]))
    )
    description: str | None = None
    payment_method: str | None = Field(
        default=PaymentMethod.OTHER.value,
        sa_column=Column(String, nullable=True)
    )
    transaction_reference: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True)
    )

    # Foreign keys
    lease_id: int = Field(foreign_key="leases.id")
    tenant_id: UUID | None = Field(
        default=None,
        sa_column=Column(String(36), ForeignKey(
            "users.id", ondelete="SET NULL"))
    )

    # Timestamps - Audit fields use naive datetimes
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )

    # Relationships
    lease: "Lease" = Relationship(back_populates="payments")
    tenant: "User" = Relationship()


class Invoice(SQLModel, table=True):
    """Invoice model for billing tenants or other parties"""

    __tablename__ = "invoices"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    invoice_number: str
    amount: float
    description: str
    issue_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    due_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)

    # Foreign keys
    property_id: int | None = Field(default=None, foreign_key="properties.id")
    tenant_id: UUID | None = Field(
        default=None,
        sa_column=Column(String(36), ForeignKey(
            "users.id", ondelete="SET NULL"))
    )

    # Timestamps - Audit fields use naive datetimes
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )

    # Relationships
    # Relationship must keep Optional[]
    property: Optional["Property"] = Relationship()
    tenant: "User" = Relationship()


class Expense(SQLModel, table=True):
    """Expense model for property-related expenses"""

    __tablename__ = "expenses"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    amount: float
    category: str  # maintenance, utilities, taxes, insurance, etc.
    description: str
    expense_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    receipt_url: str | None = None

    # Foreign keys
    property_id: int = Field(foreign_key="properties.id")

    # Timestamps - Audit fields use naive datetimes
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )

    # Relationships
    property: "Property" = Relationship(back_populates="expenses")
