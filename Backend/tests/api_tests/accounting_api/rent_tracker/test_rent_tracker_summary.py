"""
API tests for GET /api/accounting/rent-tracker/summary endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.api.accounting.rent_tracker.schemas import (
    RentTrackerSummary, 
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

def create_mock_rent_tracker_summary(
    total_units=10,
    total_expected=Decimal("15000.00"),
    total_collected=Decimal("12000.00"),
    total_outstanding=Decimal("3000.00"),
    units_paid=7,
    units_partial=1,
    units_due=1,
    units_overdue=1,
    collection_rate=Decimal("80.00")
):
    """Helper function to create a mock rent tracker summary."""
    return RentTrackerSummary(
        total_units=total_units,
        total_expected=total_expected,
        total_collected=total_collected,
        total_outstanding=total_outstanding,
        units_paid=units_paid,
        units_partial=units_partial,
        units_due=units_due,
        units_overdue=units_overdue,
        collection_rate=collection_rate
    )

# =============================================================================
# GET RENT TRACKER SUMMARY TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_success_admin():
    """Test successful rent tracker summary retrieval for ADMIN user."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN, is_admin=True)
    mock_session = AsyncMock()
    
    mock_summary = create_mock_rent_tracker_summary()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_units"] == 10
        assert data["total_expected"] == "15000.00"
        assert data["total_collected"] == "12000.00"
        assert data["total_outstanding"] == "3000.00"
        assert data["units_paid"] == 7
        assert data["units_partial"] == 1
        assert data["units_due"] == 1
        assert data["units_overdue"] == 1
        assert data["collection_rate"] == "80.00"
        
        # Verify service was called with correct parameters
        mock_service.assert_called_once()
        call_args = mock_service.call_args[1]
        assert call_args["session"] == mock_session
        assert call_args["current_user"] == mock_user
        assert isinstance(call_args["filters"], RentTrackerFilter)

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_success_landlord():
    """Test successful rent tracker summary retrieval for LANDLORD user."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    
    mock_summary = create_mock_rent_tracker_summary(
        total_units=5,
        total_expected=Decimal("7500.00"),
        total_collected=Decimal("6000.00"),
        total_outstanding=Decimal("1500.00"),
        units_paid=3,
        units_partial=1,
        units_due=1,
        units_overdue=0,
        collection_rate=Decimal("80.00")
    )

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_units"] == 5
        assert data["total_expected"] == "7500.00"
        assert data["total_collected"] == "6000.00"
        assert data["total_outstanding"] == "1500.00"
        assert data["units_paid"] == 3
        assert data["units_partial"] == 1
        assert data["units_due"] == 1
        assert data["units_overdue"] == 0
        assert data["collection_rate"] == "80.00"

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_with_month_year_filter():
    """Test rent tracker summary retrieval with month and year filters."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()
    mock_summary = create_mock_rent_tracker_summary()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary?month=5&year=2024")
        
        # Assert
        assert response.status_code == 200
        
        # Verify service was called with correct filters
        mock_service.assert_called_once()
        call_args = mock_service.call_args[1]
        filters = call_args["filters"]
        assert filters.month == 5
        assert filters.year == 2024

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_with_property_filter():
    """Test rent tracker summary retrieval with property filter."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    mock_summary = create_mock_rent_tracker_summary(
        total_units=3,
        total_expected=Decimal("4500.00"),
        total_collected=Decimal("4500.00"),
        total_outstanding=Decimal("0.00"),
        units_paid=3,
        units_partial=0,
        units_due=0,
        units_overdue=0,
        collection_rate=Decimal("100.00")
    )

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary?property_id=123")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["collection_rate"] == "100.00"
        assert data["units_overdue"] == 0
        
        # Verify service was called with property filter
        mock_service.assert_called_once()
        call_args = mock_service.call_args[1]
        filters = call_args["filters"]
        assert filters.property_id == 123

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_with_all_filters():
    """Test rent tracker summary retrieval with all query parameters."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    mock_summary = create_mock_rent_tracker_summary()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get(
            "/api/accounting/rent-tracker/summary"
            "?month=3&year=2024&property_id=456"
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
        assert filters.status is None  # Summary doesn't filter by status
        assert filters.include_vacant is False  # Summary doesn't include vacant by default

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_zero_values():
    """Test rent tracker summary with zero values (no active leases)."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    
    mock_summary = create_mock_rent_tracker_summary(
        total_units=0,
        total_expected=Decimal("0.00"),
        total_collected=Decimal("0.00"),
        total_outstanding=Decimal("0.00"),
        units_paid=0,
        units_partial=0,
        units_due=0,
        units_overdue=0,
        collection_rate=Decimal("0.00")
    )

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_units"] == 0
        assert data["total_expected"] == "0.00"
        assert data["total_collected"] == "0.00"
        assert data["total_outstanding"] == "0.00"
        assert data["units_paid"] == 0
        assert data["units_partial"] == 0
        assert data["units_due"] == 0
        assert data["units_overdue"] == 0
        assert data["collection_rate"] == "0.00"

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_forbidden_tenant_user():
    """Test rent tracker summary access forbidden for TENANT user."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.TENANT)
    mock_session = AsyncMock()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service to raise forbidden exception
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view rent tracker summary"
        )
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 403
        data = response.json()
        assert "Not authorized to view rent tracker summary" in data["detail"]

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_service_error():
    """Test rent tracker summary retrieval when service raises an error."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service to raise an error
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rent tracker summary: Database error"
        )
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get rent tracker summary" in data["detail"]

# =============================================================================
# PARAMETER VALIDATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_invalid_month():
    """Test rent tracker summary retrieval with invalid month parameter."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    client = TestClientWithHost(app)
    
    # Act
    response = client.get("/api/accounting/rent-tracker/summary?month=13")
    
    # Assert
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_invalid_year():
    """Test rent tracker summary retrieval with invalid year parameter."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    client = TestClientWithHost(app)
    
    # Act
    response = client.get("/api/accounting/rent-tracker/summary?year=1999")
    
    # Assert
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

# =============================================================================
# EDGE CASES AND BOUNDARY TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_boundary_month_values():
    """Test rent tracker summary with boundary month values."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()
    mock_summary = create_mock_rent_tracker_summary()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Test minimum month value
        response = client.get("/api/accounting/rent-tracker/summary?month=1")
        assert response.status_code == 200
        
        # Test maximum month value
        response = client.get("/api/accounting/rent-tracker/summary?month=12")
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_boundary_year_values():
    """Test rent tracker summary with boundary year values."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()
    mock_summary = create_mock_rent_tracker_summary()

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Test minimum year value
        response = client.get("/api/accounting/rent-tracker/summary?year=2000")
        assert response.status_code == 200
        
        # Test maximum year value
        response = client.get("/api/accounting/rent-tracker/summary?year=2100")
        assert response.status_code == 200

# =============================================================================
# COLLECTION RATE CALCULATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_perfect_collection_rate():
    """Test rent tracker summary with 100% collection rate."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    
    mock_summary = create_mock_rent_tracker_summary(
        total_units=5,
        total_expected=Decimal("7500.00"),
        total_collected=Decimal("7500.00"),
        total_outstanding=Decimal("0.00"),
        units_paid=5,
        units_partial=0,
        units_due=0,
        units_overdue=0,
        collection_rate=Decimal("100.00")
    )

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["collection_rate"] == "100.00"
        assert data["total_outstanding"] == "0.00"
        assert data["units_paid"] == 5
        assert data["units_overdue"] == 0

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_zero_collection_rate():
    """Test rent tracker summary with 0% collection rate."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    
    mock_summary = create_mock_rent_tracker_summary(
        total_units=3,
        total_expected=Decimal("4500.00"),
        total_collected=Decimal("0.00"),
        total_outstanding=Decimal("4500.00"),
        units_paid=0,
        units_partial=0,
        units_due=1,
        units_overdue=2,
        collection_rate=Decimal("0.00")
    )

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["collection_rate"] == "0.00"
        assert data["total_collected"] == "0.00"
        assert data["units_paid"] == 0
        assert data["units_overdue"] == 2

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_partial_collection_rate():
    """Test rent tracker summary with partial collection rate."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN)
    mock_session = AsyncMock()
    
    mock_summary = create_mock_rent_tracker_summary(
        total_units=8,
        total_expected=Decimal("12000.00"),
        total_collected=Decimal("7200.00"),
        total_outstanding=Decimal("4800.00"),
        units_paid=4,
        units_partial=2,
        units_due=1,
        units_overdue=1,
        collection_rate=Decimal("60.00")
    )

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["collection_rate"] == "60.00"
        assert data["total_collected"] == "7200.00"
        assert data["total_outstanding"] == "4800.00"
        assert data["units_partial"] == 2


