"""
API tests for GET /api/accounting/rent-tracker/ (entries) endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.api.accounting.rent_tracker.schemas import (
    RentTrackingEntry, 
    RentTrackerSummary, 
    RentStatus,
    RentTrackerFilter
)
from Backend.models.user import User
from Backend.models.enums import UserType
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

def create_mock_rent_tracking_entry(
    lease_id=1,
    tenant_id=1,
    tenant_name="John Doe",
    property_name="Test Property",
    unit_name="Unit 1A",
    monthly_rent=Decimal("1500.00"),
    amount_paid=Decimal("1500.00"),
    status=RentStatus.PAID,
    **kwargs
):
    """Helper function to create a mock rent tracking entry."""
    return RentTrackingEntry(
        lease_id=lease_id,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        property_name=property_name,
        unit_name=unit_name,
        monthly_rent=monthly_rent,
        amount_paid=amount_paid,
        remaining_due=monthly_rent - amount_paid,
        status=status,
        due_date=kwargs.get('due_date', date(2024, 1, 1)),
        last_payment_date=kwargs.get('last_payment_date'),
        days_overdue=kwargs.get('days_overdue')
    )

def create_mock_rent_tracker_summary():
    """Helper function to create a mock rent tracker summary."""
    return RentTrackerSummary(
        total_units=10,
        total_expected=Decimal("15000.00"),
        total_collected=Decimal("12000.00"),
        total_outstanding=Decimal("3000.00"),
        units_paid=7,
        units_partial=1,
        units_due=1,
        units_overdue=1,
        collection_rate=Decimal("80.00")
    )

# =============================================================================
# GET RENT TRACKER ENTRIES TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_rent_tracker_success_admin():
    """Test successful rent tracker retrieval for ADMIN user."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN, is_admin=True)
    mock_session = AsyncMock()
    
    mock_entries = [
        create_mock_rent_tracking_entry(
            lease_id=1, tenant_name="John Doe", status=RentStatus.PAID
        ),
        create_mock_rent_tracking_entry(
            lease_id=2, tenant_name="Jane Smith", status=RentStatus.OVERDUE,
            amount_paid=Decimal("0.00"), days_overdue=5
        ),
    ]

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_entries
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["tenant_name"] == "John Doe"
        assert data[0]["status"] == "PAID"
        assert data[1]["tenant_name"] == "Jane Smith"
        assert data[1]["status"] == "OVERDUE"
        assert data[1]["days_overdue"] == 5
        
        # Verify service was called with correct parameters
        mock_service.assert_called_once()
        call_args = mock_service.call_args[1]
        assert call_args["session"] == mock_session
        assert call_args["current_user"] == mock_user
        assert isinstance(call_args["filters"], RentTrackerFilter)

@pytest.mark.asyncio
async def test_get_rent_tracker_success_landlord():
    """Test successful rent tracker retrieval for LANDLORD user."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    
    mock_entries = [
        create_mock_rent_tracking_entry(
            lease_id=1, tenant_name="Alice Johnson", status=RentStatus.PARTIAL,
            amount_paid=Decimal("800.00")
        )
    ]

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_entries
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["tenant_name"] == "Alice Johnson"
        assert data[0]["status"] == "PARTIAL"
        assert data[0]["amount_paid"] == "800.00"
        assert data[0]["remaining_due"] == "700.00"

@pytest.mark.asyncio
async def test_get_rent_tracker_with_month_year_filter():
    """Test rent tracker retrieval with month and year filters."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()
    mock_entries = [create_mock_rent_tracking_entry()]

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_entries
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/?month=5&year=2024")
        
        # Assert
        assert response.status_code == 200
        
        # Verify service was called with correct filters
        mock_service.assert_called_once()
        call_args = mock_service.call_args[1]
        filters = call_args["filters"]
        assert filters.month == 5
        assert filters.year == 2024

@pytest.mark.asyncio
async def test_get_rent_tracker_with_property_filter():
    """Test rent tracker retrieval with property filter."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    mock_entries = [create_mock_rent_tracking_entry(property_name="Specific Property")]

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_entries
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/?property_id=123")
        
        # Assert
        assert response.status_code == 200
        
        # Verify service was called with property filter
        mock_service.assert_called_once()
        call_args = mock_service.call_args[1]
        filters = call_args["filters"]
        assert filters.property_id == 123

@pytest.mark.asyncio
async def test_get_rent_tracker_with_status_filter():
    """Test rent tracker retrieval with rent status filter."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()
    mock_entries = [
        create_mock_rent_tracking_entry(status=RentStatus.OVERDUE, days_overdue=10)
    ]

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_entries
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/?status=OVERDUE")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["status"] == "OVERDUE"
        
        # Verify service was called with status filter
        mock_service.assert_called_once()
        call_args = mock_service.call_args[1]
        filters = call_args["filters"]
        assert filters.status == RentStatus.OVERDUE

