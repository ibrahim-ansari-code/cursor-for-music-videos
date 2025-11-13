"""
Unit tests for UPDATE operations in the maintenance API endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.api.maintenance.schemas import (
    MaintenanceRequestUpdate,
    MaintenanceRequestResponse,
    PropertyInfo,
    UnitInfo,
    TenantInfo
)
from Backend.models.maintenance import MaintenanceRequest
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.models.enums import MaintenancePriority, MaintenanceStatus, UserType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()

# Create a custom TestClient that sets the proper host header
class TestClientWithHost(TestClient):
    def request(self, method: str, url, **kwargs):
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)

def create_test_user(user_id=None, email="test@example.com", user_type=UserType.LANDLORD, is_admin=False):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=is_admin,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )

# =============================================================================
# UPDATE MAINTENANCE REQUEST TESTS
# =============================================================================

def test_update_maintenance_request_success():
    """Test successful update of a maintenance request."""
    # Arrange
    request_id = 123
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, email="owner@example.com")
    
    update_data = {
        "issue_title": "Updated Issue Title",
        "description": "Updated description with more details",
        "priority": "LOW",
        "status": "IN_PROGRESS",
        "scheduled_date": "2024-02-15",
        "estimated_cost": "750.00",
        "assigned_to": "new-maintenance@company.com"
    }
    
    # Create the response that the service would return
    fake_response = MaintenanceRequestResponse(
        id=request_id,
        issue_title="Updated Issue Title",
        description="Updated description with more details",
        property=PropertyInfo(id=1, name="Test Property"),
        unit=UnitInfo(id=2, name="Unit B"),
        tenant=TenantInfo(id=3, first_name="John", last_name="Doe"),
        request_date=datetime.now(timezone.utc),
        priority=MaintenancePriority.LOW,
        status=MaintenanceStatus.IN_PROGRESS,
        scheduled_date=date(2024, 2, 15),
        completed_date=None,
        estimated_cost=Decimal("750.00"),
        actual_cost=None,
        photos=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        assigned_to="new-maintenance@company.com",
        vendor_id=None,
        vendor=None,
        notify_tenant=False
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.update_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == request_id
            assert data["issue_title"] == "Updated Issue Title"
            assert data["description"] == "Updated description with more details"
            assert data["priority"] == "Low"
            assert data["status"] == "In Progress"
            assert data["scheduled_date"] == "2024-02-15"
            assert data["estimated_cost"] == "750.00"
            assert data["assigned_to"] == "new-maintenance@company.com"


def test_update_maintenance_request_partial_update():
    """Test partial update with only some fields."""
    # Arrange
    request_id = 124
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    update_data = {
        "status": "COMPLETED",
        "actual_cost": "650.00"
    }
    
    fake_response = MaintenanceRequestResponse(
        id=request_id,
        issue_title="Original Title",
        description="Original description",
        property=PropertyInfo(id=1, name="Test Property"),
        unit=None,
        tenant=None,
        request_date=datetime.now(timezone.utc),
        priority=MaintenancePriority.MEDIUM,
        status=MaintenanceStatus.COMPLETED,
        scheduled_date=None,
        completed_date=datetime.now(timezone.utc),
        estimated_cost=Decimal("500.00"),
        actual_cost=Decimal("650.00"),
        photos=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        assigned_to=None,
        vendor_id=None,
        vendor=None,
        notify_tenant=False
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.update_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "Completed"
            assert data["actual_cost"] == "650.00"
            assert data["issue_title"] == "Original Title"  # Unchanged


def test_update_maintenance_request_change_property():
    """Test updating maintenance request to different property."""
    # Arrange
    request_id = 125
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    update_data = {
        "property_id": 2,  # Change to different property
        "unit_id": 5      # And different unit
    }
    
    fake_response = MaintenanceRequestResponse(
        id=request_id,
        issue_title="Issue Title",
        description="Description",
        property=PropertyInfo(id=2, name="New Property"),
        unit=UnitInfo(id=5, name="New Unit"),
        tenant=None,
        request_date=datetime.now(timezone.utc),
        priority=MaintenancePriority.MEDIUM,
        status=MaintenanceStatus.PENDING,
        scheduled_date=None,
        completed_date=None,
        estimated_cost=None,
        actual_cost=None,
        photos=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        assigned_to=None,
        vendor_id=None,
        vendor=None,
        notify_tenant=False
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.update_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["property"]["id"] == 2
            assert data["property"]["name"] == "New Property"
            assert data["unit"]["id"] == 5
            assert data["unit"]["name"] == "New Unit"


def test_update_maintenance_request_mark_completed():
    """Test marking a maintenance request as completed with completion date."""
    # Arrange
    request_id = 126
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    completed_time = datetime.now(timezone.utc)
    update_data = {
        "status": "COMPLETED",
        "completed_date": completed_time.isoformat(),
        "actual_cost": "450.00"
    }
    
    fake_response = MaintenanceRequestResponse(
        id=request_id,
        issue_title="Fixed Issue",
        description="This issue has been resolved",
        property=PropertyInfo(id=1, name="Test Property"),
        unit=None,
        tenant=None,
        request_date=datetime.now(timezone.utc),
        priority=MaintenancePriority.HIGH,
        status=MaintenanceStatus.COMPLETED,
        scheduled_date=None,
        completed_date=completed_time,
        estimated_cost=Decimal("500.00"),
        actual_cost=Decimal("450.00"),
        photos=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        assigned_to="maintenance@company.com",
        vendor_id=None,
        vendor=None,
        notify_tenant=False
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.update_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "Completed"
            assert data["completed_date"] is not None
            assert data["actual_cost"] == "450.00"


def test_update_maintenance_request_not_found():
    """Test 404 error when maintenance request doesn't exist."""
    # Arrange
    request_id = 999
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    update_data = {
        "status": "IN_PROGRESS"
    }
    
    # Mock the service layer to raise 404
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.update_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Maintenance request not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
            
            # Assert
            assert response.status_code == 404
            assert "Maintenance request not found" in response.json()["detail"]


