import pytest
from datetime import date, datetime, timedelta, UTC
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.accounting.payments import get_payments, PaginatedPaymentsResponse
from Backend.models.accounting.common import PaymentStatus
from Backend.models.accounting.payment import Payment, PaymentMethod
from Backend.models.enums import UserType
from Backend.models.user import User

@pytest.mark.asyncio
async def test_get_payments_landlord_filters_and_pagination(
    mocker,
):
    # Arrange
    # Mock landlord user
    """
    Tests that the get_payments function correctly applies landlord-specific filters and pagination.
    
    This test verifies that when a landlord user requests payments with specific filters and a pagination limit, the response contains the expected number of payment items, the has_more flag is set appropriately, and the returned payment data matches the mocked ORM objects.
    """
    landlord_user = MagicMock(spec=User)
    landlord_user.user_type = UserType.LANDLORD
    landlord_user.is_admin = False
    landlord_user.id = "landlord-uuid"

    # Mock session
    mock_session = MagicMock(spec=AsyncSession)

    # Mock payments ORM results
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
    # lease and property/tenant relationships for response
    payment1.lease = MagicMock()
    payment1.lease.tenant = MagicMock()
    payment1.lease.property = MagicMock()
    payment1.lease.property.name = "Property A"

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
    payment2.lease = MagicMock()
    payment2.lease.tenant = MagicMock()
    payment2.lease.property = MagicMock()
    payment2.lease.property.name = "Property B"

    # Simulate more than limit payments to test pagination
    payments_orm = [payment1, payment2]

    # Patch get_current_user and get_session dependencies
    mocker.patch("Backend.api.accounting.payments.get_current_user", return_value=landlord_user)
    mocker.patch("Backend.api.accounting.payments.get_session", return_value=mock_session)

    # Patch _build_payment_base_query and _apply_common_payment_filters to return a dummy query object
    dummy_query = MagicMock()
    mocker.patch("Backend.api.accounting.payments._build_payment_base_query", return_value=dummy_query)
    mocker.patch("Backend.api.accounting.payments._apply_common_payment_filters", return_value=dummy_query)
    # Patch _apply_landlord_payment_filters to return the dummy query
    mocker.patch("Backend.api.accounting.payments._apply_landlord_payment_filters", return_value=dummy_query)
    # Patch _build_payment_response_from_orm to return a simple dict for each payment
    def fake_build_payment_response_from_orm(payment_orm):
        """
        Converts a payment ORM object into a dictionary with payment and related tenant/property details.
        
        Args:
            payment_orm: The ORM object representing a payment.
        
        Returns:
            A dictionary containing payment attributes and related tenant and property names.
        """
        return {
            "id": payment_orm.id,
            "lease_id": payment_orm.lease_id,
            "tenant_id": payment_orm.tenant_id,
            "amount": payment_orm.amount,
            "payment_date": payment_orm.payment_date,
            "payment_method": payment_orm.payment_method,
            "status": payment_orm.status,
            "transaction_reference": payment_orm.transaction_reference,
            "description": payment_orm.description,
            "receipt_url": payment_orm.receipt_url,
            "created_at": payment_orm.created_at,
            "updated_at": payment_orm.updated_at,
            "tenant_name": "Tenant Name",
            "property_name": payment_orm.lease.property.name if payment_orm.lease and payment_orm.lease.property else "Unknown Property"
        }
    mocker.patch("Backend.api.accounting.payments._build_payment_response_from_orm", side_effect=fake_build_payment_response_from_orm)

    # Patch session.execute to return an object with .unique().scalars().all()
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalars.return_value = mock_execute_result
    # Simulate limit=1, so payments_orm has 2 items (to test has_more)
    mock_execute_result.all.return_value = payments_orm
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
    assert len(result.items) == 1
    assert result.has_more is True
    # Check that the returned payment matches the first payment
    returned_payment = result.items[0]
    assert returned_payment.id == payment1.id
    assert returned_payment.property_name == "Property A"
    assert returned_payment.status == PaymentStatus.PAID


@pytest.mark.asyncio
async def test_get_payments_no_matching_filters(mocker):
    # Arrange
    # Mock an authorized landlord user
    """
    Tests that get_payments returns an empty paginated response when no payments match the provided filters for a landlord user.
    """
    landlord_user = MagicMock(spec=User)
    landlord_user.user_type = UserType.LANDLORD
    landlord_user.is_admin = False
    landlord_user.id = "landlord-uuid"

    # Mock session
    mock_session = MagicMock(spec=AsyncSession)

    # Patch get_current_user and get_session dependencies
    mocker.patch("Backend.api.accounting.payments.get_current_user", return_value=landlord_user)
    mocker.patch("Backend.api.accounting.payments.get_session", return_value=mock_session)

    # Patch _build_payment_base_query and _apply_common_payment_filters to return a dummy query object
    dummy_query = MagicMock()
    mocker.patch("Backend.api.accounting.payments._build_payment_base_query", return_value=dummy_query)
    mocker.patch("Backend.api.accounting.payments._apply_common_payment_filters", return_value=dummy_query)
    # Patch _apply_landlord_payment_filters to return the dummy query
    mocker.patch("Backend.api.accounting.payments._apply_landlord_payment_filters", return_value=dummy_query)
    # Patch _build_payment_response_from_orm to return None (no ORM objects to convert)
    mocker.patch("Backend.api.accounting.payments._build_payment_response_from_orm", side_effect=lambda x: None)

    # Patch session.execute to return an object with .unique().scalars().all() returning empty list
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalars.return_value = mock_execute_result
    mock_execute_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_execute_result)

    # Act
    result = await get_payments(
        lease_id=9999,  # Assume this lease_id does not exist
        property_id=8888,  # Assume this property_id does not exist
        tenant_id=7777,  # Assume this tenant_id does not exist
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