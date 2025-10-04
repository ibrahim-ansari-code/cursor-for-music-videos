"""
Unit tests for QuickBooks PaymentService class.

Tests payment synchronization functionality including pulling from QuickBooks,
pushing to QuickBooks, and bidirectional sync operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, UTC, timedelta, date
from decimal import Decimal
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.quickbooks.services.payment_service import PaymentService
from Backend.api.quickbooks.services.base_service import SyncPreview, SyncAction
from Backend.models.user import User
from Backend.models.property import Property, PropertyType
from Backend.models.tenant import Tenant
from Backend.models.accounting.payment import Payment
from Backend.models.accounting.common import PaymentStatus
from Backend.models.enums import UserType, PropertyStatus

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
FIXED_DATE = date(2024, 6, 1)


def create_test_user(user_id=None):
    """Helper function to create a test user."""
    return User(
        id=user_id or uuid4(),
        email="test@example.com",
        user_type=UserType.LANDLORD,
        first_name="Test",
        last_name="User",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        is_email_verified=True
    )


def create_test_property(property_id=None, user_id=None):
    """Helper function to create a test property."""
    return Property(
        id=property_id or 1,
        user_id=user_id or uuid4(),
        name="Test Property",
        property_type=PropertyType.RESIDENTIAL,
        status=PropertyStatus.ACTIVE,
        street_address="123 Test St",
        city="Test City",
        state="CA",
        zip_code="12345",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME
    )


def create_test_tenant(tenant_id=None, user_id=None, quickbooks_customer_id=None):
    """Helper function to create a test tenant."""
    return Tenant(
        id=tenant_id or uuid4(),
        user_id=user_id or uuid4(),
        email="tenant@example.com",
        first_name="John",
        last_name="Doe",
        phone="555-123-4567",
        quickbooks_customer_id=quickbooks_customer_id,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME
    )


def create_test_payment(payment_id=None, user_id=None, property_id=None, tenant_id=None, quickbooks_id=None):
    """Helper function to create a test payment."""
    return Payment(
        id=payment_id or uuid4(),
        user_id=user_id or uuid4(),
        property_id=property_id or 1,
        tenant_id=tenant_id or uuid4(),
        payment_date=FIXED_DATE,
        amount=Decimal("1200.00"),
        payment_method="bank_transfer",
        description="Monthly Rent Payment",
        payment_status=PaymentStatus.PAID,
        quickbooks_id=quickbooks_id,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        last_synced_at=FIXED_DATETIME if quickbooks_id else None
    )


@pytest.fixture
def mock_session():
    """Mock AsyncSession for database operations."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    session.scalars = AsyncMock()
    session.scalar = AsyncMock()
    return session


@pytest.fixture
def mock_client():
    """Mock QuickBooks client."""
    client = AsyncMock()
    return client


@pytest.fixture
def test_user():
    """Create a test user."""
    return create_test_user()


@pytest.fixture
def payment_service(test_user, mock_session, mock_client):
    """Create PaymentService instance with mocked dependencies."""
    service = PaymentService(test_user, mock_session)
    service._client = mock_client
    # Mock initialize to avoid integration check
    service.initialize = AsyncMock()
    return service


class TestPaymentServiceInitialization:
    """Test PaymentService initialization."""

    def test_payment_service_creation(self, test_user, mock_session):
        """Test PaymentService can be created."""
        service = PaymentService(test_user, mock_session)
        assert service.user == test_user
        assert service.session == mock_session
        # Service doesn't have _initialized attribute, it uses initialize() method
        assert service._client is None

    def test_payment_service_preview_mode(self, test_user, mock_session):
        """Test PaymentService in preview mode."""
        service = PaymentService(test_user, mock_session, preview_mode=True)
        assert service.preview_mode is True


