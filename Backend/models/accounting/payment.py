"""Payment model for managing tenant rent payments and payment methods."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum as PgEnum,
    String,
    Column,
    Numeric,
    ForeignKey,
    Integer,
    Index,
)
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime, utc_now
from .common import PaymentStatus # Import PaymentStatus from common

if TYPE_CHECKING:
    from Backend.models.lease import Lease
    from Backend.models.tenant import Tenant

class PaymentMethod(str, Enum):
    CREDIT_CARD = "Credit Card"
    BANK_TRANSFER = "Bank Transfer"
    CASH = "Cash"
    CHECK = "Check"
    OTHER = "Other"

class Payment(SQLModel, table=True):
    """Payment model for rent payments from tenants"""

    __tablename__ = "payments"  # type: ignore
    __table_args__ = (
        Index("ix_payments_tenant_id", "tenant_id"),
        Index("ix_payments_lease_id", "lease_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    payment_date: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        sa_column=Column(PgEnum(PaymentStatus, name="paymentstatus",
                         create_constraint=True, values_callable=lambda x: [e.value for e in x]))
    )
    description: str | None = None
    payment_method: PaymentMethod = Field(
        default=PaymentMethod.OTHER,
        sa_column=Column(
            PgEnum(
                PaymentMethod,
                name="paymentmethod",
                create_constraint=True,
                values_callable=lambda x: [e.value for e in x],
            ),
            nullable=False,
        ),
    )
    transaction_reference: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True)
    )
    receipt_url: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True)
    )

    lease_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("leases.id", ondelete="SET NULL")),
    )
    tenant_id: int | None = Field(
        default=None,
        foreign_key="tenants.id"
    )

    # QuickBooks specific fields
    quickbooks_id: str | None = Field(
        default=None,
        sa_column=Column(String(length=64), nullable=True, unique=True),
    )

    last_synced_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now)
    )

    lease: "Lease" = Relationship(back_populates="payments")
    tenant: Optional["Tenant"] = Relationship(
        back_populates="payments",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
