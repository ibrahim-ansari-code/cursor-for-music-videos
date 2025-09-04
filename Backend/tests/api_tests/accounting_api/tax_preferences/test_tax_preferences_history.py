"""
API tests for historical tax usage endpoint.

Tests the GET /api/accounting/tax-preferences/history endpoint
for retrieving user's historical tax usage patterns.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from decimal import Decimal

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.auth.dependencies import get_current_verified_user, get_current_landlord_or_admin
from Backend.database import get_session

# Mark all tests in this module as API tests
pytestmark = pytest.mark.api

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

def create_test_user(user_id=None, email="test@example.com", user_type=UserType.LANDLORD):
    """Helper function to create a properly initialized test user."""
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_verified=True
    )

class TestHistoricalTaxUsage:
    """Test cases for historical tax usage endpoint."""

    @pytest.mark.asyncio
    async def test_get_historical_usage_success(self):
        """Test GET historical tax usage with data."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        mock_usage_data = [
            {
                "tax_name": "HST",
                "tax_rate": 13.00,
                "usage_count": 15,
                "last_used": "2024-08-15T10:30:00",
                "percentage": 60.0
            },
            {
                "tax_name": "GST",
                "tax_rate": 5.00,
                "usage_count": 8,
                "last_used": "2024-08-10T14:20:00",
                "percentage": 32.0
            },
            {
                "tax_name": "GST+PST",
                "tax_rate": 12.00,
                "usage_count": 2,
                "last_used": "2024-07-25T09:15:00",
                "percentage": 8.0
            }
        ]

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_historical_tax_usage = AsyncMock(return_value=mock_usage_data)

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/history",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            
            # Check first item (most used)
            first_item = data[0]
            assert first_item["tax_name"] == "HST"
            assert first_item["tax_rate"] == "13.0"
            assert first_item["usage_count"] == 15
            assert first_item["percentage"] == 60.0
            assert first_item["last_used"] == "2024-08-15T10:30:00"

            # Verify service was called correctly
            mock_service.get_historical_tax_usage.assert_called_once_with(
                user_id=str(test_user.id),
                limit=10  # Default limit
            )

    @pytest.mark.asyncio
    async def test_get_historical_usage_empty(self):
        """Test GET historical tax usage with no data."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_historical_tax_usage = AsyncMock(return_value=[])

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/history",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data == []

    @pytest.mark.asyncio
    async def test_get_historical_usage_with_limit(self):
        """Test GET historical tax usage with custom limit parameter."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        mock_usage_data = [
            {
                "tax_name": "HST",
                "tax_rate": Decimal("13.00"),
                "usage_count": 10,
                "last_used": "2024-08-15T10:30:00",
                "percentage": 100.0
            }
        ]

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_historical_tax_usage = AsyncMock(return_value=mock_usage_data)

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/history?limit=5",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1

            # Verify service was called with custom limit
            mock_service.get_historical_tax_usage.assert_called_once_with(
                user_id=str(test_user.id),
                limit=5
            )


    @pytest.mark.asyncio
    async def test_historical_usage_unauthorized(self):
        """Test historical usage endpoint requires authentication."""
        client = TestClientWithHost(app)

        # Act
        response = client.get("/api/accounting/tax-preferences/history")

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_historical_usage_tenant_forbidden(self):
        """Test historical usage endpoint forbids tenant users."""
        # Arrange
        test_tenant = create_test_user(user_type=UserType.TENANT)
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_verified_user] = lambda: test_tenant
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        # Act
        response = client.get(
            "/api/accounting/tax-preferences/history",
            headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_historical_usage_admin_access(self):
        """Test admin users can access historical usage endpoint."""
        # Arrange
        test_admin = create_test_user(user_type=UserType.ADMIN)
        mock_session = AsyncMock()

        mock_usage_data = [
            {
                "tax_name": "HST",
                "tax_rate": Decimal("13.00"),
                "usage_count": 5,
                "last_used": "2024-08-15T10:30:00",
                "percentage": 100.0
            }
        ]

        app.dependency_overrides[get_current_verified_user] = lambda: test_admin
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_historical_tax_usage = AsyncMock(return_value=mock_usage_data)

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/history",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1

    @pytest.mark.asyncio
    async def test_historical_usage_service_error(self):
        """Test historical usage endpoint handles service layer errors."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        app.dependency_overrides[get_current_landlord_or_admin] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_historical_tax_usage = AsyncMock(side_effect=Exception("Database error"))

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/history",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 500
            assert "Failed to get historical tax usage" in response.json()["detail"]

