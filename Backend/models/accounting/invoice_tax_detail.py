"""InvoiceTaxDetail ORM model for invoice tax line items"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Index, Numeric, String
from sqlmodel import Field, Relationship, SQLModel
from pydantic import BaseModel, field_validator

from Backend.utils.datetime_utils import create_audit_datetime
from Backend.utils.tax_utils import validate_canadian_tax_name

if TYPE_CHECKING:
    from Backend.models.accounting.invoice import Invoice

# === API Models for InvoiceTaxDetails ===

class InvoiceTaxDetailBase(BaseModel):
    tax_name: str
    tax_rate: Decimal
    
    @field_validator('tax_name')
    @classmethod
    def validate_tax_name_format(cls, v: str) -> str:
        """Validate Canadian tax name format."""
        return validate_canadian_tax_name(v)
    
    @field_validator('tax_rate')
    @classmethod
    def validate_tax_rate(cls, v: Decimal) -> Decimal:
        if v < Decimal('0') or v > Decimal('100'):
            raise ValueError('Tax rate must be between 0 and 100')
        return v


class InvoiceTaxDetailCreate(InvoiceTaxDetailBase):
    tax_amount: Decimal | None = None  # Optional: calculated if not provided
    
    @field_validator('tax_amount')
    @classmethod
    def validate_tax_amount(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < Decimal('0'):
            raise ValueError('Tax amount must be non-negative')
        return v


class InvoiceTaxDetailResponse(InvoiceTaxDetailBase):
    id: int
    tax_amount: Decimal
    invoice_id: int

    model_config = {"from_attributes": True}


# === Database ORM Model ===

class InvoiceTaxDetail(SQLModel, table=True):
    """Represents a single tax line item associated with an invoice."""

    __tablename__ = "invoice_tax_details"  # type: ignore
    __table_args__ = (
        Index("ix_invoice_tax_details_invoice_id", "invoice_id"),
        Index("uq_invoice_tax_name", "invoice_id", "tax_name", unique=True),
    )

    id: int | None = Field(default=None, primary_key=True)
    tax_name: str = Field(sa_column=Column(String, nullable=False))
    tax_rate: Decimal = Field(
        sa_column=Column(Numeric(6, 3), nullable=False),
        ge=0,
        le=100,
        description="Tax rate as percentage (0-100)",
    )
    tax_amount: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False),
        ge=0,
        description="Tax amount must be non-negative",
    )

    invoice_id: int = Field(foreign_key="invoices.id")
    invoice: "Invoice" = Relationship(back_populates="taxes")

    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, onupdate=create_audit_datetime
        ),
    )