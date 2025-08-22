"""
Unit tests for the expense CSV import service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.api.accounting.expenses.schemas import CSVExpenseImportResult, CSVExpenseData, CSVImportError
from Backend.models.accounting.expense import Expense
from Backend.models.accounting.payment import PaymentMethod
from Backend.models.user import User
from Backend.models.property import Property, PropertyType
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

class TestExpenseCSVImport:
    """Test cases for expense CSV import functionality."""

    def test_csv_import_success_landlord(self):
        """Test successful CSV import for landlord user."""
        # Arrange
        user_id = uuid4()
        property_id = uuid4()
        
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        # test_property removed - not used in this test
        
        mock_session = AsyncMock()
        
        # Mock the expense creation
        mock_created_expense = Expense(
            id=1,
            category="Maintenance",
            description="HVAC repair",
            expense_date=FIXED_DATETIME,
            subtotal_amount=Decimal("500.00"),
            total_tax_amount=Decimal("50.00"),
            payment_method=PaymentMethod.CREDIT_CARD,
            property_id=1,
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME
        )
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with patch('Backend.api.accounting.expenses.service.import_expenses_from_csv') as mock_import:
            mock_import.return_value = CSVExpenseImportResult(
                total_rows=1,
                successful_imports=1,
                failed_imports=0,
                errors=[],
                created_expense_ids=[1]
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.post(
                "/api/accounting/expenses/import-csv",
                json={
                    "expenses": [
                        {
                            "category": "Maintenance",
                            "description": "HVAC repair",
                            "expense_date": "2024-06-01",
                            "subtotal_amount": 500.00,
                            "total_tax_amount": 50.00,
                            "payment_method": "Credit Card",
                            "property_name": "Test Property"
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
            assert len(result["created_expense_ids"]) == 1

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
            "/api/accounting/expenses/import-csv",
            json={"expenses": []},
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
        
        with patch('Backend.api.accounting.expenses.service.import_expenses_from_csv') as mock_import:
            mock_import.return_value = CSVExpenseImportResult(
                total_rows=2,
                successful_imports=1,
                failed_imports=1,
                errors=[
                    CSVImportError(
                        row_number=2,
                        error_message="Property 'Nonexistent Property' not found"
                    )
                ],
                created_expense_ids=[67890]
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.post(
                "/api/accounting/expenses/import-csv",
                json={
                    "expenses": [
                        {
                            "category": "Maintenance",
                            "description": "HVAC repair",
                            "expense_date": "2024-06-01",
                            "subtotal_amount": 500.00,
                            "total_tax_amount": 50.00,
                            "payment_method": "Credit Card",
                            "property_name": "Test Property"
                        },
                        {
                            "category": "Utilities",
                            "description": "Electric bill",
                            "expense_date": "2024-06-01",
                            "subtotal_amount": 200.00,
                            "payment_method": "Bank Transfer",
                            "property_name": "Nonexistent Property"
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
        
        with patch('Backend.api.accounting.expenses.service.import_expenses_from_csv') as mock_import:
            mock_import.return_value = CSVExpenseImportResult(
                total_rows=0,
                successful_imports=0,
                failed_imports=0,
                errors=[],
                created_expense_ids=[]
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.post(
                "/api/accounting/expenses/import-csv",
                json={"expenses": []},
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
            "/api/accounting/expenses/import-csv",
            json={
                "expenses": [
                    {
                        "category": "Maintenance",
                        # Missing required subtotal_amount field
                        "description": "Test Expense"
                    }
                ]
            },
            headers={"Content-Type": "application/json"}
        )
        
        # Assert
        assert response.status_code == 422  # Validation error

    def test_csv_import_landlord_single_property(self):
        """Test CSV import for landlord with single property (auto-assignment)."""
        # Arrange
        user_id = uuid4()
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with patch('Backend.api.accounting.expenses.service.import_expenses_from_csv') as mock_import:
            mock_import.return_value = CSVExpenseImportResult(
                total_rows=1,
                successful_imports=1,
                failed_imports=0,
                errors=[],
                created_expense_ids=[67890]
            )
            
            client = TestClientWithHost(app)
            
            # Act - no property_name specified
            response = client.post(
                "/api/accounting/expenses/import-csv",
                json={
                    "expenses": [
                        {
                            "category": "Utilities",
                            "description": "Electric bill",
                            "expense_date": "2024-06-01",
                            "subtotal_amount": 200.00,
                            "payment_method": "Bank Transfer"
                            # No property_name - should auto-assign for single property landlord
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

    def test_csv_import_with_tax_amount(self):
        """Test CSV import with tax amounts."""
        # Arrange
        user_id = uuid4()
        test_user = create_test_user(user_id=user_id, user_type=UserType.ADMIN)
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with patch('Backend.api.accounting.expenses.service.import_expenses_from_csv') as mock_import:
            mock_import.return_value = CSVExpenseImportResult(
                total_rows=1,
                successful_imports=1,
                failed_imports=0,
                errors=[],
                created_expense_ids=[67890]
            )
            
            client = TestClientWithHost(app)
            
            # Act
            response = client.post(
                "/api/accounting/expenses/import-csv",
                json={
                    "expenses": [
                        {
                            "category": "Maintenance",
                            "description": "Equipment purchase",
                            "expense_date": "2024-06-01",
                            "subtotal_amount": 1000.00,
                            "total_tax_amount": 130.00,  # 13% tax
                            "payment_method": "Credit Card",
                            "property_name": "Test Property"
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