# =============================================================================
# OVERPAYMENT SCENARIO API TESTS (NEW)
# =============================================================================

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_overpayment_scenario():
    """Test rent tracker summary API with overpayment scenarios (negative outstanding, >100% collection)."""
    # Arrange - simulate real production data with massive overpayments
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    
    # Create summary with negative outstanding and high collection rate
    mock_summary = create_mock_rent_tracker_summary(
        total_units=3,
        total_expected=Decimal("4500.00"),     # $1500 * 3 units expected
        total_collected=Decimal("67999.87"),   # Massive overpayment (real production data)
        total_outstanding=Decimal("-63499.87"), # Credit balance
        units_paid=3,
        units_partial=0,
        units_due=0,
        units_overdue=0,
        collection_rate=Decimal("1511.11")    # 1,511% collection rate
    )

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify negative outstanding is properly returned
        assert data["total_outstanding"] == "-63499.87"
        
        # Verify high collection rate is properly returned
        assert data["collection_rate"] == "1511.11"
        
        # Verify other fields
        assert data["total_units"] == 3
        assert data["total_expected"] == "4500.00"
        assert data["total_collected"] == "67999.87"
        assert data["units_paid"] == 3
        assert data["units_partial"] == 0


@pytest.mark.asyncio
async def test_get_rent_tracker_summary_extreme_overpayment():
    """Test rent tracker summary API with extreme overpayment (127.5 months scenario)."""
    # Arrange - simulate the actual production case
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    
    # Tenant paid 127.5 months of $1000 rent = $127,500
    mock_summary = create_mock_rent_tracker_summary(
        total_units=1,
        total_expected=Decimal("1000.00"),      # $1000 expected for current month
        total_collected=Decimal("127500.00"),   # $127,500 total collected
        total_outstanding=Decimal("-126500.00"), # Huge credit balance
        units_paid=1,
        units_partial=0,
        units_due=0,
        units_overdue=0,
        collection_rate=Decimal("12750.00")     # 12,750% collection rate
    )

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify extreme values are handled correctly
        assert data["total_outstanding"] == "-126500.00"
        assert data["collection_rate"] == "12750.00"
        assert data["total_collected"] == "127500.00"
        assert data["units_paid"] == 1


