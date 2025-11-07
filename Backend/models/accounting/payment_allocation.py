"""PaymentAllocation model - Junction table linking payments to invoices."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Numeric, Integer, ForeignKey, DateTime, Index
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime, utc_now

if TYPE_CHECKING:
    from Backend.models.accounting.payment import Payment
    from Backend.models.accounting.invoice import Invoice


class PaymentAllocation(SQLModel, table=True):
    """
    Payment Allocation model - links payments to invoices.

    This implements the industry-standard pattern used by Stripe, QuickBooks, and FreshBooks
    for handling payment allocations. Supports:
    - Partial payments (one payment partially pays an invoice)
    - Multi-invoice payments (one payment split across multiple invoices)
    - Proper invoice status tracking (Paid/Partial/Pending)

    Example scenarios:
    1. Customer pays $500 towards a $1000 invoice → One allocation of $500
    2. Customer pays $1500 towards two $750 invoices → Two allocations of $750 each
    3. Customer pays $300 towards a $500 invoice, then $200 later → Two allocations
    """

    __tablename__ = "payment_allocations"  # type: ignore
    __table_args__ = (
        Index("idx_payment_allocations_payment_id", "payment_id"),
        Index("idx_payment_allocations_invoice_id", "invoice_id"),
        Index("idx_payment_allocations_created_at", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)

    payment_id: int = Field(
        sa_column=Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    )

    invoice_id: int = Field(
        sa_column=Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    )

    amount_applied: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False),
        description="Amount of the payment applied to this invoice"
    )

    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    # Relationships
    payment: Optional["Payment"] = Relationship(back_populates="allocations")
    invoice: Optional["Invoice"] = Relationship(back_populates="payment_allocations")
