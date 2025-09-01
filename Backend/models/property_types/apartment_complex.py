"""
Apartment Complex property type model.
Handles multi-unit residential buildings with shared amenities and management.
"""
from datetime import datetime
from typing import Any, Optional, Dict, List, TYPE_CHECKING
from decimal import Decimal
import logging

from sqlalchemy import Column, String, Numeric, JSON, DateTime, Text, CheckConstraint, Index
from sqlmodel import Field, SQLModel
from pydantic import field_validator, model_validator
from Backend.utils.datetime_utils import create_audit_datetime
from .base import LeaseExpiryHelper, UnitMixHelper

if TYPE_CHECKING:
    from Backend.models.property import PropertyUnit
    from Backend.models.lease import Lease


class PropertyApartmentComplex(SQLModel, table=True):
    """Apartment complex specific property details"""
    
    __tablename__ = "properties_apartment_complex" # type: ignore
    
    property_id: int = Field(
        foreign_key="properties.id", 
        primary_key=True,
        ondelete="CASCADE",
        description="Link to base property"
    )
    
    # ===== REQUIRED FIELDS =====
    # Complex Style (Required)
    complex_style: str = Field(
        description="Style of apartment complex: garden, highrise, midrise, townhome, luxury, student"
    )
    
    # Building Information
    number_of_buildings: int = Field(
        description="Number of buildings in the complex (Required)"
    )
    total_units: int = Field(
        description="Total number of units across all buildings (Required)"
    )
    
    # Unit Distribution (Required - stored as JSONB for flexibility)
    unit_mix: Dict[str, int] = Field(
        default_factory=dict, 
        sa_column=Column(JSON),
        description='Unit distribution e.g. {"studio": 20, "1br": 40, "2br": 30, "3br": 10, "penthouse": 2}'
    )
    
    # Management (Optional)
    assigned_property_manager: Optional[str] = Field(
        default=None,
        sa_column=Column(String(200)),
        description="Name of assigned property manager"
    )
    
    # ===== OPTIONAL BUT IMPORTANT FIELDS =====
    # Building Identification
    building_codes_names: Dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description='Building codes/names e.g. {"A": "North Tower", "B": "South Tower", "100": "Main Building"}'
    )
    
    # Shared Amenities (stored as array for easy filtering)
    shared_amenities: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description='List of amenities e.g. ["gym", "pool", "parking_garage", "clubhouse", "laundry", "playground"]'
    )
    
    # Security
    has_security_system: bool = Field(
        default=False, 
        description="Whether complex has security system"
    )
    security_system_type: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100)),
        description="Type of security system (cameras, key fob, doorman, etc.)"
    )
    security_system_details: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Additional details about the security system"
    )
    
    # Infrastructure
    floor_count: int = Field(
        default=1,
        description="Number of floors in the tallest building"
    )
    elevator_count: int = Field(
        default=0, 
        description="Total number of elevators across all buildings"
    )
    
    # Waste Management
    trash_system_type: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50)),
        description="Type of trash system: chute, compactor, curbside, valet"
    )
    trash_collection_schedule: Optional[str] = Field(
        default=None,
        sa_column=Column(String(200)),
        description="Trash collection schedule details"
    )
    trash_system_details: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Additional details about the trash system and operations"
    )
    
    # Lease Management
    lease_expiry_distribution: Dict[str, int] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description='Lease expiry summary e.g. {"2024-Q1": 15, "2024-Q2": 20, "2024-Q3": 10, "2024-Q4": 25}'
    )
    
    # Emergency Contacts (structured for consistency)
    emergency_contacts: List[Dict[str, str]] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description='Emergency contacts e.g. [{"name": "John Doe", "role": "Super", "phone": "555-0100", "available": "24/7"}]'
    )
    
    # ===== ADDITIONAL USEFUL FIELDS =====
    # Parking
    parking_spaces_total: Optional[int] = Field(
        default=None, 
        description="Total parking spaces available"
    )
    
    # Management Company
    property_management_company: Optional[str] = Field(
        default=None,
        sa_column=Column(String(200)),
        description="Property management company name if different from manager"
    )
    on_site_management: bool = Field(
        default=False, 
        description="Whether management office is on-site"
    )
    management_office_location: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100)),
        description="Location of management office (building/unit)"
    )
    management_office_hours: Dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description='Office hours e.g. {"monday": "9am-5pm", "tuesday": "9am-5pm", ...}'
    )
    
    # Financial Metrics
    average_rent_by_type: Dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description='Average rent by unit type as string values for precision e.g. {"studio": "1200.00", "1br": "1500.00", "2br": "2000.00"}'
    )
    vacancy_rate: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(5, 2), nullable=True),
        description="Current vacancy rate as percentage"
    )
    
    # Policies
    pet_policy: Optional[str] = Field(
        default=None,
        sa_column=Column(String(500)),
        description="Pet policy details"
    )
    utilities_included: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description='Utilities included in rent e.g. ["water", "trash", "sewer"]'
    )

    # Management & Contacts
    management_contact_phone: Optional[str] = Field(
        default=None,
        sa_column=Column(String(20)),
        description="Primary management contact phone"
    )
    management_contact_email: Optional[str] = Field(
        default=None,
        sa_column=Column(String(255)),
        description="Primary management contact email"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=create_audit_datetime)
    )
    
    # ===== VALIDATION METHODS =====
    @field_validator('complex_style')
    @classmethod
    def validate_complex_style(cls, v: str) -> str:
        valid_styles = {'garden', 'highrise', 'midrise', 'townhome', 'luxury', 'student'}
        if v not in valid_styles:
            raise ValueError(f"Complex style must be one of: {', '.join(valid_styles)}")
        return v
    
    @field_validator('total_units')
    @classmethod
    def validate_total_units(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Total units must be greater than 0")
        if v > 10000:  # Sanity check
            raise ValueError("Total units seems unrealistic (>10000)")
        return v
    
    @field_validator('number_of_buildings')
    @classmethod
    def validate_buildings(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Number of buildings must be at least 1")
        if v > 100:  # Sanity check
            raise ValueError("Number of buildings seems unrealistic (>100)")
        return v
    
    @field_validator('vacancy_rate')
    @classmethod
    def validate_rates(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Rate must be between 0 and 100")
        return v
    
    @field_validator('emergency_contacts')
    @classmethod
    def validate_emergency_contacts(cls, v: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Ensure emergency contacts have required fields"""
        for contact in v:
            if not contact.get('name'):
                raise ValueError("Emergency contact must have a name")
            if not contact.get('phone'):
                raise ValueError("Emergency contact must have a phone number")
            if 'role' not in contact:
                contact['role'] = 'Contact'
        return v
    
    @model_validator(mode='after')
    def validate_unit_mix_consistency(self):
        """Validate that unit mix is consistent with total units"""
        if self.unit_mix:
            mix_total = sum(self.unit_mix.values())
            if mix_total > 0 and mix_total != self.total_units:
                # Auto-correct if close (within 5%)
                if abs(mix_total - self.total_units) / self.total_units <= 0.05:
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        "Auto-correcting apartment complex total_units: %d -> %d (unit mix total). "
                        "Difference was within 5%% tolerance.",
                        self.total_units, mix_total
                    )
                    self.total_units = mix_total
                else:
                    raise ValueError(f"Unit mix total ({mix_total}) doesn't match total units ({self.total_units})")
        return self
    
    
    # ===== COMPUTED PROPERTIES =====
    def calculate_metrics(self, units: Optional[List["PropertyUnit"]] = None) -> Dict[str, Any]:
        """Calculate apartment complex specific metrics"""
        metrics: Dict[str, Any] = {}
        
        # Calculate occupancy if units provided
        if units:
            total = len(units)
            occupied = sum(1 for unit in units if unit.is_rented)
            metrics['calculated_occupancy_rate'] = (occupied / total * 100) if total > 0 else 0
            metrics['calculated_vacancy_rate'] = 100 - metrics['calculated_occupancy_rate']
            metrics['occupied_units'] = occupied
            metrics['vacant_units'] = total - occupied
            
            # Calculate average rent by type
            if self.unit_mix:
                metrics['average_rent_by_type'] = UnitMixHelper.calculate_average_rent_by_type(units)
        
        # Units per building
        if self.number_of_buildings > 0:
            metrics['units_per_building'] = self.total_units / self.number_of_buildings
        
        # Parking ratio
        if self.parking_spaces_total and self.total_units > 0:
            metrics['parking_ratio'] = Decimal(self.parking_spaces_total) / Decimal(self.total_units)
        
        return metrics
    
    def update_lease_expiry_distribution(self, leases: List["Lease"]) -> None:
        """Update lease expiry distribution from actual lease data"""
        self.lease_expiry_distribution = LeaseExpiryHelper.calculate_quarterly_distribution(leases)
    
    def get_upcoming_lease_expiries(self, leases: List["Lease"], months: int = 3) -> List["Lease"]:
        """Get leases expiring in the next N months"""
        return LeaseExpiryHelper.get_upcoming_expiries(leases, months)
    
    def validate_for_operations(self) -> List[str]:
        """Validate that the property is ready for operations"""
        errors = []
        
        if not self.assigned_property_manager and not self.property_management_company:
            errors.append("No property manager or management company assigned")
        
        if not self.emergency_contacts:
            errors.append("No emergency contacts configured")
        
        if self.total_units > 50 and not self.has_security_system:
            errors.append("Large complex without security system")
        
        if not self.trash_system_type:
            errors.append("Trash system not configured")
        
        return errors
    
    # ===== TABLE CONFIGURATION =====
    __table_args__ = (
        CheckConstraint('total_units > 0', name='check_positive_units'),
        CheckConstraint('number_of_buildings > 0', name='check_positive_buildings'),
        CheckConstraint('elevator_count >= 0', name='check_non_negative_elevators'),
        CheckConstraint('parking_spaces_total IS NULL OR parking_spaces_total >= 0', name='check_non_negative_parking'),
        CheckConstraint('(vacancy_rate IS NULL) OR (vacancy_rate >= 0 AND vacancy_rate <= 100)', 
                       name='check_vacancy_rate_range'),
        Index('idx_apartment_complex_property', 'property_id'),
        Index('idx_apartment_complex_units', 'total_units'),
    )