@pytest.mark.asyncio
async def test_get_rent_tracker_with_include_vacant():
    """Test rent tracker retrieval with include_vacant flag."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()
    mock_entries = [
        create_mock_rent_tracking_entry(tenant_name="No Tenant", status=RentStatus.DUE)
    ]

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_entries
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/?include_vacant=true")
        
        # Assert
        assert response.status_code == 200
        
        # Verify service was called with include_vacant flag
        mock_service.assert_called_once()
        call_args = mock_service.call_args[1]
        filters = call_args["filters"]
        assert filters.include_vacant is True

@pytest.mark.asyncio
async def test_get_rent_tracker_with_all_filters():
    """Test rent tracker retrieval with all query parameters."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    mock_entries = [create_mock_rent_tracking_entry()]

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_entries
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get(
            "/api/accounting/rent-tracker/"
            "?month=3&year=2024&property_id=456&status=PARTIAL&include_vacant=false"
        )
        
        # Assert
        assert response.status_code == 200
        
        # Verify service was called with all filters
        mock_service.assert_called_once()
        call_args = mock_service.call_args[1]
        filters = call_args["filters"]
        assert filters.month == 3
        assert filters.year == 2024
        assert filters.property_id == 456
        assert filters.status == RentStatus.PARTIAL
        assert filters.include_vacant is False

@pytest.mark.asyncio
async def test_get_rent_tracker_empty_result():
    """Test rent tracker retrieval with no matching entries."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call to return empty list
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = []
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

@pytest.mark.asyncio
async def test_get_rent_tracker_forbidden_tenant_user():
    """Test rent tracker access forbidden for TENANT user."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.TENANT)
    mock_session = AsyncMock()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service to raise forbidden exception
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view rent tracker"
        )
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/")
        
        # Assert
        assert response.status_code == 403
        data = response.json()
        assert "Not authorized to view rent tracker" in data["detail"]

@pytest.mark.asyncio
async def test_get_rent_tracker_service_error():
    """Test rent tracker retrieval when service raises an error."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service to raise an error
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rent tracker: Database error"
        )
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/")
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get rent tracker" in data["detail"]

# =============================================================================
# PARAMETER VALIDATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_rent_tracker_invalid_month():
    """Test rent tracker retrieval with invalid month parameter."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    client = TestClientWithHost(app)
    
    # Act
    response = client.get("/api/accounting/rent-tracker/?month=13")
    
    # Assert
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

@pytest.mark.asyncio
async def test_get_rent_tracker_invalid_year():
    """Test rent tracker retrieval with invalid year parameter."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    client = TestClientWithHost(app)
    
    # Act
    response = client.get("/api/accounting/rent-tracker/?year=1999")
    
    # Assert
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

@pytest.mark.asyncio
async def test_get_rent_tracker_invalid_rent_status():
    """Test rent tracker retrieval with invalid rent status parameter."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    client = TestClientWithHost(app)
    
    # Act
    response = client.get("/api/accounting/rent-tracker/?status=INVALID_STATUS")
    
    # Assert
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

# =============================================================================
# MULTIPLE STATUS TYPES TESTS
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_filter, expected_statuses",
    [
        (RentStatus.PAID, [RentStatus.PAID]),
        (RentStatus.PARTIAL, [RentStatus.PARTIAL]),
        (RentStatus.DUE, [RentStatus.DUE]),
        (RentStatus.OVERDUE, [RentStatus.OVERDUE]),
    ],
    ids=["paid_only", "partial_only", "due_only", "overdue_only"]
)
async def test_get_rent_tracker_status_filtering(status_filter, expected_statuses):
    """Test that rent tracker correctly filters by different status types."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()
    
    # Create entries with the expected status
    mock_entries = [
        create_mock_rent_tracking_entry(
            lease_id=i, 
            tenant_name=f"Tenant {i}", 
            status=status
        ) for i, status in enumerate(expected_statuses, 1)
    ]

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_entries
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get(f"/api/accounting/rent-tracker/?status={status_filter.value}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == len(expected_statuses)
        for i, entry in enumerate(data):
            assert entry["status"] == expected_statuses[i].value

@pytest.mark.asyncio
async def test_get_rent_tracker_mixed_status_entries():
    """Test rent tracker with mixed status entries when no filter is applied."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    
    mock_entries = [
        create_mock_rent_tracking_entry(lease_id=1, status=RentStatus.PAID),
        create_mock_rent_tracking_entry(lease_id=2, status=RentStatus.PARTIAL),
        create_mock_rent_tracking_entry(lease_id=3, status=RentStatus.DUE),
        create_mock_rent_tracking_entry(lease_id=4, status=RentStatus.OVERDUE),
    ]

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_entries
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 4
        statuses = [entry["status"] for entry in data]
        assert "PAID" in statuses
        assert "PARTIAL" in statuses
        assert "DUE" in statuses
        assert "OVERDUE" in statuses

# =============================================================================
# EDGE CASES AND BOUNDARY TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_rent_tracker_boundary_month_values():
    """Test rent tracker with boundary month values."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()
    mock_entries = [create_mock_rent_tracking_entry()]

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_entries
        
        client = TestClientWithHost(app)
        
        # Test minimum month value
        response = client.get("/api/accounting/rent-tracker/?month=1")
        assert response.status_code == 200
        
        # Test maximum month value
        response = client.get("/api/accounting/rent-tracker/?month=12")
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_rent_tracker_boundary_year_values():
    """Test rent tracker with boundary year values."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()
    mock_entries = [create_mock_rent_tracking_entry()]

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_entries
        
        client = TestClientWithHost(app)
        
        # Test minimum year value
        response = client.get("/api/accounting/rent-tracker/?year=2000")
        assert response.status_code == 200
        
        # Test maximum year value
        response = client.get("/api/accounting/rent-tracker/?year=2100")
        assert response.status_code == 200