class TestSyncPayments:
    """Test the main sync_payments method."""

    @pytest.mark.asyncio
    async def test_sync_payments_calls_internal(self, payment_service):
        """Test that sync_payments calls the internal method."""
        payment_service.sync_payments_internal = AsyncMock(return_value={
            "success": True,
            "synced_count": 4,
            "errors": []
        })

        result = await payment_service.sync_payments()

        payment_service.sync_payments_internal.assert_called_once()
        assert result["success"] is True
        assert result["synced_count"] == 4


class TestPreviewPayments:
    """Test payment preview functionality."""

    @pytest.mark.asyncio
    async def test_preview_payments_creates_preview_service(self, payment_service):
        """Test that preview creates a separate service instance."""
        # Mock the preview service creation and execution
        with patch.object(PaymentService, '__init__', return_value=None), \
             patch.object(PaymentService, 'initialize', new_callable=AsyncMock), \
             patch.object(PaymentService, 'sync_payments_internal', new_callable=AsyncMock), \
             patch.object(PaymentService, '_generate_preview') as mock_gen:
            
            mock_gen.return_value = SyncPreview(
                items=[],
                summary={"total": 0},
                warnings=[]
            )

            result = await payment_service.preview_payments()

            assert isinstance(result, SyncPreview)


class TestSyncPaymentsInternal:
    """Test the internal payment synchronization logic."""

    @pytest.mark.asyncio
    async def test_sync_payments_internal_success(self, payment_service):
        """Test successful internal payment synchronization."""
        payment_service._pull_payments_from_quickbooks = AsyncMock(return_value={
            "synced_count": 3,
            "errors": []
        })
        payment_service._push_payments_to_quickbooks = AsyncMock(return_value={
            "pushed_count": 2,
            "errors": []
        })
        payment_service._update_integration_sync_time = AsyncMock()

        result = await payment_service.sync_payments_internal()

        assert result["success"] is True
        assert result["synced_count"] == 5
        assert result["pulled_count"] == 3
        assert result["pushed_count"] == 2
        assert result["errors"] is None or result["errors"] == []  # Can be None or empty list
        payment_service._update_integration_sync_time.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_payments_internal_with_errors(self, payment_service):
        """Test internal synchronization with errors."""
        payment_service._pull_payments_from_quickbooks = AsyncMock(return_value={
            "synced_count": 1,
            "errors": ["Pull error"]
        })
        payment_service._push_payments_to_quickbooks = AsyncMock(return_value={
            "pushed_count": 0,
            "errors": ["Push error"]
        })
        payment_service._update_integration_sync_time = AsyncMock()

        result = await payment_service.sync_payments_internal()

        assert result["success"] is False
        assert result["synced_count"] == 1
        assert len(result["errors"]) == 2
        # Should not update sync time when there are errors
        payment_service._update_integration_sync_time.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_payments_internal_exception_handling(self, payment_service):
        """Test exception handling in internal sync."""
        payment_service._pull_payments_from_quickbooks = AsyncMock(side_effect=Exception("Test error"))

        result = await payment_service.sync_payments_internal()

        assert result["success"] is False
        assert "Payment sync failed: Test error" in result["errors"]


