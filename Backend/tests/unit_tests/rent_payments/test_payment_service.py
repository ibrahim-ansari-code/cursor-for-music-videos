"""
Unit tests for rent payment service functions.

Tests cover:
- Setup intent creation & idempotency
- Payment method saving & validation
- Payment creation & fee calculation
- Payment method management (list, delete, set default)
- Error handling for Stripe operations
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import uuid4
from fastapi import HTTPException

from Backend.api.rent_payments.service import (
    create_setup_intent,
    save_payment_method,
    create_payment,
    list_payment_methods,
    delete_payment_method,
    set_default_payment_method,
)
from Backend.models.enums import UserType
from Backend.models.lease import LeaseStatus
from Backend.models.rent_payment_transaction import RentPaymentTransactionStatus


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.scalar = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()  # delete is async in AsyncSession
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create a mock tenant user."""
    user = MagicMock()
    user.id = 1
    user.user_type = UserType.TENANT
    user.email = "tenant@example.com"
    return user


@pytest.fixture
def mock_tenant():
    """Create a mock tenant record."""
    tenant = MagicMock()
    tenant.id = 123
    tenant.user_id = 1
    tenant.email = "tenant@example.com"
    tenant.first_name = "John"
    tenant.last_name = "Doe"
    tenant.tenant_type = "individual"
    tenant.company_name = None
    return tenant


@pytest.fixture
def mock_lease():
    """Create a mock lease record."""
    lease = MagicMock()
    lease.id = 456
    lease.tenant_id = 123
    lease.property_id = 789
    lease.status = LeaseStatus.ACTIVE
    lease.monthly_rent = Decimal("2000.00")
    lease.rent_due_day = 1
    lease.start_date = date(2024, 1, 1)
    
    # Mock property with valid UUID
    property_mock = MagicMock()
    property_mock.user_id = uuid4()  # Use actual UUID
    property_mock.name = "Test Property"
    lease.property = property_mock
    
    return lease


@pytest.fixture
def mock_connected_account():
    """Create a mock Stripe connected account."""
    account = MagicMock()
    account.id = uuid4()
    account.stripe_account_id = "acct_test123"
    account.onboarding_status = "complete"
    account.charges_enabled = True
    account.payouts_enabled = True
    account.is_fully_onboarded = True
    account.accepted_payment_methods = ["card", "acss_debit"]
    return account


@pytest.fixture
def mock_payment_method():
    """Create a mock tenant payment method."""
    pm = MagicMock()
    pm.id = uuid4()
    pm.tenant_id = 123
    pm.stripe_payment_method_id = "pm_test123"
    pm.payment_method_type = "card"
    pm.last_four = "4242"
    pm.brand = "visa"
    pm.exp_month = 12
    pm.exp_year = 2025
    pm.is_default = False
    pm.is_verified = True
    pm.is_usable = True
    pm.bank_name = None
    pm.institution_number = None
    pm.created_at = datetime.now(timezone.utc)
    pm.updated_at = datetime.now(timezone.utc)
    pm.display_name = "Visa •••• 4242"
    return pm


