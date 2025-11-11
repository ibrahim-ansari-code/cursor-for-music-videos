"""
Unit and Integration tests for the bulk lease deletion endpoint.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status, HTTPException
from uuid import uuid4
from datetime import datetime, timezone, date

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.api.auth import get_current_user
from Backend.database import get_session
from .test_leases_delete import TestClientWithHost, create_test_user

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()

# --- API Contract Tests (mocking the service layer) ---

def test_bulk_delete_leases_success_contract():
    """Tests successful bulk deletion of leases (API contract)."""
    # Arrange
    mock_user = create_test_user()
    lease_ids = [1, 2, 3]

    with patch("Backend.api.leases.router.bulk_delete_leases", new_callable=AsyncMock) as mock_bulk_delete:
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.request("DELETE", "/api/leases/bulk-lease-delete", json={"lease_ids": lease_ids})

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_bulk_delete.assert_awaited_once()
        call_args = mock_bulk_delete.call_args
        assert call_args.args[0] == lease_ids
        assert call_args.args[1] == mock_user


def test_bulk_delete_handles_empty_list_contract():
    """Tests that the endpoint handles an empty list of IDs gracefully (API contract)."""
    # Arrange
    mock_user = create_test_user()
    lease_ids = []

    with patch("Backend.api.leases.router.bulk_delete_leases", new_callable=AsyncMock):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.request("DELETE", "/api/leases/bulk-lease-delete", json={"lease_ids": lease_ids})

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_bulk_delete_not_found_error_contract():
    """Tests failure when one or more leases are not found (API contract)."""
    # Arrange
    mock_user = create_test_user()
    lease_ids = [1, 999]

    with patch(
        "Backend.api.leases.router.bulk_delete_leases",
        new_callable=AsyncMock,
        side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more leases not found or you do not have permission to delete them."
        )
    ) as mock_bulk_delete:
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.request("DELETE", "/api/leases/bulk-lease-delete", json={"lease_ids": lease_ids})

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "One or more leases not found" in response.json()["detail"]
        mock_bulk_delete.assert_awaited_once()


def test_bulk_delete_active_lease_forbidden_contract():
    """Tests failure when attempting to delete an active lease (API contract)."""
    # Arrange
    mock_user = create_test_user()
    lease_ids = [1, 2]

    with patch(
        "Backend.api.leases.router.bulk_delete_leases",
        new_callable=AsyncMock,
        side_effect=HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete active leases: 2. Please terminate them first."
        )
    ) as mock_bulk_delete:
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.request("DELETE", "/api/leases/bulk-lease-delete", json={"lease_ids": lease_ids})

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Cannot delete active leases" in response.json()["detail"]
        mock_bulk_delete.assert_awaited_once()


def test_bulk_delete_unauthenticated():
    """Tests that the endpoint requires authentication."""
    # Arrange
    app.dependency_overrides.clear()

    with TestClientWithHost(app) as client:
        # Act
        response = client.request("DELETE", "/api/leases/bulk-lease-delete", json={"lease_ids": [1, 2]})

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_bulk_delete_handles_internal_server_error_contract():
    """Tests the endpoint's response to an unexpected server error (API contract)."""
    # Arrange
    mock_user = create_test_user()
    lease_ids = [1, 2]

    with patch(
        "Backend.api.leases.router.bulk_delete_leases",
        new_callable=AsyncMock,
        side_effect=Exception("A critical database error occurred")
    ) as mock_bulk_delete:
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app, raise_server_exceptions=False) as client:
            # Act
            response = client.request("DELETE", "/api/leases/bulk-lease-delete", json={"lease_ids": lease_ids})

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Internal Server Error" in response.text
        mock_bulk_delete.assert_awaited_once()

# --- Integration Logic Tests (testing the service function's logic) ---

from Backend.api.leases.service import bulk_delete_leases

