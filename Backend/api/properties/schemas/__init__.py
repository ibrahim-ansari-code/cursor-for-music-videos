"""
Property schemas package.
Provides all schemas for property management with hierarchical type system.
"""

# Core property schemas
from .property import (
    PropertyBase,
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyDetailResponse,
    PropertyStats,
    PropertyImageCreate,
    PropertyImageUpdate,
    PropertyImageResponse,
    OwnerResponse,
    UnitResponse,
)

# Type-specific schemas
from .types import (
    # Base
    PropertyTypeDetailsBase,
    PropertyTypeValidators,
    
    # Union types
    PropertyTypeDetailsCreate,
    PropertyTypeDetailsUpdate,
    PropertyTypeDetailsResponse,
    
    # Residential
    ResidentialPropertyDetails,
    ResidentialPropertyDetailsCreate,
    ResidentialPropertyDetailsUpdate,
    ResidentialPropertyDetailsResponse,
    
    # Apartment Complex
    ApartmentComplexPropertyDetails,
    ApartmentComplexPropertyDetailsCreate,
    ApartmentComplexPropertyDetailsUpdate,
    ApartmentComplexPropertyDetailsResponse,
    
    # Commercial
    CommercialPropertyDetails,
    CommercialPropertyDetailsCreate,
    CommercialPropertyDetailsUpdate,
    CommercialPropertyDetailsResponse,
    
    # Industrial
    IndustrialPropertyDetails,
    IndustrialPropertyDetailsCreate,
    IndustrialPropertyDetailsUpdate,
    IndustrialPropertyDetailsResponse,
    
    # Mixed Use
    MixedUsePropertyDetails,
    MixedUsePropertyDetailsCreate,
    MixedUsePropertyDetailsUpdate,
    MixedUsePropertyDetailsResponse,
)

__all__ = [
    # Core property
    'PropertyBase',
    'PropertyCreate',
    'PropertyUpdate',
    'PropertyResponse',
    'PropertyDetailResponse',
    'PropertyStats',
    
    # Images
    'PropertyImageCreate',
    'PropertyImageUpdate',
    'PropertyImageResponse',
    
    # Relations
    'OwnerResponse',
    'UnitResponse',
    
    # Type system base
    'PropertyTypeDetailsBase',
    'PropertyTypeValidators',
    'PropertyTypeDetailsCreate',
    'PropertyTypeDetailsUpdate',
    'PropertyTypeDetailsResponse',
    
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
]