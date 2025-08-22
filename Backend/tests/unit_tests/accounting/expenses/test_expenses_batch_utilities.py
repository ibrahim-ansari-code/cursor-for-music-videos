"""
Unit tests for expense batch processing utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.accounting.expenses.service_batch import (
    bulk_create_expenses,
    prepare_expense_batch,
    parse_flexible_date,
    normalize_payment_method,
    check_duplicate_expenses
)
from Backend.api.accounting.expenses.schemas import CSVExpenseData
from Backend.models.accounting.payment import PaymentMethod

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestBulkCreateExpenses:
    """Test cases for bulk_create_expenses function."""

    @pytest.mark.asyncio
    async def test_bulk_create_expenses_success(self):
        """Test successful bulk creation of expenses."""
        # Arrange
        expenses_data = [
            {
                "property_id": 1,
                "category": "Maintenance",
                "description": "Repair",
                "expense_date": FIXED_DATETIME,
                "subtotal_amount": 100.00,
                "total_tax_amount": 10.00,
                "payment_method": PaymentMethod.CASH.value,
                "created_at": FIXED_DATETIME,
                "updated_at": FIXED_DATETIME
            },
            {
                "property_id": 2,
                "category": "Utilities",
                "description": "Electric",
                "expense_date": FIXED_DATETIME,
                "subtotal_amount": 200.00,
                "total_tax_amount": 20.00,
                "payment_method": PaymentMethod.BANK_TRANSFER.value,
                "created_at": FIXED_DATETIME,
                "updated_at": FIXED_DATETIME
            }
        ]
        
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1,), (2,)]
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await bulk_create_expenses(expenses_data, mock_session)
        
        # Assert
        assert result == [1, 2]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_expenses_empty_list(self):
        """Test bulk creation with empty list returns empty result."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Act
        result = await bulk_create_expenses([], mock_session)
        
        # Assert
        assert result == []
        mock_session.execute.assert_not_called()


class TestPrepareExpenseBatch:
    """Test cases for prepare_expense_batch function."""

    def test_prepare_expense_batch_success(self):
        """Test successful preparation of expense batch."""
        # Arrange
        csv_expenses = [
            CSVExpenseData(
                category="Maintenance",
                description="Repair",
                expense_date="2024-06-01",
                subtotal_amount=Decimal("100.00"),
                total_tax_amount=Decimal("10.00"),
                payment_method="Cash",
                property_name="Property A"
            )
        ]
        
        properties = {
            "property a": MagicMock(id=1, name="Property A")
        }
        
        # Act
        valid_expenses, errors = prepare_expense_batch(
            csv_expenses,
            properties,
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_expenses) == 1
        assert len(errors) == 0
        assert valid_expenses[0]["property_id"] == 1
        assert valid_expenses[0]["category"] == "Maintenance"
        assert valid_expenses[0]["subtotal_amount"] == 100.00

    def test_prepare_expense_batch_property_not_found(self):
        """Test preparation with property not found."""
        # Arrange
        csv_expenses = [
            CSVExpenseData(
                category="Maintenance",
                description="Repair",
                expense_date="2024-06-01",
                subtotal_amount=Decimal("100.00"),
                property_name="Nonexistent Property"
            )
        ]
        
        properties = {
            "property a": MagicMock(id=1, name="Property A")
        }
        
        # Act
        valid_expenses, errors = prepare_expense_batch(
            csv_expenses,
            properties,
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_expenses) == 0
        assert len(errors) == 1
        assert errors[0]["row_number"] == 1
        assert "Property 'Nonexistent Property' not found" in errors[0]["error_message"]

    def test_prepare_expense_batch_auto_assign_single_property(self):
        """Test auto-assignment for landlord with single property."""
        # Arrange
        csv_expenses = [
            CSVExpenseData(
                category="Utilities",
                description="Electric",
                expense_date="2024-06-01",
                subtotal_amount=Decimal("200.00"),
                # No property_name specified
            )
        ]
        
        properties = {
            "property a": MagicMock(id=1, name="Property A")
        }
        
        # Act
        valid_expenses, errors = prepare_expense_batch(
            csv_expenses,
            properties,
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_expenses) == 1
        assert len(errors) == 0
        assert valid_expenses[0]["property_id"] == 1

    def test_prepare_expense_batch_admin_requires_property(self):
        """Test that admin users must specify property."""
        # Arrange
        csv_expenses = [
            CSVExpenseData(
                category="Maintenance",
                description="Repair",
                expense_date="2024-06-01",
                subtotal_amount=Decimal("100.00"),
                # No property_name specified
            )
        ]
        
        properties = {
            "property a": MagicMock(id=1, name="Property A")
        }
        
        # Act
        valid_expenses, errors = prepare_expense_batch(
            csv_expenses,
            properties,
            "admin123",
            "ADMIN"
        )
        
        # Assert
        assert len(valid_expenses) == 0
        assert len(errors) == 1
        assert "Property name is required for admin imports" in errors[0]["error_message"]


