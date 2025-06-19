"""
Unit tests for DELETE operations in the properties API endpoint.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, UTC

from fastapi import HTTPException, status

from Backend.api.properties.router import delete_property
from Backend.models.property import Property
from Backend.models.user import User
from Backend.models.lease import Lease, LeaseStatus


# =============================================================================
# DELETE PROPERTY TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_delete_property_success(mocker):
    """Test successful property deletion."""
    # Arrange
    property_id = 123
    owner_id = uuid4()
    now = datetime.now(UTC)

    current_user = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    property_to_delete = MagicMock(spec=Property)
    property_to_delete.id = property_id
    property_to_delete.user_id = owner_id

    mock_session = AsyncMock()
    
    # First query returns property
    mock_property_result = MagicMock()
    mock_property_result.scalar_one_or_none.return_value = property_to_delete
    
    # Second query returns no active leases
    mock_leases_result = MagicMock()
    mock_leases_result.scalars.return_value.all.return_value = []

    mock_session.execute = AsyncMock(side_effect=[mock_property_result, mock_leases_result])
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    # Act
    result = await delete_property(
        property_id=property_id,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert result is None
    assert mock_session.execute.await_count == 2
    mock_session.delete.assert_awaited_with(property_to_delete)
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_property_with_active_leases(mocker):
    """Test 400 error when trying to delete property with active leases."""
    # Arrange
    property_id = 123
    owner_id = uuid4()
    now = datetime.now(UTC)

    current_user = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    property_to_delete = MagicMock(spec=Property)
    property_to_delete.id = property_id
    property_to_delete.user_id = owner_id
    
    # Mock active lease
    active_lease = MagicMock(spec=Lease)
    active_lease.id = 1
    active_lease.status = LeaseStatus.ACTIVE
    
    mock_session = AsyncMock()
    
    # First query returns property
    mock_property_result = MagicMock()
    mock_property_result.scalar_one_or_none.return_value = property_to_delete
    
    # Second query returns active leases
    mock_leases_result = MagicMock()
    mock_leases_result.scalars.return_value.all.return_value = [active_lease]
    
    mock_session.execute = AsyncMock(side_effect=[mock_property_result, mock_leases_result])
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await delete_property(
            property_id=property_id,
            current_user=current_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot delete property with active leases" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_delete_property_not_found(mocker):
    """Test 404 error when trying to delete non-existent property."""
    # Arrange
    property_id = 999
    owner_id = uuid4()
    now = datetime.now(UTC)
    
    current_user = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await delete_property(
            property_id=property_id,
            current_user=current_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Property not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_delete_property_forbidden(mocker):
    """Test 403 error when non-owner tries to delete property."""
    # Arrange
    property_id = 123
    owner_id = uuid4()
    other_user_id = uuid4()
    now = datetime.now(UTC)
    
    other_user = User(
        id=other_user_id,
        email="other@example.com",
        first_name="Other",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )
    
    property_to_delete = MagicMock(spec=Property)
    property_to_delete.id = property_id
    property_to_delete.user_id = owner_id  # Different from other_user_id
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = property_to_delete
    mock_session.execute.return_value = mock_result
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await delete_property(
            property_id=property_id,
            current_user=other_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "permission" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_delete_property_admin_can_delete_any(mocker):
    """Test that admin can delete properties they don't own."""
    # Arrange
    property_id = 456
    owner_id = uuid4()
    admin_id = uuid4()
    now = datetime.now(UTC)

    admin_user = User(
        id=admin_id,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        is_admin=True,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="ADMIN"
    )

    property_to_delete = MagicMock(spec=Property)
    property_to_delete.id = property_id
    property_to_delete.user_id = owner_id  # Different from admin_id

    mock_session = AsyncMock()
    
    # First query returns property
    mock_property_result = MagicMock()
    mock_property_result.scalar_one_or_none.return_value = property_to_delete
    
    # Second query returns no active leases
    mock_leases_result = MagicMock()
    mock_leases_result.scalars.return_value.all.return_value = []

    mock_session.execute = AsyncMock(side_effect=[mock_property_result, mock_leases_result])
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    # Act
    result = await delete_property(
        property_id=property_id,
        current_user=admin_user,
        session=mock_session
    )

    # Assert - Admin should be able to delete
    assert result is None
    assert mock_session.execute.await_count == 2
    mock_session.delete.assert_awaited_with(property_to_delete)
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_property_with_pending_leases(mocker):
    """Test 400 error when trying to delete property with pending leases."""
    # Arrange
    property_id = 789
    owner_id = uuid4()
    now = datetime.now(UTC)

    current_user = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    property_to_delete = MagicMock(spec=Property)
    property_to_delete.id = property_id
    property_to_delete.user_id = owner_id
    
    # Mock pending lease
    pending_lease = MagicMock(spec=Lease)
    pending_lease.id = 2
    pending_lease.status = LeaseStatus.PENDING
    
    mock_session = AsyncMock()
    
    # First query returns property
    mock_property_result = MagicMock()
    mock_property_result.scalar_one_or_none.return_value = property_to_delete
    
    # Second query returns pending lease
    mock_leases_result = MagicMock()
    mock_leases_result.scalars.return_value.all.return_value = [pending_lease]
    
    mock_session.execute = AsyncMock(side_effect=[mock_property_result, mock_leases_result])
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await delete_property(
            property_id=property_id,
            current_user=current_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot delete property with active leases" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_delete_property_with_expired_leases_allowed(mocker):
    """Test that property with only expired leases can be deleted."""
    # Arrange
    property_id = 321
    owner_id = uuid4()
    now = datetime.now(UTC)

    current_user = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    property_to_delete = MagicMock(spec=Property)
    property_to_delete.id = property_id
    property_to_delete.user_id = owner_id

    mock_session = AsyncMock()
    
    # First query returns property
    mock_property_result = MagicMock()
    mock_property_result.scalar_one_or_none.return_value = property_to_delete
    
    # Second query returns no active/pending leases (only expired ones exist)
    mock_leases_result = MagicMock()
    mock_leases_result.scalars.return_value.all.return_value = []

    mock_session.execute = AsyncMock(side_effect=[mock_property_result, mock_leases_result])
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    # Act
    result = await delete_property(
        property_id=property_id,
        current_user=current_user,
        session=mock_session
    )

    # Assert - Should be able to delete
    assert result is None
    assert mock_session.execute.await_count == 2
    mock_session.delete.assert_awaited_with(property_to_delete)
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_property_database_error_during_deletion(mocker):
    """Test error handling when database deletion fails."""
    # Arrange
    property_id = 654
    owner_id = uuid4()
    now = datetime.now(UTC)

    current_user = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )

    property_to_delete = MagicMock(spec=Property)
    property_to_delete.id = property_id
    property_to_delete.user_id = owner_id

    mock_session = AsyncMock()
    
    # First query returns property
    mock_property_result = MagicMock()
    mock_property_result.scalar_one_or_none.return_value = property_to_delete
    
    # Second query returns no active leases
    mock_leases_result = MagicMock()
    mock_leases_result.scalars.return_value.all.return_value = []

    mock_session.execute = AsyncMock(side_effect=[mock_property_result, mock_leases_result])
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock(side_effect=Exception("Database commit failed"))
    mock_session.rollback = AsyncMock()

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await delete_property(
            property_id=property_id,
            current_user=current_user,
            session=mock_session
        )
    
    assert "Database commit failed" in str(exc_info.value)
    mock_session.delete.assert_awaited_with(property_to_delete) 