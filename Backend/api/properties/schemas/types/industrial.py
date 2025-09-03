"""
Industrial property schemas aligned with properties_industrial table.
Handles warehouse, manufacturing, and distribution facilities.
"""
from typing import Optional, List, Dict, Any, Literal
from decimal import Decimal
from pydantic import Field, field_validator, model_validator

from .base import PropertyTypeDetailsBase


class IndustrialPropertyDetails(PropertyTypeDetailsBase):
    """
    Industrial property details schema.
    Maps directly to properties_industrial table.
    """
    
    # ===== DISCRIMINATOR FIELD =====
    property_type: Literal['Industrial'] = Field(
        default='Industrial',
        description="Property type discriminator for union validation"
    )
    
    # ===== FACILITY TYPE (Required) =====
    industrial_type: str = Field(
        ...,
        description="Type of industrial facility: warehouse, distribution, manufacturing, flex, cold_storage, data_center, light_industrial, rd_tech"
    )
    
    # ===== SPACE SPECIFICATIONS (Required) =====
    total_square_feet: int = Field(
        ...,
        gt=0,
        le=5000000,
        description="Total square footage of the facility"
    )
    warehouse_square_feet: Optional[int] = Field(
        None,
        ge=0,
        description="Warehouse/storage space square footage"
    )
    office_square_feet: Optional[int] = Field(
        None,
        ge=0,
        description="Office space square footage"
    )
    manufacturing_square_feet: Optional[int] = Field(
        None,
        ge=0,
        description="Manufacturing/production space square footage"
    )
    clear_height: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        le=Decimal('100'),
        description="Clear height in feet (floor to lowest obstruction)"
    )
    
    # ===== LOADING & ACCESS =====
    loading_docks_count: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Number of loading docks"
    )
    drive_in_doors_count: int = Field(
        default=0,
        ge=0,
        le=50,
        description="Number of drive-in/grade-level doors"
    )
    rail_access: bool = Field(
        default=False,
        description="Whether facility has rail spur access"
    )
    truck_court_size: Optional[int] = Field(
        None,
        ge=0,
        description="Truck court/maneuvering area in square feet"
    )
    
    # ===== INFRASTRUCTURE =====
    power_capacity: Optional[str] = Field(
        None,
        max_length=50,
        description="Electrical power capacity (e.g., '2000 amps')"
    )
    power_voltage: Optional[str] = Field(
        None,
        max_length=50,
        description="Available power voltage (e.g., '480V 3-phase')"
    )
    has_crane: bool = Field(
        default=False,
        description="Whether facility has overhead crane"
    )
    crane_capacity: Optional[str] = Field(
        None,
        max_length=50,
        description="Crane capacity (e.g., '10 ton')"
    )
    sprinkler_system_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Type of sprinkler system (esfr, wet, dry)"
    )
    
    # ===== ENVIRONMENTAL =====
    environmental_compliance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Environmental compliance certifications and details"
    )
    hazmat_storage_permitted: bool = Field(
        default=False,
        description="Whether hazardous materials storage is permitted"
    )
    
    # ===== ZONING & USE =====
    zoning_classification: Optional[str] = Field(
        None,
        max_length=50,
        description="Industrial zoning classification"
    )
    permitted_uses: List[str] = Field(
        default_factory=list,
        description="List of permitted industrial uses"
    )
    
    # ===== VALIDATORS =====
    
    @field_validator('industrial_type')
    @classmethod
    def validate_industrial_type(cls, v: str) -> str:
        """Validate industrial facility type"""
        valid_types = {'warehouse', 'distribution', 'manufacturing', 'flex', 'cold_storage', 'data_center', 'light_industrial', 'rd_tech'}
        if v not in valid_types:
            raise ValueError(f"Industrial type must be one of: {', '.join(valid_types)}")
        return v
    
    @field_validator('sprinkler_system_type')
    @classmethod
    def validate_sprinkler_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate sprinkler system type"""
        if v:
            valid_types = ['esfr', 'wet', 'dry', 'pre_action', 'deluge', 'none']
            lower_v = v.lower().replace('-', '_').replace(' ', '_')
            # Normalize known types but allow custom
            if lower_v in valid_types:
                return lower_v
        return v
    
    @field_validator('permitted_uses')
    @classmethod
    def normalize_permitted_uses(cls, v: List[str]) -> List[str]:
        """Normalize permitted industrial uses"""
        standard_uses = {
            'warehouse': 'warehouse',
            'storage': 'warehouse',
            'distribution': 'distribution',
            'logistics': 'distribution',
            'manufacturing': 'manufacturing',
            'production': 'manufacturing',
            'assembly': 'assembly',
            'light industrial': 'light_industrial',
            'heavy industrial': 'heavy_industrial',
            'flex': 'flex_space',
            'r&d': 'research_development',
            'research': 'research_development',
            'cold storage': 'cold_storage',
            'data center': 'data_center',
        }
        
        normalized = []
        for use in v:
            if use:
                lower = use.lower().strip()
                normalized.append(standard_uses.get(lower, use))
        
        return list(set(normalized))
    
    @model_validator(mode='after')
    def validate_space_distribution(self):
        """Ensure space distributions don't exceed total"""
        components = [
            self.warehouse_square_feet or 0,
            self.office_square_feet or 0,
            self.manufacturing_square_feet or 0
        ]
        
        component_total = sum(components)
        if component_total > 0 and component_total > self.total_square_feet:
            raise ValueError("Sum of space components exceeds total square feet")
        
        return self
    
    @model_validator(mode='after')
    def validate_crane_consistency(self):
        """Ensure crane fields are consistent"""
        # Only validate - don't mutate the instance
        if not self.has_crane and self.crane_capacity:
            raise ValueError("crane_capacity should only be provided when has_crane is True")
        
        return self
    
    @model_validator(mode='after')
    def validate_loading_requirements(self):
        """Validate loading dock requirements based on size"""
        # For large warehouses, recommend minimum loading
        if self.total_square_feet > 50000 and self.loading_docks_count == 0 and self.drive_in_doors_count == 0:
            # This is valid but unusual - facility might not be for distribution
            pass
        
        return self
    
    @model_validator(mode='after')
    def validate_clear_height_requirements(self):
        """Validate clear height for warehouse space"""
        if self.warehouse_square_feet and self.warehouse_square_feet > 10000:
            # Modern warehouses typically have higher clear heights
            if not self.clear_height:
                # Set a flag or default - but don't enforce
                pass
        
        return self
    
    @model_validator(mode='after')
    def validate_environmental_consistency(self):
        """Ensure environmental fields are consistent"""
        # Only validate - don't mutate the instance
        if self.hazmat_storage_permitted and not self.environmental_compliance:
            raise ValueError("environmental_compliance details must be provided when hazmat_storage_permitted is True")
        
        return self
    
    class Config:
        """Pydantic config"""
        json_schema_extra = {
            "example": {
                "total_square_feet": 100000,
                "warehouse_square_feet": 85000,
                "office_square_feet": 5000,
                "manufacturing_square_feet": 10000,
                "clear_height": 32.0,
                "loading_docks_count": 10,
                "drive_in_doors_count": 2,
                "rail_access": False,
                "truck_court_size": 15000,
                "power_capacity": "2000 amps",
                "power_voltage": "480V 3-phase",
                "has_crane": True,
                "crane_capacity": "10 ton",
                "sprinkler_system_type": "esfr",
                "hazmat_storage_permitted": False,
                "zoning_classification": "M-2",
                "permitted_uses": ["warehouse", "distribution", "light_industrial"]
            }
        }


# Alias for different operations
IndustrialPropertyDetailsCreate = IndustrialPropertyDetails
IndustrialPropertyDetailsUpdate = IndustrialPropertyDetails
IndustrialPropertyDetailsResponse = IndustrialPropertyDetails