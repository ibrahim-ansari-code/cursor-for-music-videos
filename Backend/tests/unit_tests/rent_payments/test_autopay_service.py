"""
Unit tests for Autopay Service.

Tests automated rent payment processing including:
- Daily autopay processing
- Payment creation and confirmation
- Retry logic with exponential backoff
- Failure notifications
- Grace period handling
- Sentry integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

from Backend.api.rent_payments.autopay_service import AutopayService
from Backend.models.rent_autopay_enrollment import RentAutopayEnrollment
from Backend.models.rent_payment_transaction import (
    RentPaymentTransaction,
    RentPaymentTransactionStatus,
)
from Backend.models.lease import Lease
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.tenant_payment_method import TenantPaymentMethod
from Backend.models.stripe_connected_account import StripeConnectedAccount
from Backend.models.enums import TenantType

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
    session.exec = AsyncMock()
    return session


@pytest.fixture
def mock_lease():
    """Create mock lease."""
    property_obj = MagicMock(spec=Property)
    property_obj.id = uuid4()
    property_obj.user_id = uuid4()
    property_obj.address = "123 Test St"
    
    lease = MagicMock(spec=Lease)
    lease.id = 123
    lease.tenant_id = uuid4()
    lease.property_id = property_obj.id
    lease.monthly_rent = Decimal("2000.00")
    lease.rent_due_day = 1
    lease.property = property_obj
    return lease


@pytest.fixture
def mock_tenant():
    """Create mock tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = uuid4()
    tenant.first_name = "John"
    tenant.last_name = "Doe"
    tenant.tenant_type = TenantType.INDIVIDUAL
    tenant.company_name = None
    return tenant


@pytest.fixture
def mock_payment_method():
    """Create mock payment method."""
    pm = MagicMock(spec=TenantPaymentMethod)
    pm.id = uuid4()
    pm.stripe_payment_method_id = "pm_test123"
    pm.payment_method_type = "card"
    pm.card_brand = "visa"
    pm.card_last_four = "4242"
    return pm


@pytest.fixture
def mock_connected_account():
    """Create mock connected account."""
    account = MagicMock(spec=StripeConnectedAccount)
    account.id = uuid4()
    account.stripe_account_id = "acct_test123"
    account.onboarding_status = "complete"
    account.charges_enabled = True
    return account


@pytest.fixture
def mock_enrollment(mock_lease):
    """Create mock autopay enrollment."""
    enrollment = MagicMock(spec=RentAutopayEnrollment)
    enrollment.id = uuid4()
    enrollment.lease_id = mock_lease.id
    enrollment.tenant_id = mock_lease.tenant_id
    enrollment.payment_method_id = uuid4()
    enrollment.is_active = True
    enrollment.next_scheduled_at = date.today()
    enrollment.current_retry_count = 0
    enrollment.last_failure_reason = None
    enrollment.last_attempt_at = None
    enrollment.last_success_at = None
    return enrollment


# =============================================================================
# Tests: _calculate_next_autopay_date
# =============================================================================

def test_calculate_next_autopay_date_mid_month():
    """Test calculating next autopay date for mid-month due date."""
    # Arrange
    rent_due_day = 15
    from_date = date(2024, 1, 10)
    
    # Act
    next_date = AutopayService._calculate_next_autopay_date(rent_due_day, from_date)
    
    # Assert - Returns datetime, should schedule 1 day before due date (14th)
    assert next_date.date() == date(2024, 1, 14)


def test_calculate_next_autopay_date_first_of_month():
    """Test calculating next autopay date for 1st of month."""
    # Arrange
    rent_due_day = 1
    from_date = date(2024, 1, 15)
    
    # Act
    next_date = AutopayService._calculate_next_autopay_date(rent_due_day, from_date)
    
    # Assert - Should be last day of current month (Jan 31st)
    assert next_date.date() == date(2024, 1, 31)


def test_calculate_next_autopay_date_month_end_handling():
    """Test month-end handling for dates that don't exist in all months."""
    # Arrange
    rent_due_day = 31  # Due on 31st
    from_date = date(2024, 1, 15)
    
    # Act
    next_date = AutopayService._calculate_next_autopay_date(rent_due_day, from_date)
    
    # Assert - Should be Jan 30th (1 day before 31st)
    assert next_date.date() == date(2024, 1, 30)


