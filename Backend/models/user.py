from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, ForeignKey
from sqlalchemy.sql import join

if TYPE_CHECKING:
    from Backend.models.property import Property
    from Backend.models.lease import Lease
    from Backend.models.vendor import Vendor
    from Backend.models.message import Message, Conversation, ConversationParticipant
    from Backend.models.tenant import Tenant

from Backend.models.enums import UserType

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

    properties: List["Property"] = Relationship(back_populates="owner")
    vendor_details: Optional["Vendor"] = Relationship(back_populates="user")
    
    sent_messages: List["Message"] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"foreign_keys": "Message.sender_id"}
    )
    received_messages: List["Message"] = Relationship(
        back_populates="recipient",
        sa_relationship_kwargs={"foreign_keys": "Message.recipient_id"}
    )
    
    # We'll set up tenant_details in the setup_user_relationships function
    
    conversations: List["ConversationParticipant"] = Relationship(back_populates="user")

# Function to set up relationships that would cause circular imports
def setup_user_relationships():
    from Backend.models.tenant import Tenant
    
    # Add relationship with the primaryjoin explicitly defined
    if not hasattr(User, "tenant_details"):
        User.tenant_details = Relationship(
            back_populates="user",
            sa_relationship_kwargs={
                "primaryjoin": "User.id==Tenant.user_id",
                "lazy": "selectin"
            }
        )
