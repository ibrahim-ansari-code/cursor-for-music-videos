"""Expense and ExpenseTaxDetail ORM models"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, String, Column, Numeric, cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime
from Backend.models.property import Property


class ExpenseTaxDetail(SQLModel, table=True):
    """Represents a single tax line item associated with an expense."""
    __tablename__ = "expense_tax_details"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    tax_name: str = Field(sa_column=Column(String, nullable=False))
    tax_rate: Decimal = Field(
        sa_column=Column(Numeric(5, 2), nullable=False),
        ge=0, le=100, description="Tax rate as percentage (0-100)"
    )
    tax_amount: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False),
        ge=0, description="Tax amount must be non-negative"
    )

    expense_id: Optional[int] = Field(
        default=None, foreign_key="expenses.id", index=True)
    expense: "Expense" = Relationship(back_populates="taxes")

    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=create_audit_datetime),
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
        ge=0, description="Subtotal must be non-negative"
    )
    total_tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(12, 2), nullable=False),
        ge=0, description="Total tax must be non-negative"
    )

    property_id: int = Field(foreign_key="properties.id", index=True)

    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=create_audit_datetime),
    )

    property: "Property" = Relationship(back_populates="expenses")
    taxes: list["ExpenseTaxDetail"] = Relationship(
        back_populates="expense",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    @hybrid_property
    def total_amount(self) -> Decimal:
        """Computed property that returns subtotal_amount + total_tax_amount."""
        return self.subtotal_amount + self.total_tax_amount
    
    # Set the SQL expression directly to avoid method name collision
    total_amount = total_amount.expression(
        lambda cls: cast(cls.subtotal_amount + cls.total_tax_amount, Numeric(12, 2))
    )
