from typing import Optional, List
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

class VendorStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    INACTIVE = "inactive"

class Vendor(SQLModel, table=True):
    """Vendor model for service providers (plumbers, electricians, etc.)"""
    
    __tablename__ = "vendors"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    company_name: str
    business_type: str  # plumbing, electrical, cleaning, etc.
    tax_id: Optional[str] = None
    website: Optional[str] = None
    status: VendorStatus = Field(default=VendorStatus.PENDING)
    
    # Insurance information
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    insurance_expiry_date: Optional[date] = None
    
    # Foreign keys
    user_id: int = Field(foreign_key="users.id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: "User" = Relationship(back_populates="vendor_details")
    documents: List["VendorDocument"] = Relationship(back_populates="vendor", sa_relationship_kwargs={"lazy": "selectin"})
    properties: List["Property"] = Relationship(
        back_populates="vendors", 
        link_model="PropertyVendorLink", 
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
class VendorDocument(SQLModel, table=True):
    """Documents associated with a vendor (licenses, certifications, etc.)"""
    
    __tablename__ = "vendor_documents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    file_path: str
    document_type: str  # license, certification, insurance, etc.
    expiry_date: Optional[date] = None
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign keys
    vendor_id: int = Field(foreign_key="vendors.id")
    
    # Relationships
    vendor: Vendor = Relationship(back_populates="documents")
