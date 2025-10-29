"""
Residential unit type details schema.
Defines fields specific to residential units (apartments, houses, etc.)
"""
from typing import Optional, List, Literal
from decimal import Decimal
from uuid import UUID
from pydantic import Field, field_validator

from .base import UnitTypeDetailsBase


class ResidentialUnitDetails(UnitTypeDetailsBase):
    """
    Residential unit type details schema.
    Used for apartments, houses, condos, townhouses, etc.
    """

    # ===== DISCRIMINATOR FIELD =====
    unit_type: Literal['Residential'] = Field(
        default='Residential',
        description="Unit type discriminator for union validation"
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

    # ===== APPLIANCES & AMENITIES =====
    appliances: List[str] = Field(
        default_factory=list,
        description="List of included appliances: washer, dryer, dishwasher, refrigerator, stove, microwave, etc."
    )

    # ===== PARKING =====
    parking_spot_number: Optional[str] = Field(
        None,
        max_length=50,
        description="Assigned parking spot number or identifier"
    )

    # ===== OUTDOOR SPACE =====
    has_balcony: bool = Field(
        default=False,
        description="Whether unit has a balcony/patio"
    )
    balcony_size_sqft: Optional[int] = Field(
        None,
        ge=0,
        le=1000,
        description="Balcony/patio size in square feet"
    )

    # ===== PETS =====
    pet_friendly: bool = Field(
        default=False,
        description="Whether pets are allowed in this unit"
    )
    pet_deposit: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        description="Additional pet deposit amount if applicable"
    )

    # ===== VALIDATORS =====

    @field_validator('bathrooms')
    @classmethod
    def validate_bathrooms(cls, v: Decimal) -> Decimal:
        """Ensure bathrooms are in 0.5 increments"""
        if v % Decimal('0.5') != 0:
            raise ValueError("Bathrooms must be in 0.5 increments (e.g., 1, 1.5, 2, 2.5)")
        return v

    @field_validator('appliances')
    @classmethod
    def normalize_appliances(cls, v: List[str]) -> List[str]:
        """Normalize appliance names"""
        standard_appliances = {
            'washer': 'washer',
            'washing machine': 'washer',
            'dryer': 'dryer',
            'dishwasher': 'dishwasher',
            'refrigerator': 'refrigerator',
            'fridge': 'refrigerator',
            'stove': 'stove',
            'oven': 'stove',
            'microwave': 'microwave',
            'garbage disposal': 'garbage_disposal',
            'air conditioning': 'air_conditioning',
            'ac': 'air_conditioning',
            'heating': 'heating',
        }

        normalized = []
        for appliance in v:
            if appliance:
                lower = appliance.lower().strip()
                normalized.append(standard_appliances.get(lower, appliance))

        return list(set(normalized))  # Remove duplicates

    class Config:
        """Pydantic config"""
        json_schema_extra = {
            "example": {
                "unit_type": "Residential",
                "bedrooms": 2,
                "bathrooms": 1.5,
                "appliances": ["washer", "dryer", "dishwasher", "refrigerator", "stove"],
                "parking_spot_number": "A-12",
                "has_balcony": True,
                "balcony_size_sqft": 80,
                "pet_friendly": True,
                "pet_deposit": 500.00
            }
        }


# Aliases for different operations
ResidentialUnitDetailsCreate = ResidentialUnitDetails
ResidentialUnitDetailsUpdate = ResidentialUnitDetails
ResidentialUnitDetailsResponse = ResidentialUnitDetails
