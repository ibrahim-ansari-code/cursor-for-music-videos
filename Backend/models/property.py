from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, Dict, Any
from uuid import UUID as PythonUUID

from sqlalchemy import DateTime, Index, JSON, Numeric
from sqlalchemy import Enum as PgEnum
from sqlalchemy import ForeignKey, String, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, Relationship, SQLModel

from Backend.models.enums import PropertyStatus
from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.accounting.expense import Expense
    from Backend.models.lease import Lease
    from Backend.models.tenant import Tenant
    from Backend.models.maintenance import MaintenanceRequest
    from Backend.models.accounting.invoice import Invoice
    from Backend.models.units import PropertyUnit


class PropertyType(str, Enum):
    RESIDENTIAL = "Residential"
    COMMERCIAL = "Commercial"
    INDUSTRIAL = "Industrial"
    LAND = "Land"
    SPECIAL_PURPOSE = "Special Purpose"
    MIXED_USE = "Mixed-Use"
    APARTMENT_COMPLEX = "Apartment Complex"
    OTHER = "Other"  # Added an "Other" category


class Property(SQLModel, table=True):
    """Property model representing a real estate property"""

    __tablename__ = "properties"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(255)),
                      description="Name of the property (max 255 chars)")
    address: str = Field(sa_column=Column(String(255)),
                         description="Street address (max 255 chars)")
    city: str = Field(sa_column=Column(String(100)),
                      description="City (max 100 chars)")
    province: str = Field(sa_column=Column(String(50)),
                          description="Province or state (max 50 chars)")
    postal_code: str = Field(sa_column=Column(
        String(20)), description="Postal or ZIP code (max 20 chars)")
    property_type: str = Field(sa_column=Column(
        String(50)), description="Type of property (residential, commercial, etc.)")
    year_built: Optional[int] = Field(
        default=None, description="Year the property was built")
    description: Optional[str] = Field(default=None, sa_column=Column(
        String(500)), description="Optional property description (max 500 chars)")
    status: PropertyStatus = Field(
        sa_column=Column(PgEnum(PropertyStatus, name="propertystatus",
                         create_constraint=True), nullable=False, default=PropertyStatus.ACTIVE),
        description="Status of the property (enum: ACTIVE, INACTIVE, DRAFT, ARCHIVED)"
    )
    
    # Google Maps fields
    latitude: Optional[float] = Field(default=None, sa_column=Column(
        Float), description="Latitude coordinate for property location")
    longitude: Optional[float] = Field(default=None, sa_column=Column(
        Float), description="Longitude coordinate for property location")
    place_id: Optional[str] = Field(default=None, sa_column=Column(
        String(255)), description="Google Maps Place ID")
    formatted_address: Optional[str] = Field(default=None, sa_column=Column(
        String(500)), description="Google Maps formatted address")
    google_maps_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(
        JSON), description="Additional Google Maps metadata")
    
    # Property type-specific details (JSONB column for flexible storage)
    property_details: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(
        JSON), description="Type-specific property details stored as JSON")
    
    # Tax preference fields
    default_tax_name: str | None = Field(
        default=None,
        sa_column=Column(String(100), nullable=True),
        description="Property's default tax name (e.g., 'HST', 'GST+PST')"
    )
    default_tax_rate: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(6, 3), nullable=True),
        description="Property's default tax rate as percentage (0-100)",
        ge=0,
        le=100
    )

    # Foreign keys
    user_id: PythonUUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey(
            "users.id", ondelete="CASCADE"), nullable=False)
    )

    # Timestamps - Using datetime utilities
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=create_audit_datetime),
        description="Last update timestamp"
    )

    # Relationships
    owner: Optional[User] = Relationship(back_populates="properties", sa_relationship_kwargs={
                                         "foreign_keys": "[Property.user_id]"})

    # Configure cascade delete for units
    units: list["PropertyUnit"] = Relationship(
        back_populates="property",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
    
    # Configure cascade delete for images
    images: list["PropertyImage"] = Relationship(
        back_populates="property",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )

    leases: list["Lease"] = Relationship(back_populates="property")
    expenses: list["Expense"] = Relationship(
        back_populates="property",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )

    # Relationship to current tenants (One-to-many)
    current_tenants: list["Tenant"] = Relationship(
        back_populates="current_property",
        sa_relationship_kwargs={
            "foreign_keys": "[Tenant.current_property_id]",
            "lazy": "selectin",
        }
    )

    # Relationship to maintenance requests (One-to-many)
    maintenance_requests: list["MaintenanceRequest"] = Relationship(
        back_populates="property",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )

    invoices: list["Invoice"] = Relationship(
        back_populates="property",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )

    __table_args__ = (Index("ix_properties_user_id", "user_id"),)

class PropertyImage(SQLModel, table=True):
    """Property image model for storing property photos and documents"""
    
    __tablename__ = "property_images"  # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="properties.id", description="Property this image belongs to", ondelete="CASCADE")
    image_url: str = Field(sa_column=Column(String(500)), description="URL to the image in storage")
    image_type: str = Field(default="photo", sa_column=Column(String(50)), 
                           description="Type of image: photo, floorplan, document")
    is_primary: bool = Field(default=False, description="Is this the primary/featured image")
    caption: Optional[str] = Field(default=None, sa_column=Column(String(255)), 
                                  description="Optional caption for the image")
    display_order: int = Field(default=0, description="Order for displaying images")
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=create_audit_datetime),
        description="Last update timestamp"
    )
    
    # Relationships
    property: Optional["Property"] = Relationship(back_populates="images")

