"""
Unit tests for smart tax selection hierarchy and logic.

Tests the complex priority-based tax selection algorithm and provincial
tax rate lookups in isolation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, Mock
from uuid import uuid4
from decimal import Decimal

from Backend.api.accounting.tax_preferences.service import TaxPreferenceService
from Backend.api.accounting.tax_preferences.schemas import TaxPreferenceResponse, HistoricalTaxUsage
from Backend.models.property import Property
from Backend.models.user import User

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

class TestSmartTaxSelection:
    """Test cases for smart tax selection hierarchy logic."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def tax_service(self, mock_session):
        """Create TaxPreferenceService instance with mock session."""
        return TaxPreferenceService(mock_session)

    @pytest.fixture
    def sample_user_id(self):
        """Generate a sample user ID."""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_priority_hierarchy_property_wins(self, tax_service, sample_user_id):
        """Test that property default has highest priority over all other sources."""
        # Arrange - Mock all levels of the hierarchy
        property_response = TaxPreferenceResponse(
            tax_name="Property HST",
            tax_rate=Decimal("13.00"),
            source="property_default"
        )
        provincial_response = TaxPreferenceResponse(
            tax_name="Provincial GST+PST",
            tax_rate=Decimal("12.00"),
            source="provincial_default"
        )
        user_response = TaxPreferenceResponse(
            tax_name="User GST",
            tax_rate=Decimal("5.00"),
            source="user_default"
        )
        historical_response = HistoricalTaxUsage(
            tax_name="Historical HST",
            tax_rate=Decimal("15.00"),
            usage_count=10,
            last_used="2024-08-15T10:30:00",
            percentage=80.0
        )

        tax_service._get_property_tax_default = AsyncMock(return_value=property_response)
        tax_service._get_provincial_tax_for_property = AsyncMock(return_value=provincial_response)
        tax_service._get_user_tax_default = AsyncMock(return_value=user_response)
        tax_service._get_most_used_tax = AsyncMock(return_value=historical_response)

        # Act
        result = await tax_service.get_smart_tax_for_context(sample_user_id, property_id=1)

        # Assert
        assert result.source == "property_default"
        assert result.tax_name == "PROPERTY HST"
        assert result.confidence == 0.95

        # Verify that only property default was checked (short-circuit)
        tax_service._get_property_tax_default.assert_called_once()
        tax_service._get_provincial_tax_for_property.assert_not_called()
        tax_service._get_user_tax_default.assert_not_called()
        tax_service._get_most_used_tax.assert_not_called()

    @pytest.mark.asyncio
    async def test_priority_hierarchy_provincial_wins(self, tax_service, sample_user_id):
        """Test that provincial default has second priority."""
        # Arrange - No property default, but provincial and others available
        provincial_response = TaxPreferenceResponse(
            tax_name="Provincial GST+PST",
            tax_rate=Decimal("12.00"),
            source="provincial_default"
        )
        user_response = TaxPreferenceResponse(
            tax_name="User GST",
            tax_rate=Decimal("5.00"),
            source="user_default"
        )

        tax_service._get_property_tax_default = AsyncMock(return_value=None)
        tax_service._get_provincial_tax_for_property = AsyncMock(return_value=provincial_response)
        tax_service._get_user_tax_default = AsyncMock(return_value=user_response)

        # Act
        result = await tax_service.get_smart_tax_for_context(sample_user_id, property_id=1)

        # Assert
        assert result.source == "provincial_default"
        assert result.tax_name == "PROVINCIAL GST+PST"
        assert result.confidence == 0.85

        # Verify hierarchy was followed
        tax_service._get_property_tax_default.assert_called_once()
        tax_service._get_provincial_tax_for_property.assert_called_once()
        tax_service._get_user_tax_default.assert_not_called()  # Short-circuited

    @pytest.mark.asyncio
    async def test_priority_hierarchy_user_wins(self, tax_service, sample_user_id):
        """Test that user default has third priority."""
        # Arrange - No property context, user default available
        user_response = TaxPreferenceResponse(
            tax_name="User GST",
            tax_rate=Decimal("5.00"),
            source="user_default"
        )
        historical_response = HistoricalTaxUsage(
            tax_name="Historical HST",
            tax_rate=Decimal("13.00"),
            usage_count=5,
            last_used="2024-08-15T10:30:00",
            percentage=60.0
        )

        tax_service._get_user_tax_default = AsyncMock(return_value=user_response)
        tax_service._get_most_used_tax = AsyncMock(return_value=historical_response)

        # Act - No property_id provided
        result = await tax_service.get_smart_tax_for_context(sample_user_id, property_id=None)

        # Assert
        assert result.source == "user_default"
        assert result.tax_name == "USER GST"
        assert result.confidence == 0.75

        # Verify user default was checked and historical was not
        tax_service._get_user_tax_default.assert_called_once()
        tax_service._get_most_used_tax.assert_not_called()

    @pytest.mark.asyncio
    async def test_priority_hierarchy_historical_wins(self, tax_service, sample_user_id):
        """Test that historical usage has fourth priority."""
        # Arrange - No defaults, only historical data
        historical_response = HistoricalTaxUsage(
            tax_name="Historical HST",
            tax_rate=Decimal("13.00"),
            usage_count=5,
            last_used="2024-08-15T10:30:00",
            percentage=100.0
        )

        tax_service._get_user_tax_default = AsyncMock(return_value=None)
        tax_service._get_most_used_tax = AsyncMock(return_value=historical_response)

        # Act
        result = await tax_service.get_smart_tax_for_context(sample_user_id, property_id=None)

        # Assert
        assert result.source == "historical_usage"
        assert result.tax_name == "Historical HST"
        assert result.confidence == 0.60
        assert "5 times" in result.reasoning

    @pytest.mark.asyncio
    async def test_priority_hierarchy_none_available(self, tax_service, sample_user_id):
        """Test when no tax data is available anywhere."""
        # Arrange - All sources return None/empty
        tax_service._get_user_tax_default = AsyncMock(return_value=None)
        tax_service._get_most_used_tax = AsyncMock(return_value=None)

        # Act
        result = await tax_service.get_smart_tax_for_context(sample_user_id, property_id=None)

        # Assert
        assert result.source == "none"
        assert result.tax_name is None
        assert result.tax_rate is None
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_property_context_skipped_when_none(self, tax_service, sample_user_id):
        """Test that property-related checks are skipped when property_id is None."""
        # Arrange
        user_response = TaxPreferenceResponse(
            tax_name="User GST",
            tax_rate=Decimal("5.00"),
            source="user_default"
        )

        tax_service._get_property_tax_default = AsyncMock()
        tax_service._get_provincial_tax_for_property = AsyncMock()
        tax_service._get_user_tax_default = AsyncMock(return_value=user_response)

        # Act
        result = await tax_service.get_smart_tax_for_context(sample_user_id, property_id=None)

        # Assert
        assert result.source == "user_default"

        # Verify property-related methods were never called
        tax_service._get_property_tax_default.assert_not_called()
        tax_service._get_provincial_tax_for_property.assert_not_called()
        tax_service._get_user_tax_default.assert_called_once()

