import logging
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Optional, Union, ClassVar
from uuid import UUID

from sqlalchemy import DateTime, String, Column, UniqueConstraint, Index, CheckConstraint, text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel
from pydantic import field_validator

from .common import IntegrationStatus, IntegrationType

if TYPE_CHECKING:
    from Backend.models.user import User

logger = logging.getLogger(__name__)

class Integration(SQLModel, table=True):
    """Model for storing user integration connections (QuickBooks, Xero, etc.)"""
    
    MAX_ERROR_COUNT: ClassVar[int] = 100

    __tablename__ = "integrations"  # type: ignore
    
    __table_args__ = (
        UniqueConstraint('user_id', 'integration_type', name='unique_user_integration'),
        Index('idx_integration_user_id', 'user_id'),
        Index('idx_integration_type', 'integration_type'),
        Index('idx_integration_user_type', 'user_id', 'integration_type'),  # Composite index for common queries
        # Static constraint to prevent schema drift.
        # NOTE: If MAX_ERROR_COUNT changes, this constraint must be
        # manually updated and a new migration generated.
        CheckConstraint(
            f'error_count BETWEEN 0 AND {MAX_ERROR_COUNT}',
            name='check_error_count_range'
        ),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    
    # Integration details
    integration_type: IntegrationType = Field(sa_column=Column(SAEnum(IntegrationType, name="integration_type_enum"), nullable=False))
    status: IntegrationStatus = Field(default=IntegrationStatus.DISCONNECTED, sa_column=Column(SAEnum(IntegrationStatus, values_callable=lambda x: [e.value for e in x]), nullable=False))
    
    # Apideck specific fields
    apideck_consumer_id: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    apideck_service_id: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    
    # Connection metadata
    connected_at: datetime | None = Field(
        default=None, 
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    last_sync_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    
    # Store any additional connection metadata as JSON
    connection_metadata: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    
    # Error tracking
    last_error: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    error_count: int = Field(default=0)
    
    # Audit fields - using both Python and database-level defaults
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), 
            nullable=False,
            server_default=text('CURRENT_TIMESTAMP')
        )
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), 
            nullable=False,
            server_default=text('CURRENT_TIMESTAMP'),
            server_onupdate=text('CURRENT_TIMESTAMP')
        )
    )

    # Relationships
    user: "User" = Relationship(back_populates="integrations")

    # Validators
    @field_validator('error_count', mode='before')
    def validate_error_count(cls, v: Optional[Union[int, str]]) -> int:
        """
        Validates and sanitizes the error_count value for the Integration model.
        
        Ensures the input is an integer between 0 and MAX_ERROR_COUNT (inclusive). Non-numeric or None values are reset to 0, and values exceeding the maximum are capped at MAX_ERROR_COUNT.
        """
        # Handle None or non-numeric values
        if v is None:
            return 0
        
        try:
            v_int = int(v)  # Ensure it's an integer
        except (ValueError, TypeError):
            logger.warning("Invalid error_count value received: %s, defaulting to 0", v)
            return 0
        
        if v_int > cls.MAX_ERROR_COUNT:
            logger.warning(
                "error_count capped at MAX_ERROR_COUNT (%s). Previous: %s",
                cls.MAX_ERROR_COUNT, v_int
            )
            return cls.MAX_ERROR_COUNT
        
        return max(0, v_int)  # Ensure non-negative

