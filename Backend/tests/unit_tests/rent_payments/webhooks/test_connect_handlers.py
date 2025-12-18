"""
Unit tests for Stripe Connect account webhook handlers.

Tests account.updated webhook event handler to ensure proper
connected account status tracking.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.rent_payments.webhook_handlers.connect_handlers import (
    handle_account_updated,
)
from Backend.models.stripe_connected_account import StripeConnectedAccount

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
def mock_connected_account():
    """Create mock stripe connected account."""
    account = MagicMock(spec=StripeConnectedAccount)
    account.id = uuid4()
    account.stripe_account_id = "acct_test123"
    account.user_id = uuid4()
    account.account_status = "pending"
    account.charges_enabled = False
    account.payouts_enabled = False
    account.requirements_currently_due = []
    account.created_at = datetime.now(timezone.utc)
    account.updated_at = datetime.now(timezone.utc)
    return account


# =============================================================================
# Tests: handle_account_updated
# =============================================================================

@pytest.mark.asyncio
async def test_handle_account_updated_success(
    mock_session, mock_connected_account
):
    """Test successful account updated handler."""
    # Arrange
    account = {
        "id": "acct_test123",
        "charges_enabled": True,
        "payouts_enabled": True,
        "requirements": {
            "currently_due": [],
            "eventually_due": [],
        },
    }
    mock_session.scalar.return_value = mock_connected_account
    
    # Act
    await handle_account_updated(account, mock_session)
    
    # Assert
    assert mock_connected_account.charges_enabled is True
    assert mock_connected_account.payouts_enabled is True
    assert mock_connected_account.requirements_currently_due == []
    assert mock_connected_account.updated_at is not None
    mock_session.add.assert_called_once_with(mock_connected_account)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_account_updated_with_requirements(
    mock_session, mock_connected_account
):
    """Test account updated with requirements currently due."""
    # Arrange
    account = {
        "id": "acct_test123",
        "charges_enabled": False,
        "payouts_enabled": False,
        "requirements": {
            "currently_due": ["individual.verification.document", "business.tax_id"],
            "eventually_due": ["external_account"],
        },
    }
    mock_session.scalar.return_value = mock_connected_account
    
    # Act
    await handle_account_updated(account, mock_session)
    
    # Assert
    assert mock_connected_account.charges_enabled is False
    assert mock_connected_account.payouts_enabled is False
    assert len(mock_connected_account.requirements_currently_due) == 2
    assert "individual.verification.document" in mock_connected_account.requirements_currently_due
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_account_updated_no_account_found(mock_session):
    """Test account updated when account not found."""
    # Arrange
    account = {"id": "acct_test123", "charges_enabled": True}
    mock_session.scalar.return_value = None
    
    # Act
    await handle_account_updated(account, mock_session)
    
    # Assert
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_account_updated_missing_account_id(mock_session):
    """Test account updated with missing account ID."""
    # Arrange
    account = {"charges_enabled": True}  # No id field
    
    # Act
    await handle_account_updated(account, mock_session)
    
    # Assert
    mock_session.scalar.assert_not_called()


@pytest.mark.asyncio
async def test_handle_account_updated_no_requirements_field(
    mock_session, mock_connected_account
):
    """Test account updated without requirements field."""
    # Arrange
    account = {
        "id": "acct_test123",
        "charges_enabled": True,
        "payouts_enabled": True,
    }  # No requirements field
    mock_session.scalar.return_value = mock_connected_account
    
    # Act
    await handle_account_updated(account, mock_session)
    
    # Assert - should still update other fields
    assert mock_connected_account.charges_enabled is True
    assert mock_connected_account.payouts_enabled is True
    # requirements_currently_due should remain unchanged
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_account_updated_partial_enable(
    mock_session, mock_connected_account
):
    """Test account updated with only charges enabled."""
    # Arrange
    account = {
        "id": "acct_test123",
        "charges_enabled": True,
        "payouts_enabled": False,  # Still disabled
        "requirements": {
            "currently_due": ["external_account"],
        },
    }
    mock_session.scalar.return_value = mock_connected_account
    
    # Act
    await handle_account_updated(account, mock_session)
    
    # Assert
    assert mock_connected_account.charges_enabled is True
    assert mock_connected_account.payouts_enabled is False
    assert "external_account" in mock_connected_account.requirements_currently_due
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_account_updated_idempotent(
    mock_session, mock_connected_account
):
    """Test account updated is idempotent when called multiple times."""
    # Arrange
    account = {
        "id": "acct_test123",
        "charges_enabled": True,
        "payouts_enabled": True,
        "requirements": {"currently_due": []},
    }
    # Account already has these values
    mock_connected_account.charges_enabled = True
    mock_connected_account.payouts_enabled = True
    mock_connected_account.requirements_currently_due = []
    mock_session.scalar.return_value = mock_connected_account
    
    # Act
    await handle_account_updated(account, mock_session)
    
    # Assert - should still process (idempotent)
    assert mock_connected_account.charges_enabled is True
    assert mock_connected_account.payouts_enabled is True
    mock_session.commit.assert_called_once()


# =============================================================================
# Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_handle_account_updated_handles_missing_fields_gracefully(
    mock_session, mock_connected_account
):
    """Test account updated handles missing optional fields gracefully."""
    # Arrange
    account = {
        "id": "acct_test123",
        # Missing charges_enabled, payouts_enabled, requirements
    }
    mock_session.scalar.return_value = mock_connected_account
    
    # Act - should not raise exception
    await handle_account_updated(account, mock_session)
    
    # Assert - should still update timestamp
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_account_updated_with_empty_requirements(
    mock_session, mock_connected_account
):
    """Test account updated with empty requirements object."""
    # Arrange
    account = {
        "id": "acct_test123",
        "charges_enabled": True,
        "payouts_enabled": True,
        "requirements": {},  # Empty object
    }
    mock_session.scalar.return_value = mock_connected_account
    
    # Act
    await handle_account_updated(account, mock_session)
    
    # Assert
    assert mock_connected_account.charges_enabled is True
    mock_session.commit.assert_called_once()

