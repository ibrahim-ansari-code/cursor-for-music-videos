"""
Unit tests for rent payment refund service functions.

Tests cover:
- Refund creation with validation
- Partial and full refunds
- Platform fee handling (non-refundable)
- Access control for landlords
- Stripe API integration and error handling
- Dispute retrieval and listing
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from fastapi import HTTPException

from Backend.api.rent_payments.refund_service import (
    create_refund,
    get_refund,
    list_refunds,
    get_dispute,
    list_disputes,
)
from Backend.models.rent_payment_transaction import RentPaymentTransactionStatus
from Backend.models.rent_payment_refund import RefundStatus, RefundReason
from Backend.models.rent_payment_dispute import DisputeStatus


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
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def mock_landlord_user():
    """Create a mock landlord user."""
    user = MagicMock()
    user.id = uuid4()
    user.first_name = "Jane"
    user.last_name = "Landlord"
    user.email = "landlord@example.com"
    return user


@pytest.fixture
def mock_transaction():
    """Create a mock successful transaction."""
    transaction = MagicMock()
    transaction.id = uuid4()
    transaction.tenant_id = 123
    transaction.lease_id = 456
    transaction.landlord_user_id = uuid4()
    transaction.stripe_payment_intent_id = "pi_test123"
    transaction.stripe_charge_id = "ch_test123"
    transaction.amount_cents = 200000  # $2000
    transaction.amount_dollars = Decimal("2000.00")
    transaction.application_fee_cents = 800  # $8
    transaction.currency = "cad"
    transaction.status = RentPaymentTransactionStatus.SUCCEEDED
    transaction.refunds = []
    transaction.total_refunded_cents = 0
    
    # Mock lease
    lease = MagicMock()
    lease.id = 456
    transaction.lease = lease
    
    return transaction


@pytest.fixture
def mock_connected_account():
    """Create a mock Stripe connected account."""
    account = MagicMock()
    account.id = uuid4()
    account.user_id = uuid4()
    account.stripe_account_id = "acct_test123"
    return account


@pytest.fixture
def mock_refund():
    """Create a mock refund record."""
    refund = MagicMock()
    refund.id = uuid4()
    refund.transaction_id = uuid4()
    refund.stripe_refund_id = "re_test123"
    refund.stripe_charge_id = "ch_test123"
    refund.amount_cents = 200000
    refund.amount_dollars = Decimal("2000.00")
    refund.currency = "cad"
    refund.application_fee_refunded_cents = None  # Platform fee non-refundable
    refund.status = RefundStatus.SUCCEEDED
    refund.reason = RefundReason.REQUESTED_BY_CUSTOMER
    refund.notes = "Test refund"
    refund.failure_reason = None
    refund.initiated_by_user_id = uuid4()
    refund.created_at = datetime.now(timezone.utc)
    refund.succeeded_at = datetime.now(timezone.utc)
    refund.failed_at = None
    
    # Mock initiated_by user
    user = MagicMock()
    user.first_name = "Jane"
    user.last_name = "Landlord"
    refund.initiated_by = user
    
    # Mock transaction
    transaction = MagicMock()
    transaction.landlord_user_id = uuid4()
    refund.transaction = transaction
    
    return refund


@pytest.fixture
def mock_dispute():
    """Create a mock dispute record."""
    dispute = MagicMock()
    dispute.id = uuid4()
    dispute.transaction_id = uuid4()
    dispute.stripe_dispute_id = "dp_test123"
    dispute.stripe_charge_id = "ch_test123"
    dispute.amount_cents = 200000
    dispute.currency = "cad"
    dispute.status = DisputeStatus.NEEDS_RESPONSE
    dispute.reason = "fraudulent"
    dispute.evidence_due_by = datetime.now(timezone.utc)
    dispute.evidence_submitted = False
    dispute.evidence_submitted_at = None
    dispute.is_charge_refundable = True
    dispute.created_at = datetime.now(timezone.utc)
    dispute.closed_at = None
    dispute.landlord_notified = True
    dispute.landlord_notified_at = datetime.now(timezone.utc)
    dispute.needs_attention = True
    
    # Mock transaction
    transaction = MagicMock()
    transaction.landlord_user_id = uuid4()
    dispute.transaction = transaction
    
    return dispute


# =============================================================================
# Tests: create_refund
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.refund_service.get_stripe_client')
@patch('Backend.api.rent_payments.refund_service._build_refund_response')
async def test_create_refund_full_refund_success(
    mock_build_response, mock_get_stripe, mock_session, mock_landlord_user, 
    mock_transaction, mock_connected_account
):
    """Test successful full refund creation."""
    # Arrange
    from Backend.api.rent_payments.schemas import RefundCreateRequest
    
    # Set landlord ID to match user
    mock_transaction.landlord_user_id = mock_landlord_user.id
    mock_connected_account.user_id = mock_landlord_user.id
    
    # Mock database queries
    async def mock_scalar_side_effect(*args, **kwargs):
        if not hasattr(mock_scalar_side_effect, 'call_count'):
            mock_scalar_side_effect.call_count = 0
        mock_scalar_side_effect.call_count += 1
        
        if mock_scalar_side_effect.call_count == 1:
            return mock_transaction
        return mock_connected_account
    
    mock_session.scalar.side_effect = mock_scalar_side_effect
    
    # Mock Stripe refund
    mock_stripe_refund = MagicMock()
    mock_stripe_refund.id = "re_test123"
    
    mock_stripe = MagicMock()
    mock_stripe.refunds.create = AsyncMock(return_value=mock_stripe_refund)
    mock_get_stripe.return_value = mock_stripe
    
    # Mock refresh to populate ID
    async def mock_refresh(obj):
        if hasattr(obj, 'stripe_refund_id'):
            obj.id = uuid4()
    mock_session.refresh.side_effect = mock_refresh
    
    # Mock response builder
    mock_response = MagicMock()
    mock_response.id = uuid4()
    mock_response.amount_cents = 200000
    mock_build_response.return_value = mock_response
    
    # Act
    data = RefundCreateRequest(
        transaction_id=mock_transaction.id,
        amount_cents=200000,  # Full refund
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
        notes="Customer requested refund"
    )
    result = await create_refund(mock_landlord_user, data, mock_session)
    
    # Assert
    assert result.id is not None
    assert result.amount_cents == 200000
    
    # Verify Stripe refund call
    mock_stripe.refunds.create.assert_called_once()
    call_kwargs = mock_stripe.refunds.create.call_args[1]
    assert call_kwargs["charge"] == "ch_test123"
    assert call_kwargs["amount"] == 200000
    assert "idempotency_key" in call_kwargs
    assert call_kwargs["stripe_account"] == "acct_test123"
    
    # Verify refund record created
    mock_session.add.assert_called()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_refund_partial_refund_success(
    mock_session, mock_landlord_user, mock_transaction, mock_connected_account
):
    """Test successful partial refund creation."""
    # Arrange
    from Backend.api.rent_payments.schemas import RefundCreateRequest
    from unittest.mock import patch
    
    mock_transaction.landlord_user_id = mock_landlord_user.id
    mock_connected_account.user_id = mock_landlord_user.id
    
    async def mock_scalar_side_effect(*args, **kwargs):
        if not hasattr(mock_scalar_side_effect, 'call_count'):
            mock_scalar_side_effect.call_count = 0
        mock_scalar_side_effect.call_count += 1
        
        if mock_scalar_side_effect.call_count == 1:
            return mock_transaction
        return mock_connected_account
    
    mock_session.scalar.side_effect = mock_scalar_side_effect
    
    with patch('Backend.api.rent_payments.refund_service.get_stripe_client') as mock_get_stripe, \
         patch('Backend.api.rent_payments.refund_service._build_refund_response') as mock_build_response:
        
        mock_stripe_refund = MagicMock()
        mock_stripe_refund.id = "re_test123"
        
        mock_stripe = MagicMock()
        mock_stripe.refunds.create = AsyncMock(return_value=mock_stripe_refund)
        mock_get_stripe.return_value = mock_stripe
        
        mock_response = MagicMock()
        mock_response.amount_cents = 50000
        mock_build_response.return_value = mock_response
        
        # Act
        data = RefundCreateRequest(
            transaction_id=mock_transaction.id,
            amount_cents=50000,  # Partial refund $500
            reason=RefundReason.REQUESTED_BY_CUSTOMER,
            notes="Partial refund"
        )
        result = await create_refund(mock_landlord_user, data, mock_session)
        
        # Assert
        assert result.amount_cents == 50000
        call_kwargs = mock_stripe.refunds.create.call_args[1]
        assert call_kwargs["amount"] == 50000


@pytest.mark.asyncio
async def test_create_refund_transaction_not_found(mock_session, mock_landlord_user):
    """Test refund creation when transaction not found."""
    # Arrange
    from Backend.api.rent_payments.schemas import RefundCreateRequest
    
    mock_session.scalar.return_value = None
    
    # Act & Assert
    data = RefundCreateRequest(
        transaction_id=uuid4(),
        amount_cents=200000,
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_refund(mock_landlord_user, data, mock_session)
    
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_create_refund_wrong_landlord(
    mock_session, mock_landlord_user, mock_transaction
):
    """Test refund creation by wrong landlord (not owner)."""
    # Arrange
    from Backend.api.rent_payments.schemas import RefundCreateRequest
    
    # Different landlord ID
    mock_transaction.landlord_user_id = uuid4()
    mock_session.scalar.return_value = mock_transaction
    
    # Act & Assert
    data = RefundCreateRequest(
        transaction_id=mock_transaction.id,
        amount_cents=200000,
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_refund(mock_landlord_user, data, mock_session)
    
    assert exc_info.value.status_code == 403
    assert "your properties" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_create_refund_transaction_not_succeeded(
    mock_session, mock_landlord_user, mock_transaction
):
    """Test refund creation for non-successful transaction."""
    # Arrange
    from Backend.api.rent_payments.schemas import RefundCreateRequest
    
    mock_transaction.landlord_user_id = mock_landlord_user.id
    mock_transaction.status = RentPaymentTransactionStatus.PENDING
    mock_session.scalar.return_value = mock_transaction
    
    # Act & Assert
    data = RefundCreateRequest(
        transaction_id=mock_transaction.id,
        amount_cents=200000,
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_refund(mock_landlord_user, data, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "cannot refund" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_create_refund_no_charge_id(
    mock_session, mock_landlord_user, mock_transaction
):
    """Test refund creation when transaction has no charge ID."""
    # Arrange
    from Backend.api.rent_payments.schemas import RefundCreateRequest
    
    mock_transaction.landlord_user_id = mock_landlord_user.id
    mock_transaction.stripe_charge_id = None
    mock_session.scalar.return_value = mock_transaction
    
    # Act & Assert
    data = RefundCreateRequest(
        transaction_id=mock_transaction.id,
        amount_cents=200000,
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_refund(mock_landlord_user, data, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "no charge id" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_create_refund_exceeds_available_amount(
    mock_session, mock_landlord_user, mock_transaction
):
    """Test refund creation exceeding available amount."""
    # Arrange
    from Backend.api.rent_payments.schemas import RefundCreateRequest
    
    mock_transaction.landlord_user_id = mock_landlord_user.id
    # Mock existing refunds to calculate available amount
    existing_refund = MagicMock()
    existing_refund.amount_cents = 150000  # Already refunded $1500
    existing_refund.status = RefundStatus.SUCCEEDED
    mock_transaction.refunds = [existing_refund]
    mock_session.scalar.return_value = mock_transaction
    
    # Act & Assert
    data = RefundCreateRequest(
        transaction_id=mock_transaction.id,
        amount_cents=60000,  # Trying to refund $600 more (total would be $2100)
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_refund(mock_landlord_user, data, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "exceeds available" in exc_info.value.detail.lower()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.refund_service.get_stripe_client')
@patch('Backend.api.rent_payments.refund_service.sentry_sdk')
async def test_create_refund_stripe_invalid_request_error(
    mock_sentry, mock_get_stripe, mock_session, mock_landlord_user,
    mock_transaction, mock_connected_account
):
    """Test refund creation with Stripe invalid request error."""
    # Arrange
    from Backend.api.rent_payments.schemas import RefundCreateRequest
    from stripe import InvalidRequestError
    
    mock_transaction.landlord_user_id = mock_landlord_user.id
    mock_connected_account.user_id = mock_landlord_user.id
    
    async def mock_scalar_side_effect(*args, **kwargs):
        if not hasattr(mock_scalar_side_effect, 'call_count'):
            mock_scalar_side_effect.call_count = 0
        mock_scalar_side_effect.call_count += 1
        
        if mock_scalar_side_effect.call_count == 1:
            return mock_transaction
        return mock_connected_account
    
    mock_session.scalar.side_effect = mock_scalar_side_effect
    
    # Mock Stripe error
    mock_stripe = MagicMock()
    mock_stripe.refunds.create = AsyncMock(
        side_effect=InvalidRequestError("Charge already refunded", None)
    )
    mock_get_stripe.return_value = mock_stripe
    
    # Act & Assert
    data = RefundCreateRequest(
        transaction_id=mock_transaction.id,
        amount_cents=200000,
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_refund(mock_landlord_user, data, mock_session)
    
    assert exc_info.value.status_code == 400
    assert "refund failed" in exc_info.value.detail.lower()
    mock_sentry.capture_exception.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.refund_service.get_stripe_client')
@patch('Backend.api.rent_payments.refund_service.sentry_sdk')
async def test_create_refund_stripe_generic_error(
    mock_sentry, mock_get_stripe, mock_session, mock_landlord_user,
    mock_transaction, mock_connected_account
):
    """Test refund creation with generic Stripe error."""
    # Arrange
    from Backend.api.rent_payments.schemas import RefundCreateRequest
    from stripe import StripeError
    
    mock_transaction.landlord_user_id = mock_landlord_user.id
    mock_connected_account.user_id = mock_landlord_user.id
    
    async def mock_scalar_side_effect(*args, **kwargs):
        if not hasattr(mock_scalar_side_effect, 'call_count'):
            mock_scalar_side_effect.call_count = 0
        mock_scalar_side_effect.call_count += 1
        
        if mock_scalar_side_effect.call_count == 1:
            return mock_transaction
        return mock_connected_account
    
    mock_session.scalar.side_effect = mock_scalar_side_effect
    
    # Mock Stripe error
    mock_stripe = MagicMock()
    mock_stripe.refunds.create = AsyncMock(
        side_effect=StripeError("API error")
    )
    mock_get_stripe.return_value = mock_stripe
    
    # Act & Assert
    data = RefundCreateRequest(
        transaction_id=mock_transaction.id,
        amount_cents=200000,
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_refund(mock_landlord_user, data, mock_session)
    
    assert exc_info.value.status_code == 500
    mock_sentry.capture_exception.assert_called_once()


# =============================================================================
# Tests: get_refund
# =============================================================================

@pytest.mark.asyncio
async def test_get_refund_success(mock_session, mock_landlord_user, mock_refund):
    """Test successful refund retrieval."""
    # Arrange
    from unittest.mock import patch
    
    mock_refund.initiated_by_user_id = mock_landlord_user.id
    mock_refund.transaction.landlord_user_id = mock_landlord_user.id
    mock_session.scalar.return_value = mock_refund
    
    with patch('Backend.api.rent_payments.refund_service._build_refund_response') as mock_build:
        mock_response = MagicMock()
        mock_build.return_value = mock_response
        
        # Act
        result = await get_refund(mock_landlord_user, mock_refund.id, mock_session)
        
        # Assert
        assert result is not None
        mock_build.assert_called_once_with(mock_refund, mock_session)


@pytest.mark.asyncio
async def test_get_refund_not_found(mock_session, mock_landlord_user):
    """Test refund retrieval when not found."""
    # Arrange
    mock_session.scalar.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_refund(mock_landlord_user, uuid4(), mock_session)
    
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_refund_no_access(mock_session, mock_landlord_user, mock_refund):
    """Test refund retrieval without access."""
    # Arrange
    mock_refund.initiated_by_user_id = uuid4()  # Different user
    mock_refund.transaction.landlord_user_id = uuid4()  # Different landlord
    mock_session.scalar.return_value = mock_refund
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_refund(mock_landlord_user, mock_refund.id, mock_session)
    
    assert exc_info.value.status_code == 403


# =============================================================================
# Tests: list_refunds
# =============================================================================

@pytest.mark.asyncio
async def test_list_refunds_success(mock_session, mock_landlord_user):
    """Test successful refunds listing."""
    # Arrange
    from unittest.mock import patch
    from Backend.api.rent_payments.schemas import RefundResponse
    
    # Mock query results
    mock_result = MagicMock()
    mock_refund1 = MagicMock()
    mock_refund2 = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_refund1, mock_refund2]
    mock_session.execute.return_value = mock_result
    
    # Mock count
    mock_session.scalar.return_value = 2
    
    with patch('Backend.api.rent_payments.refund_service._build_refund_response') as mock_build:
        # Return actual RefundResponse objects
        mock_response1 = RefundResponse(
            id=uuid4(),
            transaction_id=uuid4(),
            stripe_refund_id="re_test1",
            stripe_charge_id="ch_test1",
            amount_cents=100000,
            amount=Decimal("1000.00"),
            currency="cad",
            status=RefundStatus.SUCCEEDED,
            reason=RefundReason.REQUESTED_BY_CUSTOMER,
            initiated_by_user_id=mock_landlord_user.id,
            created_at=datetime.now(timezone.utc),
        )
        mock_response2 = RefundResponse(
            id=uuid4(),
            transaction_id=uuid4(),
            stripe_refund_id="re_test2",
            stripe_charge_id="ch_test2",
            amount_cents=50000,
            amount=Decimal("500.00"),
            currency="cad",
            status=RefundStatus.SUCCEEDED,
            reason=RefundReason.REQUESTED_BY_CUSTOMER,
            initiated_by_user_id=mock_landlord_user.id,
            created_at=datetime.now(timezone.utc),
        )
        mock_build.side_effect = [mock_response1, mock_response2]
        
        # Act
        result = await list_refunds(mock_landlord_user, mock_session, limit=10, offset=0)
        
        # Assert
        assert result.total == 2
        assert len(result.items) == 2
        assert result.has_more is False


@pytest.mark.asyncio
async def test_list_refunds_with_filters(mock_session, mock_landlord_user):
    """Test refunds listing with status filter."""
    # Arrange
    from unittest.mock import patch
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_session.scalar.return_value = 0
    
    with patch('Backend.api.rent_payments.refund_service._build_refund_response'):
        # Act
        result = await list_refunds(
            mock_landlord_user, 
            mock_session, 
            status_filter="succeeded"
        )
        
        # Assert
        assert result.total == 0


# =============================================================================
# Tests: get_dispute
# =============================================================================

@pytest.mark.asyncio
async def test_get_dispute_success(mock_session, mock_landlord_user, mock_dispute):
    """Test successful dispute retrieval."""
    # Arrange
    mock_dispute.transaction.landlord_user_id = mock_landlord_user.id
    mock_session.scalar.return_value = mock_dispute
    
    # Act
    result = await get_dispute(mock_landlord_user, mock_dispute.id, mock_session)
    
    # Assert
    assert result is not None
    assert result.id == mock_dispute.id


@pytest.mark.asyncio
async def test_get_dispute_not_found(mock_session, mock_landlord_user):
    """Test dispute retrieval when not found."""
    # Arrange
    mock_session.scalar.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_dispute(mock_landlord_user, uuid4(), mock_session)
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_dispute_no_access(mock_session, mock_landlord_user, mock_dispute):
    """Test dispute retrieval without access."""
    # Arrange
    mock_dispute.transaction.landlord_user_id = uuid4()  # Different landlord
    mock_session.scalar.return_value = mock_dispute
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_dispute(mock_landlord_user, mock_dispute.id, mock_session)
    
    assert exc_info.value.status_code == 403


# =============================================================================
# Tests: list_disputes
# =============================================================================

@pytest.mark.asyncio
async def test_list_disputes_success(mock_session, mock_landlord_user):
    """Test successful disputes listing."""
    # Arrange
    from datetime import timedelta
    
    mock_result = MagicMock()
    mock_dispute1 = MagicMock()
    mock_dispute1.id = uuid4()
    mock_dispute1.transaction_id = uuid4()
    mock_dispute1.stripe_dispute_id = "dp_test1"
    mock_dispute1.stripe_charge_id = "ch_test1"
    mock_dispute1.amount_cents = 100000
    mock_dispute1.currency = "cad"
    mock_dispute1.status = DisputeStatus.NEEDS_RESPONSE
    mock_dispute1.reason = "fraudulent"
    mock_dispute1.evidence_due_by = datetime.now(timezone.utc) + timedelta(days=7)
    mock_dispute1.evidence_submitted = False
    mock_dispute1.evidence_submitted_at = None
    mock_dispute1.is_charge_refundable = True
    mock_dispute1.created_at = datetime.now(timezone.utc)
    mock_dispute1.closed_at = None
    mock_dispute1.landlord_notified = True
    mock_dispute1.landlord_notified_at = datetime.now(timezone.utc)
    mock_dispute1.needs_attention = True
    
    mock_dispute2 = MagicMock()
    mock_dispute2.id = uuid4()
    mock_dispute2.transaction_id = uuid4()
    mock_dispute2.stripe_dispute_id = "dp_test2"
    mock_dispute2.stripe_charge_id = "ch_test2"
    mock_dispute2.amount_cents = 50000
    mock_dispute2.currency = "cad"
    mock_dispute2.status = DisputeStatus.WON
    mock_dispute2.reason = "general"
    mock_dispute2.evidence_due_by = None
    mock_dispute2.evidence_submitted = True
    mock_dispute2.evidence_submitted_at = datetime.now(timezone.utc)
    mock_dispute2.is_charge_refundable = False
    mock_dispute2.created_at = datetime.now(timezone.utc)
    mock_dispute2.closed_at = datetime.now(timezone.utc)
    mock_dispute2.landlord_notified = True
    mock_dispute2.landlord_notified_at = datetime.now(timezone.utc)
    mock_dispute2.needs_attention = False
    
    mock_result.scalars.return_value.all.return_value = [mock_dispute1, mock_dispute2]
    mock_session.execute.return_value = mock_result
    
    # Mock counts - return twice (once for total, once for active)
    mock_session.scalar.side_effect = [2, 1]
    
    # Act
    result = await list_disputes(mock_landlord_user, mock_session, limit=10, offset=0)
    
    # Assert
    assert result.total == 2
    assert result.active_disputes == 1
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_list_disputes_needs_attention_only(mock_session, mock_landlord_user):
    """Test disputes listing with needs_attention filter."""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_session.scalar.side_effect = [0, 0]
    
    # Act
    result = await list_disputes(
        mock_landlord_user, 
        mock_session, 
        needs_attention_only=True
    )
    
    # Assert
    assert result.total == 0
    assert result.active_disputes == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

