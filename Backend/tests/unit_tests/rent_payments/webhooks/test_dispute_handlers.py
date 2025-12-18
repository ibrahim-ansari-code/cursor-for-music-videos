"""
Unit tests for dispute webhook handlers.

Tests all charge.dispute.* webhook event handlers to ensure proper
dispute tracking, status updates, and Sentry alerting.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.rent_payments.webhook_handlers.dispute_handlers import (
    handle_dispute_created,
    handle_dispute_updated,
    handle_dispute_closed,
    handle_dispute_funds_withdrawn,
    handle_dispute_funds_reinstated,
)
from Backend.models.rent_payment_transaction import (
    RentPaymentTransaction,
    RentPaymentTransactionStatus,
)
from Backend.models.rent_payment_dispute import (
    RentPaymentDispute,
    DisputeStatus,
    DisputeReason,
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
    transaction.created_at = datetime.now(timezone.utc)
    transaction.updated_at = datetime.now(timezone.utc)
    return transaction


@pytest.fixture
def mock_dispute():
    """Create mock rent payment dispute."""
    dispute = MagicMock(spec=RentPaymentDispute)
    dispute.id = uuid4()
    dispute.stripe_dispute_id = "dp_test789"
    dispute.transaction_id = uuid4()
    dispute.amount_cents = 200000
    dispute.amount_dollars = 2000.00
    dispute.status = DisputeStatus.WARNING_NEEDS_RESPONSE
    dispute.reason = DisputeReason.FRAUDULENT
    dispute.is_charge_refundable = True
    dispute.created_at = datetime.now(timezone.utc)
    dispute.updated_at = datetime.now(timezone.utc)
    return dispute


@pytest.fixture
def dispute_created():
    """Create mock Dispute created event data."""
    return {
        "id": "dp_test789",
        "object": "dispute",
        "charge": "ch_test456",
        "amount": 200000,
        "currency": "cad",
        "status": "warning_needs_response",
        "reason": "fraudulent",
        "is_charge_refundable": True,
        "evidence_details": {
            "due_by": 1640000000,  # Unix timestamp
        },
    }


# =============================================================================
# Tests: handle_dispute_created
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.dispute_handlers._send_dispute_notification')
@patch('Backend.api.rent_payments.webhook_handlers.dispute_handlers.sentry_sdk')
async def test_handle_dispute_created_success(
    mock_sentry, mock_send_notification, mock_session, mock_transaction, dispute_created
):
    """Test successful dispute created handler."""
    # Arrange
    mock_session.scalar.side_effect = [
        None,              # No existing dispute
        mock_transaction,  # Find transaction by charge_id
    ]
    
    # Act
    await handle_dispute_created(dispute_created, mock_session)
    
    # Assert
    mock_session.add.assert_called()
    mock_session.commit.assert_called_once()
    mock_sentry.capture_message.assert_called_once()
    mock_send_notification.assert_called_once()


@pytest.mark.asyncio
async def test_handle_dispute_created_no_charge_id(mock_session):
    """Test dispute created with missing charge ID."""
    # Arrange
    dispute = {"id": "dp_test789"}  # No charge field
    
    # Act
    await handle_dispute_created(dispute, mock_session)
    
    # Assert
    mock_session.scalar.assert_not_called()


@pytest.mark.asyncio
async def test_handle_dispute_created_no_transaction_found(
    mock_session, dispute_created
):
    """Test dispute created when transaction not found."""
    # Arrange
    mock_session.scalar.return_value = None
    
    # Act
    await handle_dispute_created(dispute_created, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_handle_dispute_created_duplicate_dispute(
    mock_session, mock_transaction, mock_dispute, dispute_created
):
    """Test dispute created when dispute already exists."""
    # Arrange
    mock_session.scalar.side_effect = [
        mock_transaction,  # Find transaction
        mock_dispute,      # Dispute already exists
    ]
    
    # Act
    await handle_dispute_created(dispute_created, mock_session)
    
    # Assert - should return early
    assert mock_session.add.call_count == 0


# =============================================================================
# Tests: handle_dispute_updated
# =============================================================================

@pytest.mark.asyncio
async def test_handle_dispute_updated_success(mock_session, mock_dispute):
    """Test successful dispute updated handler."""
    # Arrange
    dispute = {
        "id": "dp_test789",
        "status": "under_review",
    }
    mock_session.scalar.return_value = mock_dispute
    
    # Act
    await handle_dispute_updated(dispute, mock_session)
    
    # Assert
    assert mock_dispute.status == DisputeStatus.UNDER_REVIEW
    assert mock_dispute.updated_at is not None
    mock_session.add.assert_called_with(mock_dispute)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_dispute_updated_no_dispute_found(mock_session):
    """Test dispute updated when dispute not found."""
    # Arrange
    dispute = {"id": "dp_test789", "status": "under_review"}
    mock_session.scalar.return_value = None
    
    # Act
    await handle_dispute_updated(dispute, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_handle_dispute_updated_missing_dispute_id(mock_session):
    """Test dispute updated with missing dispute ID."""
    # Arrange
    dispute = {"status": "under_review"}  # No id field
    mock_session.scalar.return_value = None
    
    # Act
    await handle_dispute_updated(dispute, mock_session)
    
    # Assert - will still query database with None id
    mock_session.scalar.assert_called_once()


# =============================================================================
# Tests: handle_dispute_closed
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.dispute_handlers._send_dispute_outcome_notification')
async def test_handle_dispute_closed_won(
    mock_send_notification, mock_session, mock_dispute
):
    """Test dispute closed with won outcome."""
    # Arrange
    dispute = {
        "id": "dp_test789",
        "status": "won",
    }
    mock_session.scalar.return_value = mock_dispute
    
    # Act
    await handle_dispute_closed(dispute, mock_session)
    
    # Assert
    assert mock_dispute.status == DisputeStatus.WON
    assert mock_dispute.closed_at is not None
    mock_session.commit.assert_called_once()
    mock_send_notification.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.dispute_handlers._send_dispute_outcome_notification')
async def test_handle_dispute_closed_lost(
    mock_send_notification, mock_session, mock_dispute
):
    """Test dispute closed with lost outcome."""
    # Arrange
    dispute = {
        "id": "dp_test789",
        "status": "lost",
    }
    mock_session.scalar.return_value = mock_dispute
    
    # Act
    await handle_dispute_closed(dispute, mock_session)
    
    # Assert
    assert mock_dispute.status == DisputeStatus.LOST
    assert mock_dispute.closed_at is not None
    mock_send_notification.assert_called_once()


@pytest.mark.asyncio
async def test_handle_dispute_closed_no_dispute_found(mock_session):
    """Test dispute closed when dispute not found."""
    # Arrange
    dispute = {"id": "dp_test789", "status": "won"}
    mock_session.scalar.return_value = None
    
    # Act
    await handle_dispute_closed(dispute, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


# =============================================================================
# Tests: handle_dispute_funds_withdrawn
# =============================================================================

@pytest.mark.asyncio
async def test_handle_dispute_funds_withdrawn_success(mock_session, mock_transaction):
    """Test dispute funds withdrawn handler."""
    # Arrange
    dispute = {"id": "dp_test789", "charge": "ch_test456", "amount": 200000}
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_dispute_funds_withdrawn(dispute, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.REFUNDED
    assert mock_transaction.refunded_at is not None
    mock_session.add.assert_called_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_dispute_funds_withdrawn_no_transaction(mock_session):
    """Test dispute funds withdrawn when transaction not found."""
    # Arrange
    dispute = {"id": "dp_test789", "charge": "ch_test456"}
    mock_session.scalar.return_value = None
    
    # Act
    await handle_dispute_funds_withdrawn(dispute, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


# =============================================================================
# Tests: handle_dispute_funds_reinstated
# =============================================================================

@pytest.mark.asyncio
async def test_handle_dispute_funds_reinstated_success(mock_session):
    """Test dispute funds reinstated handler."""
    # Arrange
    dispute = {"id": "dp_test789"}
    
    # Act - this handler only logs, doesn't update anything
    await handle_dispute_funds_reinstated(dispute, mock_session)
    
    # Assert - no database operations
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_dispute_funds_reinstated_no_dispute_id(mock_session):
    """Test dispute funds reinstated without dispute ID."""
    # Arrange
    dispute = {}  # No id field
    
    # Act - still just logs
    await handle_dispute_funds_reinstated(dispute, mock_session)
    
    # Assert - no database operations
    mock_session.add.assert_not_called()


# =============================================================================
# Tests: Notification Functions
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.dispute_handlers.SendGridService')
async def test_send_dispute_notification(mock_sendgrid_class, mock_session):
    """Test dispute notification sends email."""
    # Import the notification function
    from Backend.api.rent_payments.webhook_handlers.dispute_handlers import (
        _send_dispute_notification,
    )
    from Backend.models.rent_payment_dispute import RentPaymentDispute
    from Backend.models.rent_payment_transaction import RentPaymentTransaction
    
    # Arrange - create more complete mocks with concrete values
    mock_landlord = MagicMock()
    mock_landlord.id = uuid4()
    mock_landlord.email = "landlord@example.com"
    mock_landlord.first_name = "Jane"
    
    mock_transaction = MagicMock(spec=RentPaymentTransaction)
    mock_transaction.id = uuid4()
    mock_transaction.landlord = mock_landlord
    mock_transaction.amount_dollars = 2000.00
    
    mock_dispute = MagicMock(spec=RentPaymentDispute)
    mock_dispute.id = uuid4()
    mock_dispute.amount_cents = 200000
    mock_dispute.reason = "general"
    mock_dispute.created_at = datetime.now(timezone.utc)
    mock_dispute.evidence_due_by = None  # Concrete value, not mock
    
    mock_sendgrid_instance = AsyncMock()
    mock_sendgrid_class.return_value = mock_sendgrid_instance
    
    # Act - function signature is (dispute, transaction, session)
    await _send_dispute_notification(mock_dispute, mock_transaction, mock_session)
    
    # Assert
    mock_sendgrid_instance.send_raw_email.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.dispute_handlers.SendGridService')
async def test_send_dispute_outcome_notification(mock_sendgrid_class, mock_session):
    """Test dispute outcome notification sends email."""
    # Import the notification function
    from Backend.api.rent_payments.webhook_handlers.dispute_handlers import (
        _send_dispute_outcome_notification,
    )
    from Backend.models.rent_payment_dispute import RentPaymentDispute, DisputeStatus
    from Backend.models.rent_payment_transaction import RentPaymentTransaction
    
    # Arrange - create complete mocks with concrete values
    mock_landlord = MagicMock()
    mock_landlord.id = uuid4()
    mock_landlord.email = "landlord@example.com"
    mock_landlord.first_name = "Jane"
    
    transaction_id = uuid4()
    
    mock_transaction = MagicMock(spec=RentPaymentTransaction)
    mock_transaction.id = transaction_id
    mock_transaction.landlord = mock_landlord
    mock_transaction.amount_dollars = 2000.00
    
    mock_dispute = MagicMock(spec=RentPaymentDispute)
    mock_dispute.id = uuid4()
    mock_dispute.transaction_id = transaction_id
    mock_dispute.amount_cents = 200000
    mock_dispute.reason = "general"
    mock_dispute.status = DisputeStatus.WON
    mock_dispute.created_at = datetime.now(timezone.utc)
    mock_dispute.closed_at = datetime.now(timezone.utc)
    
    # The function calls session.get() to fetch the transaction
    mock_session.get.return_value = mock_transaction
    
    mock_sendgrid_instance = AsyncMock()
    mock_sendgrid_class.return_value = mock_sendgrid_instance
    
    # Act - function signature is (dispute, session)
    await _send_dispute_outcome_notification(mock_dispute, mock_session)
    
    # Assert
    mock_sendgrid_instance.send_raw_email.assert_called_once()


# =============================================================================
# Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_dispute_handlers_handle_missing_ids_gracefully(mock_session):
    """Test all dispute handlers gracefully handle missing IDs."""
    # Arrange
    empty_dispute = {}  # No id or charge fields
    mock_session.scalar.return_value = None
    
    # Act - none should raise exceptions
    await handle_dispute_created(empty_dispute, mock_session)
    await handle_dispute_updated(empty_dispute, mock_session)
    await handle_dispute_closed(empty_dispute, mock_session)
    await handle_dispute_funds_withdrawn(empty_dispute, mock_session)
    await handle_dispute_funds_reinstated(empty_dispute, mock_session)
    
    # Assert - should handle gracefully without crashing
    assert True  # Reached here without exception


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.dispute_handlers._send_dispute_notification')
@patch('Backend.api.rent_payments.webhook_handlers.dispute_handlers.sentry_sdk')
async def test_handle_dispute_created_with_evidence_deadline(
    mock_sentry, mock_send_notification, mock_session, mock_transaction
):
    """Test dispute created captures evidence deadline."""
    # Arrange
    dispute = {
        "id": "dp_test789",
        "charge": "ch_test456",
        "amount": 200000,
        "reason": "general",
        "status": "warning_needs_response",
        "evidence_details": {
            "due_by": 1700000000,  # Specific deadline
        },
    }
    mock_session.scalar.side_effect = [None, mock_transaction]  # First check existing, then find transaction
    
    # Act
    await handle_dispute_created(dispute, mock_session)
    
    # Assert - should create dispute with deadline
    mock_session.add.assert_called()
    mock_sentry.capture_message.assert_called_once()


@pytest.mark.asyncio
async def test_handle_dispute_updated_status_transitions(mock_session, mock_dispute):
    """Test various dispute status transitions."""
    # Arrange
    status_transitions = [
        ("warning_needs_response", DisputeStatus.WARNING_NEEDS_RESPONSE),
        ("warning_under_review", DisputeStatus.WARNING_UNDER_REVIEW),
        ("warning_closed", DisputeStatus.WARNING_CLOSED),
        ("needs_response", DisputeStatus.NEEDS_RESPONSE),
        ("under_review", DisputeStatus.UNDER_REVIEW),
        ("charge_refunded", DisputeStatus.CHARGE_REFUNDED),
    ]
    
    # Act & Assert
    for stripe_status, expected_status in status_transitions:
        mock_dispute.status = DisputeStatus.WARNING_NEEDS_RESPONSE  # Reset
        mock_session.scalar.return_value = mock_dispute
        mock_session.reset_mock()
        
        dispute = {"id": "dp_test789", "status": stripe_status}
        await handle_dispute_updated(dispute, mock_session)
        
        assert mock_dispute.status == expected_status
        mock_session.commit.assert_called_once()

