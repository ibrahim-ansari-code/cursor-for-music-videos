"""
Unit tests for GET operations in the maintenance API endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.maintenance.schemas import (
    MaintenanceRequestResponse,
    PropertyInfo,
    UnitInfo,
    TenantInfo,
    MaintenanceSummaryResponse
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
        # Always add localhost to headers if not present
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

def create_mock_maintenance_request(request_id=1, **kwargs):
    """Helper function to create a mock maintenance request with all required attributes."""
    now = datetime.now(timezone.utc)
    mock_request = MagicMock(spec=MaintenanceRequest)
    mock_request.id = request_id
    mock_request.issue_title = kwargs.get('issue_title', 'Test Issue')
    mock_request.description = kwargs.get('description', 'Test description')
    mock_request.property_id = kwargs.get('property_id', 1)
    mock_request.unit_id = kwargs.get('unit_id', None)
    mock_request.tenant_id = kwargs.get('tenant_id', None)
    mock_request.user_id = kwargs.get('user_id', uuid4())
    mock_request.request_date = kwargs.get('request_date', now)
    mock_request.priority = kwargs.get('priority', MaintenancePriority.MEDIUM)
    mock_request.status = kwargs.get('status', MaintenanceStatus.PENDING)
    mock_request.scheduled_date = kwargs.get('scheduled_date', None)
    mock_request.completed_date = kwargs.get('completed_date', None)
    mock_request.estimated_cost = kwargs.get('estimated_cost', None)
    mock_request.actual_cost = kwargs.get('actual_cost', None)
    mock_request.photos = kwargs.get('photos', None)
    mock_request.assigned_to = kwargs.get('assigned_to', None)
    mock_request.created_at = kwargs.get('created_at', now)
    mock_request.updated_at = kwargs.get('updated_at', now)
    mock_request.property = kwargs.get('property', None)
    mock_request.unit = kwargs.get('unit', None)
    mock_request.tenant = kwargs.get('tenant', None)
    return mock_request

def create_mock_property(property_id=1, **kwargs):
    """Helper function to create a mock property."""
    mock_property = MagicMock(spec=Property)
    mock_property.id = property_id
    mock_property.name = kwargs.get('name', 'Test Property')
    mock_property.user_id = kwargs.get('user_id', uuid4())
    return mock_property

def create_mock_unit(unit_id=1, **kwargs):
    """Helper function to create a mock unit."""
    mock_unit = MagicMock(spec=PropertyUnit)
    mock_unit.id = unit_id
    mock_unit.name = kwargs.get('name', 'Unit 1')
    return mock_unit

def create_mock_tenant(tenant_id=1, **kwargs):
    """Helper function to create a mock tenant."""
    mock_tenant = MagicMock(spec=Tenant)
    mock_tenant.id = tenant_id
    mock_tenant.first_name = kwargs.get('first_name', 'John')
    mock_tenant.last_name = kwargs.get('last_name', 'Doe')
    return mock_tenant

# =============================================================================
# GET SINGLE MAINTENANCE REQUEST TESTS
# =============================================================================

def test_get_maintenance_request_owner_success():
    """Test successful maintenance request retrieval by property owner."""
    # Arrange
    request_id = 123
    owner_id = uuid4()
    fake_user = create_test_user(user_id=owner_id, email="owner@example.com")
    
    # Mock property
    property_mock = create_mock_property(property_id=1, name="Test Property", user_id=owner_id)
    
    # Mock unit
    unit_mock = create_mock_unit(unit_id=1, name="Unit A")
    
    # Mock tenant
    tenant_mock = create_mock_tenant(tenant_id=1, first_name="Jane", last_name="Smith")
    
    # Create mock maintenance request
    fake_request = create_mock_maintenance_request(
        request_id=request_id,
        issue_title="Leaking Faucet",
        description="Kitchen faucet is leaking",
        property_id=1,
        unit_id=1,
        tenant_id=1,
        user_id=owner_id,
        priority=MaintenancePriority.HIGH,
        status=MaintenanceStatus.IN_PROGRESS,
        scheduled_date=date(2024, 1, 15),
        estimated_cost=Decimal("150.00"),
        property=property_mock,
        unit=unit_mock,
        tenant=tenant_mock
    )
    
    # Create the response object that the service would return
    fake_response = MaintenanceRequestResponse(
        id=request_id,
        issue_title="Leaking Faucet",
        description="Kitchen faucet is leaking",
        property=PropertyInfo(id=1, name="Test Property"),
        unit=UnitInfo(id=1, name="Unit A"),
        tenant=TenantInfo(id=1, first_name="Jane", last_name="Smith"),
        request_date=fake_request.request_date,
        priority=MaintenancePriority.HIGH,
        status=MaintenanceStatus.IN_PROGRESS,
        scheduled_date=date(2024, 1, 15),
        completed_date=None,
        estimated_cost=Decimal("150.00"),
        actual_cost=None,
        photos=None,
        created_at=fake_request.created_at,
        updated_at=fake_request.updated_at,
        assigned_to=None,
        vendor_id=None,
        vendor=None,
        notify_tenant=False
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.get_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/maintenance/requests/{request_id}")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == request_id
            assert data["issue_title"] == "Leaking Faucet"
            assert data["description"] == "Kitchen faucet is leaking"
            assert data["property"]["name"] == "Test Property"
            assert data["unit"]["name"] == "Unit A"
            assert data["tenant"]["first_name"] == "Jane"
            assert data["tenant"]["last_name"] == "Smith"
            assert data["priority"] == "High"
            assert data["status"] == "In Progress"
            assert data["scheduled_date"] == "2024-01-15"
            assert data["estimated_cost"] == "150.00"


def test_get_maintenance_request_admin_can_view_any():
    """Test that admin can view maintenance requests they don't own."""
    # Arrange
    request_id = 456
    owner_id = uuid4()
    admin_id = uuid4()
    
    admin_user = create_test_user(
        user_id=admin_id,
        email="admin@example.com",
        user_type=UserType.ADMIN,
        is_admin=True
    )
    
    property_mock = create_mock_property(property_id=1, name="Someone's Property", user_id=owner_id)
    
    fake_request = create_mock_maintenance_request(
        request_id=request_id,
        issue_title="Broken Window",
        property_id=1,
        user_id=owner_id,
        property=property_mock
    )
    
    fake_response = MaintenanceRequestResponse(
        id=request_id,
        issue_title="Broken Window",
        description=fake_request.description,
        property=PropertyInfo(id=1, name="Someone's Property"),
        unit=None,
        tenant=None,
        request_date=fake_request.request_date,
        priority=fake_request.priority,
        status=fake_request.status,
        scheduled_date=None,
        completed_date=None,
        estimated_cost=None,
        actual_cost=None,
        photos=None,
        created_at=fake_request.created_at,
        updated_at=fake_request.updated_at,
        assigned_to=None,
        vendor_id=None,
        vendor=None,
        notify_tenant=False
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.get_maintenance_request", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/maintenance/requests/{request_id}")
            
            # Assert - Admin should be able to view the request
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == request_id


