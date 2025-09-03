"""
Residential property schemas aligned with properties_residential table.
Clean, focused implementation matching database model.
"""
from typing import Optional, List, Literal
from decimal import Decimal
from pydantic import Field, field_validator, model_validator

from .base import PropertyTypeDetailsBase, PropertyTypeValidators


class ResidentialPropertyDetails(PropertyTypeDetailsBase):
    """
    Residential property details schema.
    Maps directly to properties_residential table.
    """
    
    # ===== DISCRIMINATOR FIELD =====
    property_type: Literal['Residential'] = Field(
        default='Residential',
        description="Property type discriminator for union validation"
    )
    
    # ===== LIVING SPACES (Core Requirements) =====
    bedrooms: int = Field(
        ..., 
        ge=0, 
        le=20, 
        description="Number of bedrooms"
    )
    bathrooms: Decimal = Field(
        ..., 
        ge=Decimal('0'), 
        le=Decimal('20'),
        description="Number of bathrooms (supports 0.5 increments)"
    )
    square_feet: Optional[int] = Field(
        None, 
        gt=0, 
        le=50000,
        description="Living area square footage"
    )
    lot_size: Optional[int] = Field(
        None, 
        gt=0, 
        le=1000000,
        description="Lot size in square feet"
    )
    stories: int = Field(
        default=1, 
        ge=1, 
        le=5, 
        description="Number of stories/floors"
    )
    
    # ===== PARKING =====
    garage_spaces: int = Field(
        default=0, 
        ge=0, 
        le=10,
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
        None,
        max_length=50,
        description="Type of heating: forced_air, radiant, baseboard, heat_pump"
    )
    cooling_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Type of cooling: central_air, window_units, evaporative, none"
    )
    water_heater_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Type of water heater: tank, tankless, solar, heat_pump"
    )
    
    # ===== PROPERTY DETAILS =====
    property_subtype: Optional[str] = Field(
        None,
        max_length=50,
        description="Property subtype: single_family, townhouse, condo, duplex, manufactured, mobile_home"
    )
    roof_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Roof type: shingle, tile, metal, flat, slate"
    )
    exterior_material: Optional[str] = Field(
        None,
        max_length=50,
        description="Primary exterior: brick, vinyl_siding, wood, stucco, stone, fiber_cement"
    )
    
    # ===== VALIDATORS =====
    
    @field_validator('bathrooms')
    @classmethod
    def validate_bathrooms(cls, v: Decimal) -> Decimal:
        """Ensure bathrooms are in 0.5 increments"""
        if v % Decimal('0.5') != 0:
            raise ValueError("Bathrooms must be in 0.5 increments (e.g., 1, 1.5, 2, 2.5)")
        return v
    
    @field_validator('property_subtype')
    @classmethod
    def validate_property_subtype(cls, v: Optional[str]) -> Optional[str]:
        """Validate property subtype"""
        valid_subtypes = [
            'single_family', 'townhouse', 'condo', 
            'duplex', 'manufactured', 'mobile_home'
        ]
        if v and v not in valid_subtypes:
            raise ValueError(f"Property subtype must be one of: {', '.join(valid_subtypes)}")
        return v
    
    @field_validator('heating_type')
    @classmethod
    def validate_heating_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate heating system type"""
        valid_types = ['forced_air', 'radiant', 'baseboard', 'heat_pump', 'electric', 'gas', 'oil']
        if v and v not in valid_types:
            # Allow but log non-standard types
            pass  # Could add logging here
        return v
    
    @field_validator('cooling_type')
    @classmethod
    def validate_cooling_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate cooling system type"""
        valid_types = ['central_air', 'window_units', 'evaporative', 'mini_split', 'none']
        if v and v not in valid_types:
            # Allow but log non-standard types
            pass  # Could add logging here
        return v
    
    @model_validator(mode='after')
    def validate_property_logic(self):
        """Apply property-specific business logic"""
        # Condo-specific logic
        if self.property_subtype == 'condo':
            # Condos typically don't have separate lot sizes
            if self.lot_size and not self.square_feet:
                # If only lot_size provided, treat as square_feet
                self.square_feet = self.lot_size
                self.lot_size = None
            elif self.lot_size == self.square_feet:
                # If they're the same, clear lot_size
                self.lot_size = None
        
        # Manufactured/Mobile home logic
        if self.property_subtype in ['manufactured', 'mobile_home']:
            # These are typically single story
            if self.stories > 2:
                self.stories = 1
        
        # Townhouse logic
        if self.property_subtype == 'townhouse':
            # Townhouses typically have 2-3 stories
            if not self.stories:
                self.stories = 2
        
        return self
    
    class Config:
        """Pydantic config"""
        json_schema_extra = {
            "example": {
                "bedrooms": 3,
                "bathrooms": 2.5,
                "square_feet": 2000,
                "lot_size": 7500,
                "stories": 2,
                "garage_spaces": 2,
                "has_driveway": True,
                "street_parking": False,
                "property_subtype": "single_family",
                "heating_type": "forced_air",
                "cooling_type": "central_air",
                "water_heater_type": "tank",
                "roof_type": "shingle",
                "exterior_material": "brick"
            }
        }


# Alias for different operations (all use same schema now)
ResidentialPropertyDetailsCreate = ResidentialPropertyDetails
ResidentialPropertyDetailsUpdate = ResidentialPropertyDetails
ResidentialPropertyDetailsResponse = ResidentialPropertyDetails