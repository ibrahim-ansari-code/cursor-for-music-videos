"""
Unit tests for payment allocation functionality.

Tests the payment allocation system that links payments to invoices.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.accounting.payments.service import _create_payment_allocation, create_payment
from Backend.api.accounting.payments.helpers import build_payment_response_from_orm
from Backend.api.accounting.payments.schemas import PaymentCreate
from Backend.models.accounting.payment import Payment, PaymentMethod
from Backend.models.accounting.payment_allocation import PaymentAllocation
from Backend.models.accounting.invoice import Invoice
from Backend.models.accounting.common import PaymentStatus
from Backend.models.enums import UserType
from Backend.models.user import User
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.lease import Lease

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.scalar = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_landlord_user():
    """Create a mock landlord user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "landlord@example.com"
    user.user_type = UserType.LANDLORD
    user.is_admin = False
    return user


@pytest.fixture
def mock_tenant_user():
    """Create a mock tenant user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "tenant@example.com"
    user.user_type = UserType.TENANT
    user.is_admin = False
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "admin@example.com"
    user.user_type = UserType.ADMIN
    user.is_admin = True
    return user


@pytest.fixture
def mock_invoice():
    """Create a mock invoice."""
    invoice = MagicMock(spec=Invoice)
    invoice.id = 1
    invoice.amount = Decimal("1000.00")
    invoice.status = PaymentStatus.PENDING
    return invoice


# =============================================================================
# Tests for _create_payment_allocation
# =============================================================================


@pytest.mark.asyncio
async def test_create_payment_allocation_success_landlord(
    mock_session, mock_landlord_user, mock_invoice
):
    """Test successful payment allocation creation for landlord."""
    # Arrange
    payment_id = 1
    invoice_id = 1
    amount = Decimal("1000.00")
    reduction_amount = None

    # Mock invoice query result
    mock_session.scalar.return_value = mock_invoice

    # Act
    await _create_payment_allocation(
        payment_id=payment_id,
        invoice_id=invoice_id,
        amount=amount,
        reduction_amount=reduction_amount,
        session=mock_session,
        current_user=mock_landlord_user
    )

    # Assert
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

    # Verify PaymentAllocation was created with correct data
    added_allocation = mock_session.add.call_args[0][0]
    assert isinstance(added_allocation, PaymentAllocation)
    assert added_allocation.payment_id == payment_id
    assert added_allocation.invoice_id == invoice_id
    assert added_allocation.amount_applied == amount


@pytest.mark.asyncio
async def test_create_payment_allocation_with_reduction(
    mock_session, mock_landlord_user, mock_invoice
):
    """Test payment allocation with reduction amount."""
    # Arrange
    payment_id = 1
    invoice_id = 1
    amount = Decimal("1000.00")
    reduction_amount = Decimal("100.00")

    mock_session.scalar.return_value = mock_invoice

    # Act
    await _create_payment_allocation(
        payment_id=payment_id,
        invoice_id=invoice_id,
        amount=amount,
        reduction_amount=reduction_amount,
        session=mock_session,
        current_user=mock_landlord_user
    )

    # Assert
    added_allocation = mock_session.add.call_args[0][0]
    assert added_allocation.amount_applied == Decimal("900.00")  # 1000 - 100


@pytest.mark.asyncio
async def test_create_payment_allocation_admin_user(
    mock_session, mock_admin_user, mock_invoice
):
    """Test payment allocation for admin user (no ownership filter)."""
    # Arrange
    payment_id = 1
    invoice_id = 1
    amount = Decimal("1000.00")

    mock_session.scalar.return_value = mock_invoice

    # Act
    await _create_payment_allocation(
        payment_id=payment_id,
        invoice_id=invoice_id,
        amount=amount,
        reduction_amount=None,
        session=mock_session,
        current_user=mock_admin_user
    )

    # Assert
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_payment_allocation_tenant_blocked(
    mock_session, mock_tenant_user
):
    """Test that tenants are blocked from creating payment allocations."""
    # Arrange
    payment_id = 1
    invoice_id = 1
    amount = Decimal("1000.00")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await _create_payment_allocation(
            payment_id=payment_id,
            invoice_id=invoice_id,
            amount=amount,
            reduction_amount=None,
            session=mock_session,
            current_user=mock_tenant_user
        )

    assert exc_info.value.status_code == 403
    assert "Tenants cannot create payment allocations" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_payment_allocation_invoice_not_found(
    mock_session, mock_landlord_user
):
    """Test payment allocation when invoice doesn't exist."""
    # Arrange
    payment_id = 1
    invoice_id = 999
    amount = Decimal("1000.00")

    # Mock invoice not found
    mock_session.scalar.return_value = None

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await _create_payment_allocation(
            payment_id=payment_id,
            invoice_id=invoice_id,
            amount=amount,
            reduction_amount=None,
            session=mock_session,
            current_user=mock_landlord_user
        )

    assert exc_info.value.status_code == 404
    assert "not found or you don't have access to it" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_payment_allocation_invoice_not_owned(
    mock_session, mock_landlord_user
):
    """Test payment allocation when landlord doesn't own the invoice."""
    # Arrange
    payment_id = 1
    invoice_id = 1
    amount = Decimal("1000.00")

    # Mock invoice not found (due to ownership filter)
    mock_session.scalar.return_value = None

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await _create_payment_allocation(
            payment_id=payment_id,
            invoice_id=invoice_id,
            amount=amount,
            reduction_amount=None,
            session=mock_session,
            current_user=mock_landlord_user
        )

    assert exc_info.value.status_code == 404


