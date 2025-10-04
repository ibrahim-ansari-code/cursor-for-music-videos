from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import (Column, DateTime, ForeignKey, Index, Integer, String,
                        text)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel, col

from Backend.utils.datetime_utils import create_audit_datetime

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from Backend.models.lease import Lease
    from Backend.models.property import Property
    from Backend.models.units import PropertyUnit
    from Backend.models.user import User
    from Backend.models.maintenance import MaintenanceRequest
    from Backend.models.accounting.payment import Payment
    from Backend.models.accounting.invoice import Invoice


class TenantStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING = "Pending"
    EVICTED = "Evicted"
    MOVED_OUT = "Moved Out"


# Import TenantType from enums
from Backend.models.enums import TenantType


# Link table for tenant-unit many-to-many relationship


class TenantUnitLink(SQLModel, table=True):
    __tablename__ = "tenant_unit_link"  # type: ignore
    __table_args__ = (Index("ix_tenant_unit_link_unit_id", "unit_id"),)

    tenant_id: int | None = Field(
        default=None, foreign_key="tenants.id", primary_key=True
    )
    unit_id: int | None = Field(
        default=None, foreign_key="property_units.id", primary_key=True
    )
    start_date: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    end_date: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    user_id: PythonUUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            index=True,
        ),
    )
    
    # Tenant type and naming fields
    tenant_type: TenantType = Field(default=TenantType.INDIVIDUAL)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    company_name: str | None = Field(default=None, max_length=200)
    contact_person: str | None = Field(default=None, max_length=200)
    
    phone: str | None = None
    email: str | None = None
    status: TenantStatus = Field(default=TenantStatus.ACTIVE)
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    current_property_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey(
            "properties.id", ondelete="SET NULL"))
    )
    landlord_id: PythonUUID = Field(foreign_key="users.id")
    profile_image_url: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )

    # QuickBooks specific fields
    quickbooks_customer_id: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )
    last_synced_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # --- Relationships Defined Directly ---

    user: Optional["User"] = Relationship(
        back_populates="tenant_details",
        sa_relationship_kwargs={"foreign_keys": "[Tenant.user_id]"},
    )
    current_property: Optional["Property"] = Relationship(
        back_populates="current_tenants")

    leases: list["Lease"] = Relationship(back_populates="tenant")
    assigned_units: list["PropertyUnit"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={
            "foreign_keys": "[PropertyUnit.tenant_id]",
            "lazy": "selectin"
        }
    )
    units: list["PropertyUnit"] = Relationship(
        back_populates="tenants",
        link_model=TenantUnitLink,
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    maintenance_requests: list["MaintenanceRequest"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    payments: list["Payment"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    invoices: list["Invoice"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    __table_args__ = (
        Index('idx_tenant_email_unique_per_landlord', "landlord_id", text("lower(email)"), unique=True, postgresql_where=text("email IS NOT NULL")),
        Index("ix_tenants_status", "status"),
        Index("idx_tenants_email_lower", text("lower(email)"),
              postgresql_where=text("email IS NOT NULL")),
        Index("ix_tenants_current_property_id", "current_property_id"),
        Index("idx_tenants_landlord_id", "landlord_id"),
        Index("ix_tenants_tenant_type", "tenant_type"),
    )
