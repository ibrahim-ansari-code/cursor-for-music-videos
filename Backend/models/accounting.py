from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import DateTime
from sqlalchemy import Enum as PgEnum
from sqlalchemy import Float, String, Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, ForeignKey, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime, utc_now

# Use TYPE_CHECKING to prevent circular imports at runtime
if TYPE_CHECKING:
    from Backend.models.lease import Lease
    from Backend.models.property import Property
    from Backend.models.tenant import Tenant
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
    receipt_url: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True)
    )

    # Foreign keys
    lease_id: int = Field(foreign_key="leases.id")
    tenant_id: int | None = Field(
        default=None,
        foreign_key="tenants.id"
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
    tenant: Optional["Tenant"] = Relationship()


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
    tenant_id: int | None = Field(
        default=None,
        foreign_key="tenants.id"
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
    tenant: Optional["Tenant"] = Relationship()


class ExpenseTaxDetail(SQLModel, table=True):
    """Represents a single tax line item associated with an expense.

    This model stores details for an individual tax component of an overall expense,
    such as GST or PST. It includes the name of the tax, the rate applied,
    and the calculated tax amount for that specific line item. It is linked
    to an `Expense` record.
    """
    __tablename__ = "expense_tax_details"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    # E.g., "GST", "PST", "Service Fee"
    tax_name: str = Field(sa_column=Column(String, nullable=False))
    tax_rate: float = Field(sa_column=Column(
        Float, nullable=False))  # Percentage, e.g., 5 for 5%
    # Calculated: expense.subtotal_amount * tax_rate / 100
    tax_amount: float = Field(sa_column=Column(Float, nullable=False))

    expense_id: int = Field(foreign_key="expenses.id")
    expense: "Expense" = Relationship(back_populates="taxes")

    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )


class Expense(SQLModel, table=True):
    """Expense model for property-related expenses"""

    __tablename__ = "expenses"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)

    # Core expense fields
    category: str  # maintenance, utilities, insurance, etc.
    description: str | None = None  # Made description optional as per common use cases
    expense_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    receipt_url: str | None = None

    # Financial fields
    subtotal_amount: float = Field(sa_column=Column(
        Float, nullable=False))  # Amount before any taxes
    total_tax_amount: float = Field(default=0.0, sa_column=Column(
        Float, nullable=False))  # Sum of all tax_amount from ExpenseTaxDetail
    # subtotal_amount + total_tax_amount
    total_amount: float = Field(sa_column=Column(Float, nullable=False))

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
    taxes: list["ExpenseTaxDetail"] = Relationship(
        back_populates="expense",
        # Ensures tax details are deleted when an expense is deleted
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
