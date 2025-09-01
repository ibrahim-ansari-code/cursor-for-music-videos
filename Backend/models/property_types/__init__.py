"""
Property type-specific models module.
Each property type has its own model file for better organization.
"""

from .apartment_complex import PropertyApartmentComplex
from .commercial import PropertyCommercial
from .residential import PropertyResidential
from .industrial import PropertyIndustrial
from .mixed_use import PropertyMixedUse
from .land import PropertyLand
from .special_purpose import PropertySpecialPurpose
from .other import PropertyOther

__all__ = [
    "PropertyApartmentComplex",
    "PropertyCommercial", 
    "PropertyResidential",
    "PropertyIndustrial",
    "PropertyMixedUse",
    "PropertyLand",
    "PropertySpecialPurpose",
    "PropertyOther",
]
