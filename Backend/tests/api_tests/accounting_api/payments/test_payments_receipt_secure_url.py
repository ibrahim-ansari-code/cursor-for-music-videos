"""
API tests for payment receipt secure URL generation (SAS tokens).
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


def test_get_receipt_secure_url_success(mocker):
    """Test successful generation of secure payment receipt URL."""
    fake_user = create_test_user()
    receipt_url = "https://briklicorestorage.blob.core.windows.net/payment-receipts/receipt.pdf"
    
    mock_secure_url_data = {
        "secure_url": f"{receipt_url}?sv=2021&sig=xyz789",
        "expires_at": "2024-10-09T21:00:00Z",
        "expires_in_seconds": 3600
    }
    mocker.patch(
        "Backend.api.accounting.payments.router.service.generate_receipt_secure_url",
        new=AsyncMock(return_value=mock_secure_url_data)
    )
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    with TestClientWithHost(app) as client:
        encoded_url = quote(receipt_url, safe='')
        response = client.post(f"/api/accounting/payments/receipts/secure-url?receipt_url={encoded_url}")
    
    assert response.status_code == 200
    data = response.json()
    assert "secure_url" in data
    assert "?sv=" in data["secure_url"]


def test_get_receipt_secure_url_not_found(mocker):
    """Test secure URL generation when payment receipt doesn't exist."""
    fake_user = create_test_user()
    receipt_url = "https://briklicorestorage.blob.core.windows.net/payment-receipts/missing.pdf"
    
    mocker.patch(
        "Backend.api.accounting.payments.router.service.generate_receipt_secure_url",
        new=AsyncMock(side_effect=ValueError("Document file not found in storage"))
    )
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    with TestClientWithHost(app) as client:
        encoded_url = quote(receipt_url, safe='')
        response = client.post(f"/api/accounting/payments/receipts/secure-url?receipt_url={encoded_url}")
    
    assert response.status_code == 404


def test_get_receipt_secure_url_unauthorized():
    """Test secure URL generation without authentication."""
    receipt_url = "https://briklicorestorage.blob.core.windows.net/payment-receipts/receipt.pdf"
    
    with TestClientWithHost(app) as client:
        encoded_url = quote(receipt_url, safe='')
        response = client.post(f"/api/accounting/payments/receipts/secure-url?receipt_url={encoded_url}")
    
    assert response.status_code == 403