def test_get_maintenance_request_not_found():
    """Test 404 error when maintenance request doesn't exist."""
    # Arrange
    request_id = 999
    fake_user = create_test_user()
    
    # Mock the service layer to raise 404
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.get_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Maintenance request not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/maintenance/requests/{request_id}")
            
            # Assert
            assert response.status_code == 404
            assert "Maintenance request not found" in response.json()["detail"]


def test_get_maintenance_request_forbidden_non_owner():
    """Test 403 error when non-owner/non-admin tries to access maintenance request."""
    # Arrange
    request_id = 123
    owner_id = uuid4()
    other_user_id = uuid4()
    
    other_user = create_test_user(
        user_id=other_user_id,
        email="other@example.com"
    )
    
    # Mock the service layer to raise 403
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.get_maintenance_request",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="You do not have permission to access this maintenance request"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: other_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/maintenance/requests/{request_id}")
            
            # Assert
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()


# =============================================================================
# GET MAINTENANCE REQUESTS (LIST) TESTS
# =============================================================================

def test_get_maintenance_requests_regular_user_sees_only_own():
    """Test that regular users only see maintenance requests for their properties."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Create mock requests
    property_mock = create_mock_property(property_id=1, name="User's Property", user_id=user_id)
    
    request1 = create_mock_maintenance_request(
        request_id=1,
        issue_title="Issue 1",
        property_id=1,
        user_id=user_id,
        property=property_mock,
        status=MaintenanceStatus.PENDING
    )
    
    request2 = create_mock_maintenance_request(
        request_id=2,
        issue_title="Issue 2",
        property_id=1,
        user_id=user_id,
        property=property_mock,
        status=MaintenanceStatus.COMPLETED
    )
    
    # Create list response
    fake_response = [
        MaintenanceRequestResponse(
            id=1,
            issue_title="Issue 1",
            description=request1.description,
            property=PropertyInfo(id=1, name="User's Property"),
            unit=None,
            tenant=None,
            request_date=request1.request_date,
            priority=request1.priority,
            status=MaintenanceStatus.PENDING,
            scheduled_date=None,
            completed_date=None,
            estimated_cost=None,
            actual_cost=None,
            photos=None,
            created_at=request1.created_at,
            updated_at=request1.updated_at,
            assigned_to=None,
            vendor_id=None,
            vendor=None,
            notify_tenant=False
        ),
        MaintenanceRequestResponse(
            id=2,
            issue_title="Issue 2",
            description=request2.description,
            property=PropertyInfo(id=1, name="User's Property"),
            unit=None,
            tenant=None,
            request_date=request2.request_date,
            priority=request2.priority,
            status=MaintenanceStatus.COMPLETED,
            scheduled_date=None,
            completed_date=request2.completed_date,
            estimated_cost=None,
            actual_cost=None,
            photos=None,
            created_at=request2.created_at,
            updated_at=request2.updated_at,
            assigned_to=None,
            vendor_id=None,
            vendor=None,
            notify_tenant=False
        )
    ]
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.list_maintenance_requests", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/maintenance/requests")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["issue_title"] == "Issue 1"
            assert data[0]["status"] == "Pending"
            assert data[1]["issue_title"] == "Issue 2"
            assert data[1]["status"] == "Completed"


def test_get_maintenance_requests_with_filters():
    """Test maintenance request filtering by status, priority, and other fields."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Only high priority, pending requests should be returned
    property_mock = create_mock_property(property_id=1, name="Test Property", user_id=user_id)
    unit_mock = create_mock_unit(unit_id=5, name="Unit 5")
    
    filtered_request = create_mock_maintenance_request(
        request_id=1,
        issue_title="Urgent Issue",
        property_id=1,
        unit_id=5,
        priority=MaintenancePriority.HIGH,
        status=MaintenanceStatus.PENDING,
        property=property_mock,
        unit=unit_mock
    )
    
    # Create filtered response
    fake_response = [
        MaintenanceRequestResponse(
            id=1,
            issue_title="Urgent Issue",
            description=filtered_request.description,
            property=PropertyInfo(id=1, name="Test Property"),
            unit=UnitInfo(id=5, name="Unit 5"),
            tenant=None,
            request_date=filtered_request.request_date,
            priority=MaintenancePriority.HIGH,
            status=MaintenanceStatus.PENDING,
            scheduled_date=None,
            completed_date=None,
            estimated_cost=None,
            actual_cost=None,
            photos=None,
            created_at=filtered_request.created_at,
            updated_at=filtered_request.updated_at,
            assigned_to=None,
            vendor_id=None,
            vendor=None,
            notify_tenant=False
        )
    ]
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.list_maintenance_requests", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/maintenance/requests", params={
                "req_status": "PENDING",
                "priority": "HIGH",
                "property_id": 1,
                "unit_id": 5
            })
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["priority"] == "High"
            assert data[0]["status"] == "Pending"
            assert data[0]["unit"]["id"] == 5