def test_calculate_next_autopay_date_february_handling():
    """Test February handling for high due dates."""
    # Arrange
    rent_due_day = 31
    from_date = date(2024, 2, 1)  # Leap year
    
    # Act
    next_date = AutopayService._calculate_next_autopay_date(rent_due_day, from_date)
    
    # Assert - Should be Feb 28th (last day minus 1 for autopay)
    assert next_date.date() == date(2024, 2, 28)


# =============================================================================
# Tests: _find_due_enrollments
# =============================================================================

@pytest.mark.asyncio
async def test_find_due_enrollments_returns_active_enrollments(mock_session):
    """Test finding enrollments due for payment."""
    # Arrange
    today = date.today()
    mock_result = MagicMock()
    mock_result.all.return_value = [
        MagicMock(id=uuid4(), is_active=True),
        MagicMock(id=uuid4(), is_active=True),
    ]
    # session.exec is NOT async in SQLModel
    mock_session.exec.return_value = mock_result
    
    # Act
    enrollments = await AutopayService._find_due_enrollments(mock_session, today)
    
    # Assert
    assert len(enrollments) == 2
    mock_session.exec.assert_called_once()


@pytest.mark.asyncio
async def test_find_due_enrollments_empty_result(mock_session):
    """Test finding enrollments when none are due."""
    # Arrange
    today = date.today()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.exec.return_value = mock_result
    
    # Act
    enrollments = await AutopayService._find_due_enrollments(mock_session, today)
    
    # Assert
    assert len(enrollments) == 0


# =============================================================================
# Tests: _handle_payment_failure
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.AutopayService._send_failure_notification')
async def test_handle_payment_failure_first_retry(
    mock_send_notification, mock_session, mock_enrollment, mock_tenant, mock_lease
):
    """Test handling first payment failure schedules retry."""
    # Arrange
    mock_enrollment.current_retry_count = 0
    mock_enrollment.next_scheduled_at = date.today()
    failure_reason = "card_declined"
    
    # Act
    await AutopayService._handle_payment_failure(
        mock_enrollment, mock_tenant, mock_lease, mock_session, failure_reason
    )
    
    # Assert
    assert mock_enrollment.current_retry_count == 1
    assert mock_enrollment.last_failure_reason == failure_reason
    # Should schedule retry (check it's been updated to a datetime)
    assert mock_enrollment.next_scheduled_at is not None
    assert isinstance(mock_enrollment.next_scheduled_at, datetime)
    mock_session.add.assert_called_with(mock_enrollment)
    # Notification IS sent on retry with retry_days parameter
    mock_send_notification.assert_called_once_with(
        mock_enrollment, mock_tenant, mock_lease, failure_reason, 1
    )


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.AutopayService._send_failure_notification')
async def test_handle_payment_failure_second_retry(
    mock_send_notification, mock_session, mock_enrollment, mock_tenant, mock_lease
):
    """Test handling second payment failure schedules correct retry interval."""
    # Arrange
    mock_enrollment.current_retry_count = 1
    mock_enrollment.next_scheduled_at = date.today()
    failure_reason = "insufficient_funds"
    
    # Act
    await AutopayService._handle_payment_failure(
        mock_enrollment, mock_tenant, mock_lease, mock_session, failure_reason
    )
    
    # Assert
    assert mock_enrollment.current_retry_count == 2
    # Should schedule retry (check it's been updated to a datetime)
    assert mock_enrollment.next_scheduled_at is not None
    assert isinstance(mock_enrollment.next_scheduled_at, datetime)
    # Notification IS sent on retry with retry_days parameter (3 days for 2nd retry)
    mock_send_notification.assert_called_once_with(
        mock_enrollment, mock_tenant, mock_lease, failure_reason, 3
    )


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.AutopayService._send_failure_notification')
@patch('Backend.api.rent_payments.autopay_service.AutopayService._pause_enrollment')
async def test_handle_payment_failure_max_retries_pauses_enrollment(
    mock_pause, mock_send_notification, mock_session, mock_enrollment, mock_tenant, mock_lease
):
    """Test payment failure after max retries pauses enrollment."""
    # Arrange
    mock_enrollment.current_retry_count = 2  # Already tried twice
    failure_reason = "card_expired"
    
    # Act
    await AutopayService._handle_payment_failure(
        mock_enrollment, mock_tenant, mock_lease, mock_session, failure_reason
    )
    
    # Assert
    assert mock_enrollment.current_retry_count == 3
    mock_pause.assert_called_once()
    mock_send_notification.assert_called_once()  # Sends failure notification


