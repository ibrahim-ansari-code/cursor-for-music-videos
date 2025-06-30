import pytest
from datetime import date, datetime, timedelta, UTC
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.accounting.payments.service import get_payments
from Backend.api.accounting.payments.schemas import PaginatedPaymentsResponse
from Backend.models.accounting.common import PaymentStatus
from Backend.models.accounting.payment import Payment, PaymentMethod
from Backend.models.enums import UserType
from Backend.models.user import User
from Backend.models.lease import Lease
from Backend.models.property import Property
from Backend.models.tenant import Tenant


@pytest.mark.asyncio
async def test_get_payments_landlord_filters_and_pagination():
    """
    Tests that the get_payments function correctly applies landlord-specific filters and pagination.

    This test verifies that when a landlord user requests payments with specific filters and a pagination limit, 
    the response contains the expected number of payment items, the has_more flag is set appropriately, 
    and the returned payment data matches the expected results.
    """
    # Arrange
    landlord_user = MagicMock(spec=User)
    landlord_user.user_type = UserType.LANDLORD
    landlord_user.is_admin = False
    landlord_user.id = "landlord-uuid"

    # Create mock tenant and property
    mock_tenant = MagicMock(spec=Tenant)
    mock_tenant.id = 100
    mock_tenant.first_name = "John"
    mock_tenant.last_name = "Doe"

    mock_property = MagicMock(spec=Property)
    mock_property.id = 1
    mock_property.name = "Property A"
    mock_property.user_id = landlord_user.id

    # Create mock lease
    mock_lease = MagicMock(spec=Lease)
    mock_lease.id = 10
    mock_lease.tenant = mock_tenant
    mock_lease.property = mock_property

    # Create mock payments with proper relationships
    payment1 = MagicMock(spec=Payment)
    payment1.id = 1
    payment1.lease_id = 10
    payment1.tenant_id = 100
    payment1.amount = Decimal("1200.00")
    payment1.payment_date = datetime.now(UTC) - timedelta(days=2)
    payment1.payment_method = PaymentMethod.BANK_TRANSFER
    payment1.status = PaymentStatus.PAID
    payment1.transaction_reference = "TXN123"
    payment1.description = "Rent for June"
    payment1.receipt_url = "http://example.com/receipt1"
    payment1.created_at = datetime.now(UTC) - timedelta(days=3)
    payment1.updated_at = datetime.now(UTC) - timedelta(days=2)
    payment1.lease = mock_lease

    payment2 = MagicMock(spec=Payment)
    payment2.id = 2
    payment2.lease_id = 11
    payment2.tenant_id = 101
    payment2.amount = Decimal("1300.00")
    payment2.payment_date = datetime.now(UTC) - timedelta(days=1)
    payment2.payment_method = PaymentMethod.CASH
    payment2.status = PaymentStatus.PAID
    payment2.transaction_reference = "TXN124"
    payment2.description = "Rent for July"
    payment2.receipt_url = "http://example.com/receipt2"
    payment2.created_at = datetime.now(UTC) - timedelta(days=2)
    payment2.updated_at = datetime.now(UTC) - timedelta(days=1)
    # For payment2, create separate lease/property to simulate different data
    mock_lease2 = MagicMock(spec=Lease)
    mock_lease2.id = 11
    mock_lease2.tenant = mock_tenant
    mock_property2 = MagicMock(spec=Property)
    mock_property2.id = 2
    mock_property2.name = "Property B"
    mock_property2.user_id = landlord_user.id
    mock_lease2.property = mock_property2
    payment2.lease = mock_lease2

    # For payment2, create separate tenant to simulate different data
    mock_tenant2 = MagicMock(spec=Tenant)
    mock_tenant2.id = 101
    mock_tenant2.first_name = "Jane"
    mock_tenant2.last_name = "Smith"
    mock_lease2.tenant = mock_tenant2

    # Mock session and result objects
    mock_session = MagicMock(spec=AsyncSession)

    # Mock the session.execute result chain
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalars.return_value = mock_execute_result
    # Return 2 payments to test pagination (limit=1, so has_more should be True)
    mock_execute_result.all.return_value = [payment1, payment2]

    mock_session.execute = AsyncMock(return_value=mock_execute_result)

    # Act
    result = await get_payments(
        lease_id=None,
        property_id=1,
        tenant_id=None,
        payment_status=PaymentStatus.PAID,
        start_date=date.today() - timedelta(days=10),
        end_date=date.today(),
        limit=1,
        offset=0,
        session=mock_session,
        current_user=landlord_user,
    )

    # Assert
    assert isinstance(result, PaginatedPaymentsResponse)
    assert len(result.items) == 1  # Limited to 1 item
    # Should be True since we returned 2 items but limit is 1
    assert result.has_more is True

    # Check that the returned payment matches the first payment
    returned_payment = result.items[0]
    assert returned_payment.id == payment1.id
    assert returned_payment.amount == payment1.amount
    assert returned_payment.status == PaymentStatus.PAID
    assert returned_payment.property_name == "Property A"
    assert returned_payment.tenant_name == "John Doe"

    # Verify that session.execute was called (the database was queried)
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_payments_no_matching_filters():
    """
    Tests that get_payments returns an empty paginated response when no payments match the provided filters for a landlord user.
    """
    # Arrange
    landlord_user = MagicMock(spec=User)
    landlord_user.user_type = UserType.LANDLORD
    landlord_user.is_admin = False
    landlord_user.id = "landlord-uuid"

    # Mock session
    mock_session = MagicMock(spec=AsyncSession)

    # Mock the session.execute result chain to return empty results
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalars.return_value = mock_execute_result
    mock_execute_result.all.return_value = []  # No payments found

    mock_session.execute = AsyncMock(return_value=mock_execute_result)

    # Act
    result = await get_payments(
        lease_id=9999,  # Non-existent lease_id
        property_id=8888,  # Non-existent property_id
        tenant_id=7777,  # Non-existent tenant_id
        payment_status=PaymentStatus.PAID,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today(),
        limit=10,
        offset=0,
        session=mock_session,
        current_user=landlord_user,
    )

    # Assert
    assert isinstance(result, PaginatedPaymentsResponse)
    assert result.items == []
    assert result.has_more is False

    # Verify that session.execute was called
    mock_session.execute.assert_called_once()
