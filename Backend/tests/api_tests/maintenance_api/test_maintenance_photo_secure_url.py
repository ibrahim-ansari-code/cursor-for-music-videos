"""
API tests for maintenance photo secure URL generation (SAS tokens).
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime, timezone
from urllib.parse import quote

from Backend.api.app import app
from Backend.api.auth import get_current_user
from Backend.models.user import User

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()


class TestClientWithHost(TestClient):
    def request(self, method: str, url, **kwargs):
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def create_test_user(user_id=None, email="test@example.com", user_type="LANDLORD"):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=False,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )


def test_get_photo_secure_url_success(mocker):
    """Test successful generation of secure photo URL with SAS token."""
    fake_user = create_test_user()
    photo_url = "https://briklicorestorage.blob.core.windows.net/maintenance-photos/user_123/photo.jpg"
    
    # Mock generate_photo_secure_url service method
    mock_secure_url_data = {
        "secure_url": f"{photo_url}?sv=2021&sig=abc123",
        "expires_at": "2024-10-09T20:30:00Z",
        "expires_in_seconds": 3600
    }
    mocker.patch(
        "Backend.api.maintenance.router.MaintenanceService.generate_photo_secure_url",
        new=AsyncMock(return_value=mock_secure_url_data)
    )
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    with TestClientWithHost(app) as client:
        encoded_url = quote(photo_url, safe='')
        response = client.post(f"/api/maintenance/photos/secure-url?photo_url={encoded_url}")
    
    assert response.status_code == 200
    data = response.json()
    assert "secure_url" in data
    assert "?sv=" in data["secure_url"]
    assert data["expires_in_seconds"] == 3600


def test_get_photo_secure_url_not_found(mocker):
    """Test secure URL generation when photo doesn't exist in Azure."""
    fake_user = create_test_user()
    photo_url = "https://briklicorestorage.blob.core.windows.net/maintenance-photos/deleted.jpg"
    
    # Mock to raise ValueError for missing blob
    mocker.patch(
        "Backend.api.maintenance.router.MaintenanceService.generate_photo_secure_url",
        new=AsyncMock(side_effect=ValueError("Document file not found in storage"))
    )
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    with TestClientWithHost(app) as client:
        encoded_url = quote(photo_url, safe='')
        response = client.post(f"/api/maintenance/photos/secure-url?photo_url={encoded_url}")
    
    assert response.status_code == 404
    assert "no longer exists" in response.json()["detail"].lower()


def test_get_photo_secure_url_invalid_url(mocker):
    """Test secure URL generation with invalid Azure URL."""
    fake_user = create_test_user()
    photo_url = "https://example.com/not-azure.jpg"
    
    # Mock to raise ValueError for invalid URL
    mocker.patch(
        "Backend.api.maintenance.router.MaintenanceService.generate_photo_secure_url",
        new=AsyncMock(side_effect=ValueError("Not an Azure Blob Storage URL"))
    )
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    with TestClientWithHost(app) as client:
        encoded_url = quote(photo_url, safe='')
        response = client.post(f"/api/maintenance/photos/secure-url?photo_url={encoded_url}")
    
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


def test_get_photo_secure_url_unauthorized():
    """Test secure URL generation without authentication."""
    photo_url = "https://briklicorestorage.blob.core.windows.net/maintenance-photos/photo.jpg"
    
    # No user override - should fail auth
    with TestClientWithHost(app) as client:
        encoded_url = quote(photo_url, safe='')
        response = client.post(f"/api/maintenance/photos/secure-url?photo_url={encoded_url}")
    
    assert response.status_code == 403


def test_get_photo_secure_url_server_error(mocker):
    """Test secure URL generation with unexpected server error."""
    fake_user = create_test_user()
    photo_url = "https://briklicorestorage.blob.core.windows.net/maintenance-photos/photo.jpg"
    
    # Mock to raise unexpected exception
    mocker.patch(
        "Backend.api.maintenance.router.MaintenanceService.generate_photo_secure_url",
        new=AsyncMock(side_effect=Exception("Unexpected error"))
    )
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    with TestClientWithHost(app) as client:
        encoded_url = quote(photo_url, safe='')
        response = client.post(f"/api/maintenance/photos/secure-url?photo_url={encoded_url}")
    
    assert response.status_code == 500

