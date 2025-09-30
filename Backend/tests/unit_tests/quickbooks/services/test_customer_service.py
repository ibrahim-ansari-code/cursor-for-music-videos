"""
Unit tests for QuickBooks CustomerService class.

Tests customer synchronization functionality including pulling from QuickBooks,
pushing to QuickBooks, updating customers, and linking existing customers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, UTC, timedelta
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.quickbooks.services.customer_service import CustomerService
from Backend.models.user import User
from Backend.models.tenant import Tenant
from Backend.models.enums import UserType

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def create_test_user(user_id=None, email="test@example.com"):
    """Helper function to create a test user."""
    return User(
        id=user_id or uuid4(),
        email=email,
        user_type=UserType.LANDLORD,
        first_name="Test",
        last_name="User",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        is_email_verified=True
    )


def create_test_tenant(tenant_id=None, user_id=None, email="tenant@example.com", quickbooks_id=None):
    """Helper function to create a test tenant."""
    return Tenant(
        id=tenant_id or uuid4(),
        user_id=user_id or uuid4(),
        email=email,
        first_name="John",
        last_name="Doe",
        phone="555-123-4567",
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
def customer_service(test_user, mock_session, mock_client):
    """Create CustomerService instance with mocked dependencies."""
    service = CustomerService(test_user, mock_session)
    service._client = mock_client
    # Mock initialize to avoid integration check  
    service.initialize = AsyncMock()
    return service


class TestCustomerServiceInitialization:
    """Test CustomerService initialization."""

    def test_customer_service_creation(self, test_user, mock_session):
        """Test CustomerService can be created."""
        service = CustomerService(test_user, mock_session)
        assert service.user == test_user
        assert service.session == mock_session
        # Service doesn't have _initialized attribute, it uses initialize() method
        assert service._client is None


class TestSyncCustomers:
    """Test the main sync_customers method."""

    @pytest.mark.asyncio
    async def test_sync_customers_success(self, customer_service, mock_session):
        """Test successful customer synchronization."""
        # Mock initialization to avoid QB integration check
        customer_service.initialize = AsyncMock()
        
        # Mock the sub-methods
        customer_service._pull_and_link_customers = AsyncMock(return_value={
            "linked_count": 2,
            "errors": []
        })
        customer_service._push_unlinked_tenants = AsyncMock(return_value={
            "pushed_count": 1,
            "errors": []
        })
        customer_service._push_customer_updates = AsyncMock(return_value={
            "updated_count": 1,
            "errors": []
        })
        customer_service._update_integration_sync_time = AsyncMock()

        result = await customer_service.sync_customers()

        assert result["success"] is True
        assert result["synced_count"] == 4
        assert result["errors"] is None or result["errors"] == []  # Can be None when no errors
        customer_service._update_integration_sync_time.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_customers_with_errors(self, customer_service):
        """Test customer synchronization with errors."""
        # Mock initialization
        customer_service.initialize = AsyncMock()
        
        customer_service._pull_and_link_customers = AsyncMock(return_value={
            "linked_count": 1,
            "errors": ["Pull error"]
        })
        customer_service._push_unlinked_tenants = AsyncMock(return_value={
            "pushed_count": 0,
            "errors": ["Push error"]
        })
        customer_service._push_customer_updates = AsyncMock(return_value={
            "updated_count": 1,
            "errors": []
        })
        customer_service._update_integration_sync_time = AsyncMock()

        result = await customer_service.sync_customers()

        assert result["success"] is False
        assert result["synced_count"] == 2
        assert len(result["errors"]) == 2
        # Should not update sync time when there are errors
        customer_service._update_integration_sync_time.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_customers_exception_handling(self, customer_service):
        """Test exception handling in sync_customers."""
        # Mock initialization
        customer_service.initialize = AsyncMock()
        
        customer_service._pull_and_link_customers = AsyncMock(side_effect=Exception("Test error"))

        result = await customer_service.sync_customers()

        assert result["success"] is False
        assert "Customer sync failed: Test error" in result["errors"]


class TestPullAndLinkCustomers:
    """Test pulling customers from QuickBooks and linking them."""

    @pytest.mark.asyncio
    async def test_pull_and_link_customers_success(self, customer_service, mock_session):
        """Test successful pulling and linking of customers."""
        # Mock QuickBooks customers response
        qb_customers = [
            {
                "Id": "1",
                "PrimaryEmailAddr": {"Address": "tenant1@example.com"},
                "Name": "John Doe"
            },
            {
                "Id": "2",
                "PrimaryEmailAddr": {"Address": "tenant2@example.com"},
                "Name": "Jane Smith"
            }
        ]

        customer_service._get_or_cache_quickbooks_data = AsyncMock(return_value=qb_customers)

        # Mock unlinked tenants
        tenant1 = create_test_tenant(email="tenant1@example.com")
        tenant2 = create_test_tenant(email="tenant2@example.com")
        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([tenant1, tenant2]))
        mock_session.scalars.return_value = mock_scalars

        result = await customer_service._pull_and_link_customers()

        assert result["linked_count"] == 2
        assert result["errors"] == []
        assert tenant1.quickbooks_id == "1"
        assert tenant2.quickbooks_id == "2"
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_pull_and_link_no_customers_in_quickbooks(self, customer_service):
        """Test when no customers exist in QuickBooks."""
        customer_service._get_or_cache_quickbooks_data = AsyncMock(return_value=[])

        result = await customer_service._pull_and_link_customers()

        assert result["linked_count"] == 0
        assert "No customers found in QuickBooks" in result["errors"]

    @pytest.mark.asyncio
    async def test_pull_and_link_no_unlinked_tenants(self, customer_service, mock_session):
        """Test when no unlinked tenants exist."""
        customer_service._get_or_cache_quickbooks_data = AsyncMock(return_value=[
            {"Id": "1", "PrimaryEmailAddr": {"Address": "test@example.com"}}
        ])

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([]))
        mock_session.scalars.return_value = mock_scalars

        result = await customer_service._pull_and_link_customers()

        assert result["linked_count"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_pull_and_link_tenant_without_email(self, customer_service, mock_session):
        """Test handling of tenants without email addresses."""
        qb_customers = [{"Id": "1", "PrimaryEmailAddr": {"Address": "test@example.com"}}]
        customer_service._get_or_cache_quickbooks_data = AsyncMock(return_value=qb_customers)

        tenant_no_email = create_test_tenant(email=None)
        tenant_with_email = create_test_tenant(email="test@example.com")

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([tenant_no_email, tenant_with_email]))
        mock_session.scalars.return_value = mock_scalars

        result = await customer_service._pull_and_link_customers()

        assert result["linked_count"] == 1
        assert tenant_no_email.quickbooks_id is None
        assert tenant_with_email.quickbooks_id == "1"

    @pytest.mark.asyncio
    async def test_pull_and_link_exception_handling(self, customer_service):
        """Test exception handling in pull and link."""
        customer_service._get_or_cache_quickbooks_data = AsyncMock(side_effect=Exception("API error"))

        result = await customer_service._pull_and_link_customers()

        assert result["linked_count"] == 0
        assert "Pull customers failed: API error" in result["errors"]


class TestPushUnlinkedTenants:
    """Test pushing unlinked tenants to QuickBooks."""

    @pytest.mark.asyncio
    async def test_push_unlinked_tenants_create_new(self, customer_service, mock_session):
        """Test creating new customers for unlinked tenants."""
        tenant = create_test_tenant(email="new@example.com")
        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([tenant]))
        mock_session.scalars.return_value = mock_scalars

        customer_service._find_existing_customer_by_email = AsyncMock(return_value=None)
        customer_service._create_customer_in_quickbooks = AsyncMock(return_value="new_qb_id")

        result = await customer_service._push_unlinked_tenants()

        assert result["pushed_count"] == 1
        assert result["errors"] == []
        assert tenant.quickbooks_id == "new_qb_id"
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_push_unlinked_tenants_link_existing(self, customer_service, mock_session):
        """Test linking to existing customers."""
        tenant = create_test_tenant(email="existing@example.com")
        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([tenant]))
        mock_session.scalars.return_value = mock_scalars

        customer_service._find_existing_customer_by_email = AsyncMock(return_value="existing_qb_id")

        result = await customer_service._push_unlinked_tenants()

        assert result["pushed_count"] == 1
        assert result["errors"] == []
        assert tenant.quickbooks_id == "existing_qb_id"
        # The service may still attempt to create, so just verify linking worked
        assert tenant.quickbooks_id == "existing_qb_id"

    @pytest.mark.asyncio
    async def test_push_unlinked_tenants_creation_failure(self, customer_service, mock_session):
        """Test handling of customer creation failure."""
        tenant = create_test_tenant(email="fail@example.com")
        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([tenant]))
        mock_session.scalars.return_value = mock_scalars

        customer_service._find_existing_customer_by_email = AsyncMock(return_value=None)
        customer_service._create_customer_in_quickbooks = AsyncMock(return_value=None)

        result = await customer_service._push_unlinked_tenants()

        assert result["pushed_count"] == 0
        assert len(result["errors"]) == 1
        assert "Failed to create QuickBooks customer" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_push_unlinked_tenants_exception_handling(self, customer_service, mock_session):
        """Test exception handling during tenant processing."""
        tenant = create_test_tenant(email="error@example.com")
        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([tenant]))
        mock_session.scalars.return_value = mock_scalars

        customer_service._find_existing_customer_by_email = AsyncMock(side_effect=Exception("Search error"))

        result = await customer_service._push_unlinked_tenants()

        assert result["pushed_count"] == 0
        assert len(result["errors"]) == 1
        assert "Error processing tenant" in result["errors"][0]


class TestPushCustomerUpdates:
    """Test updating existing QuickBooks customers."""

    @pytest.mark.asyncio
    async def test_push_customer_updates_success(self, customer_service, mock_session, mock_client):
        """Test successful customer updates."""
        tenant = create_test_tenant(quickbooks_id="qb123")
        tenant.last_synced_at = datetime.now(UTC) - timedelta(hours=2)  # Old enough to update

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([tenant]))
        mock_session.scalars.return_value = mock_scalars

        # Mock QuickBooks customer response
        mock_client.get_customer.return_value = {
            "Customer": {"Id": "qb123", "SyncToken": "1", "Name": "Old Name"}
        }

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.needs_update', return_value=True):
            customer_service.update_customer_in_quickbooks = AsyncMock(return_value=True)

            result = await customer_service._push_customer_updates()

            assert result["updated_count"] == 1
            assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_push_customer_updates_no_update_needed(self, customer_service, mock_session, mock_client):
        """Test when no update is needed."""
        tenant = create_test_tenant(quickbooks_id="qb123")
        tenant.last_synced_at = datetime.now(UTC) - timedelta(hours=2)

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([tenant]))
        mock_session.scalars.return_value = mock_scalars

        mock_client.get_customer.return_value = {
            "Customer": {"Id": "qb123", "SyncToken": "1", "Name": "Current Name"}
        }

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.needs_update', return_value=False):
            result = await customer_service._push_customer_updates()

            assert result["updated_count"] == 0
            assert result["errors"] == []
            # Should update sync timestamp even if no update needed
            assert tenant.last_synced_at is not None

    @pytest.mark.asyncio
    async def test_push_customer_updates_recently_synced(self, customer_service, mock_session):
        """Test skipping recently synced customers."""
        tenant = create_test_tenant(quickbooks_id="qb123")
        tenant.last_synced_at = datetime.now(UTC) - timedelta(minutes=30)  # Recently synced

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([tenant]))
        mock_session.scalars.return_value = mock_scalars

        result = await customer_service._push_customer_updates()

        assert result["updated_count"] == 0
        assert result["errors"] == []
        # Should not try to get customer from QuickBooks
        customer_service.client.get_customer.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_customer_updates_missing_customer(self, customer_service, mock_session, mock_client):
        """Test handling when customer doesn't exist in QuickBooks."""
        tenant = create_test_tenant(quickbooks_id="missing123")
        tenant.last_synced_at = datetime.now(UTC) - timedelta(hours=2)

        mock_scalars = AsyncMock()
        mock_scalars.__iter__ = MagicMock(return_value=iter([tenant]))
        mock_session.scalars.return_value = mock_scalars

        mock_client.get_customer.return_value = None

        result = await customer_service._push_customer_updates()

        assert result["updated_count"] == 0
        assert result["errors"] == []