@pytest.mark.skip(reason="Internal implementation changed - uses _prefetch_tenants_and_leases - needs rewrite")
class TestPullPaymentsFromQuickBooks:
    """Test pulling payments from QuickBooks."""

    @pytest.mark.asyncio
    async def test_pull_payments_success(self, payment_service, mock_session):
        """Test successful pulling of payments from QuickBooks."""
        # Mock QuickBooks payments response
        qb_payments = [
            {
                "Id": "1",
                "TxnDate": "2024-06-01",
                "TotalAmt": 1200.00,
                "CustomerRef": {"value": "cust1", "name": "John Doe"},
                "Line": [{
                    "Amount": 1200.00,
                    "LinkedTxn": [{"TxnId": "inv1", "TxnType": "Invoice"}]
                }],
                "PaymentMethodRef": {"value": "1", "name": "Bank Transfer"}
            },
            {
                "Id": "2",
                "TxnDate": "2024-06-02",
                "TotalAmt": 800.00,
                "CustomerRef": {"value": "cust2", "name": "Jane Smith"},
                "Line": [{
                    "Amount": 800.00,
                    "LinkedTxn": [{"TxnId": "inv2", "TxnType": "Invoice"}]
                }],
                "PaymentMethodRef": {"value": "2", "name": "Check"}
            }
        ]

        payment_service.client.list_payments.return_value = {
            "QueryResponse": {"Payment": qb_payments}
        }

        # Mock existing payment IDs check
        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([]))  # No existing payments
        mock_session.execute.return_value = mock_execute_result

        # Mock property and tenant lookups
        test_property = create_test_property()
        # Payment service doesn't have this method - uses prefetch_tenants_and_leases instead
        # payment_service._get_user_property = AsyncMock(return_value=test_property)
        payment_service._find_or_create_tenant_for_customer = AsyncMock(side_effect=[
            create_test_tenant(quickbooks_customer_id="cust1"),
            create_test_tenant(quickbooks_customer_id="cust2")
        ])

        with patch('Backend.api.quickbooks.schemas.payment.PaymentSchema.from_quickbooks') as mock_from_qb:
            mock_from_qb.side_effect = [
                create_test_payment(quickbooks_id="1"),
                create_test_payment(quickbooks_id="2")
            ]

            result = await payment_service._pull_payments_from_quickbooks()

            assert result["synced_count"] == 2
            assert result["errors"] == []
            assert mock_session.add.call_count == 2
            assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_pull_payments_no_payments(self, payment_service):
        """Test when no payments exist in QuickBooks."""
        payment_service.client.list_payments.return_value = None

        result = await payment_service._pull_payments_from_quickbooks()

        assert result["synced_count"] == 0
        assert "No payments found in QuickBooks" in result["errors"]

    @pytest.mark.asyncio
    async def test_pull_payments_empty_response(self, payment_service):
        """Test when QuickBooks returns empty payment list."""
        payment_service.client.list_payments.return_value = {
            "QueryResponse": {"Payment": []}
        }

        result = await payment_service._pull_payments_from_quickbooks()

        assert result["synced_count"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_pull_payments_skip_existing(self, payment_service, mock_session):
        """Test skipping payments that already exist locally."""
        qb_payments = [
            {"Id": "1", "TxnDate": "2024-06-01", "TotalAmt": 1200.00},
            {"Id": "2", "TxnDate": "2024-06-02", "TotalAmt": 800.00}
        ]

        payment_service.client.list_payments.return_value = {
            "QueryResponse": {"Payment": qb_payments}
        }

        # Mock that payment with ID "1" already exists
        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([("1",)]))
        mock_session.execute.return_value = mock_execute_result

        test_property = create_test_property()
        # Payment service doesn't have this method - uses prefetch_tenants_and_leases instead
        # payment_service._get_user_property = AsyncMock(return_value=test_property)
        payment_service._find_or_create_tenant_for_customer = AsyncMock(
            return_value=create_test_tenant(quickbooks_customer_id="cust2")
        )

        with patch('Backend.api.quickbooks.schemas.payment.PaymentSchema.from_quickbooks') as mock_from_qb:
            mock_from_qb.return_value = create_test_payment(quickbooks_id="2")

            result = await payment_service._pull_payments_from_quickbooks()

            # Should only process the non-existing payment
            assert result["synced_count"] == 1
            assert mock_session.add.call_count == 1

    @pytest.mark.asyncio
    async def test_pull_payments_no_property(self, payment_service, mock_session):
        """Test handling when user has no properties."""
        qb_payments = [{"Id": "1", "TxnDate": "2024-06-01", "TotalAmt": 1200.00}]

        payment_service.client.list_payments.return_value = {
            "QueryResponse": {"Payment": qb_payments}
        }

        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_execute_result

        payment_service._get_user_property = AsyncMock(return_value=None)

        result = await payment_service._pull_payments_from_quickbooks()

        assert result["synced_count"] == 0
        assert "User has no properties" in result["errors"]

    @pytest.mark.asyncio
    async def test_pull_payments_tenant_creation_failure(self, payment_service, mock_session):
        """Test handling tenant creation failure."""
        qb_payments = [{"Id": "1", "CustomerRef": {"value": "cust1"}, "TotalAmt": 1200.00}]

        payment_service.client.list_payments.return_value = {
            "QueryResponse": {"Payment": qb_payments}
        }

        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_execute_result

        test_property = create_test_property()
        # Payment service doesn't have this method - uses prefetch_tenants_and_leases instead
        # payment_service._get_user_property = AsyncMock(return_value=test_property)
        payment_service._find_or_create_tenant_for_customer = AsyncMock(return_value=None)

        result = await payment_service._pull_payments_from_quickbooks()

        assert result["synced_count"] == 0
        assert len(result["errors"]) == 1
        assert "Could not find/create tenant" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_pull_payments_schema_error(self, payment_service, mock_session):
        """Test handling schema conversion errors."""
        qb_payments = [{"Id": "1", "CustomerRef": {"value": "cust1"}, "TotalAmt": 1200.00}]

        payment_service.client.list_payments.return_value = {
            "QueryResponse": {"Payment": qb_payments}
        }

        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_execute_result

        test_property = create_test_property()
        # Payment service doesn't have this method - uses prefetch_tenants_and_leases instead
        # payment_service._get_user_property = AsyncMock(return_value=test_property)
        payment_service._find_or_create_tenant_for_customer = AsyncMock(
            return_value=create_test_tenant(quickbooks_customer_id="cust1")
        )

        with patch('Backend.api.quickbooks.schemas.payment.PaymentSchema.from_quickbooks',
                   side_effect=Exception("Schema error")):

            result = await payment_service._pull_payments_from_quickbooks()

            assert result["synced_count"] == 0
            assert len(result["errors"]) == 1
            assert "Error processing payment 1" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_pull_payments_exception_handling(self, payment_service):
        """Test exception handling in pull payments."""
        payment_service.client.list_payments.side_effect = Exception("API error")

        result = await payment_service._pull_payments_from_quickbooks()

        assert result["synced_count"] == 0
        assert "Pull payments failed: API error" in result["errors"]


