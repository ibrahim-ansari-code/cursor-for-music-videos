"""
Unit tests for convenience functions.

Tests the helper functions used for integration with expense and invoice services.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from decimal import Decimal

from Backend.api.accounting.tax_preferences.service import (
    get_smart_tax_for_expense, get_smart_tax_for_invoice
)
from Backend.api.accounting.tax_preferences.schemas import SmartTaxResponse

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

class TestConvenienceFunctions:
    """Test cases for convenience functions used by expense and invoice services."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def sample_user_id(self):
        """Generate a sample user ID."""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_invoice_creation_with_existing_taxes(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_invoice_creation returns early when taxes exist - covers line 62."""
        from Backend.api.accounting.invoices.service import get_smart_tax_for_invoice_creation
        from Backend.models.accounting.invoice_tax_detail import InvoiceTaxDetailCreate
        from decimal import Decimal
        
        # Arrange - invoice data with existing taxes
        invoice_data = MagicMock()
        invoice_data.taxes = [InvoiceTaxDetailCreate(tax_name="HST", tax_rate=Decimal("13.00"))]
        
        # Act - should return immediately without calling smart tax service
        result = await get_smart_tax_for_invoice_creation(
            session=mock_session,
            user_id=sample_user_id,
            property_id=1,
            invoice_data=invoice_data
        )
        
        # Assert - should return original data unchanged (hits line 62)
        assert result == invoice_data
    
    @pytest.mark.asyncio
    async def test_get_smart_tax_for_invoice_creation_no_recommendation(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_invoice_creation when no recommendation - covers line 67."""
        from Backend.api.accounting.invoices.service import get_smart_tax_for_invoice_creation
        
        # Arrange - invoice data with no taxes
        invoice_data = MagicMock()
        invoice_data.taxes = None
        
        # Mock smart tax service to return None
        with patch('Backend.api.accounting.tax_preferences.service.get_smart_tax_for_invoice', return_value=None):
            # Act - should return original data when no recommendation (hits line 67)
            result = await get_smart_tax_for_invoice_creation(
                session=mock_session,
                user_id=sample_user_id,
                property_id=1,
                invoice_data=invoice_data
            )
            
            # Assert
            assert result == invoice_data

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_expense_success(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_expense returns tuple when tax is found."""
        # Arrange
        property_id = 1
        
        mock_smart_response = SmartTaxResponse(
            tax_name="HST",
            tax_rate=Decimal("13.00"),
            source="property_default",
            confidence=0.95,
            reasoning="Using property-specific tax preference"
        )

        with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            result = await get_smart_tax_for_expense(mock_session, sample_user_id, property_id)

            # Assert
            assert result is not None
            assert result == ("HST", Decimal("13.00"))

            # Verify service was called correctly
            mock_service_class.assert_called_once_with(mock_session)
            mock_service.get_smart_tax_for_context.assert_called_once_with(sample_user_id, property_id)

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_expense_creation_with_existing_taxes(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_expense_creation returns early when taxes already exist."""
        from Backend.api.accounting.expenses.service import get_smart_tax_for_expense_creation
        from Backend.models.accounting.expense import ExpenseTaxDetailCreate
        from decimal import Decimal
        
        # Arrange - expense data with existing taxes
        expense_data = MagicMock()
        expense_data.taxes = [ExpenseTaxDetailCreate(tax_name="HST", tax_rate=Decimal("13.00"))]
        
        # Act - should return immediately without calling smart tax service
        result = await get_smart_tax_for_expense_creation(
            session=mock_session,
            user_id=sample_user_id,
            property_id=1,
            expense_data=expense_data
        )
        
        # Assert - should return original data unchanged (hits line 68)
        assert result == expense_data

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_expense_creation_with_recommendation(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_expense_creation with smart recommendation."""
        from Backend.api.accounting.expenses.service import get_smart_tax_for_expense_creation
        from decimal import Decimal
        
        # Arrange - expense data with no taxes
        expense_data = MagicMock()
        expense_data.taxes = None
        expense_data.model_copy.return_value = expense_data
        
        # Mock smart tax service to return recommendation
        with patch('Backend.api.accounting.tax_preferences.service.get_smart_tax_for_expense', return_value=("HST", Decimal("13.00"))):
            with patch('Backend.models.accounting.expense.ExpenseTaxDetailCreate') as mock_tax_create:
                mock_tax = MagicMock()
                mock_tax_create.return_value = mock_tax
                
                # Act - should populate smart tax (hits lines 75,78-79,86-87,89-90)
                result = await get_smart_tax_for_expense_creation(
                    session=mock_session,
                    user_id=sample_user_id,
                    property_id=1,
                    expense_data=expense_data
                )
                
                # Assert
                assert result.taxes == [mock_tax]
                mock_tax_create.assert_called_once_with(
                    tax_name="HST",
                    tax_rate=Decimal("13.00")
                )

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_expense_no_tax_name(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_expense returns None when no tax_name."""
        # Arrange
        property_id = 1
        
        mock_smart_response = SmartTaxResponse(
            tax_name=None,
            tax_rate=None,
            source="none",
            confidence=0.0,
            reasoning="No tax preferences found"
        )

        with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            result = await get_smart_tax_for_expense(mock_session, sample_user_id, property_id)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_expense_no_tax_rate(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_expense returns None when no tax_rate."""
        # Arrange
        property_id = 1
        
        mock_smart_response = SmartTaxResponse(
            tax_name="HST",
            tax_rate=None,
            source="none",
            confidence=0.0,
            reasoning="Incomplete tax data"
        )

        with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            result = await get_smart_tax_for_expense(mock_session, sample_user_id, property_id)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_expense_with_zero_rate(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_expense handles zero tax rate."""
        # Arrange
        property_id = 1
        
        mock_smart_response = SmartTaxResponse(
            tax_name="No Tax",
            tax_rate=Decimal("0.00"),
            source="user_default",
            confidence=0.75,
            reasoning="User set zero tax rate"
        )

        with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            result = await get_smart_tax_for_expense(mock_session, sample_user_id, property_id)

            # Assert
            assert result is not None
            assert result == ("No Tax", Decimal("0.00"))

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_invoice_success(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_invoice returns tuple when tax is found."""
        # Arrange
        property_id = 1
        
        mock_smart_response = SmartTaxResponse(
            tax_name="GST+PST",
            tax_rate=Decimal("12.00"),
            source="provincial_default",
            confidence=0.85,
            reasoning="Using provincial tax rate"
        )

        with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            result = await get_smart_tax_for_invoice(mock_session, sample_user_id, property_id)

            # Assert
            assert result is not None
            assert result == ("GST+PST", Decimal("12.00"))

            # Verify service was called correctly
            mock_service.get_smart_tax_for_context.assert_called_once_with(sample_user_id, property_id)

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_invoice_no_property(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_invoice with None property_id."""
        # Arrange
        mock_smart_response = SmartTaxResponse(
            tax_name="GST",
            tax_rate=Decimal("5.00"),
            source="user_default",
            confidence=0.75,
            reasoning="Using user default tax"
        )

        with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            result = await get_smart_tax_for_invoice(mock_session, sample_user_id, None)

            # Assert
            assert result is not None
            assert result == ("GST", Decimal("5.00"))

            # Verify service was called with None property_id
            mock_service.get_smart_tax_for_context.assert_called_once_with(sample_user_id, None)

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_invoice_no_recommendation(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_invoice returns None when no recommendation."""
        # Arrange
        mock_smart_response = SmartTaxResponse(
            tax_name=None,
            tax_rate=None,
            source="none",
            confidence=0.0,
            reasoning="No tax data available"
        )

        with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            result = await get_smart_tax_for_invoice(mock_session, sample_user_id, 1)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_expense_different_tax_types(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_expense with different tax types."""
        # Test cases for different provincial tax types
        test_cases = [
            ("HST", Decimal("13.00")),  # Ontario
            ("GST", Decimal("5.00")),   # Alberta
            ("GST+PST", Decimal("12.00")), # BC
            ("GST+QST", Decimal("14.975")), # Quebec
        ]

        for tax_name, tax_rate in test_cases:
            with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
                mock_smart_response = SmartTaxResponse(
                    tax_name=tax_name,
                    tax_rate=tax_rate,
                    source="provincial_default",
                    confidence=0.85,
                    reasoning=f"Provincial tax: {tax_name} {tax_rate}%"
                )
                
                mock_service = mock_service_class.return_value
                mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

                # Act
                result = await get_smart_tax_for_expense(mock_session, sample_user_id, 1)

                # Assert
                assert result == (tax_name, tax_rate)

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_invoice_edge_cases(self, mock_session, sample_user_id):
        """Test get_smart_tax_for_invoice with edge cases."""
        # Test with very high tax rate
        mock_smart_response = SmartTaxResponse(
            tax_name="High Tax",
            tax_rate=Decimal("99.99"),
            source="user_default",
            confidence=0.75,
            reasoning="User set high tax rate"
        )

        with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            result = await get_smart_tax_for_invoice(mock_session, sample_user_id, 1)

            # Assert
            assert result == ("High Tax", Decimal("99.99"))

    @pytest.mark.asyncio
    async def test_convenience_functions_service_exception_handling(self, mock_session, sample_user_id):
        """Test that convenience functions properly propagate service exceptions."""
        # Arrange
        with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(side_effect=Exception("Database error"))

            # Act & Assert for expense function
            with pytest.raises(Exception, match="Database error"):
                await get_smart_tax_for_expense(mock_session, sample_user_id, 1)

            # Act & Assert for invoice function
            with pytest.raises(Exception, match="Database error"):
                await get_smart_tax_for_invoice(mock_session, sample_user_id, 1)

    @pytest.mark.asyncio
    async def test_convenience_functions_decimal_precision(self, mock_session, sample_user_id):
        """Test that convenience functions preserve decimal precision."""
        # Arrange
        precise_rate = Decimal("13.123456789")
        mock_smart_response = SmartTaxResponse(
            tax_name="Precise Tax",
            tax_rate=precise_rate,
            source="user_default",
            confidence=0.75,
            reasoning="High precision tax rate"
        )

        with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Act
            result_expense = await get_smart_tax_for_expense(mock_session, sample_user_id, 1)
            result_invoice = await get_smart_tax_for_invoice(mock_session, sample_user_id, 1)

            # Assert
            assert result_expense == ("Precise Tax", precise_rate)
            assert result_invoice == ("Precise Tax", precise_rate)
            
            # Verify exact decimal precision is maintained
            assert result_expense[1] == Decimal("13.123456789")
            assert result_invoice[1] == Decimal("13.123456789")

    @pytest.mark.asyncio
    async def test_get_smart_tax_functions_parameter_validation(self, mock_session):
        """Test convenience functions with various parameter types."""
        # Test with string user_id and int property_id
        user_id_uuid = str(uuid4())
        
        mock_smart_response = SmartTaxResponse(
            tax_name="HST",
            tax_rate=Decimal("13.00"),
            source="property_default",
            confidence=0.95,
            reasoning="Property tax"
        )

        with patch('Backend.api.accounting.tax_preferences.service.TaxPreferenceService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_smart_tax_for_context = AsyncMock(return_value=mock_smart_response)

            # Test expense function with different parameter types
            result = await get_smart_tax_for_expense(mock_session, user_id_uuid, 123)
            assert result == ("HST", Decimal("13.00"))

            # Test invoice function with None property_id
            result = await get_smart_tax_for_invoice(mock_session, user_id_uuid, None)
            assert result == ("HST", Decimal("13.00"))

            # Verify parameters were passed correctly
            calls = mock_service.get_smart_tax_for_context.call_args_list
            assert calls[0][0] == (user_id_uuid, 123)  # expense call
            assert calls[1][0] == (user_id_uuid, None)  # invoice call