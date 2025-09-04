"""
API tests for property default tax preference endpoints.

Tests the GET/POST/DELETE /api/accounting/tax-preferences/property/{id} endpoints
for property-specific tax preference management.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from decimal import Decimal

from fastapi import HTTPException, status

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

class TestPropertyTaxPreferences:
    """Test cases for property tax preference endpoints."""

    @pytest.mark.asyncio
    async def test_get_property_default_success(self):
        """Test GET property default tax preference when it exists."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        property_id = 1

        mock_preference = {
            "tax_name": "GST+PST",
            "tax_rate": Decimal("12.00"),
            "source": "property_default"
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_property_tax_default = AsyncMock(return_value=mock_preference)

            # Act
            response = client.get(
                f"/api/accounting/tax-preferences/property/{property_id}",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["tax_name"] == "GST+PST"
            assert data["tax_rate"] == "12.00"
            assert data["source"] == "property_default"

            # Verify service was called correctly
            mock_service.get_property_tax_default.assert_called_once_with(
                user_id=str(test_user.id),
                property_id=property_id
            )

    @pytest.mark.asyncio
    async def test_get_property_default_not_found(self):
        """Test GET property default tax preference when none exists."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        property_id = 1

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_property_tax_default = AsyncMock(return_value=None)

            # Act
            response = client.get(
                f"/api/accounting/tax-preferences/property/{property_id}",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            assert response.json() is None

    @pytest.mark.asyncio
    async def test_set_property_default_success(self):
        """Test POST to set property default tax preference."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        property_id = 1

        request_data = {
            "tax_name": "GST+PST",
            "tax_rate": 12.00
        }

        expected_response = {
            "tax_name": "GST+PST",
            "tax_rate": Decimal("12.00"),
            "source": "property_default"
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.set_property_tax_default = AsyncMock(return_value=expected_response)

            # Act
            response = client.post(
                f"/api/accounting/tax-preferences/property/{property_id}",
                json=request_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["tax_name"] == "GST+PST"
            assert data["tax_rate"] == "12.00"
            assert data["source"] == "property_default"

            # Verify service was called correctly
            mock_service.set_property_tax_default.assert_called_once()
            call_args = mock_service.set_property_tax_default.call_args
            assert call_args[1]["user_id"] == str(test_user.id)
            assert call_args[1]["property_id"] == property_id
            assert call_args[1]["tax_data"].tax_name == "GST+PST"
            assert call_args[1]["tax_data"].tax_rate == Decimal("12.00")

    @pytest.mark.asyncio
    async def test_set_property_default_property_not_found(self):
        """Test POST when property is not found or not owned by user."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        property_id = 999

        request_data = {
            "tax_name": "HST",
            "tax_rate": 13.00
        }

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.set_property_tax_default = AsyncMock(
                side_effect=ValueError("Property not found or access denied")
            )

            # Act
            response = client.post(
                f"/api/accounting/tax-preferences/property/{property_id}",
                json=request_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 400
            assert "Property not found or access denied" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_clear_property_default_success(self):
        """Test DELETE to clear property default tax preference."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        property_id = 1

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.clear_property_tax_default = AsyncMock()

            # Act
            response = client.delete(
                f"/api/accounting/tax-preferences/property/{property_id}",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 204

            # Verify service was called to clear defaults
            mock_service.clear_property_tax_default.assert_called_once_with(
                user_id=str(test_user.id),
                property_id=property_id
            )

    @pytest.mark.asyncio
    async def test_property_endpoints_invalid_property_id(self):
        """Test property endpoints with invalid property ID."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        # Test with non-integer property_id
        response = client.get(
            "/api/accounting/tax-preferences/property/invalid",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 422

        response = client.post(
            "/api/accounting/tax-preferences/property/invalid",
            json={"tax_name": "HST", "tax_rate": 13.0},
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 422

        response = client.delete(
            "/api/accounting/tax-preferences/property/invalid",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_property_endpoints_unauthorized(self):
        """Test all property endpoints require authentication."""
        client = TestClientWithHost(app)
        property_id = 1

        # Test GET
        response = client.get(f"/api/accounting/tax-preferences/property/{property_id}")
        assert response.status_code == 403

        # Test POST
        response = client.post(
            f"/api/accounting/tax-preferences/property/{property_id}",
            json={"tax_name": "HST", "tax_rate": 13.0}
        )
        assert response.status_code == 403

        # Test DELETE
        response = client.delete(f"/api/accounting/tax-preferences/property/{property_id}")
        assert response.status_code == 403


    @pytest.mark.asyncio
    async def test_clear_property_default_value_error(self):
        """Test DELETE with ValueError to hit line 232 coverage."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        property_id = 1

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.clear_property_tax_default = AsyncMock(side_effect=ValueError("Property access denied"))

            # Act - This will trigger line 232 in router.py
            response = client.delete(
                f"/api/accounting/tax-preferences/property/{property_id}",
                headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 400
            assert "Property access denied" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_property_default_validation_errors(self):
        """Test POST with various validation errors."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        property_id = 1

        app.dependency_overrides[get_current_verified_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session

        client = TestClientWithHost(app)

        with patch('Backend.api.accounting.tax_preferences.router.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            # Mock service to handle the empty tax_name case that passes validation
            mock_service.set_property_tax_default = AsyncMock(
                side_effect=ValueError("Invalid tax name")
            )

            # Test missing tax_name
            response = client.post(
                f"/api/accounting/tax-preferences/property/{property_id}",
                json={"tax_rate": 13.0},
                headers={"Authorization": "Bearer test-token"}
            )
            assert response.status_code == 422

            # Test negative tax rate
            response = client.post(
                f"/api/accounting/tax-preferences/property/{property_id}",
                json={"tax_name": "HST", "tax_rate": -5.0},
                headers={"Authorization": "Bearer test-token"}
            )
            assert response.status_code == 422

            # Test tax rate over 100%
            response = client.post(
                f"/api/accounting/tax-preferences/property/{property_id}",
                json={"tax_name": "HST", "tax_rate": 150.0},
                headers={"Authorization": "Bearer test-token"}
            )
            assert response.status_code == 422

            # Test empty tax_name (rejected by Pydantic validation)
            response = client.post(
                f"/api/accounting/tax-preferences/property/{property_id}",
                json={"tax_name": "", "tax_rate": 13.0},
                headers={"Authorization": "Bearer test-token"}
            )
            assert response.status_code == 422  # Pydantic validation error