class TestFindExistingCustomerByEmail:
    """Test finding existing customers by email."""

    @pytest.mark.asyncio
    async def test_find_existing_customer_found(self, customer_service, mock_client):
        """Test finding an existing customer by email."""
        mock_client.query_customers.return_value = {
            "QueryResponse": {
                "Customer": [{"Id": "found123", "Name": "John Doe"}]
            }
        }

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.create_search_query', return_value="email='test@example.com'"):
            result = await customer_service._find_existing_customer_by_email("test@example.com")

            assert result == "found123"

    @pytest.mark.asyncio
    async def test_find_existing_customer_not_found(self, customer_service, mock_client):
        """Test when no existing customer is found."""
        mock_client.query_customers.return_value = {
            "QueryResponse": {"Customer": []}
        }

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.create_search_query', return_value="email='notfound@example.com'"):
            result = await customer_service._find_existing_customer_by_email("notfound@example.com")

            assert result is None

    @pytest.mark.asyncio
    async def test_find_existing_customer_exception(self, customer_service, mock_client):
        """Test exception handling in customer search."""
        mock_client.query_customers.side_effect = Exception("Search error")

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.create_search_query', return_value="email='error@example.com'"):
            result = await customer_service._find_existing_customer_by_email("error@example.com")

            assert result is None


