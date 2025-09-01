"""
Land property type model.
Placeholder for future implementation.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import Column, Numeric, JSON, DateTime, Text
from sqlmodel import Field, SQLModel
from Backend.utils.datetime_utils import create_audit_datetime


class PropertyLand(SQLModel, table=True):
    """Land property specific details - placeholder"""
    
    __tablename__ = "properties_land"
    
    property_id: int = Field(
        foreign_key="properties.id", 
        primary_key=True,
        ondelete="CASCADE",
        description="Link to base property"
    )
    
    # Basic land field
    total_acres: Decimal = Field(
        sa_column=Column(Numeric(10, 2)),
        description="Total acreage of the land"
    )
    
    # Flexible storage for future fields
    additional_details: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Additional land details"
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

