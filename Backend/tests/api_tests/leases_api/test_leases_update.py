"""
Unit tests for the lease update service functions using hybrid API testing pattern.
"""
from uuid import uuid4
import pytest
import logging
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status, HTTPException
from datetime import datetime, timezone

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.lease import LeaseStatus
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

logger = logging.getLogger(__name__)

@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()

# Create a custom TestClient that sets the proper host header
class TestClientWithHost(TestClient):
    def request(self, method: str, url, **kwargs):
        # Always add localhost to headers if not present
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)

def create_test_user(user_id=None, email="test@example.com"):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type="LANDLORD",
        is_active=True,
        is_admin=False,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )

def test_update_lease_general_fields_success():
    # Arrange
    lease_id = 123
    update_payload = {
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "monthly_rent": "1500.00",
        "security_deposit": "1000.00",
        "rent_due_day": 1,
        "late_fee_amount": "50.00",
        "late_fee_after_days": 5,
        "special_terms": "No pets allowed"
    }

    # Mock current_user and session dependencies
    mock_user = create_test_user(email="test@example.com")
    
    # Mock update_lease to return a LeaseResponse-like dict
    mock_lease_response = {
        "id": lease_id,
        "status": LeaseStatus.ACTIVE,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-06-01T00:00:00Z",
        "tenant": None,
        "property": None,
        "start_date": update_payload["start_date"],
        "end_date": update_payload["end_date"],
        "monthly_rent": update_payload["monthly_rent"],
        "security_deposit": update_payload["security_deposit"],
        "rent_due_day": update_payload["rent_due_day"],
        "late_fee_amount": update_payload["late_fee_amount"],
        "late_fee_after_days": update_payload["late_fee_after_days"],
        "special_terms": update_payload["special_terms"],
        "property_id": 1,
        "tenant_id": 1,
        "is_renewable": True,
        "auto_renew": False,
        "unit_id": None
    }
    
    with patch("Backend.api.leases.router.update_lease", new=AsyncMock(return_value=mock_lease_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.put(
                f"/api/leases/{lease_id}",
                json=update_payload
            )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    for key in update_payload:
        assert str(data[key]) == str(update_payload[key])
    assert data["id"] == lease_id
    assert data["status"] == LeaseStatus.ACTIVE


def test_update_lease_returns_updated_lease():
    lease_id = 456
    update_payload = {
        "start_date": "2024-02-01",
        "end_date": "2024-11-30",
        "monthly_rent": "2000.00",
        "security_deposit": "1200.00",
        "rent_due_day": 5,
        "late_fee_amount": "75.00",
        "late_fee_after_days": 3,
        "special_terms": "No smoking"
    }
    mock_user = create_test_user(email="user2@example.com")
    
    mock_lease_response = {
        "id": lease_id,
        "status": LeaseStatus.ACTIVE,
        "created_at": "2024-02-01T00:00:00Z",
        "updated_at": "2024-06-02T00:00:00Z",
        "tenant": None,
        "property": None,
        "start_date": update_payload["start_date"],
        "end_date": update_payload["end_date"],
        "monthly_rent": update_payload["monthly_rent"],
        "security_deposit": update_payload["security_deposit"],
        "rent_due_day": update_payload["rent_due_day"],
        "late_fee_amount": update_payload["late_fee_amount"],
        "late_fee_after_days": update_payload["late_fee_after_days"],
        "special_terms": update_payload["special_terms"],
        "property_id": 2,
        "tenant_id": 2,
        "is_renewable": True,
        "auto_renew": False,
        "unit_id": None
    }
    
    with patch("Backend.api.leases.router.update_lease", new=AsyncMock(return_value=mock_lease_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.put(
                f"/api/leases/{lease_id}",
                json=update_payload
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    for key in update_payload:
        assert str(data[key]) == str(update_payload[key])
    assert data["id"] == lease_id
    assert data["status"] == LeaseStatus.ACTIVE


def test_update_lease_nonexistent_lease():
    lease_id = 9999
    update_payload = {
        "start_date": "2024-03-01"
    }
    mock_user = create_test_user(email="user3@example.com")
    
    not_found_exc = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lease not found")
    
    with patch("Backend.api.leases.router.update_lease", new=AsyncMock(side_effect=not_found_exc)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.put(
                f"/api/leases/{lease_id}",
                json=update_payload
            )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Lease not found"


def test_update_lease_insufficient_permissions():
    lease_id = 8888
    update_payload = {
        "monthly_rent": "2500.00"
    }
    mock_user = create_test_user(email="user4@example.com")
    
    forbidden_exc = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    
    with patch("Backend.api.leases.router.update_lease", new=AsyncMock(side_effect=forbidden_exc)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.put(
                f"/api/leases/{lease_id}",
                json=update_payload
            )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Insufficient permissions"


def test_update_lease_invalid_payload_returns_422():
    lease_id = 5555
    # Invalid payload: monthly_rent is a string that cannot be parsed as Decimal, rent_due_day is a string instead of int
    invalid_payload = {
        "monthly_rent": "not-a-decimal",
        "rent_due_day": "not-an-int"
    }
    mock_user = create_test_user(email="user5@example.com")
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.put(
            f"/api/leases/{lease_id}",
            json=invalid_payload
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # FastAPI returns 422 for validation errors, not 400
    # Check that the error mentions the problematic fields safely
    error_detail = response.json()["detail"]
    
    # Safely check for field validation errors
    has_monthly_rent_error = False
    has_rent_due_day_error = False
    
    try:
        for err in error_detail:
            if isinstance(err, dict):
                loc = err.get("loc", [])
                if "monthly_rent" in [str(field) for field in loc]:
                    has_monthly_rent_error = True
                if "rent_due_day" in [str(field) for field in loc]:
                    has_rent_due_day_error = True
    except (TypeError, KeyError, AttributeError):
        # Fallback: check if any error mentions the fields in a generic way
        error_str = str(error_detail).lower()
        has_monthly_rent_error = "monthly_rent" in error_str
        has_rent_due_day_error = "rent_due_day" in error_str
    
    assert has_monthly_rent_error, "Expected validation error for 'monthly_rent' field not found"
    assert has_rent_due_day_error, "Expected validation error for 'rent_due_day' field not found"


def test_update_lease_status_to_active_applies_side_effects():
    lease_id = 101
    status_data = {"status": LeaseStatus.ACTIVE.value}
    mock_user = create_test_user(email="sideeffect@example.com")

    # Mock the side effect function and database operations, but let update_lease_status run
    with patch("Backend.api.leases.service._apply_active_lease_side_effects", new_callable=AsyncMock) as mock_apply_active_side_effects, \
         patch("Backend.api.leases.service.check_lease_permission", new_callable=AsyncMock) as mock_check_permission:
        
        # Mock the lease permission check to return a lease that will trigger the side effects
        mock_lease = {
            "id": lease_id,
            "status": LeaseStatus.PENDING,  # Original status is not ACTIVE
            "tenant_id": 1,
            "property_id": 2,
            "tenant": {"id": 1, "name": "Test Tenant"},
            "property": {"id": 2, "address": "123 Main St"},
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "monthly_rent": "1500.00",
            "security_deposit": "1500.00",
            "is_renewable": True,
            "auto_renew": False,
            "rent_due_day": 1,
            "unit_id": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-06-01T00:00:00Z"
        }
        
        # Create a mock lease object that behaves like a database model
        mock_lease_obj = type('MockLease', (), mock_lease)()
        mock_check_permission.return_value = mock_lease_obj
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.post(
                f"/api/leases/{lease_id}/status",
                json=status_data
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == lease_id
        assert data["status"] == LeaseStatus.ACTIVE.value

        # Verify that the active lease side effects were applied
        mock_apply_active_side_effects.assert_called_once()


def test_update_lease_status_missing_status_returns_422():
    lease_id = 404
    # status_data is missing the "status" field
    status_data = {}

    mock_user = create_test_user(email="missingstatus@example.com")
    
    # Mock the service function to raise validation error
    with patch("Backend.api.leases.router.update_lease_status", new_callable=AsyncMock) as mock_update_lease_status:
        # Make it raise an HTTPException for missing status
        mock_update_lease_status.side_effect = HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Status is required"
        )
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.post(
                f"/api/leases/{lease_id}/status",
                json=status_data
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        detail = response.json()["detail"]
        assert "Status is required" in detail


def test_update_lease_status_from_active_revokes_side_effects():
    lease_id = 202
    status_data = {"status": LeaseStatus.TERMINATED.value}
    mock_user = create_test_user(email="deactivate@example.com")

    # Mock the side effect function and database operations, but let update_lease_status run
    with patch("Backend.api.leases.service._revoke_active_lease_side_effects", new_callable=AsyncMock) as mock_revoke_active_side_effects, \
         patch("Backend.api.leases.service.check_lease_permission", new_callable=AsyncMock) as mock_check_permission:

        # Mock the lease permission check to return a lease that will trigger the revoke side effects
        mock_lease = {
            "id": lease_id,
            "status": LeaseStatus.ACTIVE,  # Original status is ACTIVE, will be changed to TERMINATED
            "tenant_id": 3,
            "property_id": 4,
            "tenant": {"id": 3, "name": "Tenant X"},
            "property": {"id": 4, "address": "456 Elm St"},
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "monthly_rent": "2000.00",
            "security_deposit": "2000.00",
            "is_renewable": True,
            "auto_renew": False,
            "rent_due_day": 1,
            "unit_id": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-06-01T00:00:00Z"
        }
        
        # Create a mock lease object that behaves like a database model
        mock_lease_obj = type('MockLease', (), mock_lease)()
        mock_check_permission.return_value = mock_lease_obj
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.post(
                f"/api/leases/{lease_id}/status",
                json=status_data
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == lease_id
        assert data["status"] == LeaseStatus.TERMINATED.value

        # Verify that the active lease side effects were revoked
        mock_revoke_active_side_effects.assert_called_once()


def test_update_lease_status_returns_updated_lease():
    lease_id = 303
    status_data = {"status": LeaseStatus.PENDING.value}
    mock_user = create_test_user(email="pending@example.com")

    with patch("Backend.api.leases.router.update_lease_status", new_callable=AsyncMock) as mock_update_lease_status:
        lease_obj = {
            "id": lease_id,
            "status": LeaseStatus.PENDING.value,
            "created_at": "2024-04-01T00:00:00Z",
            "updated_at": "2024-06-10T00:00:00Z",
            "tenant": {"id": 5, "name": "Tenant Y"},
            "property": {"id": 6, "address": "789 Oak Ave"},
            "tenant_id": 5,
            "property_id": 6,
            "start_date": "2024-04-01",
            "end_date": "2025-03-31",
            "monthly_rent": "1800.00",
            "security_deposit": "1800.00",
            "is_renewable": True,
            "auto_renew": False,
            "rent_due_day": 1,
            "unit_id": None
        }
        mock_update_lease_status.return_value = lease_obj
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.post(
                f"/api/leases/{lease_id}/status",
                json=status_data
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == lease_id
        assert data["status"] == LeaseStatus.PENDING.value
        assert data["tenant"]["id"] == 5
        assert data["property"]["id"] == 6
        mock_update_lease_status.assert_awaited_once()
        # Check that it was called with the expected arguments
        call_args = mock_update_lease_status.call_args
        assert call_args is not None
        assert call_args.args[0] == lease_id
        assert call_args.args[1] == status_data
        assert call_args.args[2] == mock_user
