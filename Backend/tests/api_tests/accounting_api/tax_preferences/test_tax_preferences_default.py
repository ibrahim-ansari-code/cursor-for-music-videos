"""
API tests for user default tax preference endpoints.

Tests the GET/POST/DELETE /api/accounting/tax-preferences/default endpoints
for user default tax preference management.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from decimal import Decimal

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.auth.dependencies import get_current_verified_user
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

class TestUserDefaultTaxPreferences:
    """Test cases for user default tax preference endpoints."""

    @pytest.mark.asyncio
    async def test_get_user_default_success(self):
        """Test GET user default tax preference when it exists."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        mock_preference = {
            "tax_name": "HST",
            "tax_rate": Decimal("13.00"),
            "source": "user_default"
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_user_tax_default = AsyncMock(return_value=mock_preference)

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/default",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["tax_name"] == "HST"
            assert data["tax_rate"] == "13.00"
            assert data["source"] == "user_default"

            # Verify service was called correctly
            mock_service.get_user_tax_default.assert_called_once_with(str(test_user.id))

    @pytest.mark.asyncio
    async def test_get_user_default_not_found(self):
        """Test GET user default tax preference when none exists."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_user_tax_default = AsyncMock(return_value=None)

            # Act
            response = client.get(
                "/api/accounting/tax-preferences/default",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            assert response.json() is None

    @pytest.mark.asyncio
    async def test_set_user_default_success(self):
        """Test POST to set user default tax preference."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        request_data = {
            "tax_name": "HST",
            "tax_rate": 13.00
        }

        expected_response = {
            "tax_name": "HST",
            "tax_rate": Decimal("13.00"),
            "source": "user_default"
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.set_user_tax_default = AsyncMock(return_value=expected_response)

            # Act
            response = client.post(
                "/api/accounting/tax-preferences/default",
                json=request_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["tax_name"] == "HST"
            assert data["tax_rate"] == "13.00"
            assert data["source"] == "user_default"

            # Verify service was called correctly
            mock_service.set_user_tax_default.assert_called_once()
            call_args = mock_service.set_user_tax_default.call_args
            assert call_args[1]["user_id"] == str(test_user.id)
            assert call_args[1]["tax_data"].tax_name == "HST"
            assert call_args[1]["tax_data"].tax_rate == Decimal("13.00")

    @pytest.mark.asyncio
    async def test_set_user_default_invalid_data(self):
        """Test POST with invalid tax preference data."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        # Invalid data - missing tax_name
        request_data = {
            "tax_rate": 13.00
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        # Act
        response = client.post(
            "/api/accounting/tax-preferences/default",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == 422  # Validation error


    @pytest.mark.asyncio
    async def test_set_user_default_user_not_found(self):
        """Test POST when user is not found in database."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        request_data = {
            "tax_name": "HST",
            "tax_rate": 13.00
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.set_user_tax_default = AsyncMock(side_effect=ValueError("User not found"))

            # Act
            response = client.post(
                "/api/accounting/tax-preferences/default",
                json=request_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 400
            assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_clear_user_default_success(self):
        """Test DELETE to clear user default tax preference."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.clear_user_tax_default = AsyncMock()

            # Act
            response = client.delete(
                "/api/accounting/tax-preferences/default",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 204

            # Verify service was called to clear defaults
            mock_service.clear_user_tax_default.assert_called_once_with(
                user_id=str(test_user.id)
            )

    @pytest.mark.asyncio
    async def test_user_default_unauthorized(self):
        """Test all endpoints require authentication."""
        client = TestClientWithHost(app)

        # Test GET
        response = client.get("/api/accounting/tax-preferences/default")
        assert response.status_code == 403

        # Test POST
        response = client.post(
            "/api/accounting/tax-preferences/default",
            json={"tax_name": "HST", "tax_rate": 13.0}
        )
        assert response.status_code == 403

        # Test DELETE
        response = client.delete("/api/accounting/tax-preferences/default")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_user_default_tenant_forbidden(self):
        """Test all endpoints forbid tenant users."""
        # Arrange
        test_tenant = create_test_user(user_type=UserType.TENANT)
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_verified_user] = lambda: test_tenant
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        # Test GET
        response = client.get(
            "/api/accounting/tax-preferences/default",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 403

        # Test POST
        response = client.post(
            "/api/accounting/tax-preferences/default",
            json={"tax_name": "HST", "tax_rate": 13.0},
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 403

        # Test DELETE
        response = client.delete(
            "/api/accounting/tax-preferences/default",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 403

