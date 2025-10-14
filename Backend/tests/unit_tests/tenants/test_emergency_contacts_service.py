"""
Unit tests for Emergency Contacts service layer.

These tests focus on emergency contact CRUD operations at the service level.
Extracted from test_tenants_service.py for better organization.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException

from Backend.api.tenants.service import (
    add_emergency_contact,
    update_emergency_contact,
    delete_emergency_contact,
)
from Backend.api.tenants.schemas import (
    EmergencyContactCreate,
    EmergencyContactUpdate,
    EmergencyContactResponse,
)
from Backend.models.tenant import Tenant, TenantStatus
from Backend.models.enums import TenantType, UserType
from Backend.models.user import User

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    # Setup common mock behaviors
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.user_type = UserType.LANDLORD
    user.is_admin = False
    user.is_active = True
    return user


@pytest.fixture
def mock_tenant():
    """Create a mock individual tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = 1
    tenant.tenant_type = TenantType.INDIVIDUAL
    tenant.first_name = "John"
    tenant.last_name = "Doe"
    tenant.company_name = None
    tenant.contact_person = None
    tenant.email = "john.doe@example.com"
    tenant.phone = "555-1234"
    tenant.status = TenantStatus.ACTIVE
    tenant.landlord_id = uuid4()
    tenant.current_property_id = None
    tenant.created_at = datetime.now(timezone.utc)
    tenant.updated_at = datetime.now(timezone.utc)
    return tenant


# =============================================================================
# add_emergency_contact Tests
# =============================================================================

@pytest.mark.asyncio
async def test_add_emergency_contact_success(mock_session, mock_user, mock_tenant):
    """Test successfully adding an emergency contact - covers service.py:516-559"""
    # Arrange
    tenant_id = 1
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = []  # Empty contacts list
    mock_tenant.updated_at = datetime.now(timezone.utc)

    contact_data = EmergencyContactCreate(
        name="John Emergency",
        relationship="Brother",
        phone="555-1234567",
        email="john@example.com",
        is_primary=False,
        notes="Call after 6pm"
    )

    # Mock check_tenant_permission
    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act
        result = await add_emergency_contact(tenant_id, contact_data, mock_session, mock_user)

        # Assert
        assert isinstance(result, EmergencyContactResponse)
        assert result.name == "John Emergency"
        assert result.relationship == "Brother"
        assert result.phone == "555-1234567"
        assert result.email == "john@example.com"
        assert result.is_primary is False
        assert result.notes == "Call after 6pm"
        assert result.id is not None  # UUID should be generated

        # Verify session operations
        mock_session.add.assert_called_once_with(mock_tenant)
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(mock_tenant)


@pytest.mark.asyncio
async def test_add_emergency_contact_as_primary(mock_session, mock_user, mock_tenant):
    """Test adding emergency contact as primary - unsets other primaries"""
    # Arrange
    tenant_id = 1
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = [
        {"id": "existing-id", "name": "Existing", "relationship": "Friend", "phone": "555-0000000", "is_primary": True}
    ]
    mock_tenant.updated_at = datetime.now(timezone.utc)

    contact_data = EmergencyContactCreate(
        name="New Primary",
        relationship="Spouse",
        phone="555-9999999",
        is_primary=True
    )

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act
        result = await add_emergency_contact(tenant_id, contact_data, mock_session, mock_user)

        # Assert
        assert result.is_primary is True
        # Verify the existing primary contact was unset
        assert mock_tenant.emergency_contacts[0]["is_primary"] is False


