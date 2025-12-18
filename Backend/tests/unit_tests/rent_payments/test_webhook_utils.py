"""
Unit tests for rent payment webhook utility functions.

Tests cover:
- Webhook event logging for audit trail
- Event status updates
- Idempotency checks
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone

from Backend.api.rent_payments.webhook_utils import (
    log_webhook_event,
    update_webhook_event_status,
    check_event_already_processed,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_stripe_event():
    """Create a mock Stripe event."""
    event = MagicMock()
    event.id = "evt_test123"
    event.type = "payment_intent.succeeded"
    event.api_version = "2023-10-16"
    event.to_dict.return_value = {
        "id": "evt_test123",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_test123"}}
    }
    event.request = MagicMock()
    event.request.id = "req_test123"
    return event


# =============================================================================
# Tests: log_webhook_event
# =============================================================================

@pytest.mark.asyncio
async def test_log_webhook_event_success(mock_session, mock_stripe_event):
    """Test logging a successful webhook event."""
    # Arrange
    # Mock refresh to populate ID
    async def mock_refresh(obj):
        if hasattr(obj, 'stripe_event_id'):
            obj.id = 1
    mock_session.refresh.side_effect = mock_refresh
    
    # Act
    result = await log_webhook_event(
        mock_stripe_event,
        mock_session,
        processed=True,
        error=None,
        stripe_account_id="acct_test123"
    )
    
    # Assert
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    assert result.id == 1


@pytest.mark.asyncio
async def test_log_webhook_event_with_error(mock_session, mock_stripe_event):
    """Test logging a failed webhook event with error."""
    # Arrange
    async def mock_refresh(obj):
        if hasattr(obj, 'stripe_event_id'):
            obj.id = 1
    mock_session.refresh.side_effect = mock_refresh
    
    # Act
    result = await log_webhook_event(
        mock_stripe_event,
        mock_session,
        processed=False,
        error="Payment intent not found",
        stripe_account_id="acct_test123"
    )
    
    # Assert
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    assert result.id == 1


@pytest.mark.asyncio
async def test_log_webhook_event_no_request_id(mock_session, mock_stripe_event):
    """Test logging event when Stripe request has no ID."""
    # Arrange
    mock_stripe_event.request = None
    
    async def mock_refresh(obj):
        if hasattr(obj, 'stripe_event_id'):
            obj.id = 1
    mock_session.refresh.side_effect = mock_refresh
    
    # Act
    result = await log_webhook_event(
        mock_stripe_event,
        mock_session,
        processed=True
    )
    
    # Assert
    mock_session.add.assert_called_once()
    assert result.id == 1


# =============================================================================
# Tests: update_webhook_event_status
# =============================================================================

@pytest.mark.asyncio
async def test_update_webhook_event_status_success(mock_session):
    """Test updating webhook event status to processed."""
    # Arrange
    mock_event_log = MagicMock()
    mock_event_log.id = 1
    mock_event_log.stripe_event_id = "evt_test123"
    mock_event_log.processed = False
    mock_event_log.processing_error = None
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_event_log
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await update_webhook_event_status(
        "evt_test123",
        mock_session,
        processed=True,
        error=None
    )
    
    # Assert
    assert result is not None
    assert result.id == 1
    mock_session.add.assert_called_once_with(mock_event_log)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_webhook_event_status_with_error(mock_session):
    """Test updating webhook event status with error."""
    # Arrange
    mock_event_log = MagicMock()
    mock_event_log.id = 1
    mock_event_log.stripe_event_id = "evt_test123"
    mock_event_log.processed = True
    mock_event_log.processing_error = None
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_event_log
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await update_webhook_event_status(
        "evt_test123",
        mock_session,
        processed=False,
        error="Database connection error"
    )
    
    # Assert
    assert result is not None
    assert result.id == 1
    mock_session.add.assert_called_once_with(mock_event_log)


@pytest.mark.asyncio
async def test_update_webhook_event_status_not_found(mock_session):
    """Test updating webhook event status when event not found."""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await update_webhook_event_status(
        "evt_nonexistent",
        mock_session,
        processed=True
    )
    
    # Assert
    assert result is None
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


# =============================================================================
# Tests: check_event_already_processed
# =============================================================================

@pytest.mark.asyncio
async def test_check_event_already_processed_true(mock_session):
    """Test checking event that was already processed."""
    # Arrange
    mock_event_log = MagicMock()
    mock_event_log.stripe_event_id = "evt_test123"
    mock_event_log.event_type = "payment_intent.succeeded"
    mock_event_log.processed = True
    mock_event_log.created_at = datetime.now(timezone.utc)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_event_log
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await check_event_already_processed("evt_test123", mock_session)
    
    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_check_event_already_processed_false(mock_session):
    """Test checking event that hasn't been processed yet."""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await check_event_already_processed("evt_new123", mock_session)
    
    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_check_event_already_processed_but_failed(mock_session):
    """Test checking event that was logged but processing failed."""
    # Arrange
    mock_event_log = MagicMock()
    mock_event_log.stripe_event_id = "evt_test123"
    mock_event_log.event_type = "payment_intent.failed"
    mock_event_log.processed = False
    mock_event_log.processing_error = "Something went wrong"
    mock_event_log.created_at = datetime.now(timezone.utc)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_event_log
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await check_event_already_processed("evt_test123", mock_session)
    
    # Assert
    # Even if processing failed, event exists so return True (don't retry)
    assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

