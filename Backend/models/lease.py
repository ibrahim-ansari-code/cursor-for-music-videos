"""
This module defines SQLModel classes for lease-related entities in the application.
It includes models for Leases, Lease Statuses, Lease Documents, and associated data structures
used to manage rental agreements and their documentation.
"""
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, ForeignKey, Integer, Relationship, SQLModel

from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from .accounting.payment import Payment
    from .property import Property, PropertyUnit
    from .tenant import Tenant

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
    uploaded_by_id: PythonUUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey(
            "users.id", ondelete="SET NULL"), index=True)
    )

    # Relationships
    lease: "Lease" = Relationship(back_populates="documents")
    uploaded_by: "User" = Relationship()


class LeaseCreate(SQLModel):
    tenant_id: int
    property_id: int
    unit_id: int | None = None
    start_date: date
    end_date: date
    monthly_rent: float
    security_deposit: float
    status: LeaseStatus | None = LeaseStatus.DRAFT
    file_url: str | None = None


class LeaseUpdate(SQLModel):
    """
    Model for applying partial updates to an existing Lease object.

    All fields are optional, allowing clients to send only the data points
    that need to be modified. Status updates (e.g., activating or
    terminating a lease) are handled via a separate mechanism to maintain
    a clear distinction in API operations and business logic.
    """
    start_date: date | None = None
    end_date: date | None = None
    monthly_rent: float | None = None
    security_deposit: float | None = None
    rent_due_day: int | None = None
    late_fee_amount: float | None = Field(default=None)
    late_fee_after_days: int | None = Field(default=None)
    special_terms: str | None = Field(default=None)
    # Consider if status updates should be part of this or a separate endpoint
    # status: LeaseStatus | None = None

# Ensure all Field imports from sqlmodel are correct if this class uses them.
# If only Pydantic BaseModel is needed, adjust SQLModel inheritance.
# For now, assuming SQLModel is appropriate for consistency or future ORM use.
# If it's purely for API data validation, from pydantic import BaseModel would be more standard.
# However, to keep it consistent with LeaseCreate, using SQLModel.
# Added default=None to optional fields to be more explicit.