@pytest.mark.asyncio
async def test_add_emergency_contact_max_limit_reached(mock_session, mock_user, mock_tenant):
    """Test adding contact when max 5 limit is reached - covers service.py:522-526"""
    # Arrange
    tenant_id = 1
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    # Already has 5 contacts
    mock_tenant.emergency_contacts = [
        {"id": f"id-{i}", "name": f"Contact {i}", "relationship": "Friend", "phone": f"555-{i}000000", "is_primary": False}
        for i in range(5)
    ]

    contact_data = EmergencyContactCreate(
        name="Sixth Contact",
        relationship="Friend",
        phone="555-6666666"
    )

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await add_emergency_contact(tenant_id, contact_data, mock_session, mock_user)

        assert exc_info.value.status_code == 400
        assert "Maximum 5 emergency contacts" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_add_emergency_contact_database_error(mock_session, mock_user, mock_tenant):
    """Test adding contact handles database errors - covers service.py:560-566"""
    # Arrange
    tenant_id = 1
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = []

    contact_data = EmergencyContactCreate(
        name="Test Contact",
        relationship="Friend",
        phone="555-1111111"
    )

    # Mock commit to raise exception
    mock_session.commit = AsyncMock(side_effect=Exception("Database error"))

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await add_emergency_contact(tenant_id, contact_data, mock_session, mock_user)

        assert exc_info.value.status_code == 500
        assert "Failed to add emergency contact" in str(exc_info.value.detail)
        mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_emergency_contact_without_optional_fields(mock_session, mock_user, mock_tenant):
    """Test adding contact with only required fields"""
    # Arrange
    tenant_id = 1
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = []

    contact_data = EmergencyContactCreate(
        name="Minimal Contact",
        relationship="Friend",
        phone="555-1111111"
        # No email, no notes, is_primary defaults to False
    )

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act
        result = await add_emergency_contact(tenant_id, contact_data, mock_session, mock_user)

        # Assert
        assert result.name == "Minimal Contact"
        assert result.email is None
        assert result.notes is None
        assert result.is_primary is False


# =============================================================================
# update_emergency_contact Tests
# =============================================================================

@pytest.mark.asyncio
async def test_update_emergency_contact_success(mock_session, mock_user, mock_tenant):
    """Test successfully updating an emergency contact - covers service.py:596-646"""
    # Arrange
    tenant_id = 1
    contact_id = "contact-uuid-123"
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = [
        {"id": contact_id, "name": "Old Name", "relationship": "Friend", "phone": "555-0000000", "is_primary": False, "email": None, "notes": None}
    ]
    mock_tenant.updated_at = datetime.now(timezone.utc)

    update_data = EmergencyContactUpdate(
        name="Updated Name",
        phone="555-9999999"
    )

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act
        result = await update_emergency_contact(tenant_id, contact_id, update_data, mock_session, mock_user)

        # Assert
        assert isinstance(result, EmergencyContactResponse)
        assert result.id == contact_id
        assert result.name == "Updated Name"
        assert result.phone == "555-9999999"
        assert result.relationship == "Friend"  # Unchanged

        # Verify session operations
        mock_session.add.assert_called_once_with(mock_tenant)
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(mock_tenant)


@pytest.mark.asyncio
async def test_update_emergency_contact_set_primary(mock_session, mock_user, mock_tenant):
    """Test updating contact to set as primary - unsets others - covers service.py:622-625"""
    # Arrange
    tenant_id = 1
    contact_id = "contact-2"
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = [
        {"id": "contact-1", "name": "Contact 1", "relationship": "Friend", "phone": "555-1111111", "is_primary": True},
        {"id": contact_id, "name": "Contact 2", "relationship": "Brother", "phone": "555-2222222", "is_primary": False}
    ]

    update_data = EmergencyContactUpdate(
        is_primary=True
    )

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act
        result = await update_emergency_contact(tenant_id, contact_id, update_data, mock_session, mock_user)

        # Assert
        assert result.is_primary is True
        # Verify the old primary was unset
        assert mock_tenant.emergency_contacts[0]["is_primary"] is False


@pytest.mark.asyncio
async def test_update_emergency_contact_partial_update(mock_session, mock_user, mock_tenant):
    """Test partial update with exclude_unset - covers service.py:618"""
    # Arrange
    tenant_id = 1
    contact_id = "contact-uuid"
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = [
        {"id": contact_id, "name": "John", "relationship": "Brother", "phone": "555-1234567", "is_primary": False, "email": "john@example.com", "notes": "Old notes"}
    ]

    update_data = EmergencyContactUpdate(
        notes="Updated notes only"
    )

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act
        result = await update_emergency_contact(tenant_id, contact_id, update_data, mock_session, mock_user)

        # Assert
        assert result.notes == "Updated notes only"
        # Other fields should remain unchanged
        assert result.name == "John"
        assert result.relationship == "Brother"
        assert result.phone == "555-1234567"
        assert result.email == "john@example.com"


