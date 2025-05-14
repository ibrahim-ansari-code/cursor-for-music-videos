from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, Enum as PgEnum, Integer, ForeignKey

from Backend.models.user import User
from Backend.models.tenant import TenantUnitLink
from Backend.models.enums import PropertyStatus

if TYPE_CHECKING:
    from Backend.models.lease import Lease
    from Backend.models.tenant import Tenant
    from Backend.models.accounting import Expense

class PropertyType(str, Enum):
    RESIDENTIAL = "Residential"
    COMMERCIAL = "Commercial"
    INDUSTRIAL = "Industrial"
    LAND = "Land"
    SPECIAL_PURPOSE = "Special Purpose"
    MIXED_USE = "Mixed-Use"
    OTHER = "Other" # Added an "Other" category

class Property(SQLModel, table=True):
    """Property model representing a real estate property"""
    
    __tablename__ = "properties"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(255)), description="Name of the property (max 255 chars)")
    address: str = Field(sa_column=Column(String(255)), description="Street address (max 255 chars)")
    city: str = Field(sa_column=Column(String(100)), description="City (max 100 chars)")
    province: str = Field(sa_column=Column(String(50)), description="Province or state (max 50 chars)")
    postal_code: str = Field(sa_column=Column(String(20)), description="Postal or ZIP code (max 20 chars)")
    property_type: str = Field(sa_column=Column(String(50)), description="Type of property (residential, commercial, etc.)")
    year_built: Optional[int] = Field(default=None, description="Year the property was built")
    description: Optional[str] = Field(default=None, sa_column=Column(String(500)), description="Optional property description (max 500 chars)")
    status: PropertyStatus = Field(
        sa_column=Column(PgEnum(PropertyStatus, name="propertystatus", create_constraint=True), nullable=False, default=PropertyStatus.ACTIVE),
        description="Status of the property (enum: ACTIVE, INACTIVE, DRAFT, ARCHIVED)"
    )
    
    # Foreign keys
    user_id: UUID = Field(
        sa_column=Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(default=datetime.utcnow), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(default=datetime.utcnow, onupdate=datetime.utcnow), description="Last update timestamp")
    
    # Relationships
    owner: Optional[User] = Relationship(back_populates="properties", sa_relationship_kwargs={"foreign_keys": "[Property.user_id]"})
    
    # Configure cascade delete for units
    units: List["PropertyUnit"] = Relationship(
        back_populates="property",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
    
    leases: List["Lease"] = Relationship(back_populates="property")
    expenses: List["Expense"] = Relationship(back_populates="property")
    
    # Relationship to current tenants (One-to-many)
    current_tenants: List["Tenant"] = Relationship(
        back_populates="current_property",
        sa_relationship_kwargs={
            "foreign_keys": "[Tenant.current_property_id]",
            "lazy": "selectin"
        }
    )

class PropertyUnit(SQLModel, table=True):
    """Unit model representing individual units within a property"""
    
    __tablename__ = "property_units"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: Optional[int] = Field(
        default=None, 
        sa_column=Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"))
    )
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenants.id") # Foreign key to the assigned tenant
    name: str = Field(index=True)
    description: Optional[str] = None
    size: Optional[float] = None
    monthly_rent: Optional[float] = None
    is_rented: bool = Field(default=False)
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    floor: Optional[int] = Field(default=None, description="The floor number of the unit")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    property: Optional[Property] = Relationship(back_populates="units")
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
    tenants: List["Tenant"] = Relationship(
        back_populates="units", 
        link_model=TenantUnitLink,
        sa_relationship_kwargs={"lazy": "selectin"}
    )