# =============================================================================
# Tests: _pause_enrollment
# =============================================================================

@pytest.mark.asyncio
async def test_pause_enrollment_deactivates_and_logs_reason(
    mock_session, mock_enrollment
):
    """Test pausing enrollment sets is_active to False."""
    # Arrange
    reason = "Maximum retry attempts reached"
    
    # Act
    await AutopayService._pause_enrollment(mock_enrollment, mock_session, reason)
    
    # Assert
    assert mock_enrollment.is_active is False
    assert mock_enrollment.last_failure_reason == reason
    assert mock_enrollment.paused_at is not None
    mock_session.add.assert_called_with(mock_enrollment)


# =============================================================================
# Tests: _create_autopay_payment
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.get_stripe_client')
@patch('Backend.api.rent_payments.autopay_service.sentry_sdk')
async def test_create_autopay_payment_success(
    mock_sentry, mock_get_stripe, mock_session, mock_lease, mock_tenant,
    mock_payment_method, mock_connected_account, mock_enrollment
):
    """Test successful autopay payment creation."""
    # Arrange
    mock_stripe = MagicMock()
    mock_pi = MagicMock()
    mock_pi.id = "pi_test123"
    mock_pi.status = "succeeded"
    # Stripe client is async, so create() needs to return an awaitable
    mock_stripe.payment_intents.create = AsyncMock(return_value=mock_pi)
    mock_get_stripe.return_value = mock_stripe
    
    # Mock the transaction creation check
    mock_result = MagicMock()
    mock_result.first.return_value = None  # No existing transaction
    
    async def mock_exec(*args, **kwargs):
        return mock_result
    mock_session.exec.side_effect = mock_exec
    
    # Act
    result = await AutopayService._create_autopay_payment(
        mock_lease, mock_tenant, mock_payment_method,
        mock_connected_account, mock_enrollment,
        str(mock_lease.property.user_id), mock_session
    )
    
    # Assert
    assert result is not None
    assert result.id == "pi_test123"
    mock_stripe.payment_intents.create.assert_called_once()
    # Should create transaction record
    mock_session.add.assert_called()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.get_stripe_client')
@patch('Backend.api.rent_payments.autopay_service.sentry_sdk')
async def test_create_autopay_payment_card_declined(
    mock_sentry, mock_get_stripe, mock_session, mock_lease, mock_tenant,
    mock_payment_method, mock_connected_account, mock_enrollment
):
    """Test autopay payment with card declined error."""
    # Arrange
    from stripe import CardError
    
    mock_stripe = MagicMock()
    # Stripe client is async, so create() needs to be an AsyncMock that raises
    mock_stripe.payment_intents.create = AsyncMock(
        side_effect=CardError("Your card was declined", None, "card_declined")
    )
    mock_get_stripe.return_value = mock_stripe
    
    # Act
    result = await AutopayService._create_autopay_payment(
        mock_lease, mock_tenant, mock_payment_method,
        mock_connected_account, mock_enrollment,
        str(mock_lease.property.user_id), mock_session
    )
    
    # Assert
    assert result is None
    # CardError uses capture_message, not capture_exception
    mock_sentry.capture_message.assert_called_once()
    args, kwargs = mock_sentry.capture_message.call_args
    assert "Autopay Card Declined" in args[0]
    assert kwargs["level"] == "warning"


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.get_stripe_client')
@patch('Backend.api.rent_payments.autopay_service.sentry_sdk')
async def test_create_autopay_payment_uses_idempotency_key(
    mock_sentry, mock_get_stripe, mock_session, mock_lease, mock_tenant,
    mock_payment_method, mock_connected_account, mock_enrollment
):
    """Test autopay payment uses idempotency key."""
    # Arrange
    mock_stripe = MagicMock()
    mock_pi = MagicMock()
    mock_pi.status = "succeeded"
    mock_stripe.payment_intents.create.return_value = mock_pi
    mock_get_stripe.return_value = mock_stripe
    
    mock_enrollment.next_scheduled_at = date(2024, 1, 15)
    
    mock_result = AsyncMock()
    mock_result.first.return_value = None
    mock_session.exec.return_value = mock_result
    
    # Act
    await AutopayService._create_autopay_payment(
        mock_lease, mock_tenant, mock_payment_method,
        mock_connected_account, mock_enrollment,
        str(mock_lease.property.user_id), mock_session
    )
    
    # Assert
    call_kwargs = mock_stripe.payment_intents.create.call_args[1]
    assert 'idempotency_key' in call_kwargs
    assert call_kwargs['idempotency_key'].startswith(f"autopay-{mock_enrollment.id}")


