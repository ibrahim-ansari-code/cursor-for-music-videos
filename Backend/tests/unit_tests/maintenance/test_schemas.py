"""
Unit tests for maintenance schemas and validation.
"""
import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from pydantic import ValidationError

from Backend.api.maintenance.schemas import (
    MaintenanceRequestCreate,
    MaintenanceRequestUpdate,
    MaintenanceRequestResponse,
    MaintenanceSummaryResponse,
    MaintenancePhotoUploadResponse,
    PropertyInfo,
    UnitInfo,
    TenantInfo
)
from Backend.models.enums import MaintenancePriority, MaintenanceStatus


# =============================================================================
# MaintenanceRequestCreate TESTS
# =============================================================================

def test_maintenance_request_create_valid():
    """Test creating valid MaintenanceRequestCreate."""
    request = MaintenanceRequestCreate(
        issue_title="Leaking faucet",
        description="Kitchen faucet is dripping continuously",
        property_id=1,
        unit_id=101,
        tenant_id=1,
        priority=MaintenancePriority.MEDIUM,
        scheduled_date=date(2024, 3, 15),
        estimated_cost=Decimal("150.00"),
        actual_cost=Decimal("125.00"),
        photos=["photo1.jpg", "photo2.jpg"],
        assigned_to="John Maintenance"
    )
    
    assert request.issue_title == "Leaking faucet"
    assert request.property_id == 1
    assert request.priority == MaintenancePriority.MEDIUM
    assert request.estimated_cost == Decimal("150.00")


def test_maintenance_request_create_minimal():
    """Test creating MaintenanceRequestCreate with minimal required fields."""
    request = MaintenanceRequestCreate(
        issue_title="Broken door",
        property_id=1,
        priority=MaintenancePriority.HIGH
    )
    
    assert request.issue_title == "Broken door"
    assert request.description is None
    assert request.unit_id is None
    assert request.tenant_id is None
    assert request.scheduled_date is None
    assert request.estimated_cost is None
    assert request.actual_cost is None
    assert request.photos is None
    assert request.assigned_to is None


def test_maintenance_request_create_empty_photos_list():
    """Test MaintenanceRequestCreate with empty photos list."""
    request = MaintenanceRequestCreate(
        issue_title="Test issue",
        property_id=1,
        priority=MaintenancePriority.LOW,
        photos=[]
    )
    
    assert request.photos == []


# =============================================================================
# MaintenanceRequestUpdate TESTS
# =============================================================================

def test_maintenance_request_update_all_fields():
    """Test MaintenanceRequestUpdate with all fields."""
    update = MaintenanceRequestUpdate(
        issue_title="Updated title",
        description="Updated description",
        property_id=2,
        unit_id=102,
        tenant_id=2,
        priority=MaintenancePriority.HIGH,
        status=MaintenanceStatus.IN_PROGRESS,
        scheduled_date=date(2024, 3, 20),
        completed_date=datetime(2024, 3, 22, 14, 30),
        estimated_cost=Decimal("200.00"),
        actual_cost=Decimal("180.00"),
        photos=["updated_photo.jpg"],
        assigned_to="Jane Maintenance"
    )
    
    assert update.issue_title == "Updated title"
    assert update.status == MaintenanceStatus.IN_PROGRESS
    assert update.completed_date == datetime(2024, 3, 22, 14, 30)


def test_maintenance_request_update_partial():
    """Test MaintenanceRequestUpdate with only some fields."""
    update = MaintenanceRequestUpdate(
        status=MaintenanceStatus.COMPLETED,
        actual_cost=Decimal("175.50")
    )
    
    assert update.status == MaintenanceStatus.COMPLETED
    assert update.actual_cost == Decimal("175.50")
    assert update.issue_title is None
    assert update.property_id is None


def test_maintenance_request_update_empty():
    """Test MaintenanceRequestUpdate with no fields."""
    update = MaintenanceRequestUpdate()
    
    assert update.issue_title is None
    assert update.status is None
    assert update.priority is None


# =============================================================================
# PropertyInfo, UnitInfo, TenantInfo TESTS
# =============================================================================

def test_property_info():
    """Test PropertyInfo creation."""
    property_info = PropertyInfo(id=1, name="Sunset Apartments")
    
    assert property_info.id == 1
    assert property_info.name == "Sunset Apartments"


