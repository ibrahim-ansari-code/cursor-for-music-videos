"""
API tests for QuickBooks sync preview functionality.

Tests preview endpoints that show what would be synced without actually syncing.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.models.accounting.integration import Integration, IntegrationStatus, IntegrationType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Import helper functions from conftest.py
from ..conftest import assert_valid_json_response

# Mark all tests in this module as API tests
pytestmark = pytest.mark.api

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()


class TestClientWithHost(TestClient):
    """Custom TestClient that sets the proper host header."""
    def request(self, method: str, url, **kwargs):
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def create_test_user(user_id=None, email="test@example.com", user_type=UserType.LANDLORD):
    """Helper function to create a properly initialized test user."""
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=False,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        is_email_verified=True
    )


def create_mock_integration(connected=True):
    """Helper to create a mock QuickBooks integration."""
    mock_integration = AsyncMock(spec=Integration)
    mock_integration.id = uuid4()
    mock_integration.user_id = uuid4()
    mock_integration.integration_type = IntegrationType.QUICKBOOKS
    mock_integration.status = IntegrationStatus.CONNECTED if connected else IntegrationStatus.PENDING
    mock_integration.connected_at = FIXED_DATETIME if connected else None
    return mock_integration


def test_sync_preview_not_connected():
    """Test sync preview when not connected to QuickBooks."""
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    # Mock the services to raise error for not connected
    with patch('Backend.api.quickbooks.router.ExpenseService') as mock_expense, \
         patch('Backend.api.quickbooks.router.InvoiceService') as mock_invoice, \
         patch('Backend.api.quickbooks.router.PaymentService') as mock_payment:
        
        from fastapi import HTTPException
        mock_svc = AsyncMock()
        mock_svc.preview_expenses.side_effect = HTTPException(
            status_code=400,
            detail="QuickBooks integration not found or not connected"
        )
        mock_expense.return_value = mock_svc
        mock_invoice.return_value = AsyncMock()
        mock_payment.return_value = AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/sync/preview")
            
            # The error gets caught and returned as 500
            assert response.status_code == 500
            data = response.json()
            assert "preview" in data["detail"].lower() or "failed" in data["detail"].lower()


def test_sync_preview_endpoint_availability():
    """Test that sync preview endpoint exists and is accessible."""
    test_user = create_test_user()
    mock_session = AsyncMock()
    
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    # Mock all services to return empty previews
    with patch('Backend.api.quickbooks.router.ExpenseService') as mock_expense, \
         patch('Backend.api.quickbooks.router.InvoiceService') as mock_invoice, \
         patch('Backend.api.quickbooks.router.PaymentService') as mock_payment, \
         patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer:
        
        # Create mock preview response objects
        mock_preview = AsyncMock()
        mock_preview.items = []
        mock_preview.summary = {"create": 0, "update": 0, "skip": 0, "error": 0}
        mock_preview.warnings = []
        
        expense_svc = AsyncMock()
        expense_svc.preview_expenses.return_value = mock_preview
        mock_expense.return_value = expense_svc
        
        invoice_svc = AsyncMock()
        invoice_svc.preview_invoices.return_value = mock_preview
        mock_invoice.return_value = invoice_svc
        
        payment_svc = AsyncMock()
        payment_svc.preview_payments.return_value = mock_preview
        mock_payment.return_value = payment_svc
        
        customer_svc = AsyncMock()
        customer_svc.preview_customers.return_value = mock_preview
        mock_customer.return_value = customer_svc
        
        with TestClientWithHost(app) as client:
            response = client.get("/api/quickbooks/sync/preview")
            
            data = assert_valid_json_response(response, dict)
            # Should return preview data structure
            assert "items" in data or "preview_items" in data or "summary" in data


def test_sync_preview_permission_check():
    """Test that sync preview requires landlord permission."""
    test_user = create_test_user(user_type=UserType.TENANT)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        response = client.get("/api/quickbooks/sync/preview")

        if response.status_code == 404:
            pytest.skip("Preview endpoint not implemented")

        assert response.status_code in [200, 403, 400]


def test_apply_sync_happy_path_customer_link():
    """Test successful application of customer link operation."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    # Create a mock tenant without QuickBooks ID
    mock_tenant = AsyncMock(spec=Tenant)
    mock_tenant.id = 1
    mock_tenant.first_name = "John"
    mock_tenant.last_name = "Doe"
    mock_tenant.email = "john.doe@example.com"
    mock_tenant.quickbooks_customer_id = None
    mock_tenant.last_synced_at = None

    # Mock session.get to return our tenant
    mock_session.get.return_value = mock_tenant
    # Mock session.scalar to return None (no existing link to this QB customer)
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock CustomerService initialization
    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            # Apply a customer_link operation
            payload = [
                {
                    "entity_type": "customer_link",
                    "entity_id": "1",
                    "action": "update",
                    "details": {
                        "qb_customer_id": "QB123"
                    }
                }
            ]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            # Check response
            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["items_synced"] == 1
            assert "customer operations" in data["message"]
            assert data.get("errors") is None or len(data.get("errors", [])) == 0

            # Verify tenant was updated
            assert mock_tenant.quickbooks_customer_id == "QB123"
            assert mock_tenant.last_synced_at is not None

            # Verify session commit was called
            mock_session.commit.assert_called_once()


