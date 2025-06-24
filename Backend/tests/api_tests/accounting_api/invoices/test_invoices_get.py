"""
Unit tests for the invoice retrieval service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import date, datetime, timezone
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
async def test_get_invoices_no_filters():
    """Test successful invoice retrieval without any filters."""
    # Arrange
    fake_user = create_test_user()
    
    expected_invoices = [
        InvoiceResponse(
            id=1,
            invoice_number="INV-2024-001", 
            amount=Decimal("1500.00"),
            description="January rent",
            issue_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            due_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            status=PaymentStatus.PAID,
            property_id=123,
            tenant_id=456,
            quickbooks_id=None,
            last_synced_at=None,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
            property=PropertyInfo(id=123, name="Test Property"),
            tenant=TenantInfo(id=456, full_name="John Doe")
        ),
        InvoiceResponse(
            id=2,
            invoice_number="INV-2024-002",
            amount=Decimal("1500.00"),
            description="February rent", 
            issue_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
            due_date=datetime(2024, 2, 15, tzinfo=timezone.utc),
            status=PaymentStatus.PENDING,
            property_id=123,
            tenant_id=456,
            quickbooks_id=None,
            last_synced_at=None,
            created_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
            property=PropertyInfo(id=123, name="Test Property"),
            tenant=TenantInfo(id=456, full_name="John Doe")
        )
    ]
    
    # Mock the service layer
    with patch("Backend.api.accounting.invoices.router.service.get_invoices", new=AsyncMock(return_value=expected_invoices)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/accounting/invoices")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["id"] == 1
            assert data[0]["invoice_number"] == "INV-2024-001"
            assert data[0]["status"] == "Paid"
            assert data[1]["id"] == 2
            assert data[1]["status"] == "Pending"

@pytest.mark.asyncio
async def test_get_invoices_with_tenant_and_property_filters():
    """Test invoice retrieval with tenant and property filters."""
    # Arrange
    fake_user = create_test_user()
    tenant_id = 42
    property_id = 99
    
    expected_invoices = [
        InvoiceResponse(
            id=3,
            invoice_number="INV-2024-003",
            amount=Decimal("2000.00"),
            description="Filtered invoice",
            issue_date=datetime(2024, 3, 1, tzinfo=timezone.utc),
            due_date=datetime(2024, 3, 15, tzinfo=timezone.utc),
            status=PaymentStatus.PAID,
            property_id=property_id,
            tenant_id=tenant_id,
            quickbooks_id=None,
            last_synced_at=None,
            created_at=datetime(2024, 3, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 3, 5, tzinfo=timezone.utc),
            property=PropertyInfo(id=property_id, name="Filtered Property"),
            tenant=TenantInfo(id=tenant_id, full_name="Jane Smith")
        )
    ]
    
    # Mock the service layer
    mock_get_invoices = AsyncMock(return_value=expected_invoices)
    
    with patch("Backend.api.accounting.invoices.router.service.get_invoices", new=mock_get_invoices):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(
                f"/api/accounting/invoices?tenant_id={tenant_id}&property_id={property_id}"
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["property_id"] == property_id
            assert data[0]["tenant_id"] == tenant_id
            assert data[0]["property"]["name"] == "Filtered Property"
            assert data[0]["tenant"]["full_name"] == "Jane Smith"
            
            # Verify service was called with correct parameters
            mock_get_invoices.assert_called_once()
            call_args = mock_get_invoices.call_args
            assert call_args.kwargs["tenant_id"] == tenant_id
            assert call_args.kwargs["property_id"] == property_id

@pytest.mark.asyncio
async def test_get_invoices_with_date_and_status_filters():
    """Test invoice retrieval with date range and payment status filters."""
    # Arrange
    fake_user = create_test_user()
    start_date = date(2024, 1, 1)
    end_date = date(2024, 6, 30)
    payment_status = PaymentStatus.OVERDUE
    
    expected_invoices = [
        InvoiceResponse(
            id=4,
            invoice_number="INV-2024-004",
            amount=Decimal("1800.00"),
            description="Overdue invoice",
            issue_date=datetime(2024, 3, 15, tzinfo=timezone.utc),
            due_date=datetime(2024, 3, 30, tzinfo=timezone.utc),
            status=payment_status,
            property_id=123,
            tenant_id=456,
            quickbooks_id=None,
            last_synced_at=None,
            created_at=datetime(2024, 3, 15, tzinfo=timezone.utc),
            updated_at=datetime(2024, 4, 1, tzinfo=timezone.utc),
            property=PropertyInfo(id=123, name="Test Property"),
            tenant=TenantInfo(id=456, full_name="John Doe")
        )
    ]
    
    # Mock the service layer
    mock_get_invoices = AsyncMock(return_value=expected_invoices)
    
    with patch("Backend.api.accounting.invoices.router.service.get_invoices", new=mock_get_invoices):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(
                f"/api/accounting/invoices?payment_status_filter={payment_status.value}&start_date={start_date}&end_date={end_date}"
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == payment_status.value
            assert data[0]["issue_date"].startswith("2024-03-15")
            
            # Verify service was called with correct parameters
            mock_get_invoices.assert_called_once()
            call_args = mock_get_invoices.call_args
            assert call_args.kwargs["payment_status_filter"] == payment_status
            assert call_args.kwargs["start_date"] == start_date
            assert call_args.kwargs["end_date"] == end_date

@pytest.mark.asyncio
async def test_get_invoices_invalid_date_range():
    """Test invoice retrieval with invalid date range (start > end) should return 400."""
    # Arrange
    fake_user = create_test_user()
    start_date = date(2024, 7, 1)
    end_date = date(2024, 6, 1)  # End before start
    
    # Mock the service layer to raise validation error for invalid date range
    with patch(
        "Backend.api.accounting.invoices.router.service.get_invoices",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date range: start_date cannot be after end_date"
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(
                f"/api/accounting/invoices?start_date={start_date}&end_date={end_date}"
            )
            
            # Assert
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid date range" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_invoices_limit_zero():
    """Test invoice retrieval with limit=0 (should return empty list)."""
    # Arrange
    fake_user = create_test_user()
    
    # Mock the service layer to return empty list when limit is 0
    with patch("Backend.api.accounting.invoices.router.service.get_invoices", new=AsyncMock(return_value=[])):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/accounting/invoices?limit=0")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data == []

@pytest.mark.asyncio
async def test_get_invoice_user_access_control():
    """Test that users can only access invoices they have permission to view."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 10
    
    expected_invoice = InvoiceResponse(
        id=invoice_id,
        invoice_number="INV-2024-010",
        amount=Decimal("1500.00"),
        description="Test invoice",
        issue_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
        due_date=datetime(2024, 6, 15, tzinfo=timezone.utc),
        status=PaymentStatus.PAID,
        property_id=123,
        tenant_id=456,
        quickbooks_id=None,
        last_synced_at=None,
        created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        property=PropertyInfo(id=123, name="Test Property"),
        tenant=TenantInfo(id=456, full_name="John Doe")
    )
    
    # Mock the service layer
    mock_get_invoice_by_id = AsyncMock(return_value=expected_invoice)
    
    with patch("Backend.api.accounting.invoices.router.service.get_invoice_by_id", new=mock_get_invoice_by_id):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/accounting/invoices/{invoice_id}")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == invoice_id
            assert data["invoice_number"] == "INV-2024-010"
            assert data["status"] == "Paid"
            
            # Verify service was called with correct parameters
            mock_get_invoice_by_id.assert_called_once()
            call_args = mock_get_invoice_by_id.call_args
            assert call_args.args[0] == invoice_id  # invoice_id
            assert call_args.args[2] == fake_user  # current_user

