"""
Unit tests for CREATE operations in the maintenance API endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.maintenance.schemas import (
    MaintenanceRequestResponse,
    PropertyInfo,
    UnitInfo,
    TenantInfo
)
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
# CREATE MAINTENANCE REQUEST TESTS
# =============================================================================

def test_create_maintenance_request_success():
    """Test successful creation of a maintenance request."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, email="owner@example.com")
    
    request_data = {
        "issue_title": "Broken AC Unit",
        "description": "The air conditioning unit is not cooling properly",
        "property_id": 1,
        "unit_id": 2,
        "tenant_id": 3,
        "priority": MaintenancePriority.HIGH.value,
        "scheduled_date": "2024-02-01",
        "estimated_cost": "500.00",
        "assigned_to": "maintenance@company.com"
    }
    
    # Create the response that the service would return
    fake_response = MaintenanceRequestResponse(
        id=123,
        issue_title="Broken AC Unit",
        description="The air conditioning unit is not cooling properly",
        property=PropertyInfo(id=1, name="Test Property"),
        unit=UnitInfo(id=2, name="Unit B"),
        tenant=TenantInfo(id=3, first_name="John", last_name="Doe"),
        request_date=datetime.now(timezone.utc),
        priority=MaintenancePriority.HIGH,
        status=MaintenanceStatus.PENDING,
        scheduled_date=date(2024, 2, 1),
        completed_date=None,
        estimated_cost=Decimal("500.00"),
        actual_cost=None,
        photos=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        assigned_to="maintenance@company.com",
        vendor_id=None,
        vendor=None,
        notify_tenant=False
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.create_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/maintenance/requests", json=request_data)
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 123
            assert data["issue_title"] == "Broken AC Unit"
            assert data["description"] == "The air conditioning unit is not cooling properly"
            assert data["property"]["id"] == 1
            assert data["unit"]["id"] == 2
            assert data["tenant"]["id"] == 3
            assert data["priority"] == "High"
            assert data["status"] == "Pending"
            assert data["scheduled_date"] == "2024-02-01"
            assert data["estimated_cost"] == "500.00"
            assert data["assigned_to"] == "maintenance@company.com"


def test_create_maintenance_request_minimal_fields():
    """Test creating a maintenance request with only required fields."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    request_data = {
        "issue_title": "Simple Issue",
        "property_id": 1,
        "priority": "MEDIUM"
    }
    
    fake_response = MaintenanceRequestResponse(
        id=124,
        issue_title="Simple Issue",
        description=None,
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
        photos=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        assigned_to=None,
        vendor_id=None,
        vendor=None,
        notify_tenant=False
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.create_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/maintenance/requests", json=request_data)
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 124
            assert data["issue_title"] == "Simple Issue"
            assert data["description"] is None
            assert data["unit"] is None
            assert data["tenant"] is None


def test_create_maintenance_request_with_photos():
    """Test creating a maintenance request with photo URLs."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    request_data = {
        "issue_title": "Water Damage",
        "description": "Water damage on ceiling",
        "property_id": 1,
        "priority": "HIGH",
        "photos": [
            "https://storage.example.com/photo1.jpg",
            "https://storage.example.com/photo2.jpg"
        ]
    }
    
    fake_response = MaintenanceRequestResponse(
        id=125,
        issue_title="Water Damage",
        description="Water damage on ceiling",
        property=PropertyInfo(id=1, name="Test Property"),
        unit=None,
        tenant=None,
        request_date=datetime.now(timezone.utc),
        priority=MaintenancePriority.HIGH,
        status=MaintenanceStatus.PENDING,
        scheduled_date=None,
        completed_date=None,
        estimated_cost=None,
        actual_cost=None,
        photos=[
            "https://storage.example.com/photo1.jpg",
            "https://storage.example.com/photo2.jpg"
        ],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        assigned_to=None,
        vendor_id=None,
        vendor=None,
        notify_tenant=False
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.create_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/maintenance/requests", json=request_data)
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["photos"] == [
                "https://storage.example.com/photo1.jpg",
                "https://storage.example.com/photo2.jpg"
            ]


def test_create_maintenance_request_forbidden_wrong_property():
    """Test 403 error when user tries to create request for property they don't own."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, is_admin=False)
    
    request_data = {
        "issue_title": "Unauthorized Issue",
        "property_id": 999,  # Property not owned by user
        "priority": "LOW"
    }
    
    # Mock the service layer to raise 403
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.create_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(
            status_code=403, 
            detail="You do not have permission to create a maintenance request for this property."
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/maintenance/requests", json=request_data)
            
            # Assert
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()


def test_create_maintenance_request_invalid_unit_property_mismatch():
    """Test 400 error when unit doesn't belong to the specified property."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    request_data = {
        "issue_title": "Mismatched Unit",
        "property_id": 1,
        "unit_id": 99,  # Unit from different property
        "priority": "MEDIUM"
    }
    
    # Mock the service layer to raise 400
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.create_maintenance_request",
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
            response = client.post("/api/maintenance/requests", json=request_data)
            
            # Assert
            assert response.status_code == 400
            assert "unit does not belong" in response.json()["detail"].lower()