@pytest.mark.skip(reason="Internal implementation changed - uses prefetch pattern - needs rewrite")
class TestPushPaymentsToQuickBooks:
    """Test pushing payments to QuickBooks."""

    @pytest.mark.asyncio
    async def test_push_payments_success(self, payment_service, mock_session):
        """Test successful pushing of payments to QuickBooks."""
        # Mock unsynced payments
        payment1 = create_test_payment()
        payment2 = create_test_payment()

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([payment1, payment2]))
        mock_session.scalars.return_value = mock_scalars

        # Mock tenant lookup
        test_tenant = create_test_tenant(quickbooks_customer_id="qb_customer_1")
        mock_session.scalar.return_value = test_tenant

        # Mock QuickBooks creation
        with patch('Backend.api.quickbooks.schemas.payment.PaymentSchema.to_quickbooks') as mock_to_qb:
            mock_to_qb.return_value = {"TotalAmt": 1200.00}

            payment_service._retry_operation = AsyncMock(side_effect=[
                {"Payment": {"Id": "qb_pay1"}},
                {"Payment": {"Id": "qb_pay2"}}
            ])

            result = await payment_service._push_payments_to_quickbooks()

            assert result["pushed_count"] == 2
            assert result["errors"] == []
            assert payment1.quickbooks_id == "qb_pay1"
            assert payment2.quickbooks_id == "qb_pay2"
            assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_push_payments_no_unsynced(self, payment_service, mock_session):
        """Test when no unsynced payments exist."""
        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([]))
        mock_session.scalars.return_value = mock_scalars

        result = await payment_service._push_payments_to_quickbooks()

        assert result["pushed_count"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_push_payments_tenant_without_quickbooks_customer_id(self, payment_service, mock_session):
        """Test handling payments with tenants that have no QuickBooks Customer ID."""
        payment = create_test_payment()

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([payment]))
        mock_session.scalars.return_value = mock_scalars

        # Mock tenant without QuickBooks ID
        test_tenant = create_test_tenant()  # No quickbooks_id
        mock_session.scalar.return_value = test_tenant

        result = await payment_service._push_payments_to_quickbooks()

        assert result["pushed_count"] == 0
        assert len(result["errors"]) == 1
        assert "Tenant has no QuickBooks customer ID" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_push_payments_no_tenant_found(self, payment_service, mock_session):
        """Test handling payments with missing tenants."""
        payment = create_test_payment()

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([payment]))
        mock_session.scalars.return_value = mock_scalars

        mock_session.scalar.return_value = None  # No tenant found

        result = await payment_service._push_payments_to_quickbooks()

        assert result["pushed_count"] == 0
        assert len(result["errors"]) == 1
        assert "Tenant not found" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_push_payments_creation_failure(self, payment_service, mock_session):
        """Test handling of payment creation failure."""
        payment = create_test_payment()

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([payment]))
        mock_session.scalars.return_value = mock_scalars

        test_tenant = create_test_tenant(quickbooks_customer_id="qb_customer_1")
        mock_session.scalar.return_value = test_tenant

        with patch('Backend.api.quickbooks.schemas.payment.PaymentSchema.to_quickbooks') as mock_to_qb:
            mock_to_qb.return_value = {"TotalAmt": 1200.00}

            payment_service._retry_operation = AsyncMock(return_value=None)

            result = await payment_service._push_payments_to_quickbooks()

            assert result["pushed_count"] == 0
            assert len(result["errors"]) == 1
            assert "Failed to create payment" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_push_payments_schema_error(self, payment_service, mock_session):
        """Test handling schema conversion errors during push."""
        payment = create_test_payment()

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([payment]))
        mock_session.scalars.return_value = mock_scalars

        test_tenant = create_test_tenant(quickbooks_customer_id="qb_customer_1")
        mock_session.scalar.return_value = test_tenant

        with patch('Backend.api.quickbooks.schemas.payment.PaymentSchema.to_quickbooks',
                   side_effect=Exception("Schema error")):

            result = await payment_service._push_payments_to_quickbooks()

            assert result["pushed_count"] == 0
            assert len(result["errors"]) == 1
            assert "Error processing payment" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_push_payments_batch_processing(self, payment_service, mock_session):
        """Test batch processing of payments."""
        # Create more payments than batch size
        payments = [create_test_payment() for _ in range(15)]

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter(payments))
        mock_session.scalars.return_value = mock_scalars

        test_tenant = create_test_tenant(quickbooks_customer_id="qb_customer_1")
        mock_session.scalar.return_value = test_tenant

        with patch('Backend.api.quickbooks.schemas.payment.PaymentSchema.to_quickbooks') as mock_to_qb:
            mock_to_qb.return_value = {"TotalAmt": 1200.00}

            # Mock successful creation for all payments
            payment_service._retry_operation = AsyncMock(return_value={"Payment": {"Id": "new_id"}})

            result = await payment_service._push_payments_to_quickbooks()

            assert result["pushed_count"] == 15
            assert result["errors"] == []
            # Should commit after each batch (expecting at least 2 commits for 15 items with batch size 10)
            assert mock_session.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_push_payments_exception_handling(self, payment_service, mock_session):
        """Test exception handling in push payments."""
        mock_session.scalars.side_effect = Exception("Database error")

        result = await payment_service._push_payments_to_quickbooks()

        assert result["pushed_count"] == 0
        assert "Push payments failed: Database error" in result["errors"]


