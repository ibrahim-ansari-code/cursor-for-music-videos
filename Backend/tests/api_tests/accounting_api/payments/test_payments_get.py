"""
Unit tests for the payments retrieval service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.accounting.payments.schemas import PaymentResponse, PaginatedPaymentsResponse
from Backend.models.accounting.payment import PaymentMethod
from Backend.models.accounting.common import PaymentStatus
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 5, 1, 12, 0, 0, tzinfo=timezone.utc)

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

def build_payment_response(payment_id, lease_id, payment_date, **kwargs):
    """Helper function to build a PaymentResponse object."""
    return PaymentResponse(
        id=payment_id,
        lease_id=lease_id,
        tenant_id=kwargs.get('tenant_id', 2),
        amount=kwargs.get('amount', Decimal("1500.00")),
        payment_date=payment_date,
        payment_method=kwargs.get('payment_method', PaymentMethod.OTHER),
        status=kwargs.get('status', PaymentStatus.PAID),
        transaction_reference=kwargs.get('transaction_reference'),
        description=kwargs.get('description'),
        receipt_url=kwargs.get('receipt_url'),
        created_at=kwargs.get('created_at', FIXED_DATETIME),
        updated_at=kwargs.get('updated_at', FIXED_DATETIME),
        tenant_name=kwargs.get('tenant_name', 'Test Tenant'),
        property_name=kwargs.get('property_name', 'Test Property')
    )

# =============================================================================
# GET PAYMENTS LIST TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_payments_list_success():
    """Test successful retrieval of paginated payments list."""
    # Arrange
    fake_user = create_test_user()
    
    # Create mock payments
    payments = [
        build_payment_response(1, 101, datetime(2024, 5, 1, tzinfo=timezone.utc)),
        build_payment_response(2, 102, datetime(2024, 5, 2, tzinfo=timezone.utc)),
    ]
    paginated_response = PaginatedPaymentsResponse(items=payments, has_more=False)
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.get_payments", new=AsyncMock(return_value=paginated_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/accounting/payments")
            
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert isinstance(data["items"], list)
            assert len(data["items"]) == 2
            assert data["has_more"] is False

@pytest.mark.asyncio
async def test_get_payments_with_filters():
    """Test payment retrieval with various filters."""
    # Arrange
    fake_user = create_test_user()
    
    # Create filtered payments
    payments = [
        build_payment_response(
            1, 101, datetime(2024, 5, 1, tzinfo=timezone.utc),
            status=PaymentStatus.PENDING
        )
    ]
    paginated_response = PaginatedPaymentsResponse(items=payments, has_more=False)
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.get_payments", new=AsyncMock(return_value=paginated_response)) as mock_get_payments:
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(
                "/api/accounting/payments",
                params={
                    "lease_id": 101,
                    "property_id": 10,
                    "tenant_id": 5,
                    "payment_status": "Pending",
                    "start_date": "2024-05-01",
                    "end_date": "2024-05-31",
                    "limit": 50,
                    "offset": 0
                }
            )
            
    # Assert
            assert response.status_code == 200
            # Verify service was called with correct parameters
            mock_get_payments.assert_called_once()
            call_kwargs = mock_get_payments.call_args[1]
            assert call_kwargs["lease_id"] == 101
            assert call_kwargs["property_id"] == 10
            assert call_kwargs["tenant_id"] == 5
            assert call_kwargs["payment_status"] == PaymentStatus.PENDING
            assert call_kwargs["limit"] == 50
            assert call_kwargs["offset"] == 0

@pytest.mark.asyncio
async def test_get_payments_pagination():
    """Test payment list pagination."""
    # Arrange
    fake_user = create_test_user()
    
    # Create 100 payments (simulating more than one page)
    payments = [build_payment_response(i, 100+i, datetime(2024, 5, 1, tzinfo=timezone.utc)) for i in range(100)]
    paginated_response = PaginatedPaymentsResponse(items=payments, has_more=True)
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.get_payments", new=AsyncMock(return_value=paginated_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/accounting/payments", params={"limit": 100, "offset": 0})
            
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 100
            assert data["has_more"] is True

@pytest.mark.asyncio
async def test_get_payments_tenant_access():
    """Test that tenants can only see their own payments."""
    # Arrange
    fake_tenant_user = create_test_user(user_type=UserType.TENANT)
    
    # Create tenant's payments only
    payments = [
        build_payment_response(1, 101, datetime(2024, 5, 1, tzinfo=timezone.utc), tenant_name="Current Tenant")
    ]
    paginated_response = PaginatedPaymentsResponse(items=payments, has_more=False)
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.get_payments", new=AsyncMock(return_value=paginated_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_tenant_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/accounting/payments")
            
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1

# =============================================================================
# GET SINGLE PAYMENT TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_payment_by_id_success():
    """Test successful retrieval of a single payment."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 123
    
    payment_response = build_payment_response(
        payment_id, 1, datetime(2024, 5, 1, tzinfo=timezone.utc),
        payment_method=PaymentMethod.BANK_TRANSFER,
        status=PaymentStatus.PAID,
        transaction_reference="TXN123",
        description="Rent payment",
        tenant_name="John Doe",
        property_name="Sunset Apartments"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.get_payment_by_id", new=AsyncMock(return_value=payment_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == payment_id
            assert data["property_name"] == "Sunset Apartments"
            assert data["tenant_name"] == "John Doe"
            assert data["amount"] == "1500.00"
            assert data["status"] == "Paid"

@pytest.mark.asyncio
async def test_get_payment_not_found():
    """Test retrieval of non-existent payment."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 999
    
    # Mock the service to raise not found exception
    with patch(
        "Backend.api.accounting.payments.router.service.get_payment_by_id",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail=f"Payment {payment_id} not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 404
            assert response.json()["detail"] == f"Payment {payment_id} not found"

@pytest.mark.asyncio
async def test_get_payment_unauthorized():
    """Test unauthorized payment access by different landlord."""
    # Arrange
    fake_landlord = create_test_user()
    payment_id = 123
    
    # Mock the service to raise forbidden exception
    with patch(
        "Backend.api.accounting.payments.router.service.get_payment_by_id",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Not authorized"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_landlord
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 403
            assert response.json()["detail"] == "Not authorized"

@pytest.mark.asyncio
async def test_get_payment_admin_access():
    """Test that admin users can access any payment."""
    # Arrange
    fake_admin = create_test_user(user_type=UserType.ADMIN)
    fake_admin.is_admin = True
    payment_id = 555
    
    payment_response = build_payment_response(
        payment_id, 1, datetime(2024, 6, 1, tzinfo=timezone.utc),
        amount=Decimal("2500.00"),
        payment_method=PaymentMethod.CREDIT_CARD,
        status=PaymentStatus.PAID,
        transaction_reference="TXN555",
        description="Admin test payment",
        tenant_name="Alice Smith",
        property_name="Maple Grove"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.get_payment_by_id", new=AsyncMock(return_value=payment_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_admin
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/accounting/payments/{payment_id}")
            
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == payment_id
            assert data["property_name"] == "Maple Grove"
            assert data["tenant_name"] == "Alice Smith"
            assert data["amount"] == "2500.00"
            assert data["status"] == "Paid"

# =============================================================================
# GET OUTSTANDING PAYMENTS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_outstanding_payments_current_month():
    """Test retrieval of outstanding payments for current month."""
    # Arrange
    fake_user = create_test_user()
    
    # Create outstanding payments (PENDING and OVERDUE)
    payments = [
        build_payment_response(1, 101, FIXED_DATETIME, status=PaymentStatus.PENDING),
        build_payment_response(2, 102, FIXED_DATETIME, status=PaymentStatus.OVERDUE),
    ]
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.get_outstanding_payments_for_month", new=AsyncMock(return_value=payments)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/accounting/payments/outstanding/current-month")
            
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert all(p["status"] in ["Pending", "Overdue"] for p in data)

@pytest.mark.asyncio
async def test_get_outstanding_payments_with_limit():
    """Test outstanding payments retrieval respects limit."""
    # Arrange
    fake_user = create_test_user()
    
    # Create many outstanding payments
    payments = [
        build_payment_response(i, 100+i, FIXED_DATETIME, status=PaymentStatus.PENDING)
        for i in range(50)
    ]
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.get_outstanding_payments_for_month", new=AsyncMock(return_value=payments)) as mock_service:
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act - Request with specific limit
            response = client.get("/api/accounting/payments/outstanding/current-month", params={"limit": 25})
            
    # Assert
            assert response.status_code == 200
            # Verify service was called with the limit parameter
            mock_service.assert_called_once()
            call_kwargs = mock_service.call_args.kwargs
            assert call_kwargs.get("limit") == 25

@pytest.mark.asyncio
async def test_get_outstanding_payments_limit_validation():
    """Test that excessive limits are rejected with validation error."""
    # Arrange
    fake_user = create_test_user()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act - Request with excessive limit
        response = client.get("/api/accounting/payments/outstanding/current-month", params={"limit": 1000})
        
    # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("less than or equal to 500" in str(error) for error in error_detail)

# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_payments_database_error():
    """Test error handling for database failures."""
    # Arrange
    fake_user = create_test_user()
    
    # Mock the service to raise internal server error
    with patch(
        "Backend.api.accounting.payments.router.service.get_payments",
        new=AsyncMock(side_effect=HTTPException(status_code=500, detail="Failed to fetch payments."))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/accounting/payments")
            
    # Assert
            assert response.status_code == 500
            assert "Failed to fetch payments" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_payment_date_filter_validation():
    """Test date filter parameter validation."""
    # Arrange
    fake_user = create_test_user()
    
    # Create empty response
    paginated_response = PaginatedPaymentsResponse(items=[], has_more=False)
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.get_payments", new=AsyncMock(return_value=paginated_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act - Invalid date format
            response = client.get(
                "/api/accounting/payments",
                params={"start_date": "invalid-date"}
            )
            
    # Assert - Should get 422 for invalid date format
            assert response.status_code == 422