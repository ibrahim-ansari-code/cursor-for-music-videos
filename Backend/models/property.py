from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String

from Backend.models.user import User

if TYPE_CHECKING:
    from Backend.models.lease import Lease
    from Backend.models.vendor import Vendor
    from Backend.models.tenant import Tenant, TenantUnitLink
    from Backend.models.accounting import Expense

class PropertyStatus(str, Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    VACANT = "vacant"

class PropertyVendorLink(SQLModel, table=True):
    """Link table for properties and vendors (many-to-many)"""
    
    __tablename__ = "property_vendor_links"
    
    property_id: int = Field(foreign_key="properties.id", primary_key=True)
    vendor_id: int = Field(foreign_key="vendors.id", primary_key=True)
    
    # Additional metadata about the relationship can be added here
    start_date: Optional[datetime] = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

class Property(SQLModel, table=True):
    """Property model representing a real estate property"""
    
    __tablename__ = "properties"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: str
    city: str
    province: str
    postal_code: str
    property_type: str  # residential, commercial, etc.
    year_built: Optional[int] = None
    description: Optional[str] = None
    status: str = Field(sa_column=Column(String), default=PropertyStatus.ACTIVE)  # Using String column to store enum
    
    # Foreign keys
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    owner: Optional[User] = Relationship(back_populates="properties")
    units: List["PropertyUnit"] = Relationship(back_populates="property")
    leases: List["Lease"] = Relationship(back_populates="property")
    vendors: List["Vendor"] = Relationship(
        back_populates="properties",
        sa_relationship_kwargs={
            "secondary": "property_vendor_links"
        }
    )
    expenses: List["Expense"] = Relationship(back_populates="property")
    
    # current_tenants relationship will be set up in the setup_relationships function

class PropertyUnit(SQLModel, table=True):
    """Unit model representing individual units within a property"""
    
    __tablename__ = "property_units"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: Optional[int] = Field(default=None, foreign_key="properties.id")
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
    property: Optional["Property"] = Relationship(back_populates="units")
    leases: List["Lease"] = Relationship(back_populates="unit")
    
# Function to initialize relationships that would otherwise cause circular imports
def setup_property_relationships():
    from Backend.models.tenant import Tenant, TenantUnitLink
    
    # Add tenant relationships to PropertyUnit
    PropertyUnit.tenants = Relationship(
        back_populates="units",
        sa_relationship_kwargs={
            "secondary": "tenant_unit_link"
        }
    )
    
    PropertyUnit.tenant_links = Relationship(
        back_populates="unit"
    )
    
    # Set up current_tenants relationship for Property
    Property.current_tenants = Relationship(
        back_populates="current_property",
        sa_relationship_kwargs={
            "foreign_keys": [Tenant.current_property_id]
        }
    )

