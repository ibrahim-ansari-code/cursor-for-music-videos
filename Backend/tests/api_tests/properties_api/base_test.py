"""
Base test utilities for properties API testing.
Provides common fixtures, helpers, and base classes for all property tests.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from Backend.api.app import app
from Backend.models.property import Property, PropertyType
from Backend.models.units import PropertyUnit
from Backend.models.user import User
from Backend.models.enums import PropertyStatus
from Backend.api.auth import get_current_user
from Backend.database import get_session


# Create a custom TestClient that sets the proper host header
class TestClientWithHost(TestClient):
    def request(self, method: str, url, **kwargs):
        # Always add localhost to headers if not present
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def create_test_user(user_id=None, email="test@example.com", user_type="LANDLORD"):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        phone="1234567890",
        profile_image_url=None,
        created_at=now,
        updated_at=now,
        user_type=user_type
    )


def create_test_property(
    property_id: int = 1,
    user_id: Optional[UUID] = None,
    property_type: PropertyType = PropertyType.RESIDENTIAL,
    name: str = "Test Property",
    **kwargs
) -> Property:
    """Helper function to create a test property."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": property_id,
        "name": name,
        "address": "123 Test St",
        "city": "Test City",
        "province": "TC",
        "postal_code": "12345",
        "property_type": property_type,
        "description": "Test property description",
        "year_built": 2020,
        "status": PropertyStatus.ACTIVE,
        "user_id": user_id or uuid4(),
        "latitude": 40.7128,
        "longitude": -74.0060,
        "place_id": "test_place_id",
        "formatted_address": "123 Test St, Test City, TC 12345",
        "google_maps_data": {"test": "data"},
        "property_details": {"test": "details"},
        "created_at": now,
        "updated_at": now,
        "images": [],
        "units": []
    }
    defaults.update(kwargs)
    return Property(**defaults)