class TestProvincialTaxLogic:
    """Test cases for provincial tax rate logic."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def tax_service(self, mock_session):
        """Create TaxPreferenceService instance with mock session."""
        return TaxPreferenceService(mock_session)

    @pytest.mark.asyncio
    async def test_get_provincial_tax_for_property_ontario(self, tax_service, mock_session):
        """Test provincial tax lookup for Ontario property."""
        # Arrange
        user_id = str(uuid4())
        property_id = 1
        
        mock_property = MagicMock()
        mock_property.province = "ON"
        tax_service._get_user_property = AsyncMock(return_value=mock_property)

        with patch('Backend.api.accounting.tax_preferences.service.get_provincial_tax_rate') as mock_get_rate:
            mock_get_rate.return_value = ("HST", Decimal("13.00"))

            # Act
            result = await tax_service._get_provincial_tax_for_property(property_id, user_id)

            # Assert
            assert result is not None
            assert result.tax_name == "HST"
            assert result.tax_rate == Decimal("13.00")
            assert result.source == "provincial_default"

            # Verify utility function was called
            mock_get_rate.assert_called_once_with("ON")

    @pytest.mark.asyncio
    async def test_get_provincial_tax_for_property_alberta(self, tax_service, mock_session):
        """Test provincial tax lookup for Alberta property (GST only)."""
        # Arrange
        user_id = str(uuid4())
        property_id = 1
        
        mock_property = MagicMock()
        mock_property.province = "AB"
        tax_service._get_user_property = AsyncMock(return_value=mock_property)

        with patch('Backend.api.accounting.tax_preferences.service.get_provincial_tax_rate') as mock_get_rate:
            mock_get_rate.return_value = ("GST", Decimal("5.00"))

            # Act
            result = await tax_service._get_provincial_tax_for_property(property_id, user_id)

            # Assert
            assert result.tax_name == "GST"
            assert result.tax_rate == Decimal("5.00")

    @pytest.mark.asyncio
    async def test_get_provincial_tax_for_property_no_property(self, tax_service):
        """Test provincial tax lookup when property is not found."""
        # Arrange
        user_id = str(uuid4())
        property_id = 999
        
        tax_service._get_user_property = AsyncMock(return_value=None)

        # Act
        result = await tax_service._get_provincial_tax_for_property(property_id, user_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_provincial_tax_for_property_no_province(self, tax_service):
        """Test provincial tax lookup when property has no province."""
        # Arrange
        user_id = str(uuid4())
        property_id = 1
        
        mock_property = MagicMock()
        mock_property.province = None
        tax_service._get_user_property = AsyncMock(return_value=mock_property)

        # Act
        result = await tax_service._get_provincial_tax_for_property(property_id, user_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_provincial_tax_for_property_invalid_province(self, tax_service):
        """Test provincial tax lookup with invalid province code."""
        # Arrange
        user_id = str(uuid4())
        property_id = 1
        
        mock_property = MagicMock()
        mock_property.province = "XX"  # Invalid province
        tax_service._get_user_property = AsyncMock(return_value=mock_property)

        with patch('Backend.api.accounting.tax_preferences.service.get_provincial_tax_rate') as mock_get_rate:
            mock_get_rate.return_value = None  # Invalid province returns None

            # Act
            result = await tax_service._get_provincial_tax_for_property(property_id, user_id)

            # Assert
            assert result is None
            mock_get_rate.assert_called_once_with("XX")

class TestUserAndPropertyDefaults:
    """Test cases for user and property default retrieval."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def tax_service(self, mock_session):
        """Create TaxPreferenceService instance with mock session."""
        return TaxPreferenceService(mock_session)

    @pytest.mark.asyncio
    async def test_get_user_tax_default_with_data(self, tax_service, mock_session):
        """Test getting user tax default when data exists."""
        # Arrange
        user_id = str(uuid4())
        
        mock_user = MagicMock()
        mock_user.default_tax_name = "HST"
        mock_user.default_tax_rate = Decimal("13.00")
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        # Act
        result = await tax_service._get_user_tax_default(user_id)

        # Assert
        assert result is not None
        assert result.tax_name == "HST"
        assert result.tax_rate == Decimal("13.00")
        assert result.source == "user_default"

    @pytest.mark.asyncio
    async def test_get_user_tax_default_no_user(self, tax_service, mock_session):
        """Test getting user tax default when user doesn't exist."""
        # Arrange
        user_id = str(uuid4())
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await tax_service._get_user_tax_default(user_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_tax_default_no_tax_data(self, tax_service, mock_session):
        """Test getting user tax default when user has no tax preferences."""
        # Arrange
        user_id = str(uuid4())
        
        mock_user = MagicMock()
        mock_user.default_tax_name = None
        mock_user.default_tax_rate = None
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        # Act
        result = await tax_service._get_user_tax_default(user_id)

        # Assert
        assert result is None
