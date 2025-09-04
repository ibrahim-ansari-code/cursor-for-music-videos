"""Defines the User SQLModel, representing users within the application, including their attributes and relationships."""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, String, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.property import Property
    from Backend.models.tenant import Tenant
    from Backend.models.maintenance import MaintenanceRequest
    from Backend.models.accounting.integration import Integration


class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore

    id: PythonUUID = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True)
    )
    email: str = Field(unique=True, index=True)
    first_name: str | None = None
    last_name: str | None = None
    # <-- force String instead of Enum
    user_type: str = Field(default="LANDLORD", sa_column=Column(String))
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
    profile_image_url: str | None = None
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    # Tax preference fields
    default_tax_name: str | None = Field(
        default=None,
        sa_column=Column(String(100), nullable=True),
        description="User's default tax name (e.g., 'HST', 'GST')"
    )
    default_tax_rate: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(6, 3), nullable=True),
        description="User's default tax rate as percentage (0-100)",
        ge=0,
        le=100
    )
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    is_email_verified: bool = Field(default=False)

    properties: list["Property"] = Relationship(back_populates="owner")

    # Define tenant_details relationship directly
    tenant_details: Optional["Tenant"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[Tenant.user_id]"}
    )
    maintenance_requests: list["MaintenanceRequest"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # Integration connections (QuickBooks, Xero, etc.)
    integrations: list["Integration"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

