"""
Land property type model.
Supports ground leases, vacant land, and land-only properties.
"""
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from decimal import Decimal

from sqlalchemy import Column, Numeric, JSON, DateTime, Text, String, Boolean, Date
from sqlmodel import Field, SQLModel
from Backend.utils.datetime_utils import create_audit_datetime


class PropertyLand(SQLModel, table=True):
    """
    Land property specific details for ground leases, vacant land, and land parcels.
    Supports commercial ground leases (e.g., McDonald's), agricultural land, and development land.
    """
    
    __tablename__ = "properties_land"
    
    property_id: int = Field(
        foreign_key="properties.id", 
        primary_key=True,
        ondelete="CASCADE",
        description="Link to base property"
    )
    
    # ===== LAND MEASUREMENTS =====
    total_area_sqft: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(12, 2)),
        description="Total land area in square feet"
    )
    total_acres: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(10, 4)),
        description="Total acreage (1 acre = 43,560 sq ft)"
    )
    leased_portion_sqft: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(12, 2)),
        description="Leased portion in square feet (for partial land leases)"
    )
    leased_portion_percentage: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(5, 2)),
        description="Percentage of land being leased (0-100)"
    )
    frontage_meters: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(10, 2)),
        description="Road frontage in meters"
    )
    depth_meters: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(10, 2)),
        description="Lot depth in meters"
    )
    survey_date: Optional[date] = Field(
        default=None,
        sa_column=Column(Date),
        description="Date of most recent survey"
    )
    survey_reference: Optional[str] = Field(
        default=None,
        sa_column=Column(String(200)),
        description="Survey plan number or reference"
    )
    survey_document_url: Optional[str] = Field(
        default=None,
        sa_column=Column(String(500)),
        description="URL to uploaded survey document"
    )
    lot_numbers: Optional[str] = Field(
        default=None,
        sa_column=Column(String(200)),
        description="Cadastre/lot identification numbers"
    )
    
    # ===== LAND USE & ZONING =====
    municipality: Optional[str] = Field(
        default=None,
        sa_column=Column(String(200)),
        description="Municipality or regional district name"
    )
    zoning_code: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100)),
        description="Zoning classification code"
    )
    official_plan_designation: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100)),
        description="Official plan designation (residential, commercial, agricultural, etc.)"
    )
    overlays_restrictions: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Zoning overlays (Greenbelt, ALR, Conservation Authority, Heritage, etc.)"
    )
    site_plan_status: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50)),
        description="Site plan approval status: approved, pending, not_submitted"
    )
    permitted_uses: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="List of permitted land uses"
    )
    
    # ===== GROUND LEASE SPECIFICS =====
    lease_structure: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100)),
        description="Type: ground_lease, air_rights, mineral_rights, agricultural, mixed"
    )
    allows_structures: bool = Field(
        default=False,
        description="Whether tenant can build structures on the land"
    )
    development_rights: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Development rights and restrictions"
    )
    signage_rights: bool = Field(
        default=False,
        description="Whether tenant has signage rights"
    )
    subletting_allowed: bool = Field(
        default=False,
        description="Whether subletting/subleasing is permitted"
    )
    revenue_share_percentage: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(5, 2)),
        description="Revenue sharing percentage (0-100) if applicable"
    )
    
    # ===== ENCUMBRANCES & LEGAL =====
    registered_covenants: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Registered covenants and encroachments"
    )
    title_registration_province: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100)),
        description="Province/state where title is registered"
    )
    title_registration_number: Optional[str] = Field(
        default=None,
        sa_column=Column(String(200)),
        description="Title registration number (PIN, lot number, etc.)"
    )
    easements: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Easements, rights of way, and access restrictions"
    )
    environmental_restrictions: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Environmental restrictions and requirements"
    )
    
    # ===== FINANCIAL STRUCTURE =====
    assessment_roll_number: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100)),
        description="Municipal assessment roll number"
    )
    insurance_responsibility: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50)),
        description="Insurance responsibility: landlord, tenant, shared"
    )
    operating_expenses_responsibility: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50)),
        description="Operating expenses responsibility: landlord, tenant, shared"
    )
    
    # ===== PHYSICAL FEATURES =====
    topography: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50)),
        description="Topography type: flat, sloped, hilly, mixed"
    )
    soil_type: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100)),
        description="Soil type or classification"
    )
    drainage: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100)),
        description="Drainage characteristics"
    )
    floodplain_indicator: bool = Field(
        default=False,
        description="Whether land is in a floodplain zone"
    )
    brownfield_indicator: bool = Field(
        default=False,
        description="Whether land is classified as brownfield (contaminated)"
    )
    conservation_area: bool = Field(
        default=False,
        description="Whether land is in a conservation area"
    )
    
    # ===== UTILITIES & INFRASTRUCTURE =====
    utilities_status: Dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Utility connection status: {water: 'connected'|'available'|'not_available', ...}"
    )
    road_access: Optional[str] = Field(
        default=None,
        sa_column=Column(String(200)),
        description="Road access description and type"
    )
    parking_spaces: Optional[int] = Field(
        default=None,
        description="Number of parking spaces (if applicable)"
    )
    
    # ===== ENVIRONMENTAL ASSESSMENTS =====
    environmental_assessment_phase1: bool = Field(
        default=False,
        description="Whether Phase I Environmental Site Assessment completed"
    )
    environmental_assessment_phase2: bool = Field(
        default=False,
        description="Whether Phase II Environmental Site Assessment completed"
    )
    esa_document_urls: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="URLs to environmental assessment documents"
    )
    
    # ===== DOCUMENTATION & MEDIA =====
    zoning_certificate_url: Optional[str] = Field(
        default=None,
        sa_column=Column(String(500)),
        description="URL to zoning certificate/confirmation document"
    )
    site_plan_url: Optional[str] = Field(
        default=None,
        sa_column=Column(String(500)),
        description="URL to site plan document"
    )
    parcel_map_url: Optional[str] = Field(
        default=None,
        sa_column=Column(String(500)),
        description="URL to parcel map or GIS overlay"
    )
    aerial_photo_urls: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="URLs to drone/aerial photographs"
    )
    
    # ===== ADDITIONAL DETAILS =====
    notes: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Additional notes and information"
    )
    additional_details: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Flexible storage for additional land details"
    )
    
    # ===== TIMESTAMPS =====
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=create_audit_datetime)
    )

