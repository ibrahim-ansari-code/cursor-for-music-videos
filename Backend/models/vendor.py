from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, date
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from Backend.models.user import User
    from Backend.models.property import Property, PropertyVendorLink

# Import only what's needed at runtime
from Backend.models.property import PropertyVendorLink

class VendorStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    INACTIVE = "INACTIVE"

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
    properties: List["Property"] = Relationship(
        back_populates="vendors",
        link_model=PropertyVendorLink
    )
    documents: List["VendorDocument"] = Relationship(
        back_populates="vendor"
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