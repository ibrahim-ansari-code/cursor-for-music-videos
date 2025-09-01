"""
Apartment complex property schemas aligned with properties_apartment_complex table.
Handles multi-unit residential properties with shared amenities.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import Field, field_validator, model_validator

from .base import PropertyTypeDetailsBase, PropertyTypeValidators


class ApartmentComplexPropertyDetails(PropertyTypeDetailsBase):
    """
    Apartment complex property details schema.
    Maps directly to properties_apartment_complex table.
    """
    
    # ===== BUILDING INFORMATION (Required) =====
    number_of_buildings: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Number of buildings in the complex"
    )
    total_units: int = Field(
        ...,
        ge=1,
        le=5000,
        description="Total number of units in the complex"
    )
    assigned_property_manager: Optional[str] = Field(
        None,
        max_length=200,
        description="Name of assigned property manager"
    )
    
    # ===== UNIT DISTRIBUTION =====
    unit_mix: Dict[str, int] = Field(
        default_factory=dict,
        description='Unit distribution e.g. {"studio": 20, "1br": 40, "2br": 30}'
    )
    studio_units: int = Field(default=0, ge=0, description="Number of studio units")
    one_bed_units: int = Field(default=0, ge=0, description="Number of 1-bedroom units")
    two_bed_units: int = Field(default=0, ge=0, description="Number of 2-bedroom units")
    three_bed_units: int = Field(default=0, ge=0, description="Number of 3-bedroom units")
    penthouse_units: int = Field(default=0, ge=0, description="Number of penthouse units")
    
    # ===== AMENITIES & INFRASTRUCTURE =====
    shared_amenities: List[str] = Field(
        default_factory=list,
        description="List of shared amenities: gym, pool, parking_garage, clubhouse, etc."
    )
    has_security_system: bool = Field(
        default=False,
        description="Whether complex has security system"
    )
    security_system_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Type of security system"
    )
    security_system_details: Optional[str] = Field(
        None,
        description="Additional security system details"
    )
    floor_count: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Number of floors in the tallest building"
    )
    elevator_count: int = Field(
        default=0,
        ge=0,
        le=50,
        description="Number of elevators"
    )
    parking_spaces_total: Optional[int] = Field(
        None,
        ge=0,
        description="Total parking spaces available"
    )
    
    # ===== WASTE MANAGEMENT =====
    trash_system_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Type: chute, compactor, curbside, valet"
    )
    trash_collection_schedule: Optional[str] = Field(
        None,
        max_length=200,
        description="Trash collection schedule"
    )
    trash_system_details: Optional[str] = Field(
        None,
        description="Additional trash system details"
    )
    
    # ===== MANAGEMENT & OPERATIONS =====
    property_management_company: Optional[str] = Field(
        None,
        max_length=200,
        description="Property management company name"
    )
    on_site_management: bool = Field(
        default=False,
        description="Whether management is on-site"
    )
    management_office_location: Optional[str] = Field(
        None,
        max_length=100,
        description="Management office location"
    )
    management_office_hours: Dict[str, Any] = Field(
        default_factory=dict,
        description="Office hours by day of week"
    )
    emergency_contacts: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Emergency contact list"
    )
    lease_expiry_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of lease expiries by month"
    )
    
    # ===== POLICIES & FINANCIALS =====
    pet_policy: Optional[str] = Field(
        None,
        max_length=500,
        description="Pet policy details"
    )
    utilities_included: List[str] = Field(
        default_factory=list,
        description="List of included utilities: water, trash, sewer, etc."
    )
    average_rent_by_type: Dict[str, Decimal] = Field(
        default_factory=dict,
        description="Average rent by unit type"
    )
    vacancy_rate: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        le=Decimal('100'),
        description="Current vacancy percentage"
    )
    
    # ===== MANAGEMENT CONTACTS =====
    management_contact_phone: Optional[str] = Field(
        None,
        max_length=20,
        description="Management contact phone"
    )
    management_contact_email: Optional[str] = Field(
        None,
        max_length=255,
        description="Management contact email"
    )
    
    # ===== VALIDATORS =====
    
    @field_validator('management_contact_email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format"""
        return PropertyTypeValidators.validate_email(v)
    
    @field_validator('management_contact_phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone format"""
        return PropertyTypeValidators.validate_phone(v)
    
    @field_validator('trash_system_type')
    @classmethod
    def validate_trash_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate trash system type"""
        valid_types = ['chute', 'compactor', 'curbside', 'valet', 'dumpster']
        if v and v not in valid_types:
            # Allow custom types but normalize known ones
            pass
        return v
    
    @field_validator('shared_amenities')
    @classmethod
    def normalize_amenities(cls, v: List[str]) -> List[str]:
        """Normalize amenity names"""
        standard_amenities = {
            'gym': 'gym',
            'fitness': 'gym',
            'pool': 'pool',
            'swimming pool': 'pool',
            'parking': 'parking_garage',
            'garage': 'parking_garage',
            'clubhouse': 'clubhouse',
            'lounge': 'lounge',
            'bbq': 'bbq_area',
            'playground': 'playground',
            'dog park': 'dog_park',
            'business center': 'business_center',
            'laundry': 'laundry_facility',
        }
        
        normalized = []
        for amenity in v:
            if amenity:
                lower = amenity.lower().strip()
                normalized.append(standard_amenities.get(lower, amenity))
        
        return list(set(normalized))  # Remove duplicates
    
    @model_validator(mode='after')
    def validate_unit_distribution(self):
        """Ensure unit counts are consistent"""
        # Calculate total from individual unit types
        unit_type_total = (
            self.studio_units +
            self.one_bed_units +
            self.two_bed_units +
            self.three_bed_units +
            self.penthouse_units
        )
        
        # If individual counts are provided, they should roughly match total
        if unit_type_total > 0:
            # Allow for some units not categorized (like 4BR, etc.)
            if unit_type_total > self.total_units:
                raise ValueError("Sum of unit types exceeds total units")
        
        # Validate unit_mix if provided
        if self.unit_mix:
            mix_total = sum(self.unit_mix.values())
            if mix_total > self.total_units:
                raise ValueError("Unit mix total exceeds total units")
        
        return self
    
    
    @model_validator(mode='after')
    def validate_security_consistency(self):
        """Ensure security fields are consistent"""
        if not self.has_security_system:
            self.security_system_type = None
            self.security_system_details = None
        
        return self
    
    
    class Config:
        """Pydantic config"""
        json_schema_extra = {
            "example": {
                "number_of_buildings": 2,
                "total_units": 48,
                "unit_mix": {"studio": 8, "1br": 20, "2br": 16, "3br": 4},
                "shared_amenities": ["gym", "pool", "parking_garage", "clubhouse"],
                "has_security_system": True,
                "security_system_type": "24/7 monitored",
                "elevator_count": 2,
                "parking_spaces_total": 72,
                "on_site_management": True,
                "pet_policy": "Cats and dogs under 50lbs allowed with deposit",
                "utilities_included": ["water", "trash", "sewer"]
            }
        }


# Alias for different operations
ApartmentComplexPropertyDetailsCreate = ApartmentComplexPropertyDetails
ApartmentComplexPropertyDetailsUpdate = ApartmentComplexPropertyDetails
ApartmentComplexPropertyDetailsResponse = ApartmentComplexPropertyDetails