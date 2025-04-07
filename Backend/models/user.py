from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String

if TYPE_CHECKING:
    from Backend.models.property import Property
    from Backend.models.lease import Lease
    from Backend.models.vendor import Vendor
    from Backend.models.message import Message, Conversation, ConversationParticipant

class UserType(str, Enum):
    ADMIN = "ADMIN"
    LANDLORD = "LANDLORD"
    TENANT = "TENANT"
    VENDOR = "VENDOR"

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    first_name: str
    last_name: str
    user_type: str = Field(sa_column=Column(String))  # <-- force String instead of Enum
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    properties: List["Property"] = Relationship(back_populates="owner", sa_relationship_kwargs={"lazy": "selectin"})
    leases: List["Lease"] = Relationship(back_populates="tenant", sa_relationship_kwargs={"lazy": "selectin"})
    vendor_details: Optional["Vendor"] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "selectin"})
    
    sent_messages: List["Message"] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"foreign_keys": "Message.sender_id", "lazy": "selectin"}
    )
    received_messages: List["Message"] = Relationship(
        back_populates="recipient",
        sa_relationship_kwargs={"foreign_keys": "Message.recipient_id", "lazy": "selectin"}
    )
    
    conversations: List["ConversationParticipant"] = Relationship(back_populates="user")

from Backend.models import property, lease, vendor, message
