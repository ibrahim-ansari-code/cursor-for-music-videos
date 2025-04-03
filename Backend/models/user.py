from typing import Optional, List
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

class UserType(str, Enum):
    ADMIN = "admin"
    LANDLORD = "landlord"
    TENANT = "tenant"
    VENDOR = "vendor"

class User(SQLModel, table=True):
    """User model for all types of users in the system"""
    
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    first_name: str
    last_name: str
    user_type: UserType
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships based on user type
    # A user can be associated with multiple properties (if landlord)
    properties: List["Property"] = Relationship(back_populates="owner", sa_relationship_kwargs={"lazy": "selectin"})
    
    # A user can have multiple leases (if tenant)
    leases: List["Lease"] = Relationship(back_populates="tenant", sa_relationship_kwargs={"lazy": "selectin"})
    
    # A user can be a vendor with vendor details
    vendor_details: Optional["Vendor"] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "selectin"})
    
    # A user can send and receive messages
    sent_messages: List["Message"] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"foreign_keys": "Message.sender_id", "lazy": "selectin"}
    )
    received_messages: List["Message"] = Relationship(
        back_populates="recipient",
        sa_relationship_kwargs={"foreign_keys": "Message.recipient_id", "lazy": "selectin"}
    )
