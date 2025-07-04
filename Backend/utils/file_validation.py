"""File validation utilities with magic number checking for security."""
import logging
from typing import BinaryIO, Union
from fastapi import UploadFile
import asyncio
import inspect

from Backend.config import settings

logger = logging.getLogger(__name__)

# Magic number signatures for supported file types
FILE_SIGNATURES = {
    # PDF files
    b'\x25\x50\x44\x46': 'application/pdf',
    
    # JPEG files
    b'\xFF\xD8\xFF\xE0': 'image/jpeg',
    b'\xFF\xD8\xFF\xE1': 'image/jpeg',
    b'\xFF\xD8\xFF\xE2': 'image/jpeg',
    b'\xFF\xD8\xFF\xE3': 'image/jpeg',
    b'\xFF\xD8\xFF\xE8': 'image/jpeg',
    b'\xFF\xD8\xFF\xDB': 'image/jpeg',
    
    # PNG files
    b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A': 'image/png',
}


def detect_file_type_by_magic(file_content: bytes) -> str | None:
    """
    Detect file type by examining magic numbers in file header.
    
    Args:
        file_content: Binary content of the file
        
    Returns:
        Detected MIME type or None if not recognized
    """
    if not file_content:
        return None
    
    # Check against known file signatures
    for signature, mime_type in FILE_SIGNATURES.items():
        if file_content.startswith(signature):
            return mime_type
    
    return None


def validate_file_size(file_content: bytes, max_size: int | None = None) -> None:
    """
    Validate file size is within limits.
    
    Args:
        file_content: Binary content of the file
        max_size: Maximum allowed file size in bytes. Defaults to config setting.
        
    Raises:
        ValueError: If file exceeds size limit
    """
    limit = max_size if max_size is not None else settings.MAX_FILE_SIZE
    if len(file_content) > limit:
        raise ValueError(f"File size {len(file_content)} bytes exceeds limit of {limit} bytes")


def validate_receipt_file(file_content: bytes, declared_mime_type: str | None = None) -> str:
    """
    Comprehensive validation of receipt file including magic number checking.
    
    Args:
        file_content: Binary content of the file
        declared_mime_type: MIME type declared by the client
        
    Returns:
        Validated MIME type
        
    Raises:
        ValueError: If file validation fails
    """
    if not file_content:
        raise ValueError("File content is empty")
    
    # Validate file size
    validate_file_size(file_content)
    
    # Detect actual file type by magic numbers
    detected_mime_type = detect_file_type_by_magic(file_content)
    
    if not detected_mime_type:
        raise ValueError("Unsupported file type - could not detect valid file signature")
    
    # Check if detected type is allowed
    if detected_mime_type not in settings.ALLOWED_RECEIPT_MIME_TYPES:
        raise ValueError(f"File type {detected_mime_type} is not allowed for receipts")
    
    # Verify declared MIME type matches detected type (if provided)
    if declared_mime_type:
        # Normalize jpg to jpeg for comparison
        normalized_declared = declared_mime_type.replace('image/jpg', 'image/jpeg')
        
        if normalized_declared != detected_mime_type:
            logger.warning(
                "MIME type mismatch: declared=%s, detected=%s", 
                declared_mime_type, detected_mime_type
            )
            # Use detected type for security
    
    return detected_mime_type


async def validate_file_from_upload(file: Union[UploadFile, BinaryIO], declared_mime_type: str | None = None) -> tuple[bytes, str]:
    """
    Validate an uploaded file and return content and validated MIME type.
    
    Args:
        file: File-like object from upload (UploadFile or BinaryIO)
        declared_mime_type: MIME type declared by the client
        
    Returns:
        Tuple of (file_content, validated_mime_type)
        
    Raises:
        ValueError: If file validation fails
    """
    # Read file content
    try:
        # Try async read first (for UploadFile and similar async file objects)
        if hasattr(file, 'read'):
            # Check if it's a coroutine function
            read_method = getattr(file, 'read')
            if inspect.iscoroutinefunction(read_method) or inspect.iscoroutinefunction(file.read):
                file_content = await read_method()
            else:
                # Call the method and check if result is awaitable
                result = read_method()
                if inspect.isawaitable(result):
                    file_content = await result
                else:
                    file_content = result
            
            # Reset file pointer if possible
            if hasattr(file, 'seek'):
                try:
                    if inspect.iscoroutinefunction(file.seek):
                        await file.seek(0)
                    else:
                        file.seek(0)
                except Exception:
                    pass  # Some file objects don't support seeking
        else:
            raise ValueError("File object must have a 'read' method")
    except Exception as e:
        logger.exception("Error reading file content")
        raise ValueError(f"Failed to read file content: {e}")

    # Ensure we have bytes
    if not isinstance(file_content, bytes):
        raise ValueError(f"Expected bytes from file read, got {type(file_content).__name__}")
    
    # Validate the file
    validated_mime_type = validate_receipt_file(file_content, declared_mime_type)
    
    return file_content, validated_mime_type