@pytest.mark.asyncio
async def test_get_rent_tracker_summary_mixed_overpayment_underpayment():
    """Test rent tracker summary API with mixed overpayment and underpayment scenarios."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.ADMIN, is_admin=True)
    mock_session = AsyncMock()
    
    # Some tenants overpaid, some underpaid, net result is credit balance
    mock_summary = create_mock_rent_tracker_summary(
        total_units=10,
        total_expected=Decimal("15000.00"),    # 10 units * $1500 average
        total_collected=Decimal("20000.00"),   # Total overpayment across all units
        total_outstanding=Decimal("-5000.00"), # Net credit balance
        units_paid=8,  # Most units fully paid
        units_partial=1,
        units_due=0,
        units_overdue=1,
        collection_rate=Decimal("133.33")      # 133.33% collection rate
    )

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify mixed scenario handling
        assert data["total_outstanding"] == "-5000.00"
        assert data["collection_rate"] == "133.33"
        assert data["units_paid"] == 8
        assert data["units_overdue"] == 1


@pytest.mark.asyncio
async def test_get_rent_tracker_summary_advance_payment_scenario():
    """Test rent tracker summary API with advance payment scenarios."""
    # Arrange - tenant paid multiple months in advance
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    mock_session = AsyncMock()
    
    mock_summary = create_mock_rent_tracker_summary(
        total_units=2,
        total_expected=Decimal("3000.00"),     # 2 units * $1500
        total_collected=Decimal("36000.00"),   # 12 months advance payment
        total_outstanding=Decimal("-33000.00"), # Major advance payment credit
        units_paid=2,
        units_partial=0,
        units_due=0,
        units_overdue=0,
        collection_rate=Decimal("1200.00")     # 1200% collection rate (12 months)
    )

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock service call
    with patch('Backend.api.accounting.rent_tracker.router.RentTrackerService.get_rent_tracker_summary', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_summary
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/accounting/rent-tracker/summary")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify advance payment scenario
        assert data["total_outstanding"] == "-33000.00"
        assert data["collection_rate"] == "1200.00"
        assert data["units_paid"] == 2
        assert data["units_partial"] == 0
        assert data["units_due"] == 0