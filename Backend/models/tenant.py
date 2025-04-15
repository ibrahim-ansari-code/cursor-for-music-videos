from typing import Optional, List, TYPE_CHECKING
from datetime import date, datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
from sqlalchemy import Column, String, Integer, ForeignKey, Table

if TYPE_CHECKING:
    from Backend.models.user import User
    from Backend.models.property import Property, PropertyUnit
    from Backend.models.lease import Lease

class TenantStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING = "Pending"
    EVICTION = "Eviction"

# Link table for tenant-unit many-to-many relationship
class TenantUnitLink(SQLModel, table=True):
    """Link table for tenant to unit relationship"""
    __tablename__ = "tenant_unit_link"
    
    tenant_id: Optional[int] = Field(
        default=None, foreign_key="tenants.id", primary_key=True
    )
    unit_id: Optional[int] = Field(
        default=None, foreign_key="property_units.id", primary_key=True
    )
    assigned_date: datetime = Field(default_factory=datetime.utcnow)
    is_primary: bool = Field(default=True)
    
    # Relationship fields will be set up in setup_relationships function

class Tenant(SQLModel, table=True):
    """Model representing a tenant's information"""
    __tablename__ = "tenants"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(foreign_key="users.id", index=True, default=None)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    phone: Optional[str] = None
    email: Optional[str] = None
    status: TenantStatus = Field(default=TenantStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Optional foreign key for current property
    current_property_id: Optional[int] = Field(default=None, foreign_key="properties.id")
    
    # Direct relationship definitions - adding leases here
    leases: List["Lease"] = Relationship(back_populates="tenant")
    
    # Other relationships will be set up in setup_relationships function

# This function will be called after all models are defined
# to avoid circular import issues
def setup_relationships():
    from Backend.models.property import PropertyUnit, setup_property_relationships
    from Backend.models.lease import Lease
    from Backend.models.user import User, setup_user_relationships
    
    # Set up tenant links
    TenantUnitLink.tenant = Relationship(
        back_populates="unit_links"
    )
    TenantUnitLink.unit = Relationship(
        back_populates="tenant_links"
    )
    
    # Set up tenant relationships
    Tenant.user = Relationship(
        back_populates="tenant_details",
        sa_relationship_kwargs={
            "primaryjoin": "Tenant.user_id==User.id"
        }
    )
    
    Tenant.unit_links = Relationship(
        back_populates="tenant"
    )
    
    # Add relationship to current property
    Tenant.current_property = Relationship(
        back_populates="current_tenants", 
        sa_relationship_kwargs={
            "foreign_keys": [Tenant.current_property_id]
        }
    )
    
    # Set up units relationship for Tenant
    Tenant.units = Relationship(
        back_populates="tenants",
        sa_relationship_kwargs={
            "secondary": "tenant_unit_link"
        }
    )
    
    # Set up user relationships
    setup_user_relationships()
    
    # Now set up property relationships
    setup_property_relationships() 