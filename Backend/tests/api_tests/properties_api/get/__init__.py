"""
GET operation tests for properties API.
Tests for retrieving individual properties and property lists.
"""

from .test_apartment_complex_get import TestApartmentComplexPropertyGet
from .test_commercial_get import TestCommercialPropertyGet
from .test_industrial_get import TestIndustrialPropertyGet
from .test_mixed_use_get import TestMixedUsePropertyGet
from .test_residential_get import TestResidentialPropertyGet

__all__ = [
    'TestApartmentComplexPropertyGet',
    'TestCommercialPropertyGet', 
    'TestIndustrialPropertyGet',
    'TestMixedUsePropertyGet',
    'TestResidentialPropertyGet'
]