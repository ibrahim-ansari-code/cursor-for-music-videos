"""
Unit and Integration tests for the bulk property deletion endpoint.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status, HTTPException
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.tenant import Tenant
from Backend.api.auth import get_current_user
from Backend.database import get_session
from ..base_test import BasePropertyTest, TestClientWithHost, create_test_user

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()


# --- API Contract Tests (mocking the service layer) ---

def test_bulk_delete_properties_success_contract():
    """Tests successful bulk deletion of properties (API contract)."""
    # Arrange
    mock_user = create_test_user()
    property_ids = [1, 2, 3]

    with patch("Backend.api.properties.service.PropertyService.bulk_delete_properties", new_callable=AsyncMock) as mock_bulk_delete:
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.request("DELETE", "/api/properties/bulk-delete-property", json={"property_ids": property_ids})

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_bulk_delete.assert_awaited_once()
        call_args = mock_bulk_delete.call_args
        assert call_args.args[0] == property_ids
        assert call_args.args[1] == mock_user


def test_bulk_delete_handles_empty_list_contract():
    """Tests that the endpoint handles an empty list of IDs gracefully (API contract)."""
    # Arrange
    mock_user = create_test_user()
    property_ids = []

    with patch("Backend.api.properties.service.PropertyService.bulk_delete_properties", new_callable=AsyncMock):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.request("DELETE", "/api/properties/bulk-delete-property", json={"property_ids": property_ids})

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_bulk_delete_not_found_error_contract():
    """Tests failure when one or more properties are not found (API contract)."""
    # Arrange
    mock_user = create_test_user()
    property_ids = [1, 999]

    with patch(
        "Backend.api.properties.service.PropertyService.bulk_delete_properties",
        new_callable=AsyncMock,
        side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more properties not found or you do not have permission to delete them."
        )
    ) as mock_bulk_delete:
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.request("DELETE", "/api/properties/bulk-delete-property", json={"property_ids": property_ids})

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "One or more properties not found" in response.json()["detail"]
        mock_bulk_delete.assert_awaited_once()


def test_bulk_delete_active_associations_forbidden_contract():
    """Tests failure when attempting to delete properties with active associations (API contract)."""
    # Arrange
    mock_user = create_test_user()
    property_ids = [1, 2]

    with patch(
        "Backend.api.properties.service.PropertyService.bulk_delete_properties",
        new_callable=AsyncMock,
        side_effect=HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The following properties are currently active and cannot be deleted: Property 1, Property 2. Please terminate or cancel all active leases, vacate all rented units, and remove tenant associations before deleting these properties."
        )
    ) as mock_bulk_delete:
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.request("DELETE", "/api/properties/bulk-delete-property", json={"property_ids": property_ids})

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "currently active and cannot be deleted" in response.json()["detail"]
        mock_bulk_delete.assert_awaited_once()


def test_bulk_delete_unauthenticated():
    """Tests that the endpoint requires authentication."""
    # Arrange
    app.dependency_overrides.clear()

    with TestClientWithHost(app) as client:
        # Act
        response = client.request("DELETE", "/api/properties/bulk-delete-property", json={"property_ids": [1, 2]})

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_bulk_delete_handles_internal_server_error_contract():
    """Tests the endpoint's response to an unexpected server error (API contract)."""
    # Arrange
    mock_user = create_test_user()
    property_ids = [1, 2]

    with patch(
        "Backend.api.properties.service.PropertyService.bulk_delete_properties",
        new_callable=AsyncMock,
        side_effect=Exception("A critical database error occurred")
    ) as mock_bulk_delete:
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app, raise_server_exceptions=False) as client:
            # Act
            response = client.request("DELETE", "/api/properties/bulk-delete-property", json={"property_ids": property_ids})

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to bulk delete properties" in response.json()["detail"]
        mock_bulk_delete.assert_awaited_once()


# --- Integration Logic Tests (testing the service function's logic) ---

from Backend.api.properties.service import PropertyService