@pytest.mark.asyncio
async def test_get_invoice_response_fields():
    """Test that all expected fields are present in the invoice response."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 101
    
    expected_invoice = InvoiceResponse(
        id=invoice_id,
        invoice_number="INV-2024-101",
        amount=Decimal("500.00"),
        description="June rent",
        issue_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
        due_date=datetime(2024, 6, 15, tzinfo=timezone.utc),
        status=PaymentStatus.PAID,
        property_id=77,
        tenant_id=55,
        quickbooks_id="QB-INV-101",
        last_synced_at=datetime(2024, 6, 2, tzinfo=timezone.utc),
        created_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2024, 6, 2, 12, 0, 0, tzinfo=timezone.utc),
        property=PropertyInfo(id=77, name="Property 77"),
        tenant=TenantInfo(id=55, full_name="Tenant 55")
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.invoices.router.service.get_invoice_by_id", new=AsyncMock(return_value=expected_invoice)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/accounting/invoices/{invoice_id}")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Check all required fields are present
            required_fields = [
                "id", "invoice_number", "amount", "description",
                "issue_date", "due_date", "status", "property_id",
                "tenant_id", "quickbooks_id", "last_synced_at",
                "created_at", "updated_at", "property", "tenant"
            ]
            
            for field in required_fields:
                assert field in data, f"Field '{field}' missing from response"
            
            # Verify specific values
            assert data["id"] == invoice_id
            assert data["amount"] == "500.00"  # Amount is returned as string
            assert data["status"] == "Paid"
            assert data["property"]["name"] == "Property 77"
            assert data["tenant"]["full_name"] == "Tenant 55"

@pytest.mark.asyncio
async def test_get_invoice_with_extra_request_data():
    """Test that extra query params and headers are ignored by the endpoint."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 202
    
    expected_invoice = InvoiceResponse(
        id=invoice_id,
        invoice_number="INV-2024-202",
        amount=Decimal("750.00"),
        description="July rent",
        issue_date=datetime(2024, 7, 1, tzinfo=timezone.utc),
        due_date=datetime(2024, 7, 15, tzinfo=timezone.utc),
        status=PaymentStatus.PENDING,
        property_id=88,
        tenant_id=66,
        quickbooks_id=None,
        last_synced_at=None,
        created_at=datetime(2024, 7, 1, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2024, 7, 2, 12, 0, 0, tzinfo=timezone.utc),
        property=PropertyInfo(id=88, name="Property 88"),
        tenant=TenantInfo(id=66, full_name="Tenant 66")
    )
    
    # Mock the service layer
    mock_get_invoice_by_id = AsyncMock(return_value=expected_invoice)
    
    with patch("Backend.api.accounting.invoices.router.service.get_invoice_by_id", new=mock_get_invoice_by_id):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act - Add extra query param and header (should be ignored)
            response = client.get(
                f"/api/accounting/invoices/{invoice_id}?irrelevant_param=foo&another=bar",
                headers={"X-Extra-Header": "should-be-ignored", "X-Another": "test"}
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == invoice_id
            assert data["status"] == "Pending"
            
            # Verify service was called with only the expected parameters
            mock_get_invoice_by_id.assert_called_once()
            call_args = mock_get_invoice_by_id.call_args
            assert call_args.args[0] == invoice_id
            # Extra params should not be passed to service

@pytest.mark.asyncio
async def test_get_invoice_not_found():
    """Test 404 response when invoice doesn't exist."""
    # Arrange
    fake_user = create_test_user()
    invoice_id = 9999
    
    # Mock the service layer to raise 404 exception
    with patch(
        "Backend.api.accounting.invoices.router.service.get_invoice_by_id",
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
            response = client.get(f"/api/accounting/invoices/{invoice_id}")
            
            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "Invoice not found"

@pytest.mark.asyncio
async def test_get_invoice_unauthenticated():
    """Test 401 response when user is not authenticated."""
    # Arrange
    invoice_id = 303
    
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
        response = client.get(f"/api/accounting/invoices/{invoice_id}")
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_get_invoice_forbidden_access():
    """Test 403 response when user doesn't have permission to access invoice."""
    # Arrange
    fake_user = create_test_user()  # Using uuid4() instead of string literal
    invoice_id = 404
    
    # Mock the service layer to raise forbidden exception
    with patch(
        "Backend.api.accounting.invoices.router.service.get_invoice_by_id",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden"
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/accounting/invoices/{invoice_id}")
            
            # Assert
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json()["detail"] == "Forbidden"