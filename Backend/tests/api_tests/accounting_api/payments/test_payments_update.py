"""
Unit tests for the payments update service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.api.accounting.payments.schemas import PaymentUpdate, PaymentResponse
from Backend.models.accounting.payment import PaymentMethod
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

def build_payment_response(payment_id, lease_id, **kwargs):
    """Helper function to build a PaymentResponse object."""
    return PaymentResponse(
        id=payment_id,
        lease_id=lease_id,
        tenant_id=kwargs.get('tenant_id', 2),
        amount=kwargs.get('amount', Decimal("1500.00")),
        payment_date=kwargs.get('payment_date', FIXED_DATETIME),
        payment_method=kwargs.get('payment_method', PaymentMethod.OTHER),
        status=kwargs.get('status', PaymentStatus.PENDING),
        transaction_reference=kwargs.get('transaction_reference'),
        description=kwargs.get('description'),
        receipt_url=kwargs.get('receipt_url'),
        created_at=kwargs.get('created_at', FIXED_DATETIME),
        updated_at=kwargs.get('updated_at', FIXED_DATETIME),
        tenant_name=kwargs.get('tenant_name', 'Test Tenant'),
        property_name=kwargs.get('property_name', 'Test Property')
    )

# =============================================================================
# UPDATE PAYMENT TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_update_payment_all_fields_success():
    """Test successful update of all payment fields."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 123
    
    update_data = {
        "amount": "1500.00",
        "payment_date": "2024-06-01T12:00:00Z",
        "payment_method": "Bank Transfer",
        "status": "Paid",
        "transaction_reference": "TXN-9999",
        "description": "Updated rent payment",
        "receipt_url": "https://example.com/receipt.pdf"
    }
    
    # Create the response that service would return
    updated_response = build_payment_response(
        payment_id, 1,
        amount=Decimal("1500.00"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.BANK_TRANSFER,
        status=PaymentStatus.PAID,
        transaction_reference="TXN-9999",
        description="Updated rent payment",
        receipt_url="https://example.com/receipt.pdf",
        tenant_name="John Doe",
        property_name="Sunset Apartments"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.update_payment", new=AsyncMock(return_value=updated_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
            
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == payment_id
            assert data["amount"] == "1500.00"
            assert data["payment_method"] == "Bank Transfer"
            assert data["status"] == "Paid"
            assert data["transaction_reference"] == "TXN-9999"
            assert data["description"] == "Updated rent payment"
            assert data["receipt_url"] == "https://example.com/receipt.pdf"

@pytest.mark.asyncio
async def test_update_payment_single_field():
    """Test partial update with single field."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 456
    
    update_data = {
        "description": "Corrected payment note"
    }
    
    # Create response with only description changed
    updated_response = build_payment_response(
        payment_id, 10,
        amount=Decimal("1200.00"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.CASH,
        status=PaymentStatus.PENDING,
        transaction_reference="TXN-1234",
        description="Corrected payment note",
        receipt_url="https://example.com/receipt2.pdf",
        tenant_name="Jane Smith",
        property_name="Maple Residences"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.update_payment", new=AsyncMock(return_value=updated_response)) as mock_update:
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
            
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["description"] == "Corrected payment note"
            # Verify service was called with correct parameters
            mock_update.assert_called_once()
            call_args = mock_update.call_args[0]
            assert call_args[0] == payment_id
            assert isinstance(call_args[1], PaymentUpdate)

@pytest.mark.asyncio
async def test_update_payment_tenant_forbidden():
    """Test that tenants cannot update payments."""
    # Arrange
    fake_tenant = create_test_user(user_type=UserType.TENANT)
    payment_id = 789
    
    update_data = {
        "amount": "1000.00"
    }
    
    # Mock the service to raise forbidden exception
    with patch(
        "Backend.api.accounting.payments.router.service.update_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Tenants cannot update payment records."))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_tenant
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
            
    # Assert
            assert response.status_code == 403
            assert "Tenants cannot update payment records" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_payment_not_found():
    """Test updating non-existent payment."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 9999
    
    update_data = {
        "description": "Trying to update non-existent payment"
    }
    
    # Mock the service to raise not found exception
    with patch(
        "Backend.api.accounting.payments.router.service.update_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail=f"Payment {payment_id} not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
            
    # Assert
            assert response.status_code == 404
            assert f"Payment {payment_id} not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_payment_unauthorized():
    """Test updating payment owned by another landlord."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 321
    
    update_data = {
        "amount": "2000.00"
    }
    
    # Mock the service to raise forbidden exception
    with patch(
        "Backend.api.accounting.payments.router.service.update_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Not authorized to update this payment"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
            
    # Assert
            assert response.status_code == 403
            assert "Not authorized to update this payment" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_payment_validation_errors():
    """Test validation errors for invalid update data."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 321
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    invalid_test_cases = [
        # Negative amount
        (
            {"amount": "-500.00"},
            "Amount must be positive"
        ),
        # Invalid status
        (
            {"status": "INVALID_STATUS"},
            "Input should be"
        ),
        # Invalid payment method
        (
            {"payment_method": "BITCOIN"},
            "Input should be"
        ),
        # Invalid date format
        (
            {"payment_date": "not-a-date"},
            "Input should be a valid datetime"
        ),
    ]
    
    with TestClientWithHost(app) as client:
        for test_data, expected_error in invalid_test_cases:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=test_data)
            
            # Assert
            assert response.status_code == 422
            error_detail = response.json()["detail"]
            assert any(expected_error in str(error) for error in error_detail)

@pytest.mark.asyncio
async def test_update_payment_empty_update():
    """Test that empty update is allowed (all fields are optional)."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 321
    
    # Create response for empty update (returns existing data)
    existing_payment = build_payment_response(
        payment_id, 1,
        amount=Decimal("1500.00"),
        status=PaymentStatus.PAID
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.update_payment", new=AsyncMock(return_value=existing_payment)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json={})
            
    # Assert - Empty update should succeed and return existing data
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == payment_id

@pytest.mark.asyncio
async def test_update_payment_admin_access():
    """Test that admin users can update any payment."""
    # Arrange
    fake_admin = create_test_user(user_type=UserType.ADMIN)
    fake_admin.is_admin = True
    payment_id = 999
    
    update_data = {
        "status": "Paid",
        "description": "Admin updated payment"
    }
    
    # Create the response
    updated_response = build_payment_response(
        payment_id, 50,
        status=PaymentStatus.PAID,
        description="Admin updated payment",
        tenant_name="Admin Test Tenant",
        property_name="Admin Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.update_payment", new=AsyncMock(return_value=updated_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_admin
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
            
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "Paid"
            assert data["description"] == "Admin updated payment"

@pytest.mark.asyncio
async def test_update_payment_status_transitions():
    """Test various payment status transitions."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 100
    
    # Test various status transitions
    status_transitions = [
        ("Pending", "Paid"),
        ("Pending", "Cancelled"),
        ("Paid", "Refunded"),
        ("Pending", "Overdue"),
        ("Partial", "Paid"),
    ]
    
    for from_status, to_status in status_transitions:
        update_data = {"status": to_status}
        
        # Create response with new status
        updated_response = build_payment_response(
            payment_id, 1,
            status=getattr(PaymentStatus, to_status.upper().replace(" ", "_"))
        )
        
        # Mock the service layer
        with patch("Backend.api.accounting.payments.router.service.update_payment", new=AsyncMock(return_value=updated_response)):
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
                
        # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == to_status

@pytest.mark.asyncio
async def test_update_payment_receipt_url():
    """Test updating payment with new receipt URL."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 200
    
    update_data = {
        "receipt_url": "https://newstorage.example.com/receipts/updated-receipt.pdf"
    }
    
    # Create response with new receipt URL
    updated_response = build_payment_response(
        payment_id, 1,
        receipt_url="https://newstorage.example.com/receipts/updated-receipt.pdf"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.update_payment", new=AsyncMock(return_value=updated_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
            
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["receipt_url"] == "https://newstorage.example.com/receipts/updated-receipt.pdf"

@pytest.mark.asyncio
async def test_update_payment_large_amount():
    """Test updating payment with large amount."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 300
    
    update_data = {
        "amount": "999999.99"  # Maximum reasonable amount
    }
    
    # Create response with large amount
    updated_response = build_payment_response(
        payment_id, 1,
        amount=Decimal("999999.99")
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.update_payment", new=AsyncMock(return_value=updated_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
            
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["amount"] == "999999.99"

@pytest.mark.asyncio
async def test_update_payment_decimal_precision_validation():
    """Test payment update with amounts having more than 2 decimal places."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 301
    
    # Test with 3 decimal places
    update_data = {
        "amount": "1500.123"  # 3 decimal places
    }
    
    # Create a mock response - the service would handle decimal validation
    updated_response = build_payment_response(
        payment_id, 1,
        amount=Decimal("1500.12")  # Rounded to 2 decimal places
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.update_payment", new=AsyncMock(return_value=updated_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
            
    # Assert
        # Should succeed and return rounded amount
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["amount"] == "1500.12"  # Rounded to 2 decimal places

@pytest.mark.asyncio
async def test_update_payment_database_error():
    """Test error handling for database failures during update."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 400
    
    update_data = {
        "amount": "1500.00"
    }
    
    # Mock the service to raise internal server error
    with patch(
        "Backend.api.accounting.payments.router.service.update_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=500, detail="Failed to update payment."))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
            
    # Assert
            assert response.status_code == 500
            assert "Failed to update payment" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_payment_concurrent_modification():
    """Test handling of concurrent modification conflicts."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 500
    
    update_data = {
        "amount": "2000.00"
    }
    
    # Mock the service to raise conflict exception
    with patch(
        "Backend.api.accounting.payments.router.service.update_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=409, detail="Payment was modified by another user"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
            
    # Assert
            assert response.status_code == 409
            assert "Payment was modified by another user" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_payment_with_reduction():
    """Test updating a payment to add reduction amount and reason."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 100
    
    update_data = {
        "amount": "1400.00",  # Reduced from $1500
        "reduction_amount": "100.00",  # Reduction is less than the amount
        "reduction_reason": "First-time tenant discount"
    }
    
    # Create the updated response
    fake_response = PaymentResponse(
        id=payment_id,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("1400.00"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.BANK_TRANSFER,
        status=PaymentStatus.PAID,
        reduction_amount=Decimal("100.00"),
        reduction_reason="First-time tenant discount",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="John Doe",
        property_name="Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.update_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
    
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["amount"] == "1400.00"
            assert data["reduction_amount"] == "100.00"
            assert data["reduction_reason"] == "First-time tenant discount"

@pytest.mark.asyncio
async def test_update_payment_remove_reduction():
    """Test updating a payment to remove reduction."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 101
    
    update_data = {
        "amount": "1500.00",  # Full amount
        "reduction_amount": None,  # Remove reduction
        "reduction_reason": None
    }
    
    # Create the updated response
    fake_response = PaymentResponse(
        id=payment_id,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("1500.00"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.BANK_TRANSFER,
        status=PaymentStatus.PAID,
        reduction_amount=None,
        reduction_reason=None,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="John Doe",
        property_name="Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.update_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
    
    # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["amount"] == "1500.00"
            assert data["reduction_amount"] is None
            assert data["reduction_reason"] is None

@pytest.mark.asyncio
async def test_update_payment_negative_reduction_validation():
    """Test that updating with negative reduction amount is rejected."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 102
    
    update_data = {
        "reduction_amount": "-50.00"  # Invalid negative reduction
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
        
        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("Reduction amount must be zero or positive" in str(error["msg"]) for error in error_detail)

@pytest.mark.asyncio
async def test_update_payment_with_new_payment_methods():
    """Test updating payment to use newly added payment methods."""
    # Arrange
    fake_user = create_test_user()
    
    # Test updating to each new payment method
    new_payment_methods = [
        ("Debit Card", PaymentMethod.DEBIT_CARD),
        ("Wire Transfer", PaymentMethod.WIRE_TRANSFER),
        ("Direct Deposit", PaymentMethod.DIRECT_DEPOSIT),
        ("Interac e-Transfer", PaymentMethod.INTERAC_E_TRANSFER),
        ("Bank Draft", PaymentMethod.BANK_DRAFT),
        ("PayPal", PaymentMethod.PAYPAL),
        ("Internal Transfer", PaymentMethod.INTERNAL_TRANSFER)
    ]
    
    for idx, (method_value, method_enum) in enumerate(new_payment_methods, start=200):
        payment_id = idx
        update_data = {
            "payment_method": method_value
        }
        
        # Create response for each method update
        fake_response = PaymentResponse(
            id=payment_id,
            lease_id=123,
            tenant_id=456,
            amount=Decimal("1500.00"),
            payment_date=FIXED_DATETIME,
            payment_method=method_enum,
            status=PaymentStatus.PAID,
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name="Test Tenant",
            property_name="Test Property"
        )
        
        # Mock the service layer
        with patch("Backend.api.accounting.payments.router.service.update_payment", new=AsyncMock(return_value=fake_response)):
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
        
        # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["payment_method"] == method_value

@pytest.mark.asyncio
async def test_update_payment_reduction_exceeds_amount_validation():
    """Test that updating payment with reduction exceeding amount is rejected."""
    # Arrange
    fake_user = create_test_user()
    payment_id = 103
    
    # Test that reduction amount cannot exceed the payment amount
    update_data = {
        "amount": "1000.00",  # Payment amount
        "reduction_amount": "1200.00"  # Invalid: reduction ($1200) > amount ($1000)
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
        
        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("Reduction amount cannot be greater than payment amount" in str(error["msg"]) for error in error_detail)