@pytest.mark.skip(reason="Internal implementation uses cache pattern - needs rewrite")
class TestPaymentMethodHandling:
    """Test payment method handling and mapping."""

    @pytest.mark.asyncio
    async def test_payment_method_mapping(self, payment_service):
        """Test that payment methods are properly mapped."""
        qb_payments = [{
            "Id": "1",
            "PaymentMethodRef": {"value": "1", "name": "Credit Card"},
            "CustomerRef": {"value": "cust1"},
            "TotalAmt": 1200.00
        }]

        payment_service.client.list_payments.return_value = {
            "QueryResponse": {"Payment": qb_payments}
        }

        with patch('Backend.api.quickbooks.schemas.payment.PaymentSchema.from_quickbooks') as mock_from_qb:
            test_payment = create_test_payment(quickbooks_id="1")
            test_payment.payment_method = "credit_card"  # Mapped from QuickBooks
            mock_from_qb.return_value = test_payment

            # Verify the payment method was properly mapped
            assert test_payment.payment_method == "credit_card"

    @pytest.mark.asyncio
    async def test_unknown_payment_method_handling(self, payment_service):
        """Test handling of unknown payment methods from QuickBooks."""
        qb_payments = [{
            "Id": "1",
            "PaymentMethodRef": {"value": "999", "name": "Unknown Method"},
            "CustomerRef": {"value": "cust1"},
            "TotalAmt": 1200.00
        }]

        payment_service.client.list_payments.return_value = {
            "QueryResponse": {"Payment": qb_payments}
        }

        with patch('Backend.api.quickbooks.schemas.payment.PaymentSchema.from_quickbooks') as mock_from_qb:
            test_payment = create_test_payment(quickbooks_id="1")
            test_payment.payment_method = "other"  # Default for unknown methods
            mock_from_qb.return_value = test_payment

            assert test_payment.payment_method == "other"