def test_update_maintenance_request_forbidden_non_owner():
    """Test 403 error when non-owner tries to update maintenance request."""
    # Arrange
    request_id = 127
    user_id = uuid4()
    other_user_id = uuid4()
    
    other_user = create_test_user(
        user_id=other_user_id,
        email="other@example.com"
    )
    
    update_data = {
        "status": "CANCELLED"
    }
    
    # Mock the service layer to raise 403
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.update_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(
            status_code=403,
            detail="You do not have permission to access this maintenance request"
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: other_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
            
            # Assert
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()


def test_update_maintenance_request_invalid_property_change():
    """Test 403 error when trying to change to property user doesn't own."""
    # Arrange
    request_id = 128
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, is_admin=False)
    
    update_data = {
        "property_id": 999  # Property not owned by user
    }
    
    # Mock the service layer to raise 403
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.update_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(
            status_code=403,
            detail="You do not have permission to assign this maintenance request to the specified property."
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
            
            # Assert
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()


def test_update_maintenance_request_unit_property_mismatch():
    """Test 400 error when unit doesn't belong to the specified property."""
    # Arrange
    request_id = 129
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    update_data = {
        "property_id": 1,
        "unit_id": 99  # Unit from different property
    }
    
    # Mock the service layer to raise 400
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.update_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="The specified unit does not belong to the specified property."
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
            
            # Assert
            assert response.status_code == 400
            assert "unit does not belong" in response.json()["detail"].lower()


def test_update_maintenance_request_admin_any_property():
    """Test that admin can update maintenance request for any property."""
    # Arrange
    request_id = 130
    admin_id = uuid4()
    owner_id = uuid4()
    
    admin_user = create_test_user(
        user_id=admin_id,
        email="admin@example.com",
        user_type=UserType.ADMIN,
        is_admin=True
    )
    
    update_data = {
        "status": "SCHEDULED",
        "scheduled_date": "2024-03-01",
        "assigned_to": "admin-assigned@company.com"
    }
    
    fake_response = MaintenanceRequestResponse(
        id=request_id,
        issue_title="Admin Updated Issue",
        description="Updated by admin",
        property=PropertyInfo(id=5, name="Someone's Property"),
        unit=None,
        tenant=None,
        request_date=datetime.now(timezone.utc),
        priority=MaintenancePriority.MEDIUM,
        status=MaintenanceStatus.SCHEDULED,
        scheduled_date=date(2024, 3, 1),
        completed_date=None,
        estimated_cost=None,
        actual_cost=None,
        photos=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        assigned_to="admin-assigned@company.com",
        vendor_id=None,
        vendor=None,
        notify_tenant=False
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.update_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
            
            # Assert - Admin should be able to update
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "Scheduled"
            assert data["scheduled_date"] == "2024-03-01"
            assert data["assigned_to"] == "admin-assigned@company.com"


def test_update_maintenance_request_add_photos():
    """Test adding photos to an existing maintenance request."""
    # Arrange
    request_id = 131
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    update_data = {
        "photos": [
            "https://storage.example.com/new-photo1.jpg",
            "https://storage.example.com/new-photo2.jpg",
            "https://storage.example.com/new-photo3.jpg"
        ]
    }
    
    fake_response = MaintenanceRequestResponse(
        id=request_id,
        issue_title="Issue with Photos",
        description="Now with photos",
        property=PropertyInfo(id=1, name="Test Property"),
        unit=None,
        tenant=None,
        request_date=datetime.now(timezone.utc),
        priority=MaintenancePriority.MEDIUM,
        status=MaintenanceStatus.PENDING,
        scheduled_date=None,
        completed_date=None,
        estimated_cost=None,
        actual_cost=None,
        photos=[
            "https://storage.example.com/new-photo1.jpg",
            "https://storage.example.com/new-photo2.jpg",
            "https://storage.example.com/new-photo3.jpg"
        ],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        assigned_to=None,
        vendor_id=None,
        vendor=None,
        notify_tenant=False
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.update_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data["photos"]) == 3
            assert "new-photo1.jpg" in data["photos"][0]


def test_update_maintenance_request_invalid_status():
    """Test validation error for invalid status value."""
    # Arrange
    request_id = 132
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    update_data = {
        "status": "INVALID_STATUS"  # Invalid status
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
        
        # Assert
        assert response.status_code == 422  # Validation error


def test_update_maintenance_request_database_error():
    """Test error handling for database exceptions during update."""
    # Arrange
    request_id = 133
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    update_data = {
        "status": "IN_PROGRESS"
    }
    
    # Mock the service layer to raise a database error
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.update_maintenance_request",
        new=AsyncMock(side_effect=Exception("Database connection failed"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/maintenance/requests/{request_id}", json=update_data)
            
            # Assert
            assert response.status_code == 500
            assert "Failed to update maintenance request" in response.json()["detail"]