class TestParseFlexibleDate:
    """Test cases for parse_flexible_date function."""

    def test_parse_iso_format(self):
        """Test parsing ISO format date."""
        result = parse_flexible_date("2024-06-01")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 1

    def test_parse_us_format(self):
        """Test parsing US format date."""
        result = parse_flexible_date("06/01/2024")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 1

    def test_parse_datetime_with_timezone(self):
        """Test parsing datetime with timezone."""
        result = parse_flexible_date("2024-06-01T12:00:00Z")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 1

    def test_parse_invalid_date(self):
        """Test parsing invalid date raises error."""
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_flexible_date("not-a-date")

    def test_parse_empty_date(self):
        """Test parsing empty date raises error."""
        with pytest.raises(ValueError, match="Date is required"):
            parse_flexible_date("")


class TestNormalizePaymentMethod:
    """Test cases for normalize_payment_method function."""

    def test_normalize_credit_card(self):
        """Test normalizing credit card payment method."""
        assert normalize_payment_method("credit card") == PaymentMethod.CREDIT_CARD
        assert normalize_payment_method("Credit Card") == PaymentMethod.CREDIT_CARD
        assert normalize_payment_method(" CREDIT CARD ") == PaymentMethod.CREDIT_CARD

    def test_normalize_bank_transfer(self):
        """Test normalizing bank transfer payment method."""
        assert normalize_payment_method("bank transfer") == PaymentMethod.BANK_TRANSFER
        assert normalize_payment_method("wire transfer") == PaymentMethod.WIRE_TRANSFER

    def test_normalize_check_variants(self):
        """Test normalizing check/cheque variants."""
        assert normalize_payment_method("check") == PaymentMethod.CHECK
        assert normalize_payment_method("cheque") == PaymentMethod.CHECK

    def test_normalize_unknown_method(self):
        """Test unknown payment method defaults to OTHER."""
        assert normalize_payment_method("bitcoin") == PaymentMethod.OTHER
        assert normalize_payment_method("unknown") == PaymentMethod.OTHER

    def test_normalize_none_method(self):
        """Test None payment method defaults to OTHER."""
        assert normalize_payment_method(None) == PaymentMethod.OTHER
        assert normalize_payment_method("") == PaymentMethod.OTHER


class TestCheckDuplicateExpenses:
    """Test cases for check_duplicate_expenses function."""

    @pytest.mark.asyncio
    async def test_check_duplicates_found(self):
        """Test finding duplicate expenses."""
        # Arrange
        expenses_data = [
            {
                "property_id": 1,
                "category": "Maintenance",
                "subtotal_amount": 100.00,
                "expense_date": FIXED_DATETIME
            },
            {
                "property_id": 2,
                "category": "Utilities",
                "subtotal_amount": 200.00,
                "expense_date": FIXED_DATETIME
            }
        ]
        
        mock_session = AsyncMock(spec=AsyncSession)
        
        # First expense is duplicate, second is not
        mock_result1 = MagicMock()
        mock_result1.scalar.return_value = 123  # Existing ID found
        
        mock_result2 = MagicMock()
        mock_result2.scalar.return_value = None  # No duplicate
        
        mock_session.execute.side_effect = [mock_result1, mock_result2]
        
        # Act
        result = await check_duplicate_expenses(expenses_data, mock_session)
        
        # Assert
        assert result == [0]  # First expense is duplicate
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_check_duplicates_none_found(self):
        """Test when no duplicates are found."""
        # Arrange
        expenses_data = [
            {
                "property_id": 1,
                "category": "Maintenance",
                "subtotal_amount": 100.00,
                "expense_date": FIXED_DATETIME
            }
        ]
        
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await check_duplicate_expenses(expenses_data, mock_session)
        
        # Assert
        assert result == []
        mock_session.execute.assert_called_once()