from typing import Optional, List, TYPE_CHECKING
from datetime import date, datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

if TYPE_CHECKING:
    from Backend.models.user import User
    from Backend.models.property import Property, PropertyUnit
    from Backend.models.lease import Lease

class TenantStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"
    EVICTED = "EVICTED"
    MOVED_OUT = "MOVED_OUT"

class Tenant(SQLModel, table=True):
    """Tenant model representing a tenant's relationship with properties and leases"""
    
    __tablename__ = "tenants"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)
    status: TenantStatus = Field(default=TenantStatus.PENDING)
    
    # Contact Information
    phone_number: Optional[str] = None
    email: Optional[str] = None
    
    # Property Information
    current_property_id: Optional[int] = Field(default=None, foreign_key="properties.id")
    
    # Additional Details
    move_in_date: Optional[date] = None
    move_out_date: Optional[date] = None
    notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: "User" = Relationship(back_populates="tenant_details")
    current_property: Optional["Property"] = Relationship(
        back_populates="current_tenants",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    current_unit: Optional["PropertyUnit"] = Relationship(
        back_populates="current_tenant",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    leases: List["Lease"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

# Update the User model to include the tenant relationship
from Backend.models.user import User

User.tenant_details: Optional["Tenant"] = Relationship(
    back_populates="user",
    sa_relationship_kwargs={"lazy": "selectin"}
)

# Update the Property model to include current tenants
from Backend.models.property import Property

Property.current_tenants: List["Tenant"] = Relationship(
    back_populates="current_property",
    sa_relationship_kwargs={"lazy": "selectin"}
)

# Update the PropertyUnit model to include current tenant
from Backend.models.property import PropertyUnit

PropertyUnit.current_tenant: Optional["Tenant"] = Relationship(
    back_populates="current_unit",
    sa_relationship_kwargs={"lazy": "selectin"}
) 