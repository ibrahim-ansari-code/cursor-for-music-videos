"""Invoice ORM model"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Numeric, Column
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime
from .common import PaymentStatus # Import PaymentStatus from common

if TYPE_CHECKING:
    from Backend.models.property import Property
    from Backend.models.tenant import Tenant

class Invoice(SQLModel, table=True):
    """Invoice model for billing tenants or other parties"""

    __tablename__ = "invoices"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    invoice_number: str = Field(unique=True, index=True)
    amount: Decimal = Field(sa_column=Column(Numeric(precision=12, scale=2), nullable=False))
    description: str
    issue_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    due_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)

    property_id: int | None = Field(default=None, foreign_key="properties.id")
    tenant_id: int | None = Field(
        default=None,
        foreign_key="tenants.id"
    )

    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    property: Optional["Property"] = Relationship()
    tenant: Optional["Tenant"] = Relationship() 