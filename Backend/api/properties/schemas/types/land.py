"""
Land property schemas aligned with properties_land table.
Handles ground leases, vacant land, and land-only properties.
"""
from typing import Optional, List, Dict, Any, Literal
from decimal import Decimal
from datetime import date
from pydantic import Field, field_validator, model_validator, ValidationInfo

from .base import PropertyTypeDetailsBase


class LandPropertyDetailsBase(PropertyTypeDetailsBase):
    """
    Land property details base schema.
    Maps directly to properties_land table.
    """
    
    # ===== DISCRIMINATOR FIELD =====
    property_type: Literal['Land'] = Field(
        default='Land',
        description="Property type discriminator for union validation"
    )
    
    # ===== LAND MEASUREMENTS =====
    total_area_sqft: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Total land area in square feet"
    )
    total_acres: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Total acreage (1 acre = 43,560 sq ft)"
    )
    leased_portion_sqft: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Leased portion in square feet (for partial land leases)"
    )
    leased_portion_percentage: Optional[Decimal] = Field(
        None,
        ge=0,
        le=100,
        description="Percentage of land being leased (0-100)"
    )
    frontage_meters: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Road frontage in meters"
    )
    depth_meters: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Lot depth in meters"
    )
    survey_date: Optional[date] = Field(
        None,
        description="Date of most recent survey"
    )
    
    @field_validator('survey_date', mode='before')
    @classmethod
    def validate_survey_date(cls, v):
        """Convert empty string to None for optional date field"""
        if v == '' or v is None:
            return None
        return v
    
    @field_validator('total_acres', mode='before')
    @classmethod
    def auto_calculate_acres(cls, v, info: ValidationInfo):
        """Auto-calculate total_acres from total_area_sqft if not provided"""
        # If acres explicitly provided, use it
        if v is not None and v != '':
            return v
        
        # Otherwise calculate from sqft (1 acre = 43,560 sq ft)
        total_sqft = info.data.get('total_area_sqft')
        if total_sqft is not None and total_sqft > 0:
            return Decimal(str(total_sqft)) / Decimal('43560')
        
        return None
    survey_reference: Optional[str] = Field(
        None,
        max_length=200,
        description="Survey plan number or reference"
    )
    survey_document_url: Optional[str] = Field(
        None,
        max_length=500,
        description="URL to uploaded survey document"
    )
    lot_numbers: Optional[str] = Field(
        None,
        max_length=200,
        description="Cadastre/lot identification numbers"
    )
    
    # ===== LAND USE & ZONING =====
    municipality: Optional[str] = Field(
        None,
        max_length=200,
        description="Municipality or regional district name"
    )
    zoning_code: Optional[str] = Field(
        None,
        max_length=100,
        description="Zoning classification code"
    )
    official_plan_designation: Optional[str] = Field(
        None,
        max_length=100,
        description="Official plan designation"
    )
    overlays_restrictions: Optional[str] = Field(
        None,
        description="Zoning overlays and restrictions"
    )
    site_plan_status: Optional[str] = Field(
        None,
        max_length=50,
        description="Site plan approval status: approved, pending, not_submitted"
    )
    permitted_uses: List[str] = Field(
        default_factory=list,
        description="List of permitted land uses"
    )
    
    # ===== GROUND LEASE SPECIFICS =====
    lease_structure: Optional[str] = Field(
        None,
        max_length=100,
        description="Lease type: ground_lease, air_rights, mineral_rights, agricultural, mixed"
    )
    allows_structures: bool = Field(
        default=False,
        description="Whether tenant can build structures"
    )
    development_rights: Optional[str] = Field(
        None,
        description="Development rights and restrictions"
    )
    signage_rights: bool = Field(
        default=False,
        description="Whether tenant has signage rights"
    )
    subletting_allowed: bool = Field(
        default=False,
        description="Whether subletting is permitted"
    )
    revenue_share_percentage: Optional[Decimal] = Field(
        None,
        ge=0,
        le=100,
        description="Revenue sharing percentage if applicable"
    )
    
    # ===== ENCUMBRANCES & LEGAL =====
    registered_covenants: Optional[str] = Field(
        None,
        description="Registered covenants and encroachments"
    )
    title_registration_province: Optional[str] = Field(
        None,
        max_length=100,
        description="Province/state where title is registered"
    )
    title_registration_number: Optional[str] = Field(
        None,
        max_length=200,
        description="Title registration number"
    )
    easements: Optional[str] = Field(
        None,
        description="Easements and access restrictions"
    )
    environmental_restrictions: Optional[str] = Field(
        None,
        description="Environmental restrictions"
    )
    
    # ===== FINANCIAL STRUCTURE =====
    assessment_roll_number: Optional[str] = Field(
        None,
        max_length=100,
        description="Municipal assessment roll number"
    )
    insurance_responsibility: Optional[str] = Field(
        None,
        max_length=50,
        description="Insurance responsibility: landlord, tenant, shared"
    )
    operating_expenses_responsibility: Optional[str] = Field(
        None,
        max_length=50,
        description="Operating expenses responsibility"
    )
    
    @model_validator(mode='before')
    @classmethod
    def convert_all_empty_strings_to_none(cls, values):
        """Convert all empty strings to None for optional fields to avoid constraint violations"""
        if isinstance(values, dict):
            for key, value in values.items():
                if value == '':
                    values[key] = None
        return values
    
    # ===== PHYSICAL FEATURES =====
    topography: Optional[str] = Field(
        None,
        max_length=50,
        description="Topography: flat, sloped, hilly, mixed"
    )
    soil_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Soil type or classification"
    )
    drainage: Optional[str] = Field(
        None,
        max_length=100,
        description="Drainage characteristics"
    )
    floodplain_indicator: bool = Field(
        default=False,
        description="Whether in floodplain zone"
    )
    brownfield_indicator: bool = Field(
        default=False,
        description="Whether classified as brownfield"
    )
    conservation_area: bool = Field(
        default=False,
        description="Whether in conservation area"
    )
    
    # ===== UTILITIES & INFRASTRUCTURE =====
    utilities_status: Dict[str, str] = Field(
        default_factory=dict,
        description="Utility connection status"
    )
    road_access: Optional[str] = Field(
        None,
        max_length=200,
        description="Road access description"
    )
    parking_spaces: Optional[int] = Field(
        None,
        ge=0,
        description="Number of parking spaces"
    )
    
    # ===== ENVIRONMENTAL ASSESSMENTS =====
    environmental_assessment_phase1: bool = Field(
        default=False,
        description="Phase I ESA completed"
    )
    environmental_assessment_phase2: bool = Field(
        default=False,
        description="Phase II ESA completed"
    )
    esa_document_urls: List[str] = Field(
        default_factory=list,
        description="Environmental assessment document URLs"
    )
    
    # ===== DOCUMENTATION & MEDIA =====
    zoning_certificate_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Zoning certificate URL"
    )
    site_plan_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Site plan document URL"
    )
    parcel_map_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Parcel map URL"
    )
    aerial_photo_urls: List[str] = Field(
        default_factory=list,
        description="Aerial photograph URLs"
    )


class LandPropertyDetailsCreate(LandPropertyDetailsBase):
    """Schema for creating land property details"""
    pass


class LandPropertyDetailsUpdate(LandPropertyDetailsBase):
    """Schema for updating land property details - all fields optional"""
    
    # Override to make all fields optional for updates
    total_area_sqft: Optional[Decimal] = None
    property_type: Literal['Land'] = 'Land'  # Still required for discriminator


class LandPropertyDetailsResponse(LandPropertyDetailsBase):
    """Schema for land property details responses"""
    pass

