"""
Unit tests for the invoice CSV import service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.api.accounting.invoices.schemas import CSVImportRequest, CSVImportResult, CSVInvoiceData
from Backend.api.accounting.invoices.service import import_invoices_from_csv
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
        user_type=user_type,
        first_name="Test",
        last_name="User",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        email_verified=True
    )

def create_test_property(property_id=None, user_id=None, name="Test Property"):
    """Helper function to create a test property."""
    return Property(
        id=property_id or uuid4(),
        user_id=user_id or uuid4(),
        name=name,
        address="123 Test St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME
    )

def create_test_tenant(tenant_id=None, first_name="John", last_name="Doe"):
    """Helper function to create a test tenant."""
    return Tenant(
        id=tenant_id or uuid4(),
        first_name=first_name,
        last_name=last_name,
        email="john.doe@example.com",
        phone="555-1234",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME
    )

class TestInvoiceCSVImport:
    """Test cases for invoice CSV import functionality."""

    def test_csv_import_success_landlord(self):
        """Test successful CSV import for landlord user."""
        # Arrange
        user_id = uuid4()
        property_id = uuid4()
        tenant_id = uuid4()
        
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        test_property = create_test_property(property_id=property_id, user_id=user_id)
        test_tenant = create_test_tenant(tenant_id=tenant_id)
        
        mock_session = AsyncMock()
        
        # Mock the invoice creation
        mock_created_invoice = Invoice(
            id=12345,
            invoice_number="INV-001",
            amount=Decimal("1500.00"),
            description="Test Invoice",
            issue_date=FIXED_DATETIME,
            due_date=FIXED_DATETIME,
            status=PaymentStatus.PENDING,
            property_id=property_id,
            tenant_id=tenant_id,
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME
        )
        
        # CSV data
        csv_data = [
            CSVInvoiceData(
                invoice_number="INV-001",
                amount=Decimal("1500.00"),
                description="Test Invoice",
                issue_date="2024-06-01",
                due_date="2024-06-15",
                status="Pending",
                property_name="Test Property",
                tenant_name="John Doe"
            )
        ]
        
        import_request = CSVImportRequest(invoices=csv_data)
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with patch('Backend.api.accounting.invoices.service.import_invoices_from_csv') as mock_import:
            mock_import.return_value = CSVImportResult(
                total_rows=1,
                successful_imports=1,
                failed_imports=0,
                errors=[],
                created_invoice_ids=[mock_created_invoice.id]
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.post(
                "/api/accounting/invoices/import-csv",
                json={
                    "invoices": [
                        {
                            "invoice_number": "INV-001",
                            "amount": 1500.00,
                            "description": "Test Invoice",
                            "issue_date": "2024-06-01",
                            "due_date": "2024-06-15",
                            "status": "Pending",
                            "property_name": "Test Property",
                            "tenant_name": "John Doe"
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
            assert len(result["created_invoice_ids"]) == 1

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
            "/api/accounting/invoices/import-csv",
            json={"invoices": []},
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
        
        with patch('Backend.api.accounting.invoices.service.import_invoices_from_csv') as mock_import:
            mock_import.return_value = CSVImportResult(
                total_rows=2,
                successful_imports=1,
                failed_imports=1,
                errors=[
                    {
                        "row_number": 2,
                        "error_message": "Property 'Nonexistent Property' not found"
                    }
                ],
                created_invoice_ids=[67890]
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.post(
                "/api/accounting/invoices/import-csv",
                json={
                    "invoices": [
                        {
                            "invoice_number": "INV-001",
                            "amount": 1500.00,
                            "description": "Test Invoice",
                            "issue_date": "2024-06-01",
                            "due_date": "2024-06-15",
                            "status": "Pending",
                            "property_name": "Test Property",
                            "tenant_name": "John Doe"
                        },
                        {
                            "invoice_number": "INV-002",
                            "amount": 1200.00,
                            "description": "Test Invoice 2",
                            "issue_date": "2024-06-01",
                            "due_date": "2024-06-15",
                            "status": "Pending",
                            "property_name": "Nonexistent Property",
                            "tenant_name": "Jane Doe"
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
            assert "Property 'Nonexistent Property' not found" in result["errors"][0]["error_message"]

    def test_csv_import_empty_data(self):
        """Test CSV import with empty data."""
        # Arrange
        test_user = create_test_user(user_type=UserType.ADMIN)
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with patch('Backend.api.accounting.invoices.service.import_invoices_from_csv') as mock_import:
            mock_import.return_value = CSVImportResult(
                total_rows=0,
                successful_imports=0,
                failed_imports=0,
                errors=[],
                created_invoice_ids=[]
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.post(
                "/api/accounting/invoices/import-csv",
                json={"invoices": []},
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
            "/api/accounting/invoices/import-csv",
            json={
                "invoices": [
                    {
                        "invoice_number": "INV-001",
                        # Missing required amount field
                        "description": "Test Invoice"
                    }
                ]
            },
            headers={"Content-Type": "application/json"}
        )
        
        # Assert
        assert response.status_code == 422  # Validation error