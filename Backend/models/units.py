"""
Unit models for property management.
Separated from property.py for better organization.
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, Index, Integer, String, Float, Boolean
from sqlalchemy import ForeignKey
from sqlmodel import Column, Field, Relationship, SQLModel

from Backend.models.tenant import TenantUnitLink
from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.property import Property
    from Backend.models.lease import Lease
    from Backend.models.tenant import Tenant
    from Backend.models.maintenance import MaintenanceRequest


class PropertyUnit(SQLModel, table=True):
    """Unit model representing individual units within a property"""

    __tablename__ = "property_units"  # type: ignore
    __table_args__ = (
        # Composite index for queries filtering by both property and tenant
        Index("ix_property_units_property_tenant", "property_id", "tenant_id"),
        Index("ix_property_units_name", "name"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey(
            "properties.id", ondelete="CASCADE"))
    )
    # Foreign key to the assigned tenant
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenants.id")
    name: str
    description: Optional[str] = None
    size: Optional[float] = None
    monthly_rent: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(12, 2)))
    is_rented: bool = Field(default=False)
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    floor: Optional[int] = Field(
        default=None, description="The floor number of the unit")
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=create_audit_datetime)
    )

    # Relationships
    property: Optional["Property"] = Relationship(back_populates="units")
    leases: List["Lease"] = Relationship(back_populates="unit")

    # Relationship to the assigned Tenant (Many-to-one)
    tenant: Optional["Tenant"] = Relationship(
        back_populates="assigned_units",
        sa_relationship_kwargs={
            # Explicitly define foreign keys using string
            "foreign_keys": "[PropertyUnit.tenant_id]",
        }
    )

    # Relationship to Tenants via link table (Many-to-many)
    tenants: list["Tenant"] = Relationship(
        back_populates="units",
        link_model=TenantUnitLink,
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    # Relationship to maintenance requests (One-to-many)
    maintenance_requests: list["MaintenanceRequest"] = Relationship(
        back_populates="unit",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
