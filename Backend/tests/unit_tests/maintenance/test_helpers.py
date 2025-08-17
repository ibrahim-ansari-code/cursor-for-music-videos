"""
Unit tests for maintenance helper functions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from io import BytesIO
from fastapi import HTTPException, UploadFile

from Backend.api.maintenance.helpers import (
    validate_file_content,
    validate_file_size,
    check_permission
)
from Backend.models.maintenance import MaintenanceRequest
from Backend.models.property import Property
from Backend.models.user import User


# =============================================================================
# validate_file_content TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_validate_file_content_jpeg():
    """Test JPEG file validation."""
    mock_file = AsyncMock()
    mock_file.seek = AsyncMock()
    mock_file.read = AsyncMock(return_value=b'\xFF\xD8\xFF\xE0' + b'rest of jpeg content')
    
    result = await validate_file_content(mock_file)
    
    assert result is True
    assert mock_file.seek.call_count == 2  # Called at start and end
    mock_file.read.assert_called_once_with(32)


@pytest.mark.asyncio
async def test_validate_file_content_png():
    """Test PNG file validation."""
    mock_file = AsyncMock()
    mock_file.seek = AsyncMock()
    mock_file.read = AsyncMock(return_value=b'\x89PNG\r\n\x1a\n' + b'rest of png content')
    
    result = await validate_file_content(mock_file)
    
    assert result is True


@pytest.mark.asyncio
async def test_validate_file_content_pdf():
    """Test PDF file validation."""
    mock_file = AsyncMock()
    mock_file.seek = AsyncMock()
    mock_file.read = AsyncMock(return_value=b'%PDF-1.4' + b'rest of pdf content')
    
    result = await validate_file_content(mock_file)
    
    assert result is True


@pytest.mark.asyncio
async def test_validate_file_content_invalid():
    """Test invalid file type validation."""
    mock_file = AsyncMock()
    mock_file.seek = AsyncMock()
    mock_file.read = AsyncMock(return_value=b'INVALID_HEADER' + b'rest of content')
    
    result = await validate_file_content(mock_file)
    
    assert result is False


@pytest.mark.asyncio
async def test_validate_file_content_empty():
    """Test empty file validation."""
    mock_file = AsyncMock()
    mock_file.seek = AsyncMock()
    mock_file.read = AsyncMock(return_value=b'')
    
    result = await validate_file_content(mock_file)
    
    assert result is False


@pytest.mark.asyncio
async def test_validate_file_content_short_header():
    """Test file with header shorter than 16 bytes."""
    mock_file = AsyncMock()
    mock_file.seek = AsyncMock()
    mock_file.read = AsyncMock(return_value=b'\xFF\xD8\xFF')  # Only 3 bytes
    
    result = await validate_file_content(mock_file)
    
    assert result is True  # Should still match JPEG magic bytes


# =============================================================================
# validate_file_size TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_validate_file_size_within_limit():
    """Test file size validation within limit."""
    mock_file = AsyncMock()
    mock_file.seek = AsyncMock()
    
    # Mock file reading in chunks
    chunks = [b'x' * 1000, b'x' * 500, b'']  # 1.5KB total
    mock_file.read = AsyncMock(side_effect=chunks)
    
    max_size = 2048  # 2KB limit
    result = await validate_file_size(mock_file, max_size)
    
    assert result == 1500  # 1.5KB
    mock_file.seek.assert_called_with(0)


@pytest.mark.asyncio
async def test_validate_file_size_exceeds_limit():
    """Test file size validation exceeding limit."""
    mock_file = AsyncMock()
    mock_file.seek = AsyncMock()
    
    # Mock large file that exceeds limit
    chunks = [b'x' * 8192] * 10 + [b'']  # 80KB total
    mock_file.read = AsyncMock(side_effect=chunks)
    
    max_size = 1024  # 1KB limit
    
    with pytest.raises(HTTPException) as exc_info:
        await validate_file_size(mock_file, max_size)
    
    assert exc_info.value.status_code == 413
    assert "File too large" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_file_size_empty_file():
    """Test empty file size validation."""
    mock_file = AsyncMock()
    mock_file.seek = AsyncMock()
    mock_file.read = AsyncMock(return_value=b'')  # Empty file
    
    max_size = 1024
    result = await validate_file_size(mock_file, max_size)
    
    assert result == 0


@pytest.mark.asyncio
async def test_validate_file_size_exact_limit():
    """Test file size exactly at limit."""
    mock_file = AsyncMock()
    mock_file.seek = AsyncMock()
    
    # Mock file exactly at limit
    chunks = [b'x' * 1024, b'']  # Exactly 1KB
    mock_file.read = AsyncMock(side_effect=chunks)
    
    max_size = 1024  # 1KB limit
    result = await validate_file_size(mock_file, max_size)
    
    assert result == 1024


@pytest.mark.asyncio
async def test_validate_file_size_mb_calculation():
    """Test MB calculation in error message."""
    mock_file = AsyncMock()
    mock_file.seek = AsyncMock()
    
    # Mock large file
    chunks = [b'x' * 8192] * 1000  # Very large
    mock_file.read = AsyncMock(side_effect=chunks)
    
    max_size = 5 * 1024 * 1024  # 5MB limit
    
    with pytest.raises(HTTPException) as exc_info:
        await validate_file_size(mock_file, max_size)
    
    assert "5 MB" in exc_info.value.detail


# =============================================================================
# check_permission TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_check_permission_admin_user():
    """Test permission check for admin user."""
    mock_request = MagicMock()
    mock_user = MagicMock()
    mock_user.is_admin = True
    mock_session = AsyncMock()
    
    # Should not raise any exception
    await check_permission(mock_request, mock_user, mock_session)
    
    # Session should not be used for admin users
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_check_permission_property_already_loaded():
    """Test permission check when property is already loaded on request."""
    mock_request = MagicMock()
    mock_property = MagicMock()
    mock_property.user_id = "user123"
    mock_request.property = mock_property
    
    mock_user = MagicMock()
    mock_user.is_admin = False
    mock_user.id = "user123"
    
    mock_session = AsyncMock()
    
    # Should not raise any exception
    await check_permission(mock_request, mock_user, mock_session)
    
    # Session should not be used when property is already loaded
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_check_permission_load_property_success():
    """Test permission check when property needs to be loaded."""
    mock_request = MagicMock()
    mock_request.property = None
    mock_request.property_id = 123
    
    mock_property = MagicMock()
    mock_property.user_id = "user123"
    
    mock_user = MagicMock()
    mock_user.is_admin = False
    mock_user.id = "user123"
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_property
    mock_session.execute.return_value = mock_result
    
    # Should not raise any exception
    await check_permission(mock_request, mock_user, mock_session)
    
    # Property should be set on request
    assert mock_request.property == mock_property
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_permission_property_not_found():
    """Test permission check when property is not found."""
    mock_request = MagicMock()
    mock_request.property = None
    mock_request.property_id = 123
    
    mock_user = MagicMock()
    mock_user.is_admin = False
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(HTTPException) as exc_info:
        await check_permission(mock_request, mock_user, mock_session)
    
    assert exc_info.value.status_code == 404
    assert "Property not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_check_permission_database_error():
    """Test permission check when database query fails."""
    mock_request = MagicMock()
    mock_request.property = None
    mock_request.property_id = 123
    
    mock_user = MagicMock()
    mock_user.is_admin = False
    
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Database connection failed")
    
    with pytest.raises(HTTPException) as exc_info:
        await check_permission(mock_request, mock_user, mock_session)
    
    assert exc_info.value.status_code == 500
    assert "Failed to load property relationship" in exc_info.value.detail


@pytest.mark.asyncio
async def test_check_permission_unauthorized_user():
    """Test permission check for unauthorized user."""
    mock_request = MagicMock()
    mock_property = MagicMock()
    mock_property.user_id = "owner123"
    mock_request.property = mock_property
    
    mock_user = MagicMock()
    mock_user.is_admin = False
    mock_user.id = "different_user456"
    
    mock_session = AsyncMock()
    
    with pytest.raises(HTTPException) as exc_info:
        await check_permission(mock_request, mock_user, mock_session)
    
    assert exc_info.value.status_code == 403
    assert "You do not have permission" in exc_info.value.detail


@pytest.mark.asyncio
async def test_check_permission_property_without_user_id():
    """Test permission check when property has no user_id attribute."""
    mock_request = MagicMock()
    mock_property = MagicMock()
    # Property without user_id attribute
    del mock_property.user_id
    mock_request.property = mock_property
    
    mock_user = MagicMock()
    mock_user.is_admin = False
    mock_user.id = "user123"
    
    mock_session = AsyncMock()
    
    with pytest.raises(HTTPException) as exc_info:
        await check_permission(mock_request, mock_user, mock_session)
    
    assert exc_info.value.status_code == 403
    assert "You do not have permission" in exc_info.value.detail


@pytest.mark.asyncio
async def test_check_permission_http_exception_reraise():
    """Test that HTTPException is re-raised as-is."""
    mock_request = MagicMock()
    mock_request.property = None
    mock_request.property_id = 123
    
    mock_user = MagicMock()
    mock_user.is_admin = False
    
    mock_session = AsyncMock()
    # Simulate an HTTPException being raised
    original_exception = HTTPException(status_code=404, detail="Property not found")
    mock_session.execute.side_effect = original_exception
    
    with pytest.raises(HTTPException) as exc_info:
        await check_permission(mock_request, mock_user, mock_session)
    
    # Should be the same exception
    assert exc_info.value is original_exception