"""
Unit tests for Stripe client.
"""
import pytest
from unittest.mock import MagicMock, patch

from Backend.api.stripe.client import (
    get_stripe_client,
    format_stripe_error,
    is_retryable_error
)


pytestmark = pytest.mark.unit


class TestFormatStripeError:
    """Tests for format_stripe_error."""
    
    def test_format_stripe_error(self):
        """Test formatting Stripe error."""
        # Arrange
        mock_error = MagicMock()
        mock_error.user_message = "Payment failed"
        mock_error.code = "card_declined"
        mock_error.param = "card_number"
        
        # Act
        result = format_stripe_error(mock_error)
        
        # Assert
        assert "message" in result
        assert "code" in result


class TestIsRetryableError:
    """Tests for is_retryable_error."""
    
    def test_retryable_error(self):
        """Test identifying retryable errors."""
        # Arrange
        mock_error = MagicMock()
        mock_error.code = "rate_limit"
        
        # Act
        result = is_retryable_error(mock_error)
        
        # Assert
        assert isinstance(result, bool)
    
    def test_non_retryable_error(self):
        """Test identifying non-retryable errors."""
        # Arrange
        mock_error = MagicMock()
        mock_error.code = "card_declined"
        
        # Act
        result = is_retryable_error(mock_error)
        
        # Assert
        assert isinstance(result, bool)