@pytest.mark.asyncio
async def test_bulk_delete_properties_success_integration():
    """Tests successful bulk deletion of multiple properties owned by the user."""
    # Arrange
    user = create_test_user()
    property1 = Property(id=1, name="Property 1", address="123 St", city="City", province="Province", postal_code="12345", property_type="Residential", user_id=user.id, status="ACTIVE", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    property2 = Property(id=2, name="Property 2", address="456 St", city="City", province="Province", postal_code="12345", property_type="Residential", user_id=user.id, status="ACTIVE", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    
    # Mock the database session and its methods
    mock_session = AsyncMock()
    
    # Mock properties result
    mock_properties_result = MagicMock()
    mock_properties_scalars = MagicMock()
    mock_properties_scalars.all.return_value = [property1, property2]
    mock_properties_result.scalars.return_value = mock_properties_scalars
    
    # Mock empty results for all checks
    mock_empty_result = MagicMock()
    mock_empty_scalars = MagicMock()
    mock_empty_scalars.all.return_value = []
    mock_empty_result.scalars.return_value = mock_empty_scalars
    
    mock_session.execute.side_effect = [
        mock_properties_result,  # Get properties
        mock_empty_result,       # Check active leases
        mock_empty_result,       # Check rented units
        mock_empty_result,       # Check tenants
        mock_empty_result,       # Check terminated leases
    ]

    # Act
    await PropertyService.bulk_delete_properties(property_ids=[1, 2], current_user=user, session=mock_session)

    # Assert
    assert mock_session.delete.call_count == 2
    mock_session.delete.assert_any_call(property1)
    mock_session.delete.assert_any_call(property2)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_properties_not_found_integration():
    """Tests that an exception is raised if some properties are not found."""
    # Arrange
    user = create_test_user()
    property1 = Property(id=1, name="Property 1", address="123 St", city="City", province="Province", postal_code="12345", property_type="Residential", user_id=user.id, status="ACTIVE", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [property1]  # Only returns one property
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await PropertyService.bulk_delete_properties(property_ids=[1, 999], current_user=user, session=mock_session)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "One or more properties not found" in exc_info.value.detail
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_properties_active_lease_forbidden_integration():
    """Tests that deleting properties with active leases is forbidden."""
    # Arrange
    user = create_test_user()
    property1 = Property(id=1, name="Property 1", address="123 St", city="City", province="Province", postal_code="12345", property_type="Residential", user_id=user.id, status="ACTIVE", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    property2 = Property(id=2, name="Property 2", address="456 St", city="City", province="Province", postal_code="12345", property_type="Residential", user_id=user.id, status="ACTIVE", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    
    active_lease = Lease(id=1, property_id=2, status=LeaseStatus.ACTIVE)
    
    mock_session = AsyncMock()
    
    # First call: get properties
    mock_properties_result = MagicMock()
    mock_properties_scalars = MagicMock()
    mock_properties_scalars.all.return_value = [property1, property2]
    mock_properties_result.scalars.return_value = mock_properties_scalars
    
    # Second call: check active leases - returns property_ids as rows
    mock_lease_result = MagicMock()
    mock_lease_result.all.return_value = [(2,)]  # Returns property_id 2 as a row tuple
    
    # Third call: check rented units (empty)
    mock_units_result = MagicMock()
    mock_units_result.all.return_value = []
    
    # Fourth call: check tenants (empty)
    mock_tenants_result = MagicMock()
    mock_tenants_result.all.return_value = []
    
    # Note: We don't include the terminated leases check because we fail early on active leases
    mock_session.execute.side_effect = [mock_properties_result, mock_lease_result, mock_units_result, mock_tenants_result]

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await PropertyService.bulk_delete_properties(property_ids=[1, 2], current_user=user, session=mock_session)
        
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "currently active and cannot be deleted" in exc_info.value.detail
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_properties_rented_units_forbidden_integration():
    """Tests that deleting properties with rented units is forbidden."""
    # Arrange
    user = create_test_user()
    property1 = Property(id=1, name="Property 1", address="123 St", city="City", province="Province", postal_code="12345", property_type="Residential", user_id=user.id, status="ACTIVE", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    
    rented_unit = PropertyUnit(id=1, property_id=1, name="Unit 1", is_rented=True)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    # First call: get properties
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [property1]
    mock_result.scalars.return_value = mock_scalars
    
    # Second call: check active leases (empty)
    mock_lease_result = MagicMock()
    mock_lease_result.all.return_value = []
    
    # Third call: check rented units - returns property_id as row
    mock_units_result = MagicMock()
    mock_units_result.all.return_value = [(1,)]  # Returns property_id 1 as a row tuple
    
    # Fourth call: check tenants (empty)
    mock_tenants_result = MagicMock()
    mock_tenants_result.all.return_value = []
    
    mock_session.execute.side_effect = [mock_result, mock_lease_result, mock_units_result, mock_tenants_result]

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await PropertyService.bulk_delete_properties(property_ids=[1], current_user=user, session=mock_session)
        
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "currently active and cannot be deleted" in exc_info.value.detail
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_properties_tenants_association_forbidden_integration():
    """Tests that deleting properties with tenant associations is forbidden."""
    # Arrange
    user = create_test_user()
    property1 = Property(id=1, name="Property 1", address="123 St", city="City", province="Province", postal_code="12345", property_type="Residential", user_id=user.id, status="ACTIVE", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    
    tenant = Tenant(id=1, current_property_id=1, landlord_id=user.id, tenant_type="INDIVIDUAL", status="ACTIVE", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    # First call: get properties
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [property1]
    mock_result.scalars.return_value = mock_scalars
    
    # Second call: check active leases (empty)
    mock_lease_result = MagicMock()
    mock_lease_result.all.return_value = []
    
    # Third call: check rented units (empty)
    mock_units_result = MagicMock()
    mock_units_result.all.return_value = []
    
    # Fourth call: check tenants - returns property_id as row
    mock_tenants_result = MagicMock()
    mock_tenants_result.all.return_value = [(1,)]  # Returns property_id 1 as a row tuple
    
    mock_session.execute.side_effect = [mock_result, mock_lease_result, mock_units_result, mock_tenants_result]

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await PropertyService.bulk_delete_properties(property_ids=[1], current_user=user, session=mock_session)
        
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "currently active and cannot be deleted" in exc_info.value.detail
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_properties_unauthorized_owner_integration():
    """Tests that a landlord cannot delete properties they do not own."""
    # Arrange
    user = create_test_user(user_id=uuid4())  # Landlord
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []  # Simulates no properties found for this user
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await PropertyService.bulk_delete_properties(property_ids=[1, 2], current_user=user, session=mock_session)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_properties_admin_success_integration():
    """Tests that an admin can delete any property."""
    # Arrange
    admin_user = create_test_user()
    admin_user.is_admin = True
    property1 = Property(id=1, name="Property 1", address="123 St", city="City", province="Province", postal_code="12345", property_type="Residential", user_id=uuid4(), status="ACTIVE", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    property2 = Property(id=2, name="Property 2", address="456 St", city="City", province="Province", postal_code="12345", property_type="Residential", user_id=uuid4(), status="ACTIVE", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [property1, property2]
    
    # Mock all subsequent queries (leases, units, tenants, terminated leases) to return empty
    mock_empty_result = MagicMock()
    mock_empty_scalars = MagicMock()
    mock_empty_scalars.all.return_value = []
    mock_empty_result.scalars.return_value = mock_empty_scalars
    
    mock_session.execute.side_effect = [mock_result, mock_empty_result, mock_empty_result, mock_empty_result, mock_empty_result]

    # Act
    await PropertyService.bulk_delete_properties(property_ids=[1, 2], current_user=admin_user, session=mock_session)

    # Assert
    assert mock_session.delete.call_count == 2
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_handles_foreign_key_conflict_integration():
    """Tests that a foreign key violation during deletion is handled."""
    # Arrange
    user = create_test_user()
    property1 = Property(id=1, name="Property 1", address="123 St", city="City", province="Province", postal_code="12345", property_type="Residential", user_id=user.id, status="ACTIVE", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [property1]
    
    # Mock all subsequent queries (leases, units, tenants, terminated leases) to return empty
    mock_empty_result = MagicMock()
    mock_empty_scalars = MagicMock()
    mock_empty_scalars.all.return_value = []
    mock_empty_result.scalars.return_value = mock_empty_scalars
    
    mock_session.execute.side_effect = [mock_result, mock_empty_result, mock_empty_result, mock_empty_result, mock_empty_result]
    mock_session.commit.side_effect = Exception("violates foreign key constraint")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await PropertyService.bulk_delete_properties(property_ids=[1], current_user=user, session=mock_session)
        
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "associated records" in exc_info.value.detail
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_empty_list():
    """Tests that an empty list raises an error."""
    # Arrange
    user = create_test_user()
    mock_session = AsyncMock()

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await PropertyService.bulk_delete_properties(property_ids=[], current_user=user, session=mock_session)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "cannot be empty" in exc_info.value.detail

