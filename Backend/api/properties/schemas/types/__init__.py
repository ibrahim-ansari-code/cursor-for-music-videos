"""
Property type-specific schemas for hierarchical table pattern.
Each property type has its own table with type-specific fields.
"""
from typing import Union, Annotated
from pydantic import Field

# Base utilities
from .base import (
    PropertyTypeDetailsBase,
    PropertyTypeValidators,
)

# Residential property schemas
from .residential import (
    ResidentialPropertyDetails,
    ResidentialPropertyDetailsCreate,
    ResidentialPropertyDetailsUpdate,
    ResidentialPropertyDetailsResponse,
)

# Apartment complex schemas
from .apartment_complex import (
    ApartmentComplexPropertyDetails,
    ApartmentComplexPropertyDetailsCreate,
    ApartmentComplexPropertyDetailsUpdate,
    ApartmentComplexPropertyDetailsResponse,
)

# Commercial property schemas
from .commercial import (
    CommercialPropertyDetails,
    CommercialPropertyDetailsCreate,
    CommercialPropertyDetailsUpdate,
    CommercialPropertyDetailsResponse,
)

# Industrial property schemas
from .industrial import (
    IndustrialPropertyDetails,
    IndustrialPropertyDetailsCreate,
    IndustrialPropertyDetailsUpdate,
    IndustrialPropertyDetailsResponse,
)

# Mixed-use property schemas
from .mixed_use import (
    MixedUsePropertyDetails,
    MixedUsePropertyDetailsCreate,
    MixedUsePropertyDetailsUpdate,
    MixedUsePropertyDetailsResponse,
)

# Discriminated union types for robust polymorphic handling
PropertyTypeDetailsCreate = Annotated[
    Union[
        ApartmentComplexPropertyDetailsCreate,
        CommercialPropertyDetailsCreate,
        ResidentialPropertyDetailsCreate,
        IndustrialPropertyDetailsCreate,
        MixedUsePropertyDetailsCreate,
    ],
    Field(discriminator='property_type')
]

PropertyTypeDetailsUpdate = Annotated[
    Union[
        ApartmentComplexPropertyDetailsUpdate,
        CommercialPropertyDetailsUpdate,
        ResidentialPropertyDetailsUpdate,
        IndustrialPropertyDetailsUpdate,
        MixedUsePropertyDetailsUpdate,
    ],
    Field(discriminator='property_type')
]

PropertyTypeDetailsResponse = Annotated[
    Union[
        ApartmentComplexPropertyDetailsResponse,
        CommercialPropertyDetailsResponse,
        ResidentialPropertyDetailsResponse,
        IndustrialPropertyDetailsResponse,
        MixedUsePropertyDetailsResponse,
    ],
    Field(discriminator='property_type')
]

__all__ = [
    # Base
    'PropertyTypeDetailsBase',
    'PropertyTypeValidators',
    
    # Residential
    'ResidentialPropertyDetails',
    'ResidentialPropertyDetailsCreate',
    'ResidentialPropertyDetailsUpdate',
    'ResidentialPropertyDetailsResponse',
    
    # Apartment Complex
    'ApartmentComplexPropertyDetails',
    'ApartmentComplexPropertyDetailsCreate',
    'ApartmentComplexPropertyDetailsUpdate',
    'ApartmentComplexPropertyDetailsResponse',
    
    # Commercial
    'CommercialPropertyDetails',
    'CommercialPropertyDetailsCreate',
    'CommercialPropertyDetailsUpdate',
    'CommercialPropertyDetailsResponse',
    
    # Industrial
    'IndustrialPropertyDetails',
    'IndustrialPropertyDetailsCreate',
    'IndustrialPropertyDetailsUpdate',
    'IndustrialPropertyDetailsResponse',
    
    # Mixed Use
    'MixedUsePropertyDetails',
    'MixedUsePropertyDetailsCreate',
    'MixedUsePropertyDetailsUpdate',
    'MixedUsePropertyDetailsResponse',
    
    # Union types
    'PropertyTypeDetailsCreate',
    'PropertyTypeDetailsUpdate',
    'PropertyTypeDetailsResponse',
]