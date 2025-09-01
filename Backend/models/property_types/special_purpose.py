"""
Special purpose property type model.
Placeholder for future implementation (churches, schools, hospitals, etc.)
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, JSON, DateTime, Text
from sqlmodel import Field, SQLModel
from Backend.utils.datetime_utils import create_audit_datetime


class PropertySpecialPurpose(SQLModel, table=True):
    """Special purpose property specific details - placeholder"""
    
    __tablename__ = "properties_special_purpose"
    
    property_id: int = Field(
        foreign_key="properties.id", 
        primary_key=True,
        ondelete="CASCADE",
        description="Link to base property"
    )
    
    # Basic field
    special_purpose_type: str = Field(
        sa_column=Column(String(100)),
        description="Type of special purpose property"
    )
    
    # Flexible storage for future fields
    additional_details: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Additional special purpose details"
    )
    
    notes: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Additional notes"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=create_audit_datetime)
    )
