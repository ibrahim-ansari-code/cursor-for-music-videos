"""
UPDATE operation tests for properties API.
Tests for updating property details and type-specific information.
"""

from .test_apartment_complex_update import TestApartmentComplexPropertyUpdate
from .test_commercial_update import TestCommercialPropertyUpdate
from .test_industrial_update import TestIndustrialPropertyUpdate
from .test_mixed_use_update import TestMixedUsePropertyUpdate
from .test_residential_update import TestResidentialPropertyUpdate

__all__ = [
    'TestApartmentComplexPropertyUpdate',
    'TestCommercialPropertyUpdate', 
    'TestIndustrialPropertyUpdate',
    'TestMixedUsePropertyUpdate',
    'TestResidentialPropertyUpdate'
]