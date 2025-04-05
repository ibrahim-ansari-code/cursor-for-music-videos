from Backend.models.user import User
from typing import Optional
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

class MessageType(str, Enum):
    DIRECT = "direct"
    ANNOUNCEMENT = "announcement"
    SYSTEM = "system"

class Message(SQLModel, table=True):
    """Message model for communication between users"""

    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    message_type: MessageType = Field(default=MessageType.DIRECT)
    is_read: bool = Field(default=False)
    read_at: Optional[datetime] = None

    # Foreign keys
    sender_id: int = Field(foreign_key="users.id")
    recipient_id: Optional[int] = Field(default=None, foreign_key="users.id")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    sender: User = Relationship(
        back_populates="sent_messages", 
        sa_relationship_kwargs={"foreign_keys": "Message.sender_id"}
    )
    recipient: Optional[User] = Relationship(
        back_populates="received_messages", 
        sa_relationship_kwargs={"foreign_keys": "Message.recipient_id"}
    )
