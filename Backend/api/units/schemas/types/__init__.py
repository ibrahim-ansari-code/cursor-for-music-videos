"""
Unit type-specific detail schemas.

This module provides Pydantic schemas for different unit types, similar to
the property type details pattern. The unit_type field acts as a discriminator
for proper validation and serialization.

Each unit type has its own set of required and optional fields:
- Residential: bedrooms, bathrooms, appliances, parking, etc.
- Industrial: ownership_entity_id, additional_rent, lease_structure, etc.

The discriminated union allows FastAPI to automatically validate and route
to the correct schema based on the unit_type field.
"""
from typing import Union, Annotated
from pydantic import Field

from .base import UnitTypeDetailsBase
from .residential import (
    ResidentialUnitDetails,
    ResidentialUnitDetailsCreate,
    ResidentialUnitDetailsUpdate,
    ResidentialUnitDetailsResponse
)
from .industrial import (
    IndustrialUnitDetails,
    IndustrialUnitDetailsCreate,
    IndustrialUnitDetailsUpdate,
    IndustrialUnitDetailsResponse
)

# Discriminated unions for unit type details
# The unit_type field determines which schema to use for validation

UnitTypeDetailsCreate = Annotated[
    Union[
        ResidentialUnitDetailsCreate,
        IndustrialUnitDetailsCreate
    ],
    Field(discriminator='unit_type')
]

UnitTypeDetailsUpdate = Annotated[
    Union[
        ResidentialUnitDetailsUpdate,
        IndustrialUnitDetailsUpdate
    ],
    Field(discriminator='unit_type')
]

UnitTypeDetailsResponse = Annotated[
    Union[
        ResidentialUnitDetailsResponse,
        IndustrialUnitDetailsResponse
    ],
    Field(discriminator='unit_type')
]

__all__ = [
    # Base
    'UnitTypeDetailsBase',

    # Residential
    'ResidentialUnitDetails',
    'ResidentialUnitDetailsCreate',
    'ResidentialUnitDetailsUpdate',
    'ResidentialUnitDetailsResponse',

    # Industrial
    'IndustrialUnitDetails',
    'IndustrialUnitDetailsCreate',
    'IndustrialUnitDetailsUpdate',
    'IndustrialUnitDetailsResponse',

    # Discriminated unions
    'UnitTypeDetailsCreate',
    'UnitTypeDetailsUpdate',
    'UnitTypeDetailsResponse',
]
