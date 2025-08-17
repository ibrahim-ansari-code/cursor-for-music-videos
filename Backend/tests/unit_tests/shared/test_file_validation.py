"""Unit tests for file validation utilities."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from io import BytesIO
from fastapi import UploadFile

from Backend.utils.file_validation import (
    detect_file_type_by_magic,
    validate_file_size,
    validate_receipt_file,
    validate_file_from_upload,
    FILE_SIGNATURES
)
from Backend.config import settings


# =============================================================================
# DETECT FILE TYPE BY MAGIC TESTS
# =============================================================================

def test_detect_pdf():
    """Test PDF file detection."""
    pdf_content = b'\x25\x50\x44\x46' + b'rest of content'
    assert detect_file_type_by_magic(pdf_content) == 'application/pdf'


def test_detect_jpeg():
    """Test JPEG file detection with various headers."""
    jpeg_headers = [
        b'\xFF\xD8\xFF\xE0',
        b'\xFF\xD8\xFF\xE1',
        b'\xFF\xD8\xFF\xDB'
    ]
    for header in jpeg_headers:
        content = header + b'rest of content'
        assert detect_file_type_by_magic(content) == 'image/jpeg'


def test_detect_png():
    """Test PNG file detection."""
    png_content = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A' + b'rest of content'
    assert detect_file_type_by_magic(png_content) == 'image/png'


def test_unknown_file_type():
    """Test unknown file type returns None."""
    unknown_content = b'UNKNOWN_HEADER_12345'
    assert detect_file_type_by_magic(unknown_content) is None


def test_empty_content():
    """Test empty content returns None."""
    assert detect_file_type_by_magic(b'') is None


# =============================================================================
# VALIDATE FILE SIZE TESTS
# =============================================================================

def test_valid_size():
    """Test file within size limit passes."""
    content = b'x' * 1000  # 1KB
    validate_file_size(content, max_size=2000)  # 2KB limit


def test_exceeds_size_limit():
    """Test file exceeding size limit raises error."""
    content = b'x' * 3000  # 3KB
    with pytest.raises(ValueError, match="exceeds limit"):
        validate_file_size(content, max_size=2000)  # 2KB limit


def test_uses_default_limit():
    """Test uses settings default when no limit specified."""
    content = b'x' * 100
    validate_file_size(content)  # Should use settings.MAX_FILE_SIZE


# =============================================================================
# VALIDATE RECEIPT FILE TESTS
# =============================================================================

def test_valid_pdf():
    """Test valid PDF file validation."""
    pdf_content = b'\x25\x50\x44\x46' + b'rest of content'
    mime_type = validate_receipt_file(pdf_content)
    assert mime_type == 'application/pdf'


def test_empty_content_raises_error():
    """Test empty content raises error."""
    with pytest.raises(ValueError, match="File content is empty"):
        validate_receipt_file(b'')


def test_unsupported_file_type():
    """Test unsupported file type raises error."""
    unknown_content = b'UNKNOWN_HEADER_12345'
    with pytest.raises(ValueError, match="Unsupported file type"):
        validate_receipt_file(unknown_content)


def test_mime_type_mismatch_warning(caplog):
    """Test warning on MIME type mismatch."""
    pdf_content = b'\x25\x50\x44\x46' + b'rest of content'
    mime_type = validate_receipt_file(pdf_content, declared_mime_type='image/jpeg')
    assert mime_type == 'application/pdf'  # Uses detected type
    assert "MIME type mismatch" in caplog.text


def test_normalizes_jpg_to_jpeg():
    """Test normalizes image/jpg to image/jpeg."""
    jpeg_content = b'\xFF\xD8\xFF\xE0' + b'rest of content'
    mime_type = validate_receipt_file(jpeg_content, declared_mime_type='image/jpg')
    assert mime_type == 'image/jpeg'


def test_disallowed_mime_type(monkeypatch):
    """Test file type not in ALLOWED_RECEIPT_MIME_TYPES raises error."""
    # Mock a valid file signature that would normally be detected
    # but is not in the allowed types list
    monkeypatch.setattr(
        'Backend.utils.file_validation.FILE_SIGNATURES',
        {b'TESTFILE': 'application/test-type'}
    )
    monkeypatch.setattr(
        'Backend.config.settings.ALLOWED_RECEIPT_MIME_TYPES',
        {'application/pdf', 'image/jpeg', 'image/png'}  # Exclude test-type
    )
    
    test_content = b'TESTFILE' + b'rest of content'
    with pytest.raises(ValueError, match="is not allowed for receipts"):
        validate_receipt_file(test_content)


# =============================================================================
# VALIDATE FILE FROM UPLOAD TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_async_upload_file():
    """Test with async UploadFile that has coroutine read method."""
    # Create mock UploadFile with async read
    mock_file = AsyncMock()
    mock_file.read = AsyncMock(return_value=b'\x25\x50\x44\x46' + b'test pdf content')
    mock_file.seek = AsyncMock()
    
    content, mime_type = await validate_file_from_upload(mock_file)
    
    assert content == b'\x25\x50\x44\x46' + b'test pdf content'
    assert mime_type == 'application/pdf'
    mock_file.read.assert_called_once()
    mock_file.seek.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_sync_file_object():
    """Test with sync file object like BytesIO."""
    pdf_content = b'\x25\x50\x44\x46' + b'test pdf content'
    file_obj = BytesIO(pdf_content)
    
    content, mime_type = await validate_file_from_upload(file_obj)
    
    assert content == pdf_content
    assert mime_type == 'application/pdf'
    assert file_obj.tell() == 0  # File pointer reset


@pytest.mark.asyncio
async def test_sync_read_returning_awaitable():
    """Test file with sync read method that returns an awaitable."""
    pdf_content = b'\x25\x50\x44\x46' + b'test pdf content'
    
    # Create a mock that returns a coroutine when read() is called
    async def async_content():
        return pdf_content
    
    mock_file = Mock()
    mock_file.read = Mock(return_value=async_content())
    mock_file.seek = Mock()
    
    content, mime_type = await validate_file_from_upload(mock_file)
    
    assert content == pdf_content
    assert mime_type == 'application/pdf'


@pytest.mark.asyncio
async def test_file_without_seek():
    """Test file object without seek method."""
    # Create mock file without seek
    mock_file = Mock()
    mock_file.read = Mock(return_value=b'\xFF\xD8\xFF\xE0' + b'test jpeg')
    del mock_file.seek  # Remove seek attribute
    
    content, mime_type = await validate_file_from_upload(mock_file)
    
    assert content == b'\xFF\xD8\xFF\xE0' + b'test jpeg'
    assert mime_type == 'image/jpeg'


@pytest.mark.asyncio
async def test_sync_seek_method():
    """Test file with synchronous seek method."""
    mock_file = Mock()
    mock_file.read = Mock(return_value=b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A' + b'png')
    mock_file.seek = Mock()  # Sync seek
    
    content, mime_type = await validate_file_from_upload(mock_file)
    
    assert mime_type == 'image/png'
    mock_file.seek.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_seek_exception_ignored():
    """Test that seek exceptions are ignored."""
    mock_file = Mock()
    mock_file.read = Mock(return_value=b'\x25\x50\x44\x46' + b'pdf')
    mock_file.seek = Mock(side_effect=Exception("Seek not supported"))
    
    # Should not raise exception
    content, mime_type = await validate_file_from_upload(mock_file)
    
    assert content == b'\x25\x50\x44\x46' + b'pdf'
    assert mime_type == 'application/pdf'


@pytest.mark.asyncio
async def test_no_read_method():
    """Test file without read method raises error."""
    mock_file = Mock(spec=[])  # No read method
    
    with pytest.raises(ValueError, match="must have a 'read' method"):
        await validate_file_from_upload(mock_file)


@pytest.mark.asyncio
async def test_read_exception():
    """Test read exception is properly handled."""
    mock_file = Mock()
    mock_file.read = Mock(side_effect=Exception("Read failed"))
    
    with pytest.raises(ValueError, match="Failed to read file content"):
        await validate_file_from_upload(mock_file)


@pytest.mark.asyncio
async def test_non_bytes_content():
    """Test non-bytes content raises error."""
    mock_file = Mock()
    mock_file.read = Mock(return_value="string content")  # Returns string, not bytes
    
    with pytest.raises(ValueError, match="Expected bytes from file read"):
        await validate_file_from_upload(mock_file)


@pytest.mark.asyncio
async def test_declared_mime_type_passed_through():
    """Test declared MIME type is passed to validation."""
    jpeg_content = b'\xFF\xD8\xFF\xE0' + b'test jpeg'
    file_obj = BytesIO(jpeg_content)
    
    content, mime_type = await validate_file_from_upload(
        file_obj, 
        declared_mime_type='image/jpeg'
    )
    
    assert mime_type == 'image/jpeg'


@pytest.mark.asyncio
async def test_mixed_async_sync_methods():
    """Test file with async read but sync seek."""
    mock_file = AsyncMock()
    mock_file.read = AsyncMock(return_value=b'\x25\x50\x44\x46' + b'pdf')
    mock_file.seek = Mock()  # Sync seek, not async
    
    content, mime_type = await validate_file_from_upload(mock_file)
    
    assert content == b'\x25\x50\x44\x46' + b'pdf'
    assert mime_type == 'application/pdf'
    mock_file.seek.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_async_seek_method():
    """Test file with async seek method."""
    mock_file = AsyncMock()
    mock_file.read = AsyncMock(return_value=b'\xFF\xD8\xFF\xE0' + b'jpeg')
    mock_file.seek = AsyncMock()  # Async seek
    
    content, mime_type = await validate_file_from_upload(mock_file)
    
    assert content == b'\xFF\xD8\xFF\xE0' + b'jpeg'
    assert mime_type == 'image/jpeg'
    mock_file.seek.assert_called_once_with(0)


# =============================================================================
# REAL WORLD SCENARIOS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_fastapi_upload_file():
    """Test with FastAPI UploadFile mock."""
    # Create a more realistic UploadFile mock
    pdf_content = b'\x25\x50\x44\x46' + b'test pdf'
    
    mock_upload = Mock(spec=UploadFile)
    mock_upload.read = AsyncMock(return_value=pdf_content)
    mock_upload.seek = AsyncMock()
    mock_upload.filename = "test.pdf"
    mock_upload.content_type = "application/pdf"
    
    content, mime_type = await validate_file_from_upload(
        mock_upload,
        declared_mime_type=mock_upload.content_type
    )
    
    assert content == pdf_content
    assert mime_type == 'application/pdf'


@pytest.mark.asyncio
async def test_large_file_within_limit():
    """Test large file within size limit."""
    # Create a 5MB file (assuming default limit is higher)
    large_content = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A' + b'x' * (5 * 1024 * 1024)
    file_obj = BytesIO(large_content)
    
    if settings.MAX_FILE_SIZE > 5 * 1024 * 1024:
        content, mime_type = await validate_file_from_upload(file_obj)
        assert mime_type == 'image/png'
        assert len(content) > 5 * 1024 * 1024