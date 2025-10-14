"""
API tests for tenant emergency contacts endpoints.

These tests cover the atomic emergency contact operations:
- POST /tenants/{tenant_id}/emergency-contacts (create)
- PUT /tenants/{tenant_id}/emergency-contacts/{contact_id} (update)
- DELETE /tenants/{tenant_id}/emergency-contacts/{contact_id} (delete)

Tests verify:
- Happy path scenarios
- Atomic primary contact logic
- Permission checks
- Validation error handling
- Business rule enforcement (max 5 contacts)
"""

import pytest
from fastapi import status, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.tenants.schemas import EmergencyContactResponse
from Backend.models.tenant import TenantStatus, Tenant
from Backend.models.enums import TenantType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()


class TestClientWithHost(TestClient):
    """Custom TestClient to set the host header."""
    def request(self, method: str, url, **kwargs):
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
        updated_at=now,
        is_email_verified=True
    )


# =============================================================================
# CREATE EMERGENCY CONTACT TESTS
# =============================================================================

def test_create_emergency_contact_success():
    """Test successfully creating an emergency contact - covers router.py:405,410"""
    # Arrange
    tenant_id = 1
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")

    contact_data = {
        "name": "John Emergency",
        "relationship": "Brother",
        "phone": "555-1234567",
        "email": "john.emergency@example.com",
        "is_primary": True,
        "notes": "Call after 6pm"
    }

    mock_contact_response = EmergencyContactResponse(
        id=str(uuid4()),
        name="John Emergency",
        relationship="Brother",
        phone="555-1234567",
        email="john.emergency@example.com",
        is_primary=True,
        notes="Call after 6pm"
    )

    with patch("Backend.api.tenants.router.add_emergency_contact", new_callable=AsyncMock) as mock_add:
        mock_add.return_value = mock_contact_response

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(f"/api/tenants/{tenant_id}/emergency-contacts", json=contact_data)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "John Emergency"
        assert data["relationship"] == "Brother"
        assert data["phone"] == "555-1234567"
        assert data["email"] == "john.emergency@example.com"
        assert data["is_primary"] is True
        assert data["notes"] == "Call after 6pm"
        assert "id" in data

        # Verify service was called with correct parameters
        mock_add.assert_awaited_once_with(tenant_id, unittest.mock.ANY, unittest.mock.ANY, mock_user)


def test_create_emergency_contact_as_primary():
    """Test creating emergency contact with primary flag."""
    # Arrange
    tenant_id = 1
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)

    contact_data = {
        "name": "Primary Contact",
        "relationship": "Spouse",
        "phone": "555-9999999",
        "is_primary": True
    }

    mock_contact_response = EmergencyContactResponse(
        id=str(uuid4()),
        name="Primary Contact",
        relationship="Spouse",
        phone="555-9999999",
        email=None,
        is_primary=True,
        notes=None
    )

    with patch("Backend.api.tenants.router.add_emergency_contact", new_callable=AsyncMock) as mock_add:
        mock_add.return_value = mock_contact_response

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(f"/api/tenants/{tenant_id}/emergency-contacts", json=contact_data)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["is_primary"] is True


def test_create_emergency_contact_max_limit_reached():
    """Test creating emergency contact when max 5 limit is reached."""
    # Arrange
    tenant_id = 1
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)

    contact_data = {
        "name": "Sixth Contact",
        "relationship": "Friend",
        "phone": "555-0000000"
    }

    with patch("Backend.api.tenants.router.add_emergency_contact", new_callable=AsyncMock) as mock_add:
        mock_add.side_effect = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 emergency contacts allowed per tenant"
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(f"/api/tenants/{tenant_id}/emergency-contacts", json=contact_data)

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Maximum 5 emergency contacts" in response.json()["detail"]


def test_create_emergency_contact_tenant_not_found():
    """Test creating emergency contact for non-existent tenant."""
    # Arrange
    tenant_id = 999
    mock_user = create_test_user()

    contact_data = {
        "name": "Test Contact",
        "relationship": "Friend",
        "phone": "555-1111111"
    }

    with patch("Backend.api.tenants.router.add_emergency_contact", new_callable=AsyncMock) as mock_add:
        mock_add.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(f"/api/tenants/{tenant_id}/emergency-contacts", json=contact_data)

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Tenant not found" in response.json()["detail"]


