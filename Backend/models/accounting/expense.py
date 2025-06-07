"""Expense and ExpenseTaxDetail ORM models"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String, Column, Numeric
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.property import Property

class ExpenseTaxDetail(SQLModel, table=True):
    """Represents a single tax line item associated with an expense."""
    __tablename__ = "expense_tax_details"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    tax_name: str = Field(sa_column=Column(String, nullable=False))
    tax_rate: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    tax_amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))

    expense_id: Optional[int] = Field(default=None, foreign_key="expenses.id")
    expense: "Expense" = Relationship(back_populates="taxes")

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
    category: str
    description: str | None = None
    expense_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    receipt_url: str | None = None
    subtotal_amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    total_tax_amount: Decimal = Field(default=Decimal("0.00"), sa_column=Column(Numeric(12, 2), nullable=False))
    total_amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))

    property_id: int = Field(foreign_key="properties.id")

    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )

    property: "Property" = Relationship(back_populates="expenses")
    taxes: list["ExpenseTaxDetail"] = Relationship(
        back_populates="expense",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    ) 