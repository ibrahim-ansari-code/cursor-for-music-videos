"""
API tests for GET operations in the dashboard endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.api.dashboard.schemas import DashboardSummary, OccupancyData, RevenueData, PaymentDue
from Backend.models.user import User
from Backend.models.accounting.common import PaymentStatus
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

def create_test_user(user_id=None, email="test@example.com", user_type="LANDLORD", is_admin=False):
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
        updated_at=now
    )

def create_mock_dashboard_data():
    """Helper function to create mock dashboard data."""
    summary = DashboardSummary(
        total_properties=5,
        total_units=20,
        occupied_units=18,
        vacancy_rate=Decimal("10.0"),
        monthly_revenue=Decimal("15000.00"),
        monthly_expenses=Decimal("3000.00"),
        outstanding_rent=Decimal("2500.00"),
        maintenance_expenses=Decimal("1200.00")
    )
    
    occupancy = OccupancyData(
        total_units=20,
        occupied_units=18,
        vacant_units=2,
        occupancy_rate=Decimal("90.0")
    )
    
    revenue = RevenueData(
        months=["Jan", "Feb", "Mar"],
        revenue=[Decimal("5000"), Decimal("5200"), Decimal("5100")],
        expenses=[Decimal("1000"), Decimal("1100"), Decimal("900")],
        net_income=[Decimal("4000"), Decimal("4100"), Decimal("4200")]
    )
    
    payments_due = [
        PaymentDue(
            id=1,
            tenant_name="John Doe",
            amount=Decimal("1200.00"),
            due_date=date(2024, 1, 15),
            days_overdue=5,
            status=PaymentStatus.OVERDUE
        )
    ]
    
    return summary, occupancy, revenue, payments_due

class TestDashboardGetOperations:
    """Test class for dashboard GET operations."""

    @pytest.mark.asyncio
    async def test_get_dashboard_success_admin(self):
        """Test successful dashboard retrieval for ADMIN user."""
        # Arrange
        mock_user = create_test_user(user_type="ADMIN", is_admin=True)
        mock_session = AsyncMock()
        mock_dashboard_data = create_mock_dashboard_data()

        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock service call
        with patch('Backend.api.dashboard.service.DashboardService.get_dashboard', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_dashboard_data
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.get("/api/dashboard/")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            
            assert "summary" in data
            assert "occupancy" in data
            assert "revenue" in data
            assert "payments_due" in data
            
            # Verify service was called with correct parameters
            mock_service.assert_called_once()
            call_args = mock_service.call_args
            assert call_args[1]["session"] == mock_session
            assert call_args[1]["current_user"] == mock_user
            assert call_args[1]["property_id"] is None
            assert call_args[1]["time_period"] == "month"
            assert call_args[1]["start_date_override"] is None
            assert call_args[1]["end_date_override"] is None

    @pytest.mark.asyncio
    async def test_get_dashboard_success_landlord(self):
        """Test successful dashboard retrieval for LANDLORD user."""
        # Arrange
        mock_user = create_test_user(user_type="LANDLORD")
        mock_session = AsyncMock()
        mock_dashboard_data = create_mock_dashboard_data()

        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock service call
        with patch('Backend.api.dashboard.service.DashboardService.get_dashboard', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_dashboard_data
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.get("/api/dashboard/")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            
            assert "summary" in data
            assert data["summary"]["total_properties"] == 5
            assert data["occupancy"]["occupancy_rate"] == "90.0"
            assert len(data["payments_due"]) == 1

    @pytest.mark.asyncio
    async def test_get_dashboard_with_property_filter(self):
        """Test dashboard retrieval with property filter."""
        # Arrange
        mock_user = create_test_user(user_type="ADMIN")
        mock_session = AsyncMock()
        mock_dashboard_data = create_mock_dashboard_data()

        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock service call
        with patch('Backend.api.dashboard.service.DashboardService.get_dashboard', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_dashboard_data
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.get("/api/dashboard/?property_id=123")
            
            # Assert
            assert response.status_code == 200
            
            # Verify service was called with property filter
            mock_service.assert_called_once()
            call_args = mock_service.call_args
            assert call_args[1]["property_id"] == 123

    @pytest.mark.asyncio
    async def test_get_dashboard_with_time_period_filter(self):
        """Test dashboard retrieval with time period filter."""
        # Arrange
        mock_user = create_test_user(user_type="ADMIN")
        mock_session = AsyncMock()
        mock_dashboard_data = create_mock_dashboard_data()

        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock service call
        with patch('Backend.api.dashboard.service.DashboardService.get_dashboard', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_dashboard_data
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.get("/api/dashboard/?time_period=quarter")
            
            # Assert
            assert response.status_code == 200
            
            # Verify service was called with time period filter
            mock_service.assert_called_once()
            call_args = mock_service.call_args
            assert call_args[1]["time_period"] == "quarter"

    @pytest.mark.asyncio
    async def test_get_dashboard_with_date_range(self):
        """Test dashboard retrieval with custom date range."""
        # Arrange
        mock_user = create_test_user(user_type="ADMIN")
        mock_session = AsyncMock()
        mock_dashboard_data = create_mock_dashboard_data()

        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock service call
        with patch('Backend.api.dashboard.service.DashboardService.get_dashboard', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_dashboard_data
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.get("/api/dashboard/?start_date=2024-01-01&end_date=2024-01-31")
            
            # Assert
            assert response.status_code == 200
            
            # Verify service was called with date range
            mock_service.assert_called_once()
            call_args = mock_service.call_args
            assert call_args[1]["start_date_override"] == date(2024, 1, 1)
            assert call_args[1]["end_date_override"] == date(2024, 1, 31)

    @pytest.mark.asyncio
    async def test_get_dashboard_with_all_parameters(self):
        """Test dashboard retrieval with all query parameters."""
        # Arrange
        mock_user = create_test_user(user_type="LANDLORD")
        mock_session = AsyncMock()
        mock_dashboard_data = create_mock_dashboard_data()

        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock service call
        with patch('Backend.api.dashboard.service.DashboardService.get_dashboard', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_dashboard_data
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.get(
                "/api/dashboard/"
                "?property_id=456"
                "&time_period=year"
                "&start_date=2024-01-01"
                "&end_date=2024-12-31"
            )
            
            # Assert
            assert response.status_code == 200
            
            # Verify service was called with all parameters
            mock_service.assert_called_once()
            call_args = mock_service.call_args
            assert call_args[1]["property_id"] == 456
            assert call_args[1]["time_period"] == "year"
            assert call_args[1]["start_date_override"] == date(2024, 1, 1)
            assert call_args[1]["end_date_override"] == date(2024, 12, 31)

    @pytest.mark.asyncio
    async def test_get_dashboard_forbidden_tenant_user(self):
        """Test dashboard access forbidden for TENANT user."""
        # Arrange
        mock_user = create_test_user(user_type="TENANT")
        mock_session = AsyncMock()

        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/dashboard/")
        
        # Assert
        assert response.status_code == 403
        data = response.json()
        assert "Not authorized to access dashboard data" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_dashboard_forbidden_other_user_type(self):
        """Test dashboard access forbidden for other user types."""
        # Arrange
        mock_user = create_test_user(user_type="MAINTENANCE_STAFF")
        mock_session = AsyncMock()

        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/dashboard/")
        
        # Assert
        assert response.status_code == 403
        data = response.json()
        assert "Not authorized to access dashboard data" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_dashboard_service_error(self):
        """Test dashboard retrieval when service raises an error."""
        # Arrange
        mock_user = create_test_user(user_type="ADMIN")
        mock_session = AsyncMock()

        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock service to raise an error
        with patch('Backend.api.dashboard.service.DashboardService.get_dashboard', new_callable=AsyncMock) as mock_service:
            mock_service.side_effect = HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve dashboard data"
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.get("/api/dashboard/")
            
            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "Failed to retrieve dashboard data" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_dashboard_invalid_date_format(self):
        """Test dashboard retrieval with invalid date format."""
        # Arrange
        mock_user = create_test_user(user_type="ADMIN")
        mock_session = AsyncMock()

        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/api/dashboard/?start_date=invalid-date")
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_dashboard_empty_response(self):
        """Test dashboard retrieval with empty data."""
        # Arrange
        mock_user = create_test_user(user_type="ADMIN")
        mock_session = AsyncMock()
        
        # Create empty dashboard data
        empty_summary = DashboardSummary(
            total_properties=0,
            total_units=0,
            occupied_units=0,
            vacancy_rate=Decimal("0.0"),
            monthly_revenue=Decimal("0.0"),
            monthly_expenses=Decimal("0.0"),
            outstanding_rent=Decimal("0.0"),
            maintenance_expenses=Decimal("0.0")
        )
        
        empty_occupancy = OccupancyData(
            total_units=0,
            occupied_units=0,
            vacant_units=0,
            occupancy_rate=Decimal("0.0")
        )
        
        empty_revenue = RevenueData(
            months=[],
            revenue=[],
            expenses=[],
            net_income=[]
        )
        
        empty_payments = []
        
        mock_empty_data = (empty_summary, empty_occupancy, empty_revenue, empty_payments)

        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock service call
        with patch('Backend.api.dashboard.service.DashboardService.get_dashboard', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_empty_data
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.get("/api/dashboard/")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            
            assert data["summary"]["total_properties"] == 0
            assert data["occupancy"]["total_units"] == 0
            assert len(data["revenue"]["months"]) == 0
            assert len(data["payments_due"]) == 0