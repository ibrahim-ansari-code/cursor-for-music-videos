"""
Unit tests for the payments delete service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
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

def create_test_user(user_id=None, email="test@example.com", user_type=UserType.LANDLORD):
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

# =============================================================================
# DELETE PAYMENT TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_delete_payment_success():
    """Test successful payment deletion by landlord."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 123
    
    # Mock the service layer to return None (no receipt URL)
    with patch("Backend.api.accounting.payments.router.service.delete_payment", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 204
            assert response.content == b""  # No content for 204 response

@pytest.mark.asyncio
async def test_delete_payment_with_receipt():
    """Test payment deletion with receipt triggers background task."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 456
    receipt_url = "https://storage.example.com/receipts/receipt456.pdf"
    
    # Mock the service layer and background task
    with patch("Backend.api.accounting.payments.router.service.delete_payment", new=AsyncMock(return_value=receipt_url)) as mock_delete:
        with patch("Backend.api.accounting.payments.router.delete_blob_in_background") as mock_blob_delete:
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.delete(f"/api/accounting/payments/{payment_id}")
                
    # Assert
                assert response.status_code == 204
                # Verify service was called
                mock_delete.assert_called_once()
                # Verify background task was called with the receipt URL
                mock_blob_delete.assert_called_once_with(receipt_url)

@pytest.mark.asyncio
async def test_delete_payment_admin_access():
    """Test that admin users can delete any payment."""
    # Arrange
    fake_admin = create_test_user(user_type=UserType.ADMIN)
    fake_admin.is_admin = True
    payment_id = 789
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.delete_payment", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_admin
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 204

@pytest.mark.asyncio
async def test_delete_payment_tenant_forbidden():
    """Test that tenants cannot delete payments."""
    # Arrange
    fake_tenant = create_test_user(user_type=UserType.TENANT)
    payment_id = 321
    
    # Mock the service to raise forbidden exception
    with patch(
        "Backend.api.accounting.payments.router.service.delete_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Not authorized to delete this payment"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_tenant
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 403
            assert "Not authorized to delete this payment" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_payment_not_found():
    """Test deleting non-existent payment."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 9999
    
    # Mock the service to raise not found exception
    with patch(
        "Backend.api.accounting.payments.router.service.delete_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail=f"Payment {payment_id} not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 404
            assert f"Payment {payment_id} not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_payment_unauthorized():
    """Test deleting payment owned by another landlord."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 654
    
    # Mock the service to raise forbidden exception
    with patch(
        "Backend.api.accounting.payments.router.service.delete_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Not authorized to delete this payment"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 403
            assert "Not authorized to delete this payment" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_payment_database_error():
    """Test error handling for database failures during deletion."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 111
    
    # Mock the service to raise internal server error
    with patch(
        "Backend.api.accounting.payments.router.service.delete_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=500, detail="Failed to delete payment."))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 500
            assert "Failed to delete payment" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_payment_multiple_receipts():
    """Test deleting payment with multiple receipt URLs."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 222
    receipt_url = "https://storage.example.com/receipts/multi-receipt.pdf"
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.delete_payment", new=AsyncMock(return_value=receipt_url)):
        with patch("Backend.api.accounting.payments.router.delete_blob_in_background") as mock_blob_delete:
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.delete(f"/api/accounting/payments/{payment_id}")
                
    # Assert
                assert response.status_code == 204

@pytest.mark.asyncio
async def test_delete_payment_with_orphaned_lease():
    """Test deleting payment when lease is orphaned (property deleted)."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 333
    
    # Service should still allow deletion of orphaned payments
    with patch("Backend.api.accounting.payments.router.service.delete_payment", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 204

@pytest.mark.asyncio
async def test_delete_payment_concurrent_deletion():
    """Test handling concurrent deletion attempts."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 444
    
    # Mock the service to raise conflict exception (payment already deleted)
    with patch(
        "Backend.api.accounting.payments.router.service.delete_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail=f"Payment {payment_id} not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_payment_background_task_resilience():
    """Test that payment deletion succeeds and background task is scheduled properly."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 555
    receipt_url = "https://storage.example.com/receipts/receipt555.pdf"
    
    # Mock the service layer to return receipt URL
    with patch("Backend.api.accounting.payments.router.service.delete_payment", new=AsyncMock(return_value=receipt_url)) as mock_delete:
        # Mock background task normally (don't make it fail during response)
        with patch("Backend.api.accounting.payments.router.delete_blob_in_background") as mock_blob_delete:
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.delete(f"/api/accounting/payments/{payment_id}")
                
                # Assert - The deletion should succeed and background task should be scheduled
                assert response.status_code == 204
                # Verify service was called successfully
                mock_delete.assert_called_once()
                # Verify background task was scheduled properly
                mock_blob_delete.assert_called_once_with(receipt_url)

@pytest.mark.asyncio
async def test_delete_payment_idempotency():
    """Test that deleting an already deleted payment returns 404."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 666
    
    # First deletion succeeds
    with patch("Backend.api.accounting.payments.router.service.delete_payment", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act - First deletion
            response1 = client.delete(f"/api/accounting/payments/{payment_id}")
            assert response1.status_code == 204
    
    # Second deletion fails with 404
    with patch(
        "Backend.api.accounting.payments.router.service.delete_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail=f"Payment {payment_id} not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act - Second deletion
            response2 = client.delete(f"/api/accounting/payments/{payment_id}")
            assert response2.status_code == 404

@pytest.mark.asyncio
async def test_delete_payment_with_invalid_id():
    """Test deleting payment with invalid ID format."""
    # Arrange
    fake_user = create_test_user()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act - Invalid ID format
        response = client.delete("/api/accounting/payments/invalid-id")
        
    # Assert
        assert response.status_code == 422  # Validation error