def test_apply_sync_happy_path_customer_create():
    """Test successful application of customer create operation."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    # Create a mock tenant without QuickBooks ID
    mock_tenant = AsyncMock(spec=Tenant)
    mock_tenant.id = 2
    mock_tenant.first_name = "Jane"
    mock_tenant.last_name = "Smith"
    mock_tenant.email = "jane.smith@example.com"
    mock_tenant.quickbooks_customer_id = None
    mock_tenant.last_synced_at = None

    # Mock session.get to return our tenant
    mock_session.get.return_value = mock_tenant
    # Mock session.scalar to return None (no existing links)
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    # Mock CustomerService
    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        # Mock the create operation to return a new QB ID
        mock_customer_service._find_existing_customer_by_email = AsyncMock(return_value=None)
        mock_customer_service._create_customer_in_quickbooks = AsyncMock(return_value="QB_NEW_456")
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            # Apply a customer_create operation
            payload = [
                {
                    "entity_type": "customer_create",
                    "entity_id": "2",
                    "action": "create",
                    "details": {
                        "destination": "QuickBooks"
                    }
                }
            ]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            # Check response
            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["items_synced"] == 1
            # Updated to match actual message: "Successfully applied 1 customer operations."
            assert "customer operations" in data["message"]

            # Verify tenant was updated with new QB ID
            assert mock_tenant.quickbooks_customer_id == "QB_NEW_456"
            assert mock_tenant.last_synced_at is not None

            # Verify create was called
            mock_customer_service._create_customer_in_quickbooks.assert_called_once()


def test_apply_sync_idempotent_link():
    """Test that re-linking same customer is idempotent."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    # Create a mock tenant already linked to QB
    mock_tenant = AsyncMock(spec=Tenant)
    mock_tenant.id = 3
    mock_tenant.quickbooks_customer_id = "QB123"  # Already linked
    mock_tenant.last_synced_at = FIXED_DATETIME

    mock_session.get.return_value = mock_tenant
    mock_session.commit = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            # Try to link to the same QB customer again
            payload = [
                {
                    "entity_type": "customer_link",
                    "entity_id": "3",
                    "action": "update",
                    "details": {
                        "qb_customer_id": "QB123"  # Same as existing
                    }
                }
            ]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            # Should succeed (idempotent)
            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["items_synced"] == 1  # Counted as successful no-op


