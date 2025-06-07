from datetime import datetime, date, timezone
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID as PythonUUID

from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, Date, JSON, TIMESTAMP, Enum as PgEnum
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import sqlalchemy as sa

from Backend.models.enums import MaintenancePriority, MaintenanceStatus

if TYPE_CHECKING:
    from Backend.models.property import Property, PropertyUnit
    from Backend.models.tenant import Tenant
    from Backend.models.user import User


class MaintenanceRequest(SQLModel, table=True):
    __tablename__ = "maintenance_requests"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    issue_title: str = Field(sa_column=Column(String(255), nullable=False))
    description: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True))
    property_id: int = Field(sa_column=Column(Integer, ForeignKey(
        "properties.id", ondelete="CASCADE"), nullable=False))
    unit_id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, ForeignKey("property_units.id", ondelete="SET NULL")))
    tenant_id: Optional[int] = Field(default=None, sa_column=Column(
        Integer, ForeignKey("tenants.id", ondelete="SET NULL")))
    user_id: Optional[PythonUUID] = Field(default=None, sa_column=Column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")))
    request_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(
        TIMESTAMP(timezone=True), nullable=False))
    priority: MaintenancePriority = Field(
        sa_column=Column(PgEnum(MaintenancePriority, name="maintenance_priority", create_constraint=False, values_callable=lambda obj: [e.value for e in obj]), nullable=False))
    status: MaintenanceStatus = Field(
        default=MaintenanceStatus.PENDING,
        sa_column=Column(PgEnum(MaintenanceStatus, name="maintenance_status", create_constraint=False, values_callable=lambda obj: [e.value for e in obj]), nullable=False))
    scheduled_date: Optional[date] = Field(
        default=None, sa_column=Column(Date, nullable=True))
    estimated_cost: Optional[float] = Field(
        default=None, sa_column=Column(Numeric(10, 2), nullable=True))
    actual_cost: Optional[float] = Field(
        default=None, sa_column=Column(Numeric(10, 2), nullable=True))
    photos: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), onupdate=sa.func.now()))
    assigned_to: Optional[str] = Field(
        default=None, sa_column=Column(String, nullable=True))

    # Relationships
    property: "Property" = Relationship(back_populates="maintenance_requests")
    unit: Optional["PropertyUnit"] = Relationship(
        back_populates="maintenance_requests")
    tenant: Optional["Tenant"] = Relationship(
        back_populates="maintenance_requests")
    user: Optional["User"] = Relationship(
        back_populates="maintenance_requests")