def test_get_maintenance_requests_pagination():
    """Test pagination with limit and offset parameters."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Create a limited response (simulating pagination)
    fake_response = []
    for i in range(5):  # Only 5 results despite more being available
        fake_response.append(
            MaintenanceRequestResponse(
                id=i + 1,
                issue_title=f"Issue {i + 1}",
                description=f"Description {i + 1}",
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
        )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.list_maintenance_requests", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/maintenance/requests", params={
                "limit": 5,
                "offset": 10
            })
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 5


def test_get_maintenance_requests_database_error():
    """Test error handling for database exceptions."""
    # Arrange
    fake_user = create_test_user()
    
    # Mock the service layer to raise an exception
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.list_maintenance_requests",
        new=AsyncMock(side_effect=Exception("Database connection failed"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/maintenance/requests")
            
            # Assert
            assert response.status_code == 500
            assert "Failed to list maintenance requests" in response.json()["detail"]


# =============================================================================
# GET MAINTENANCE SUMMARY TESTS
# =============================================================================

def test_get_maintenance_summary_success():
    """Test successful retrieval of maintenance summary."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Create summary response
    fake_summary = MaintenanceSummaryResponse(
        total_requests=15,
        pending=5,
        in_progress=3,
        completed=6,
        scheduled=1,
        cancelled=0
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.get_maintenance_summary", new=AsyncMock(return_value=fake_summary)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/maintenance/summary")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["total_requests"] == 15
            assert data["pending"] == 5
            assert data["in_progress"] == 3
            assert data["completed"] == 6
            assert data["scheduled"] == 1
            assert data["cancelled"] == 0


