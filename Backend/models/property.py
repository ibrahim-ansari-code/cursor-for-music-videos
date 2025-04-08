from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String

from Backend.models.user import User
from Backend.models.accounting import Expense

if TYPE_CHECKING:
    from Backend.models.lease import Lease
    from Backend.models.vendor import Vendor

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
    state: str
    zip_code: str
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
    units: List["PropertyUnit"] = Relationship(back_populates="property", sa_relationship_kwargs={"lazy": "selectin"})
    leases: List["Lease"] = Relationship(back_populates="property", sa_relationship_kwargs={"lazy": "selectin"})
    vendors: List["Vendor"] = Relationship(
        back_populates="properties", 
        link_model=PropertyVendorLink, 
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    expenses: List[Expense] = Relationship(back_populates="property", sa_relationship_kwargs={"lazy": "selectin"})

class PropertyUnit(SQLModel, table=True):
    """Unit model representing individual units within a property"""
    
    __tablename__ = "property_units"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    unit_number: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    rent_amount: float
    is_occupied: bool = Field(default=False)
    
    # Foreign keys
    property_id: int = Field(foreign_key="properties.id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    property: "Property" = Relationship(back_populates="units")
    leases: List["Lease"] = Relationship(back_populates="unit", sa_relationship_kwargs={"lazy": "selectin"})

