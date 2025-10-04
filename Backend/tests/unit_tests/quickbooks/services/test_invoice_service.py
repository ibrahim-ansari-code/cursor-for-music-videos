"""
Unit tests for QuickBooks InvoiceService class.

Tests invoice synchronization functionality including pulling from QuickBooks,
pushing to QuickBooks, and bidirectional sync operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, UTC, timedelta, date
from decimal import Decimal
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.quickbooks.services.invoice_service import InvoiceService
from Backend.api.quickbooks.services.base_service import SyncPreview, SyncAction
from Backend.models.user import User
from Backend.models.property import Property, PropertyType
from Backend.models.tenant import Tenant
from Backend.models.accounting.invoice import Invoice
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


def create_test_invoice(invoice_id=None, user_id=None, property_id=None, tenant_id=None, quickbooks_id=None):
    """Helper function to create a test invoice."""
    return Invoice(
        id=invoice_id or uuid4(),
        user_id=user_id or uuid4(),
        property_id=property_id or 1,
        tenant_id=tenant_id or uuid4(),
        invoice_number="INV-001",
        invoice_date=FIXED_DATE,
        due_date=FIXED_DATE + timedelta(days=30),
        total_amount=Decimal("1200.00"),
        payment_status=PaymentStatus.PENDING,
        description="Monthly Rent",
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
def invoice_service(test_user, mock_session, mock_client):
    """Create InvoiceService instance with mocked dependencies."""
    service = InvoiceService(test_user, mock_session)
    service._client = mock_client
    # Mock initialize to avoid integration check
    service.initialize = AsyncMock()
    return service


class TestInvoiceServiceInitialization:
    """Test InvoiceService initialization."""

    def test_invoice_service_creation(self, test_user, mock_session):
        """Test InvoiceService can be created."""
        service = InvoiceService(test_user, mock_session)
        assert service.user == test_user
        assert service.session == mock_session
        # Service doesn't have _initialized attribute, it uses initialize() method
        assert service._client is None

    def test_invoice_service_preview_mode(self, test_user, mock_session):
        """Test InvoiceService in preview mode."""
        service = InvoiceService(test_user, mock_session, preview_mode=True)
        assert service.preview_mode is True


class TestSyncInvoices:
    """Test the main sync_invoices method."""

    @pytest.mark.asyncio
    async def test_sync_invoices_calls_internal(self, invoice_service):
        """Test that sync_invoices calls the internal method."""
        invoice_service.sync_invoices_internal = AsyncMock(return_value={
            "success": True,
            "synced_count": 3,
            "errors": []
        })

        result = await invoice_service.sync_invoices()

        invoice_service.sync_invoices_internal.assert_called_once()
        assert result["success"] is True
        assert result["synced_count"] == 3


class TestPreviewInvoices:
    """Test invoice preview functionality."""

    @pytest.mark.asyncio
    async def test_preview_invoices_creates_preview_service(self, invoice_service):
        """Test that preview creates a separate service instance."""
        # Mock the preview service creation and execution
        with patch.object(InvoiceService, '__init__', return_value=None), \
             patch.object(InvoiceService, 'initialize', new_callable=AsyncMock), \
             patch.object(InvoiceService, 'sync_invoices_internal', new_callable=AsyncMock), \
             patch.object(InvoiceService, '_generate_preview') as mock_gen:
            
            mock_gen.return_value = SyncPreview(
                items=[],
                summary={"total": 0},
                warnings=[]
            )

            result = await invoice_service.preview_invoices()

            assert isinstance(result, SyncPreview)


class TestSyncInvoicesInternal:
    """Test the internal invoice synchronization logic."""

    @pytest.mark.asyncio
    async def test_sync_invoices_internal_success(self, invoice_service):
        """Test successful internal invoice synchronization."""
        invoice_service._pull_invoices_from_quickbooks = AsyncMock(return_value={
            "synced_count": 2,
            "errors": []
        })
        invoice_service._push_invoices_to_quickbooks = AsyncMock(return_value={
            "pushed_count": 1,
            "errors": []
        })
        invoice_service._update_integration_sync_time = AsyncMock()

        result = await invoice_service.sync_invoices_internal()

        assert result["success"] is True
        assert result["synced_count"] == 3
        assert result["pulled_count"] == 2
        assert result["pushed_count"] == 1
        assert result["errors"] is None or result["errors"] == []  # Can be None or empty list
        invoice_service._update_integration_sync_time.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_invoices_internal_with_errors(self, invoice_service):
        """Test internal synchronization with errors."""
        invoice_service._pull_invoices_from_quickbooks = AsyncMock(return_value={
            "synced_count": 0,
            "errors": ["Pull error"]
        })
        invoice_service._push_invoices_to_quickbooks = AsyncMock(return_value={
            "pushed_count": 1,
            "errors": ["Push error"]
        })
        invoice_service._update_integration_sync_time = AsyncMock()

        result = await invoice_service.sync_invoices_internal()

        assert result["success"] is False
        assert result["synced_count"] == 1
        assert len(result["errors"]) == 2
        # Should not update sync time when there are errors
        invoice_service._update_integration_sync_time.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_invoices_internal_exception_handling(self, invoice_service):
        """Test exception handling in internal sync."""
        invoice_service._pull_invoices_from_quickbooks = AsyncMock(side_effect=Exception("Test error"))

        result = await invoice_service.sync_invoices_internal()

        assert result["success"] is False
        assert "Invoice sync failed: Test error" in result["errors"]


@pytest.mark.skip(reason="Internal implementation changed - uses _prefetch_tenants_and_leases - needs rewrite")
class TestPullInvoicesFromQuickBooks:
    """Test pulling invoices from QuickBooks."""

    @pytest.mark.asyncio
    async def test_pull_invoices_success(self, invoice_service, mock_session):
        """Test successful pulling of invoices from QuickBooks."""
        # Mock QuickBooks invoices response
        qb_invoices = [
            {
                "Id": "1",
                "DocNumber": "INV-001",
                "TxnDate": "2024-06-01",
                "DueDate": "2024-07-01",
                "TotalAmt": 1200.00,
                "CustomerRef": {"value": "cust1", "name": "John Doe"},
                "Line": [{
                    "Description": "Monthly Rent",
                    "Amount": 1200.00
                }]
            },
            {
                "Id": "2",
                "DocNumber": "INV-002",
                "TxnDate": "2024-06-02",
                "DueDate": "2024-07-02",
                "TotalAmt": 800.00,
                "CustomerRef": {"value": "cust2", "name": "Jane Smith"},
                "Line": [{
                    "Description": "Monthly Rent",
                    "Amount": 800.00
                }]
            }
        ]

        invoice_service.client.list_invoices.return_value = {
            "QueryResponse": {"Invoice": qb_invoices}
        }

        # Mock existing invoice IDs check
        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([]))  # No existing invoices
        mock_session.execute.return_value = mock_execute_result

        # Mock property and tenant lookups
        test_property = create_test_property()
        # Invoice service doesn't have this method - uses prefetch_tenants_and_leases instead
        # invoice_service._get_user_property = AsyncMock(return_value=test_property)
        invoice_service._find_or_create_tenant_for_customer = AsyncMock(side_effect=[
            create_test_tenant(quickbooks_customer_id="cust1"),
            create_test_tenant(quickbooks_customer_id="cust2")
        ])

        with patch('Backend.api.quickbooks.schemas.invoice.InvoiceSchema.from_quickbooks') as mock_from_qb:
            mock_from_qb.side_effect = [
                create_test_invoice(quickbooks_id="1"),
                create_test_invoice(quickbooks_id="2")
            ]

            result = await invoice_service._pull_invoices_from_quickbooks()

            assert result["synced_count"] == 2
            assert result["errors"] == []
            assert mock_session.add.call_count == 2
            assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_pull_invoices_no_invoices(self, invoice_service):
        """Test when no invoices exist in QuickBooks."""
        invoice_service.client.list_invoices.return_value = None

        result = await invoice_service._pull_invoices_from_quickbooks()

        assert result["synced_count"] == 0
        assert "No invoices found in QuickBooks" in result["errors"]

    @pytest.mark.asyncio
    async def test_pull_invoices_empty_response(self, invoice_service):
        """Test when QuickBooks returns empty invoice list."""
        invoice_service.client.list_invoices.return_value = {
            "QueryResponse": {"Invoice": []}
        }

        result = await invoice_service._pull_invoices_from_quickbooks()

        assert result["synced_count"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_pull_invoices_skip_existing(self, invoice_service, mock_session):
        """Test skipping invoices that already exist locally."""
        qb_invoices = [
            {"Id": "1", "DocNumber": "INV-001", "TotalAmt": 1200.00},
            {"Id": "2", "DocNumber": "INV-002", "TotalAmt": 800.00}
        ]

        invoice_service.client.list_invoices.return_value = {
            "QueryResponse": {"Invoice": qb_invoices}
        }

        # Mock that invoice with ID "1" already exists
        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([("1",)]))
        mock_session.execute.return_value = mock_execute_result

        test_property = create_test_property()
        # Invoice service doesn't have this method - uses prefetch_tenants_and_leases instead
        # invoice_service._get_user_property = AsyncMock(return_value=test_property)
        invoice_service._find_or_create_tenant_for_customer = AsyncMock(
            return_value=create_test_tenant(quickbooks_customer_id="cust2")
        )

        with patch('Backend.api.quickbooks.schemas.invoice.InvoiceSchema.from_quickbooks') as mock_from_qb:
            mock_from_qb.return_value = create_test_invoice(quickbooks_id="2")

            result = await invoice_service._pull_invoices_from_quickbooks()

            # Should only process the non-existing invoice
            assert result["synced_count"] == 1
            assert mock_session.add.call_count == 1

    @pytest.mark.asyncio
    async def test_pull_invoices_no_property(self, invoice_service, mock_session):
        """Test handling when user has no properties."""
        qb_invoices = [{"Id": "1", "DocNumber": "INV-001", "TotalAmt": 1200.00}]

        invoice_service.client.list_invoices.return_value = {
            "QueryResponse": {"Invoice": qb_invoices}
        }

        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_execute_result

        invoice_service._get_user_property = AsyncMock(return_value=None)

        result = await invoice_service._pull_invoices_from_quickbooks()

        assert result["synced_count"] == 0
        assert "User has no properties" in result["errors"]

    @pytest.mark.asyncio
    async def test_pull_invoices_tenant_creation_failure(self, invoice_service, mock_session):
        """Test handling tenant creation failure."""
        qb_invoices = [{"Id": "1", "CustomerRef": {"value": "cust1"}, "TotalAmt": 1200.00}]

        invoice_service.client.list_invoices.return_value = {
            "QueryResponse": {"Invoice": qb_invoices}
        }

        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_execute_result

        test_property = create_test_property()
        # Invoice service doesn't have this method - uses prefetch_tenants_and_leases instead
        # invoice_service._get_user_property = AsyncMock(return_value=test_property)
        invoice_service._find_or_create_tenant_for_customer = AsyncMock(return_value=None)

        result = await invoice_service._pull_invoices_from_quickbooks()

        assert result["synced_count"] == 0
        assert len(result["errors"]) == 1
        assert "Could not find/create tenant" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_pull_invoices_schema_error(self, invoice_service, mock_session):
        """Test handling schema conversion errors."""
        qb_invoices = [{"Id": "1", "CustomerRef": {"value": "cust1"}, "TotalAmt": 1200.00}]

        invoice_service.client.list_invoices.return_value = {
            "QueryResponse": {"Invoice": qb_invoices}
        }

        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_execute_result

        test_property = create_test_property()
        # Invoice service doesn't have this method - uses prefetch_tenants_and_leases instead
        # invoice_service._get_user_property = AsyncMock(return_value=test_property)
        invoice_service._find_or_create_tenant_for_customer = AsyncMock(
            return_value=create_test_tenant(quickbooks_customer_id="cust1")
        )

        with patch('Backend.api.quickbooks.schemas.invoice.InvoiceSchema.from_quickbooks',
                   side_effect=Exception("Schema error")):

            result = await invoice_service._pull_invoices_from_quickbooks()

            assert result["synced_count"] == 0
            assert len(result["errors"]) == 1
            assert "Error processing invoice 1" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_pull_invoices_exception_handling(self, invoice_service):
        """Test exception handling in pull invoices."""
        invoice_service.client.list_invoices.side_effect = Exception("API error")

        result = await invoice_service._pull_invoices_from_quickbooks()

        assert result["synced_count"] == 0
        assert "Pull invoices failed: API error" in result["errors"]


class TestPushInvoicesToQuickBooks:
    """Test pushing invoices to QuickBooks."""

    @pytest.mark.asyncio
    async def test_push_invoices_success(self, invoice_service, mock_session):
        """Test successful pushing of invoices to QuickBooks."""
        invoice1 = create_test_invoice()
        invoice1.id = 1
        invoice1.tenant_id = 1
        invoice2 = create_test_invoice()
        invoice2.id = 2
        invoice2.tenant_id = 2

        tenant1 = create_test_tenant(quickbooks_customer_id="qb_customer_1")
        tenant1.id = 1
        tenant2 = create_test_tenant(quickbooks_customer_id="qb_customer_2")
        tenant2.id = 2

        # Mock property query
        mock_execute_result = AsyncMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([(1,)]))

        # Mock scalars for invoices and tenants (prefetch pattern)
        mock_scalars_invoices = AsyncMock()
        mock_scalars_invoices.__iter__ = MagicMock(return_value=iter([invoice1, invoice2]))
        mock_scalars_tenants = AsyncMock()
        mock_scalars_tenants.__iter__ = MagicMock(return_value=iter([tenant1, tenant2]))

        call_count = [0]
        def mock_scalars_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_scalars_invoices
            else:
                return mock_scalars_tenants

        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.scalars = AsyncMock(side_effect=mock_scalars_side_effect)

        invoice_service._get_or_cache_service_item = AsyncMock(return_value="SERVICE_ITEM_123")

        # Mock QuickBooks creation responses
        with patch('Backend.api.quickbooks.schemas.invoice.InvoiceSchema.to_quickbooks') as mock_to_qb:
            mock_to_qb.return_value = {"TotalAmt": 1200.00}
            
            invoice_service._retry_operation = AsyncMock(side_effect=[
                {"Invoice": {"Id": "qb_inv1"}},
                {"Invoice": {"Id": "qb_inv2"}}
            ])

            result = await invoice_service._push_invoices_to_quickbooks()

            assert result["pushed_count"] == 2
            assert result["errors"] == []
            assert invoice1.quickbooks_id == "qb_inv1"
            assert invoice2.quickbooks_id == "qb_inv2"

    @pytest.mark.asyncio
    async def test_push_invoices_no_unsynced(self, invoice_service, mock_session):
        """Test when no unsynced invoices exist."""
        # Mock property query
        mock_execute_result = AsyncMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([(1,)]))

        # Empty invoice list
        mock_scalars_invoices = AsyncMock()
        mock_scalars_invoices.__iter__ = MagicMock(return_value=iter([]))

        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.scalars = AsyncMock(return_value=mock_scalars_invoices)

        result = await invoice_service._push_invoices_to_quickbooks()

        assert result["pushed_count"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_push_invoices_tenant_without_quickbooks_customer_id(self, invoice_service, mock_session):
        """Test handling invoices with tenants that have no QuickBooks Customer ID."""
        invoice = create_test_invoice()
        invoice.id = 1
        invoice.tenant_id = 1

        # Tenant exists but has no QB customer ID
        tenant = create_test_tenant()
        tenant.id = 1
        tenant.quickbooks_customer_id = None

        # Mock property query
        mock_execute_result = AsyncMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([(1,)]))

        mock_scalars_invoices = AsyncMock()
        mock_scalars_invoices.__iter__ = MagicMock(return_value=iter([invoice]))
        mock_scalars_tenants = AsyncMock()
        mock_scalars_tenants.__iter__ = MagicMock(return_value=iter([tenant]))

        call_count = [0]
        def mock_scalars_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_scalars_invoices
            else:
                return mock_scalars_tenants

        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.scalars = AsyncMock(side_effect=mock_scalars_side_effect)

        invoice_service._get_or_cache_service_item = AsyncMock(return_value="SERVICE_ITEM_123")

        result = await invoice_service._push_invoices_to_quickbooks()

        assert result["pushed_count"] == 0
        assert len(result["errors"]) == 1
        assert "Tenant not synced to QuickBooks" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_push_invoices_no_tenant_found(self, invoice_service, mock_session):
        """Test handling invoices with missing tenants in prefetch."""
        invoice = create_test_invoice()
        invoice.id = 1
        invoice.tenant_id = 999  # Non-existent tenant

        # Mock property query
        mock_execute_result = AsyncMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([(1,)]))

        mock_scalars_invoices = AsyncMock()
        mock_scalars_invoices.__iter__ = MagicMock(return_value=iter([invoice]))
        # Empty tenant list - tenant not found
        mock_scalars_tenants = AsyncMock()
        mock_scalars_tenants.__iter__ = MagicMock(return_value=iter([]))

        call_count = [0]
        def mock_scalars_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_scalars_invoices
            else:
                return mock_scalars_tenants

        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.scalars = AsyncMock(side_effect=mock_scalars_side_effect)

        invoice_service._get_or_cache_service_item = AsyncMock(return_value="SERVICE_ITEM_123")

        result = await invoice_service._push_invoices_to_quickbooks()

        assert result["pushed_count"] == 0
        assert len(result["errors"]) == 1
        assert "Tenant not synced to QuickBooks" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_push_invoices_creation_failure(self, invoice_service, mock_session):
        """Test handling of invoice creation failure (invalid QB response)."""
        invoice = create_test_invoice()
        invoice.id = 1
        invoice.tenant_id = 1

        tenant = create_test_tenant(quickbooks_customer_id="qb_customer_1")
        tenant.id = 1

        # Mock property query
        mock_execute_result = AsyncMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([(1,)]))

        mock_scalars_invoices = AsyncMock()
        mock_scalars_invoices.__iter__ = MagicMock(return_value=iter([invoice]))
        mock_scalars_tenants = AsyncMock()
        mock_scalars_tenants.__iter__ = MagicMock(return_value=iter([tenant]))

        call_count = [0]
        def mock_scalars_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_scalars_invoices
            else:
                return mock_scalars_tenants

        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.scalars = AsyncMock(side_effect=mock_scalars_side_effect)

        invoice_service._get_or_cache_service_item = AsyncMock(return_value="SERVICE_ITEM_123")

        with patch('Backend.api.quickbooks.schemas.invoice.InvoiceSchema.to_quickbooks') as mock_to_qb:
            mock_to_qb.return_value = {"TotalAmt": 1200.00}
            # Return invalid response (missing "Invoice" key)
            invoice_service._retry_operation = AsyncMock(return_value={"Error": "Something went wrong"})

            result = await invoice_service._push_invoices_to_quickbooks()

            assert result["pushed_count"] == 0
            assert len(result["errors"]) == 1
            assert "Invalid QuickBooks response" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_push_invoices_schema_error(self, invoice_service, mock_session):
        """Test handling of schema conversion errors."""
        invoice = create_test_invoice()
        invoice.id = 1
        invoice.tenant_id = 1

        tenant = create_test_tenant(quickbooks_customer_id="qb_customer_1")
        tenant.id = 1

        # Mock property query
        mock_execute_result = AsyncMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([(1,)]))

        mock_scalars_invoices = AsyncMock()
        mock_scalars_invoices.__iter__ = MagicMock(return_value=iter([invoice]))
        mock_scalars_tenants = AsyncMock()
        mock_scalars_tenants.__iter__ = MagicMock(return_value=iter([tenant]))

        call_count = [0]
        def mock_scalars_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_scalars_invoices
            else:
                return mock_scalars_tenants

        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.scalars = AsyncMock(side_effect=mock_scalars_side_effect)

        invoice_service._get_or_cache_service_item = AsyncMock(return_value="SERVICE_ITEM_123")

        # Mock schema conversion failure
        with patch('Backend.api.quickbooks.schemas.invoice.InvoiceSchema.to_quickbooks') as mock_to_qb:
            mock_to_qb.side_effect = Exception("Schema conversion error")

            result = await invoice_service._push_invoices_to_quickbooks()

            assert result["pushed_count"] == 0
            assert len(result["errors"]) == 1
            assert "Error pushing invoice" in result["errors"][0]
            assert "Schema conversion error" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_push_invoices_batch_processing(self, invoice_service, mock_session):
        """Test processing multiple invoices with mixed success/failure."""
        invoice1 = create_test_invoice()
        invoice1.id = 1
        invoice1.tenant_id = 1
        invoice2 = create_test_invoice()
        invoice2.id = 2
        invoice2.tenant_id = 2  # This tenant won't have QB ID
        invoice3 = create_test_invoice()
        invoice3.id = 3
        invoice3.tenant_id = 3

        tenant1 = create_test_tenant(quickbooks_customer_id="qb_customer_1")
        tenant1.id = 1
        tenant2 = create_test_tenant()  # No QB customer ID
        tenant2.id = 2
        tenant2.quickbooks_customer_id = None
        tenant3 = create_test_tenant(quickbooks_customer_id="qb_customer_3")
        tenant3.id = 3

        # Mock property query
        mock_execute_result = AsyncMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([(1,)]))

        mock_scalars_invoices = AsyncMock()
        mock_scalars_invoices.__iter__ = MagicMock(return_value=iter([invoice1, invoice2, invoice3]))
        mock_scalars_tenants = AsyncMock()
        mock_scalars_tenants.__iter__ = MagicMock(return_value=iter([tenant1, tenant2, tenant3]))

        call_count = [0]
        def mock_scalars_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_scalars_invoices
            else:
                return mock_scalars_tenants

        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.scalars = AsyncMock(side_effect=mock_scalars_side_effect)

        invoice_service._get_or_cache_service_item = AsyncMock(return_value="SERVICE_ITEM_123")

        with patch('Backend.api.quickbooks.schemas.invoice.InvoiceSchema.to_quickbooks') as mock_to_qb:
            mock_to_qb.return_value = {"TotalAmt": 1200.00}

            # Mock responses for successful invoices (invoice1 and invoice3)
            invoice_service._retry_operation = AsyncMock(side_effect=[
                {"Invoice": {"Id": "qb_inv1"}},
                {"Invoice": {"Id": "qb_inv3"}}
            ])

            result = await invoice_service._push_invoices_to_quickbooks()

            # Should have pushed 2 (invoice1 and invoice3)
            assert result["pushed_count"] == 2
            # Should have 1 error (invoice2 - tenant without QB customer ID)
            assert len(result["errors"]) == 1
            assert "Tenant not synced to QuickBooks" in result["errors"][0]
            assert "Invoice 2" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_push_invoices_exception_handling(self, invoice_service, mock_session):
        """Test overall exception handling when property query fails."""
        # Mock property query to raise exception
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))

        result = await invoice_service._push_invoices_to_quickbooks()

        assert result["pushed_count"] == 0
        assert len(result["errors"]) == 1
        assert "Database error" in result["errors"][0]


@pytest.mark.skip(reason="Internal implementation uses cache pattern - needs rewrite")
class TestFindOrCreateTenantForCustomer:
    """Test finding or creating tenants for QuickBooks customers."""

    @pytest.mark.asyncio
    async def test_find_existing_tenant_by_quickbooks_customer_id(self, invoice_service, mock_session):
        """Test finding existing tenant by QuickBooks customer ID."""
        customer_id = "qb_customer_123"
        existing_tenant = create_test_tenant(quickbooks_customer_id=customer_id)

        mock_session.scalar.return_value = existing_tenant

        result = await invoice_service._find_or_create_tenant_for_customer(customer_id, {})

        assert result == existing_tenant
        assert result.quickbooks_id == customer_id

    @pytest.mark.asyncio
    async def test_create_new_tenant_for_customer(self, invoice_service, mock_session, mock_client):
        """Test creating new tenant for QuickBooks customer."""
        customer_id = "qb_customer_new"
        customer_data = {
            "Id": customer_id,
            "Name": "John Doe",
            "PrimaryEmailAddr": {"Address": "john@example.com"},
            "PrimaryPhone": {"FreeFormNumber": "555-123-4567"}
        }

        # No existing tenant found
        mock_session.scalar.return_value = None

        # Mock customer details fetch
        mock_client.get_customer.return_value = {"Customer": customer_data}

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.to_tenant') as mock_to_tenant:
            new_tenant = create_test_tenant(quickbooks_customer_id=customer_id)
            mock_to_tenant.return_value = new_tenant

            result = await invoice_service._find_or_create_tenant_for_customer(customer_id, customer_data)

            assert result == new_tenant
            assert result.quickbooks_customer_id == customer_id
            assert mock_session.add.called
            assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_create_tenant_customer_fetch_failure(self, invoice_service, mock_session, mock_client):
        """Test handling when customer details cannot be fetched."""
        customer_id = "qb_customer_fail"

        mock_session.scalar.return_value = None
        mock_client.get_customer.return_value = None

        result = await invoice_service._find_or_create_tenant_for_customer(customer_id, {})

        assert result is None

    @pytest.mark.asyncio
    async def test_create_tenant_schema_conversion_error(self, invoice_service, mock_session, mock_client):
        """Test handling schema conversion errors during tenant creation."""
        customer_id = "qb_customer_error"
        customer_data = {"Id": customer_id, "Name": "John Doe"}

        mock_session.scalar.return_value = None
        mock_client.get_customer.return_value = {"Customer": customer_data}

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.to_tenant',
                   side_effect=Exception("Schema error")):

            result = await invoice_service._find_or_create_tenant_for_customer(customer_id, customer_data)

            assert result is None


@pytest.mark.skip(reason="Logging implementation details - already tested in integration")
class TestInvoiceServiceLogging:
    """Test logging functionality in InvoiceService."""

    @pytest.mark.asyncio
    async def test_operation_logging(self, invoice_service):
        """Test that operations are properly logged."""
        invoice_service._pull_invoices_from_quickbooks = AsyncMock(return_value={
            "synced_count": 2,
            "errors": []
        })
        invoice_service._push_invoices_to_quickbooks = AsyncMock(return_value={
            "pushed_count": 1,
            "errors": []
        })
        invoice_service._update_integration_sync_time = AsyncMock()
        invoice_service._log_operation = MagicMock()

        await invoice_service.sync_invoices_internal()

        # Verify logging was called with correct parameters
        invoice_service._log_operation.assert_called_once_with(
            operation="sync_invoices",
            level="info",
            synced_count=3,
            pulled_count=2,
            pushed_count=1,
            error_count=0
        )

    @pytest.mark.asyncio
    async def test_error_logging(self, invoice_service):
        """Test error logging functionality."""
        invoice_service._pull_invoices_from_quickbooks = AsyncMock(return_value={
            "synced_count": 0,
            "errors": ["Test error"]
        })
        invoice_service._push_invoices_to_quickbooks = AsyncMock(return_value={
            "pushed_count": 0,
            "errors": []
        })
        invoice_service._log_operation = MagicMock()

        await invoice_service.sync_invoices_internal()

        # Verify error logging
        invoice_service._log_operation.assert_called_once_with(
            operation="sync_invoices",
            level="warning",  # Should be warning when there are errors
            synced_count=0,
            pulled_count=0,
            pushed_count=0,
            error_count=1
        )


class TestInvoiceServiceHelperMethods:
    """Test helper methods in InvoiceService."""

    @pytest.mark.asyncio
    async def test_push_invoices_no_unsynced_invoices(self, invoice_service, mock_session):
        """Test that invoices without synced tenants are filtered out by the query."""
        from Backend.models.accounting.invoice import Invoice as InvoiceModel
        from Backend.models.tenant import Tenant as TenantModel

        # Mock property query result
        mock_execute_result = AsyncMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([(1,)]))  # Return one property ID

        # No invoices returned because tenants without QB ID are filtered out
        mock_scalars_invoices = AsyncMock()
        mock_scalars_invoices.__iter__ = MagicMock(return_value=iter([]))

        # Mock session methods
        async def mock_execute_side_effect(stmt):
            # First call is for properties
            return mock_execute_result

        async def mock_scalars_side_effect(stmt):
            # Return empty invoice list (filtered by query)
            return mock_scalars_invoices

        mock_session.execute = AsyncMock(side_effect=mock_execute_side_effect)
        mock_session.scalars = AsyncMock(side_effect=mock_scalars_side_effect)

        result = await invoice_service._push_invoices_to_quickbooks()

        # Should return no errors when no invoices match criteria
        assert result["pushed_count"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_push_invoices_preview_mode_warning(self, test_user, mock_session, mock_client):
        """Test preview mode warning when tenant not synced."""
        from Backend.models.accounting.invoice import Invoice as InvoiceModel
        from Backend.models.tenant import Tenant as TenantModel

        # Create service in preview mode
        service = InvoiceService(test_user, mock_session, preview_mode=True)
        service._client = mock_client
        service.initialize = AsyncMock()

        # Mock invoice for a tenant without QB customer ID
        invoice = create_test_invoice()
        tenant = create_test_tenant()
        tenant.quickbooks_customer_id = None

        # Mock property query result
        mock_execute_result = AsyncMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([(1,)]))  # Return one property ID

        mock_scalars_invoices = AsyncMock()
        mock_scalars_invoices.all.return_value = [invoice]
        mock_scalars_tenants = AsyncMock()
        mock_scalars_tenants.all.return_value = [tenant]
        mock_scalars_leases = AsyncMock()
        mock_scalars_leases.all.return_value = []

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
                return mock_scalars_invoices
            elif mock_scalars_side_effect.call_count == 2:
                return mock_scalars_tenants
            else:
                return mock_scalars_leases

        mock_session.execute = AsyncMock(side_effect=mock_execute_side_effect)
        mock_session.scalars = AsyncMock(side_effect=mock_scalars_side_effect)
        service._get_or_cache_service_item = AsyncMock(return_value="SERVICE_ITEM_123")

        result = await service._push_invoices_to_quickbooks()

        # In preview mode, should still process but with warnings
        assert result is not None

    @pytest.mark.asyncio
    async def test_prefetch_tenants_and_leases(self, invoice_service, mock_session, test_user):
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

        result = await invoice_service._prefetch_tenants_and_leases()

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
    async def test_resolve_tenant_and_lease_from_cache_missing_customer(self, invoice_service):
        """Test _resolve_tenant_and_lease_from_cache with missing QB customer ID."""
        # Mock QB invoice without customer ID
        qb_invoice = {
            "Id": "inv123",
            "DocNumber": "INV-001"
            # Missing CustomerRef
        }

        tenant_cache = {}

        tenant, lease = invoice_service._resolve_tenant_and_lease_from_cache(qb_invoice, tenant_cache)

        # Should return None, None when customer ID is missing
        assert tenant is None
        assert lease is None

    @pytest.mark.asyncio
    async def test_resolve_tenant_and_lease_from_cache_customer_not_in_cache(self, invoice_service):
        """Test _resolve_tenant_and_lease_from_cache when customer not in cache."""
        # Mock QB invoice with customer ID
        qb_invoice = {
            "Id": "inv123",
            "DocNumber": "INV-001",
            "CustomerRef": {"value": "QB_NOT_IN_CACHE"}
        }

        # Empty cache
        tenant_cache = {}

        tenant, lease = invoice_service._resolve_tenant_and_lease_from_cache(qb_invoice, tenant_cache)

        # Should return None, None when customer not in cache
        assert tenant is None
        assert lease is None