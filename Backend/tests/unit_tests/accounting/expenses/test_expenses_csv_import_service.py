"""
Unit tests for the expenses CSV import service layer.

These tests focus on business logic, database interactions, and service-level
functionality without involving the HTTP layer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.accounting.expenses.service import import_expenses_from_csv
from Backend.api.accounting.expenses.schemas import CSVExpenseImportRequest, CSVExpenseImportResult, CSVExpenseData
from Backend.models.accounting.expense import Expense
from Backend.models.accounting.payment import PaymentMethod
from Backend.models.enums import UserType, PropertyStatus
from Backend.models.user import User
from Backend.models.property import Property, PropertyType

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

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

class TestExpenseCSVImportService:
    """Test cases for expense CSV import service functionality."""

    @pytest.mark.asyncio
    async def test_import_expenses_from_csv_success(self):
        """Test successful CSV import with valid data."""
        # Arrange
        user_id = uuid4()
        property_id = 1
        
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        test_property = create_test_property(property_id=property_id, user_id=user_id, name="Test Property")
        
        csv_data = [
            CSVExpenseData(
                category="Maintenance",
                description="HVAC repair",
                expense_date="2024-06-01",
                subtotal_amount=Decimal("500.00"),
                total_tax_amount=Decimal("50.00"),
                payment_method="Credit Card",
                property_name="Test Property"
            )
        ]
        
        import_request = CSVExpenseImportRequest(expenses=csv_data)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock database queries
        properties_result = MagicMock()
        properties_result.scalars.return_value.all.return_value = [test_property]
        mock_session.execute.return_value = properties_result
        
        # Mock expense creation
        created_expense = Expense(
            id=12345,
            category="Maintenance",
            description="HVAC repair",
            expense_date=FIXED_DATETIME,
            subtotal_amount=Decimal("500.00"),
            total_tax_amount=Decimal("50.00"),
            payment_method=PaymentMethod.CREDIT_CARD,
            property_id=property_id
        )
        
        # Mock the batch processing functions
        with patch('Backend.api.accounting.expenses.service.prepare_expense_batch') as mock_prepare:
            mock_prepare.return_value = ([{
                'category': 'Maintenance',
                'description': 'HVAC repair', 
                'expense_date': FIXED_DATETIME,
                'subtotal_amount': Decimal('500.00'),
                'total_tax_amount': Decimal('50.00'),
                'payment_method': PaymentMethod.CREDIT_CARD,
                'property_id': property_id
            }], [])  # valid_expenses, preparation_errors
            
            with patch('Backend.api.accounting.expenses.service.check_duplicate_expenses') as mock_check_dups:
                mock_check_dups.return_value = []  # No duplicates
                
                with patch('Backend.api.accounting.expenses.service.bulk_create_expenses') as mock_bulk_create:
                    mock_bulk_create.return_value = [12345]  # created expense IDs
                    
                    # Act
                    result = await import_expenses_from_csv(import_request, mock_session, test_user)
                    
                    # Assert
                    assert isinstance(result, CSVExpenseImportResult)
                    assert result.total_rows == 1
                    assert result.successful_imports == 1
                    assert result.failed_imports == 0
                    assert len(result.errors) == 0
                    assert len(result.created_expense_ids) == 1
                    assert result.created_expense_ids[0] == 12345

    @pytest.mark.asyncio
    async def test_import_expenses_from_csv_unauthorized_user(self):
        """Test CSV import fails for unauthorized user."""
        # Arrange
        test_user = create_test_user(user_type=UserType.TENANT)
        import_request = CSVExpenseImportRequest(expenses=[])
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await import_expenses_from_csv(import_request, mock_session, test_user)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_import_expenses_from_csv_property_not_found(self):
        """Test CSV import with non-existent property."""
        # Arrange
        user_id = uuid4()
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        
        csv_data = [
            CSVExpenseData(
                category="Utilities",
                description="Electric bill",
                expense_date="2024-06-01",
                subtotal_amount=Decimal("200.00"),
                payment_method="Bank Transfer",
                property_name="Nonexistent Property"
            )
        ]
        
        import_request = CSVExpenseImportRequest(expenses=csv_data)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock database queries - empty results
        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = empty_result
        
        # Act
        result = await import_expenses_from_csv(import_request, mock_session, test_user)
        
        # Assert
        assert result.total_rows == 1
        assert result.successful_imports == 0
        assert result.failed_imports == 1
        assert len(result.errors) == 1
        assert result.errors[0].row_number == 1
        assert "Property 'Nonexistent Property' not found" in result.errors[0].error_message

    @pytest.mark.asyncio
    async def test_import_expenses_from_csv_landlord_single_property_auto_assign(self):
        """Test CSV import for landlord with single property auto-assignment."""
        # Arrange
        user_id = uuid4()
        property_id = 2
        
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        test_property = create_test_property(property_id=property_id, user_id=user_id, name="Only Property")
        
        csv_data = [
            CSVExpenseData(
                category="Utilities",
                description="Electric bill",
                expense_date="2024-06-01",
                subtotal_amount=Decimal("200.00"),
                payment_method="Bank Transfer"
                # No property_name specified
            )
        ]
        
        import_request = CSVExpenseImportRequest(expenses=csv_data)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock properties query - single property
        properties_result = MagicMock()
        properties_result.scalars.return_value.all.return_value = [test_property]
        mock_session.execute.return_value = properties_result
        
        # Mock the batch processing functions
        with patch('Backend.api.accounting.expenses.service.prepare_expense_batch') as mock_prepare:
            mock_prepare.return_value = ([{
                'category': 'Utilities',
                'description': 'Electric bill',
                'expense_date': FIXED_DATETIME,
                'subtotal_amount': Decimal('200.00'),
                'property_id': property_id  # Auto-assigned by prepare_expense_batch
            }], [])
            
            with patch('Backend.api.accounting.expenses.service.check_duplicate_expenses') as mock_check_dups:
                mock_check_dups.return_value = []
                
                with patch('Backend.api.accounting.expenses.service.bulk_create_expenses') as mock_bulk_create:
                    mock_bulk_create.return_value = [12345]
                    
                    # Act
                    result = await import_expenses_from_csv(import_request, mock_session, test_user)
                    
                    # Assert
                    assert result.total_rows == 1
                    assert result.successful_imports == 1
                    assert result.failed_imports == 0

    @pytest.mark.asyncio
    async def test_import_expenses_from_csv_landlord_multiple_properties_no_name(self):
        """Test CSV import for landlord with multiple properties but no property name specified."""
        # Arrange
        user_id = uuid4()
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        
        # Create multiple properties
        property1 = create_test_property(property_id=3, user_id=user_id, name="Property 1")
        property2 = create_test_property(property_id=4, user_id=user_id, name="Property 2")
        
        csv_data = [
            CSVExpenseData(
                category="Utilities",
                description="Electric bill",
                expense_date="2024-06-01",
                subtotal_amount=Decimal("200.00"),
                payment_method="Bank Transfer"
                # No property_name specified
            )
        ]
        
        import_request = CSVExpenseImportRequest(expenses=csv_data)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock properties query - multiple properties
        properties_result = MagicMock()
        properties_result.scalars.return_value.all.return_value = [property1, property2]
        mock_session.execute.return_value = properties_result
        
        # Act
        result = await import_expenses_from_csv(import_request, mock_session, test_user)
        
        # Assert
        assert result.total_rows == 1
        assert result.successful_imports == 0
        assert result.failed_imports == 1
        assert len(result.errors) == 1
        assert "Property name is required" in result.errors[0].error_message

    @pytest.mark.asyncio
    async def test_import_expenses_from_csv_invalid_date_format(self):
        """Test CSV import with invalid date format."""
        # Arrange
        from pydantic import ValidationError
        
        # Test that invalid date format is caught at schema validation level
        with pytest.raises(ValidationError) as exc_info:
            CSVExpenseData(
                category="Maintenance",
                description="HVAC repair",
                expense_date="invalid-date",
                subtotal_amount=Decimal("500.00"),
                payment_method="Credit Card",
                property_name="Test Property"
            )
        
        # Assert the validation error contains expected message
        assert "Date format not recognized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_import_expenses_from_csv_payment_method_normalization(self):
        """Test CSV import with payment method normalization."""
        # Arrange
        user_id = uuid4()
        property_id = 6
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        test_property = create_test_property(property_id=property_id, user_id=user_id, name="Test Property")
        
        csv_data = [
            CSVExpenseData(
                category="Utilities",
                description="Electric bill",
                expense_date="2024-06-01",
                subtotal_amount=Decimal("200.00"),
                payment_method="credit card",  # lowercase - should be normalized
                property_name="Test Property"
            )
        ]
        
        import_request = CSVExpenseImportRequest(expenses=csv_data)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock database queries
        properties_result = MagicMock()
        properties_result.scalars.return_value.all.return_value = [test_property]
        mock_session.execute.return_value = properties_result
        
        # Mock the batch processing functions
        with patch('Backend.api.accounting.expenses.service.prepare_expense_batch') as mock_prepare:
            mock_prepare.return_value = ([{
                'category': 'Utilities',
                'description': 'Electric bill',
                'expense_date': FIXED_DATETIME,
                'subtotal_amount': Decimal('200.00'),
                'payment_method': PaymentMethod.CREDIT_CARD,  # Normalized by prepare_expense_batch
                'property_id': property_id
            }], [])
            
            with patch('Backend.api.accounting.expenses.service.check_duplicate_expenses') as mock_check_dups:
                mock_check_dups.return_value = []
                
                with patch('Backend.api.accounting.expenses.service.bulk_create_expenses') as mock_bulk_create:
                    mock_bulk_create.return_value = [12345]
                    
                    # Act
                    result = await import_expenses_from_csv(import_request, mock_session, test_user)
                    
                    # Assert
                    assert result.total_rows == 1
                    assert result.successful_imports == 1

    @pytest.mark.asyncio
    async def test_import_expenses_from_csv_admin_user(self):
        """Test CSV import works for admin user."""
        # Arrange
        test_user = create_test_user(user_type=UserType.ADMIN)
        import_request = CSVExpenseImportRequest(expenses=[])
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock empty results
        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = empty_result
        
        # Act
        result = await import_expenses_from_csv(import_request, mock_session, test_user)
        
        # Assert - should not raise permission error
        assert isinstance(result, CSVExpenseImportResult)
        assert result.total_rows == 0

    @pytest.mark.asyncio
    async def test_import_expenses_from_csv_with_tax_amount_update(self):
        """Test CSV import with tax amount being updated after creation."""
        # Arrange
        user_id = uuid4()
        property_id = 7
        expense_id = 123
        
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        test_property = create_test_property(property_id=property_id, user_id=user_id, name="Test Property")
        
        csv_data = [
            CSVExpenseData(
                category="Equipment",
                description="Purchase",
                expense_date="2024-06-01",
                subtotal_amount=Decimal("1000.00"),
                total_tax_amount=Decimal("130.00"),  # Tax specified
                payment_method="Credit Card",
                property_name="Test Property"
            )
        ]
        
        import_request = CSVExpenseImportRequest(expenses=csv_data)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock database queries
        properties_result = MagicMock()
        properties_result.scalars.return_value.all.return_value = [test_property]
        mock_session.execute.return_value = properties_result
        
        # Mock the batch processing functions
        with patch('Backend.api.accounting.expenses.service.prepare_expense_batch') as mock_prepare:
            mock_prepare.return_value = ([{
                'category': 'Equipment',
                'description': 'New laptop',
                'expense_date': FIXED_DATETIME,
                'subtotal_amount': Decimal('1000.00'),
                'total_tax_amount': Decimal('130.00'),
                'payment_method': PaymentMethod.CREDIT_CARD,
                'property_id': property_id
            }], [])
            
            with patch('Backend.api.accounting.expenses.service.check_duplicate_expenses') as mock_check_dups:
                mock_check_dups.return_value = []
                
                with patch('Backend.api.accounting.expenses.service.bulk_create_expenses') as mock_bulk_create:
                    mock_bulk_create.return_value = [expense_id]
                    
                    # Act
                    result = await import_expenses_from_csv(import_request, mock_session, test_user)
                    
                    # Assert
                    assert result.total_rows == 1
                    assert result.successful_imports == 1