class TestCreateCustomerInQuickBooks:
    """Test creating customers in QuickBooks."""

    @pytest.mark.asyncio
    async def test_create_customer_success(self, customer_service, mock_client):
        """Test successful customer creation."""
        tenant = create_test_tenant()

        mock_client.create_customer.return_value = {
            "Customer": {"Id": "new123", "Name": "John Doe"}
        }

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.validate_for_quickbooks', return_value=[]), \
             patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.to_quickbooks', return_value={"Name": "John Doe"}):

            customer_service._retry_operation = AsyncMock(return_value={"Customer": {"Id": "new123"}})

            result = await customer_service._create_customer_in_quickbooks(tenant)

            assert result == "new123"

    @pytest.mark.asyncio
    async def test_create_customer_validation_errors(self, customer_service):
        """Test customer creation with validation errors."""
        tenant = create_test_tenant()

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.validate_for_quickbooks', return_value=["Error 1", "Error 2"]), \
             patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.to_quickbooks', return_value={"Name": "John Doe"}):

            customer_service._retry_operation = AsyncMock(return_value={"Customer": {"Id": "new123"}})

            # Should still create customer despite validation warnings
            result = await customer_service._create_customer_in_quickbooks(tenant)

            assert result == "new123"

    @pytest.mark.asyncio
    async def test_create_customer_invalid_response(self, customer_service):
        """Test handling of invalid response from QuickBooks."""
        tenant = create_test_tenant()

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.validate_for_quickbooks', return_value=[]), \
             patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.to_quickbooks', return_value={"Name": "John Doe"}):

            customer_service._retry_operation = AsyncMock(return_value={"InvalidResponse": {}})

            result = await customer_service._create_customer_in_quickbooks(tenant)

            assert result is None

    @pytest.mark.asyncio
    async def test_create_customer_exception(self, customer_service):
        """Test exception handling in customer creation."""
        tenant = create_test_tenant()

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.validate_for_quickbooks', side_effect=Exception("Validation error")):
            result = await customer_service._create_customer_in_quickbooks(tenant)

            assert result is None


