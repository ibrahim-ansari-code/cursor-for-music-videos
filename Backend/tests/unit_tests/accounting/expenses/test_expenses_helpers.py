"""
Unit tests for expense helpers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.accounting.expenses.helpers import update_expense_taxes
from Backend.models.accounting.expense import Expense, ExpenseUpdate, ExpenseTaxDetail

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestUpdateExpenseTaxes:
    """Test cases for update_expense_taxes function."""

    @pytest.mark.asyncio
    @patch('Backend.api.accounting.expenses.helpers.calculate_expense_taxes')
    @patch('Backend.api.accounting.expenses.helpers.create_expense_tax_orm_list')
    async def test_update_expense_taxes_with_new_tax_data(self, mock_create_tax_orm, mock_calc_taxes):
        """Test updating taxes with new tax data provided - covers lines 208-209."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        db_expense = MagicMock(spec=Expense)
        db_expense.subtotal_amount = Decimal("100.00")
        db_expense.taxes = []
        
        # Mock the helper functions
        mock_tax_details = [MagicMock()]
        mock_calc_taxes.return_value = (mock_tax_details, Decimal("10.00"))
        mock_tax_orm_objects = [MagicMock(spec=ExpenseTaxDetail)]
        mock_create_tax_orm.return_value = mock_tax_orm_objects
        
        # Mock ExpenseUpdate with taxes data
        expense_data = MagicMock(spec=ExpenseUpdate)
        expense_data.taxes = [
            MagicMock(tax_type="GST", rate=Decimal("0.10"), amount=Decimal("10.00"))
        ]
        
        subtotal_updated = False
        
        # Act
        await update_expense_taxes(db_expense, expense_data, subtotal_updated, mock_session)
        
        # Assert - verify session.flush() and session.refresh() were called (lines 208-209)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(
            db_expense, attribute_names=["total_tax_amount", "subtotal_amount"]
        )

    @pytest.mark.asyncio
    @patch('Backend.api.accounting.expenses.helpers.recalculate_orm_taxes')
    async def test_update_expense_taxes_with_subtotal_updated(self, mock_recalc_taxes):
        """Test updating taxes when subtotal was updated - covers lines 216-217."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        db_expense = MagicMock(spec=Expense)
        db_expense.subtotal_amount = Decimal("150.00")
        
        # Mock existing taxes
        existing_tax = MagicMock(spec=ExpenseTaxDetail)
        existing_tax.tax_type = "GST"
        existing_tax.rate = Decimal("0.10")
        db_expense.taxes = [existing_tax]
        
        # Mock the recalculate function
        mock_recalc_taxes.return_value = Decimal("15.00")
        
        # Mock ExpenseUpdate without taxes data (None)
        expense_data = MagicMock(spec=ExpenseUpdate)
        expense_data.taxes = None
        
        subtotal_updated = True
        
        # Act
        await update_expense_taxes(db_expense, expense_data, subtotal_updated, mock_session)
        
        # Assert - verify session.flush() and session.refresh() were called (lines 216-217)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(
            db_expense, attribute_names=["total_tax_amount", "subtotal_amount"]
        )

    @pytest.mark.asyncio
    async def test_update_expense_taxes_no_changes_needed(self):
        """Test when no tax updates are needed."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        db_expense = MagicMock(spec=Expense)
        db_expense.subtotal_amount = Decimal("100.00")
        
        # Mock ExpenseUpdate without taxes data (None)
        expense_data = MagicMock(spec=ExpenseUpdate)
        expense_data.taxes = None
        
        subtotal_updated = False  # No subtotal change either
        
        # Act
        await update_expense_taxes(db_expense, expense_data, subtotal_updated, mock_session)
        
        # Assert - no session operations should be called
        mock_session.flush.assert_not_called()
        mock_session.refresh.assert_not_called()