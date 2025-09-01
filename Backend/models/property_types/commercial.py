"""
Commercial property type model.
Handles retail, office, medical, restaurant, hotel/motel, and multi-tenant spaces.
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, JSON, DateTime
from sqlmodel import Field, SQLModel
from Backend.utils.datetime_utils import create_audit_datetime


class PropertyCommercial(SQLModel, table=True):
    """Commercial property specific details"""
    
    __tablename__ = "properties_commercial" # type: ignore
    
    property_id: int = Field(
        foreign_key="properties.id", 
        primary_key=True,
        ondelete="CASCADE",
        description="Link to base property"
    )
    
    # ===== SPACE INFORMATION =====
    space_type: str = Field(
        sa_column=Column(String(50)), 
        description="Type: retail, office, medical, restaurant, hotel_motel, mixed"
    )
    usable_square_feet: int = Field(
        description="Actual usable space in square feet"
    )
    rentable_square_feet: int = Field(
        description="Rentable space including common areas"
    )
    # Common Area Factor is computed, not stored
    # CAF = ((rentable_square_feet - usable_square_feet) / usable_square_feet) * 100
    lease_type: str = Field(
        sa_column=Column(String(50)), 
        description="Lease type: gross, triple_net, modified_gross, percentage, other"
    )
    
    # ===== COMPLIANCE & ZONING =====
    zoning_code: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Zoning classification code"
    )
    business_licensing_compliance: Dict[str, Any] = Field(
        default_factory=dict, 
        sa_column=Column(JSON),
        description='Compliance status and licenses'
    )
    permitted_uses: List[str] = Field(
        default_factory=list, 
        sa_column=Column(JSON),
        description='List of permitted business uses'
    )
    
    # ===== PHYSICAL SPECIFICATIONS =====
    ceiling_height: Optional[Decimal] = Field(
        default=None, 
        sa_column=Column(Numeric(5, 2)),
        description="Ceiling height in feet"
    )
    has_loading_area: bool = Field(
        default=False,
        description="Whether property has loading area"
    )
    loading_docks_count: int = Field(
        default=0,
        description="Number of loading docks"
    )
    loading_area_details: Optional[str] = Field(
        default=None, 
        sa_column=Column(Text),
        description="Loading area specifications"
    )
    signage_rights: bool = Field(
        default=False,
        description="Whether tenant has signage rights"
    )
    signage_restrictions: Optional[str] = Field(
        default=None, 
        sa_column=Column(Text),
        description="Signage restrictions and requirements"
    )
    floor_count: int = Field(
        default=1,
        description="Number of floors"
    )
    
    # ===== INFRASTRUCTURE =====
    power_supply_info: Dict[str, Any] = Field(
        default_factory=dict, 
        sa_column=Column(JSON),
        description='Power specifications {"voltage": ["120V", "240V"], "phase": "3-phase", "capacity": "400A"}'
    )
    hvac_details: Dict[str, Any] = Field(
        default_factory=dict, 
        sa_column=Column(JSON),
        description='HVAC system details'
    )
    internet_infrastructure: Dict[str, Any] = Field(
        default_factory=dict, 
        sa_column=Column(JSON),
        description='Internet/telecom infrastructure'
    )
    
    # ===== MANAGEMENT =====
    on_site_maintenance: bool = Field(
        default=False,
        description="Whether maintenance staff is on-site"
    )
    common_area_maintenance_fee: Optional[Decimal] = Field(
        default=None, 
        sa_column=Column(Numeric(12, 2)),
        description="Monthly CAM fees"
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
    
    # ===== COMPUTED PROPERTIES =====
    
    @property
    def common_area_factor(self) -> Optional[Decimal]:
        """
        Calculate Common Area Factor (CAF) as a percentage.
        CAF = ((rentable_square_feet - usable_square_feet) / usable_square_feet) * 100
        """
        if not self.usable_square_feet or self.usable_square_feet <= 0:
            return None
            
        try:
            caf = ((self.rentable_square_feet - self.usable_square_feet) / self.usable_square_feet) * 100
            return Decimal(str(round(caf, 2)))
        except (ZeroDivisionError, ValueError):
            return None