# =============================================================================
# Tests: create_setup_intent
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service.get_stripe_client')
@patch('Backend.api.rent_payments.service.get_connected_account_for_landlord')
@patch('Backend.api.rent_payments.service._get_active_lease_for_tenant')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_create_setup_intent_success(
    mock_get_tenant, mock_get_lease, mock_get_account, mock_get_stripe,
    mock_session, mock_user, mock_tenant, mock_lease, mock_connected_account
):
    """Test successful setup intent creation."""
    # Arrange
    mock_get_tenant.return_value = mock_tenant
    mock_get_lease.return_value = mock_lease
    mock_get_account.return_value = mock_connected_account
    
    mock_stripe = MagicMock()
    mock_setup_intent = MagicMock()
    mock_setup_intent.id = "seti_test123"
    mock_setup_intent.client_secret = "seti_test123_secret_xyz"
    mock_stripe.setup_intents.create = AsyncMock(return_value=mock_setup_intent)
    mock_get_stripe.return_value = mock_stripe
    
    # Act
    result = await create_setup_intent(mock_user, mock_session)
    
    # Assert
    assert result.setup_intent_id == "seti_test123"
    assert result.client_secret == "seti_test123_secret_xyz"
    
    # Verify Stripe API call
    mock_stripe.setup_intents.create.assert_called_once()
    call_kwargs = mock_stripe.setup_intents.create.call_args[1]
    assert "card" in call_kwargs["payment_method_types"]
    assert "acss_debit" in call_kwargs["payment_method_types"]
    assert "idempotency_key" in call_kwargs
    assert call_kwargs["idempotency_key"].startswith(f"setup-intent-{mock_tenant.id}")


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service._get_active_lease_for_tenant')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_create_setup_intent_no_active_lease(
    mock_get_tenant, mock_get_lease, mock_session, mock_user, mock_tenant
):
    """Test setup intent creation when no active lease exists."""
    # Arrange
    mock_get_tenant.return_value = mock_tenant
    mock_get_lease.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_setup_intent(mock_user, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "No active lease found" in exc_info.value.detail


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service.get_connected_account_for_landlord')
@patch('Backend.api.rent_payments.service._get_active_lease_for_tenant')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_create_setup_intent_account_not_onboarded(
    mock_get_tenant, mock_get_lease, mock_get_account,
    mock_session, mock_user, mock_tenant, mock_lease, mock_connected_account
):
    """Test setup intent creation when connected account not onboarded."""
    # Arrange
    mock_get_tenant.return_value = mock_tenant
    mock_get_lease.return_value = mock_lease
    mock_connected_account.is_fully_onboarded = False
    mock_get_account.return_value = mock_connected_account
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_setup_intent(mock_user, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "not set up online payments" in exc_info.value.detail


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service.get_stripe_client')
@patch('Backend.api.rent_payments.service.get_connected_account_for_landlord')
@patch('Backend.api.rent_payments.service._get_active_lease_for_tenant')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_create_setup_intent_stripe_error(
    mock_get_tenant, mock_get_lease, mock_get_account, mock_get_stripe,
    mock_session, mock_user, mock_tenant, mock_lease, mock_connected_account
):
    """Test setup intent creation with Stripe error."""
    # Arrange
    from stripe import InvalidRequestError
    
    mock_get_tenant.return_value = mock_tenant
    mock_get_lease.return_value = mock_lease
    mock_get_account.return_value = mock_connected_account
    
    mock_stripe = MagicMock()
    mock_stripe.setup_intents.create = AsyncMock(
        side_effect=InvalidRequestError("Account not set up", None)
    )
    mock_get_stripe.return_value = mock_stripe
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_setup_intent(mock_user, mock_session)
    
    assert exc_info.value.status_code == 502


# =============================================================================
# Tests: save_payment_method
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service._unset_default_payment_method')
@patch('Backend.api.rent_payments.service.get_stripe_client')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_save_payment_method_card_success(
    mock_get_tenant, mock_get_stripe, mock_unset_default, mock_session, mock_user, mock_tenant
):
    """Test saving a card payment method."""
    # Arrange
    from Backend.api.rent_payments.schemas import PaymentMethodCreate
    
    mock_get_tenant.return_value = mock_tenant
    mock_unset_default.return_value = None
    
    # Mock Stripe payment method
    mock_stripe_pm = MagicMock()
    mock_stripe_pm.id = "pm_test123"
    mock_stripe_pm.type = "card"
    mock_stripe_pm.card = MagicMock()
    mock_stripe_pm.card.last4 = "4242"
    mock_stripe_pm.card.brand = "visa"
    mock_stripe_pm.card.exp_month = 12
    mock_stripe_pm.card.exp_year = 2025
    
    mock_stripe = MagicMock()
    mock_stripe.payment_methods.retrieve = AsyncMock(return_value=mock_stripe_pm)
    mock_get_stripe.return_value = mock_stripe
    
    # Mock database check for existing
    mock_session.scalar.return_value = None
    
    # Mock the created payment method after refresh
    mock_saved_pm = MagicMock()
    mock_saved_pm.id = uuid4()
    mock_saved_pm.tenant_id = 123
    mock_saved_pm.stripe_payment_method_id = "pm_test123"
    mock_saved_pm.payment_method_type = "card"
    mock_saved_pm.last_four = "4242"
    mock_saved_pm.brand = "visa"
    mock_saved_pm.exp_month = 12
    mock_saved_pm.exp_year = 2025
    mock_saved_pm.is_default = True
    mock_saved_pm.is_verified = True
    mock_saved_pm.is_usable = True
    mock_saved_pm.bank_name = None
    mock_saved_pm.institution_number = None
    mock_saved_pm.created_at = datetime.now(timezone.utc)
    mock_saved_pm.display_name = "Visa •••• 4242"
    
    # Mock refresh to populate the ID
    async def mock_refresh(obj):
        if hasattr(obj, 'stripe_payment_method_id'):
            obj.id = mock_saved_pm.id
    mock_session.refresh.side_effect = mock_refresh
    
    # Act
    data = PaymentMethodCreate(
        stripe_payment_method_id="pm_test123",
        set_as_default=True
    )
    result = await save_payment_method(mock_user, data, mock_session)
    
    # Assert
    assert result.payment_method_type == "card"
    assert result.last_four == "4242"
    assert result.brand == "visa"
    assert result.is_verified is True
    mock_unset_default.assert_called_once()
    mock_session.add.assert_called()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service.get_stripe_client')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_save_payment_method_acss_debit_success(
    mock_get_tenant, mock_get_stripe, mock_session, mock_user, mock_tenant
):
    """Test saving a PAD (ACSS debit) payment method."""
    # Arrange
    from Backend.api.rent_payments.schemas import PaymentMethodCreate
    
    mock_get_tenant.return_value = mock_tenant
    
    # Mock Stripe payment method
    mock_stripe_pm = MagicMock()
    mock_stripe_pm.id = "pm_pad123"
    mock_stripe_pm.type = "acss_debit"
    mock_stripe_pm.card = None
    mock_stripe_pm.acss_debit = MagicMock()
    mock_stripe_pm.acss_debit.last4 = "6789"
    mock_stripe_pm.acss_debit.bank_name = "TD Bank"
    mock_stripe_pm.acss_debit.institution_number = "004"
    
    mock_stripe = MagicMock()
    mock_stripe.payment_methods.retrieve = AsyncMock(return_value=mock_stripe_pm)
    mock_get_stripe.return_value = mock_stripe
    
    # Mock database check for existing
    mock_session.scalar.return_value = None
    
    # Mock refresh to populate the ID
    async def mock_refresh(obj):
        if hasattr(obj, 'stripe_payment_method_id'):
            obj.id = uuid4()
    mock_session.refresh.side_effect = mock_refresh
    
    # Act
    data = PaymentMethodCreate(
        stripe_payment_method_id="pm_pad123",
        set_as_default=False
    )
    result = await save_payment_method(mock_user, data, mock_session)
    
    # Assert
    assert result.payment_method_type == "acss_debit"
    assert result.last_four == "6789"
    assert result.bank_name == "TD Bank"
    assert result.institution_number == "004"
    assert result.is_verified is False  # PAD requires async verification


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service.get_stripe_client')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_save_payment_method_duplicate(
    mock_get_tenant, mock_get_stripe, mock_session, mock_user, mock_tenant, mock_payment_method
):
    """Test saving a duplicate payment method."""
    # Arrange
    from Backend.api.rent_payments.schemas import PaymentMethodCreate
    
    mock_get_tenant.return_value = mock_tenant
    
    # Mock Stripe payment method
    mock_stripe_pm = MagicMock()
    mock_stripe_pm.id = "pm_test123"
    mock_stripe_pm.type = "card"
    
    mock_stripe = MagicMock()
    mock_stripe.payment_methods.retrieve = AsyncMock(return_value=mock_stripe_pm)
    mock_get_stripe.return_value = mock_stripe
    
    # Mock existing payment method
    mock_session.scalar.return_value = mock_payment_method
    
    # Act & Assert
    data = PaymentMethodCreate(
        stripe_payment_method_id="pm_test123",
        set_as_default=False
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await save_payment_method(mock_user, data, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "already saved" in exc_info.value.detail


# =============================================================================
# Tests: create_payment
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service.get_stripe_client')
@patch('Backend.api.rent_payments.service.get_connected_account_for_landlord')
@patch('Backend.api.rent_payments.service._get_lease_by_id')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_create_payment_success(
    mock_get_tenant, mock_get_lease, mock_get_account, mock_get_stripe,
    mock_session, mock_user, mock_tenant, mock_lease, mock_connected_account, mock_payment_method
):
    """Test successful payment creation."""
    # Arrange
    from Backend.api.rent_payments.schemas import PaymentRequest
    
    mock_get_tenant.return_value = mock_tenant
    mock_get_lease.return_value = mock_lease
    mock_get_account.return_value = mock_connected_account
    
    # Mock payment method lookup
    async def mock_scalar_side_effect(*args, **kwargs):
        return mock_payment_method
    mock_session.scalar.side_effect = mock_scalar_side_effect
    
    # Mock Stripe payment intent
    mock_pi = MagicMock()
    mock_pi.id = "pi_test123"
    mock_pi.client_secret = "pi_test123_secret_xyz"
    mock_pi.status = "requires_confirmation"
    
    mock_stripe = MagicMock()
    mock_stripe.payment_intents.create = AsyncMock(return_value=mock_pi)
    mock_get_stripe.return_value = mock_stripe
    
    # Mock refresh to populate transaction ID
    transaction_id = uuid4()
    async def mock_refresh(obj):
        if hasattr(obj, 'stripe_payment_intent_id'):
            obj.id = transaction_id
    mock_session.refresh.side_effect = mock_refresh
    
    # Act
    data = PaymentRequest(
        lease_id=456,
        amount_cents=200000,
        payment_method_id=mock_payment_method.id
    )
    result = await create_payment(mock_user, data, mock_session)
    
    # Assert
    assert result.payment_intent_id == "pi_test123"
    assert result.client_secret == "pi_test123_secret_xyz"
    assert result.amount_cents == 200000
    assert result.application_fee_cents == 800  # $8 for card
    assert result.stripe_account_id == "acct_test123"
    
    # Verify transaction was created
    mock_session.add.assert_called()
    mock_session.commit.assert_called_once()
    
    # Verify Stripe call
    mock_stripe.payment_intents.create.assert_called_once()
    call_kwargs = mock_stripe.payment_intents.create.call_args[1]
    assert call_kwargs["amount"] == 200000
    assert call_kwargs["application_fee_amount"] == 800
    assert call_kwargs["stripe_account"] == "acct_test123"
    assert "idempotency_key" in call_kwargs


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service._get_lease_by_id')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_create_payment_lease_not_found(
    mock_get_tenant, mock_get_lease, mock_session, mock_user, mock_tenant
):
    """Test payment creation when lease not found."""
    # Arrange
    from Backend.api.rent_payments.schemas import PaymentRequest
    
    mock_get_tenant.return_value = mock_tenant
    mock_get_lease.return_value = None
    
    # Act & Assert
    data = PaymentRequest(
        lease_id=999,
        amount_cents=200000,
        payment_method_id=uuid4()
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_payment(mock_user, data, mock_session)
    
    assert exc_info.value.status_code == 404
    assert "Lease not found" in exc_info.value.detail


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service._get_lease_by_id')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_create_payment_wrong_tenant(
    mock_get_tenant, mock_get_lease, mock_session, mock_user, mock_tenant, mock_lease
):
    """Test payment creation for wrong tenant's lease."""
    # Arrange
    from Backend.api.rent_payments.schemas import PaymentRequest
    
    mock_get_tenant.return_value = mock_tenant
    mock_lease.tenant_id = 999  # Different tenant
    mock_get_lease.return_value = mock_lease
    
    # Act & Assert
    data = PaymentRequest(
        lease_id=456,
        amount_cents=200000,
        payment_method_id=uuid4()
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_payment(mock_user, data, mock_session)
    
    assert exc_info.value.status_code == 403
    assert "your own lease" in exc_info.value.detail


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service._get_lease_by_id')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_create_payment_inactive_lease(
    mock_get_tenant, mock_get_lease, mock_session, mock_user, mock_tenant, mock_lease
):
    """Test payment creation for inactive lease."""
    # Arrange
    from Backend.api.rent_payments.schemas import PaymentRequest
    
    mock_get_tenant.return_value = mock_tenant
    mock_lease.status = LeaseStatus.EXPIRED
    mock_get_lease.return_value = mock_lease
    
    # Act & Assert
    data = PaymentRequest(
        lease_id=456,
        amount_cents=200000,
        payment_method_id=uuid4()
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_payment(mock_user, data, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "inactive lease" in exc_info.value.detail


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service.get_connected_account_for_landlord')
@patch('Backend.api.rent_payments.service._get_lease_by_id')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_create_payment_account_not_onboarded(
    mock_get_tenant, mock_get_lease, mock_get_account,
    mock_session, mock_user, mock_tenant, mock_lease, mock_connected_account
):
    """Test payment creation when connected account not onboarded."""
    # Arrange
    from Backend.api.rent_payments.schemas import PaymentRequest
    
    mock_get_tenant.return_value = mock_tenant
    mock_get_lease.return_value = mock_lease
    mock_connected_account.is_fully_onboarded = False
    mock_get_account.return_value = mock_connected_account
    
    # Act & Assert
    data = PaymentRequest(
        lease_id=456,
        amount_cents=200000,
        payment_method_id=uuid4()
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_payment(mock_user, data, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "not set up online payments" in exc_info.value.detail


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service.get_stripe_client')
@patch('Backend.api.rent_payments.service.get_connected_account_for_landlord')
@patch('Backend.api.rent_payments.service._get_lease_by_id')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_create_payment_pad_lower_fee(
    mock_get_tenant, mock_get_lease, mock_get_account, mock_get_stripe,
    mock_session, mock_user, mock_tenant, mock_lease, mock_connected_account, mock_payment_method
):
    """Test payment creation with PAD has lower fee."""
    # Arrange
    from Backend.api.rent_payments.schemas import PaymentRequest
    
    mock_get_tenant.return_value = mock_tenant
    mock_get_lease.return_value = mock_lease
    mock_get_account.return_value = mock_connected_account
    
    # Mock PAD payment method
    mock_payment_method.payment_method_type = "acss_debit"
    mock_session.scalar.return_value = mock_payment_method
    
    # Mock Stripe payment intent
    mock_pi = MagicMock()
    mock_pi.id = "pi_test123"
    mock_pi.client_secret = "pi_test123_secret_xyz"
    mock_pi.status = "requires_confirmation"
    
    mock_stripe = MagicMock()
    mock_stripe.payment_intents.create = AsyncMock(return_value=mock_pi)
    mock_get_stripe.return_value = mock_stripe
    
    # Mock refresh to populate transaction ID
    transaction_id = uuid4()
    async def mock_refresh(obj):
        if hasattr(obj, 'stripe_payment_intent_id'):
            obj.id = transaction_id
    mock_session.refresh.side_effect = mock_refresh
    
    # Act
    data = PaymentRequest(
        lease_id=456,
        amount_cents=200000,
        payment_method_id=mock_payment_method.id
    )
    result = await create_payment(mock_user, data, mock_session)
    
    # Assert
    assert result.application_fee_cents == 300  # $3 for PAD


# =============================================================================
# Tests: delete_payment_method
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service.get_stripe_client')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_delete_payment_method_success(
    mock_get_tenant, mock_get_stripe, mock_session, mock_user, mock_tenant, mock_payment_method
):
    """Test successful payment method deletion."""
    # Arrange
    mock_get_tenant.return_value = mock_tenant
    
    # Mock database lookups
    async def mock_scalar_side_effect(*args, **kwargs):
        # First call returns payment method, second returns None (no autopay)
        if not hasattr(mock_scalar_side_effect, 'call_count'):
            mock_scalar_side_effect.call_count = 0
        mock_scalar_side_effect.call_count += 1
        
        if mock_scalar_side_effect.call_count == 1:
            return mock_payment_method
        return None
    
    mock_session.scalar.side_effect = mock_scalar_side_effect
    
    # Mock Stripe detach
    mock_stripe = MagicMock()
    mock_stripe.payment_methods.detach = AsyncMock()
    mock_get_stripe.return_value = mock_stripe
    
    # Act
    await delete_payment_method(mock_user, mock_payment_method.id, mock_session)
    
    # Assert
    mock_stripe.payment_methods.detach.assert_called_once_with(mock_payment_method.stripe_payment_method_id)
    mock_session.delete.assert_called_once_with(mock_payment_method)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_delete_payment_method_with_active_autopay(
    mock_get_tenant, mock_session, mock_user, mock_tenant, mock_payment_method
):
    """Test deleting payment method used by active autopay."""
    # Arrange
    mock_get_tenant.return_value = mock_tenant
    
    # Mock active autopay exists
    mock_autopay = MagicMock()
    mock_autopay.is_active = True
    
    async def mock_scalar_side_effect(*args, **kwargs):
        if not hasattr(mock_scalar_side_effect, 'call_count'):
            mock_scalar_side_effect.call_count = 0
        mock_scalar_side_effect.call_count += 1
        
        if mock_scalar_side_effect.call_count == 1:
            return mock_payment_method
        return mock_autopay
    
    mock_session.scalar.side_effect = mock_scalar_side_effect
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await delete_payment_method(mock_user, mock_payment_method.id, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "active autopay" in exc_info.value.detail


# =============================================================================
# Tests: set_default_payment_method
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service._unset_default_payment_method')
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_set_default_payment_method_success(
    mock_get_tenant, mock_unset_default, mock_session, mock_user, mock_tenant, mock_payment_method
):
    """Test setting a payment method as default."""
    # Arrange
    mock_get_tenant.return_value = mock_tenant
    mock_session.scalar.return_value = mock_payment_method
    mock_unset_default.return_value = None
    
    # Act
    result = await set_default_payment_method(mock_user, mock_payment_method.id, mock_session)
    
    # Assert
    assert result.is_default is True
    mock_unset_default.assert_called_once_with(mock_tenant.id, mock_session)
    mock_session.add.assert_called_with(mock_payment_method)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_set_default_payment_method_not_found(
    mock_get_tenant, mock_session, mock_user, mock_tenant
):
    """Test setting non-existent payment method as default."""
    # Arrange
    mock_get_tenant.return_value = mock_tenant
    mock_session.scalar.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await set_default_payment_method(mock_user, uuid4(), mock_session)
    
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail


# =============================================================================
# Tests: list_payment_methods
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.service._get_tenant_for_user')
async def test_list_payment_methods_success(
    mock_get_tenant, mock_session, mock_user, mock_tenant
):
    """Test listing payment methods."""
    # Arrange
    mock_get_tenant.return_value = mock_tenant
    
    # Create multiple payment methods
    pm1 = MagicMock()
    pm1.id = uuid4()
    pm1.is_default = True
    pm1.payment_method_type = "card"
    pm1.last_four = "4242"
    pm1.brand = "visa"
    pm1.is_verified = True
    pm1.is_usable = True
    pm1.display_name = "Visa •••• 4242"
    pm1.created_at = datetime.now(timezone.utc)
    pm1.bank_name = None
    pm1.institution_number = None
    pm1.exp_month = 12
    pm1.exp_year = 2025
    
    pm2 = MagicMock()
    pm2.id = uuid4()
    pm2.is_default = False
    pm2.payment_method_type = "acss_debit"
    pm2.last_four = "6789"
    pm2.bank_name = "TD Bank"
    pm2.is_verified = True
    pm2.is_usable = True
    pm2.display_name = "TD Bank •••• 6789"
    pm2.created_at = datetime.now(timezone.utc)
    pm2.brand = None
    pm2.institution_number = "004"
    pm2.exp_month = None
    pm2.exp_year = None
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [pm1, pm2]
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await list_payment_methods(mock_user, mock_session)
    
    # Assert
    assert len(result.items) == 2
    assert result.default_id == pm1.id
    assert result.items[0].payment_method_type == "card"
    assert result.items[1].payment_method_type == "acss_debit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

