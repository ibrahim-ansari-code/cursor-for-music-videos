"""
DELETE operation tests for properties API.
Tests for deleting properties with various conditions and constraints.
"""

from .test_apartment_complex_delete import TestApartmentComplexPropertyDelete
from .test_commercial_delete import TestCommercialPropertyDelete
from .test_industrial_delete import TestIndustrialPropertyDelete
from .test_mixed_use_delete import TestMixedUsePropertyDelete
from .test_residential_delete import TestResidentialPropertyDelete

__all__ = [
    'TestApartmentComplexPropertyDelete',
    'TestCommercialPropertyDelete', 
    'TestIndustrialPropertyDelete',
    'TestMixedUsePropertyDelete',
    'TestResidentialPropertyDelete'
]