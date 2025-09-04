"""
API tests for smart tax recommendation endpoint.

Tests the GET /api/accounting/tax-preferences/smart endpoint with different
contexts and priority hierarchy scenarios.
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

class TestSmartTaxRecommendation:
    """Test cases for smart tax recommendation endpoint."""

    @pytest.mark.asyncio
    async def test_smart_tax_property_default_success(self):
        """Test smart tax returns property-specific default with highest priority."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        # Mock service to return property default
        mock_smart_response = {
            "tax_name": "HST",
            "tax_rate": Decimal("13.00"),
            "source": "property_default",
            "confidence": 0.95,
            "reasoning": "Using property-specific tax preference: HST 13.0%"
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/smart?property_id=1",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["tax_name"] == "HST"
            assert data["tax_rate"] == "13.00"
            assert data["source"] == "property_default"
            assert data["confidence"] == 0.95
            assert "property-specific" in data["reasoning"]

            # Verify service was called correctly
            mock_service.get_smart_tax_for_context.assert_called_once_with(
                user_id=str(test_user.id),
                property_id=1
            )

    @pytest.mark.asyncio
    async def test_smart_tax_provincial_default_success(self):
        """Test smart tax returns provincial default when no property default."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        # Mock service to return provincial default
        mock_smart_response = {
            "tax_name": "HST",
            "tax_rate": Decimal("13.00"),
            "source": "provincial_default",
            "confidence": 0.85,
            "reasoning": "Using provincial tax rate for property location: HST 13.0%"
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/smart?property_id=2",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["tax_name"] == "HST"
            assert data["source"] == "provincial_default"
            assert data["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_smart_tax_user_default_success(self):
        """Test smart tax returns user default when no property context."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        # Mock service to return user default
        mock_smart_response = {
            "tax_name": "GST",
            "tax_rate": Decimal("5.00"),
            "source": "user_default",
            "confidence": 0.75,
            "reasoning": "Using your personal tax default: GST 5.0%"
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/smart",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["tax_name"] == "GST"
            assert data["source"] == "user_default"
            assert data["confidence"] == 0.75

    @pytest.mark.asyncio
    async def test_smart_tax_historical_usage_success(self):
        """Test smart tax returns historical usage when no defaults available."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        # Mock service to return historical usage
        mock_smart_response = {
            "tax_name": "HST",
            "tax_rate": Decimal("13.00"),
            "source": "historical_usage",
            "confidence": 0.60,
            "reasoning": "Based on your usage history: HST 13.0% (used 15 times)"
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/smart",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["source"] == "historical_usage"
            assert "usage history" in data["reasoning"]

    @pytest.mark.asyncio
    async def test_smart_tax_no_recommendation(self):
        """Test smart tax returns no recommendation for new users."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        # Mock service to return no recommendation
        mock_smart_response = {
            "tax_name": None,
            "tax_rate": None,
            "source": "none",
            "confidence": 0.0,
            "reasoning": "No tax preferences or usage history found. Please select tax manually."
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/smart",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["tax_name"] is None
            assert data["tax_rate"] is None
            assert data["source"] == "none"
            assert data["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_smart_tax_unauthorized(self):
        """Test smart tax endpoint requires authentication."""
        # Arrange
        client = TestClientWithHost(app)

        # Act
        response = client.get("/api/accounting/tax-preferences/smart")

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_smart_tax_tenant_forbidden(self):
        """Test smart tax endpoint forbids tenant users."""
        # Arrange
        test_tenant = create_test_user(user_type=UserType.TENANT)
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_verified_user] = lambda: test_tenant
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        # Act
        response = client.get(
            "/api/accounting/tax-preferences/smart",
            headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_smart_tax_service_error(self):
        """Test smart tax handles service layer errors."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        app.dependency_overrides[get_current_landlord_or_admin] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(side_effect=Exception("Database error"))

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/smart",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 500
            assert "Failed to get tax recommendation" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_smart_tax_property_id_validation(self):
        """Test smart tax handles invalid property_id parameter."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        # Act
        response = client.get(
            "/api/accounting/tax-preferences/smart?property_id=invalid",
            headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == 422  # Validation error