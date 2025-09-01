"""
Mixed-use property type model.
Handles properties combining residential and commercial spaces.
"""
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy import Column, String, Text, JSON, DateTime
from sqlmodel import Field, SQLModel
from Backend.utils.datetime_utils import create_audit_datetime


class PropertyMixedUse(SQLModel, table=True):
    """Mixed-use property specific details"""
    
    __tablename__ = "properties_mixed_use" # type: ignore
    
    property_id: int = Field(
        foreign_key="properties.id", 
        primary_key=True,
        ondelete="CASCADE",
        description="Link to base property"
    )
    
    # ===== SPACE DISTRIBUTION =====
    residential_square_feet: Optional[int] = Field(
        default=None,
        description="Total residential space square footage"
    )
    commercial_square_feet: Optional[int] = Field(
        default=None,
        description="Total commercial space square footage"
    )
    residential_units_count: Optional[int] = Field(
        default=None,
        description="Number of residential units"
    )
    commercial_units_count: Optional[int] = Field(
        default=None,
        description="Number of commercial units"
    )
    
    # ===== UNIT TYPES =====
    residential_unit_types: Dict[str, int] = Field(
        default_factory=dict, 
        sa_column=Column(JSON),
        description='Residential unit mix {"studio": 5, "1br": 10, "2br": 8}'
    )
    commercial_space_types: List[str] = Field(
        default_factory=list, 
        sa_column=Column(JSON),
        description='Types of commercial spaces ["retail", "office", "restaurant"]'
    )
    
    # ===== SHARED FACILITIES =====
    shared_amenities: List[str] = Field(
        default_factory=list, 
        sa_column=Column(JSON),
        description='Shared amenities between residential and commercial'
    )
    separate_entrances: bool = Field(
        default=True,
        description="Whether residential and commercial have separate entrances"
    )
    shared_parking: bool = Field(
        default=True,
        description="Whether parking is shared between uses"
    )
    parking_spaces_total: Optional[int] = Field(
        default=None,
        description="Total parking spaces available"
    )
    
    # ===== MANAGEMENT =====
    single_management_company: bool = Field(
        default=True,
        description="Whether one company manages both residential and commercial"
    )
    management_structure: Optional[str] = Field(
        default=None, 
        sa_column=Column(Text),
        description="Description of management structure"
    )
    
    # ===== ZONING =====
    zoning_designation: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Mixed-use zoning designation"
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
