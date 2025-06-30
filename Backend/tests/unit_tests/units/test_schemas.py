"""
Unit tests for Units schemas validation.

These tests ensure that the Pydantic schemas properly validate input data
and enforce business rules at the data model level.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from pydantic import ValidationError

from Backend.api.units.schemas import (
    UnitBase, UnitCreate, UnitUpdate, UnitCreateResponse,
    UnitResponse, TenantInfo, BulkUnitCreate, BulkUnitCreateResponse,
    UnitSearchFilters
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


# =============================================================================
# UnitBase and UnitCreate Tests
# =============================================================================

def test_unit_create_valid():
    """Test creating a unit with valid data."""
    unit_data = {
        "name": "Unit 101",
        "description": "A nice unit",
        "size": 1200.5,
        "monthly_rent": "1500.00",
        "is_rented": False,
        "bedrooms": 2,
        "bathrooms": 1.5,
        "floor": 1
    }
    
    unit = UnitCreate(**unit_data)
    
    assert unit.name == "Unit 101"
    assert unit.size == 1200.5
    assert unit.monthly_rent == Decimal("1500.00")
    assert unit.bedrooms == 2
    assert unit.bathrooms == 1.5


def test_unit_create_minimal():
    """Test creating a unit with minimal required data."""
    unit_data = {
        "name": "Unit A",
        "is_rented": False
    }
    
    unit = UnitCreate(**unit_data)
    
    assert unit.name == "Unit A"
    assert unit.is_rented is False
    assert unit.description is None
    assert unit.monthly_rent is None


def test_unit_create_empty_name_fails():
    """Test that empty unit name fails validation."""
    unit_data = {
        "name": "",  # Empty string
        "is_rented": False
    }
    
    with pytest.raises(ValidationError) as exc_info:
        UnitCreate(**unit_data)
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("name",) for error in errors)
    assert any("at least 1 character" in str(error) for error in errors)


def test_unit_create_name_too_long_fails():
    """Test that overly long unit name fails validation."""
    unit_data = {
        "name": "A" * 256,  # Exceeds 255 character limit
        "is_rented": False
    }
    
    with pytest.raises(ValidationError) as exc_info:
        UnitCreate(**unit_data)
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("name",) for error in errors)


def test_unit_create_negative_rent_fails():
    """Test that negative rent fails validation."""
    unit_data = {
        "name": "Unit A",
        "monthly_rent": "-500.00",
        "is_rented": False
    }
    
    with pytest.raises(ValidationError) as exc_info:
        UnitCreate(**unit_data)
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("monthly_rent",) for error in errors)
    assert any("Monthly rent cannot be negative" in str(error["msg"]) for error in errors)


def test_unit_create_zero_size_fails():
    """Test that zero size fails validation."""
    unit_data = {
        "name": "Unit A",
        "size": 0,
        "is_rented": False
    }
    
    with pytest.raises(ValidationError) as exc_info:
        UnitCreate(**unit_data)
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("size",) for error in errors)
    assert any("Size must be greater than 0" in str(error["msg"]) for error in errors)


def test_unit_create_negative_bedrooms_fails():
    """Test that negative bedrooms fails validation."""
    unit_data = {
        "name": "Unit A",
        "bedrooms": -1,
        "is_rented": False
    }
    
    with pytest.raises(ValidationError) as exc_info:
        UnitCreate(**unit_data)
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("bedrooms",) for error in errors)
    assert any("Bedrooms cannot be negative" in str(error["msg"]) for error in errors)


def test_unit_create_negative_bathrooms_fails():
    """Test that negative bathrooms fails validation."""
    unit_data = {
        "name": "Unit A",
        "bathrooms": -0.5,
        "is_rented": False
    }
    
    with pytest.raises(ValidationError) as exc_info:
        UnitCreate(**unit_data)
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("bathrooms",) for error in errors)
    assert any("Bathrooms cannot be negative" in str(error["msg"]) for error in errors)


# =============================================================================
# UnitUpdate Tests
# =============================================================================

def test_unit_update_partial():
    """Test updating unit with partial data."""
    update_data = {
        "name": "Updated Unit",
        "monthly_rent": Decimal("1800.00")
    }
    
    update = UnitUpdate(**update_data)
    
    assert update.name == "Updated Unit"
    assert update.monthly_rent == Decimal("1800.00")
    assert update.description is None  # Not provided
    assert update.size is None  # Not provided


def test_unit_update_empty_valid():
    """Test that empty update is valid (no fields set)."""
    update = UnitUpdate()
    
    # All fields should be None
    assert update.name is None
    assert update.monthly_rent is None
    assert update.tenant_id is None


def test_unit_update_negative_rent_fails():
    """Test that negative rent fails validation in update."""
    with pytest.raises(ValidationError) as exc_info:
        UnitUpdate(monthly_rent=Decimal("-100.00"))
    
    errors = exc_info.value.errors()
    assert any("Monthly rent cannot be negative" in str(error["msg"]) for error in errors)


def test_unit_update_zero_size_fails():
    """Test that zero size fails validation in update."""
    with pytest.raises(ValidationError) as exc_info:
        UnitUpdate(size=0.0)
    
    errors = exc_info.value.errors()
    assert any("Size must be greater than 0" in str(error["msg"]) for error in errors)


def test_unit_update_tenant_assignment():
    """Test update with tenant assignment."""
    update_data = {
        "tenant_id": 5,
        "name": "Updated Unit Name"
    }
    
    update = UnitUpdate(**update_data)
    
    assert update.tenant_id == 5
    assert update.name == "Updated Unit Name"
    # is_rented is no longer part of UnitUpdate schema


def test_unit_update_cannot_set_is_rented():
    """Test that is_rented field is not allowed in UnitUpdate."""
    update_data = {
        "name": "Unit 101",
        "is_rented": True  # This should not be allowed
    }
    
    # Pydantic v2 behavior - extra fields are ignored by default
    # unless model config forbids them
    update = UnitUpdate(**update_data)
    
    # Verify is_rented is not an attribute of the update
    assert not hasattr(update, 'is_rented')
    assert update.name == "Unit 101"


# =============================================================================
# Response Model Tests
# =============================================================================

def test_unit_create_response():
    """Test UnitCreateResponse model."""
    now = datetime.now(timezone.utc)
    response_data = {
        "id": 1,
        "property_id": 10,
        "name": "Unit 101",
        "description": "Nice unit",
        "size": 1200.0,
        "monthly_rent": Decimal("1500.00"),
        "is_rented": False,
        "bedrooms": 2,
        "bathrooms": 1.5,
        "floor": 1,
        "created_at": now,
        "updated_at": now
    }
    
    response = UnitCreateResponse(**response_data)
    
    assert response.id == 1
    assert response.property_id == 10
    assert response.name == "Unit 101"
    assert response.monthly_rent == Decimal("1500.00")


def test_unit_response_with_tenant():
    """Test UnitResponse with tenant information."""
    now = datetime.now(timezone.utc)
    response_data = {
        "id": 1,
        "property_id": 10,
        "name": "Unit 101",
        "is_rented": True,
        "created_at": now,
        "updated_at": now,
        "tenant": {
            "id": 5,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com"
        }
    }
    
    response = UnitResponse(**response_data)
    
    assert response.is_rented is True
    assert response.tenant is not None
    assert response.tenant.id == 5
    assert response.tenant.first_name == "John"


def test_unit_response_without_tenant():
    """Test UnitResponse without tenant (vacant unit)."""
    now = datetime.now(timezone.utc)
    response_data = {
        "id": 1,
        "property_id": 10,
        "name": "Unit 101",
        "is_rented": False,
        "created_at": now,
        "updated_at": now,
        "tenant": None
    }
    
    response = UnitResponse(**response_data)
    
    assert response.is_rented is False
    assert response.tenant is None


# =============================================================================
# BulkUnitCreate Tests
# =============================================================================

def test_bulk_unit_create_valid():
    """Test bulk unit creation with valid data."""
    units = [
        UnitCreate(name="Unit A", is_rented=False),
        UnitCreate(name="Unit B", is_rented=False),
        UnitCreate(name="Unit C", is_rented=False)
    ]
    
    bulk = BulkUnitCreate(units=units)
    
    assert len(bulk.units) == 3
    assert all(isinstance(unit, UnitCreate) for unit in bulk.units)
    assert bulk.units[0].name == "Unit A"


def test_bulk_unit_create_empty_fails():
    """Test bulk creation with empty unit list fails."""
    bulk_data = {
        "units": []
    }
    
    with pytest.raises(ValidationError) as exc_info:
        BulkUnitCreate(**bulk_data)
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("units",) for error in errors)
    assert any("at least 1 item" in str(error) for error in errors)


def test_bulk_unit_create_too_many_fails():
    """Test bulk creation with too many units fails."""
    units = [UnitCreate(name=f"Unit {i}", is_rented=False) for i in range(101)]
    
    with pytest.raises(ValidationError) as exc_info:
        BulkUnitCreate(units=units)
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("units",) for error in errors)
    assert any("at most 100" in str(error) for error in errors)


def test_bulk_unit_create_response():
    """Test BulkUnitCreateResponse model."""
    now = datetime.now(timezone.utc)
    
    # Create proper UnitCreateResponse instances
    created_units = [
        UnitCreateResponse(
            id=1,
            property_id=10,
            name="Unit A",
            is_rented=False,
            created_at=now,
            updated_at=now
        )
    ]
    
    failed_units = [
        {
            "index": 1,
            "data": {"name": "Unit B", "is_rented": False},
            "error": "Duplicate name"
        }
    ]
    
    response = BulkUnitCreateResponse(created=created_units, failed=failed_units)
    
    assert len(response.created) == 1
    assert len(response.failed) == 1
    assert response.created[0].name == "Unit A"
    assert response.failed[0]["index"] == 1
    assert "Duplicate name" in response.failed[0]["error"]


# =============================================================================
# UnitSearchFilters Tests
# =============================================================================

def test_search_filters_valid():
    """Test search filters with valid data."""
    filters = UnitSearchFilters(
        min_rent=Decimal("1000.00"),
        max_rent=Decimal("2000.00"),
        min_bedrooms=2,
        max_bedrooms=4,
        min_bathrooms=1.5,
        is_rented=False,
        property_ids=[1, 2, 3]
    )
    
    assert filters.min_rent == Decimal("1000.00")
    assert filters.max_rent == Decimal("2000.00")
    assert filters.min_bedrooms == 2
    assert filters.property_ids == [1, 2, 3]


def test_search_filters_empty():
    """Test search filters with no criteria (all None)."""
    filters = UnitSearchFilters(
        min_rent=None,
        max_rent=None,
        min_bedrooms=None,
        max_bedrooms=None,
        min_bathrooms=None
    )
    
    assert filters.min_rent is None
    assert filters.max_rent is None
    assert filters.is_rented is None
    assert filters.property_ids is None


def test_search_filters_invalid_rent_range():
    """Test search filters with max_rent < min_rent fails."""
    with pytest.raises(ValidationError) as exc_info:
        UnitSearchFilters(
            min_rent=Decimal("2000.00"),
            max_rent=Decimal("1000.00"),  # Less than min_rent
            min_bedrooms=None,
            max_bedrooms=None,
            min_bathrooms=None
        )
    
    errors = exc_info.value.errors()
    assert any("max_rent" in error["loc"] for error in errors)
    assert any("greater than or equal to min_rent" in str(error["msg"]) for error in errors)


def test_search_filters_negative_values_fail():
    """Test search filters with negative values fail."""
    # Test negative rent
    with pytest.raises(ValidationError):
        UnitSearchFilters(
            min_rent=Decimal("-100"),
            max_rent=None,
            min_bedrooms=None,
            max_bedrooms=None,
            min_bathrooms=None
        )
    
    # Test negative bedrooms
    with pytest.raises(ValidationError):
        UnitSearchFilters(
            min_rent=None,
            max_rent=None,
            min_bedrooms=-1,
            max_bedrooms=None,
            min_bathrooms=None
        )
    
    # Test negative bathrooms
    with pytest.raises(ValidationError):
        UnitSearchFilters(
            min_rent=None,
            max_rent=None,
            min_bedrooms=None,
            max_bedrooms=None,
            min_bathrooms=-0.5
        )


# =============================================================================
# Edge Cases and Special Scenarios
# =============================================================================

def test_decimal_precision_handling():
    """Test that decimal values maintain precision."""
    unit_data = {
        "name": "Unit A",
        "monthly_rent": "1234.56",
        "is_rented": False
    }
    
    unit = UnitCreate(**unit_data)
    
    assert unit.monthly_rent == Decimal("1234.56")
    assert str(unit.monthly_rent) == "1234.56"


def test_float_bathroom_values():
    """Test that bathroom values handle float properly."""
    unit_data = {
        "name": "Unit A",
        "bathrooms": 2.5,  # Half bathroom
        "is_rented": False
    }
    
    unit = UnitCreate(**unit_data)
    
    assert unit.bathrooms == 2.5


def test_tenant_info_minimal():
    """Test TenantInfo with minimal data."""
    tenant_data = {
        "id": 1,
        "first_name": "John",
        "last_name": "Doe",
        "email": None  # Optional
    }
    
    tenant = TenantInfo(**tenant_data)
    
    assert tenant.id == 1
    assert tenant.email is None