"""
Commercial property schemas aligned with properties_commercial table.
Handles retail, office, medical, restaurant, hotel/motel, and multi-tenant spaces.
"""
from typing import Optional, List, Dict, Any, Literal
from decimal import Decimal
from pydantic import Field, field_validator, model_validator

from .base import PropertyTypeDetailsBase


class CommercialPropertyDetailsBase(PropertyTypeDetailsBase):
    """
    Commercial property details base schema used for create/update.
    Excludes CAF because it is computed in the database as a generated column.
    """
    
    # ===== DISCRIMINATOR FIELD =====
    property_type: Literal['Commercial'] = Field(
        default='Commercial',
        description="Property type discriminator for union validation"
    )
    
    # ===== SPACE INFORMATION (Required) =====
    space_type: str = Field(
        ...,
        max_length=50,
        description="Type of commercial space: retail, office, medical, restaurant, hotel_motel, multi_tenant"
    )
    usable_square_feet: int = Field(
        ...,
        gt=0,
        le=1000000,
        description="Usable square footage (actual space for tenant use)"
    )
    rentable_square_feet: int = Field(
        ...,
        gt=0,
        le=1000000,
        description="Rentable square footage (includes share of common areas)"
    )
    lease_type: str = Field(
        ...,
        max_length=50,
        description="Lease structure: gross, triple_net, modified_gross"
    )
    
    # ===== COMPLIANCE & ZONING =====
    zoning_code: Optional[str] = Field(
        None,
        max_length=50,
        description="Zoning classification code"
    )
    business_licensing_compliance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Business licensing compliance information"
    )
    permitted_uses: List[str] = Field(
        default_factory=list,
        description="List of permitted business uses"
    )
    
    # ===== PHYSICAL SPECIFICATIONS =====
    ceiling_height: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        le=Decimal('100'),
        description="Ceiling height in feet"
    )
    has_loading_area: bool = Field(
        default=False,
        description="Whether property has loading area"
    )
    loading_docks_count: int = Field(
        default=0,
        ge=0,
        le=20,
        description="Number of loading docks"
    )
    loading_area_details: Optional[str] = Field(
        None,
        description="Loading area specifications and details"
    )
    signage_rights: bool = Field(
        default=False,
        description="Whether tenant has signage rights"
    )
    signage_restrictions: Optional[str] = Field(
        None,
        description="Signage restrictions and guidelines"
    )
    floor_count: int = Field(
        default=1,
        ge=1,
        le=200,
        description="Number of floors in the property"
    )
    
    # ===== INFRASTRUCTURE =====
    power_supply_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Electrical power supply specifications"
    )
    hvac_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="HVAC system details"
    )
    internet_infrastructure: Dict[str, Any] = Field(
        default_factory=dict,
        description="Internet and telecom infrastructure"
    )
    
    # ===== MANAGEMENT =====
    on_site_maintenance: bool = Field(
        default=False,
        description="Whether maintenance staff is on-site"
    )
    common_area_maintenance_fee: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        description="Monthly CAM fees"
    )
    
    # ===== VALIDATORS =====
    
    @field_validator('space_type')
    @classmethod
    def validate_space_type(cls, v: str) -> str:
        """Validate commercial space type"""
        valid_types = ['retail', 'office', 'medical', 'restaurant', 'hotel_motel', 'multi_tenant']
        lower_v = v.lower()
        # Backward compatibility: normalize historical values
        if lower_v == 'mixed':
            return 'multi_tenant'
        if lower_v in valid_types:
            return lower_v
        # Allow custom types but prefer standardized set
        return v
    
    @field_validator('lease_type')
    @classmethod
    def validate_lease_type(cls, v: str) -> str:
        """Validate lease type"""
        valid_types = ['gross', 'triple_net', 'modified_gross', 'percentage', 'net', 'absolute_net', 'other']
        lower_v = v.lower().replace(' ', '_')
        if lower_v not in valid_types:
            # Allow custom types but normalize known ones
            return v
        return lower_v
    
    @field_validator('permitted_uses')
    @classmethod
    def normalize_permitted_uses(cls, v: List[str]) -> List[str]:
        """Normalize permitted use types"""
        standard_uses = {
            'retail': 'retail',
            'shop': 'retail',
            'store': 'retail',
            'office': 'office',
            'medical': 'medical',
            'healthcare': 'medical',
            'restaurant': 'restaurant',
            'food': 'restaurant',
            'cafe': 'cafe',
            'coffee': 'cafe',
            'service': 'service',
            'professional': 'professional_services',
            'light industrial': 'light_industrial',
            'storage': 'storage',
            'hotel': 'hotel_motel',
            'motel': 'hotel_motel',
        }
        
        normalized = []
        for use in v:
            if use:
                lower = use.lower().strip()
                normalized.append(standard_uses.get(lower, use))
        
        return list(set(normalized))
    
    @model_validator(mode='after')
    def validate_square_footage(self):
        """Ensure square footage values are consistent"""
        # Only validate if both values are provided (guard against None in partial updates)
        if self.rentable_square_feet is not None and self.usable_square_feet is not None:
            if self.rentable_square_feet < self.usable_square_feet:
                raise ValueError("Rentable square feet should be >= usable square feet")
        return self
    
    @model_validator(mode='after')
    def validate_loading_consistency(self):
        """Ensure loading area fields are consistent"""
        if not self.has_loading_area:
            self.loading_docks_count = 0
            self.loading_area_details = None
        elif self.has_loading_area and self.loading_docks_count == 0:
            # Has loading area but no docks - valid for ground-level loading
            pass
        
        return self
    
    @model_validator(mode='after')
    def validate_signage_consistency(self):
        """Ensure signage fields are consistent"""
        if not self.signage_rights:
            self.signage_restrictions = None
        
        return self
    
    @model_validator(mode='after')
    def validate_space_type_requirements(self):
        """Apply space type specific validations"""
        if self.space_type == 'restaurant':
            # Restaurants typically need specific infrastructure
            if not self.hvac_details:
                self.hvac_details = {"note": "Restaurant grade ventilation required"}
        
        elif self.space_type == 'medical':
            # Medical spaces have specific requirements
            if not self.business_licensing_compliance:
                self.business_licensing_compliance = {"note": "Medical licensing compliance required"}
        
        return self
    
    class Config:
        """Pydantic config"""
        json_schema_extra = {
            "example": {
                "space_type": "retail",
                "usable_square_feet": 5000,
                "rentable_square_feet": 5500,
                "lease_type": "triple_net",
                "zoning_code": "C-2",
                "permitted_uses": ["retail", "office", "service"],
                "ceiling_height": 14.5,
                "has_loading_area": True,
                "loading_docks_count": 1,
                "signage_rights": True,
                "floor_count": 1,
                "on_site_maintenance": False,
                "common_area_maintenance_fee": 250.00
            }
        }


# Main class alias for consistency with other property types
CommercialPropertyDetails = CommercialPropertyDetailsBase

# Create/Update/Response schemas
CommercialPropertyDetailsCreate = CommercialPropertyDetailsBase
CommercialPropertyDetailsUpdate = CommercialPropertyDetailsBase

class CommercialPropertyDetailsResponse(CommercialPropertyDetailsBase):
    """Response schema includes CAF computed by the database."""
    common_area_factor: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        le=Decimal('50'),
        description="Common area factor percentage"
    )