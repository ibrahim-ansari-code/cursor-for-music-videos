"""
API tests for property image secure URL generation (SAS tokens).
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


def test_get_image_secure_url_success(mocker):
    """Test successful generation of secure property image URL."""
    fake_user = create_test_user()
    image_url = "https://briklicorestorage.blob.core.windows.net/property-images/property1.jpg"
    
    mock_secure_url_data = {
        "secure_url": f"{image_url}?sv=2021&sig=def456",
        "expires_at": "2024-10-09T22:00:00Z",
        "expires_in_seconds": 3600
    }
    mocker.patch(
        "Backend.api.properties.image_router.PropertyImageService.generate_image_secure_url",
        new=AsyncMock(return_value=mock_secure_url_data)
    )
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    with TestClientWithHost(app) as client:
        encoded_url = quote(image_url, safe='')
        response = client.post(f"/api/properties/images/secure-url?image_url={encoded_url}")
    
    assert response.status_code == 200
    data = response.json()
    assert "secure_url" in data
    assert "?sv=" in data["secure_url"]


def test_get_image_secure_url_not_found(mocker):
    """Test secure URL generation when image doesn't exist."""
    fake_user = create_test_user()
    image_url = "https://briklicorestorage.blob.core.windows.net/property-images/deleted.jpg"
    
    mocker.patch(
        "Backend.api.properties.image_router.PropertyImageService.generate_image_secure_url",
        new=AsyncMock(side_effect=ValueError("Document file not found in storage"))
    )
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    with TestClientWithHost(app) as client:
        encoded_url = quote(image_url, safe='')
        response = client.post(f"/api/properties/images/secure-url?image_url={encoded_url}")
    
    assert response.status_code == 404


def test_get_image_secure_url_unauthorized():
    """Test secure URL generation without authentication."""
    image_url = "https://briklicorestorage.blob.core.windows.net/property-images/image.jpg"
    
    with TestClientWithHost(app) as client:
        encoded_url = quote(image_url, safe='')
        response = client.post(f"/api/properties/images/secure-url?image_url={encoded_url}")
    
    assert response.status_code == 403

