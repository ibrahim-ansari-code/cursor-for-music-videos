from typing import Optional, List
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

class MessageType(str, Enum):
    DIRECT = "direct"
    ANNOUNCEMENT = "announcement"
    SYSTEM = "system"

class Conversation(SQLModel, table=True):
    """Conversation model for grouping messages between users"""
    
    __tablename__ = "conversations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    is_group: bool = Field(default=False)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    messages: List["Message"] = Relationship(back_populates="conversation", sa_relationship_kwargs={"lazy": "selectin"})
    participants: List["User"] = Relationship(
        back_populates="conversations",
        link_model="ConversationParticipant",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

class ConversationParticipant(SQLModel, table=True):
    """Link table for conversations and participants (many-to-many)"""
    
    __tablename__ = "conversation_participants"
    
    conversation_id: int = Field(foreign_key="conversations.id", primary_key=True)
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

class Message(SQLModel, table=True):
    """Message model for communication between users"""
    
    __tablename__ = "messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    message_type: MessageType = Field(default=MessageType.DIRECT)
    is_read: bool = Field(default=False)
    read_at: Optional[datetime] = None
    
    # Foreign keys
    conversation_id: int = Field(foreign_key="conversations.id")
    sender_id: int = Field(foreign_key="users.id")
    recipient_id: Optional[int] = Field(default=None, foreign_key="users.id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    conversation: Conversation = Relationship(back_populates="messages")
    sender: "User" = Relationship(
        back_populates="sent_messages", 
        sa_relationship_kwargs={"foreign_keys": "Message.sender_id"}
    )
    recipient: Optional["User"] = Relationship(
        back_populates="received_messages", 
        sa_relationship_kwargs={"foreign_keys": "Message.recipient_id"}
    )
