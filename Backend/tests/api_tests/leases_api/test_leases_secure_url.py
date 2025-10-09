"""
API tests for lease document secure URL generation (SAS tokens).
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.app import app
from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.user import User
from Backend.models.lease import LeaseDocument

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


def test_get_secure_url_success(mocker):
    """Test successful generation of secure document URL with SAS token."""
    # Arrange
    lease_id = 123
    document_id = 456
    fake_user = create_test_user()
    
    # Create mock document
    mock_document = MagicMock(spec=LeaseDocument)
    mock_document.id = document_id
    mock_document.lease_id = lease_id
    mock_document.file_path = "https://briklicorestorage.blob.core.windows.net/lease-uploads/user_123/doc.pdf"
    mock_document.name = "Test Lease.pdf"
    mock_document.document_type = "contract"
    
    # Mock get_lease_document_by_id to return the document
    mocker.patch(
        "Backend.api.leases.router.get_lease_document_by_id",
        new=AsyncMock(return_value=mock_document)
    )
    
    # Mock generate_secure_document_url
    mock_secure_url_data = {
        "secure_url": "https://briklicorestorage.blob.core.windows.net/lease-uploads/user_123/doc.pdf?sv=2021&sig=abc123",
        "expires_at": "2024-10-09T20:30:00Z",
        "expires_in_seconds": 3600
    }
    mocker.patch(
        "Backend.api.leases.router.generate_secure_document_url",
        new=AsyncMock(return_value=mock_secure_url_data)
    )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    # Act
    with TestClientWithHost(app) as client:
        response = client.get(f"/api/leases/{lease_id}/documents/{document_id}/secure-url")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "secure_url" in data
    assert "expires_at" in data
    assert "expires_in_seconds" in data
    assert data["expires_in_seconds"] == 3600
    assert "?sv=" in data["secure_url"]  # Has SAS token
    assert "sig=" in data["secure_url"]  # Has signature


def test_get_secure_url_document_not_found(mocker):
    """Test secure URL generation when document doesn't exist."""
    # Arrange
    lease_id = 123
    document_id = 999
    fake_user = create_test_user()
    
    # Mock get_lease_document_by_id to raise 404
    mocker.patch(
        "Backend.api.leases.router.get_lease_document_by_id",
        new=AsyncMock(side_effect=Exception("Document not found"))
    )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    # Act
    with TestClientWithHost(app) as client:
        response = client.get(f"/api/leases/{lease_id}/documents/{document_id}/secure-url")
    
    # Assert
    assert response.status_code == 500


def test_get_secure_url_no_permission(mocker):
    """Test secure URL generation without lease permission."""
    # Arrange
    lease_id = 123
    document_id = 456
    fake_user = create_test_user()
    
    # Mock get_lease_document_by_id to raise permission error
    from fastapi import HTTPException
    mocker.patch(
        "Backend.api.leases.router.get_lease_document_by_id",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Permission denied"))
    )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    # Act
    with TestClientWithHost(app) as client:
        response = client.get(f"/api/leases/{lease_id}/documents/{document_id}/secure-url")
    
    # Assert
    assert response.status_code == 403
    assert "denied" in response.json()["detail"].lower()


def test_get_secure_url_configuration_error(mocker):
    """Test secure URL generation when Azure config is missing."""
    # Arrange
    lease_id = 123
    document_id = 456
    fake_user = create_test_user()
    
    # Create mock document
    mock_document = MagicMock(spec=LeaseDocument)
    mock_document.id = document_id
    mock_document.lease_id = lease_id
    mock_document.file_path = "https://briklicorestorage.blob.core.windows.net/lease-uploads/doc.pdf"
    
    mocker.patch(
        "Backend.api.leases.router.get_lease_document_by_id",
        new=AsyncMock(return_value=mock_document)
    )
    
    # Mock SAS generation to raise ValueError (config error)
    mocker.patch(
        "Backend.api.leases.router.generate_secure_document_url",
        new=AsyncMock(side_effect=ValueError("Azure account key not configured"))
    )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    # Act
    with TestClientWithHost(app) as client:
        response = client.get(f"/api/leases/{lease_id}/documents/{document_id}/secure-url")
    
    # Assert
    assert response.status_code == 500
    assert "configuration error" in response.json()["detail"].lower()


def test_get_secure_url_invalid_lease_id(mocker):
    """Test secure URL generation with invalid lease ID."""
    # Arrange
    fake_user = create_test_user()
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    # Act
    with TestClientWithHost(app) as client:
        response = client.get("/api/leases/invalid/documents/123/secure-url")
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_get_secure_url_requires_authentication():
    """Test secure URL generation requires authentication."""
    # Act - No auth override (no token)
    with TestClientWithHost(app) as client:
        response = client.get("/api/leases/123/documents/456/secure-url")
    
    # Assert
    assert response.status_code in [401, 403]  # Unauthorized or Forbidden