def test_create_emergency_contact_forbidden():
    """Test creating emergency contact without permission."""
    # Arrange
    tenant_id = 1
    mock_user = create_test_user(email="unauthorized@example.com")

    contact_data = {
        "name": "Test Contact",
        "relationship": "Friend",
        "phone": "555-1111111"
    }

    with patch("Backend.api.tenants.router.add_emergency_contact", new_callable=AsyncMock) as mock_add:
        mock_add.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this tenant"
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(f"/api/tenants/{tenant_id}/emergency-contacts", json=contact_data)

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["detail"]


def test_create_emergency_contact_invalid_data():
    """Test creating emergency contact with invalid data."""
    # Arrange
    tenant_id = 1
    mock_user = create_test_user()

    contact_data = {
        "name": "",  # Empty name should fail
        "relationship": "Friend",
        "phone": "555-1111111"
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        # Act
        response = client.post(f"/api/tenants/{tenant_id}/emergency-contacts", json=contact_data)

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_emergency_contact_missing_required_fields():
    """Test creating emergency contact with missing required fields."""
    # Arrange
    tenant_id = 1
    mock_user = create_test_user()

    contact_data = {
        "name": "John Doe"
        # Missing phone and relationship
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        # Act
        response = client.post(f"/api/tenants/{tenant_id}/emergency-contacts", json=contact_data)

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# UPDATE EMERGENCY CONTACT TESTS
# =============================================================================

def test_update_emergency_contact_success():
    """Test successfully updating an emergency contact - covers router.py:445,451"""
    # Arrange
    tenant_id = 1
    contact_id = str(uuid4())
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)

    update_data = {
        "name": "Updated Name",
        "phone": "555-9876543"
    }

    mock_updated_contact = EmergencyContactResponse(
        id=contact_id,
        name="Updated Name",
        relationship="Brother",
        phone="555-9876543",
        email="john@example.com",
        is_primary=False,
        notes=None
    )

    with patch("Backend.api.tenants.router.update_emergency_contact", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_updated_contact

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.put(
                f"/api/tenants/{tenant_id}/emergency-contacts/{contact_id}",
                json=update_data
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == contact_id
        assert data["name"] == "Updated Name"
        assert data["phone"] == "555-9876543"

        # Verify service was called
        mock_update.assert_awaited_once()


def test_update_emergency_contact_set_primary():
    """Test updating emergency contact to set as primary."""
    # Arrange
    tenant_id = 1
    contact_id = str(uuid4())
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)

    update_data = {
        "is_primary": True
    }

    mock_updated_contact = EmergencyContactResponse(
        id=contact_id,
        name="John Emergency",
        relationship="Brother",
        phone="555-1234567",
        email=None,
        is_primary=True,
        notes=None
    )

    with patch("Backend.api.tenants.router.update_emergency_contact", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_updated_contact

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.put(
                f"/api/tenants/{tenant_id}/emergency-contacts/{contact_id}",
                json=update_data
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_primary"] is True


def test_update_emergency_contact_partial_update():
    """Test partial update of emergency contact (only some fields)."""
    # Arrange
    tenant_id = 1
    contact_id = str(uuid4())
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)

    update_data = {
        "notes": "Updated notes only"
    }

    mock_updated_contact = EmergencyContactResponse(
        id=contact_id,
        name="John Emergency",  # Unchanged
        relationship="Brother",  # Unchanged
        phone="555-1234567",  # Unchanged
        email=None,
        is_primary=False,
        notes="Updated notes only"  # Updated
    )

    with patch("Backend.api.tenants.router.update_emergency_contact", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_updated_contact

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.put(
                f"/api/tenants/{tenant_id}/emergency-contacts/{contact_id}",
                json=update_data
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["notes"] == "Updated notes only"


def test_update_emergency_contact_not_found():
    """Test updating non-existent emergency contact."""
    # Arrange
    tenant_id = 1
    contact_id = str(uuid4())
    mock_user = create_test_user()

    update_data = {
        "name": "Updated Name"
    }

    with patch("Backend.api.tenants.router.update_emergency_contact", new_callable=AsyncMock) as mock_update:
        mock_update.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Emergency contact with ID {contact_id} not found"
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.put(
                f"/api/tenants/{tenant_id}/emergency-contacts/{contact_id}",
                json=update_data
            )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]


def test_update_emergency_contact_forbidden():
    """Test updating emergency contact without permission."""
    # Arrange
    tenant_id = 1
    contact_id = str(uuid4())
    mock_user = create_test_user(email="unauthorized@example.com")

    update_data = {
        "name": "Updated Name"
    }

    with patch("Backend.api.tenants.router.update_emergency_contact", new_callable=AsyncMock) as mock_update:
        mock_update.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this tenant"
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.put(
                f"/api/tenants/{tenant_id}/emergency-contacts/{contact_id}",
                json=update_data
            )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["detail"]


def test_update_emergency_contact_invalid_data():
    """Test updating emergency contact with invalid data."""
    # Arrange
    tenant_id = 1
    contact_id = str(uuid4())
    mock_user = create_test_user()

    update_data = {
        "phone": "123"  # Too short
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        # Act
        response = client.put(
            f"/api/tenants/{tenant_id}/emergency-contacts/{contact_id}",
            json=update_data
        )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# DELETE EMERGENCY CONTACT TESTS
# =============================================================================

def test_delete_emergency_contact_success():
    """Test successfully deleting an emergency contact - covers router.py:480,486-487"""
    # Arrange
    tenant_id = 1
    contact_id = str(uuid4())
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)

    with patch("Backend.api.tenants.router.delete_emergency_contact", new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = None  # Successful deletion returns None

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}/emergency-contacts/{contact_id}")

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify service was called
        mock_delete.assert_awaited_once_with(tenant_id, contact_id, unittest.mock.ANY, mock_user)


def test_delete_emergency_contact_not_found():
    """Test deleting non-existent emergency contact."""
    # Arrange
    tenant_id = 1
    contact_id = str(uuid4())
    mock_user = create_test_user()

    with patch("Backend.api.tenants.router.delete_emergency_contact", new_callable=AsyncMock) as mock_delete:
        mock_delete.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Emergency contact with ID {contact_id} not found"
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}/emergency-contacts/{contact_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]


def test_delete_emergency_contact_forbidden():
    """Test deleting emergency contact without permission."""
    # Arrange
    tenant_id = 1
    contact_id = str(uuid4())
    mock_user = create_test_user(email="unauthorized@example.com")

    with patch("Backend.api.tenants.router.delete_emergency_contact", new_callable=AsyncMock) as mock_delete:
        mock_delete.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this tenant"
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}/emergency-contacts/{contact_id}")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["detail"]


def test_delete_emergency_contact_tenant_not_found():
    """Test deleting emergency contact when tenant doesn't exist."""
    # Arrange
    tenant_id = 999
    contact_id = str(uuid4())
    mock_user = create_test_user()

    with patch("Backend.api.tenants.router.delete_emergency_contact", new_callable=AsyncMock) as mock_delete:
        mock_delete.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/tenants/{tenant_id}/emergency-contacts/{contact_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Tenant not found" in response.json()["detail"]


# =============================================================================
# EDGE CASES AND INTEGRATION SCENARIOS
# =============================================================================

def test_create_emergency_contact_without_optional_fields():
    """Test creating emergency contact with only required fields."""
    # Arrange
    tenant_id = 1
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)

    contact_data = {
        "name": "Minimal Contact",
        "relationship": "Friend",
        "phone": "555-1111111"
        # No email, no notes, is_primary defaults to False
    }

    mock_contact_response = EmergencyContactResponse(
        id=str(uuid4()),
        name="Minimal Contact",
        relationship="Friend",
        phone="555-1111111",
        email=None,
        is_primary=False,
        notes=None
    )

    with patch("Backend.api.tenants.router.add_emergency_contact", new_callable=AsyncMock) as mock_add:
        mock_add.return_value = mock_contact_response

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(f"/api/tenants/{tenant_id}/emergency-contacts", json=contact_data)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Minimal Contact"
        assert data["email"] is None
        assert data["notes"] is None
        assert data["is_primary"] is False


def test_update_emergency_contact_clear_optional_field():
    """Test updating emergency contact to clear an optional field."""
    # Arrange
    tenant_id = 1
    contact_id = str(uuid4())
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)

    update_data = {
        "email": None,  # Clear the email
        "notes": None   # Clear the notes
    }

    mock_updated_contact = EmergencyContactResponse(
        id=contact_id,
        name="John Emergency",
        relationship="Brother",
        phone="555-1234567",
        email=None,  # Cleared
        is_primary=False,
        notes=None   # Cleared
    )

    with patch("Backend.api.tenants.router.update_emergency_contact", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_updated_contact

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.put(
                f"/api/tenants/{tenant_id}/emergency-contacts/{contact_id}",
                json=update_data
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] is None
        assert data["notes"] is None


# Add missing import for unittest.mock
import unittest.mock