def test_unit_info():
    """Test UnitInfo creation."""
    unit_info = UnitInfo(id=101, name="Unit 101")
    
    assert unit_info.id == 101
    assert unit_info.name == "Unit 101"


def test_tenant_info():
    """Test TenantInfo creation."""
    tenant_info = TenantInfo(id=1, first_name="John", last_name="Doe")
    
    assert tenant_info.id == 1
    assert tenant_info.first_name == "John"
    assert tenant_info.last_name == "Doe"


# =============================================================================
# MaintenanceRequestResponse TESTS
# =============================================================================

def test_maintenance_request_response_from_dict():
    """Test MaintenanceRequestResponse creation from dictionary."""
    data = {
        "id": 1,
        "issue_title": "Test issue",
        "description": "Test description",
        "property": {"id": 1, "name": "Test Property"},
        "unit": {"id": 101, "name": "Unit 101"},
        "tenant": {"id": 1, "first_name": "John", "last_name": "Doe"},
        "request_date": datetime(2024, 3, 15, 10, 0),
        "priority": MaintenancePriority.MEDIUM,
        "status": MaintenanceStatus.PENDING,
        "scheduled_date": date(2024, 3, 20),
        "completed_date": None,
        "estimated_cost": Decimal("150.00"),
        "actual_cost": None,
        "photos": ["photo1.jpg"],
        "created_at": datetime(2024, 3, 15, 10, 0),
        "updated_at": datetime(2024, 3, 15, 10, 0),
        "assigned_to": "Jane Maintenance"
    }
    
    response = MaintenanceRequestResponse(**data)
    
    assert response.id == 1
    assert response.issue_title == "Test issue"
    assert response.property.id == 1
    assert response.property.name == "Test Property"
    assert response.unit.id == 101
    assert response.tenant.first_name == "John"


def test_maintenance_request_response_convert_nested_objects():
    """Test MaintenanceRequestResponse model_validator for nested objects."""
    # Create mock SQLModel objects
    mock_property = MagicMock()
    mock_property.id = 1
    mock_property.name = "Test Property"
    
    mock_unit = MagicMock()
    mock_unit.id = 101
    mock_unit.name = "Unit 101"
    
    mock_tenant = MagicMock()
    mock_tenant.id = 1
    mock_tenant.first_name = "John"
    mock_tenant.last_name = "Doe"
    
    # Create mock SQLModel maintenance request
    mock_request = MagicMock()
    mock_request.id = 1
    mock_request.issue_title = "Test issue"
    mock_request.description = "Test description"
    mock_request.property = mock_property
    mock_request.unit = mock_unit
    mock_request.tenant = mock_tenant
    mock_request.request_date = datetime(2024, 3, 15, 10, 0)
    mock_request.priority = MaintenancePriority.MEDIUM
    mock_request.status = MaintenanceStatus.PENDING
    mock_request.scheduled_date = date(2024, 3, 20)
    mock_request.completed_date = None
    mock_request.estimated_cost = Decimal("150.00")
    mock_request.actual_cost = None
    mock_request.photos = ["photo1.jpg"]
    mock_request.created_at = datetime(2024, 3, 15, 10, 0)
    mock_request.updated_at = datetime(2024, 3, 15, 10, 0)
    mock_request.assigned_to = "Jane Maintenance"
    
    response = MaintenanceRequestResponse.model_validate(mock_request)
    
    assert response.id == 1
    assert response.property.id == 1
    assert response.property.name == "Test Property"
    assert response.unit.id == 101
    assert response.unit.name == "Unit 101"
    assert response.tenant.id == 1
    assert response.tenant.first_name == "John"
    assert response.tenant.last_name == "Doe"


def test_maintenance_request_response_none_relationships():
    """Test MaintenanceRequestResponse with None relationships."""
    mock_request = MagicMock()
    mock_request.id = 1
    mock_request.issue_title = "Test issue"
    mock_request.description = None
    mock_request.property = None
    mock_request.unit = None
    mock_request.tenant = None
    mock_request.request_date = datetime(2024, 3, 15, 10, 0)
    mock_request.priority = MaintenancePriority.LOW
    mock_request.status = MaintenanceStatus.PENDING
    mock_request.scheduled_date = None
    mock_request.completed_date = None
    mock_request.estimated_cost = None
    mock_request.actual_cost = None
    mock_request.photos = None
    mock_request.created_at = datetime(2024, 3, 15, 10, 0)
    mock_request.updated_at = datetime(2024, 3, 15, 10, 0)
    mock_request.assigned_to = None
    
    response = MaintenanceRequestResponse.model_validate(mock_request)
    
    assert response.property is None
    assert response.unit is None
    assert response.tenant is None
    assert response.description is None


