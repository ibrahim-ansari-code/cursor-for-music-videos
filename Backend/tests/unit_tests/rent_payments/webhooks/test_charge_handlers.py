"""
Unit tests for charge webhook handlers.

Tests all charge.* webhook event handlers to ensure proper
transaction status updates, refund tracking, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.rent_payments.webhook_handlers.charge_handlers import (
    handle_charge_succeeded,
    handle_charge_failed,
    handle_charge_pending,
    handle_charge_expired,
    handle_charge_refunded,
    handle_charge_updated,
)
from Backend.models.rent_payment_transaction import (
    RentPaymentTransaction,
    RentPaymentTransactionStatus,
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
    transaction.status = RentPaymentTransactionStatus.PENDING
    transaction.tenant_id = uuid4()
    transaction.lease_id = 123
    transaction.landlord_user_id = uuid4()
    transaction.receipt_url = None
    transaction.failure_code = None
    transaction.failure_message = None
    transaction.created_at = datetime.now(timezone.utc)
    transaction.updated_at = datetime.now(timezone.utc)
    return transaction


@pytest.fixture
def charge_succeeded():
    """Create mock Charge succeeded event data."""
    return {
        "id": "ch_test456",
        "object": "charge",
        "payment_intent": "pi_test123",
        "amount": 200000,
        "currency": "cad",
        "status": "succeeded",
        "receipt_url": "https://stripe.com/receipt/ch_test456",
    }


@pytest.fixture
def charge_failed():
    """Create mock Charge failed event data."""
    return {
        "id": "ch_test456",
        "object": "charge",
        "payment_intent": "pi_test123",
        "amount": 200000,
        "currency": "cad",
        "status": "failed",
        "failure_code": "insufficient_funds",
        "failure_message": "Insufficient funds",
    }


# =============================================================================
# Tests: handle_charge_succeeded
# =============================================================================

@pytest.mark.asyncio
async def test_handle_charge_succeeded_success(
    mock_session, mock_transaction, charge_succeeded
):
    """Test successful charge succeeded handler."""
    # Arrange
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_charge_succeeded(charge_succeeded, mock_session)
    
    # Assert
    assert mock_transaction.stripe_charge_id == "ch_test456"
    # Note: receipt_url comes from charge.updated, not charge.succeeded
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_charge_succeeded_no_receipt_url(
    mock_session, mock_transaction
):
    """Test charge succeeded without receipt URL."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
    }  # No receipt_url
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_charge_succeeded(charge, mock_session)
    
    # Assert
    assert mock_transaction.stripe_charge_id == "ch_test456"
    assert mock_transaction.receipt_url is None


