"""
Unit schemas package.

This package contains all Pydantic schemas for unit CRUD operations.
Organized by:
- unit.py: Main unit schemas (Base, Create, Update, Response, etc.)
- types/: Type-specific detail schemas (Residential, Industrial, etc.)
"""

from .unit import (
    # Mixins and validators
    UnitValidatorMixin,
    
    # Core schemas
    UnitBase,
    UnitCreate,
    UnitUpdate,
    UnitResponse,
    UnitCreateResponse,
    
    # Related schemas
    TenantInfo,
    
    # Bulk operations
    BulkUnitCreate,
    BulkUnitCreateResponse,
    
    # Search and filters
    UnitSearchFilters,
    
    # CSV bulk assignment
    CSVAssignmentRow,
    CSVBulkAssignRequest,
    CSVAssignmentError,
    CSVBulkAssignResponse,
    
    # Bulk assignment
    BulkAssignmentRequest,
    BulkAssignmentResponse,
)

from .types import (
    # Base
    UnitTypeDetailsBase,
    
    # Residential
    ResidentialUnitDetails,
    ResidentialUnitDetailsCreate,
    ResidentialUnitDetailsUpdate,
    ResidentialUnitDetailsResponse,
    
    # Industrial
    IndustrialUnitDetails,
    IndustrialUnitDetailsCreate,
    IndustrialUnitDetailsUpdate,
    IndustrialUnitDetailsResponse,
    
    # Discriminated unions
    UnitTypeDetailsCreate,
    UnitTypeDetailsUpdate,
    UnitTypeDetailsResponse,
)

__all__ = [
    # Mixins
    'UnitValidatorMixin',
    
    # Core schemas
    'UnitBase',
    'UnitCreate',
    'UnitUpdate',
    'UnitResponse',
    'UnitCreateResponse',
    
    # Related schemas
    'TenantInfo',
    
    # Bulk operations
    'BulkUnitCreate',
    'BulkUnitCreateResponse',
    
    # Search and filters
    'UnitSearchFilters',
    
    # CSV bulk assignment
    'CSVAssignmentRow',
    'CSVBulkAssignRequest',
    'CSVAssignmentError',
    'CSVBulkAssignResponse',
    
    # Bulk assignment
    'BulkAssignmentRequest',
    'BulkAssignmentResponse',
    
    # Type-specific details - Base
    'UnitTypeDetailsBase',
    
    # Type-specific details - Residential
    'ResidentialUnitDetails',
    'ResidentialUnitDetailsCreate',
    'ResidentialUnitDetailsUpdate',
    'ResidentialUnitDetailsResponse',
    
    # Type-specific details - Industrial
    'IndustrialUnitDetails',
    'IndustrialUnitDetailsCreate',
    'IndustrialUnitDetailsUpdate',
    'IndustrialUnitDetailsResponse',
    
    # Discriminated unions
    'UnitTypeDetailsCreate',
    'UnitTypeDetailsUpdate',
    'UnitTypeDetailsResponse',
]