def test_get_maintenance_summary_empty():
    """Test maintenance summary when user has no requests."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    
    # Create empty summary response
    fake_summary = MaintenanceSummaryResponse(
        total_requests=0,
        pending=0,
        in_progress=0,
        completed=0,
        scheduled=0,
        cancelled=0
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.get_maintenance_summary", new=AsyncMock(return_value=fake_summary)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/maintenance/summary")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["total_requests"] == 0
            assert all(v == 0 for k, v in data.items())


def test_get_maintenance_summary_admin_sees_all():
    """Test that admin sees summary of all maintenance requests."""
    # Arrange
    admin_id = uuid4()
    admin_user = create_test_user(
        user_id=admin_id,
        email="admin@example.com",
        user_type=UserType.ADMIN,
        is_admin=True
    )
    
    # Create summary with larger numbers (admin sees all)
    fake_summary = MaintenanceSummaryResponse(
        total_requests=100,
        pending=30,
        in_progress=20,
        completed=45,
        scheduled=5,
        cancelled=0
    )
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.get_maintenance_summary", new=AsyncMock(return_value=fake_summary)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/maintenance/summary")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["total_requests"] == 100
            assert data["pending"] == 30
            assert data["in_progress"] == 20
            assert data["completed"] == 45


def test_get_maintenance_summary_database_error():
    """Test error handling for database exceptions in summary endpoint."""
    # Arrange
    fake_user = create_test_user()
    
    # Mock the service layer to raise an exception
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.get_maintenance_summary",
        new=AsyncMock(side_effect=Exception("Database error"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/maintenance/summary")

            # Assert
            assert response.status_code == 500
            assert "Failed to get maintenance summary" in response.json()["detail"]


def test_get_maintenance_summary_with_property_filter():
    """Test maintenance summary filtered by property ID."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id)
    property_id = 123

    # Create filtered summary response
    fake_summary = MaintenanceSummaryResponse(
        total_requests=5,
        pending=2,
        in_progress=1,
        completed=2,
        scheduled=0,
        cancelled=0
    )

    # Mock the service layer
    mock_get_summary = AsyncMock(return_value=fake_summary)
    with patch("Backend.api.maintenance.router.MaintenanceService.get_maintenance_summary", new=mock_get_summary):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/maintenance/summary?property_id={property_id}")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["total_requests"] == 5
            assert data["pending"] == 2

            # Verify service was called with property_id parameter
            mock_get_summary.assert_called_once()
            call_kwargs = mock_get_summary.call_args.kwargs
            assert call_kwargs["property_id"] == property_id