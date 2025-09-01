"""
Industrial property type model.
Handles warehouses, manufacturing facilities, and distribution centers.
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
from decimal import Decimal

from sqlalchemy import Column, String, Numeric, JSON, DateTime
from sqlmodel import Field, SQLModel
from pydantic import field_validator, model_validator
from Backend.utils.datetime_utils import create_audit_datetime


class PropertyIndustrial(SQLModel, table=True):
    """Industrial property specific details"""
    
    __tablename__ = "properties_industrial" # type: ignore
    
    property_id: int = Field(
        foreign_key="properties.id", 
        primary_key=True,
        ondelete="CASCADE",
        description="Link to base property"
    )
    
    # ===== FACILITY TYPE =====
    industrial_type: str = Field(
        description="Type of industrial facility: warehouse, distribution, manufacturing, flex, cold_storage, data_center, light_industrial, rd_tech"
    )
    
    # ===== SPACE SPECIFICATIONS =====
    total_square_feet: int = Field(
        gt=0,
        description="Total square footage of the facility"
    )
    warehouse_square_feet: Optional[int] = Field(
        default=None,
        description="Warehouse/storage space square footage"
    )
    office_square_feet: Optional[int] = Field(
        default=None,
        description="Office space square footage"
    )
    manufacturing_square_feet: Optional[int] = Field(
        default=None,
        description="Manufacturing/production space square footage"
    )
    clear_height: Optional[Decimal] = Field(
        default=None, 
        sa_column=Column(Numeric(5, 2)),
        description="Clear ceiling height in feet"
    )
    
    # ===== LOADING & ACCESS =====
    loading_docks_count: int = Field(
        default=0,
        description="Number of loading docks"
    )
    drive_in_doors_count: int = Field(
        default=0,
        description="Number of drive-in/grade-level doors"
    )
    rail_access: bool = Field(
        default=False,
        description="Whether property has rail spur access"
    )
    truck_court_size: Optional[int] = Field(
        default=None,
        description="Truck court/maneuvering area in square feet"
    )
    
    # ===== INFRASTRUCTURE =====
    power_capacity: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Electrical capacity (e.g., 2000 amps)"
    )
    power_voltage: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Available voltage (e.g., 480V 3-phase)"
    )
    has_crane: bool = Field(
        default=False,
        description="Whether facility has overhead crane"
    )
    crane_capacity: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Crane capacity (e.g., 10 tons)"
    )
    sprinkler_system_type: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Type of sprinkler system (esfr, wet, dry)"
    )
    
    # ===== ENVIRONMENTAL =====
    environmental_compliance: Dict[str, Any] = Field(
        default_factory=dict, 
        sa_column=Column(JSON),
        description='Environmental compliance certifications and status'
    )
    hazmat_storage_permitted: bool = Field(
        default=False,
        description="Whether hazardous materials storage is permitted"
    )
    
    # ===== ZONING & USE =====
    zoning_classification: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(50)),
        description="Industrial zoning classification"
    )
    permitted_uses: List[str] = Field(
        default_factory=list, 
        sa_column=Column(JSON),
        description='List of permitted industrial uses'
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

    @field_validator('industrial_type')
    @classmethod
    def validate_industrial_type(cls, v: str) -> str:
        """Validate industrial type against allowed values."""
        valid_types = {
            'warehouse', 'distribution', 'manufacturing', 'flex', 
            'cold_storage', 'data_center', 'light_industrial', 'rd_tech'
        }
        if v not in valid_types:
            raise ValueError(f"Industrial type must be one of: {', '.join(sorted(valid_types))}")
        return v
    
    @model_validator(mode='after')
    def validate_space_consistency(self):
        """Validate that total square feet matches sum of component spaces when provided."""
        warehouse = self.warehouse_square_feet or 0
        office = self.office_square_feet or 0  
        manufacturing = self.manufacturing_square_feet or 0
        
        # Only validate if at least one component space is provided
        if warehouse > 0 or office > 0 or manufacturing > 0:
            component_sum = warehouse + office + manufacturing
            if component_sum != self.total_square_feet:
                raise ValueError(
                    f"Total square feet ({self.total_square_feet}) must equal sum of component spaces "
                    f"({component_sum}). Warehouse: {warehouse}, Office: {office}, Manufacturing: {manufacturing}"
                )
        
        # Validate crane_capacity consistency with has_crane
        if not self.has_crane and self.crane_capacity:
            raise ValueError("crane_capacity should only be set when has_crane is True")
        
        return self