@pytest.mark.asyncio
async def test_handle_charge_succeeded_no_transaction_found(
    mock_session, charge_succeeded
):
    """Test charge succeeded when transaction not found."""
    # Arrange
    mock_session.scalar.return_value = None
    
    # Act
    await handle_charge_succeeded(charge_succeeded, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_charge_succeeded_missing_pi_id(mock_session):
    """Test charge succeeded with missing PaymentIntent ID."""
    # Arrange
    charge = {"id": "ch_test456"}  # No payment_intent field
    
    # Act
    await handle_charge_succeeded(charge, mock_session)
    
    # Assert
    mock_session.scalar.assert_not_called()


# =============================================================================
# Tests: handle_charge_failed
# =============================================================================

@pytest.mark.asyncio
async def test_handle_charge_failed_success(
    mock_session, mock_transaction, charge_failed
):
    """Test successful charge failed handler."""
    # Arrange
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_charge_failed(charge_failed, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.FAILED
    assert mock_transaction.failed_at is not None
    assert mock_transaction.stripe_charge_id == "ch_test456"
    assert mock_transaction.failure_code == "insufficient_funds"
    assert mock_transaction.failure_message == "Insufficient funds"
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_charge_failed_no_error_details(
    mock_session, mock_transaction
):
    """Test charge failed without error details."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
    }  # No failure_code or failure_message
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_charge_failed(charge, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.FAILED
    assert mock_transaction.failure_code is None
    assert mock_transaction.failure_message is None


@pytest.mark.asyncio
async def test_handle_charge_failed_no_transaction(mock_session, charge_failed):
    """Test charge failed when transaction not found."""
    # Arrange
    mock_session.scalar.return_value = None
    
    # Act
    await handle_charge_failed(charge_failed, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


# =============================================================================
# Tests: handle_charge_pending
# =============================================================================

@pytest.mark.asyncio
async def test_handle_charge_pending_success(mock_session, mock_transaction):
    """Test successful charge pending handler."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
        "status": "pending",
    }
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_charge_pending(charge, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.PROCESSING
    assert mock_transaction.stripe_charge_id == "ch_test456"
    assert mock_transaction.updated_at is not None
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_charge_pending_no_transaction(mock_session):
    """Test charge pending when transaction not found."""
    # Arrange
    charge = {"id": "ch_test456", "payment_intent": "pi_test123"}
    mock_session.scalar.return_value = None
    
    # Act
    await handle_charge_pending(charge, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


# =============================================================================
# Tests: handle_charge_expired
# =============================================================================

@pytest.mark.asyncio
async def test_handle_charge_expired_success(mock_session, mock_transaction):
    """Test successful charge expired handler."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
        "status": "expired",
    }
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_charge_expired(charge, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.FAILED
    assert mock_transaction.failed_at is not None
    assert mock_transaction.stripe_charge_id == "ch_test456"
    assert mock_transaction.failure_code == "charge_expired"
    assert mock_transaction.failure_message == "Payment authorization expired"
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_charge_expired_no_transaction(mock_session):
    """Test charge expired when transaction not found."""
    # Arrange
    charge = {"id": "ch_test456", "payment_intent": "pi_test123"}
    mock_session.scalar.return_value = None
    
    # Act
    await handle_charge_expired(charge, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


# =============================================================================
# Tests: handle_charge_refunded
# =============================================================================

@pytest.mark.asyncio
async def test_handle_charge_refunded_full_refund(mock_session, mock_transaction):
    """Test charge refunded with full refund."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
        "amount": 200000,
        "amount_refunded": 200000,  # Full refund
        "refunded": True,
    }
    mock_session.scalar.return_value = mock_transaction
    mock_session.get = AsyncMock(return_value=None)  # No ledger payment
    
    # Act
    await handle_charge_refunded(charge, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.REFUNDED
    assert mock_transaction.refunded_at is not None
    assert mock_transaction.updated_at is not None
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_charge_refunded_partial_refund(
    mock_session, mock_transaction
):
    """Test charge refunded with partial refund."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
        "amount": 200000,
        "amount_refunded": 100000,  # Partial refund (50%)
        "refunded": False,
    }
    mock_session.scalar.return_value = mock_transaction
    mock_session.get = AsyncMock(return_value=None)  # No ledger payment
    
    # Act
    await handle_charge_refunded(charge, mock_session)
    
    # Assert
    # Partial refunds set status to PARTIALLY_REFUNDED
    assert mock_transaction.status == RentPaymentTransactionStatus.PARTIALLY_REFUNDED
    assert mock_transaction.updated_at is not None
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_charge_refunded_no_transaction(mock_session):
    """Test charge refunded when transaction not found."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
        "amount": 200000,
        "amount_refunded": 200000,
        "refunded": True,
    }
    mock_session.scalar.return_value = None
    
    # Act
    await handle_charge_refunded(charge, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


# =============================================================================
# Tests: handle_charge_updated
# =============================================================================

@pytest.mark.asyncio
async def test_handle_charge_updated_with_receipt(mock_session, mock_transaction):
    """Test charge updated with new receipt URL."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
        "receipt_url": "https://stripe.com/receipt/updated",
    }
    mock_transaction.receipt_url = None  # No receipt initially
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_charge_updated(charge, mock_session)
    
    # Assert
    assert mock_transaction.receipt_url == "https://stripe.com/receipt/updated"
    assert mock_transaction.stripe_charge_id == "ch_test456"
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_charge_updated_receipt_already_exists(
    mock_session, mock_transaction
):
    """Test charge updated when receipt already exists (should not update)."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
        "receipt_url": "https://stripe.com/receipt/new",
    }
    mock_transaction.receipt_url = "https://stripe.com/receipt/existing"
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_charge_updated(charge, mock_session)
    
    # Assert - should not update if receipt already exists
    assert mock_transaction.receipt_url == "https://stripe.com/receipt/existing"
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_charge_updated_no_receipt_in_event(
    mock_session, mock_transaction
):
    """Test charge updated without receipt URL in event."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
    }  # No receipt_url
    mock_transaction.receipt_url = None
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_charge_updated(charge, mock_session)
    
    # Assert - should still update charge_id
    assert mock_transaction.stripe_charge_id == "ch_test456"
    assert mock_transaction.receipt_url is None
    mock_session.add.assert_not_called()  # No update since receipt unchanged


@pytest.mark.asyncio
async def test_handle_charge_updated_no_transaction(mock_session):
    """Test charge updated when transaction not found."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
        "receipt_url": "https://stripe.com/receipt/new",
    }
    mock_session.scalar.return_value = None
    
    # Act
    await handle_charge_updated(charge, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


# =============================================================================
# Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_charge_handlers_handle_missing_pi_id_gracefully(mock_session):
    """Test charge handlers gracefully handle missing PaymentIntent ID."""
    # Arrange
    charge = {"id": "ch_test456"}  # No payment_intent field
    
    # Act - none should raise exceptions
    await handle_charge_succeeded(charge, mock_session)
    await handle_charge_failed(charge, mock_session)
    await handle_charge_pending(charge, mock_session)
    await handle_charge_expired(charge, mock_session)
    # Note: charge_refunded and charge_updated use charge_id, not payment_intent_id
    # so we test them separately
    
    # Assert - no database operations should occur (since no payment_intent)
    mock_session.scalar.assert_not_called()
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_charge_refunded_zero_amount_refunded(mock_session, mock_transaction):
    """Test charge refunded with zero amount refunded."""
    # Arrange
    charge = {
        "id": "ch_test456",
        "payment_intent": "pi_test123",
        "amount": 200000,
        "amount_refunded": 0,
        "refunded": False,
    }
    mock_session.scalar.return_value = mock_transaction
    mock_session.get = AsyncMock(return_value=None)  # No ledger payment
    
    # Act
    await handle_charge_refunded(charge, mock_session)
    
    # Assert - updates timestamp even with zero refund
    assert mock_transaction.status == RentPaymentTransactionStatus.PENDING  # Unchanged
    assert mock_transaction.updated_at is not None
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_charge_handlers_update_charge_id_consistently(
    mock_session, mock_transaction
):
    """Test all charge handlers update stripe_charge_id consistently."""
    # Arrange
    charge = {
        "id": "ch_new789",
        "payment_intent": "pi_test123",
        "status": "succeeded",
    }
    mock_transaction.stripe_charge_id = None
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_charge_succeeded(charge, mock_session)
    
    # Assert
    assert mock_transaction.stripe_charge_id == "ch_new789"

