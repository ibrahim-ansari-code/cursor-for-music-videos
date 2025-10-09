"""
Unit tests for lease document service functions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException

from Backend.api.leases.service import get_lease_document_by_id
from Backend.models.user import User
from Backend.models.lease import LeaseDocument

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


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


@pytest.mark.asyncio
async def test_get_lease_document_by_id_success(mocker):
    """Test successful retrieval of lease document."""
    # Arrange
    lease_id = 123
    document_id = 456
    user = create_test_user()
    
    # Mock document
    mock_document = MagicMock(spec=LeaseDocument)
    mock_document.id = document_id
    mock_document.lease_id = lease_id
    mock_document.file_path = "https://storage.blob.core.windows.net/lease-uploads/doc.pdf"
    mock_document.name = "Lease Contract.pdf"
    mock_document.document_type = "contract"
    
    # Mock permission check
    mocker.patch(
        "Backend.api.leases.service.check_lease_permission",
        new=AsyncMock(return_value=None)
    )
    
    # Mock database query
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_document
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_lease_document_by_id(
        lease_id=lease_id,
        document_id=document_id,
        current_user=user,
        session=mock_session
    )
    
    # Assert
    assert result == mock_document
    assert result.id == document_id
    assert result.lease_id == lease_id


@pytest.mark.asyncio
async def test_get_lease_document_by_id_not_found(mocker):
    """Test error when document not found."""
    # Arrange
    lease_id = 123
    document_id = 999
    user = create_test_user()
    
    # Mock permission check
    mocker.patch(
        "Backend.api.leases.service.check_lease_permission",
        new=AsyncMock(return_value=None)
    )
    
    # Mock database query to return None
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_lease_document_by_id(
            lease_id=lease_id,
            document_id=document_id,
            current_user=user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == 404
    assert str(document_id) in exc_info.value.detail
    assert str(lease_id) in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_lease_document_by_id_permission_denied(mocker):
    """Test error when user lacks permission to access lease."""
    # Arrange
    lease_id = 123
    document_id = 456
    user = create_test_user()
    
    # Mock permission check to raise 403
    mocker.patch(
        "Backend.api.leases.service.check_lease_permission",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Permission denied"))
    )
    
    mock_session = AsyncMock()
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_lease_document_by_id(
            lease_id=lease_id,
            document_id=document_id,
            current_user=user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == 403
    assert "denied" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_lease_document_wrong_lease(mocker):
    """Test error when document belongs to different lease."""
    # Arrange
    lease_id = 123
    document_id = 456
    user = create_test_user()
    
    # Mock permission check
    mocker.patch(
        "Backend.api.leases.service.check_lease_permission",
        new=AsyncMock(return_value=None)
    )
    
    # Mock database to return None (document doesn't belong to this lease)
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_lease_document_by_id(
            lease_id=lease_id,
            document_id=document_id,
            current_user=user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == 404

