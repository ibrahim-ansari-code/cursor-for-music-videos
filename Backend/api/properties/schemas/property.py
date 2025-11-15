"""
Core property schemas for create, update, and response operations.
Uses hierarchical table pattern with type-specific details.
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field

from Backend.api.units.schemas import TenantInfo, UnitCreate
from Backend.models.enums import PropertyStatus
from Backend.models.property import PropertyType
from .types import (
    PropertyTypeDetailsCreate,
    PropertyTypeDetailsUpdate,
    PropertyTypeDetailsResponse,
)


# ===== BASE SCHEMAS =====

class PropertyBase(BaseModel):
    """Shared base schema for property operations"""
    name: str = Field(..., min_length=1, max_length=255, description="Property name")
    address: str = Field(..., min_length=1, max_length=500, description="Street address")
    city: str = Field(..., min_length=1, max_length=100, description="City name")
    province: str = Field(..., min_length=2, max_length=50, description="Province/State")
    postal_code: str = Field(..., min_length=3, max_length=20, description="Postal/ZIP code")
    description: Optional[str] = Field(None, max_length=2000, description="Property description")
    year_built: Optional[int] = Field(None, ge=1800, le=2100, description="Year of construction")
    ownership_entity_id: Optional[UUID] = Field(None, description="UUID of the ownership entity that owns this property")
    
    @field_validator("name", "address", "city", "province", "postal_code")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure string fields are not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v.strip()


# ===== CREATE SCHEMAS =====

class PropertyCreate(PropertyBase):
    """Schema for creating a new property with type-specific details"""
    property_type: PropertyType = Field(..., description="Type of property")
    status: PropertyStatus = Field(
        default=PropertyStatus.ACTIVE,
        description="Property status"
    )
    
    # Location data from Google Maps integration
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    place_id: Optional[str] = Field(None, max_length=255, description="Google Places ID")
    formatted_address: Optional[str] = Field(None, max_length=500, description="Formatted address from Google")
    google_maps_data: Optional[Dict[str, Any]] = Field(None, description="Additional Google Maps data")
    
    # Type-specific details (stored in hierarchical tables)
    type_specific_details: Optional[PropertyTypeDetailsCreate] = Field(
        None,
        description="Property type-specific details for hierarchical tables"
    )
    
    # Flexible additional data (stored in property_details JSONB)
    property_details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional flexible property data"
    )
    
    # Initial units (optional) - support both simple names and detailed units
    units: Optional[List[str]] = Field(
        None,
        description="Initial unit names to create (legacy support)"
    )
    detailed_units: Optional[List[UnitCreate]] = Field(
        None,
        description="Detailed unit data with bedrooms, bathrooms, rent, etc."
    )
    
    @model_validator(mode='after')
    def validate_units_fields(self):
        """Ensure only one units field is provided to avoid confusion"""
        if self.units and self.detailed_units:
            raise ValueError(
                "Cannot provide both 'units' and 'detailed_units'. "
                "Use 'detailed_units' for new properties with full unit data, "
                "or 'units' for simple unit name lists (legacy support)."
            )
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Maple Ridge Apartments",
                "address": "123 Main Street",
                "city": "Toronto",
                "province": "ON",
                "postal_code": "M5V 3A8",
                "property_type": "apartment_complex",
                "year_built": 2010,
                "description": "Modern 24-unit apartment complex",
                "status": "active",
                "type_specific_details": {
                    "total_units": 24,
                    "number_of_buildings": 1
                }
            }
        }
    )


# ===== UPDATE SCHEMAS =====

class PropertyUpdate(BaseModel):
    """Schema for updating property details"""
    # All fields optional for partial updates
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    province: Optional[str] = Field(None, min_length=2, max_length=50)
    postal_code: Optional[str] = Field(None, min_length=3, max_length=20)
    description: Optional[str] = Field(None, max_length=2000)
    year_built: Optional[int] = Field(None, ge=1800, le=2100)
    status: Optional[PropertyStatus] = None
    ownership_entity_id: Optional[UUID] = None
    
    # Location updates
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    place_id: Optional[str] = Field(None, max_length=255)
    formatted_address: Optional[str] = Field(None, max_length=500)
    google_maps_data: Optional[Dict[str, Any]] = None
    
    # Type-specific details update (hierarchical tables)
    type_specific_details: Optional[PropertyTypeDetailsUpdate] = None
    
    # Flexible data update
    property_details: Optional[Dict[str, Any]] = None
    
    @field_validator("name", "address", "city", "province", "postal_code")
    @classmethod
    def validate_not_empty_if_provided(cls, v: Optional[str]) -> Optional[str]:
        """Ensure string fields are not empty if provided"""
        if v is not None and not v.strip():
            raise ValueError("Field must not be empty if provided")
        return v.strip() if v else v
    
    model_config = ConfigDict(extra="forbid")  # Prevent unexpected fields


# ===== IMAGE SCHEMAS =====

class PropertyImageBase(BaseModel):
    """Base schema for property images"""
    image_type: str = Field(default="photo", max_length=50, description="Type of image")
    is_primary: bool = Field(default=False, description="Is this the primary image")
    caption: Optional[str] = Field(None, max_length=500, description="Image caption")
    display_order: int = Field(default=0, ge=0, description="Display order")


class PropertyImageCreate(PropertyImageBase):
    """Schema for creating property images"""
    pass


class PropertyImageUpdate(BaseModel):
    """Schema for updating property images"""
    image_type: Optional[str] = Field(None, max_length=50)
    is_primary: Optional[bool] = None
    caption: Optional[str] = Field(None, max_length=500)
    display_order: Optional[int] = Field(None, ge=0)


class PropertyImageResponse(PropertyImageBase):
    """Response schema for property images"""
    id: int
    property_id: int
    image_url: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ===== RESPONSE SCHEMAS =====

class OwnerResponse(BaseModel):
    """Property owner information"""
    id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    profile_image_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class UnitResponse(BaseModel):
    """Unit information within a property"""
    id: int
    name: str
    description: Optional[str] = None
    size: Optional[float] = None
    monthly_rent: Optional[Decimal] = None
    is_rented: bool
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    floor: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    tenant: Optional[TenantInfo] = None
    
    model_config = ConfigDict(from_attributes=True)


class PropertyStats(BaseModel):
    """Calculated property statistics"""
    total_units: int = 0
    vacant_units: int = 0
    occupied_units: int = 0
    monthly_revenue: Decimal = Field(default=Decimal("0.00"))
    occupancy_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    
    model_config = ConfigDict(from_attributes=True)


class PropertyResponse(BaseModel):
    """Basic property response"""
    id: int
    name: str
    address: str
    city: str
    province: str
    postal_code: str
    property_type: PropertyType
    description: Optional[str] = None
    year_built: Optional[int] = None
    status: PropertyStatus
    ownership_entity_id: Optional[UUID] = None

    # Location data
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None
    formatted_address: Optional[str] = None
    google_maps_data: Optional[Dict[str, Any]] = None

    # Property details (from JSONB and hierarchical tables)
    property_details: Optional[Dict[str, Any]] = None
    type_specific_details: Optional[PropertyTypeDetailsResponse] = None

    # Relations
    images: List[PropertyImageResponse] = Field(default_factory=list)
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class PropertyDetailResponse(PropertyResponse):
    """Detailed property response with additional relations"""
    owner: Optional[OwnerResponse] = None
    units: List[UnitResponse] = Field(default_factory=list)
    stats: Optional[PropertyStats] = None
    
    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


# ===== BULK DELETE SCHEMA =====

class PropertyBulkDelete(BaseModel):
    """Schema for bulk property deletion"""
    property_ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of property IDs to delete (max 100 per batch)"
    )

    @field_validator('property_ids')
    @classmethod
    def validate_property_ids(cls, v: List[int]) -> List[int]:
        """Validate property IDs are positive, unique, and within limits"""
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate property IDs are not allowed")

        # Check for positive integers only
        if any(id <= 0 for id in v):
            raise ValueError("Property IDs must be positive integers")

        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "property_ids": [1, 2, 3]
            }
        }
    )