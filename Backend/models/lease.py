from Backend.models.user import User
from Backend.models.accounting import Payment
from typing import Optional, List, TYPE_CHECKING
from datetime import date, datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from Backend.models.property import Property, PropertyUnit

class LeaseStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"
    RENEWED = "RENEWED"

class Lease(SQLModel, table=True):
    """Lease model representing a rental agreement between landlord and tenant"""
    
    __tablename__ = "leases"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    start_date: date
    end_date: date
    monthly_rent: float
    security_deposit: float
    status: LeaseStatus = Field(default=LeaseStatus.DRAFT)
    
    # Additional lease terms
    is_renewable: bool = Field(default=True)
    auto_renew: bool = Field(default=False)
    rent_due_day: int = Field(default=1)  # Day of month rent is due
    late_fee_amount: Optional[float] = None
    late_fee_after_days: Optional[int] = None
    special_terms: Optional[str] = None
    
    # Foreign keys
    property_id: int = Field(foreign_key="properties.id")
    unit_id: Optional[int] = Field(default=None, foreign_key="property_units.id")
    tenant_id: int = Field(foreign_key="users.id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    property: "Property" = Relationship(back_populates="leases")  # ✅ fixed circular import
    unit: Optional["PropertyUnit"] = Relationship(back_populates="leases")
    tenant: User = Relationship(back_populates="leases")
    documents: List["LeaseDocument"] = Relationship(back_populates="lease", sa_relationship_kwargs={"lazy": "selectin"})
    payments: List[Payment] = Relationship(back_populates="lease", sa_relationship_kwargs={"lazy": "selectin"})

class LeaseDocument(SQLModel, table=True):
    """Document associated with a lease (contract, addendums, etc.)"""
    
    __tablename__ = "lease_documents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    file_path: str
    document_type: str  # contract, addendum, notice, etc.
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign keys
    lease_id: int = Field(foreign_key="leases.id")
    uploaded_by_id: int = Field(foreign_key="users.id")
    
    # Relationships
    lease: Lease = Relationship(back_populates="documents")
    uploaded_by: User = Relationship()