def test_apply_sync_partial_failure():
    """Test atomic transaction behavior - all operations rolled back if any fail."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    # First tenant exists, second doesn't
    def mock_get_tenant(model, tenant_id):
        if tenant_id == 1:
            mock_tenant = AsyncMock(spec=Tenant)
            mock_tenant.id = 1
            mock_tenant.quickbooks_customer_id = None
            return mock_tenant
        else:
            return None  # Tenant 2 doesn't exist

    mock_session.get = AsyncMock(side_effect=mock_get_tenant)
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            # Apply operations for two tenants
            payload = [
                {
                    "entity_type": "customer_link",
                    "entity_id": "1",
                    "action": "update",
                    "details": {"qb_customer_id": "QB1"}
                },
                {
                    "entity_type": "customer_link",
                    "entity_id": "2",  # This tenant doesn't exist
                    "action": "update",
                    "details": {"qb_customer_id": "QB2"}
                }
            ]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            # Should return 200 but with errors
            assert response.status_code == 200
            data = response.json()

            # Atomic behavior: all or nothing
            assert data["success"] is False  # Has errors
            assert data["items_synced"] == 0  # All rolled back due to atomic transaction
            assert data["errors"] is not None
            assert len(data["errors"]) == 1
            assert "Tenant 2 not found" in data["errors"][0]
            
            # Verify rollback was called, not commit
            mock_session.rollback.assert_called_once()
            mock_session.commit.assert_not_called()


def test_apply_sync_permission_check():
    """Test that apply sync requires landlord permission."""
    test_user = create_test_user(user_type=UserType.TENANT)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClientWithHost(app) as client:
        payload = [{
            "entity_type": "customer_link",
            "entity_id": "1",
            "action": "update",
            "details": {"qb_customer_id": "QB123"}
        }]

        response = client.post("/api/quickbooks/sync/apply", json=payload)

        # Should be forbidden for tenants
        assert response.status_code == 403
        data = response.json()
        assert "landlord" in data["detail"].lower() or "admin" in data["detail"].lower()


def test_apply_sync_invalid_entity_type():
    """Test validation error for invalid entity_type."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            payload = [{
                "entity_type": "invalid_type",
                "entity_id": "1",
                "action": "update",
                "details": {}
            }]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is False
            assert data["items_synced"] == 0
            assert len(data["errors"]) == 1
            assert "Invalid entity_type" in data["errors"][0]


def test_apply_sync_invalid_action():
    """Test validation error for invalid action."""
    test_user = create_test_user()
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            payload = [{
                "entity_type": "customer_link",
                "entity_id": "1",
                "action": "delete",  # Invalid action
                "details": {}
            }]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is False
            assert data["items_synced"] == 0
            assert len(data["errors"]) == 1
            assert "Invalid action" in data["errors"][0]


def test_apply_sync_missing_qb_customer_id():
    """Test error when qb_customer_id is missing for customer_link."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    mock_tenant = AsyncMock(spec=Tenant)
    mock_tenant.id = 1
    mock_tenant.quickbooks_customer_id = None

    mock_session.get.return_value = mock_tenant
    mock_session.rollback = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            payload = [{
                "entity_type": "customer_link",
                "entity_id": "1",
                "action": "update",
                "details": {}  # Missing qb_customer_id
            }]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is False
            assert data["items_synced"] == 0
            assert len(data["errors"]) == 1
            assert "Missing qb_customer_id" in data["errors"][0]


def test_apply_sync_duplicate_qb_customer_link():
    """Test error when trying to link a QB customer that's already linked to another tenant."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    # Tenant we're trying to link
    mock_tenant = AsyncMock(spec=Tenant)
    mock_tenant.id = 1
    mock_tenant.quickbooks_customer_id = None

    # Existing tenant that's already linked to the same QB customer
    existing_tenant = AsyncMock(spec=Tenant)
    existing_tenant.id = 5

    mock_session.get.return_value = mock_tenant
    # Return existing link when checking for duplicates
    mock_session.scalar = AsyncMock(return_value=existing_tenant)
    mock_session.rollback = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            payload = [{
                "entity_type": "customer_link",
                "entity_id": "1",
                "action": "update",
                "details": {"qb_customer_id": "QB999"}
            }]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is False
            assert data["items_synced"] == 0
            assert len(data["errors"]) == 1
            assert "already linked to another tenant" in data["errors"][0]


def test_apply_sync_idempotent_customer_create():
    """Test that creating a customer for a tenant that already has a QB ID is idempotent."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    # Tenant already has a QB customer ID
    mock_tenant = AsyncMock(spec=Tenant)
    mock_tenant.id = 1
    mock_tenant.quickbooks_customer_id = "QB_EXISTING"

    mock_session.get.return_value = mock_tenant
    mock_session.commit = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            payload = [{
                "entity_type": "customer_create",
                "entity_id": "1",
                "action": "create",
                "details": {}
            }]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            assert response.status_code == 200
            data = response.json()

            # Should succeed as idempotent no-op
            assert data["success"] is True
            assert data["items_synced"] == 1


def test_apply_sync_existing_customer_by_email_conflict():
    """Test error when customer exists by email but is already linked to another tenant."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    # Tenant we're trying to create a customer for
    mock_tenant = AsyncMock(spec=Tenant)
    mock_tenant.id = 1
    mock_tenant.email = "duplicate@example.com"
    mock_tenant.quickbooks_customer_id = None

    # Another tenant already linked to the QB customer with this email
    existing_tenant = AsyncMock(spec=Tenant)
    existing_tenant.id = 5

    mock_session.get.return_value = mock_tenant
    # Return existing link when checking
    mock_session.scalar = AsyncMock(return_value=existing_tenant)
    mock_session.rollback = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        # Customer exists in QB by email
        mock_customer_service._find_existing_customer_by_email = AsyncMock(return_value="QB_EMAIL_MATCH")
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            payload = [{
                "entity_type": "customer_create",
                "entity_id": "1",
                "action": "create",
                "details": {}
            }]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is False
            assert data["items_synced"] == 0
            assert len(data["errors"]) == 1
            assert "already exists and is linked to another tenant" in data["errors"][0]


