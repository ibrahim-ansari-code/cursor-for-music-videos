"""
Unit tests for the invoice update service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.api.accounting.invoices.schemas import InvoiceResponse, PropertyInfo, TenantInfo
from Backend.models.accounting.common import PaymentStatus
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
async def test_update_invoice_success():
    """Test successful invoice update with all fields."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 123
    
    update_data = {
        "amount": "2500.00",
        "description": "Updated description",
        "status": "Paid",
        "issue_date": "2024-06-05T12:00:00Z",
        "due_date": "2024-06-20T12:00:00Z"
    }
    
    # Expected response after update
    updated_invoice = InvoiceResponse(
        id=invoice_id,
        invoice_number="INV-2024-123",
        amount=Decimal("2500.00"),
        description="Updated description",
        issue_date=datetime(2024, 6, 5, tzinfo=timezone.utc),
        due_date=datetime(2024, 6, 20, tzinfo=timezone.utc),
        status=PaymentStatus.PAID,
        property_id=123,
        tenant_id=456,
        quickbooks_id=None,
        last_synced_at=None,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        property=PropertyInfo(id=123, name="Test Property"),
        tenant=TenantInfo(id=456, full_name="John Doe")
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.invoices.router.service.update_invoice", new=AsyncMock(return_value=updated_invoice)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/invoices/{invoice_id}", json=update_data)
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == invoice_id
            assert data["amount"] == "2500.00"
            assert data["description"] == "Updated description"
            assert data["status"] == "Paid"

@pytest.mark.asyncio
async def test_update_invoice_partial_update():
    """Test partial invoice update - only updating status."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 456
    
    update_data = {
        "status": "Paid"
    }
    
    # Expected response with only status updated
    updated_invoice = InvoiceResponse(
        id=invoice_id,
        invoice_number="INV-2024-456",
        amount=Decimal("1500.00"),  # Original amount
        description="Original description",
        issue_date=FIXED_DATETIME,
        due_date=datetime(2024, 6, 15, tzinfo=timezone.utc),
        status=PaymentStatus.PAID,  # Updated status
        property_id=123,
        tenant_id=456,
        quickbooks_id=None,
        last_synced_at=None,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        property=PropertyInfo(id=123, name="Test Property"),
        tenant=TenantInfo(id=456, full_name="John Doe")
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.invoices.router.service.update_invoice", new=AsyncMock(return_value=updated_invoice)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/invoices/{invoice_id}", json=update_data)
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "Paid"
            assert data["amount"] == "1500.00"  # Unchanged

@pytest.mark.asyncio
async def test_update_invoice_not_found():
    """Test update for non-existent invoice."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 9999
    
    update_data = {
        "amount": "2000.00"
    }
    
    # Mock the service layer to raise 404
    with patch(
        "Backend.api.accounting.invoices.router.service.update_invoice",
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
            response = client.put(f"/api/accounting/invoices/{invoice_id}", json=update_data)
            
            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Invoice not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_invoice_unauthorized():
    """Test update by unauthorized user (tenant)."""
    # Arrange
    fake_tenant_user = create_test_user(user_type=UserType.TENANT)
    invoice_id = 321
    
    update_data = {
        "amount": "3000.00"
    }
    
    # Mock the service layer to raise 403
    with patch(
        "Backend.api.accounting.invoices.router.service.update_invoice",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update invoices"
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_tenant_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/invoices/{invoice_id}", json=update_data)
            
            # Assert
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "Not authorized" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_invoice_invalid_amount():
    """Test update with invalid amount (negative)."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 654
    
    update_data = {
        "amount": "-100.00"  # Negative amount
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.put(f"/api/accounting/invoices/{invoice_id}", json=update_data)
        
        # Assert - Should get validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_detail = response.json()["detail"]
        assert any("Amount must be greater than 0" in str(error) for error in error_detail)

@pytest.mark.asyncio
async def test_update_invoice_invalid_date_range():
    """Test update with due date before issue date."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 789
    
    update_data = {
        "issue_date": "2024-06-15T12:00:00Z",
        "due_date": "2024-06-01T12:00:00Z"  # Due before issue
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.put(f"/api/accounting/invoices/{invoice_id}", json=update_data)
        
        # Assert - Pydantic validation returns 422, not 400
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_detail = response.json()["detail"]
        assert any("Due date cannot be earlier than issue date" in str(error) for error in error_detail)

@pytest.mark.asyncio
async def test_update_invoice_landlord_unauthorized_property():
    """Test landlord trying to update invoice for property they don't own."""
    # Arrange
    fake_landlord = create_test_user()
    invoice_id = 555
    
    update_data = {
        "amount": "1800.00"
    }
    
    # Mock the service layer to raise forbidden for property ownership
    with patch(
        "Backend.api.accounting.invoices.router.service.update_invoice",
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
            response = client.put(f"/api/accounting/invoices/{invoice_id}", json=update_data)
            
            # Assert
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "Not authorized for this property" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_invoice_admin_can_update_any():
    """Test admin can update any invoice."""
    # Arrange
    fake_admin = create_test_user(user_type=UserType.ADMIN)
    fake_admin.is_admin = True
    invoice_id = 888
    
    update_data = {
        "amount": "5000.00",
        "description": "Admin updated invoice"
    }
    
    # Expected response
    updated_invoice = InvoiceResponse(
        id=invoice_id,
        invoice_number="INV-2024-888",
        amount=Decimal("5000.00"),
        description="Admin updated invoice",
        issue_date=FIXED_DATETIME,
        due_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
        status=PaymentStatus.PENDING,
        property_id=999,  # Any property
        tenant_id=888,
        quickbooks_id=None,
        last_synced_at=None,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        property=PropertyInfo(id=999, name="Any Property"),
        tenant=TenantInfo(id=888, full_name="Any Tenant")
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.invoices.router.service.update_invoice", new=AsyncMock(return_value=updated_invoice)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_admin
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/invoices/{invoice_id}", json=update_data)
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["amount"] == "5000.00"
            assert data["description"] == "Admin updated invoice"