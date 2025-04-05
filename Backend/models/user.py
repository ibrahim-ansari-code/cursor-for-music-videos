from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from Backend.models.property import Property
    from Backend.models.lease import Lease
    from Backend.models.vendor import Vendor
    from Backend.models.message import Message  # Only keeping Message if needed for sent/received messages

class UserType(str, Enum):
    ADMIN = "admin"
    LANDLORD = "landlord"
    TENANT = "tenant"
    VENDOR = "vendor"

class User(SQLModel, table=True):
    """User model for authentication and authorization"""
    
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships based on user type
    properties: List["Property"] = Relationship(back_populates="owner", sa_relationship_kwargs={"lazy": "selectin"})
    leases: List["Lease"] = Relationship(back_populates="tenant", sa_relationship_kwargs={"lazy": "selectin"})
    vendor_details: Optional["Vendor"] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "selectin"})

    # Optional: Keep message relationships only if you're actively using messaging now
    # sent_messages: List["Message"] = Relationship(
    #     back_populates="sender",
    #     sa_relationship_kwargs={"foreign_keys": "Message.sender_id", "lazy": "selectin"}
    # )
    # received_messages: List["Message"] = Relationship(
    #     back_populates="recipient",
    #     sa_relationship_kwargs={"foreign_keys": "Message.recipient_id", "lazy": "selectin"}
    # )

from Backend.models import property, lease, vendor
