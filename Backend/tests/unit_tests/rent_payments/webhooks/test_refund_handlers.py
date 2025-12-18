"""
Unit tests for refund webhook handlers.

Tests all refund.* webhook event handlers to ensure proper
refund tracking, status updates, and notification handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.rent_payments.webhook_handlers.refund_handlers import (
    handle_refund_created,
    handle_refund_updated,
    handle_refund_failed,
)
from Backend.models.rent_payment_transaction import (
    RentPaymentTransaction,
    RentPaymentTransactionStatus,
)
from Backend.models.rent_payment_refund import (
    RentPaymentRefund,
    RefundStatus,
)

pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_session():
    """Create mock async database session."""
    session = AsyncMock()
    session.scalar = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def mock_transaction():
    """Create mock rent payment transaction."""
    transaction = MagicMock(spec=RentPaymentTransaction)
    transaction.id = uuid4()
    transaction.stripe_payment_intent_id = "pi_test123"
    transaction.stripe_charge_id = "ch_test456"
    transaction.amount_cents = 200000  # $2000
    transaction.amount_dollars = 2000.00
    transaction.status = RentPaymentTransactionStatus.SUCCEEDED
    transaction.tenant_id = uuid4()
    transaction.lease_id = 123
    transaction.landlord_user_id = uuid4()
    transaction.payment_id = None
    transaction.total_refunded_cents = 200000  # Fully refunded
    transaction.created_at = datetime.now(timezone.utc)
    transaction.updated_at = datetime.now(timezone.utc)
    return transaction


@pytest.fixture
def mock_refund():
    """Create mock rent payment refund."""
    refund = MagicMock(spec=RentPaymentRefund)
    refund.id = uuid4()
    refund.stripe_refund_id = "re_test789"
    refund.transaction_id = uuid4()
    refund.amount_cents = 200000
    refund.amount_dollars = 2000.00
    refund.status = RefundStatus.PENDING
    refund.reason = "requested_by_customer"
    refund.transaction = None
    refund.created_at = datetime.now(timezone.utc)
    refund.updated_at = datetime.now(timezone.utc)
    return refund


@pytest.fixture
def refund_created():
    """Create mock Refund created event data."""
    return {
        "id": "re_test789",
        "object": "refund",
        "charge": "ch_test456",
        "amount": 200000,
        "currency": "cad",
        "status": "succeeded",
        "reason": "requested_by_customer",
    }


@pytest.fixture
def refund_failed():
    """Create mock Refund failed event data."""
    return {
        "id": "re_test789",
        "object": "refund",
        "charge": "ch_test456",
        "amount": 200000,
        "currency": "cad",
        "status": "failed",
        "failure_reason": "insufficient_funds",
    }


# =============================================================================
# Tests: handle_refund_created
# =============================================================================

@pytest.mark.asyncio
async def test_handle_refund_created_new_refund(mock_session, refund_created):
    """Test refund created with new refund (no existing record)."""
    # Arrange
    mock_session.scalar.return_value = None  # No existing refund
    
    # Act
    await handle_refund_created(refund_created, mock_session)
    
    # Assert - should just log, not update anything
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_refund_created_existing_refund(mock_session, mock_refund, refund_created):
    """Test refund created when refund already exists."""
    # Arrange
    mock_session.scalar.return_value = mock_refund  # Refund already exists
    
    # Act
    await handle_refund_created(refund_created, mock_session)
    
    # Assert - should return early
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_refund_created_no_refund_id(mock_session):
    """Test refund created with missing refund ID."""
    # Arrange
    refund = {"charge": "ch_test456"}  # No id field
    mock_session.scalar.return_value = None
    
    # Act
    await handle_refund_created(refund, mock_session)
    
    # Assert - will check database with None id
    mock_session.scalar.assert_called_once()


# =============================================================================
# Tests: handle_refund_updated
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.refund_handlers._send_refund_notification')
async def test_handle_refund_updated_to_succeeded(
    mock_send_notification, mock_session, mock_refund, mock_transaction
):
    """Test refund updated to succeeded status."""
    # Arrange
    refund = {
        "id": "re_test789",
        "status": "succeeded",
        "amount": 200000,
    }
    mock_refund.status = RefundStatus.PENDING
    mock_refund.transaction = mock_transaction
    mock_session.scalar.return_value = mock_refund
    mock_session.get.return_value = mock_transaction
    
    # Act
    await handle_refund_updated(refund, mock_session)
    
    # Assert
    assert mock_refund.status == RefundStatus.SUCCEEDED
    assert mock_refund.succeeded_at is not None
    mock_session.add.assert_called()
    mock_session.commit.assert_called_once()
    mock_send_notification.assert_called_once_with(mock_refund, mock_session)


@pytest.mark.asyncio
async def test_handle_refund_updated_no_refund_found(mock_session):
    """Test refund updated when refund not found."""
    # Arrange
    refund = {"id": "re_test789", "status": "succeeded"}
    mock_session.scalar.return_value = None
    
    # Act
    await handle_refund_updated(refund, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.refund_handlers._send_refund_notification')
async def test_handle_refund_updated_full_refund_updates_transaction(
    mock_send_notification, mock_session, mock_refund, mock_transaction
):
    """Test refund updated marks transaction as refunded when fully refunded."""
    # Arrange
    refund = {
        "id": "re_test789",
        "status": "succeeded",
        "amount": 200000,
    }
    mock_refund.transaction = mock_transaction
    mock_refund.transaction_id = mock_transaction.id
    mock_refund.amount_cents = 200000  # This refund is for the full amount
    mock_refund.status = RefundStatus.SUCCEEDED
    
    # Mock the refunds relationship so total_refunded_cents property works
    mock_transaction.refunds = [mock_refund]
    mock_transaction.amount_cents = 200000
    # Mock the property to return the calculated value
    type(mock_transaction).total_refunded_cents = property(lambda self: sum(r.amount_cents for r in self.refunds if r.status != RefundStatus.FAILED))
    
    mock_session.scalar.return_value = mock_refund
    mock_session.get.return_value = mock_transaction
    
    # Act
    await handle_refund_updated(refund, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.REFUNDED
    assert mock_transaction.refunded_at is not None


@pytest.mark.asyncio
async def test_handle_refund_updated_to_failed(mock_session, mock_refund):
    """Test refund updated to failed status."""
    # Arrange
    refund = {
        "id": "re_test789",
        "status": "failed",
        "failure_reason": "insufficient_funds",
    }
    mock_refund.transaction = None
    mock_session.scalar.return_value = mock_refund
    
    # Act
    await handle_refund_updated(refund, mock_session)
    
    # Assert
    assert mock_refund.status == RefundStatus.FAILED
    assert mock_refund.failed_at is not None
    assert mock_refund.failure_reason == "insufficient_funds"
    mock_session.commit.assert_called_once()


# =============================================================================
# Tests: handle_refund_failed
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.refund_handlers._send_refund_failure_notification')
async def test_handle_refund_failed_success(
    mock_send_notification, mock_session, mock_refund, refund_failed
):
    """Test successful refund failed handler."""
    # Arrange
    mock_refund.transaction = MagicMock()  # Has transaction for notification
    mock_session.scalar.return_value = mock_refund
    
    # Act
    await handle_refund_failed(refund_failed, mock_session)
    
    # Assert
    assert mock_refund.status == RefundStatus.FAILED
    assert mock_refund.failed_at is not None
    assert mock_refund.failure_reason == "insufficient_funds"
    mock_session.add.assert_called_with(mock_refund)
    mock_session.commit.assert_called_once()
    mock_send_notification.assert_called_once_with(mock_refund, mock_session)


@pytest.mark.asyncio
async def test_handle_refund_failed_no_refund_found(mock_session, refund_failed):
    """Test refund failed when refund not found."""
    # Arrange
    mock_session.scalar.return_value = None
    
    # Act
    await handle_refund_failed(refund_failed, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.refund_handlers._send_refund_failure_notification')
async def test_handle_refund_failed_no_failure_reason(
    mock_send_notification, mock_session, mock_refund
):
    """Test refund failed without failure reason."""
    # Arrange
    refund = {
        "id": "re_test789",
        "status": "failed",
    }  # No failure_reason
    mock_refund.transaction = MagicMock()
    mock_session.scalar.return_value = mock_refund
    
    # Act
    await handle_refund_failed(refund, mock_session)
    
    # Assert
    assert mock_refund.status == RefundStatus.FAILED
    assert mock_refund.failure_reason is None
    mock_send_notification.assert_called_once()


@pytest.mark.asyncio
async def test_handle_refund_failed_no_transaction(mock_session, mock_refund):
    """Test refund failed with no transaction (no notification sent)."""
    # Arrange
    refund = {
        "id": "re_test789",
        "status": "failed",
        "failure_reason": "test_failure",
    }
    mock_refund.transaction = None  # No transaction
    mock_session.scalar.return_value = mock_refund
    
    # Act
    await handle_refund_failed(refund, mock_session)
    
    # Assert
    assert mock_refund.status == RefundStatus.FAILED
    mock_session.commit.assert_called_once()


# =============================================================================
# Tests: Notification Functions
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.refund_handlers.SendGridService')
async def test_send_refund_notification_success(
    mock_sendgrid_class, mock_session, mock_refund, mock_transaction
):
    """Test refund notification sends email correctly."""
    # Import the notification function
    from Backend.api.rent_payments.webhook_handlers.refund_handlers import (
        _send_refund_notification,
    )
    
    # Arrange
    mock_tenant = MagicMock()
    mock_tenant.id = uuid4()
    mock_tenant.email = "tenant@example.com"
    mock_tenant.first_name = "John"
    
    mock_transaction.tenant = mock_tenant
    mock_session.get.return_value = mock_transaction
    
    mock_sendgrid_instance = AsyncMock()
    mock_sendgrid_class.return_value = mock_sendgrid_instance
    
    # Act
    await _send_refund_notification(mock_refund, mock_session)
    
    # Assert
    mock_sendgrid_instance.send_raw_email.assert_called_once()


@pytest.mark.asyncio
async def test_send_refund_notification_no_transaction(mock_session, mock_refund):
    """Test refund notification when transaction not found."""
    # Import the notification function
    from Backend.api.rent_payments.webhook_handlers.refund_handlers import (
        _send_refund_notification,
    )
    
    # Arrange
    mock_session.get.return_value = None
    
    # Act
    await _send_refund_notification(mock_refund, mock_session)
    
    # Assert - should return early without error
    mock_session.get.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.refund_handlers.SendGridService')
@patch('Backend.api.rent_payments.webhook_handlers.refund_handlers.logger')
async def test_send_refund_notification_email_failure(
    mock_logger, mock_sendgrid_class, mock_session, mock_refund, mock_transaction
):
    """Test refund notification handles email send failure gracefully."""
    # Import the notification function
    from Backend.api.rent_payments.webhook_handlers.refund_handlers import (
        _send_refund_notification,
    )
    
    # Arrange
    mock_tenant = MagicMock()
    mock_tenant.email = "tenant@example.com"
    mock_tenant.first_name = "John"
    mock_transaction.tenant = mock_tenant
    mock_session.get.return_value = mock_transaction
    
    mock_sendgrid_instance = AsyncMock()
    mock_sendgrid_instance.send_raw_email.side_effect = Exception("Email send failed")
    mock_sendgrid_class.return_value = mock_sendgrid_instance
    
    # Act - should not raise exception
    await _send_refund_notification(mock_refund, mock_session)
    
    # Assert
    mock_logger.error.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.refund_handlers.SendGridService')
async def test_send_refund_failure_notification_success(
    mock_sendgrid_class, mock_session, mock_refund, mock_transaction
):
    """Test refund failure notification sends email correctly."""
    # Import the notification function
    from Backend.api.rent_payments.webhook_handlers.refund_handlers import (
        _send_refund_failure_notification,
    )
    
    # Arrange
    mock_landlord = MagicMock()
    mock_landlord.id = uuid4()
    mock_landlord.email = "landlord@example.com"
    mock_landlord.first_name = "Jane"
    
    mock_transaction.landlord = mock_landlord
    mock_session.get.return_value = mock_transaction
    
    mock_sendgrid_instance = AsyncMock()
    mock_sendgrid_class.return_value = mock_sendgrid_instance
    
    # Act
    await _send_refund_failure_notification(mock_refund, mock_session)
    
    # Assert
    mock_sendgrid_instance.send_raw_email.assert_called_once()


# =============================================================================
# Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_refund_handlers_handle_none_refund_id(mock_session):
    """Test refund handlers with None refund ID."""
    # Arrange
    empty_refund = {"status": "succeeded"}  # No id field
    mock_session.scalar.return_value = None
    
    # Act - should not crash
    await handle_refund_created(empty_refund, mock_session)
    await handle_refund_updated(empty_refund, mock_session)
    await handle_refund_failed(empty_refund, mock_session)
    
    # Assert - will attempt database lookups with None
    assert mock_session.scalar.call_count == 3


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.refund_handlers._send_refund_notification')
async def test_handle_refund_updated_partial_refund(
    mock_send_notification, mock_session, mock_refund, mock_transaction
):
    """Test refund updated with partial refund (doesn't mark transaction as refunded)."""
    # Arrange
    refund = {
        "id": "re_test789",
        "status": "succeeded",
    }
    mock_refund.transaction = mock_transaction
    mock_transaction.total_refunded_cents = 100000  # Partial (50%)
    mock_transaction.amount_cents = 200000
    mock_session.scalar.return_value = mock_refund
    mock_session.get.return_value = mock_transaction
    
    # Act
    await handle_refund_updated(refund, mock_session)
    
    # Assert - transaction status should NOT change to refunded
    assert mock_transaction.status == RentPaymentTransactionStatus.SUCCEEDED


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.refund_handlers._send_refund_notification')
async def test_handle_refund_updated_no_transaction_for_refund(
    mock_send_notification, mock_session, mock_refund
):
    """Test refund updated when transaction not found."""
    # Arrange
    refund = {
        "id": "re_test789",
        "status": "succeeded",
    }
    mock_refund.transaction = None
    mock_refund.transaction_id = uuid4()
    mock_session.scalar.return_value = mock_refund
    mock_session.get.return_value = None  # No transaction
    
    # Act
    await handle_refund_updated(refund, mock_session)
    
    # Assert - should still update refund status
    assert mock_refund.status == RefundStatus.SUCCEEDED
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.refund_handlers._send_refund_failure_notification')
async def test_handle_refund_failed_idempotent(
    mock_send_notification, mock_session, mock_refund
):
    """Test refund failed is idempotent when called multiple times."""
    # Arrange
    refund = {
        "id": "re_test789",
        "status": "failed",
        "failure_reason": "insufficient_funds",
    }
    mock_refund.status = RefundStatus.FAILED  # Already failed
    mock_refund.transaction = MagicMock()
    mock_session.scalar.return_value = mock_refund
    
    # Act
    await handle_refund_failed(refund, mock_session)
    
    # Assert - should be idempotent
    assert mock_refund.status == RefundStatus.FAILED
    mock_session.commit.assert_called_once()
    mock_send_notification.assert_called_once()
