"""
Database models for AI Agent functionality
"""
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, DateTime
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

from Backend.utils.datetime_utils import create_audit_datetime

class UserAgentThread(SQLModel, table=True):
    """
    Maps internal user_id to Azure Assistant thread_id
    
    This table maintains the relationship between our users and their
    conversation threads in Azure AI Assistant service.
    """
    __tablename__ = "user_agent_threads" # type: ignore
    
    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Foreign keys
    user_id: UUID = Field(
        foreign_key="users.id",
        index=True,
        nullable=False,
        description="User who owns this conversation thread"
    )
    
    # Azure Assistant thread ID
    thread_id: str = Field(
        index=True,
        unique=True,
        nullable=False,
        description="Azure Assistant thread ID"
    )
    
    # Metadata
    title: Optional[str] = Field(
        default=None,
        description="Optional title for the conversation"
    )
    
    # Timestamps - explicitly use timezone-aware columns
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="When the thread was created"
    )
    last_active: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="Last activity on this thread"
    )
    
    # Status
    is_active: bool = Field(
        default=True,
        description="Whether this is the user's active thread"
    )
    
    # Future: store conversation summary, tags, etc.
    conversation_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional metadata about the conversation"
    )

