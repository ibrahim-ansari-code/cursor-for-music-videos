"""
Unit tests for billing webhooks main handler.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, Request, BackgroundTasks

from Backend.api.billing.webhooks import stripe_webhook_handler


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_request():
    """Create mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.body = AsyncMock(return_value=b'{"type": "customer.subscription.created"}')
    request.headers = {"stripe-signature": "test_signature"}
    return request


@pytest.fixture
def mock_background_tasks():
    """Create mock BackgroundTasks."""
    return MagicMock(spec=BackgroundTasks)


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


class TestStripeWebhookHandler:
    """Tests for Stripe webhook handler."""
    
    async def test_webhook_missing_signature_header(
        self, mock_background_tasks, mock_session
    ):
        """Test webhook with missing signature header."""
        # Arrange
        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b'{"type": "test"}')
        request.headers = {}  # No stripe-signature header
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await stripe_webhook_handler(request, mock_background_tasks, mock_session)
        
        assert exc_info.value.status_code == 400
    
    @patch('Backend.api.billing.webhooks.stripe.Webhook.construct_event')
    async def test_webhook_invalid_signature(
        self, mock_construct, mock_request, mock_background_tasks, mock_session
    ):
        """Test webhook with invalid signature."""
        # Arrange
        mock_construct.side_effect = ValueError("Invalid signature")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await stripe_webhook_handler(mock_request, mock_background_tasks, mock_session)
        
        assert exc_info.value.status_code == 400