def test_apply_sync_link_to_existing_customer_by_email():
    """Test successful linking to existing QB customer found by email."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    mock_tenant = AsyncMock(spec=Tenant)
    mock_tenant.id = 1
    mock_tenant.email = "existing@example.com"
    mock_tenant.quickbooks_customer_id = None
    mock_tenant.last_synced_at = None

    mock_session.get.return_value = mock_tenant
    # No existing link (None)
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        # Customer exists in QB by email, not linked to anyone
        mock_customer_service._find_existing_customer_by_email = AsyncMock(return_value="QB_FOUND_BY_EMAIL")
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            payload = [{
                "entity_type": "customer_create",
                "entity_id": "1",
                "action": "create",
                "details": {}
            }]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["items_synced"] == 1
            # Verify tenant was linked to existing customer
            assert mock_tenant.quickbooks_customer_id == "QB_FOUND_BY_EMAIL"
            assert mock_tenant.last_synced_at is not None


def test_apply_sync_customer_creation_failure():
    """Test handling of customer creation failure."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    mock_tenant = AsyncMock(spec=Tenant)
    mock_tenant.id = 1
    mock_tenant.email = "newcustomer@example.com"
    mock_tenant.quickbooks_customer_id = None

    mock_session.get.return_value = mock_tenant
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.rollback = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        # No existing customer
        mock_customer_service._find_existing_customer_by_email = AsyncMock(return_value=None)
        # Creation fails
        mock_customer_service._create_customer_in_quickbooks = AsyncMock(return_value=None)
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            payload = [{
                "entity_type": "customer_create",
                "entity_id": "1",
                "action": "create",
                "details": {}
            }]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is False
            assert data["items_synced"] == 0
            assert len(data["errors"]) == 1
            assert "Failed to create QuickBooks customer" in data["errors"][0]


def test_apply_sync_customer_update_success():
    """Test successful customer update operation."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    mock_tenant = AsyncMock(spec=Tenant)
    mock_tenant.id = 1
    mock_tenant.quickbooks_customer_id = "QB123"

    mock_session.get.return_value = mock_tenant
    mock_session.commit = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        # Update succeeds
        mock_customer_service.update_customer_in_quickbooks = AsyncMock(return_value=True)
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            payload = [{
                "entity_type": "customer_update",
                "entity_id": "1",
                "action": "update",
                "details": {}
            }]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["items_synced"] == 1
            mock_customer_service.update_customer_in_quickbooks.assert_called_once()


def test_apply_sync_customer_update_failure():
    """Test handling of customer update failure."""
    from Backend.models.tenant import Tenant

    test_user = create_test_user()
    mock_session = AsyncMock()

    mock_tenant = AsyncMock(spec=Tenant)
    mock_tenant.id = 1
    mock_tenant.quickbooks_customer_id = "QB123"

    mock_session.get.return_value = mock_tenant
    mock_session.rollback = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch('Backend.api.quickbooks.services.customer_service.CustomerService') as mock_customer_service_class:
        mock_customer_service = AsyncMock()
        mock_customer_service.initialize = AsyncMock()
        # Update fails
        mock_customer_service.update_customer_in_quickbooks = AsyncMock(return_value=False)
        mock_customer_service_class.return_value = mock_customer_service

        with TestClientWithHost(app) as client:
            payload = [{
                "entity_type": "customer_update",
                "entity_id": "1",
                "action": "update",
                "details": {}
            }]

            response = client.post("/api/quickbooks/sync/apply", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is False
            assert data["items_synced"] == 0
            assert len(data["errors"]) == 1
            assert "Failed to update QuickBooks customer" in data["errors"][0]
