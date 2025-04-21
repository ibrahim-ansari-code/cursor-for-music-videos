from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from Backend.models.user import User

class MessageType(str, Enum):
    DIRECT = "direct"
    ANNOUNCEMENT = "announcement"
    SYSTEM = "system"

class Conversation(SQLModel, table=True):
    """Conversation model for grouping messages between multiple participants"""
    
    __tablename__ = "conversations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    messages: List["Message"] = Relationship(back_populates="conversation")
    participants: List["ConversationParticipant"] = Relationship(back_populates="conversation")

class ConversationParticipant(SQLModel, table=True):
    """Model for tracking participants in a conversation"""
    
    __tablename__ = "conversation_participants"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id")
    user_id: int = Field(foreign_key="users.id")
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    # Relationships
    conversation: Conversation = Relationship(back_populates="participants")
    user: "User" = Relationship(back_populates="conversations")

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
    conversation_id: Optional[int] = Field(default=None, foreign_key="conversations.id")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    sender: "User" = Relationship(
        back_populates="sent_messages", 
        sa_relationship_kwargs={"foreign_keys": "Message.sender_id"}
    )
    recipient: Optional["User"] = Relationship(
        back_populates="received_messages", 
        sa_relationship_kwargs={"foreign_keys": "Message.recipient_id"}
    )
    conversation: Optional[Conversation] = Relationship(back_populates="messages")