# =============================================================================
# Tests for build_payment_response_from_orm
# =============================================================================


def test_build_payment_response_payment_without_id():
    """Test that function returns None when payment has no ID."""
    # Arrange
    payment = MagicMock(spec=Payment)
    payment.id = None

    # Act
    result = build_payment_response_from_orm(payment)

    # Assert
    assert result is None


def test_build_payment_response_with_lease_and_tenant():
    """Test payment response with lease and tenant."""
    # Arrange
    tenant = MagicMock(spec=Tenant)
    tenant.tenant_type.value = 'Individual'
    tenant.first_name = "John"
    tenant.last_name = "Doe"

    property_obj = MagicMock(spec=Property)
    property_obj.name = "Test Property"

    lease = MagicMock(spec=Lease)
    lease.tenant = tenant
    lease.property = property_obj

    payment = MagicMock(spec=Payment)
    payment.id = 1
    payment.lease_id = 1
    payment.tenant_id = 1
    payment.amount = Decimal("1000.00")
    payment.payment_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.payment_method = PaymentMethod.BANK_TRANSFER
    payment.status = PaymentStatus.PAID
    payment.transaction_reference = "TXN-001"
    payment.description = "Test payment"
    payment.receipt_url = None
    payment.reduction_amount = None
    payment.reduction_reason = None
    payment.quickbooks_id = None
    payment.stripe_payment_intent_id = None
    payment.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.lease = lease
    payment.tenant = tenant

    # Act
    result = build_payment_response_from_orm(payment)

    # Assert
    assert result is not None
    assert result.id == 1
    assert result.tenant_name == "John Doe"
    assert result.property_name == "Test Property"


def test_build_payment_response_with_tenant_no_lease():
    """Test payment response with tenant but no lease."""
    # Arrange
    tenant_type = MagicMock()
    tenant_type.value = 'Company'

    tenant = MagicMock(spec=Tenant)
    tenant.tenant_type = tenant_type
    tenant.company_name = "Acme Corp"
    # Avoid accessing first_name/last_name for company
    tenant.first_name = None
    tenant.last_name = None

    payment = MagicMock(spec=Payment)
    payment.id = 1
    payment.lease_id = None
    payment.tenant_id = 1
    payment.amount = Decimal("500.00")
    payment.payment_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.payment_method = PaymentMethod.CHECK
    payment.status = PaymentStatus.PENDING
    payment.transaction_reference = None
    payment.description = None
    payment.receipt_url = None
    payment.reduction_amount = None
    payment.reduction_reason = None
    payment.quickbooks_id = None
    payment.stripe_payment_intent_id = None
    payment.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.lease = None
    payment.tenant = tenant

    # Act
    result = build_payment_response_from_orm(payment)

    # Assert
    assert result is not None
    assert result.id == 1
    assert result.tenant_name == "Acme Corp"
    assert result.property_name == "No Property"


def test_build_payment_response_no_tenant():
    """Test payment response with no tenant."""
    # Arrange
    payment = MagicMock(spec=Payment)
    payment.id = 1
    payment.lease_id = None
    payment.tenant_id = None
    payment.amount = Decimal("250.00")
    payment.payment_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.payment_method = PaymentMethod.CASH
    payment.status = PaymentStatus.PAID
    payment.transaction_reference = None
    payment.description = "Miscellaneous payment"
    payment.receipt_url = None
    payment.reduction_amount = None
    payment.reduction_reason = None
    payment.quickbooks_id = None
    payment.stripe_payment_intent_id = None
    payment.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.lease = None
    payment.tenant = None

    # Act
    result = build_payment_response_from_orm(payment)

    # Assert
    assert result is not None
    assert result.id == 1
    assert result.tenant_name == "No Tenant"
    assert result.property_name == "No Property"


def test_build_payment_response_lease_without_property():
    """Test payment response with lease but no property."""
    # Arrange
    tenant = MagicMock(spec=Tenant)
    tenant.tenant_type.value = 'Individual'
    tenant.first_name = "Jane"
    tenant.last_name = "Smith"

    lease = MagicMock(spec=Lease)
    lease.tenant = tenant
    lease.property = None

    payment = MagicMock(spec=Payment)
    payment.id = 1
    payment.lease_id = 1
    payment.tenant_id = 1
    payment.amount = Decimal("1500.00")
    payment.payment_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.payment_method = PaymentMethod.CREDIT_CARD
    payment.status = PaymentStatus.PAID
    payment.transaction_reference = "CC-002"
    payment.description = "Rent payment"
    payment.receipt_url = None
    payment.reduction_amount = None
    payment.reduction_reason = None
    payment.quickbooks_id = None
    payment.stripe_payment_intent_id = None
    payment.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    payment.lease = lease
    payment.tenant = tenant

    # Act
    result = build_payment_response_from_orm(payment)

    # Assert
    assert result is not None
    assert result.id == 1
    assert result.tenant_name == "Jane Smith"
    assert result.property_name == "No Property"
