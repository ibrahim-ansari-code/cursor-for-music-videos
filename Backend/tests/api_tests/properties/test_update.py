"""
Unit tests for UPDATE operations in the properties API endpoint.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, UTC
from pydantic import ValidationError

from fastapi import HTTPException, status

from Backend.api.properties.router import update_property
from Backend.api.properties.schemas import PropertyUpdate, PropertyDetailResponse_Standalone
from Backend.models.property import Property
from Backend.models.user import User
from Backend.models.enums import PropertyStatus
from Backend.models.property import PropertyType


# =============================================================================
# UPDATE PROPERTY TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_update_property_success(mocker):
    """Test successful property update."""
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
    
    update_data = PropertyUpdate(
        name="Updated Property Name",
        description="Updated description",
        year_built=2024
    )

    # Mock existing property
    existing_property = MagicMock(spec=Property)
    existing_property.id = property_id
    existing_property.user_id = owner_id
    existing_property.name = "Old Name"
    existing_property.description = "Old description"
    existing_property.year_built = 2020
    
    # Mock updated property after refresh
    updated_property = MagicMock(spec=Property)
    updated_property.id = property_id
    updated_property.name = "Updated Property Name"
    updated_property.description = "Updated description"
    updated_property.year_built = 2024
    updated_property.user_id = owner_id
    updated_property.owner = current_user
    updated_property.units = []
    updated_property.status = PropertyStatus.ACTIVE
    updated_property.address = "123 Main St"
    updated_property.city = "Test City"
    updated_property.province = "Test Province"
    updated_property.postal_code = "12345"
    updated_property.property_type = PropertyType.RESIDENTIAL
    updated_property.created_at = now
    updated_property.updated_at = now
    
    mock_session = AsyncMock()
    
    # First query returns existing property
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = existing_property
    
    # Second query returns updated property
    mock_result2 = MagicMock()
    mock_result2.unique.return_value.scalar_one_or_none.return_value = updated_property
    
    mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act
    response = await update_property(
        property_id=property_id,
        property_data=update_data,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.id == property_id
    assert response.name == "Updated Property Name"
    assert response.description == "Updated description"
    assert response.year_built == 2024


@pytest.mark.asyncio
async def test_update_property_not_found(mocker):
    """Test 404 error when updating non-existent property."""
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
    
    update_data = PropertyUpdate(name="New Name")
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_property(
            property_id=property_id,
            property_data=update_data,
            current_user=current_user,
            session=mock_session
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Property not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_update_property_forbidden(mocker):
    """Test 403 error when non-owner tries to update property."""
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

    update_data = PropertyUpdate(name="Unauthorized Update")
    
    existing_property = MagicMock(spec=Property)
    existing_property.id = property_id
    existing_property.user_id = owner_id  # Different from other_user_id

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_property
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_property(
            property_id=property_id,
            property_data=update_data,
            current_user=other_user,
            session=mock_session
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "permission" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_update_property_no_data_provided(mocker):
    """Test 400 error when no update data is provided."""
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

    # Empty update data
    update_data = PropertyUpdate()
    
    existing_property = MagicMock(spec=Property)
    existing_property.id = property_id
    existing_property.user_id = owner_id
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_property
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_property(
            property_id=property_id,
            property_data=update_data,
            current_user=current_user,
            session=mock_session
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "No update data provided" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_update_property_validation_error():
    """Test validation error for invalid update data."""
    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        PropertyUpdate(
            name="",  # Empty name should fail
            year_built=1800  # Could add validation for reasonable year range
        )
    
    errors = exc_info.value.errors()
    assert any("name must not be an empty string" in str(error) for error in errors)


@pytest.mark.asyncio
async def test_update_property_admin_can_update_any(mocker):
    """Test that admin can update properties they don't own."""
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
    
    update_data = PropertyUpdate(
        name="Admin Updated Name",
        status=PropertyStatus.INACTIVE
    )

    # Mock existing property owned by someone else
    existing_property = MagicMock(spec=Property)
    existing_property.id = property_id
    existing_property.user_id = owner_id  # Different from admin_id
    existing_property.name = "Original Name"
    existing_property.status = PropertyStatus.ACTIVE
    
    # Mock property owner
    property_owner = User(
        id=owner_id,
        email="owner@example.com",
        first_name="Property",
        last_name="Owner",
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        user_type="LANDLORD"
    )
    
    # Mock updated property
    updated_property = MagicMock(spec=Property)
    updated_property.id = property_id
    updated_property.name = "Admin Updated Name"
    updated_property.status = PropertyStatus.INACTIVE
    updated_property.user_id = owner_id
    updated_property.owner = property_owner
    updated_property.units = []
    updated_property.address = "123 Main St"
    updated_property.city = "Test City"
    updated_property.province = "Test Province"
    updated_property.postal_code = "12345"
    updated_property.property_type = PropertyType.RESIDENTIAL
    updated_property.description = "Property description"  # Add missing description
    updated_property.year_built = 2020  # Add missing year_built
    updated_property.created_at = now
    updated_property.updated_at = now
    
    mock_session = AsyncMock()
    
    # First query returns existing property
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = existing_property
    
    # Second query returns updated property
    mock_result2 = MagicMock()
    mock_result2.unique.return_value.scalar_one_or_none.return_value = updated_property
    
    mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act
    response = await update_property(
        property_id=property_id,
        property_data=update_data,
        current_user=admin_user,
        session=mock_session
    )

    # Assert - Admin should be able to update
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.id == property_id
    assert response.name == "Admin Updated Name"
    assert response.status == PropertyStatus.INACTIVE


