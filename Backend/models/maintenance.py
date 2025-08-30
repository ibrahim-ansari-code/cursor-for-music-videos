from datetime import datetime, date, timezone, UTC
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, Date, JSON, TIMESTAMP, Enum as PgEnum, Index
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import sqlalchemy as sa

from Backend.models.enums import MaintenancePriority, MaintenanceStatus

if TYPE_CHECKING:
    from Backend.models.property import Property
    from Backend.models.units import PropertyUnit
    from Backend.models.tenant import Tenant
    from Backend.models.user import User


class MaintenanceRequest(SQLModel, table=True):
    __tablename__ = "maintenance_requests"  # type: ignore

    __table_args__ = (
        Index("ix_maintenance_requests_property_id", "property_id"),
        Index("ix_maintenance_requests_unit_id", "unit_id"),
        Index("ix_maintenance_requests_tenant_id", "tenant_id"),
        Index("ix_maintenance_requests_user_id", "user_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    issue_title: str = Field(sa_column=Column(String(255), nullable=False))
    description: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True))
    property_id: int = Field(sa_column=Column(Integer, ForeignKey(
        "properties.id", ondelete="CASCADE"), nullable=False))
    unit_id: int | None = Field(
        default=None, sa_column=Column(Integer, ForeignKey("property_units.id", ondelete="SET NULL")))
    tenant_id: int | None = Field(default=None, sa_column=Column(
        Integer, ForeignKey("tenants.id", ondelete="SET NULL")))
    user_id: PythonUUID | None = Field(default=None, sa_column=Column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")))
    request_date: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_column=Column(
        TIMESTAMP(timezone=True), nullable=False))
    priority: MaintenancePriority = Field(
        sa_column=Column(PgEnum(MaintenancePriority, name="maintenance_priority", create_constraint=False, values_callable=lambda obj: [e.value for e in obj]), nullable=False))
    status: MaintenanceStatus = Field(
        default=MaintenanceStatus.PENDING,
        sa_column=Column(PgEnum(MaintenanceStatus, name="maintenance_status", create_constraint=False, values_callable=lambda obj: [e.value for e in obj]), nullable=False))
    scheduled_date: date | None = Field(
        default=None, sa_column=Column(Date, nullable=True))
    completed_date: datetime | None = Field(
        default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=True))
    estimated_cost: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(10, 2), nullable=True))
    actual_cost: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(10, 2), nullable=True))
    photos: list[str] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True))

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_column=Column(
         TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_column=Column(
         TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), onupdate=sa.func.now()))
    assigned_to: str | None = Field(
         default=None, sa_column=Column(String, nullable=True))

    @staticmethod
    def validate_photos(value: list[str] | None) -> list[str] | None:
        """Validates that the 'photos' field is a list of strings."""
        if value is None:
            return None
        if not isinstance(value, list):
            raise TypeError("The 'photos' field must be a list of URL strings.")
        if not all(isinstance(item, str) for item in value):
            raise TypeError("Each item in the 'photos' list must be a string URL.")
        return value

    # Relationships
    property: "Property" = Relationship(back_populates="maintenance_requests")
    unit: Optional["PropertyUnit"] = Relationship(
        back_populates="maintenance_requests")
    tenant: Optional["Tenant"] = Relationship(
        back_populates="maintenance_requests")
    user: Optional["User"] = Relationship(
        back_populates="maintenance_requests")