@pytest.mark.asyncio
async def test_bulk_delete_leases_success_integration():
    """Tests successful bulk deletion of multiple leases owned by the user."""
    # Arrange
    user = create_test_user()
    lease1 = Lease(id=1, property_id=10, status=LeaseStatus.TERMINATED, start_date=date(2023, 1, 1), end_date=date(2023, 12, 31), monthly_rent=1000, security_deposit=500, tenant_id=1)
    lease2 = Lease(id=2, property_id=10, status=LeaseStatus.DRAFT, start_date=date(2023, 1, 1), end_date=date(2023, 12, 31), monthly_rent=1000, security_deposit=500, tenant_id=1)
    
    # Mock the database session and its methods
    mock_session = AsyncMock()
    mock_result = MagicMock()
    # For the query that checks ownership
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [lease1, lease2]
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    # Act
    await bulk_delete_leases(lease_ids=[1, 2], current_user=user, session=mock_session)

    # Assert
    assert mock_session.delete.call_count == 2
    mock_session.delete.assert_any_call(lease1)
    mock_session.delete.assert_any_call(lease2)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_leases_not_found_integration():
    """Tests that an exception is raised if some leases are not found."""
    # Arrange
    user = create_test_user()
    lease1 = Lease(id=1, property_id=10, status=LeaseStatus.TERMINATED, start_date=date(2023, 1, 1), end_date=date(2023, 12, 31), monthly_rent=1000, security_deposit=500, tenant_id=1)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [lease1] # Only returns one lease
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await bulk_delete_leases(lease_ids=[1, 999], current_user=user, session=mock_session)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "One or more leases not found" in exc_info.value.detail
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_leases_active_lease_forbidden_integration():
    """Tests that deleting an active lease is forbidden."""
    # Arrange
    user = create_test_user()
    lease1 = Lease(id=1, property_id=10, status=LeaseStatus.TERMINATED, start_date=date(2023, 1, 1), end_date=date(2023, 12, 31), monthly_rent=1000, security_deposit=500, tenant_id=1)
    lease2 = Lease(id=2, property_id=10, status=LeaseStatus.ACTIVE, start_date=date(2023, 1, 1), end_date=date(2023, 12, 31), monthly_rent=1000, security_deposit=500, tenant_id=1) # Active lease
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [lease1, lease2]
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await bulk_delete_leases(lease_ids=[1, 2], current_user=user, session=mock_session)
        
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "Cannot delete active leases" in exc_info.value.detail
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_leases_unauthorized_owner_integration():
    """Tests that a landlord cannot delete leases they do not own."""
    # Arrange
    user = create_test_user(user_id=uuid4()) # Landlord
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [] # Simulates no leases found for this user
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await bulk_delete_leases(lease_ids=[1, 2], current_user=user, session=mock_session)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_leases_admin_success_integration():
    """Tests that an admin can delete any lease."""
    # Arrange
    admin_user = create_test_user()
    admin_user.is_admin = True
    lease1 = Lease(id=1, property_id=10, status=LeaseStatus.TERMINATED, start_date=date(2023, 1, 1), end_date=date(2023, 12, 31), monthly_rent=1000, security_deposit=500, tenant_id=1)
    lease2 = Lease(id=2, property_id=20, status=LeaseStatus.DRAFT, start_date=date(2023, 1, 1), end_date=date(2023, 12, 31), monthly_rent=1000, security_deposit=500, tenant_id=1)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [lease1, lease2]
    mock_session.execute.return_value = mock_result

    # Act
    await bulk_delete_leases(lease_ids=[1, 2], current_user=admin_user, session=mock_session)

    # Assert
    assert mock_session.delete.call_count == 2
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_delete_handles_foreign_key_conflict_integration():
    """Tests that a foreign key violation during deletion is handled."""
    # Arrange
    user = create_test_user()
    lease1 = Lease(id=1, property_id=10, status=LeaseStatus.TERMINATED, start_date=date(2023, 1, 1), end_date=date(2023, 12, 31), monthly_rent=1000, security_deposit=500, tenant_id=1)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [lease1]
    mock_session.execute.return_value = mock_result
    
    mock_session.commit.side_effect = Exception("violates foreign key constraint")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await bulk_delete_leases(lease_ids=[1], current_user=user, session=mock_session)
        
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "referenced by other records" in exc_info.value.detail
    mock_session.rollback.assert_awaited_once()
