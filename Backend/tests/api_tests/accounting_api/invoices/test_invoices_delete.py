"""
Unit tests for the invoice delete service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

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
        is_active=True,
        is_admin=False,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        is_email_verified=True
    )

@pytest.mark.asyncio
async def test_delete_invoice_success():
    """Test successful invoice deletion."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 123
    
    # Mock the service layer to return None (successful deletion)
    with patch("Backend.api.accounting.invoices.router.service.delete_invoice", new=AsyncMock(return_value=None)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/invoices/{invoice_id}")
            
            # Assert
            assert response.status_code == status.HTTP_204_NO_CONTENT
            assert response.content == b''  # No content in 204 response

@pytest.mark.asyncio
async def test_delete_invoice_by_admin():
    """Test that admin can delete any invoice."""
    # Arrange
    fake_admin = create_test_user(user_type=UserType.ADMIN)
    fake_admin.is_admin = True
    invoice_id = 456
    
    # Mock the service layer
    mock_delete = AsyncMock(return_value=None)
    with patch("Backend.api.accounting.invoices.router.service.delete_invoice", new=mock_delete):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_admin
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/invoices/{invoice_id}")
            
            # Assert
            assert response.status_code == status.HTTP_204_NO_CONTENT
            # Verify service was called with correct parameters
            mock_delete.assert_called_once()
            call_args = mock_delete.call_args
            assert call_args.args[0] == invoice_id

@pytest.mark.asyncio
async def test_delete_invoice_not_found():
    """Test delete for non-existent invoice."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 99999
    
    # Mock the service layer to raise 404
    with patch(
        "Backend.api.accounting.invoices.router.service.delete_invoice",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/invoices/{invoice_id}")
            
            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Invoice not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_invoice_unauthorized_user():
    """Test delete by unauthorized user (tenant)."""
    # Arrange
    fake_tenant = create_test_user(user_type=UserType.TENANT)
    invoice_id = 321
    
    # Mock the service layer to raise 403
    with patch(
        "Backend.api.accounting.invoices.router.service.delete_invoice",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete invoices"
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_tenant
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/invoices/{invoice_id}")
            
            # Assert
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "Not authorized to delete invoices" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_invoice_landlord_unauthorized_property():
    """Test landlord trying to delete invoice for property they don't own."""
    # Arrange
    fake_landlord = create_test_user()
    invoice_id = 789
    
    # Mock the service layer to raise forbidden for property ownership
    with patch(
        "Backend.api.accounting.invoices.router.service.delete_invoice",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this property"
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_landlord
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/invoices/{invoice_id}")
            
            # Assert
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "Not authorized for this property" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_invoice_invalid_id():
    """Test delete with invalid invoice ID format."""
    # Arrange
    fake_user = create_test_user()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act - Test non-integer ID
        response = client.delete("/api/accounting/invoices/not-an-int")
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_detail = response.json()["detail"]
        assert any("invoice_id" in str(err) for err in error_detail)

@pytest.mark.asyncio
async def test_delete_invoice_database_error():
    """Test error handling when database operation fails."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 555
    
    # Mock the service layer to raise internal server error
    with patch(
        "Backend.api.accounting.invoices.router.service.delete_invoice",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/invoices/{invoice_id}")
            
            # Assert
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Database error occurred" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_invoice_with_related_data():
    """Test deletion of invoice that has related payments or other dependencies."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 888
    
    # Mock the service layer to raise conflict error
    with patch(
        "Backend.api.accounting.invoices.router.service.delete_invoice",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete invoice with existing payments"
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/invoices/{invoice_id}")
            
            # Assert
            assert response.status_code == status.HTTP_409_CONFLICT
            assert "Cannot delete invoice with existing payments" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_invoice_unauthenticated():
    """Test delete without authentication."""
    # Arrange
    invoice_id = 999
    
    # Override get_current_user to raise authentication error
    def raise_auth_error():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Override only the auth dependency
    app.dependency_overrides[get_current_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.delete(f"/api/accounting/invoices/{invoice_id}")
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Not authenticated"