def create_test_unit(
    unit_id: int = 1,
    property_id: int = 1,
    name: str = "Unit 1",
    is_rented: bool = False,
    **kwargs
) -> PropertyUnit:
    """Helper function to create a test property unit."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": unit_id,
        "property_id": property_id,
        "name": name,
        "description": "Test unit",
        "size": 1000.0,
        "bedrooms": 2,
        "bathrooms": 1.5,
        "floor": 1,
        "monthly_rent": 1500.00,
        "deposit_amount": 1500.00,
        "is_rented": is_rented,
        "unit_details": {"test": "details"},
        "created_at": now,
        "updated_at": now
    }
    defaults.update(kwargs)
    return PropertyUnit(**defaults)


def get_base_property_payload(property_type: PropertyType) -> Dict[str, Any]:
    """Get base property creation payload for testing."""
    return {
        "name": "Test Property",
        "address": "123 Test Street",
        "city": "Toronto",
        "province": "ON",
        "postal_code": "M5V 3A8",
        "property_type": property_type.value,
        "description": f"Test {property_type.value} property",
        "year_built": 2020,
        "status": PropertyStatus.ACTIVE.value,
        "latitude": 43.6532,
        "longitude": -79.3832,
        "place_id": "ChIJpTvG15DL1IkRd8S0KlBVNTI",
        "formatted_address": "123 Test Street, Toronto, ON M5V 3A8, Canada",
        "google_maps_data": {
            "vicinity": "Toronto",
            "types": ["premise"]
        },
        "property_details": {
            "additional_info": "Test property"
        }
    }


def get_residential_details() -> Dict[str, Any]:
    """Get residential property type-specific details."""
    return {
        "property_type": "Residential",  # Discriminator field
        "property_subtype": "single_family",
        "bedrooms": 3,
        "bathrooms": 2.5,
        "square_feet": 2500,
        "lot_size": 5000,
        "stories": 2,
        "basement_type": "finished",
        "garage_type": "attached",
        "garage_spaces": 2,
        "heating_type": "forced_air",
        "cooling_type": "central",
        "flooring_types": ["hardwood", "carpet", "tile"],
        "has_driveway": False,
        "street_parking": False,
        "has_garden": True,
        "fencing_type": "wood",
        "roof_type": "shingle",
        "roof_age": 5,
        "hvac_age": 3,
        "property_tax": "5000.00",  # Use string for Decimal compatibility
        "occupied": False,
        "rental_price": "2500.00"  # Use string for Decimal compatibility
    }


def get_apartment_complex_details() -> Dict[str, Any]:
    """Get apartment complex property type-specific details."""
    return {
        "property_type": "Apartment Complex",  # Discriminator field
        "complex_style": "garden",  # Required field
        "number_of_buildings": 2,
        "total_units": 48,
        "studio_units": 8,
        "one_bed_units": 20,
        "two_bed_units": 16,
        "three_bed_units": 4,
        "unit_mix": {"studio": 8, "1br": 20, "2br": 16, "3br": 4},
        "shared_amenities": ["gym", "pool", "parking_garage", "clubhouse"],
        "has_security_system": True,
        "security_system_type": "24/7 monitored",
        "security_system_details": "Card access and CCTV",
        "elevator_count": 2,
        "parking_spaces_total": 72,
        "trash_system_type": "chute",
        "trash_collection_schedule": "Daily",
        "property_management_company": "Test Management Co",
        "on_site_management": True,
        "management_office_location": "Building A, Suite 100",
        "management_office_hours": {
            "monday": "9:00 AM - 5:00 PM",
            "tuesday": "9:00 AM - 5:00 PM",
            "wednesday": "9:00 AM - 5:00 PM",
            "thursday": "9:00 AM - 5:00 PM",
            "friday": "9:00 AM - 5:00 PM"
        },
        "pet_policy": "Cats and dogs under 50lbs allowed with deposit",
        "utilities_included": ["water", "trash", "sewer"],
        "assigned_property_manager": "John Smith"
    }


def get_commercial_details() -> Dict[str, Any]:
    """Get commercial property type-specific details."""
    return {
        "property_type": "Commercial",  # Discriminator field
        "space_type": "office",  # Required field
        "usable_square_feet": 45000,  # Required field
        "rentable_square_feet": 50000,  # Required field
        "lease_type": "triple_net",  # Required field
        "building_class": "A",
        "property_subtype": "office",
        "total_floors": 10,
        "rentable_area": 50000,
        "occupancy_rate": 92.5,
        "average_floor_size": 5000,
        "parking_ratio": 4.0,
        "parking_spaces": 200,
        "elevators": 4,
        "loading_docks": 2,
        "zoning": "C-2",
        "ceiling_height": 12,
        "hvac_system": "central",
        "year_renovated": 2018,
        "anchor_tenants": ["Tech Corp", "Finance Inc"],
        "lease_types": ["triple_net", "gross"],
        "average_lease_term": 5,
        "common_area_factor": 15.5,
        "building_amenities": ["conference_center", "fitness_center", "cafeteria"],
        "nearby_transit": ["subway", "bus"],
        "walk_score": 95,
        "energy_rating": "LEED Gold",
        "management_company": "Commercial Management LLC",
        "operating_expenses": 12.50
    }


def get_industrial_details() -> Dict[str, Any]:
    """Get industrial property type-specific details."""
    return {
        "property_type": "Industrial",  # Discriminator field
        "industrial_type": "warehouse",  # Required field
        "total_square_feet": 100000,  # Required field
        "property_subtype": "warehouse",
        "building_size": 100000,
        "land_area": 250000,
        "clear_height": 30,
        "loading_docks": 10,
        "loading_docks_count": 10,  # Updated field name
        "drive_in_doors_count": 1,  # Updated field name
        "grade_level_doors": 2,
        "rail_access": True,
        "has_crane": True,  # Required when crane_capacity is provided
        "crane_capacity": "20 tons",
        "power_capacity": "2000 amps",
        "column_spacing": 40,
        "floor_type": "reinforced_concrete",
        "floor_load_capacity": 1000,
        "sprinkler_system": True,
        "hvac_office": True,
        "hvac_warehouse": False,
        "office_space": 5000,
        "truck_court": True,
        "yard_size": 50000,
        "fenced": True,
        "security_features": ["cameras", "guard", "keycard"],
        "zoning": "M-2",
        "environmental_phase": 2,
        "last_environmental_date": "2023-01-15",
        "tenant": "Logistics Corp",
        "lease_type": "triple_net",
        "lease_expiry": "2028-12-31"
    }


def get_mixed_use_details() -> Dict[str, Any]:
    """Get mixed-use property type-specific details."""
    return {
        "property_type": "Mixed-Use",  # Discriminator field
        "mixed_use_type": "live_work",  # Required field
        "residential_square_feet": 80000,  # Required field
        "commercial_square_feet": 20000,  # Required field
        "residential_units_count": 100,
        "commercial_units_count": 10,
        "residential_unit_types": {"studio": 20, "1br": 40, "2br": 30, "3br": 10},
        "commercial_space_types": ["retail", "office"],
        "shared_amenities": ["gym", "pool", "rooftop_deck"],
        "separate_entrances": True,
        "shared_parking": False,
        "parking_spaces_total": 200,
        "single_management_company": True,
        "management_structure": "Unified management for all components",
        "zoning_designation": "MU-1",
        # Legacy fields for backward compatibility
        "total_floors": 15,
        "residential_floors": 10,
        "commercial_floors": 2,
        "office_floors": 3,
        "total_units": 120,
        "residential_units": 100,
        "commercial_units": 10,
        "office_units": 10,
        "retail_space": 20000,
        "office_space": 30000,
        "parking_spaces": 200,
        "parking_residential": 150,
        "parking_commercial": 30,
        "parking_visitor": 20,
        "ground_floor_use": ["retail", "lobby"],
        "amenities_residential": ["gym", "pool", "rooftop_terrace"],
        "amenities_commercial": ["conference_rooms", "loading_area"],
        "transit_score": 98,
        "walk_score": 95,
        "bike_score": 88,
        "management_office": "Level 2, Suite 201",
        "concierge_hours": "24/7",
        "security_type": "24/7 security and concierge",
        "mixed_use_zoning": "MU-1",
        "anchor_retail": ["Grocery Store", "Coffee Shop"],
        "office_tenants": ["Tech Startup", "Law Firm"],
        "residential_occupancy": 94.0,
        "commercial_occupancy": 100.0,
        "average_residential_rent": 2800.00,
        "average_retail_lease": 45.00,
        "average_office_lease": 35.00
    }


class BasePropertyTest:
    """Base class for property API tests."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test."""
        self.client = TestClientWithHost(app)
        self.mock_user = create_test_user()
        app.dependency_overrides.clear()
        yield
        app.dependency_overrides.clear()
    
    def setup_mocks(self, mock_session=None):
        """Setup common mocks for testing."""
        # Mock authentication
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        
        # Mock database session if provided
        if mock_session:
            # Configure mock session.execute to return a proper mock result
            mock_result = MagicMock()
            mock_result.unique.return_value.scalar_one_or_none.return_value = None
            mock_result.unique.return_value.scalars.return_value.all.return_value = []
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            app.dependency_overrides[get_session] = lambda: mock_session
        
        return mock_session