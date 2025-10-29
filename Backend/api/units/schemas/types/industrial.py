"""
Industrial unit type details schema.
Defines fields specific to industrial units (warehouses, manufacturing, flex spaces, etc.)

Note: Ownership entity is now tracked at the property level, not the unit level.
"""
from typing import Optional, Literal
from decimal import Decimal
from pydantic import Field, field_validator, model_validator

from .base import UnitTypeDetailsBase


class LeaseStructureType(str):
    """Lease structure types for industrial/commercial leases"""
    NNN = "NNN"  # Triple Net
    GROSS = "Gross"
    MODIFIED_GROSS = "Modified Gross"
    FULL_SERVICE = "Full Service"


class IndustrialUseType(str):
    """Types of industrial unit usage"""
    WAREHOUSE = "warehouse"
    OFFICE = "office"
    MANUFACTURING = "manufacturing"
    FLEX_SPACE = "flex_space"
    DISTRIBUTION = "distribution"
    COLD_STORAGE = "cold_storage"
    RESEARCH_DEVELOPMENT = "research_development"


class IndustrialUnitDetails(UnitTypeDetailsBase):
    """
    Industrial unit type details schema.
    Used for warehouse spaces, manufacturing floors, office spaces within industrial properties, etc.
    """

    # ===== DISCRIMINATOR FIELD =====
    unit_type: Literal['Industrial'] = Field(
        default='Industrial',
        description="Unit type discriminator for union validation"
    )

    # ===== FINANCIAL TERMS =====
    additional_rent: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        description="Additional rent beyond base rent (CAM charges, utilities, taxes, etc.)"
    )
    security_deposit: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        description="Security deposit amount"
    )
    parking_fee: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        description="Monthly parking charges"
    )
    storage_fee: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        description="Storage space charges"
    )
    additional_fees: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        description="Other miscellaneous fees"
    )

    # ===== LEASE STRUCTURE =====
    lease_structure: Optional[str] = Field(
        None,
        description="Type of lease: NNN (Triple Net), Gross, Modified Gross, Full Service"
    )

    # ===== USE TYPE =====
    use_type: Optional[str] = Field(
        None,
        description="Primary use type: warehouse, office, manufacturing, flex_space, distribution, etc."
    )

    # ===== LOADING & ACCESS =====
    loading_dock_access: bool = Field(
        default=False,
        description="Whether this unit has direct loading dock access"
    )
    drive_in_door_access: bool = Field(
        default=False,
        description="Whether this unit has drive-in door access"
    )

    # ===== UTILITIES & INFRASTRUCTURE =====
    has_separate_utilities: bool = Field(
        default=False,
        description="Whether unit has separately metered utilities"
    )

    # ===== VALIDATORS =====

    @field_validator('lease_structure')
    @classmethod
    def validate_lease_structure(cls, v: Optional[str]) -> Optional[str]:
        """Validate lease structure type"""
        if v:
            valid_structures = ['NNN', 'Gross', 'Modified Gross', 'Full Service', 'Triple Net']
            if v not in valid_structures:
                # Allow custom values but could add logging
                pass
        return v

    @field_validator('use_type')
    @classmethod
    def validate_use_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize use type"""
        if v:
            valid_types = ['warehouse', 'office', 'manufacturing', 'flex_space',
                          'distribution', 'cold_storage', 'research_development']
            lower_v = v.lower().replace(' ', '_').replace('-', '_')

            # Normalize known types
            if lower_v in valid_types:
                return lower_v
        return v

    class Config:
        """Pydantic config"""
        json_schema_extra = {
            "example": {
                "unit_type": "Industrial",
                "additional_rent": 1200.00,
                "security_deposit": 5000.00,
                "parking_fee": 200.00,
                "storage_fee": 400.00,
                "additional_fees": 200.00,
                "lease_structure": "NNN",
                "use_type": "warehouse",
                "loading_dock_access": True,
                "drive_in_door_access": False,
                "has_separate_utilities": True
            }
        }


# Aliases for different operations
IndustrialUnitDetailsCreate = IndustrialUnitDetails
IndustrialUnitDetailsUpdate = IndustrialUnitDetails
IndustrialUnitDetailsResponse = IndustrialUnitDetails
