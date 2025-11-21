"""
Unit tests for billing webhook utilities.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from Backend.api.billing.webhook_utils import (
    log_stripe_event,
    log_billing_audit
)


pytestmark = pytest.mark.unit


class TestWebhookUtils:
    """Tests for webhook utilities."""
    
    async def test_log_stripe_event(self):
        """Test log_stripe_event."""
        # Arrange
        event = MagicMock()
        event.id = 'evt_123'
        event.type = 'test'
        event.api_version = '2023-10-16'
        event.to_dict.return_value = {'id': 'evt_123'}
        event.request = None
        
        session = MagicMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        
        # Act
        result = await log_stripe_event(event, session)
        
        # Assert
        session.add.assert_called_once()
        session.commit.assert_called_once()
        assert result.stripe_event_id == 'evt_123'
    
    async def test_log_billing_audit(self):
        """Test log_billing_audit."""
        # Arrange
        session = MagicMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        
        # Act
        await log_billing_audit(
            action="subscription_created",
            actor="system",
            session=session,
            user_id=None,
            audit_metadata={"sub_id": "sub_123"}
        )
        
        # Assert
        session.add.assert_called_once()
        session.commit.assert_called_once()
