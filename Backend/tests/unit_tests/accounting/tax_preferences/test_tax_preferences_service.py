"""
Unit tests for TaxPreferenceService class methods.

Tests the core service layer business logic for tax preference management
without external dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession


from Backend.api.accounting.tax_preferences.service import TaxPreferenceService
from Backend.api.accounting.tax_preferences.schemas import (
    TaxPreferenceCreate, TaxPreferenceResponse, SmartTaxResponse, HistoricalTaxUsage
)
from Backend.models.user import User
from Backend.models.property import Property

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

class TestTaxPreferenceService:
    """Test cases for TaxPreferenceService class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def tax_service(self, mock_session):
        """Create TaxPreferenceService instance with mock session."""
        return TaxPreferenceService(mock_session)

    @pytest.fixture
    def sample_user_id(self):
        """Generate a sample user ID."""
        return str(uuid4())

    @pytest.fixture
    def sample_property_id(self):
        """Generate a sample property ID."""
        return 1

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_context_property_default(self, tax_service, sample_user_id, sample_property_id):
        """Test smart tax selection returns property default with highest priority."""
        # Arrange
        expected_response = TaxPreferenceResponse(
            tax_name="HST",
            tax_rate=Decimal("13.00"),
            source="property_default"
        )
        
        tax_service._get_property_tax_default = AsyncMock(return_value=expected_response)

        # Act
        result = await tax_service.get_smart_tax_for_context(sample_user_id, sample_property_id)

        # Assert
        assert isinstance(result, SmartTaxResponse)
        assert result.tax_name == "HST"
        assert result.tax_rate == Decimal("13.00")
        assert result.source == "property_default"
        assert result.confidence == 0.95
        assert "property-specific" in result.reasoning

        # Verify property default was checked first
        tax_service._get_property_tax_default.assert_called_once_with(sample_property_id, sample_user_id)

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_context_provincial_default(self, tax_service, sample_user_id, sample_property_id):
        """Test smart tax selection falls back to provincial default."""
        # Arrange
        provincial_response = TaxPreferenceResponse(
            tax_name="HST",
            tax_rate=Decimal("13.00"),
            source="provincial_default"
        )
        
        tax_service._get_property_tax_default = AsyncMock(return_value=None)
        tax_service._get_provincial_tax_for_property = AsyncMock(return_value=provincial_response)

        # Act
        result = await tax_service.get_smart_tax_for_context(sample_user_id, sample_property_id)

        # Assert
        assert result.source == "provincial_default"
        assert result.confidence == 0.85
        assert "provincial tax rate" in result.reasoning

        # Verify fallback hierarchy
        tax_service._get_property_tax_default.assert_called_once()
        tax_service._get_provincial_tax_for_property.assert_called_once_with(sample_property_id, sample_user_id)

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_context_user_default(self, tax_service, sample_user_id):
        """Test smart tax selection falls back to user default when no property."""
        # Arrange
        user_response = TaxPreferenceResponse(
            tax_name="GST",
            tax_rate=Decimal("5.00"),
            source="user_default"
        )
        
        tax_service._get_user_tax_default = AsyncMock(return_value=user_response)

        # Act
        result = await tax_service.get_smart_tax_for_context(sample_user_id, None)

        # Assert
        assert result.source == "user_default"
        assert result.confidence == 0.75
        assert "personal tax default" in result.reasoning

        # Verify user default was called
        tax_service._get_user_tax_default.assert_called_once_with(sample_user_id)

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_context_historical_usage(self, tax_service, sample_user_id):
        """Test smart tax selection falls back to historical usage."""
        # Arrange
        historical_response = HistoricalTaxUsage(
            tax_name="HST",
            tax_rate=Decimal("13.00"),
            usage_count=15,
            last_used="2024-08-15T10:30:00",
            percentage=60.0
        )
        
        tax_service._get_user_tax_default = AsyncMock(return_value=None)
        tax_service._get_most_used_tax = AsyncMock(return_value=historical_response)

        # Act
        result = await tax_service.get_smart_tax_for_context(sample_user_id, None)

        # Assert
        assert result.source == "historical_usage"
        assert result.confidence == 0.60
        assert "usage history" in result.reasoning
        assert "15 times" in result.reasoning

    @pytest.mark.asyncio
    async def test_get_smart_tax_for_context_no_recommendation(self, tax_service, sample_user_id):
        """Test smart tax selection when no data is available."""
        # Arrange
        tax_service._get_user_tax_default = AsyncMock(return_value=None)
        tax_service._get_most_used_tax = AsyncMock(return_value=None)

        # Act
        result = await tax_service.get_smart_tax_for_context(sample_user_id, None)

        # Assert
        assert result.tax_name is None
        assert result.tax_rate is None
        assert result.source == "none"
        assert result.confidence == 0.0
        assert "no tax preferences" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_set_user_tax_default_success(self, tax_service, sample_user_id, mock_session):
        """Test setting user tax default successfully."""
        # Arrange
        tax_data = TaxPreferenceCreate(tax_name="HST", tax_rate=Decimal("13.00"))
        
        mock_user = User(id=uuid4(), email="test@example.com", first_name="Test")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        # Act
        result = await tax_service.set_user_tax_default(sample_user_id, tax_data)

        # Assert
        assert isinstance(result, TaxPreferenceResponse)
        assert result.tax_name == "HST"
        assert result.tax_rate == Decimal("13.00")
        assert result.source == "user_default"

        # Verify user was updated
        assert mock_user.default_tax_name == "HST"
        assert mock_user.default_tax_rate == Decimal("13.00")
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_user_tax_default_user_not_found(self, tax_service, sample_user_id, mock_session):
        """Test setting user tax default when user is not found."""
        # Arrange
        tax_data = TaxPreferenceCreate(tax_name="HST", tax_rate=Decimal("13.00"))
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            await tax_service.set_user_tax_default(sample_user_id, tax_data)

    @pytest.mark.asyncio
    async def test_set_property_tax_default_success(self, tax_service, sample_user_id, sample_property_id, mock_session):
        """Test setting property tax default successfully."""
        # Arrange
        tax_data = TaxPreferenceCreate(tax_name="GST+PST", tax_rate=Decimal("12.00"))
        
        mock_property = Property(id=sample_property_id, address="123 Test St")
        tax_service._get_user_property = AsyncMock(return_value=mock_property)

        # Act
        result = await tax_service.set_property_tax_default(sample_user_id, sample_property_id, tax_data)

        # Assert
        assert isinstance(result, TaxPreferenceResponse)
        assert result.tax_name == "GST+PST"
        assert result.tax_rate == Decimal("12.00")
        assert result.source == "property_default"

        # Verify property was updated
        assert mock_property.default_tax_name == "GST+PST"
        assert mock_property.default_tax_rate == Decimal("12.00")
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_property_tax_default_property_not_found(self, tax_service, sample_user_id, sample_property_id):
        """Test setting property tax default when property is not found."""
        # Arrange
        tax_data = TaxPreferenceCreate(tax_name="HST", tax_rate=Decimal("13.00"))
        tax_service._get_user_property = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="Property not found or access denied"):
            await tax_service.set_property_tax_default(sample_user_id, sample_property_id, tax_data)

    @pytest.mark.asyncio
    async def test_get_user_tax_default_success(self, tax_service, sample_user_id):
        """Test getting user tax default successfully."""
        # Arrange
        expected_response = TaxPreferenceResponse(
            tax_name="HST",
            tax_rate=Decimal("13.00"),
            source="user_default"
        )
        tax_service._get_user_tax_default = AsyncMock(return_value=expected_response)

        # Act
        result = await tax_service.get_user_tax_default(sample_user_id)

        # Assert
        assert result == expected_response
        tax_service._get_user_tax_default.assert_called_once_with(sample_user_id)



    @pytest.mark.asyncio
    async def test_get_historical_tax_usage_success(self, tax_service, sample_user_id, mock_session):
        """Test getting historical tax usage successfully."""
        # Arrange
        mock_rows = [
            MagicMock(
                tax_name="HST",
                tax_rate=Decimal("13.00"),
                usage_count=15,
                last_used=datetime(2024, 8, 15, 10, 30)
            ),
            MagicMock(
                tax_name="GST",
                tax_rate=Decimal("5.00"),
                usage_count=10,
                last_used=datetime(2024, 8, 10, 14, 20)
            )
        ]

        mock_result = Mock()
        mock_result.all.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        # Act
        result = await tax_service.get_historical_tax_usage(sample_user_id, limit=10)

        # Assert
        assert len(result) == 2
        
        first_item = result[0]
        assert isinstance(first_item, HistoricalTaxUsage)
        assert first_item.tax_name == "HST"
        assert first_item.tax_rate == Decimal("13.00")
        assert first_item.usage_count == 15
        assert first_item.percentage == 60.0  # 15/25 * 100

        second_item = result[1]
        assert second_item.tax_name == "GST"
        assert second_item.usage_count == 10
        assert second_item.percentage == 40.0  # 10/25 * 100

    @pytest.mark.asyncio
    async def test_get_historical_tax_usage_empty(self, tax_service, sample_user_id, mock_session):
        """Test getting historical tax usage when no data exists."""
        # Arrange
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Act
        result = await tax_service.get_historical_tax_usage(sample_user_id)

        # Assert
        assert result == []


    @pytest.mark.asyncio  
    async def test_tax_rate_validation_error(self):
        """Test tax rate validation error through Pydantic Field constraints."""
        from Backend.api.accounting.tax_preferences.schemas import TaxPreferenceCreate
        from decimal import Decimal
        from pydantic import ValidationError
        
        # This should trigger Pydantic Field validation (ge=0, le=100)
        with pytest.raises(ValidationError) as exc_info:
            TaxPreferenceCreate(tax_name="HST", tax_rate=Decimal("150.00"))
        
        # Verify the validation error mentions tax_rate field
        assert "tax_rate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_clear_user_tax_default_user_not_found(self):
        """Test clear_user_tax_default when user doesn't exist - covers lines 168-170,172-173."""
        mock_session = AsyncMock()
        service = TaxPreferenceService(mock_session)
        
        # Mock user not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act & Assert - should hit lines 168-170,172-173
        with pytest.raises(ValueError, match="User not found"):
            await service.clear_user_tax_default("nonexistent-user")
    
    @pytest.mark.asyncio
    async def test_clear_property_tax_default_property_not_found(self):
        """Test clear_property_tax_default when property doesn't exist - covers lines 185-187,190-191,193."""
        mock_session = AsyncMock()
        service = TaxPreferenceService(mock_session)
        
        # Mock _get_user_property to return None
        service._get_user_property = AsyncMock(return_value=None)
        
        # Act & Assert - should hit lines 185-187
        with pytest.raises(ValueError, match="Property not found or access denied"):
            await service.clear_property_tax_default("user123", 999)
    
    @pytest.mark.asyncio
    async def test_get_property_tax_default_success(self):
        """Test get_property_tax_default success path - covers lines 201-202."""
        mock_session = AsyncMock()
        service = TaxPreferenceService(mock_session)
        
        # Mock successful property tax retrieval
        mock_tax_response = TaxPreferenceResponse(
            tax_name="HST",
            tax_rate=Decimal("13.00"),
            source="property_default"
        )
        service._get_property_tax_default = AsyncMock(return_value=mock_tax_response)
        
        # Act - should hit lines 201-202
        result = await service.get_property_tax_default("user123", 1)
        
        # Assert
        assert result == mock_tax_response
        service._get_property_tax_default.assert_called_once_with(1, "user123")

    @pytest.mark.asyncio
    async def test_get_most_used_tax_success(self, tax_service, sample_user_id):
        """Test getting most used tax successfully."""
        # Arrange
        expected_usage = HistoricalTaxUsage(
            tax_name="HST",
            tax_rate=Decimal("13.00"),
            usage_count=15,
            last_used="2024-08-15T10:30:00",
            percentage=60.0
        )
        
        tax_service.get_historical_tax_usage = AsyncMock(return_value=[expected_usage])

        # Act
        result = await tax_service._get_most_used_tax(sample_user_id)

        # Assert
        assert result == expected_usage
        tax_service.get_historical_tax_usage.assert_called_once_with(sample_user_id, limit=1)


    @pytest.mark.asyncio
    async def test_get_user_property_success(self, tax_service, sample_user_id, sample_property_id, mock_session):
        """Test getting user property with ownership validation."""
        # Arrange
        mock_property = Property(id=sample_property_id, address="123 Test St")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property
        mock_session.execute.return_value = mock_result

        # Act
        result = await tax_service._get_user_property(sample_user_id, sample_property_id)

        # Assert
        assert result == mock_property
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_expense_smart_tax_no_recommendation(self):
        """Test expense smart tax when no recommendation - hits expenses/service.py lines 71-73."""
        from Backend.api.accounting.expenses.service import get_smart_tax_for_expense_creation
        
        mock_session = AsyncMock()
        # Use mock object instead of real model  
        expense_data = MagicMock()
        expense_data.taxes = None
        expense_data.model_copy.return_value = expense_data
        
        # Mock to return None - hits lines 71-73
        with patch('Backend.api.accounting.tax_preferences.service.get_smart_tax_for_expense', return_value=None):
            result = await get_smart_tax_for_expense_creation(mock_session, "user123", 1, expense_data)
            assert result == expense_data

    @pytest.mark.asyncio  
    async def test_invoice_smart_tax_with_recommendation(self):
        """Test invoice smart tax with recommendation - hits invoices/service.py lines 69-84."""
        from Backend.api.accounting.invoices.service import get_smart_tax_for_invoice_creation
        
        mock_session = AsyncMock()
        # Use mock object instead of real model
        invoice_data = MagicMock()
        invoice_data.taxes = None
        invoice_data.model_copy.return_value = invoice_data
        
        # Mock to return recommendation - hits lines 69-84  
        with patch('Backend.api.accounting.tax_preferences.service.get_smart_tax_for_invoice', return_value=("HST", Decimal("13.00"))):
            with patch('Backend.models.accounting.invoice_tax_detail.InvoiceTaxDetailCreate') as mock_tax_create:
                mock_tax = MagicMock()
                mock_tax_create.return_value = mock_tax
                result = await get_smart_tax_for_invoice_creation(mock_session, "user123", 1, invoice_data)
                assert result.taxes == [mock_tax]

    @pytest.mark.asyncio
    async def test_invoice_subtotal_validation_error(self):
        """Test invoice subtotal validation error - hits invoices/schemas.py line 44."""
        from Backend.api.accounting.invoices.schemas import InvoiceCreate
        
        # This should trigger line 44 in invoices/schemas.py  
        with pytest.raises(ValueError, match="Subtotal must be greater than 0"):
            InvoiceCreate(
                invoice_number="INV-001", amount=Decimal("100.00"), subtotal_amount=Decimal("0.00"),
                description="Test", issue_date="2024-01-01T00:00:00Z", property_id=1
            )