# =============================================================================
# Tests: _process_single_enrollment
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.AutopayService._create_autopay_payment')
@patch('Backend.api.rent_payments.autopay_service.AutopayService._send_success_notification')
async def test_process_single_enrollment_success(
    mock_send_success, mock_create_payment, mock_session,
    mock_enrollment, mock_lease, mock_tenant, mock_payment_method, mock_connected_account
):
    """Test successful processing of single enrollment."""
    # Arrange
    mock_pi = MagicMock()
    mock_pi.id = "pi_test123"
    mock_create_payment.return_value = mock_pi
    
    # Mock all database queries - Results are not async, only exec() is
    lease_result = MagicMock()
    lease_result.first.return_value = mock_lease
    
    tenant_result = MagicMock()
    tenant_result.first.return_value = mock_tenant
    
    pm_result = MagicMock()
    pm_result.first.return_value = mock_payment_method
    
    account_result = MagicMock()
    account_result.first.return_value = mock_connected_account
    
    # session.exec() is async, so we need to make it return an awaitable
    async def mock_exec(*args, **kwargs):
        return mock_session.exec.side_effect_results.pop(0)
    
    mock_session.exec.side_effect_results = [
        lease_result, tenant_result, pm_result, account_result
    ]
    mock_session.exec.side_effect = mock_exec
    
    # Act
    success = await AutopayService._process_single_enrollment(mock_enrollment, mock_session)
    
    # Assert
    assert success is True
    assert mock_enrollment.last_success_at is not None
    assert mock_enrollment.current_retry_count == 0
    assert mock_enrollment.next_scheduled_at is not None
    mock_send_success.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.AutopayService._pause_enrollment')
async def test_process_single_enrollment_lease_not_found(
    mock_pause, mock_session, mock_enrollment
):
    """Test processing enrollment when lease not found."""
    # Arrange
    lease_result = MagicMock()
    lease_result.first.return_value = None
    
    async def mock_exec(*args, **kwargs):
        return lease_result
    mock_session.exec.side_effect = mock_exec
    
    # Act
    success = await AutopayService._process_single_enrollment(mock_enrollment, mock_session)
    
    # Assert
    assert success is False
    mock_pause.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.AutopayService._pause_enrollment')
async def test_process_single_enrollment_payment_method_not_found(
    mock_pause, mock_session, mock_enrollment, mock_lease, mock_tenant
):
    """Test processing enrollment when payment method not found."""
    # Arrange
    lease_result = MagicMock()
    lease_result.first.return_value = mock_lease
    
    tenant_result = MagicMock()
    tenant_result.first.return_value = mock_tenant
    
    pm_result = MagicMock()
    pm_result.first.return_value = None  # Payment method not found
    
    async def mock_exec(*args, **kwargs):
        return mock_session.exec.side_effect_results.pop(0)
    
    mock_session.exec.side_effect_results = [lease_result, tenant_result, pm_result]
    mock_session.exec.side_effect = mock_exec
    
    # Act
    success = await AutopayService._process_single_enrollment(mock_enrollment, mock_session)
    
    # Assert
    assert success is False
    mock_pause.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.AutopayService._pause_enrollment')
async def test_process_single_enrollment_connected_account_not_active(
    mock_pause, mock_session, mock_enrollment, mock_lease,
    mock_tenant, mock_payment_method, mock_connected_account
):
    """Test processing enrollment when connected account not active."""
    # Arrange
    mock_connected_account.onboarding_status = "pending"  # Not complete
    
    lease_result = MagicMock()
    lease_result.first.return_value = mock_lease
    
    tenant_result = MagicMock()
    tenant_result.first.return_value = mock_tenant
    
    pm_result = MagicMock()
    pm_result.first.return_value = mock_payment_method
    
    account_result = MagicMock()
    account_result.first.return_value = mock_connected_account
    
    async def mock_exec(*args, **kwargs):
        return mock_session.exec.side_effect_results.pop(0)
    
    mock_session.exec.side_effect_results = [
        lease_result, tenant_result, pm_result, account_result
    ]
    mock_session.exec.side_effect = mock_exec
    
    # Act
    success = await AutopayService._process_single_enrollment(mock_enrollment, mock_session)
    
    # Assert
    assert success is False
    mock_pause.assert_called_once()


