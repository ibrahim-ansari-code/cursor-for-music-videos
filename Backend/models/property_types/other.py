"""
Other/custom property type model.
Catch-all for properties that don't fit standard categories.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, JSON, DateTime, Text
from sqlmodel import Field, SQLModel
from Backend.utils.datetime_utils import create_audit_datetime


class PropertyOther(SQLModel, table=True):
    """Other/custom property type details - catch-all"""
    
    __tablename__ = "properties_other"
    
    property_id: int = Field(
        foreign_key="properties.id", 
        primary_key=True,
        ondelete="CASCADE",
        description="Link to base property"
    )
    
    # Flexible Fields
    property_subtype: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(100)),
        description="Custom property subtype"
    )
    
    custom_attributes: Dict[str, Any] = Field(
        default_factory=dict, 
        sa_column=Column(JSON),
        description="Custom property attributes"
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
