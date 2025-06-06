from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from Backend.models.lease import Lease
    from Backend.models.property import Property, PropertyUnit
    from Backend.models.user import User
    from Backend.models.maintenance import MaintenanceRequest


class TenantStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING = "Pending"
    EVICTED = "Evicted"
    MOVED_OUT = "Moved Out"

# Link table for tenant-unit many-to-many relationship


class TenantUnitLink(SQLModel, table=True):
    __tablename__ = "tenant_unit_link"  # type: ignore
    tenant_id: int | None = Field(
        default=None, foreign_key="tenants.id", primary_key=True)
    unit_id: int | None = Field(
        default=None, foreign_key="property_units.id", primary_key=True)
    start_date: datetime | None = Field(default_factory=create_audit_datetime)
    end_date: datetime | None = None


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    user_id: PythonUUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey(
            "users.id", ondelete="SET NULL"), index=True)
    )
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    phone: str | None = None
    email: str | None = None
    status: TenantStatus = Field(default=TenantStatus.ACTIVE, index=True)
    created_at: datetime = Field(default_factory=create_audit_datetime)
    updated_at: datetime = Field(default_factory=create_audit_datetime)
    current_property_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey(
            "properties.id", ondelete="SET NULL"))
    )

    # --- Relationships Defined Directly ---

    user: Optional["User"] = Relationship(back_populates="tenant_details")
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
        back_populates="tenant")
