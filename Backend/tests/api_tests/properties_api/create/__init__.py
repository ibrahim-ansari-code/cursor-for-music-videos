"""
Property creation API tests organized by property type.
"""

from .test_residential_create import TestResidentialPropertyCreate
from .test_apartment_complex_create import TestApartmentComplexPropertyCreate
from .test_commercial_create import TestCommercialPropertyCreate
from .test_industrial_create import TestIndustrialPropertyCreate
from .test_mixed_use_create import TestMixedUsePropertyCreate

__all__ = [
    'TestResidentialPropertyCreate',
    'TestApartmentComplexPropertyCreate', 
    'TestCommercialPropertyCreate',
    'TestIndustrialPropertyCreate',
    'TestMixedUsePropertyCreate'
]