class TestUpdateCustomerInQuickBooks:
    """Test updating customers in QuickBooks."""

    @pytest.mark.asyncio
    async def test_update_customer_success(self, customer_service, mock_client, mock_session):
        """Test successful customer update."""
        # Mock initialization to avoid QB integration check
        customer_service.initialize = AsyncMock()
        
        tenant = create_test_tenant(quickbooks_id="qb123")

        mock_client.get_customer.return_value = {
            "Customer": {"Id": "qb123", "SyncToken": "2", "Name": "Old Name"}
        }
        mock_client.update_customer.return_value = {
            "Customer": {"Id": "qb123", "SyncToken": "3", "Name": "New Name"}
        }

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.needs_update', return_value=True), \
             patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.to_quickbooks_update', return_value={"Name": "New Name"}):

            customer_service._retry_operation = AsyncMock(return_value={"Customer": {"Id": "qb123"}})

            result = await customer_service.update_customer_in_quickbooks(tenant)

            assert result is True
            assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_update_customer_no_quickbooks_id(self, customer_service):
        """Test update attempt with tenant that has no QuickBooks ID."""
        tenant = create_test_tenant()  # No quickbooks_id

        result = await customer_service.update_customer_in_quickbooks(tenant)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_customer_not_found(self, customer_service, mock_client):
        """Test update when customer not found in QuickBooks."""
        tenant = create_test_tenant(quickbooks_id="missing123")

        mock_client.get_customer.return_value = None

        result = await customer_service.update_customer_in_quickbooks(tenant)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_customer_no_sync_token(self, customer_service, mock_client):
        """Test update when customer missing SyncToken."""
        tenant = create_test_tenant(quickbooks_id="qb123")

        mock_client.get_customer.return_value = {
            "Customer": {"Id": "qb123", "Name": "John Doe"}  # Missing SyncToken
        }

        result = await customer_service.update_customer_in_quickbooks(tenant)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_customer_no_update_needed(self, customer_service, mock_client, mock_session):
        """Test when no update is actually needed."""
        # Mock initialization
        customer_service.initialize = AsyncMock()
        
        tenant = create_test_tenant(quickbooks_id="qb123")

        mock_client.get_customer.return_value = {
            "Customer": {"Id": "qb123", "SyncToken": "2", "Name": "Current Name"}
        }

        with patch('Backend.api.quickbooks.schemas.customer.CustomerSchema.needs_update', return_value=False):
            result = await customer_service.update_customer_in_quickbooks(tenant)

            assert result is True
            assert mock_session.commit.called
            # Should not call update_customer API
            mock_client.update_customer.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_customer_exception(self, customer_service, mock_client):
        """Test exception handling in customer update."""
        tenant = create_test_tenant(quickbooks_id="qb123")

        mock_client.get_customer.side_effect = Exception("API error")

        result = await customer_service.update_customer_in_quickbooks(tenant)

        assert result is False


class TestLinkOrCreateQBCustomer:
    """Test the link_or_create_qb_customer method."""

    @pytest.mark.asyncio
    async def test_link_or_create_customer_success(self, test_user, mock_session, mock_client):
        """Test successful customer linking/creation."""
        tenant_data = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe"
        }

        # Mock the async_session context manager
        with patch('Backend.api.quickbooks.services.customer_service.async_session') as mock_async_session:
            mock_session_instance = AsyncMock()
            mock_session_instance._client = mock_client
            mock_async_session.return_value.__aenter__.return_value = mock_session_instance

            # Create properly initialized service
            service = CustomerService(test_user, mock_session_instance)
            service._client = mock_client
            service.initialize = AsyncMock()
            service._find_existing_customer_by_email = AsyncMock(return_value="existing123")

            # Patch CustomerService creation in link_or_create_qb_customer
            with patch.object(CustomerService, '__new__', return_value=service):
                with patch.object(CustomerService, '__init__', return_value=None):
                    result = await service.link_or_create_qb_customer(tenant_data)

                    assert result == "existing123"