@pytest.mark.asyncio
async def test_update_emergency_contact_not_found(mock_session, mock_user, mock_tenant):
    """Test updating non-existent contact - covers service.py:608-612"""
    # Arrange
    tenant_id = 1
    contact_id = "non-existent-id"
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = [
        {"id": "different-id", "name": "John", "relationship": "Brother", "phone": "555-1234567", "is_primary": False}
    ]

    update_data = EmergencyContactUpdate(
        name="Updated Name"
    )

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_emergency_contact(tenant_id, contact_id, update_data, mock_session, mock_user)

        assert exc_info.value.status_code == 404
        assert contact_id in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_update_emergency_contact_database_error(mock_session, mock_user, mock_tenant):
    """Test updating contact handles database errors - covers service.py:647-653"""
    # Arrange
    tenant_id = 1
    contact_id = "contact-id"
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = [
        {"id": contact_id, "name": "John", "relationship": "Brother", "phone": "555-1234567", "is_primary": False}
    ]

    update_data = EmergencyContactUpdate(
        name="Updated Name"
    )

    # Mock commit to raise exception
    mock_session.commit = AsyncMock(side_effect=Exception("Database error"))

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_emergency_contact(tenant_id, contact_id, update_data, mock_session, mock_user)

        assert exc_info.value.status_code == 500
        assert "Failed to update emergency contact" in str(exc_info.value.detail)
        mock_session.rollback.assert_awaited_once()


# =============================================================================
# delete_emergency_contact Tests
# =============================================================================

@pytest.mark.asyncio
async def test_delete_emergency_contact_success(mock_session, mock_user, mock_tenant):
    """Test successfully deleting an emergency contact - covers service.py:675-708"""
    # Arrange
    tenant_id = 1
    contact_id = "contact-to-delete"
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = [
        {"id": "contact-1", "name": "Contact 1", "relationship": "Friend", "phone": "555-1111111", "is_primary": False},
        {"id": contact_id, "name": "Contact to Delete", "relationship": "Brother", "phone": "555-2222222", "is_primary": False},
        {"id": "contact-3", "name": "Contact 3", "relationship": "Sister", "phone": "555-3333333", "is_primary": False}
    ]
    mock_tenant.updated_at = datetime.now(timezone.utc)

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act
        await delete_emergency_contact(tenant_id, contact_id, mock_session, mock_user)

        # Assert
        # Verify the contact was removed
        assert len(mock_tenant.emergency_contacts) == 2
        assert all(c["id"] != contact_id for c in mock_tenant.emergency_contacts)

        # Verify session operations
        mock_session.add.assert_called_once_with(mock_tenant)
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_emergency_contact_not_found(mock_session, mock_user, mock_tenant):
    """Test deleting non-existent contact - covers service.py:689-693"""
    # Arrange
    tenant_id = 1
    contact_id = "non-existent-id"
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = [
        {"id": "contact-1", "name": "Contact 1", "relationship": "Friend", "phone": "555-1111111", "is_primary": False}
    ]

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_emergency_contact(tenant_id, contact_id, mock_session, mock_user)

        assert exc_info.value.status_code == 404
        assert contact_id in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_delete_emergency_contact_last_contact(mock_session, mock_user, mock_tenant):
    """Test deleting the last emergency contact"""
    # Arrange
    tenant_id = 1
    contact_id = "last-contact"
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = [
        {"id": contact_id, "name": "Last Contact", "relationship": "Friend", "phone": "555-1111111", "is_primary": False}
    ]

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act
        await delete_emergency_contact(tenant_id, contact_id, mock_session, mock_user)

        # Assert
        assert len(mock_tenant.emergency_contacts) == 0


@pytest.mark.asyncio
async def test_delete_emergency_contact_database_error(mock_session, mock_user, mock_tenant):
    """Test deleting contact handles database errors - covers service.py:709-715"""
    # Arrange
    tenant_id = 1
    contact_id = "contact-id"
    mock_tenant.id = tenant_id
    mock_tenant.landlord_id = mock_user.id
    mock_tenant.emergency_contacts = [
        {"id": contact_id, "name": "Contact", "relationship": "Friend", "phone": "555-1111111", "is_primary": False}
    ]

    # Mock commit to raise exception
    mock_session.commit = AsyncMock(side_effect=Exception("Database error"))

    with patch('Backend.api.tenants.service.check_tenant_permission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_tenant

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_emergency_contact(tenant_id, contact_id, mock_session, mock_user)

        assert exc_info.value.status_code == 500
        assert "Failed to delete emergency contact" in str(exc_info.value.detail)
        mock_session.rollback.assert_awaited_once()
