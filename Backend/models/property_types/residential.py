"""
Residential property type model.
Handles single-family homes, townhouses, condos, and other residential properties.
"""
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import Column, String, Numeric, DateTime
from sqlmodel import Field, SQLModel
from Backend.utils.datetime_utils import create_audit_datetime


class PropertyResidential(SQLModel, table=True):
    """Residential property specific details"""
    
    __tablename__ = "properties_residential" # type: ignore
    
    property_id: int = Field(
        foreign_key="properties.id", 
        primary_key=True,
        ondelete="CASCADE",
        description="Link to base property"
    )
    
    # ===== LIVING SPACES =====
    bedrooms: int = Field(
        description="Number of bedrooms"
    )
    bathrooms: Decimal = Field(
        sa_column=Column(Numeric(3, 1)),
        description="Number of bathrooms (can be partial like 2.5)"
    )
    square_feet: Optional[int] = Field(
        default=None,
        description="Living area square footage"
    )
    lot_size: Optional[int] = Field(
        default=None,
        description="Lot size in square feet"
    )
    stories: int = Field(
        default=1,
        description="Number of stories/floors"
    )
    
    # ===== PARKING =====
    garage_spaces: int = Field(
        default=0,
        description="Number of garage parking spaces"
    )
    has_driveway: bool = Field(
        default=False,
        description="Whether property has a driveway"
    )
    street_parking: bool = Field(
        default=False,
        description="Whether street parking is available"
    )
    
    # ===== SYSTEMS =====
    heating_type: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Type of heating system (forced air, radiant, baseboard, etc.)"
    )
    cooling_type: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Type of cooling system (central AC, window units, etc.)"
    )
    water_heater_type: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Type of water heater (tank, tankless, etc.)"
    )
    
    # ===== PROPERTY DETAILS =====
    property_subtype: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Subtype: single_family, townhouse, condo, mobile_home, duplex"
    )
    roof_type: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Roof type (shingle, tile, metal, flat)"
    )
    exterior_material: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Primary exterior material (brick, siding, stucco, etc.)"
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