# =============================================================================
# MaintenanceSummaryResponse TESTS
# =============================================================================

def test_maintenance_summary_response():
    """Test MaintenanceSummaryResponse creation."""
    summary = MaintenanceSummaryResponse(
        total_requests=25,
        pending=5,
        in_progress=8,
        completed=10,
        scheduled=2,
        cancelled=0
    )
    
    assert summary.total_requests == 25
    assert summary.pending == 5
    assert summary.in_progress == 8
    assert summary.completed == 10
    assert summary.scheduled == 2
    assert summary.cancelled == 0


def test_maintenance_summary_response_zero_values():
    """Test MaintenanceSummaryResponse with zero values."""
    summary = MaintenanceSummaryResponse(
        total_requests=0,
        pending=0,
        in_progress=0,
        completed=0,
        scheduled=0,
        cancelled=0
    )
    
    assert summary.total_requests == 0
    assert all(getattr(summary, field) == 0 for field in 
               ['pending', 'in_progress', 'completed', 'scheduled', 'cancelled'])


# =============================================================================
# MaintenancePhotoUploadResponse TESTS
# =============================================================================

def test_maintenance_photo_upload_response():
    """Test MaintenancePhotoUploadResponse creation."""
    response = MaintenancePhotoUploadResponse(
        photo_url="https://storage.example.com/maintenance/photo123.jpg"
    )
    
    assert response.photo_url == "https://storage.example.com/maintenance/photo123.jpg"


def test_maintenance_photo_upload_response_local_path():
    """Test MaintenancePhotoUploadResponse with local file path."""
    response = MaintenancePhotoUploadResponse(
        photo_url="/local/storage/maintenance/photo.jpg"
    )
    
    assert response.photo_url == "/local/storage/maintenance/photo.jpg"


# =============================================================================
# ENUM VALIDATION TESTS
# =============================================================================

def test_maintenance_priority_validation():
    """Test MaintenancePriority enum validation in schemas."""
    # Valid priority
    request = MaintenanceRequestCreate(
        issue_title="Test",
        property_id=1,
        priority=MaintenancePriority.HIGH
    )
    assert request.priority == MaintenancePriority.HIGH
    
    # Invalid priority should raise validation error
    with pytest.raises(ValidationError):
        MaintenanceRequestCreate(
            issue_title="Test",
            property_id=1,
            priority="INVALID_PRIORITY"
        )


def test_maintenance_status_validation():
    """Test MaintenanceStatus enum validation in schemas."""
    # Valid status
    update = MaintenanceRequestUpdate(status=MaintenanceStatus.CANCELLED)
    assert update.status == MaintenanceStatus.CANCELLED
    
    # Invalid status should raise validation error
    with pytest.raises(ValidationError):
        MaintenanceRequestUpdate(status="INVALID_STATUS")


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

def test_decimal_precision():
    """Test decimal precision handling in cost fields."""
    request = MaintenanceRequestCreate(
        issue_title="Test",
        property_id=1,
        priority=MaintenancePriority.LOW,
        estimated_cost=Decimal("123.456"),  # More than 2 decimal places
        actual_cost=Decimal("99.99")
    )
    
    assert request.estimated_cost == Decimal("123.456")  # Should preserve precision
    assert request.actual_cost == Decimal("99.99")


def test_negative_ids():
    """Test that negative IDs are accepted (schema doesn't validate this)."""
    request = MaintenanceRequestCreate(
        issue_title="Test",
        property_id=-1,  # Negative ID
        unit_id=-101,
        tenant_id=-1,
        priority=MaintenancePriority.LOW
    )
    
    assert request.property_id == -1
    assert request.unit_id == -101
    assert request.tenant_id == -1


def test_empty_string_fields():
    """Test empty string handling."""
    request = MaintenanceRequestCreate(
        issue_title="",  # Empty string
        description="",
        property_id=1,
        priority=MaintenancePriority.LOW,
        assigned_to=""
    )
    
    assert request.issue_title == ""
    assert request.description == ""
    assert request.assigned_to == ""