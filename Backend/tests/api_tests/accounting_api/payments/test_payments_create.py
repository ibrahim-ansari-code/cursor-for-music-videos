"""
Unit tests for the payments creation service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.api.accounting.payments.schemas import PaymentResponse
from Backend.models.accounting.payment import Payment, PaymentMethod
from Backend.models.accounting.common import PaymentStatus
from Backend.models.user import User
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.tenant import Tenant
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

@pytest.fixture(autouse=True)
def mock_recaptcha_for_payment_tests():
    """Mock reCAPTCHA verification for payment tests."""
    with patch('Backend.utils.recaptcha.settings') as mock_settings:
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = ""  # This will cause bypass
        yield mock_settings

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

def create_mock_property(property_id=1, user_id=None, **kwargs):
    """Helper function to create a mock property."""
    mock_property = MagicMock(spec=Property)
    mock_property.id = property_id
    mock_property.name = kwargs.get('name', 'Test Property')
    mock_property.user_id = user_id or uuid4()
    mock_property.created_at = kwargs.get('created_at', FIXED_DATETIME)
    mock_property.updated_at = kwargs.get('updated_at', FIXED_DATETIME)
    return mock_property

def create_mock_tenant(tenant_id=1, **kwargs):
    """Helper function to create a mock tenant."""
    mock_tenant = MagicMock(spec=Tenant)
    mock_tenant.id = tenant_id
    mock_tenant.first_name = kwargs.get('first_name', 'John')
    mock_tenant.last_name = kwargs.get('last_name', 'Doe')
    mock_tenant.email = kwargs.get('email', 'tenant@example.com')
    mock_tenant.created_at = kwargs.get('created_at', FIXED_DATETIME)
    mock_tenant.updated_at = kwargs.get('updated_at', FIXED_DATETIME)
    return mock_tenant

def create_mock_lease(lease_id=1, property_id=1, tenant_id=1, user_property=None, **kwargs):
    """Helper function to create a mock lease."""
    mock_lease = MagicMock(spec=Lease)
    mock_lease.id = lease_id
    mock_lease.property_id = property_id
    mock_lease.tenant_id = tenant_id
    mock_lease.monthly_rent = kwargs.get('monthly_rent', Decimal('1500.00'))
    mock_lease.status = kwargs.get('status', LeaseStatus.ACTIVE)
    mock_lease.property = user_property or create_mock_property(property_id)
    mock_lease.tenant = kwargs.get('tenant', create_mock_tenant(tenant_id))
    mock_lease.created_at = kwargs.get('created_at', FIXED_DATETIME)
    mock_lease.updated_at = kwargs.get('updated_at', FIXED_DATETIME)
    return mock_lease

# =============================================================================
# CREATE PAYMENT TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_create_payment_success():
    """Test successful payment creation with all fields."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "1500.00",
        "payment_date": "2024-06-01T12:00:00Z",
        "payment_method": "Bank Transfer",
        "status": "Paid",
        "transaction_reference": "TXN-001",
        "description": "June rent payment",
        "tenant_name": "John Doe",
        "receipt_url": "https://example.com/receipt.pdf"
    }
    
    # Create the response that service would return
    fake_response = PaymentResponse(
        id=1,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("1500.00"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.BANK_TRANSFER,
        status=PaymentStatus.PAID,
        transaction_reference="TXN-001",
        description="June rent payment",
        receipt_url="https://example.com/receipt.pdf",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="John Doe",
        property_name="Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
            
            # Debug output
            if response.status_code != 201:
                print(f"Response status: {response.status_code}")
                print(f"Response body: {response.text}")
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 1
            assert data["lease_id"] == 123
            assert data["amount"] == "1500.00"
            assert data["payment_method"] == "Bank Transfer"
            assert data["status"] == "Paid"
            assert data["transaction_reference"] == "TXN-001"
            assert data["tenant_name"] == "John Doe"
            assert data["property_name"] == "Test Property"

@pytest.mark.asyncio
async def test_create_payment_minimal_fields():
    """Test payment creation with only required fields."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "1000.00"
    }
    
    # Create the response with defaults applied
    fake_response = PaymentResponse(
        id=2,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("1000.00"),
        payment_date=FIXED_DATETIME,  # Default to current time
        payment_method=PaymentMethod.OTHER,  # Default
        status=PaymentStatus.PENDING,  # Default
        transaction_reference=None,
        description=None,
        receipt_url=None,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="Jane Smith",
        property_name="Another Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 2
            assert data["lease_id"] == 123
            assert data["amount"] == "1000.00"
            assert data["payment_method"] == "Other"  # Default
            assert data["status"] == "Pending"  # Default
            assert data["transaction_reference"] is None
            assert data["description"] is None

@pytest.mark.asyncio
async def test_create_payment_tenant_forbidden():
    """Test that tenants cannot create payments."""
    # Arrange
    fake_tenant_user = create_test_user(user_type=UserType.TENANT)
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "1500.00"
    }
    
    # Mock the service to raise forbidden exception
    with patch(
        "Backend.api.accounting.payments.router.service.create_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Tenants cannot directly create payment records."))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_tenant_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 403
            assert "Tenants cannot directly create payment records" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_payment_invalid_lease():
    """Test payment creation with non-existent lease."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 999,  # Non-existent lease
        "amount": "1500.00"
    }
    
    # Mock the service to raise not found exception
    with patch(
        "Backend.api.accounting.payments.router.service.create_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Lease 999 not found"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 404
            assert "Lease 999 not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_payment_unauthorized_lease():
    """Test payment creation for lease not owned by user."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 456,  # Lease owned by another landlord
        "amount": "1500.00"
    }
    
    # Mock the service to raise forbidden exception
    with patch(
        "Backend.api.accounting.payments.router.service.create_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Not authorized to access this lease"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 403
            assert "Not authorized to access this lease" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_payment_various_statuses():
    """Test payment creation with different payment statuses."""
    # Arrange
    fake_user = create_test_user()
    
    # Map of status values to enum members
    status_map = {
        "Pending": PaymentStatus.PENDING,
        "Paid": PaymentStatus.PAID,
        "Overdue": PaymentStatus.OVERDUE,
        "Cancelled": PaymentStatus.CANCELLED,
        "Refunded": PaymentStatus.REFUNDED,
        "Partial": PaymentStatus.PARTIAL
    }
    
    for idx, (status_value, status_enum) in enumerate(status_map.items(), start=1):
        test_payment_data = {
            "lease_id": 123,
            "amount": "1500.00",
            "status": status_value
        }
        
        # Create response for each status
        fake_response = PaymentResponse(
            id=idx,
            lease_id=123,
            tenant_id=456,
            amount=Decimal("1500.00"),
            payment_date=FIXED_DATETIME,
            payment_method=PaymentMethod.OTHER,
            status=status_enum,
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name="Test Tenant",
            property_name="Test Property"
        )
        
        # Mock the service layer
        with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.post("/api/accounting/payments", json=test_payment_data)
        
        # Assert
                assert response.status_code == 201
                data = response.json()
                assert data["status"] == status_value

@pytest.mark.asyncio
async def test_create_payment_various_payment_methods():
    """Test payment creation with different payment methods."""
    # Arrange
    fake_user = create_test_user()
    
    # Map of method values to enum members
    method_map = {
        "Bank Transfer": PaymentMethod.BANK_TRANSFER,
        "Credit Card": PaymentMethod.CREDIT_CARD,
        "Cash": PaymentMethod.CASH,
        "Check": PaymentMethod.CHECK,
        "Other": PaymentMethod.OTHER
    }
    
    for idx, (method_value, method_enum) in enumerate(method_map.items(), start=1):
        test_payment_data = {
            "lease_id": 123,
            "amount": "1500.00",
            "payment_method": method_value
        }
        
        # Create response for each method
        fake_response = PaymentResponse(
            id=idx,
            lease_id=123,
            tenant_id=456,
            amount=Decimal("1500.00"),
            payment_date=FIXED_DATETIME,
            payment_method=method_enum,
            status=PaymentStatus.PENDING,
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name="Test Tenant",
            property_name="Test Property"
        )
        
        # Mock the service layer
        with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.post("/api/accounting/payments", json=test_payment_data)
        
        # Assert
                assert response.status_code == 201
                data = response.json()
                assert data["payment_method"] == method_value

@pytest.mark.asyncio
async def test_create_payment_validation_errors():
    """Test validation errors for invalid payment data."""
    # Arrange
    fake_user = create_test_user()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    invalid_test_cases = [
        # Missing required fields
        (
            {},
            "Field required"
        ),
        # Invalid amount
        (
            {"lease_id": 123, "amount": "not_a_number"},
            "Input should be a valid decimal"
        ),
        # Negative amount
        (
            {"lease_id": 123, "amount": "-100.00"},
            "Amount must be positive"
        ),
        # Invalid status
        (
            {"lease_id": 123, "amount": "100.00", "status": "INVALID_STATUS"},
            "Input should be"
        ),
        # Invalid payment method
        (
            {"lease_id": 123, "amount": "100.00", "payment_method": "BITCOIN"},
            "Input should be"
        ),
        # Invalid date format
        (
            {"lease_id": 123, "amount": "100.00", "payment_date": "not-a-date"},
            "Input should be a valid datetime"
        ),
    ]
    
    with TestClientWithHost(app) as client:
        for test_data, expected_error in invalid_test_cases:
            # Act
            response = client.post("/api/accounting/payments", json=test_data)
            
            # Assert
            assert response.status_code == 422
            error_detail = response.json()["detail"]
            assert any(expected_error in str(error) for error in error_detail)

@pytest.mark.asyncio
async def test_create_payment_database_error():
    """Test error handling for database commit failure."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "1500.00"
    }
    
    # Mock the service to raise internal server error
    with patch(
        "Backend.api.accounting.payments.router.service.create_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=500, detail="Failed to create payment."))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 500
            assert "Failed to create payment" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_payment_with_quickbooks_integration():
    """Test payment creation with QuickBooks integration (future feature)."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "1500.00",
        "payment_method": "Bank Transfer",
        "transaction_reference": "QB-12345"  # QuickBooks reference
    }
    
    # Create response simulating QuickBooks sync
    fake_response = PaymentResponse(
        id=10,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("1500.00"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.BANK_TRANSFER,
        status=PaymentStatus.PAID,
        transaction_reference="QB-12345",
        description="June rent payment",
        receipt_url=None,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="John Doe",
        property_name="Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["transaction_reference"] == "QB-12345"

@pytest.mark.asyncio
async def test_create_payment_admin_user():
    """Test that admin users can create payments."""
    # Arrange
    fake_admin_user = create_test_user(user_type=UserType.ADMIN)
    fake_admin_user.is_admin = True
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "2000.00",
        "description": "Admin created payment"
    }
    
    # Create the response
    fake_response = PaymentResponse(
        id=11,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("2000.00"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.OTHER,
        status=PaymentStatus.PENDING,
        description="Admin created payment",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="Admin Test Tenant",
        property_name="Admin Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["description"] == "Admin created payment"

@pytest.mark.asyncio
async def test_create_payment_large_amount():
    """Test payment creation with large amount."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "999999.99"  # Maximum reasonable amount
    }
    
    # Create response with large amount
    fake_response = PaymentResponse(
        id=10,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("999999.99"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.OTHER,
        status=PaymentStatus.PENDING,
        description="Large payment test",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="Test Tenant",
        property_name="Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["amount"] == "999999.99"

@pytest.mark.asyncio
async def test_create_payment_decimal_precision_validation():
    """Test payment creation with amounts having more than 2 decimal places."""
    # Arrange
    fake_user = create_test_user()
    
    # Test with 3 decimal places
    test_payment_data = {
        "lease_id": 123,
        "amount": "1500.123"  # 3 decimal places
    }
    
    # Create a mock response - the service would handle decimal validation
    fake_response = PaymentResponse(
        id=11,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("1500.12"),  # Rounded to 2 decimal places
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.OTHER,
        status=PaymentStatus.PENDING,
        description="Payment with precision test",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="Test Tenant",
        property_name="Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
            
    # Assert
            # Should succeed and return rounded amount
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["amount"] == "1500.12"  # Rounded to 2 decimal places

@pytest.mark.asyncio
async def test_create_payment_with_receipt_url():
    """Test payment creation with receipt URL."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "1500.00",
        "receipt_url": "https://storage.example.com/receipts/receipt-123.pdf",
        "description": "Payment with receipt"
    }
    
    # Create the response
    fake_response = PaymentResponse(
        id=13,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("1500.00"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.OTHER,
        status=PaymentStatus.PAID,
        description="Payment with receipt",
        receipt_url="https://storage.example.com/receipts/receipt-123.pdf",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="Test Tenant",
        property_name="Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["receipt_url"] == "https://storage.example.com/receipts/receipt-123.pdf"
            assert data["description"] == "Payment with receipt"

@pytest.mark.asyncio
async def test_create_payment_duplicate_transaction_reference():
    """Test payment creation with duplicate transaction reference."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "1500.00",
        "transaction_reference": "TXN-DUP-001"  # Duplicate reference
    }
    
    # Mock the service to raise conflict exception
    with patch(
        "Backend.api.accounting.payments.router.service.create_payment",
        new=AsyncMock(side_effect=HTTPException(status_code=409, detail="Payment with transaction reference TXN-DUP-001 already exists"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 409
            assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_payment_with_reduction():
    """Test payment creation with reduction amount and reason."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "1400.00",  # $1500 rent - $100 reduction
        "payment_date": "2024-06-01T12:00:00Z",
        "payment_method": "Bank Transfer",
        "status": "Paid",
        "reduction_amount": "100.00",
        "reduction_reason": "Tenant referred a friend"
    }
    
    # Create the response with reduction fields
    fake_response = PaymentResponse(
        id=100,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("1400.00"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.BANK_TRANSFER,
        status=PaymentStatus.PAID,
        reduction_amount=Decimal("100.00"),
        reduction_reason="Tenant referred a friend",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="John Doe",
        property_name="Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 100
            assert data["amount"] == "1400.00"
            assert data["reduction_amount"] == "100.00"
            assert data["reduction_reason"] == "Tenant referred a friend"

@pytest.mark.asyncio
async def test_create_payment_with_zero_reduction():
    """Test payment creation with zero reduction amount."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "1500.00",
        "reduction_amount": "0.00",
        "reduction_reason": ""  # Should be allowed when reduction is 0
    }
    
    # Create the response
    fake_response = PaymentResponse(
        id=101,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("1500.00"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.OTHER,
        status=PaymentStatus.PENDING,
        reduction_amount=Decimal("0.00"),
        reduction_reason="",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="John Doe",
        property_name="Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["reduction_amount"] == "0.00"

@pytest.mark.asyncio
async def test_create_payment_negative_reduction_validation():
    """Test that negative reduction amount is rejected."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "1500.00",
        "reduction_amount": "-100.00",  # Negative reduction
        "reduction_reason": "Invalid negative reduction"
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/accounting/payments", json=test_payment_data)
        
        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("Reduction amount must be zero or positive" in str(error["msg"]) for error in error_detail)

@pytest.mark.asyncio
async def test_create_payment_with_new_payment_methods():
    """Test payment creation with newly added payment methods."""
    # Arrange
    fake_user = create_test_user()
    
    # Test all new payment methods
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
        test_payment_data = {
            "lease_id": 123,
            "amount": "1500.00",
            "payment_method": method_value
        }
        
        # Create response for each new method
        fake_response = PaymentResponse(
            id=idx,
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
        with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.post("/api/accounting/payments", json=test_payment_data)
        
        # Assert
                assert response.status_code == 201
                data = response.json()
                assert data["payment_method"] == method_value

@pytest.mark.asyncio
async def test_create_payment_partial_with_reduction():
    """Test creating a partial payment with reduction applied."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "900.00",  # Partial payment after $100 reduction on $1500 rent
        "status": "Partial",
        "reduction_amount": "100.00",
        "reduction_reason": "Holiday goodwill discount",
        "description": "Partial payment for December with holiday discount"
    }
    
    # Create the response
    fake_response = PaymentResponse(
        id=300,
        lease_id=123,
        tenant_id=456,
        amount=Decimal("900.00"),
        payment_date=FIXED_DATETIME,
        payment_method=PaymentMethod.OTHER,
        status=PaymentStatus.PARTIAL,
        reduction_amount=Decimal("100.00"),
        reduction_reason="Holiday goodwill discount",
        description="Partial payment for December with holiday discount",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        tenant_name="John Doe",
        property_name="Test Property"
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.create_payment", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/payments", json=test_payment_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["amount"] == "900.00"
            assert data["status"] == "Partial"
            assert data["reduction_amount"] == "100.00"
            assert data["reduction_reason"] == "Holiday goodwill discount"

@pytest.mark.asyncio
async def test_create_payment_reduction_exceeds_amount_validation():
    """Test that reduction amount cannot exceed the payment amount."""
    # Arrange
    fake_user = create_test_user()
    
    test_payment_data = {
        "lease_id": 123,
        "amount": "1000.00",
        "reduction_amount": "1500.00",  # Reduction exceeds payment amount
        "reduction_reason": "Invalid excessive reduction"
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/accounting/payments", json=test_payment_data)
        
        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("Reduction amount cannot be greater than payment amount" in str(error["msg"]) for error in error_detail)