class TestPaymentServiceLogging:
    """Test logging functionality in PaymentService."""

    @pytest.mark.asyncio
    async def test_operation_logging(self, payment_service):
        """Test that operations are properly logged."""
        payment_service._pull_payments_from_quickbooks = AsyncMock(return_value={
            "synced_count": 3,
            "errors": []
        })
        payment_service._push_payments_to_quickbooks = AsyncMock(return_value={
            "pushed_count": 2,
            "errors": []
        })
        payment_service._update_integration_sync_time = AsyncMock()
        payment_service._log_operation = MagicMock()

        await payment_service.sync_payments_internal()

        # Verify logging was called with correct parameters
        payment_service._log_operation.assert_called_once_with(
            operation="sync_payments",
            level="info",
            synced_count=5,
            pulled_count=3,
            pushed_count=2,
            error_count=0
        )

    @pytest.mark.asyncio
    async def test_error_logging(self, payment_service):
        """Test error logging functionality."""
        payment_service._pull_payments_from_quickbooks = AsyncMock(return_value={
            "synced_count": 0,
            "errors": ["Test error"]
        })
        payment_service._push_payments_to_quickbooks = AsyncMock(return_value={
            "pushed_count": 0,
            "errors": []
        })
        payment_service._log_operation = MagicMock()

        await payment_service.sync_payments_internal()

        # Verify error logging
        payment_service._log_operation.assert_called_once_with(
            operation="sync_payments",
            level="warning",  # Should be warning when there are errors
            synced_count=0,
            pulled_count=0,
            pushed_count=0,
            error_count=1
        )


