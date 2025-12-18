"""
Unit tests for payment intent webhook handlers.

Tests all payment_intent.* webhook event handlers to ensure proper
transaction status updates, ledger integration, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.rent_payments.webhook_handlers.payment_intent_handlers import (
    handle_payment_intent_succeeded,
    handle_payment_intent_failed,
    handle_payment_intent_canceled,
    handle_payment_intent_processing,
    handle_payment_intent_requires_action,
    handle_payment_intent_amount_capturable_updated,
    handle_payment_intent_partially_funded,
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
    transaction.amount_cents = 200000  # $2000
    transaction.amount_dollars = 2000.00
    transaction.status = RentPaymentTransactionStatus.PENDING
    transaction.tenant_id = uuid4()
    transaction.lease_id = 123
    transaction.landlord_user_id = uuid4()
    transaction.payment_id = None
    transaction.succeeded_at = None
    transaction.failed_at = None
    transaction.created_at = datetime.now(timezone.utc)
    transaction.updated_at = datetime.now(timezone.utc)
    transaction.payment_method_type = None
    transaction.payment_method_last_four = None
    transaction.payment_method_bank_name = None
    transaction.stripe_charge_id = None
    transaction.receipt_url = None
    transaction.failure_code = None
    transaction.failure_message = None
    return transaction


@pytest.fixture
def payment_intent_succeeded():
    """Create mock PaymentIntent succeeded event data."""
    return {
        "id": "pi_test123",
        "object": "payment_intent",
        "amount": 200000,
        "currency": "cad",
        "status": "succeeded",
        "payment_method_details": {
            "card": {
                "brand": "visa",
                "last4": "4242",
                "exp_month": 12,
                "exp_year": 2025,
            }
        },
    }


@pytest.fixture
def payment_intent_failed():
    """Create mock PaymentIntent failed event data."""
    return {
        "id": "pi_test123",
        "object": "payment_intent",
        "amount": 200000,
        "currency": "cad",
        "status": "requires_payment_method",
        "last_payment_error": {
            "code": "card_declined",
            "message": "Your card was declined",
            "type": "card_error",
        },
    }


# =============================================================================
# Tests: handle_payment_intent_succeeded
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_intent_succeeded_success(
    mock_session, mock_transaction, payment_intent_succeeded
):
    """Test successful payment intent succeeded handler."""
    # Arrange
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_payment_intent_succeeded(payment_intent_succeeded, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.SUCCEEDED
    assert mock_transaction.succeeded_at is not None
    assert mock_transaction.payment_method_type == "card"
    assert mock_transaction.payment_method_last_four == "4242"
    # add() is called twice: once for transaction, once for ledger payment
    assert mock_session.add.call_count == 2
    assert mock_session.commit.call_count == 2  # Once for transaction, once for ledger


@pytest.mark.asyncio
async def test_handle_payment_intent_succeeded_with_acss_debit(
    mock_session, mock_transaction
):
    """Test payment intent succeeded with ACSS debit payment method."""
    # Arrange
    payment_intent = {
        "id": "pi_test123",
        "payment_method_details": {
            "acss_debit": {
                "last4": "6789",
                "bank_name": "TD Bank",
                "institution_number": "004",
            }
        },
    }
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_payment_intent_succeeded(payment_intent, mock_session)
    
    # Assert
    assert mock_transaction.payment_method_type == "acss_debit"
    assert mock_transaction.payment_method_last_four == "6789"
    assert mock_transaction.payment_method_bank_name == "TD Bank"


@pytest.mark.asyncio
async def test_handle_payment_intent_succeeded_no_transaction_found(
    mock_session, payment_intent_succeeded
):
    """Test payment intent succeeded when transaction not found."""
    # Arrange
    mock_session.scalar.return_value = None
    
    # Act - should not raise exception
    await handle_payment_intent_succeeded(payment_intent_succeeded, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payment_intent_succeeded_missing_pi_id(mock_session):
    """Test payment intent succeeded with missing PaymentIntent ID."""
    # Arrange
    payment_intent = {"object": "payment_intent"}  # No id field
    
    # Act
    await handle_payment_intent_succeeded(payment_intent, mock_session)
    
    # Assert
    mock_session.scalar.assert_not_called()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.webhook_handlers.payment_intent_handlers.create_ledger_payment')
async def test_handle_payment_intent_succeeded_creates_ledger_payment(
    mock_create_ledger, mock_session, mock_transaction, payment_intent_succeeded
):
    """Test that successful payment creates ledger payment record."""
    # Arrange
    mock_session.scalar.return_value = mock_transaction
    mock_create_ledger.return_value = None
    
    # Act
    await handle_payment_intent_succeeded(payment_intent_succeeded, mock_session)
    
    # Assert
    mock_create_ledger.assert_called_once_with(mock_transaction, mock_session)


# =============================================================================
# Tests: handle_payment_intent_failed
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_intent_failed_success(
    mock_session, mock_transaction, payment_intent_failed
):
    """Test successful payment intent failed handler."""
    # Arrange
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_payment_intent_failed(payment_intent_failed, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.FAILED
    assert mock_transaction.failed_at is not None
    assert mock_transaction.failure_code == "card_declined"
    assert mock_transaction.failure_message == "Your card was declined"
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_payment_intent_failed_no_error_details(
    mock_session, mock_transaction
):
    """Test payment intent failed with no error details."""
    # Arrange
    payment_intent = {"id": "pi_test123"}  # No last_payment_error
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_payment_intent_failed(payment_intent, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.FAILED
    assert mock_transaction.failure_code is None
    assert mock_transaction.failure_message is None


@pytest.mark.asyncio
async def test_handle_payment_intent_failed_no_transaction_found(
    mock_session, payment_intent_failed
):
    """Test payment intent failed when transaction not found."""
    # Arrange
    mock_session.scalar.return_value = None
    
    # Act
    await handle_payment_intent_failed(payment_intent_failed, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


# =============================================================================
# Tests: handle_payment_intent_canceled
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_intent_canceled_success(
    mock_session, mock_transaction
):
    """Test successful payment intent canceled handler."""
    # Arrange
    payment_intent = {"id": "pi_test123", "status": "canceled"}
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_payment_intent_canceled(payment_intent, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.CANCELED
    assert mock_transaction.updated_at is not None
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_payment_intent_canceled_no_transaction(mock_session):
    """Test payment intent canceled when transaction not found."""
    # Arrange
    payment_intent = {"id": "pi_test123"}
    mock_session.scalar.return_value = None
    
    # Act
    await handle_payment_intent_canceled(payment_intent, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


# =============================================================================
# Tests: handle_payment_intent_processing
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_intent_processing_success(
    mock_session, mock_transaction
):
    """Test successful payment intent processing handler."""
    # Arrange
    payment_intent = {"id": "pi_test123", "status": "processing"}
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_payment_intent_processing(payment_intent, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.PROCESSING
    assert mock_transaction.authorized_at is not None
    assert mock_transaction.updated_at is not None
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_payment_intent_processing_no_transaction(mock_session):
    """Test payment intent processing when transaction not found."""
    # Arrange
    payment_intent = {"id": "pi_test123"}
    mock_session.scalar.return_value = None
    
    # Act
    await handle_payment_intent_processing(payment_intent, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


# =============================================================================
# Tests: handle_payment_intent_requires_action
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_intent_requires_action_success(
    mock_session, mock_transaction
):
    """Test successful payment intent requires_action handler."""
    # Arrange
    payment_intent = {"id": "pi_test123", "status": "requires_action"}
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_payment_intent_requires_action(payment_intent, mock_session)
    
    # Assert
    assert mock_transaction.status == RentPaymentTransactionStatus.REQUIRES_ACTION
    assert mock_transaction.updated_at is not None
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


# =============================================================================
# Tests: handle_payment_intent_amount_capturable_updated
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_intent_amount_capturable_updated(
    mock_session, mock_transaction
):
    """Test payment intent amount_capturable_updated handler."""
    # Arrange
    payment_intent = {
        "id": "pi_test123",
        "amount_capturable": 150000,  # Partial authorization
    }
    mock_session.scalar.return_value = mock_transaction
    
    # Act - this handler only logs, doesn't update status
    await handle_payment_intent_amount_capturable_updated(payment_intent, mock_session)
    
    # Assert - should not change status
    assert mock_transaction.status == RentPaymentTransactionStatus.PENDING
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payment_intent_amount_capturable_updated_no_transaction(
    mock_session
):
    """Test amount_capturable_updated when transaction not found."""
    # Arrange
    payment_intent = {"id": "pi_test123", "amount_capturable": 150000}
    mock_session.scalar.return_value = None
    
    # Act - should not raise exception
    await handle_payment_intent_amount_capturable_updated(payment_intent, mock_session)
    
    # Assert
    mock_session.scalar.assert_called_once()


# =============================================================================
# Tests: handle_payment_intent_partially_funded
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_intent_partially_funded_success(
    mock_session, mock_transaction
):
    """Test payment intent partially_funded handler."""
    # Arrange
    payment_intent = {
        "id": "pi_test123",
        "amount": 200000,
        "amount_received": 100000,  # 50% funded
    }
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_payment_intent_partially_funded(payment_intent, mock_session)
    
    # Assert - should move to PROCESSING
    assert mock_transaction.status == RentPaymentTransactionStatus.PROCESSING
    assert mock_transaction.updated_at is not None
    mock_session.add.assert_called_once_with(mock_transaction)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_payment_intent_partially_funded_already_processing(
    mock_session, mock_transaction
):
    """Test partially_funded when already processing - should not update."""
    # Arrange
    payment_intent = {
        "id": "pi_test123",
        "amount": 200000,
        "amount_received": 100000,
    }
    mock_transaction.status = RentPaymentTransactionStatus.PROCESSING  # Already processing
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_payment_intent_partially_funded(payment_intent, mock_session)
    
    # Assert - should not update status again
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payment_intent_partially_funded_no_transaction(
    mock_session
):
    """Test partially_funded when transaction not found."""
    # Arrange
    payment_intent = {
        "id": "pi_test123",
        "amount": 200000,
        "amount_received": 100000,
    }
    mock_session.scalar.return_value = None
    
    # Act
    await handle_payment_intent_partially_funded(payment_intent, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


# =============================================================================
# Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_payment_intent_handlers_handle_empty_payment_method_details(
    mock_session, mock_transaction
):
    """Test payment intent succeeded with empty payment_method_details."""
    # Arrange
    payment_intent = {
        "id": "pi_test123",
        "payment_method_details": {},  # Empty
    }
    mock_session.scalar.return_value = mock_transaction
    
    # Act
    await handle_payment_intent_succeeded(payment_intent, mock_session)
    
    # Assert - should still succeed without payment method details
    assert mock_transaction.status == RentPaymentTransactionStatus.SUCCEEDED
    assert mock_transaction.payment_method_type is None
    assert mock_transaction.payment_method_last_four is None


@pytest.mark.asyncio
async def test_payment_intent_handlers_handle_missing_id_gracefully(mock_session):
    """Test all handlers gracefully handle missing PaymentIntent ID."""
    # Arrange
    payment_intent = {}  # No id field
    
    # Act - none should raise exceptions
    await handle_payment_intent_succeeded(payment_intent, mock_session)
    await handle_payment_intent_failed(payment_intent, mock_session)
    await handle_payment_intent_canceled(payment_intent, mock_session)
    await handle_payment_intent_processing(payment_intent, mock_session)
    await handle_payment_intent_requires_action(payment_intent, mock_session)
    await handle_payment_intent_amount_capturable_updated(payment_intent, mock_session)
    await handle_payment_intent_partially_funded(payment_intent, mock_session)
    
    # Assert - no database operations should occur
    mock_session.scalar.assert_not_called()
    mock_session.add.assert_not_called()

