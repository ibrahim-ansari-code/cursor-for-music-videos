"""
Unit tests for the lease retrieval service functions.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.leases.schemas import LeaseResponse
from Backend.models.user import User
from Backend.models.lease import LeaseStatus, Lease
from Backend.models.property import Property
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

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

def create_test_user(user_id=None, email="test@example.com", user_type="LANDLORD"):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=False,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )

def test_get_lease_success(mocker):
    # Arrange
    lease_id = 123
    fake_user = create_test_user()
    
    # Create a mock property
    mock_property = MagicMock(spec=Property)
    mock_property.id = 1
    mock_property.user_id = fake_user.id
    
    # Create a mock Lease ORM object with all required fields
    fake_lease = MagicMock(spec=Lease)
    fake_lease.id = lease_id
    fake_lease.property_id = 1
    fake_lease.tenant_id = 1
    fake_lease.start_date = date(2024, 1, 1)
    fake_lease.end_date = date(2024, 12, 31)
    fake_lease.monthly_rent = Decimal("1500.00")
    fake_lease.security_deposit = Decimal("1500.00")
    fake_lease.status = LeaseStatus.ACTIVE
    fake_lease.created_at = datetime(2024, 1, 1, 0, 0, 0)
    fake_lease.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    fake_lease.tenant = None
    fake_lease.property = mock_property  # Set the property relationship
    fake_lease.unit = None
    
    # Mock all the LeaseBase fields
    fake_lease.is_renewable = True
    fake_lease.auto_renew = False
    fake_lease.rent_due_day = 1
    fake_lease.late_fee_amount = None  # Use None instead of MagicMock
    fake_lease.late_fee_after_days = None
    fake_lease.special_terms = None  # Use None instead of MagicMock
    fake_lease.unit_id = None

    # Mock the check_lease_permission function
    mocker.patch(
        "Backend.api.leases.service.check_lease_permission",
        new=AsyncMock(return_value=fake_lease)
    )

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    # Create test client with proper host header
    with TestClientWithHost(app) as client:
        # Act
        response = client.get(f"/api/leases/{lease_id}")
        
        # Debug output
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            print(f"Response headers: {dict(response.headers)}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == lease_id
        assert data["status"] == "ACTIVE"

def test_get_lease_response_model(mocker):
    lease_id = 456
    fake_user = create_test_user(email="user2@example.com")
    
    # Create a mock Lease ORM object with all required fields
    fake_lease = MagicMock(spec=Lease)
    fake_lease.id = lease_id
    fake_lease.property_id = 2
    fake_lease.tenant_id = 2
    fake_lease.start_date = date(2024, 2, 1)
    fake_lease.end_date = date(2025, 1, 31)
    fake_lease.monthly_rent = Decimal("1800.00")
    fake_lease.security_deposit = Decimal("1800.00")
    fake_lease.status = LeaseStatus.ACTIVE
    fake_lease.created_at = datetime(2024, 2, 1, 0, 0, 0)
    fake_lease.updated_at = datetime(2024, 2, 1, 0, 0, 0)
    fake_lease.tenant = None
    fake_lease.property = None  # Set to None for serialization
    fake_lease.unit = None
    
    # Mock all the LeaseBase fields
    fake_lease.is_renewable = True
    fake_lease.auto_renew = False
    fake_lease.rent_due_day = 1
    fake_lease.late_fee_amount = Decimal("50.00")  # Example with value
    fake_lease.late_fee_after_days = 5
    fake_lease.special_terms = "No pets allowed"  # Example with value
    fake_lease.unit_id = None

    mocker.patch(
        "Backend.api.leases.service.check_lease_permission",
        new=AsyncMock(return_value=fake_lease)
    )

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.get(f"/api/leases/{lease_id}")

        assert response.status_code == 200
        data = response.json()
        # Check that all LeaseResponse fields are present and types are correct
        expected_keys = {
            "id", "property_id", "tenant_id", "start_date", "end_date",
            "monthly_rent", "security_deposit", "status", "created_at", 
            "updated_at", "tenant", "property", "is_renewable", "auto_renew",
            "rent_due_day", "late_fee_amount", "late_fee_after_days", 
            "special_terms", "unit_id"
        }
        assert set(data.keys()).issuperset(expected_keys)
        assert data["id"] == lease_id
        assert data["property_id"] == 2
        assert data["tenant_id"] == 2
        assert data["status"] == "ACTIVE"
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)
        assert data["tenant"] is None
        assert data["property"] is None
        assert data["late_fee_amount"] == "50.00"
        assert data["late_fee_after_days"] == 5
        assert data["special_terms"] == "No pets allowed"

def test_get_lease_not_found(mocker):
    lease_id = 9999
    fake_user = create_test_user(email="notfound@example.com")

    mocker.patch(
        "Backend.api.leases.service.check_lease_permission",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail=f"Lease with ID {lease_id} not found"))
    )

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.get(f"/api/leases/{lease_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

def test_get_lease_permission_denied(mocker):
    lease_id = 321
    fake_user = create_test_user(email="denied@example.com")

    mocker.patch(
        "Backend.api.leases.service.check_lease_permission",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Permission denied"))
    )

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.get(f"/api/leases/{lease_id}")

        assert response.status_code == 403
        assert response.json()["detail"] == "Permission denied"

def test_get_lease_invalid_lease_id(mocker):
    # Create a fake user for auth
    fake_user = create_test_user()
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Non-integer lease_id
        response = client.get("/api/leases/not-an-integer")
        assert response.status_code == 422
        assert "detail" in response.json()
        
        # For negative lease_id, mock the service to return 404
        mocker.patch(
            "Backend.api.leases.service.check_lease_permission",
            new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Lease with ID -5 not found"))
        )
        
        response = client.get("/api/leases/-5")
        # The service should handle negative IDs appropriately
        assert response.status_code == 404

def test_landlord_retrieves_leases_by_property(mocker):
    # Arrange
    landlord_id = uuid4()
    fake_user = create_test_user(user_id=landlord_id, email="landlord@example.com", user_type="LANDLORD")
    property_id = 42

    # Create mock Lease ORM objects
    fake_lease1 = MagicMock(spec=Lease)
    fake_lease1.id = 1
    fake_lease1.property_id = property_id
    fake_lease1.tenant_id = 100
    fake_lease1.start_date = date(2024, 1, 1)
    fake_lease1.end_date = date(2024, 12, 31)
    fake_lease1.monthly_rent = Decimal("2000.00")
    fake_lease1.security_deposit = Decimal("2000.00")
    fake_lease1.status = LeaseStatus.ACTIVE
    fake_lease1.created_at = datetime(2024, 1, 1, 0, 0, 0)
    fake_lease1.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    fake_lease1.tenant = None
    fake_lease1.property = None
    fake_lease1.unit = None
    fake_lease1.is_renewable = True
    fake_lease1.auto_renew = False
    fake_lease1.rent_due_day = 1
    fake_lease1.late_fee_amount = None
    fake_lease1.late_fee_after_days = None
    fake_lease1.special_terms = None
    fake_lease1.unit_id = None

    fake_lease2 = MagicMock(spec=Lease)
    fake_lease2.id = 2
    fake_lease2.property_id = property_id
    fake_lease2.tenant_id = 101
    fake_lease2.start_date = date(2024, 2, 1)
    fake_lease2.end_date = date(2025, 1, 31)
    fake_lease2.monthly_rent = Decimal("2100.00")
    fake_lease2.security_deposit = Decimal("2100.00")
    fake_lease2.status = LeaseStatus.PENDING
    fake_lease2.created_at = datetime(2024, 2, 1, 0, 0, 0)
    fake_lease2.updated_at = datetime(2024, 2, 1, 0, 0, 0)
    fake_lease2.tenant = None
    fake_lease2.property = None
    fake_lease2.unit = None
    fake_lease2.is_renewable = True
    fake_lease2.auto_renew = False
    fake_lease2.rent_due_day = 1
    fake_lease2.late_fee_amount = None
    fake_lease2.late_fee_after_days = None
    fake_lease2.special_terms = None
    fake_lease2.unit_id = None

    fake_leases = [fake_lease1, fake_lease2]

    # Mock the database session and its execute method
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.unique.return_value.all.return_value = fake_leases
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.get(f"/api/leases/?property_id={property_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        for lease in data:
            assert lease["property_id"] == property_id
            assert lease["id"] in [1, 2]
            assert lease["status"] in ["ACTIVE", "PENDING"]

def test_invalid_property_id_returns_empty_list(mocker):
    # Arrange
    fake_user = create_test_user(email="user@example.com", user_type="LANDLORD")
    invalid_property_id = 99999

    # Mock the database session to return empty list
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.unique.return_value.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.get(f"/api/leases/?property_id={invalid_property_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data == []

def test_user_with_no_leases_receives_empty_list(mocker):
    fake_user = create_test_user(email="noleases@example.com", user_type="LANDLORD")

    # Mock the database session to return empty list
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.unique.return_value.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    with TestClientWithHost(app) as client:
        response = client.get("/api/leases/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data == []