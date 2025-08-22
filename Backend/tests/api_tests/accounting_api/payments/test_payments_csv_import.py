"""
Unit tests for the payment CSV import service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import status

from Backend.api.app import app
from Backend.api.accounting.payments.schemas import CSVPaymentImportResult, CSVImportError
from Backend.models.accounting.payment import Payment, PaymentMethod
from Backend.models.accounting.common import PaymentStatus
from Backend.models.user import User
from Backend.models.property import Property, PropertyType
from Backend.models.tenant import Tenant
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.enums import UserType, PropertyStatus
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
        user_type=user_type,
        first_name="Test",
        last_name="User",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        is_email_verified=True
    )

def create_test_property(property_id=None, user_id=None, name="Test Property"):
    """Helper function to create a test property."""
    return Property(
        id=property_id or 1,
        user_id=user_id or uuid4(),
        name=name,
        address="123 Test St",
        city="Test City",
        province="Test Province",
        postal_code="12345",
        property_type=PropertyType.RESIDENTIAL,
        status=PropertyStatus.ACTIVE,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME
    )

def create_test_tenant(tenant_id=None, first_name="John", last_name="Doe", landlord_id=None):
    """Helper function to create a test tenant."""
    return Tenant(
        id=tenant_id or 1,
        landlord_id=landlord_id or uuid4(),
        first_name=first_name,
        last_name=last_name,
        email="john.doe@example.com",
        phone="555-1234",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME
    )

def create_test_lease(lease_id=None, property_id=None, tenant_id=None):
    """Helper function to create a test lease."""
    return Lease(
        id=lease_id or 1,
        property_id=property_id or 1,
        tenant_id=tenant_id or 1,
        monthly_rent=Decimal("1500.00"),
        security_deposit=Decimal("1500.00"),
        status=LeaseStatus.ACTIVE,
        start_date=FIXED_DATETIME.date(),
        end_date=FIXED_DATETIME.date(),
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME
    )

class TestPaymentCSVImport:
    """Test cases for payment CSV import functionality."""

    def test_csv_import_success_landlord(self):
        """Test successful CSV import for landlord user."""
        # Arrange
        user_id = uuid4()
        property_id = uuid4()
        tenant_id = uuid4()
        lease_id = uuid4()
        
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        test_property = create_test_property(property_id=property_id, user_id=user_id)
        test_tenant = create_test_tenant(tenant_id=tenant_id)
        test_lease = create_test_lease(lease_id=lease_id, property_id=property_id, tenant_id=tenant_id)
        
        mock_session = AsyncMock()
        
        # Mock the payment creation
        mock_created_payment = Payment(
            id=1,
            lease_id=1,
            amount=Decimal("1500.00"),
            payment_date=FIXED_DATETIME,
            payment_method=PaymentMethod.BANK_TRANSFER,
            status=PaymentStatus.PAID,
            description="Monthly rent payment",
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME
        )
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with patch('Backend.api.accounting.payments.service.import_payments_from_csv') as mock_import:
            mock_import.return_value = CSVPaymentImportResult(
                total_rows=1,
                successful_imports=1,
                failed_imports=0,
                errors=[],
                created_payment_ids=[1]
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.post(
                "/api/accounting/payments/import-csv",
                json={
                    "payments": [
                        {
                            "amount": 1500.00,
                            "payment_date": "2024-06-01",
                            "tenant_name": "John Doe",
                            "property_name": "Test Property",
                            "payment_method": "Bank Transfer",
                            "status": "Paid",
                            "description": "Monthly rent payment"
                        }
                    ]
                },
                headers={"Content-Type": "application/json"}
            )
            
            # Assert
            assert response.status_code == 200
            result = response.json()
            assert result["total_rows"] == 1
            assert result["successful_imports"] == 1
            assert result["failed_imports"] == 0
            assert len(result["errors"]) == 0
            assert len(result["created_payment_ids"]) == 1

    def test_csv_import_unauthorized_tenant(self):
        """Test CSV import fails for tenant user."""
        # Arrange
        test_user = create_test_user(user_type=UserType.TENANT)
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.post(
            "/api/accounting/payments/import-csv",
            json={"payments": []},
            headers={"Content-Type": "application/json"}
        )
        
        # Assert
        assert response.status_code == 403

    def test_csv_import_with_errors(self):
        """Test CSV import with some failed rows."""
        # Arrange
        user_id = uuid4()
        test_user = create_test_user(user_id=user_id, user_type=UserType.ADMIN)
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with patch('Backend.api.accounting.payments.service.import_payments_from_csv') as mock_import:
            mock_import.return_value = CSVPaymentImportResult(
                total_rows=2,
                successful_imports=1,
                failed_imports=1,
                errors=[
                    CSVImportError(
                        row_number=2,
                        error_message="Tenant 'Nonexistent Tenant' not found or not in active lease"
                    )
                ],
                created_payment_ids=[67890]
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.post(
                "/api/accounting/payments/import-csv",
                json={
                    "payments": [
                        {
                            "amount": 1500.00,
                            "payment_date": "2024-06-01",
                            "tenant_name": "John Doe",
                            "property_name": "Test Property",
                            "payment_method": "Bank Transfer",
                            "status": "Paid",
                            "description": "Monthly rent payment"
                        },
                        {
                            "amount": 1200.00,
                            "payment_date": "2024-06-01",
                            "tenant_name": "Nonexistent Tenant",
                            "property_name": "Test Property",
                            "payment_method": "Credit Card",
                            "status": "Pending",
                            "description": "Payment"
                        }
                    ]
                },
                headers={"Content-Type": "application/json"}
            )
            
            # Assert
            assert response.status_code == 200
            result = response.json()
            assert result["total_rows"] == 2
            assert result["successful_imports"] == 1
            assert result["failed_imports"] == 1
            assert len(result["errors"]) == 1
            assert result["errors"][0]["row_number"] == 2
            assert "Tenant 'Nonexistent Tenant' not found" in result["errors"][0]["error_message"]

    def test_csv_import_empty_data(self):
        """Test CSV import with empty data."""
        # Arrange
        test_user = create_test_user(user_type=UserType.ADMIN)
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with patch('Backend.api.accounting.payments.service.import_payments_from_csv') as mock_import:
            mock_import.return_value = CSVPaymentImportResult(
                total_rows=0,
                successful_imports=0,
                failed_imports=0,
                errors=[],
                created_payment_ids=[]
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.post(
                "/api/accounting/payments/import-csv",
                json={"payments": []},
                headers={"Content-Type": "application/json"}
            )
            
            # Assert
            assert response.status_code == 200
            result = response.json()
            assert result["total_rows"] == 0
            assert result["successful_imports"] == 0
            assert result["failed_imports"] == 0
            assert len(result["errors"]) == 0

    def test_csv_import_invalid_schema(self):
        """Test CSV import with invalid request schema."""
        # Arrange
        test_user = create_test_user(user_type=UserType.ADMIN)
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        client = TestClientWithHost(app)
        
        # Act - missing required fields
        response = client.post(
            "/api/accounting/payments/import-csv",
            json={
                "payments": [
                    {
                        # Missing required amount field
                        "payment_date": "2024-06-01",
                        "description": "Test Payment"
                    }
                ]
            },
            headers={"Content-Type": "application/json"}
        )
        
        # Assert
        assert response.status_code == 422  # Validation error

    def test_csv_import_with_reduction_amount(self):
        """Test CSV import with reduction amounts."""
        # Arrange
        user_id = uuid4()
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with patch('Backend.api.accounting.payments.service.import_payments_from_csv') as mock_import:
            mock_import.return_value = CSVPaymentImportResult(
                total_rows=1,
                successful_imports=1,
                failed_imports=0,
                errors=[],
                created_payment_ids=[67890]
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.post(
                "/api/accounting/payments/import-csv",
                json={
                    "payments": [
                        {
                            "amount": 1500.00,
                            "payment_date": "2024-06-01",
                            "tenant_name": "John Doe",
                            "property_name": "Test Property",
                            "payment_method": "Bank Transfer",
                            "status": "Paid",
                            "description": "Monthly rent payment",
                            "reduction_amount": 100.00,
                            "reduction_reason": "Early payment discount"
                        }
                    ]
                },
                headers={"Content-Type": "application/json"}
            )
            
            # Assert
            assert response.status_code == 200
            result = response.json()
            assert result["total_rows"] == 1
            assert result["successful_imports"] == 1