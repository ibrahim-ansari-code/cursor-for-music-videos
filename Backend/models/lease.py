"""
This module defines SQLModel classes for lease-related entities in the application.
It includes models for Leases, Lease Statuses, Lease Documents, and associated data structures
used to manage rental agreements and their documentation.
"""
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String
from sqlmodel import Column, Field, ForeignKey, Integer, Relationship, SQLModel

from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.accounting import Payment
    from Backend.models.property import Property, PropertyUnit
    from Backend.models.tenant import Tenant

# Enum for lease status


class LeaseStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"
    RENEWED = "RENEWED"


class Lease(SQLModel, table=True):
    """Lease model representing a rental agreement between landlord and tenant"""

    __tablename__ = "leases"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    start_date: date
    end_date: date
    monthly_rent: float
    security_deposit: float
    status: LeaseStatus = Field(default=LeaseStatus.DRAFT, index=True)

    # Additional lease terms
    is_renewable: bool = Field(default=True)
    auto_renew: bool = Field(default=False)
    rent_due_day: int = Field(default=1)  # Day of month rent is due
    late_fee_amount: float | None = None
    late_fee_after_days: int | None = None
    special_terms: str | None = None

    # Foreign keys
    property_id: int = Field(foreign_key="properties.id", index=True)
    unit_id: int | None = Field(default=None, foreign_key="property_units.id")
    tenant_id: int = Field(foreign_key="tenants.id", index=True)

    # Timestamps
    created_at: datetime = Field(default_factory=create_audit_datetime)
    updated_at: datetime = Field(default_factory=create_audit_datetime)

    # Relationships
    property: "Property" = Relationship(back_populates="leases")
    unit: Optional["PropertyUnit"] = Relationship(back_populates="leases")

    # Ensure this is defined before any tenant.py imports this file
    tenant: "Tenant" = Relationship(back_populates="leases")

    documents: list["LeaseDocument"] = Relationship(back_populates="lease")
    payments: list["Payment"] = Relationship(back_populates="lease")


class LeaseDocument(SQLModel, table=True):
    """Document associated with a lease (contract, addendums, etc.)"""

    __tablename__ = "lease_documents"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    name: str
    file_path: str
    document_type: str  # contract, addendum, notice, etc.
    upload_date: datetime = Field(default_factory=create_audit_datetime)

    # Foreign keys
    lease_id: int = Field(sa_column=Column(
        Integer, ForeignKey("leases.id", ondelete="CASCADE")))
    uploaded_by_id: str | None = Field(
        default=None,
        sa_column=Column(String(36), ForeignKey(
            "users.id", ondelete="SET NULL"))
    )

    # Relationships
    lease: Lease = Relationship(back_populates="documents")
    uploaded_by: User = Relationship()


class LeaseCreate(SQLModel):
    tenant_id: int
    property_id: int
    unit_id: int | None = None
    start_date: date
    end_date: date
    monthly_rent: float
    security_deposit: float
