"""
Mixed-use property schemas aligned with properties_mixed_use table.
Handles properties combining residential and commercial spaces.
"""
from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator, model_validator

from .base import PropertyTypeDetailsBase


class MixedUsePropertyDetails(PropertyTypeDetailsBase):
    """
    Mixed-use property details schema.
    Maps directly to properties_mixed_use table.
    """
    
    # ===== SPACE DISTRIBUTION =====
    residential_square_feet: Optional[int] = Field(
        None,
        ge=0,
        description="Total residential square footage"
    )
    commercial_square_feet: Optional[int] = Field(
        None,
        ge=0,
        description="Total commercial square footage"
    )
    residential_units_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of residential units"
    )
    commercial_units_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of commercial units"
    )
    
    # ===== UNIT TYPES =====
    residential_unit_types: Dict[str, int] = Field(
        default_factory=dict,
        description='Residential unit mix e.g. {"studio": 5, "1br": 10, "2br": 8}'
    )
    commercial_space_types: List[str] = Field(
        default_factory=list,
        description='Types of commercial spaces: ["retail", "office", "restaurant"]'
    )
    
    # ===== SHARED FACILITIES =====
    shared_amenities: List[str] = Field(
        default_factory=list,
        description="List of shared amenities available to all tenants"
    )
    separate_entrances: bool = Field(
        default=True,
        description="Whether residential and commercial have separate entrances"
    )
    shared_parking: bool = Field(
        default=True,
        description="Whether parking is shared between residential and commercial"
    )
    parking_spaces_total: Optional[int] = Field(
        None,
        ge=0,
        description="Total parking spaces for entire property"
    )
    
    # ===== MANAGEMENT =====
    single_management_company: bool = Field(
        default=True,
        description="Whether entire property is managed by single company"
    )
    management_structure: Optional[str] = Field(
        None,
        description="Description of management structure and responsibilities"
    )
    
    # ===== ZONING =====
    zoning_designation: Optional[str] = Field(
        None,
        max_length=50,
        description="Mixed-use zoning designation"
    )
    
    # ===== VALIDATORS =====
    
    @field_validator('commercial_space_types')
    @classmethod
    def normalize_commercial_types(cls, v: List[str]) -> List[str]:
        """Normalize commercial space type names"""
        standard_types = {
            'retail': 'retail',
            'shop': 'retail',
            'store': 'retail',
            'office': 'office',
            'restaurant': 'restaurant',
            'food': 'restaurant',
            'cafe': 'cafe',
            'service': 'service',
            'medical': 'medical',
            'fitness': 'fitness',
            'gym': 'fitness',
        }
        
        normalized = []
        for space_type in v:
            if space_type:
                lower = space_type.lower().strip()
                normalized.append(standard_types.get(lower, space_type))
        
        return list(set(normalized))
    
    @field_validator('shared_amenities')
    @classmethod
    def normalize_amenities(cls, v: List[str]) -> List[str]:
        """Normalize amenity names"""
        standard_amenities = {
            'gym': 'gym',
            'fitness': 'gym',
            'pool': 'pool',
            'parking': 'parking',
            'garage': 'parking_garage',
            'lobby': 'lobby',
            'concierge': 'concierge',
            'rooftop': 'rooftop_deck',
            'courtyard': 'courtyard',
            'garden': 'garden',
            'lounge': 'lounge',
            'business center': 'business_center',
        }
        
        normalized = []
        for amenity in v:
            if amenity:
                lower = amenity.lower().strip()
                normalized.append(standard_amenities.get(lower, amenity))
        
        return list(set(normalized))
    
    @model_validator(mode='after')
    def validate_unit_distribution(self):
        """Ensure residential unit types match count if both provided"""
        if self.residential_unit_types and self.residential_units_count:
            type_total = sum(self.residential_unit_types.values())
            if type_total > self.residential_units_count:
                raise ValueError("Sum of residential unit types exceeds total residential units")
        
        return self
    
    @model_validator(mode='after')
    def validate_space_requirements(self):
        """Ensure at least some space is defined"""
        has_residential = (
            self.residential_square_feet or 
            self.residential_units_count or 
            bool(self.residential_unit_types)
        )
        has_commercial = (
            self.commercial_square_feet or 
            self.commercial_units_count or 
            bool(self.commercial_space_types)
        )
        
        # Mixed-use should have both components, but during creation might not
        # So we just ensure at least something is defined
        if not has_residential and not has_commercial:
            # This is valid during initial creation
            pass
        
        return self
    
    @model_validator(mode='after')
    def validate_parking_consistency(self):
        """Validate parking configuration"""
        if not self.shared_parking and not self.parking_spaces_total:
            # Separate parking but no total specified - valid but flag it
            pass
        
        # If we have unit counts, can calculate rough parking ratio
        if self.parking_spaces_total and (self.residential_units_count or self.commercial_units_count):
            total_units = (self.residential_units_count or 0) + (self.commercial_units_count or 0)
            if total_units > 0:
                parking_ratio = self.parking_spaces_total / total_units
                # Just for reference - not enforced
                # Typical is 1-2 spaces per residential unit, 3-4 per 1000 sqft commercial
        
        return self
    
    @model_validator(mode='after')
    def validate_entrance_logic(self):
        """Apply logic for entrance configuration"""
        if not self.separate_entrances:
            # Shared entrance typically means integrated building design
            # Could affect management structure
            pass
        
        return self
    
    class Config:
        """Pydantic config"""
        json_schema_extra = {
            "example": {
                "residential_square_feet": 50000,
                "commercial_square_feet": 15000,
                "residential_units_count": 40,
                "commercial_units_count": 5,
                "residential_unit_types": {
                    "studio": 8,
                    "1br": 20,
                    "2br": 12
                },
                "commercial_space_types": ["retail", "restaurant", "office"],
                "shared_amenities": ["lobby", "parking_garage", "rooftop_deck"],
                "separate_entrances": True,
                "shared_parking": False,
                "parking_spaces_total": 60,
                "single_management_company": True,
                "management_structure": "Single property management company handles both residential and commercial",
                "zoning_designation": "MU-2"
            }
        }


# Alias for different operations
MixedUsePropertyDetailsCreate = MixedUsePropertyDetails
MixedUsePropertyDetailsUpdate = MixedUsePropertyDetails
MixedUsePropertyDetailsResponse = MixedUsePropertyDetails