"""
Unit tests for the invoice creation service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.api.accounting.invoices.schemas import InvoiceResponse, PropertyInfo, TenantInfo
from Backend.models.accounting.invoice import Invoice
from Backend.models.accounting.common import PaymentStatus
from Backend.models.user import User
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

@pytest.mark.asyncio
async def test_create_invoice_success():
    """Test successful invoice creation with all fields."""
    # Arrange
    fake_user = create_test_user()
    
    test_invoice_data = {
        "invoice_number": "INV-2024-001",
        "amount": "1500.00",
        "description": "June 2024 Rent",
        "issue_date": "2024-06-01T12:00:00Z",
        "due_date": "2024-06-15T12:00:00Z",
        "status": "Pending",
        "property_id": 123,
        "tenant_id": 456
    }
    
    # Create the response that service would return
    fake_response = InvoiceResponse(
        id=1,
        invoice_number="INV-2024-001",
        amount=Decimal("1500.00"),
        description="June 2024 Rent",
        issue_date=FIXED_DATETIME,
        due_date=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        status=PaymentStatus.PENDING,
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
    with patch("Backend.api.accounting.invoices.router.service.create_invoice", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/invoices", json=test_invoice_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 1
            assert data["invoice_number"] == "INV-2024-001"
            assert data["amount"] == "1500.00"
            assert data["description"] == "June 2024 Rent"
            assert data["status"] == "Pending"
            assert data["property"]["name"] == "Test Property"
            assert data["tenant"]["full_name"] == "John Doe"

@pytest.mark.asyncio
async def test_create_invoice_minimal_fields():
    """Test invoice creation with only required fields - supporting external system imports."""
    # Arrange
    fake_user = create_test_user()
    
    # Minimal data - only required fields
    test_invoice_data = {
        "invoice_number": "INV-2024-002",
        "amount": "1000.00",
        "description": "Service charge",
        "issue_date": "2024-06-01T12:00:00Z",
        "due_date": "2024-06-30T12:00:00Z"
        # No property_id or tenant_id - supporting imports from external systems
    }
    
    # Create response with defaults applied
    fake_response = InvoiceResponse(
        id=2,
        invoice_number="INV-2024-002",
        amount=Decimal("1000.00"),
        description="Service charge",
        issue_date=FIXED_DATETIME,
        due_date=datetime(2024, 6, 30, 12, 0, 0, tzinfo=timezone.utc),
        status=PaymentStatus.PENDING,  # Default status
        property_id=None,  # No property
        tenant_id=None,    # No tenant
        quickbooks_id=None,
        last_synced_at=None,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        property=None,
        tenant=None
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.invoices.router.service.create_invoice", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/invoices", json=test_invoice_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 2
            assert data["invoice_number"] == "INV-2024-002"
            assert data["amount"] == "1000.00"
            assert data["status"] == "Pending"  # Default
            assert data["property"] is None
            assert data["tenant"] is None

@pytest.mark.asyncio
async def test_create_invoice_tenant_forbidden():
    """Test that tenants cannot create invoices."""
    # Arrange
    fake_tenant_user = create_test_user(user_type=UserType.TENANT)
    
    test_invoice_data = {
        "invoice_number": "INV-2024-003",
        "amount": "1500.00",
        "description": "Rent invoice",
        "issue_date": "2024-06-01T12:00:00Z",
        "due_date": "2024-06-15T12:00:00Z",
        "property_id": 123,
        "tenant_id": 456
    }
    
    # Mock the service to raise forbidden exception
    with patch(
        "Backend.api.accounting.invoices.router.service.create_invoice",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Not authorized to create invoices"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_tenant_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/invoices", json=test_invoice_data)
    
    # Assert
            assert response.status_code == 403
            assert "Not authorized to create invoices" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_invoice_unauthorized_property():
    """Test invoice creation for property not owned by user."""
    # Arrange
    fake_user = create_test_user()
    
    test_invoice_data = {
        "invoice_number": "INV-2024-004",
        "amount": "1500.00",
        "description": "Rent for unauthorized property",
        "issue_date": "2024-06-01T12:00:00Z",
        "due_date": "2024-06-15T12:00:00Z",
        "property_id": 999,  # Property owned by another landlord
        "tenant_id": 456
    }
    
    # Mock the service to raise forbidden exception
    with patch(
        "Backend.api.accounting.invoices.router.service.create_invoice",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Not authorized for this property"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/invoices", json=test_invoice_data)
    
    # Assert
            assert response.status_code == 403
            assert "Not authorized for this property" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_invoice_validation_errors():
    """Test validation errors for invalid invoice data."""
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
            {
                "invoice_number": "INV-001",
                "amount": "not_a_number",
                "description": "Test",
                "issue_date": "2024-06-01T12:00:00Z",
                "due_date": "2024-06-15T12:00:00Z"
            },
            "Input should be a valid decimal"
        ),
        # Negative amount
        (
            {
                "invoice_number": "INV-001",
                "amount": "-100.00",
                "description": "Test",
                "issue_date": "2024-06-01T12:00:00Z",
                "due_date": "2024-06-15T12:00:00Z"
            },
            "Amount must be greater than 0"
        ),
        # Invalid status
        (
            {
                "invoice_number": "INV-001",
                "amount": "100.00",
                "description": "Test",
                "issue_date": "2024-06-01T12:00:00Z",
                "due_date": "2024-06-15T12:00:00Z",
                "status": "INVALID_STATUS"
            },
            "Input should be"
        ),
        # Invalid date format
        (
            {
                "invoice_number": "INV-001",
                "amount": "100.00",
                "description": "Test",
                "issue_date": "not-a-date",
                "due_date": "2024-06-15T12:00:00Z"
            },
            "Input should be a valid datetime"
        ),
    ]
    
    with TestClientWithHost(app) as client:
        for test_data, expected_error in invalid_test_cases:
            # Act
            response = client.post("/api/accounting/invoices", json=test_data)
            
            # Assert
            assert response.status_code == 422
            error_detail = response.json()["detail"]
            assert any(expected_error in str(error) for error in error_detail)

@pytest.mark.asyncio
async def test_create_invoice_due_date_before_issue_date():
    """Test that due date cannot be before issue date."""
    # Arrange
    fake_user = create_test_user()
    
    test_invoice_data = {
        "invoice_number": "INV-2024-005",
        "amount": "1500.00",
        "description": "Invalid date range",
        "issue_date": "2024-06-15T12:00:00Z",
        "due_date": "2024-06-01T12:00:00Z",  # Due date before issue date
        "property_id": 123
    }
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/accounting/invoices", json=test_invoice_data)

    # Assert - Pydantic validation returns 422, not 400
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("Due date cannot be earlier than issue date" in str(error) for error in error_detail)

@pytest.mark.asyncio
async def test_create_invoice_admin_user():
    """Test that admin users can create invoices for any property."""
    # Arrange
    fake_admin_user = create_test_user(user_type=UserType.ADMIN)
    fake_admin_user.is_admin = True
    
    test_invoice_data = {
        "invoice_number": "INV-ADMIN-001",
        "amount": "2000.00",
        "description": "Admin created invoice",
        "issue_date": "2024-06-01T12:00:00Z",
        "due_date": "2024-06-30T12:00:00Z",
        "property_id": 999,  # Any property ID
        "tenant_id": 888
    }
    
    # Create the response
    fake_response = InvoiceResponse(
        id=10,
        invoice_number="INV-ADMIN-001",
        amount=Decimal("2000.00"),
        description="Admin created invoice",
        issue_date=FIXED_DATETIME,
        due_date=datetime(2024, 6, 30, 12, 0, 0, tzinfo=timezone.utc),
        status=PaymentStatus.PENDING,
        property_id=999,
        tenant_id=888,
        quickbooks_id=None,
        last_synced_at=None,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        property=PropertyInfo(id=999, name="Any Property"),
        tenant=TenantInfo(id=888, full_name="Any Tenant")
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.invoices.router.service.create_invoice", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/invoices", json=test_invoice_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["description"] == "Admin created invoice"
            assert data["property_id"] == 999

@pytest.mark.asyncio
async def test_create_invoice_with_quickbooks_sync():
    """Test invoice creation with QuickBooks integration data."""
    # Arrange
    fake_user = create_test_user()
    
    test_invoice_data = {
        "invoice_number": "QB-INV-12345",
        "amount": "1500.00",
        "description": "QuickBooks synced invoice",
        "issue_date": "2024-06-01T12:00:00Z",
        "due_date": "2024-06-15T12:00:00Z",
        "status": "Paid",
        "property_id": 123,
        "tenant_id": 456
    }
    
    # Create response simulating QuickBooks sync
    fake_response = InvoiceResponse(
        id=20,
        invoice_number="QB-INV-12345",
        amount=Decimal("1500.00"),
        description="QuickBooks synced invoice",
        issue_date=FIXED_DATETIME,
        due_date=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        status=PaymentStatus.PAID,
        property_id=123,
        tenant_id=456,
        quickbooks_id="QB-12345",  # QuickBooks ID set
        last_synced_at=FIXED_DATETIME,  # Sync timestamp
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        property=PropertyInfo(id=123, name="Test Property"),
        tenant=TenantInfo(id=456, full_name="John Doe")
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.invoices.router.service.create_invoice", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/invoices", json=test_invoice_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["quickbooks_id"] == "QB-12345"
            assert data["last_synced_at"] is not None
            assert data["status"] == "Paid"

@pytest.mark.asyncio
async def test_create_invoice_database_error():
    """Test error handling for database commit failure."""
    # Arrange
    fake_user = create_test_user()
    
    test_invoice_data = {
        "invoice_number": "INV-2024-ERR",
        "amount": "1500.00",
        "description": "Database error test",
        "issue_date": "2024-06-01T12:00:00Z",
        "due_date": "2024-06-15T12:00:00Z"
    }
    
    # Mock the service to raise internal server error
    with patch(
        "Backend.api.accounting.invoices.router.service.create_invoice",
        new=AsyncMock(side_effect=HTTPException(status_code=500, detail="Failed to create invoice."))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/invoices", json=test_invoice_data)
    
    # Assert
            assert response.status_code == 500
            assert "Failed to create invoice" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_invoice_duplicate_invoice_number():
    """Test invoice creation with duplicate invoice number."""
    # Arrange
    fake_user = create_test_user()
    
    test_invoice_data = {
        "invoice_number": "INV-DUP-001",  # Duplicate invoice number
        "amount": "1500.00",
        "description": "Duplicate invoice number test",
        "issue_date": "2024-06-01T12:00:00Z",
        "due_date": "2024-06-15T12:00:00Z",
        "property_id": 123
    }
    
    # Mock the service to raise conflict exception
    with patch(
        "Backend.api.accounting.invoices.router.service.create_invoice",
        new=AsyncMock(side_effect=HTTPException(status_code=409, detail="Invoice with number INV-DUP-001 already exists"))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/invoices", json=test_invoice_data)
    
    # Assert
            assert response.status_code == 409
            assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_invoice_with_property_inference():
    """Test invoice creation with automatic property inference from tenant."""
    # Arrange
    fake_user = create_test_user()
    
    test_invoice_data = {
        "invoice_number": "INV-2024-INFER",
        "amount": "1500.00",
        "description": "Invoice with inferred property",
        "issue_date": "2024-06-01T12:00:00Z",
        "due_date": "2024-06-15T12:00:00Z",
        "tenant_id": 789  # Only tenant_id provided, property will be inferred
    }
    
    # Create response with inferred property
    fake_response = InvoiceResponse(
        id=30,
        invoice_number="INV-2024-INFER",
        amount=Decimal("1500.00"),
        description="Invoice with inferred property",
        issue_date=FIXED_DATETIME,
        due_date=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        status=PaymentStatus.PENDING,
        property_id=123,  # Property was inferred
        tenant_id=789,
        quickbooks_id=None,
        last_synced_at=None,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        property=PropertyInfo(id=123, name="Inferred Property"),
        tenant=TenantInfo(id=789, full_name="Test Tenant")
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.invoices.router.service.create_invoice", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/accounting/invoices", json=test_invoice_data)
    
    # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["property_id"] == 123  # Property was inferred
            assert data["property"]["name"] == "Inferred Property"
            assert data["tenant_id"] == 789