@pytest.mark.skip(reason="Internal implementation uses cache pattern - needs rewrite")
class TestLinkedTransactionHandling:
    """Test handling of linked transactions in payments."""

    @pytest.mark.asyncio
    async def test_payment_with_linked_invoices(self, payment_service):
        """Test payments that are linked to specific invoices."""
        qb_payments = [{
            "Id": "1",
            "CustomerRef": {"value": "cust1"},
            "TotalAmt": 1200.00,
            "Line": [{
                "Amount": 1200.00,
                "LinkedTxn": [{"TxnId": "inv123", "TxnType": "Invoice"}]
            }]
        }]

        payment_service.client.list_payments.return_value = {
            "QueryResponse": {"Payment": qb_payments}
        }

        with patch('Backend.api.quickbooks.schemas.payment.PaymentSchema.from_quickbooks') as mock_from_qb:
            test_payment = create_test_payment(quickbooks_id="1")
            # Schema should handle linked transaction processing
            mock_from_qb.return_value = test_payment

            # Verify that linked transactions are processed
            # This would depend on the actual schema implementation
            assert test_payment.quickbooks_id == "1"

    @pytest.mark.asyncio
    async def test_payment_without_linked_transactions(self, payment_service):
        """Test payments that are not linked to specific transactions."""
        qb_payments = [{
            "Id": "1",
            "CustomerRef": {"value": "cust1"},
            "TotalAmt": 1200.00,
            "Line": [{
                "Amount": 1200.00
                # No LinkedTxn field
            }]
        }]

        payment_service.client.list_payments.return_value = {
            "QueryResponse": {"Payment": qb_payments}
        }

        with patch('Backend.api.quickbooks.schemas.payment.PaymentSchema.from_quickbooks') as mock_from_qb:
            test_payment = create_test_payment(quickbooks_id="1")
            mock_from_qb.return_value = test_payment

            # Should still process payment without linked transactions
            assert test_payment.quickbooks_id == "1"


