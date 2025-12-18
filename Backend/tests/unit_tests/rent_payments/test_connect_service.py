"""
Unit tests for Stripe Connect service functions.

Tests cover:
- Connected account creation and onboarding
- Account status retrieval
- Refresh and dashboard link generation
- Access control and validation
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException

from Backend.api.rent_payments.connect_service import (
    create_connected_account,
    get_connect_status,
    create_refresh_link,
    create_dashboard_link,
    get_connected_account_for_landlord,
    landlord_can_accept_payments,
)
from Backend.models.enums import UserType


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.scalar = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_landlord_user():
    """Create a mock landlord user."""
    user = MagicMock()
    user.id = uuid4()
    user.user_type = UserType.LANDLORD
    user.email = "landlord@example.com"
    user.first_name = "John"
    user.last_name = "Landlord"
    return user


@pytest.fixture
def mock_connected_account():
    """Create a mock connected account."""
    account = MagicMock()
    account.id = uuid4()
    account.user_id = uuid4()
    account.stripe_account_id = "acct_test123"
    account.country = "CA"
    account.default_currency = "cad"
    account.charges_enabled = True
    account.payouts_enabled = True
    account.details_submitted = True
    account.onboarding_status = "complete"
    account.is_fully_onboarded = True
    account.needs_action = False
    account.disabled_reason = None
    account.requirements_currently_due = []
    account.requirements_past_due = []
    account.requirements_eventually_due = []
    account.business_type = "individual"
    account.onboarding_completed_at = datetime.now(timezone.utc)
    return account


# =============================================================================
# Tests: create_connected_account
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.connect_service.get_stripe_client')
@patch('Backend.api.rent_payments.connect_service._create_account_link')
async def test_create_connected_account_success(
    mock_create_link, mock_get_stripe, mock_session, mock_landlord_user
):
    """Test successful connected account creation."""
    # Arrange
    mock_session.scalar.return_value = None  # No existing account
    
    # Mock Stripe account creation
    mock_stripe_account = MagicMock()
    mock_stripe_account.id = "acct_test123"
    
    mock_stripe = MagicMock()
    mock_stripe.accounts.create = AsyncMock(return_value=mock_stripe_account)
    mock_get_stripe.return_value = mock_stripe
    
    # Mock account link response
    mock_link_response = MagicMock()
    mock_link_response.account_id = "acct_test123"
    mock_link_response.onboarding_url = "https://connect.stripe.com/setup/xxx"
    mock_create_link.return_value = mock_link_response
    
    # Act
    result = await create_connected_account(mock_landlord_user, mock_session)
    
    # Assert
    assert result.account_id == "acct_test123"
    assert result.onboarding_url is not None
    mock_stripe.accounts.create.assert_called_once()
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_connected_account_not_landlord(mock_session, mock_landlord_user):
    """Test account creation by non-landlord user."""
    # Arrange
    mock_landlord_user.user_type = UserType.TENANT
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_connected_account(mock_landlord_user, mock_session)
    
    assert exc_info.value.status_code == 403
    assert "only landlords" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_create_connected_account_already_onboarded(
    mock_session, mock_landlord_user, mock_connected_account
):
    """Test account creation when already fully onboarded."""
    # Arrange
    mock_connected_account.is_fully_onboarded = True
    mock_session.scalar.return_value = mock_connected_account
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_connected_account(mock_landlord_user, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "already set up" in exc_info.value.detail.lower()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.connect_service._create_account_link')
async def test_create_connected_account_incomplete_existing(
    mock_create_link, mock_session, mock_landlord_user, mock_connected_account
):
    """Test account creation when incomplete account exists - returns new link."""
    # Arrange
    mock_connected_account.is_fully_onboarded = False
    mock_session.scalar.return_value = mock_connected_account
    
    mock_link_response = MagicMock()
    mock_link_response.onboarding_url = "https://connect.stripe.com/setup/xxx"
    mock_create_link.return_value = mock_link_response
    
    # Act
    result = await create_connected_account(mock_landlord_user, mock_session)
    
    # Assert
    assert result.onboarding_url is not None
    mock_create_link.assert_called_once_with(mock_connected_account, mock_session)


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.connect_service.get_stripe_client')
async def test_create_connected_account_stripe_error(
    mock_get_stripe, mock_session, mock_landlord_user
):
    """Test account creation with Stripe error."""
    # Arrange
    from stripe import StripeError
    
    mock_session.scalar.return_value = None
    
    mock_stripe = MagicMock()
    mock_stripe.accounts.create = AsyncMock(side_effect=StripeError("API error"))
    mock_get_stripe.return_value = mock_stripe
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_connected_account(mock_landlord_user, mock_session)
    
    assert exc_info.value.status_code == 502


# =============================================================================
# Tests: get_connect_status
# =============================================================================

@pytest.mark.asyncio
async def test_get_connect_status_no_account(mock_session, mock_landlord_user):
    """Test getting status when no account exists."""
    # Arrange
    mock_session.scalar.return_value = None
    
    # Act
    result = await get_connect_status(mock_landlord_user, mock_session)
    
    # Assert
    assert result.is_connected is False
    assert result.onboarding_status == "not_started"


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.connect_service.get_stripe_client')
async def test_get_connect_status_success(
    mock_get_stripe, mock_session, mock_landlord_user, mock_connected_account
):
    """Test successful status retrieval."""
    # Arrange
    mock_session.scalar.return_value = mock_connected_account
    
    # Mock Stripe account retrieval
    mock_stripe_account = MagicMock()
    mock_stripe_account.charges_enabled = True
    mock_stripe_account.payouts_enabled = True
    mock_stripe_account.details_submitted = True
    mock_stripe_account.business_type = "individual"
    mock_stripe_account.get.return_value = {"currently_due": [], "past_due": [], "eventually_due": []}
    
    mock_stripe = MagicMock()
    mock_stripe.accounts.retrieve = AsyncMock(return_value=mock_stripe_account)
    mock_get_stripe.return_value = mock_stripe
    
    # Act
    result = await get_connect_status(mock_landlord_user, mock_session)
    
    # Assert
    assert result.is_connected is True
    assert result.account_id == "acct_test123"
    assert result.charges_enabled is True
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.connect_service.get_stripe_client')
async def test_get_connect_status_stripe_error_returns_cached(
    mock_get_stripe, mock_session, mock_landlord_user, mock_connected_account
):
    """Test status retrieval returns cached data on Stripe error."""
    # Arrange
    from stripe import StripeError
    
    mock_session.scalar.return_value = mock_connected_account
    
    mock_stripe = MagicMock()
    mock_stripe.accounts.retrieve = AsyncMock(side_effect=StripeError("API error"))
    mock_get_stripe.return_value = mock_stripe
    
    # Act
    result = await get_connect_status(mock_landlord_user, mock_session)
    
    # Assert
    assert result.is_connected is True
    assert result.account_id == "acct_test123"
    # Should return cached data, not raise exception
    mock_session.commit.assert_not_called()


# =============================================================================
# Tests: create_refresh_link
# =============================================================================

@pytest.mark.asyncio
async def test_create_refresh_link_no_account(mock_session, mock_landlord_user):
    """Test creating refresh link when no account exists."""
    # Arrange
    mock_session.scalar.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_refresh_link(mock_landlord_user, mock_session)
    
    assert exc_info.value.status_code == 404
    assert "no payment account" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_create_refresh_link_already_onboarded(
    mock_session, mock_landlord_user, mock_connected_account
):
    """Test creating refresh link when already onboarded."""
    # Arrange
    mock_connected_account.is_fully_onboarded = True
    mock_session.scalar.return_value = mock_connected_account
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_refresh_link(mock_landlord_user, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "already fully set up" in exc_info.value.detail.lower()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.connect_service._create_account_link')
async def test_create_refresh_link_success(
    mock_create_link, mock_session, mock_landlord_user, mock_connected_account
):
    """Test successful refresh link creation."""
    # Arrange
    mock_connected_account.is_fully_onboarded = False
    mock_session.scalar.return_value = mock_connected_account
    
    mock_link_response = MagicMock()
    mock_link_response.onboarding_url = "https://connect.stripe.com/setup/xxx"
    mock_link_response.expires_at = datetime.now(timezone.utc)
    mock_create_link.return_value = mock_link_response
    
    # Act
    result = await create_refresh_link(mock_landlord_user, mock_session)
    
    # Assert
    assert result.onboarding_url is not None
    mock_create_link.assert_called_once()


# =============================================================================
# Tests: create_dashboard_link
# =============================================================================

@pytest.mark.asyncio
async def test_create_dashboard_link_no_account(mock_session, mock_landlord_user):
    """Test creating dashboard link when no account exists."""
    # Arrange
    mock_session.scalar.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_dashboard_link(mock_landlord_user, mock_session)
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.connect_service.get_stripe_client')
async def test_create_dashboard_link_success(
    mock_get_stripe, mock_session, mock_landlord_user, mock_connected_account
):
    """Test successful dashboard link creation."""
    # Arrange
    mock_session.scalar.return_value = mock_connected_account
    
    mock_login_link = MagicMock()
    mock_login_link.url = "https://dashboard.stripe.com/login/xxx"
    
    mock_stripe = MagicMock()
    mock_stripe.accounts.create_login_link = AsyncMock(return_value=mock_login_link)
    mock_get_stripe.return_value = mock_stripe
    
    # Act
    result = await create_dashboard_link(mock_landlord_user, mock_session)
    
    # Assert
    assert result.dashboard_url is not None
    assert result.expires_at is not None
    mock_stripe.accounts.create_login_link.assert_called_once_with("acct_test123")


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.connect_service.get_stripe_client')
async def test_create_dashboard_link_stripe_error(
    mock_get_stripe, mock_session, mock_landlord_user, mock_connected_account
):
    """Test dashboard link creation with Stripe error."""
    # Arrange
    from stripe import StripeError
    
    mock_session.scalar.return_value = mock_connected_account
    
    mock_stripe = MagicMock()
    mock_stripe.accounts.create_login_link = AsyncMock(side_effect=StripeError("API error"))
    mock_get_stripe.return_value = mock_stripe
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_dashboard_link(mock_landlord_user, mock_session)
    
    assert exc_info.value.status_code == 502


# =============================================================================
# Tests: get_connected_account_for_landlord
# =============================================================================

@pytest.mark.asyncio
async def test_get_connected_account_for_landlord_success(
    mock_session, mock_connected_account
):
    """Test getting connected account by landlord ID."""
    # Arrange
    landlord_id = str(uuid4())
    mock_session.scalar.return_value = mock_connected_account
    
    # Act
    result = await get_connected_account_for_landlord(landlord_id, mock_session)
    
    # Assert
    assert result is not None
    assert result.stripe_account_id == "acct_test123"


@pytest.mark.asyncio
async def test_get_connected_account_for_landlord_not_found(mock_session):
    """Test getting connected account when not found."""
    # Arrange
    landlord_id = str(uuid4())
    mock_session.scalar.return_value = None
    
    # Act
    result = await get_connected_account_for_landlord(landlord_id, mock_session)
    
    # Assert
    assert result is None


# =============================================================================
# Tests: landlord_can_accept_payments
# =============================================================================

@pytest.mark.asyncio
async def test_landlord_can_accept_payments_true(
    mock_session, mock_connected_account
):
    """Test landlord can accept payments when fully onboarded."""
    # Arrange
    landlord_id = str(uuid4())
    mock_connected_account.is_fully_onboarded = True
    mock_session.scalar.return_value = mock_connected_account
    
    # Act
    result = await landlord_can_accept_payments(landlord_id, mock_session)
    
    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_landlord_can_accept_payments_false_not_onboarded(
    mock_session, mock_connected_account
):
    """Test landlord cannot accept payments when not onboarded."""
    # Arrange
    landlord_id = str(uuid4())
    mock_connected_account.is_fully_onboarded = False
    mock_session.scalar.return_value = mock_connected_account
    
    # Act
    result = await landlord_can_accept_payments(landlord_id, mock_session)
    
    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_landlord_can_accept_payments_false_no_account(mock_session):
    """Test landlord cannot accept payments when no account exists."""
    # Arrange
    landlord_id = str(uuid4())
    mock_session.scalar.return_value = None
    
    # Act
    result = await landlord_can_accept_payments(landlord_id, mock_session)
    
    # Assert
    assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

