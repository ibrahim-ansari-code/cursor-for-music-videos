from typing import Optional, List, TYPE_CHECKING
from datetime import date, datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

if TYPE_CHECKING:
    from Backend.models.user import User
    from Backend.models.property import Property, PropertyUnit
    from Backend.models.lease import Lease

class TenantStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING = "Pending"
    EVICTED = "Evicted"
    MOVED_OUT = "Moved Out"

class Tenant(SQLModel, table=True):
    """Tenant model representing a tenant's relationship with properties and leases"""
    
    __tablename__ = "tenants"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str = Field(...)
    status: TenantStatus = Field(default=TenantStatus.PENDING)
    
    # User Association
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    
    # Contact Information
    phone: Optional[str] = None
    email: Optional[str] = None
    
    # Property Information
    current_property_id: Optional[int] = Field(default=None, foreign_key="properties.id")
    unit_id: Optional[int] = Field(default=None, foreign_key="property_units.id")
    unit: Optional[str] = None
    
    # Lease Information
    lease_start: Optional[date] = None
    lease_end: Optional[date] = None
    monthly_rent: Optional[float] = None
    
    # Additional Details
    notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional["User"] = Relationship(
        back_populates="tenant_details",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    current_property: Optional["Property"] = Relationship(
        back_populates="current_tenants",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    current_unit: Optional["PropertyUnit"] = Relationship(
        back_populates="current_tenant",
        sa_relationship_kwargs={"lazy": "selectin", "foreign_keys": "[Tenant.unit_id]"}
    )
    leases: List["Lease"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

# Avoiding circular imports - these will be imported at runtime
def setup_relationships():
    from Backend.models.property import Property, PropertyUnit
    from Backend.models.user import User
    
    # Update the Property model to include current tenants
    if not hasattr(Property, 'current_tenants'):
        Property.current_tenants = Relationship(
            back_populates="current_property",
            sa_relationship_kwargs={"lazy": "selectin"}
        )
    
    # Update User model if needed
    if not hasattr(User, 'tenant_details'):
        User.tenant_details = Relationship(
            back_populates="user",
            sa_relationship_kwargs={"lazy": "selectin"}
        ) 