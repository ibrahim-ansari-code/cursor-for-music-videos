"""Expense and ExpenseTaxDetail ORM models"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, DateTime, Index, Numeric, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.expression import cast
from sqlmodel import Field, Relationship, SQLModel
from pydantic import BaseModel

from Backend.models.property import Property
from Backend.utils.datetime_utils import create_audit_datetime

# === API Models for Expenses ===


class TaxDetailItem(BaseModel):
    """Pydantic model for individual tax items in API responses."""
    tax_name: str
    tax_rate: Decimal  # Percentage as Decimal for precision
    tax_amount: Decimal  # Dollar amount as Decimal for precision


class ExpenseTaxDetailBase(BaseModel):
    tax_name: str
    tax_rate: Decimal


class ExpenseTaxDetailCreate(ExpenseTaxDetailBase):
    tax_amount: Decimal | None = None  # Optional: calculated if not provided


class ExpenseTaxDetailResponse(ExpenseTaxDetailBase):
    id: int
    tax_amount: Decimal
    expense_id: int

    class Config:
        from_attributes = True


class ExpenseBase(BaseModel):
    category: str
    description: str | None = None
    expense_date: datetime
    receipt_url: str | None = None
    property_id: int
    subtotal_amount: Decimal


class ExpenseCreate(BaseModel):
    property_id: int
    category: str
    subtotal_amount: Decimal
    expense_date: datetime
    description: str | None = None
    receipt_url: str | None = None
    taxes: list[ExpenseTaxDetailCreate] | None = None


class ExpenseUpdate(BaseModel):
    property_id: int | None = None
    category: str | None = None
    subtotal_amount: Decimal | None = None
    expense_date: datetime | None = None
    description: str | None = None
    receipt_url: str | None = None
    taxes: list[ExpenseTaxDetailCreate] | None = None


class ExpenseResponse(ExpenseBase):
    id: int
    total_tax_amount: Decimal
    total_amount: Decimal
    taxes: list[ExpenseTaxDetailResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExpenseReceiptParseDetails(BaseModel):
    expense_date: str | None = None  # LLM might return it as expense_date
    payment_date: str | None = None  # LLM might return it as payment_date
    subtotal_amount: Decimal
    total_tax_amount: Decimal
    total_amount: Decimal
    currency: str | None = None
    tax_details: list[TaxDetailItem] = []  # Individual tax line items
    # Payment method is actually useful for expense tracking
    payment_method: str | None = None
    description_notes: str | None = None
    raw_text_preview: str | None = None


class ExpenseReceiptParseResponse(BaseModel):
    receipt_url: str
    parsed_details: ExpenseReceiptParseDetails
    message: str | None = None

# === Database ORM Models ===


class ExpenseTaxDetail(SQLModel, table=True):
    """Represents a single tax line item associated with an expense."""

    __tablename__ = "expense_tax_details"  # type: ignore
    __table_args__ = (Index("ix_expense_tax_details_expense_id", "expense_id"),)

    id: int | None = Field(default=None, primary_key=True)
    tax_name: str = Field(sa_column=Column(String, nullable=False))
    tax_rate: Decimal = Field(
        sa_column=Column(Numeric(5, 2), nullable=False),
        ge=0,
        le=100,
        description="Tax rate as percentage (0-100)",
    )
    tax_amount: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False),
        ge=0,
        description="Tax amount must be non-negative",
    )

    expense_id: Optional[int] = Field(default=None, foreign_key="expenses.id")
    expense: "Expense" = Relationship(back_populates="taxes")

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


class Expense(SQLModel, table=True):
    """Expense model for property-related expenses"""

    __tablename__ = "expenses"  # type: ignore

    model_config = {  # type: ignore
        "arbitrary_types_allowed": True,
        "ignored_types": (hybrid_property,),
    }

    id: int | None = Field(default=None, primary_key=True)
    category: str
    description: str | None = None
    expense_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    receipt_url: str | None = None
    subtotal_amount: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False),
        ge=0,
        description="Subtotal must be non-negative",
    )
    total_tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(12, 2), nullable=False),
        ge=0,
        description="Total tax must be non-negative",
    )

    property_id: int = Field(foreign_key="properties.id", index=True)

    # QuickBooks specific fields
    quickbooks_id: str | None = Field(
        default=None,
        sa_column=Column(String(length=64), unique=True,
                        index=True, nullable=True),
    )
    last_synced_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False,
                         onupdate=create_audit_datetime),
    )

    property: "Property" = Relationship(back_populates="expenses")
    taxes: list["ExpenseTaxDetail"] = Relationship(
        back_populates="expense",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )

    __table_args__ = (Index("ix_expenses_property_id", "property_id"),)

    @hybrid_property
    def total_amount(self) -> Decimal:
        """
        Returns the total amount of the expense, including subtotal and total tax.
        
        This computed property adds the subtotal amount and the total tax amount to provide
        the full expense value.
        """
        return self.subtotal_amount + self.total_tax_amount

    # Set the SQL expression directly to avoid method name collision
    total_amount = total_amount.expression(
        lambda cls: cast(cls.subtotal_amount +
                         cls.total_tax_amount, Numeric(12, 2))
    )
