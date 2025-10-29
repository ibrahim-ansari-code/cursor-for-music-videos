"""
Ownership Entity model for tracking companies, individuals, and other entities
that own or have stakes in industrial and commercial property units.
"""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional, List
from uuid import UUID as PythonUUID, uuid4

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import ForeignKey
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.user import User
    from Backend.models.property import Property


class EntityType(str, Enum):
    """Types of ownership entities"""
    COMPANY = "company"
    INDIVIDUAL = "individual"
    TRUST = "trust"
    PARTNERSHIP = "partnership"
    LLC = "llc"
    CORPORATION = "corporation"
    OTHER = "other"


class OwnershipEntity(SQLModel, table=True):
    """
    Ownership Entity model representing companies, individuals, or organizations
    that own or have stakes in property units (primarily industrial/commercial).
    """

    __tablename__ = "ownership_entities"  # type: ignore
    __table_args__ = (
        Index("ix_ownership_entities_user_id", "user_id"),
        Index("ix_ownership_entities_name", "name"),
        Index("ix_ownership_entities_entity_type", "entity_type"),
    )

    id: PythonUUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True)
    )

    # Owner (landlord) who created this entity
    user_id: PythonUUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
        )
    )

    # Entity identification
    entity_type: str = Field(
        sa_column=Column(String(50), nullable=False),
        description="Type of entity: company, individual, trust, partnership, etc."
    )
    name: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Display name of the entity"
    )
    legal_name: Optional[str] = Field(
        default=None,
        sa_column=Column(String(500)),
        description="Legal/registered name if different from display name"
    )
    tax_id: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100)),
        description="Tax ID / EIN / Business Number (consider encryption for production)"
    )

    # Contact information
    contact_email: Optional[str] = Field(
        default=None,
        sa_column=Column(String(255)),
        description="Primary contact email"
    )
    contact_phone: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50)),
        description="Primary contact phone"
    )
    contact_name: Optional[str] = Field(
        default=None,
        sa_column=Column(String(255)),
        description="Primary contact person name"
    )

    # Address (optional)
    address: Optional[str] = Field(
        default=None,
        sa_column=Column(String(500)),
        description="Street address"
    )
    city: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100)),
        description="City"
    )
    province: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50)),
        description="Province/State"
    )
    postal_code: Optional[str] = Field(
        default=None,
        sa_column=Column(String(20)),
        description="Postal/ZIP code"
    )
    country: Optional[str] = Field(
        default="Canada",
        sa_column=Column(String(100)),
        description="Country"
    )

    # Additional notes
    notes: Optional[str] = Field(
        default=None,
        sa_column=Column(String(2000)),
        description="Additional notes or information about the entity"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            onupdate=create_audit_datetime
        ),
        description="Last update timestamp"
    )

    # Relationships
    owner: Optional["User"] = Relationship(
        back_populates="ownership_entities",
        sa_relationship_kwargs={"foreign_keys": "[OwnershipEntity.user_id]"}
    )

    # Relationship to properties (one entity can own many properties)
    properties: List["Property"] = Relationship(
        back_populates="ownership_entity",
        sa_relationship_kwargs={"foreign_keys": "[Property.ownership_entity_id]"}
    )