@pytest.mark.asyncio
async def test_update_property_partial_update(mocker):
    """Test partial property update (only some fields)."""
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
    
    # Only updating description
    update_data = PropertyUpdate(
        description="New and improved description"
    )

    # Mock existing property with all fields
    existing_property = MagicMock(spec=Property)
    existing_property.id = property_id
    existing_property.user_id = owner_id
    existing_property.name = "Unchanged Name"
    existing_property.description = "Old description"
    existing_property.year_built = 2020
    existing_property.status = PropertyStatus.ACTIVE
    
    # Mock updated property - only description changed
    updated_property = MagicMock(spec=Property)
    updated_property.id = property_id
    updated_property.name = "Unchanged Name"  # Not changed
    updated_property.description = "New and improved description"  # Changed
    updated_property.year_built = 2020  # Not changed
    updated_property.status = PropertyStatus.ACTIVE  # Not changed
    updated_property.user_id = owner_id
    updated_property.owner = current_user
    updated_property.units = []
    updated_property.address = "123 Main St"
    updated_property.city = "Test City"
    updated_property.province = "Test Province"
    updated_property.postal_code = "12345"
    updated_property.property_type = PropertyType.RESIDENTIAL
    updated_property.created_at = now
    updated_property.updated_at = now
    
    mock_session = AsyncMock()
    
    # First query returns existing property
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = existing_property
    
    # Second query returns updated property
    mock_result2 = MagicMock()
    mock_result2.unique.return_value.scalar_one_or_none.return_value = updated_property
    
    mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act
    response = await update_property(
        property_id=property_id,
        property_data=update_data,
        current_user=current_user,
        session=mock_session
    )

    # Assert
    assert isinstance(response, PropertyDetailResponse_Standalone)
    assert response.id == property_id
    assert response.name == "Unchanged Name"  # Should remain unchanged
    assert response.description == "New and improved description"  # Should be updated
    assert response.year_built == 2020  # Should remain unchanged


@pytest.mark.asyncio
async def test_update_property_retrieval_failure_after_update(mocker):
    """Test error handling when property retrieval fails after update."""
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
    
    update_data = PropertyUpdate(name="Updated Name")

    # Mock existing property
    existing_property = MagicMock(spec=Property)
    existing_property.id = property_id
    existing_property.user_id = owner_id
    
    mock_session = AsyncMock()
    
    # First query returns existing property
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = existing_property
    
    # Second query returns None (retrieval failure)
    mock_result2 = MagicMock()
    mock_result2.unique.return_value.scalar_one_or_none.return_value = None
    
    mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    mocker.patch("Backend.utils.datetime_utils.create_audit_datetime", return_value=now)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_property(
            property_id=property_id,
            property_data=update_data,
            current_user=current_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Property updated but could not be re-retrieved" in str(exc_info.value.detail) 