def test_create_maintenance_request_nonexistent_property():
    """Test 404 error when property doesn't exist."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    request_data = {
        "issue_title": "Issue for Nonexistent Property",
        "property_id": 99999,
        "priority": "HIGH"
    }
    
    # Mock the service layer to raise 404
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.create_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(
            status_code=404,
            detail="Property not found."
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/maintenance/requests", json=request_data)
            
            # Assert
            assert response.status_code == 404
            assert "Property not found" in response.json()["detail"]


def test_create_maintenance_request_nonexistent_unit():
    """Test 404 error when unit doesn't exist."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    request_data = {
        "issue_title": "Issue for Nonexistent Unit",
        "property_id": 1,
        "unit_id": 99999,
        "priority": "MEDIUM"
    }
    
    # Mock the service layer to raise 404
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.create_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(
            status_code=404,
            detail="Unit not found."
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/maintenance/requests", json=request_data)
            
            # Assert
            assert response.status_code == 404
            assert "Unit not found" in response.json()["detail"]


def test_create_maintenance_request_nonexistent_tenant():
    """Test 404 error when tenant doesn't exist."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    request_data = {
        "issue_title": "Issue with Nonexistent Tenant",
        "property_id": 1,
        "tenant_id": 99999,
        "priority": "LOW"
    }
    
    # Mock the service layer to raise 404
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.create_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(
            status_code=404,
            detail="Tenant not found."
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/maintenance/requests", json=request_data)
            
            # Assert
            assert response.status_code == 404
            assert "Tenant not found" in response.json()["detail"]


def test_create_maintenance_request_admin_any_property():
    """Test that admin can create maintenance request for any property."""
    # Arrange
    admin_id = uuid4()
    admin_user = create_test_user(
        user_id=admin_id,
        email="admin@example.com",
        user_type=UserType.ADMIN,
        is_admin=True
    )
    
    request_data = {
        "issue_title": "Admin Created Issue",
        "description": "Issue created by admin for another user's property",
        "property_id": 5,  # Property owned by someone else
        "priority": "MEDIUM"
    }
    
    fake_response = MaintenanceRequestResponse(
        id=126,
        issue_title="Admin Created Issue",
        description="Issue created by admin for another user's property",
        property=PropertyInfo(id=5, name="Someone's Property"),
        unit=None,
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
    with patch("Backend.api.maintenance.router.MaintenanceService.create_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/maintenance/requests", json=request_data)
            
            # Assert - Admin should be able to create the request
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 126
            assert data["property"]["id"] == 5


def test_create_maintenance_request_database_error():
    """Test error handling for database exceptions during creation."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    request_data = {
        "issue_title": "Database Error Test",
        "property_id": 1,
        "priority": "HIGH"
    }
    
    # Mock the service layer to raise a database error
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.create_maintenance_request",
        new=AsyncMock(side_effect=Exception("Database connection failed"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/maintenance/requests", json=request_data)
            
            # Assert
            assert response.status_code == 500
            assert "Failed to create maintenance request" in response.json()["detail"]


def test_create_maintenance_request_invalid_priority():
    """Test validation error for invalid priority value."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    request_data = {
        "issue_title": "Invalid Priority",
        "property_id": 1,
        "priority": "SUPER_URGENT"  # Invalid priority
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/maintenance/requests", json=request_data)
        
        # Assert
        assert response.status_code == 422  # Validation error


def test_create_maintenance_request_missing_required_fields():
    """Test validation error when required fields are missing."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    request_data = {
        "description": "Missing required fields"
        # Missing: issue_title, property_id, priority
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/maintenance/requests", json=request_data)
        
        # Assert
        assert response.status_code == 422  # Validation error
        error_detail = response.json()["detail"]
        assert any("issue_title" in str(err) for err in error_detail)
        assert any("property_id" in str(err) for err in error_detail)
        assert any("priority" in str(err) for err in error_detail)