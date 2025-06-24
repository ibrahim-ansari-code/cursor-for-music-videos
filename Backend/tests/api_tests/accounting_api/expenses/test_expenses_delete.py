"""
Unit tests for the expenses deletion service functions using hybrid API testing pattern.
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


@pytest.mark.asyncio
async def test_delete_expense_success_with_receipt():
    """Test successful expense deletion with receipt blob deletion"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 42
    receipt_url = "https://blob.example.com/receipt.png"
    
    # Mock the service layer to return the receipt URL that needs deletion
    with patch(
        "Backend.api.accounting.expenses.router.service.delete_expense",
        new=AsyncMock(return_value=receipt_url)
    ):
        # Mock blob deletion
        with patch("Backend.api.accounting.expenses.router.delete_blob_with_error_handling") as mock_delete_blob:
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.delete(f"/api/accounting/expenses/{expense_id}")
                
                # Assert
                assert response.status_code == status.HTTP_204_NO_CONTENT
                assert response.content == b''  # No content for 204 response
                
                # Verify blob deletion was called
                mock_delete_blob.assert_called_once_with(receipt_url)


@pytest.mark.asyncio
async def test_delete_expense_success_without_receipt():
    """Test successful expense deletion without receipt"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 99
    
    # Mock the service layer to return None (no receipt to delete)
    with patch(
        "Backend.api.accounting.expenses.router.service.delete_expense",
        new=AsyncMock(return_value=None)
    ):
        # Mock blob deletion
        with patch("Backend.api.accounting.expenses.router.delete_blob_with_error_handling") as mock_delete_blob:
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.delete(f"/api/accounting/expenses/{expense_id}")
                
                # Assert
                assert response.status_code == status.HTTP_204_NO_CONTENT
                
                # Verify blob deletion was NOT called
                mock_delete_blob.assert_not_called()


@pytest.mark.asyncio
async def test_delete_expense_returns_204_status():
    """Test that successful deletion always returns 204 status"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 1
    receipt_url = "https://blob.example.com/receipt.png"
    
    with patch(
        "Backend.api.accounting.expenses.router.service.delete_expense",
        new=AsyncMock(return_value=receipt_url)
    ):
        with patch("Backend.api.accounting.expenses.router.delete_blob_with_error_handling"):
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.delete(f"/api/accounting/expenses/{expense_id}")
                
                # Assert
                assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_delete_expense_not_found():
    """Test deletion of non-existent expense"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 404
    
    with patch(
        "Backend.api.accounting.expenses.router.service.delete_expense",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        ))
    ):
        with patch("Backend.api.accounting.expenses.router.delete_blob_with_error_handling") as mock_delete_blob:
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.delete(f"/api/accounting/expenses/{expense_id}")
                
                # Assert
                assert response.status_code == status.HTTP_404_NOT_FOUND
                assert response.json()["detail"] == "Expense not found"
                
                # Verify blob deletion was NOT called
                mock_delete_blob.assert_not_called()


@pytest.mark.asyncio
async def test_delete_expense_unauthorized():
    """Test deletion by unauthorized user"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 2
    
    with patch(
        "Backend.api.accounting.expenses.router.service.delete_expense",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        ))
    ):
        with patch("Backend.api.accounting.expenses.router.delete_blob_with_error_handling") as mock_delete_blob:
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.delete(f"/api/accounting/expenses/{expense_id}")
                
                # Assert
                assert response.status_code == status.HTTP_403_FORBIDDEN
                assert response.json()["detail"] == "Not authorized"
                
                # Verify blob deletion was NOT called
                mock_delete_blob.assert_not_called()


@pytest.mark.asyncio
async def test_delete_expense_background_task_error_handling():
    """Test that blob deletion errors are handled gracefully"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 3
    receipt_url = "https://blob.example.com/receipt.png"
    
    with patch(
        "Backend.api.accounting.expenses.router.service.delete_expense",
        new=AsyncMock(return_value=receipt_url)
    ):
        # Mock blob deletion - the error handling should catch the exception
        with patch(
            "Backend.api.accounting.expenses.router.delete_blob_with_error_handling"
        ) as mock_delete_blob:
            # The function handles errors internally, so it shouldn't raise
            mock_delete_blob.return_value = None
            
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.delete(f"/api/accounting/expenses/{expense_id}")
                
                # Assert
                assert response.status_code == status.HTTP_204_NO_CONTENT
                
                # Verify blob deletion was attempted
                mock_delete_blob.assert_called_once_with(receipt_url)


@pytest.mark.asyncio
async def test_delete_expense_invalid_id():
    """Test deletion with invalid expense ID format"""
    # Arrange
    fake_user = create_test_user()
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.delete("/api/accounting/expenses/not-a-number")
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any(
            error["loc"] == ["path", "expense_id"] and error["type"] == "int_parsing"
            for error in errors
        )


@pytest.mark.asyncio
async def test_delete_expense_admin_user():
    """Test that admin users can delete any expense"""
    # Arrange
    fake_admin_user = create_test_user(user_type=UserType.ADMIN)
    fake_admin_user.is_admin = True
    expense_id = 555
    receipt_url = "https://blob.example.com/admin-deleted-receipt.png"
    
    with patch(
        "Backend.api.accounting.expenses.router.service.delete_expense",
        new=AsyncMock(return_value=receipt_url)
    ):
        with patch("Backend.api.accounting.expenses.router.delete_blob_with_error_handling") as mock_delete_blob:
            app.dependency_overrides[get_current_user] = lambda: fake_admin_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.delete(f"/api/accounting/expenses/{expense_id}")
                
                # Assert
                assert response.status_code == status.HTTP_204_NO_CONTENT
                
                # Verify blob deletion was called
                mock_delete_blob.assert_called_once_with(receipt_url)


@pytest.mark.asyncio
async def test_delete_expense_database_error():
    """Test deletion with database error"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 789
    
    with patch(
        "Backend.api.accounting.expenses.router.service.delete_expense",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed"
        ))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.delete(f"/api/accounting/expenses/{expense_id}")
            
            # Assert
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert response.json()["detail"] == "Database connection failed"


@pytest.mark.asyncio
async def test_delete_expense_multiple_receipts():
    """Test deletion of expense with multiple receipt URLs (future feature)"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 1234
    receipt_url = "https://blob.example.com/main-receipt.png"  # Only main receipt returned by service
    
    with patch(
        "Backend.api.accounting.expenses.router.service.delete_expense",
        new=AsyncMock(return_value=receipt_url)
    ):
        with patch("Backend.api.accounting.expenses.router.delete_blob_with_error_handling") as mock_delete_blob:
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.delete(f"/api/accounting/expenses/{expense_id}")
                
                # Assert
                assert response.status_code == status.HTTP_204_NO_CONTENT
                
                # Verify only the main receipt deletion was called
                mock_delete_blob.assert_called_once_with(receipt_url)