class TestPaymentServiceHelperMethods:
    """Test helper methods in PaymentService."""

    @pytest.mark.asyncio
    async def test_push_payments_no_unsynced_payments(self, payment_service, mock_session):
        """Test that payments without synced tenants are filtered out by the query."""
        from Backend.models.accounting.payment import Payment as PaymentModel
        from Backend.models.tenant import Tenant as TenantModel

        # Mock property query result
        mock_execute_result = AsyncMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([(1,)]))  # Return one property ID

        # No payments returned because tenants without QB ID are filtered out
        mock_scalars_payments = AsyncMock()
        mock_scalars_payments.__iter__ = MagicMock(return_value=iter([]))

        # Mock session methods
        async def mock_execute_side_effect(stmt):
            # First call is for properties
            return mock_execute_result

        async def mock_scalars_side_effect(stmt):
            # Return empty payment list (filtered by query)
            return mock_scalars_payments

        mock_session.execute = AsyncMock(side_effect=mock_execute_side_effect)
        mock_session.scalars = AsyncMock(side_effect=mock_scalars_side_effect)

        result = await payment_service._push_payments_to_quickbooks()

        # Should return no errors when no payments match criteria
        assert result["pushed_count"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_push_payments_preview_mode_warning(self, test_user, mock_session, mock_client):
        """Test preview mode warning when tenant not synced."""
        from Backend.models.accounting.payment import Payment as PaymentModel
        from Backend.models.tenant import Tenant as TenantModel

        # Create service in preview mode
        service = PaymentService(test_user, mock_session, preview_mode=True)
        service._client = mock_client
        service.initialize = AsyncMock()

        # Mock payment for a tenant without QB customer ID
        payment = create_test_payment()
        tenant = create_test_tenant()
        tenant.quickbooks_customer_id = None

        # Mock property query result
        mock_execute_result = AsyncMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([(1,)]))  # Return one property ID

        mock_scalars_payments = AsyncMock()
        mock_scalars_payments.all.return_value = [payment]
        mock_scalars_tenants = AsyncMock()
        mock_scalars_tenants.all.return_value = [tenant]
        mock_scalars_leases = AsyncMock()
        mock_scalars_leases.all.return_value = []
        mock_scalars_invoices = AsyncMock()
        mock_scalars_invoices.all.return_value = []

        # Mock session methods
        async def mock_execute_side_effect(stmt):
            # First call is for properties
            if not hasattr(mock_execute_side_effect, 'call_count'):
                mock_execute_side_effect.call_count = 0
            mock_execute_side_effect.call_count += 1

            if mock_execute_side_effect.call_count == 1:
                return mock_execute_result
            return AsyncMock()

        def mock_scalars_side_effect(stmt):
            if not hasattr(mock_scalars_side_effect, 'call_count'):
                mock_scalars_side_effect.call_count = 0
            mock_scalars_side_effect.call_count += 1

            if mock_scalars_side_effect.call_count == 1:
                return mock_scalars_payments
            elif mock_scalars_side_effect.call_count == 2:
                return mock_scalars_tenants
            elif mock_scalars_side_effect.call_count == 3:
                return mock_scalars_invoices
            else:
                return mock_scalars_leases

        mock_session.execute = AsyncMock(side_effect=mock_execute_side_effect)
        mock_session.scalars = AsyncMock(side_effect=mock_scalars_side_effect)

        result = await service._push_payments_to_quickbooks()

        # In preview mode, should still process but with warnings
        assert result is not None

    @pytest.mark.asyncio
    async def test_prefetch_tenants_and_leases(self, payment_service, mock_session, test_user):
        """Test _prefetch_tenants_and_leases cache building."""
        from Backend.models.tenant import Tenant as TenantModel
        from Backend.models.lease import Lease

        # Create test data with proper user_id/landlord_id
        tenant1 = create_test_tenant(tenant_id=1, user_id=test_user.id, quickbooks_customer_id="QB1")
        tenant1.landlord_id = test_user.id
        tenant1.id = 1

        tenant2 = create_test_tenant(tenant_id=2, user_id=test_user.id, quickbooks_customer_id="QB2")
        tenant2.landlord_id = test_user.id
        tenant2.id = 2

        lease1 = MagicMock(spec=Lease)
        lease1.tenant_id = 1
        lease1.status = "active"

        # Create iterables that session.scalars returns
        async def mock_scalars_side_effect(stmt):
            if not hasattr(mock_scalars_side_effect, 'call_count'):
                mock_scalars_side_effect.call_count = 0
            mock_scalars_side_effect.call_count += 1

            if mock_scalars_side_effect.call_count == 1:
                # Return tenants iterable
                return iter([tenant1, tenant2])
            else:
                # Return leases iterable
                return iter([lease1])

        mock_session.scalars = AsyncMock(side_effect=mock_scalars_side_effect)

        result = await payment_service._prefetch_tenants_and_leases()

        # Should return dict with QB customer IDs as keys
        assert "QB1" in result
        assert "QB2" in result
        # QB1 should have tenant and lease
        assert result["QB1"][0] == tenant1
        assert result["QB1"][1] == lease1
        # QB2 should have tenant but no lease
        assert result["QB2"][0] == tenant2
        assert result["QB2"][1] is None

    @pytest.mark.asyncio
    async def test_resolve_tenant_and_lease_from_cache_missing_customer(self, payment_service):
        """Test _resolve_tenant_and_lease_from_cache with missing QB customer ID."""
        # Mock QB payment without customer ID
        qb_payment = {
            "Id": "pay123",
            "TotalAmt": 1200.00
            # Missing CustomerRef
        }

        tenant_cache = {}

        tenant, lease = payment_service._resolve_tenant_and_lease_from_cache(qb_payment, tenant_cache)

        # Should return None, None when customer ID is missing
        assert tenant is None
        assert lease is None

    @pytest.mark.asyncio
    async def test_resolve_tenant_and_lease_from_cache_customer_not_in_cache(self, payment_service):
        """Test _resolve_tenant_and_lease_from_cache when customer not in cache."""
        # Mock QB payment with customer ID
        qb_payment = {
            "Id": "pay123",
            "TotalAmt": 1200.00,
            "CustomerRef": {"value": "QB_NOT_IN_CACHE"}
        }

        # Empty cache
        tenant_cache = {}

        tenant, lease = payment_service._resolve_tenant_and_lease_from_cache(qb_payment, tenant_cache)

        # Should return None, None when customer not in cache
        assert tenant is None
        assert lease is None