# =============================================================================
# Tests: process_daily_autopay
# =============================================================================

@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.AutopayService._find_due_enrollments')
@patch('Backend.api.rent_payments.autopay_service.AutopayService._process_single_enrollment')
async def test_process_daily_autopay_success(
    mock_process_enrollment, mock_find_enrollments, mock_session
):
    """Test daily autopay processing with successful payments."""
    # Arrange
    enrollments = [MagicMock(id=uuid4()) for _ in range(3)]
    mock_find_enrollments.return_value = enrollments
    mock_process_enrollment.side_effect = [True, True, False]  # 2 success, 1 fail
    
    # Act
    results = await AutopayService.process_daily_autopay(mock_session)
    
    # Assert
    assert results["processed"] == 3
    assert results["successful"] == 2
    assert results["failed"] == 1
    assert len(results["errors"]) == 0
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.AutopayService._find_due_enrollments')
async def test_process_daily_autopay_no_enrollments(
    mock_find_enrollments, mock_session
):
    """Test daily autopay processing with no due enrollments."""
    # Arrange
    mock_find_enrollments.return_value = []
    
    # Act
    results = await AutopayService.process_daily_autopay(mock_session)
    
    # Assert
    assert results["processed"] == 0
    assert results["successful"] == 0
    assert results["failed"] == 0


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.AutopayService._find_due_enrollments')
@patch('Backend.api.rent_payments.autopay_service.AutopayService._process_single_enrollment')
async def test_process_daily_autopay_handles_individual_errors(
    mock_process_enrollment, mock_find_enrollments, mock_session
):
    """Test daily autopay processing handles individual enrollment errors."""
    # Arrange
    enrollments = [MagicMock(id=uuid4()) for _ in range(2)]
    mock_find_enrollments.return_value = enrollments
    mock_process_enrollment.side_effect = [
        Exception("Database error"),  # First enrollment raises error
        True,  # Second enrollment succeeds
    ]
    
    # Act
    results = await AutopayService.process_daily_autopay(mock_session)
    
    # Assert
    assert results["processed"] == 1  # Only second processed
    assert results["successful"] == 1
    assert results["failed"] == 1
    assert len(results["errors"]) == 1
    assert "Database error" in str(results["errors"][0]["error"])


# =============================================================================
# Edge Cases
# =============================================================================

def test_calculate_next_autopay_date_handles_leap_year():
    """Test next autopay date calculation in leap year February."""
    # Arrange
    rent_due_day = 29
    from_date = date(2024, 2, 1)  # 2024 is a leap year
    
    # Act
    next_date = AutopayService._calculate_next_autopay_date(rent_due_day, from_date)
    
    # Assert - Should be Feb 28th (1 day before 29th)
    assert next_date.date() == date(2024, 2, 28)


def test_calculate_next_autopay_date_handles_non_leap_year():
    """Test next autopay date calculation in non-leap year February."""
    # Arrange
    rent_due_day = 29
    from_date = date(2023, 2, 1)  # 2023 is not a leap year
    
    # Act
    next_date = AutopayService._calculate_next_autopay_date(rent_due_day, from_date)
    
    # Assert - Should be Feb 27th (1 day before last day of Feb)
    assert next_date.date() == date(2023, 2, 27)


@pytest.mark.asyncio
@patch('Backend.api.rent_payments.autopay_service.AutopayService._send_failure_notification')
async def test_handle_payment_failure_with_no_tenant_or_lease(
    mock_send_notification, mock_session, mock_enrollment
):
    """Test handling payment failure when tenant/lease are None."""
    # Arrange
    failure_reason = "Error loading data"
    
    # Act - should not crash
    await AutopayService._handle_payment_failure(
        mock_enrollment, None, None, mock_session, failure_reason
    )
    
    # Assert
    assert mock_enrollment.current_retry_count == 1
    mock_session.add.assert_called()

