"""
Unit tests for payment method and setup intent webhook handlers.

Tests payment_method.* and setup_intent.* webhook event handlers
to ensure proper payment method tracking and setup completion.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.rent_payments.webhook_handlers.payment_method_handlers import (
    handle_payment_method_attached,
    handle_payment_method_updated,
    handle_payment_method_detached,
    handle_setup_intent_succeeded,
)
from Backend.models.tenant_payment_method import TenantPaymentMethod

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
def mock_payment_method():
    """Create mock tenant payment method."""
    method = MagicMock(spec=TenantPaymentMethod)
    method.id = uuid4()
    method.stripe_payment_method_id = "pm_test123"
    method.tenant_id = uuid4()
    method.card_last_four = "4242"
    method.card_brand = "visa"
    method.is_default = True
    method.created_at = datetime.now(timezone.utc)
    method.updated_at = datetime.now(timezone.utc)
    return method


# =============================================================================
# Tests: handle_payment_method_attached
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_method_attached_success(
    mock_session, mock_payment_method
):
    """Test successful payment method attached handler."""
    # Arrange
    payment_method = {
        "id": "pm_test123",
        "card": {"last4": "4242", "brand": "visa"},
    }
    mock_session.scalar.return_value = mock_payment_method
    
    # Act
    await handle_payment_method_attached(payment_method, mock_session)
    
    # Assert - should just log, no database updates
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payment_method_attached_no_id(mock_session):
    """Test payment method attached with missing ID."""
    # Arrange
    payment_method = {}  # No id field
    
    # Act
    await handle_payment_method_attached(payment_method, mock_session)
    
    # Assert
    mock_session.scalar.assert_not_called()


# =============================================================================
# Tests: handle_payment_method_updated
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_method_updated_card_expiry(
    mock_session, mock_payment_method
):
    """Test payment method updated with card expiry changes."""
    # Arrange
    payment_method = {
        "id": "pm_test123",
        "type": "card",
        "card": {
            "exp_month": 12,
            "exp_year": 2025,
        },
    }
    mock_session.scalar.return_value = mock_payment_method
    
    # Act
    await handle_payment_method_updated(payment_method, mock_session)
    
    # Assert - only exp_month and exp_year are updated
    assert mock_payment_method.card_exp_month == "12"
    assert mock_payment_method.card_exp_year == "2025"
    mock_session.add.assert_called_once_with(mock_payment_method)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_payment_method_updated_acss_debit_no_updates(
    mock_session, mock_payment_method
):
    """Test payment method updated for ACSS debit (no updates)."""
    # Arrange
    payment_method = {
        "id": "pm_test123",
        "type": "acss_debit",  # Not 'card' type
        "acss_debit": {
            "last4": "6789",
        },
    }
    mock_session.scalar.return_value = mock_payment_method
    
    # Act
    await handle_payment_method_updated(payment_method, mock_session)
    
    # Assert - handler only updates card expiry, not acss_debit details
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payment_method_updated_no_method_found(mock_session):
    """Test payment method updated when method not found."""
    # Arrange
    payment_method = {"id": "pm_test123", "card": {"last4": "4242"}}
    mock_session.scalar.return_value = None
    
    # Act
    await handle_payment_method_updated(payment_method, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payment_method_updated_missing_id(mock_session):
    """Test payment method updated with missing ID."""
    # Arrange
    payment_method = {"card": {"last4": "4242"}}  # No id
    
    # Act
    await handle_payment_method_updated(payment_method, mock_session)
    
    # Assert
    mock_session.scalar.assert_not_called()


# =============================================================================
# Tests: handle_payment_method_detached
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_method_detached_success(
    mock_session, mock_payment_method
):
    """Test successful payment method detached handler."""
    # Arrange
    payment_method = {"id": "pm_test123"}
    mock_session.scalar.return_value = mock_payment_method
    
    # Act
    await handle_payment_method_detached(payment_method, mock_session)
    
    # Assert - detached sets is_default to False (soft delete)
    assert mock_payment_method.is_default is False
    assert mock_payment_method.updated_at is not None
    mock_session.add.assert_called_once_with(mock_payment_method)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_payment_method_detached_no_method_found(mock_session):
    """Test payment method detached when method not found."""
    # Arrange
    payment_method = {"id": "pm_test123"}
    mock_session.scalar.return_value = None
    
    # Act
    await handle_payment_method_detached(payment_method, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payment_method_detached_missing_id(mock_session):
    """Test payment method detached with missing ID."""
    # Arrange
    payment_method = {}  # No id field
    
    # Act
    await handle_payment_method_detached(payment_method, mock_session)
    
    # Assert
    mock_session.scalar.assert_not_called()


# =============================================================================
# Tests: handle_setup_intent_succeeded
# =============================================================================

@pytest.mark.asyncio
async def test_handle_setup_intent_succeeded_success(mock_session):
    """Test successful setup intent succeeded handler."""
    # Arrange
    setup_intent = {
        "id": "seti_test123",
        "payment_method": "pm_test123",
        "status": "succeeded",
    }
    
    # Act - handler only logs, doesn't update database
    await handle_setup_intent_succeeded(setup_intent, mock_session)
    
    # Assert - no database operations
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_setup_intent_succeeded_missing_id(mock_session):
    """Test setup intent succeeded with missing ID."""
    # Arrange
    setup_intent = {}  # No id field
    
    # Act
    await handle_setup_intent_succeeded(setup_intent, mock_session)
    
    # Assert - still logs, no issue
    mock_session.add.assert_not_called()


# =============================================================================
# Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_payment_method_handlers_handle_missing_ids_gracefully(mock_session):
    """Test all payment method handlers gracefully handle missing IDs."""
    # Arrange
    empty_method = {}  # No id field
    
    # Act - none should raise exceptions
    await handle_payment_method_attached(empty_method, mock_session)
    await handle_payment_method_updated(empty_method, mock_session)
    await handle_payment_method_detached(empty_method, mock_session)
    await handle_setup_intent_succeeded(empty_method, mock_session)
    
    # Assert - should handle gracefully
    assert True  # Reached here without exception


@pytest.mark.asyncio
async def test_handle_payment_method_updated_no_card_or_bank_data(
    mock_session, mock_payment_method
):
    """Test payment method updated with no card or bank data."""
    # Arrange
    payment_method = {"id": "pm_test123"}  # No card or acss_debit
    mock_session.scalar.return_value = mock_payment_method
    
    # Act
    await handle_payment_method_updated(payment_method, mock_session)
    
    # Assert - should not crash, just skip updates
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payment_method_detached_idempotent(
    mock_session, mock_payment_method
):
    """Test payment method detached is idempotent."""
    # Arrange
    payment_method = {"id": "pm_test123"}
    mock_payment_method.is_default = False  # Already detached
    mock_session.scalar.return_value = mock_payment_method
    
    # Act
    await handle_payment_method_detached(payment_method, mock_session)
    
    # Assert - should still process (idempotent)
    assert mock_payment_method.is_default is False
    mock_session.commit.assert_called_once()

