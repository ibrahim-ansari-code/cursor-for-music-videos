from typing import Optional, List, TYPE_CHECKING
from datetime import date, datetime
from uuid import UUID
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
from sqlalchemy import Column, String, Integer, ForeignKey

# Use TYPE_CHECKING to avoid circular imports at runtime
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

# Link table for tenant-unit many-to-many relationship
class TenantUnitLink(SQLModel, table=True):
    __tablename__ = "tenant_unit_link"
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenants.id", primary_key=True)
    unit_id: Optional[int] = Field(default=None, foreign_key="property_units.id", primary_key=True)
    start_date: Optional[datetime] = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None

class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    )
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    phone: Optional[str] = None
    email: Optional[str] = None
    status: TenantStatus = Field(default=TenantStatus.ACTIVE, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    current_property_id: Optional[int] = Field(
        default=None, 
        sa_column=Column(Integer, ForeignKey("properties.id", ondelete="SET NULL"))
    )
    
    # --- Relationships Defined Directly --- 
    
    # Relationship to User (Optional one-to-one or one-to-many backref)
    user: Optional["User"] = Relationship(back_populates="tenant_details") 

    # Relationship to Property (Current Property - Optional one-to-many backref)
    current_property: Optional["Property"] = Relationship(back_populates="current_tenants")
    
    # Relationship to Leases (One-to-many)
    leases: List["Lease"] = Relationship(back_populates="tenant")
    
    # Relationship to PropertyUnits (Assigned Units - One-to-many)
    assigned_units: List["PropertyUnit"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={
            "foreign_keys": "[PropertyUnit.tenant_id]", 
            "lazy": "selectin"
        }
    )

    # Relationship to PropertyUnits (Units via link table - Many-to-many)
    units: List["PropertyUnit"] = Relationship(
        back_populates="tenants", 
        link_model=TenantUnitLink, 
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    