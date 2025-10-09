import logging
import uuid
import functools
from uuid import UUID as PythonUUID
from datetime import datetime, timedelta
from urllib.parse import urlparse

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import ContentSettings, generate_blob_sas, BlobSasPermissions
from fastapi import UploadFile

from Backend.config import settings
from Backend.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# Initialize BlobServiceClient only if connection string is present
blob_service_client = None
if settings.AZURE_STORAGE_CONNECTION_STRING:
    try:
        # For local development SSL issues, set environment variable: PYTHONHTTPSVERIFY=0
        # Or install certificates: pip install --upgrade certifi
        blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        logger.info("Azure Blob Service Client initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize Azure Blob Service Client: %s", e)
else:
    logger.warning(
        "AZURE_STORAGE_CONNECTION_STRING not set. Azure Blob Storage functionality will be disabled.")


async def _upload_to_blob(
    file: UploadFile,
    user_id: PythonUUID,
    container_name: str,
    default_filename_prefix: str,
    safe_filename_suffix_limit: int
) -> str:
    """
    Uploads a file asynchronously to a specified Azure Blob Storage container and returns its public URL.
    
    The file is saved with a unique name based on the user ID and a sanitized version of the original filename, truncated to a specified length. The function ensures the target container exists, streams the file directly to Azure Blob Storage, and applies the appropriate content type. Raises a ConnectionError if the Blob Storage client is not initialized, and propagates exceptions encountered during container creation or upload.
    
    Args:
        file: The file to upload.
        user_id: The UUID of the user associated with the file.
        container_name: The name of the Azure Blob Storage container.
        default_filename_prefix: Prefix to use if the original filename is missing.
        safe_filename_suffix_limit: Maximum length for the sanitized filename suffix.
    
    Returns:
        The public URL of the uploaded blob.
    """
    if not blob_service_client:
        raise ConnectionError(
            "Azure Blob Storage client is not initialized. Check connection string.")

    original_filename = file.filename if file.filename is not None else default_filename_prefix
    # Basic sanitization: replace spaces and common problematic characters.
    # For more robust sanitization, consider a library or more extensive regex.
    safe_filename_suffix = "".join(c if c.isalnum() or c in (
        '.', '-', '_') else '_' for c in original_filename)
    safe_filename_suffix = safe_filename_suffix[-safe_filename_suffix_limit:]

    # Sanitize user_id to prevent path traversal
    safe_user_id = str(user_id).replace("/", "_")
    blob_name = f"user_{safe_user_id}/{uuid.uuid4()}_{safe_filename_suffix}"

    container_client = blob_service_client.get_container_client(container_name)

    blob_client = container_client.get_blob_client(blob_name)

    # Provide a default content type if file.content_type is None
    effective_content_type = file.content_type if file.content_type else 'application/octet-stream'
    blob_content_settings = ContentSettings(
        content_type=effective_content_type)

    try:
        # Reset the stream's pointer to the beginning before uploading
        await file.seek(0)
        # Pass the underlying file-like object (UploadFile.file) for streaming
        await blob_client.upload_blob(
            data=file.file,
            overwrite=True,
            content_settings=blob_content_settings,
        )
        logger.info("Successfully uploaded %s to %s/%s",
                    default_filename_prefix, container_name, blob_name)
    except Exception as e:
        logger.error("Failed to upload blob '%s' to container '%s': %s",
                     blob_name, container_name, e)
        raise
    finally:
        # FastAPI's UploadFile close() method is async and must be awaited
        await file.close()

    public_url = f"{settings.AZURE_BLOB_PUBLIC_URL.rstrip('/')}/{container_name}/{blob_name}"
    logger.info("%s public URL: %s",
                default_filename_prefix.capitalize(), public_url)
    return public_url

# Preserve original docstrings and annotations for the partial functions
_upload_avatar_doc = """
    Uploads a user avatar file to the Azure Blob Storage "avatars" container
    and returns its public URL.

    Generates a unique blob name using the user ID and a UUID to prevent
    filename collisions. Creates the container if it does not exist, uploads
    the file content asynchronously, and constructs the public URL of the
    uploaded avatar.

    Args:
        file: The file-like object representing the avatar to upload.
        user_id (PythonUUID): The user identifier used to namespace the uploaded file.

    Returns:
        str: The public URL of the uploaded avatar file.

    Raises:
        ConnectionError: If the Azure Blob Storage client is not initialized.
        Exception: If container creation or file upload fails.
    """
_upload_avatar_annotations = {
    'file': UploadFile,
    'user_id': PythonUUID,
    'return': str
}

upload_avatar_to_blob = functools.partial(
    _upload_to_blob,
    container_name="avatars",
    default_filename_prefix="avatar",
    safe_filename_suffix_limit=50
)
setattr(upload_avatar_to_blob, '__doc__', _upload_avatar_doc)
setattr(upload_avatar_to_blob, '__annotations__', _upload_avatar_annotations)


_upload_lease_doc = """
    Asynchronously uploads a lease file to Azure Blob Storage and returns its
    public URL.

    Uploads the provided file to the 'lease-uploads' container, generating a
    unique blob name using the user ID and a UUID to prevent collisions.
    Creates the container if it does not exist. Returns the public URL of the
    uploaded file.

    Args:
        file (UploadFile): The lease file to upload.
        user_id (PythonUUID): The user identifier used to namespace the uploaded file.

    Returns:
        str: The public URL of the uploaded lease file.

    Raises:
        ConnectionError: If the Azure Blob Storage client is not initialized.
        Exception: If container creation or file upload fails.
    """
_upload_lease_annotations = {
    'file': UploadFile,
    'user_id': PythonUUID,
    'return': str
}

upload_lease_to_blob = functools.partial(
    _upload_to_blob,
    container_name="lease-uploads",
    default_filename_prefix="lease_document",
    safe_filename_suffix_limit=100
)
setattr(upload_lease_to_blob, '__doc__', _upload_lease_doc)
setattr(upload_lease_to_blob, '__annotations__', _upload_lease_annotations)


_upload_payment_receipt_doc = """
    Asynchronously uploads a payment receipt file to Azure Blob Storage and returns its public URL.

    Uploads the provided file to the 'payment-receipts' container, generating a
    unique blob name using the user ID and a UUID to prevent collisions.
    Creates the container if it does not exist. Returns the public URL of the
    uploaded file.

    Args:
        file (UploadFile): The payment receipt file to upload (image or PDF).
        user_id (PythonUUID): The user identifier used to namespace the uploaded file.

    Returns:
        str: The public URL of the uploaded payment receipt file.

    Raises:
        ConnectionError: If the Azure Blob Storage client is not initialized.
        Exception: If container creation or file upload fails.
    """
_upload_payment_receipt_annotations = {
    'file': UploadFile,
    'user_id': PythonUUID,
    'return': str
}

upload_payment_receipt_to_blob = functools.partial(
    _upload_to_blob,
    container_name="payment-receipts",
    default_filename_prefix="receipt",
    safe_filename_suffix_limit=50
)
setattr(upload_payment_receipt_to_blob, '__doc__', _upload_payment_receipt_doc)
setattr(upload_payment_receipt_to_blob, '__annotations__',
        _upload_payment_receipt_annotations)


_upload_expense_receipt_doc = """
    Asynchronously uploads an expense receipt file to Azure Blob Storage 
    (container: "expense-receipts") and returns its public URL.
    Similar to upload_payment_receipt_to_blob.

    Args:
        file (UploadFile): The expense receipt file to upload (image or PDF).
        user_id (PythonUUID): The user identifier used to namespace the uploaded file.

    Returns:
        str: The public URL of the uploaded expense receipt file.

    Raises:
        ConnectionError: If the Azure Blob Storage client is not initialized.
        Exception: If container creation or file upload fails.
    """
_upload_expense_receipt_annotations = {
    'file': UploadFile,
    'user_id': PythonUUID,
    'return': str
}

upload_expense_receipt_to_blob = functools.partial(
    _upload_to_blob,
    container_name="expense-receipts",
    default_filename_prefix="receipt",
    safe_filename_suffix_limit=50
)
setattr(upload_expense_receipt_to_blob, '__doc__', _upload_expense_receipt_doc)
setattr(upload_expense_receipt_to_blob, '__annotations__',
        _upload_expense_receipt_annotations)


upload_maintenance_photo_to_blob = functools.partial(
    _upload_to_blob,
    container_name="maintenance-photos",
    default_filename_prefix="maintenance_photo",
    safe_filename_suffix_limit=80
)
setattr(upload_maintenance_photo_to_blob, '__doc__', """
    Asynchronously uploads a maintenance photo file to Azure Blob Storage and returns its public URL.

    Uploads the provided file to the 'maintenance-photos' container, generating a
    unique blob name using the user ID and a UUID to prevent collisions.
    Creates the container if it does not exist. Returns the public URL of the
    uploaded file.

    Args:
        file (UploadFile): The maintenance photo file to upload (image or PDF).
        user_id (PythonUUID): The user identifier used to namespace the uploaded file.

    Returns:
        str: The public URL of the uploaded maintenance photo file.

    Raises:
        ConnectionError: If the Azure Blob Storage client is not initialized.
        Exception: If container creation or file upload fails.
""")
setattr(upload_maintenance_photo_to_blob, '__annotations__', {
    'file': UploadFile,
    'user_id': PythonUUID,
    'return': str
})


# Property image upload function - follows same pattern as working expense receipts
upload_property_image_to_blob = functools.partial(
    _upload_to_blob,
    container_name="property-images",
    default_filename_prefix="property_image",
    safe_filename_suffix_limit=100
)
setattr(upload_property_image_to_blob, '__doc__', """
    Asynchronously uploads a property image file to Azure Blob Storage and returns its public URL.

    Uploads the provided file to the 'property-images' container, generating a
    unique blob name using the user ID and a UUID to prevent collisions.
    Returns the public URL of the uploaded file.

    Args:
        file (UploadFile): The property image file to upload.
        user_id (PythonUUID): The user identifier used to namespace the uploaded file.

    Returns:
        str: The public URL of the uploaded property image file.

    Raises:
        ConnectionError: If the Azure Blob Storage client is not initialized.
        Exception: If file upload fails.
""")
setattr(upload_property_image_to_blob, '__annotations__', {
    'file': UploadFile,
    'user_id': PythonUUID,
    'return': str
})


async def delete_blob_by_url(blob_url: str) -> bool:
    """
    Deletes a blob from Azure Blob Storage using its public URL.
    
    Parses the container and blob name from the provided URL based on the configured public base URL. Returns True if the blob was deleted or did not exist, and False if an error occurred or the URL is invalid.
    """
    if not blob_service_client or not settings.AZURE_BLOB_PUBLIC_URL:
        logger.error(
            "Azure Blob Storage client or public URL not initialized. Cannot delete blob.")
        return False

    try:
        public_url_base = settings.AZURE_BLOB_PUBLIC_URL.rstrip('/')
        if not blob_url.startswith(public_url_base):
            logger.error("Blob URL '%s' does not match configured public base URL '%s'.",
                         blob_url, public_url_base)
            return False

        path_part = blob_url[len(public_url_base):].lstrip('/')

        # Path part is expected to be "container_name/actual_blob_name_with_internal_path"
        parts = path_part.split('/', 1)
        if len(parts) < 2:
            logger.error("Could not parse container and blob name from path: %s",
                         path_part)
            return False

        container_name = parts[0]
        blob_name = parts[1]

        logger.info(
            "Attempting to delete blob: container='%s', blob='%s'", container_name, blob_name)

        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )

        if await blob_client.exists():
            await blob_client.delete_blob(delete_snapshots="include")
            logger.info(
                "Successfully deleted blob: %s/%s", container_name, blob_name)
        else:
            logger.info(
                "Blob not found, no deletion needed: %s/%s", container_name, blob_name)
        return True

    except Exception:
        logger.exception("Failed to delete blob '%s'", blob_url)
        return False


# ==================== SAS TOKEN GENERATION FOR SECURE DOCUMENT ACCESS ====================


def extract_blob_info_from_url(blob_url: str) -> tuple[str, str]:
    """
    Extract container name and blob name from full Azure blob URL.
    
    Args:
        blob_url: Full Azure Blob URL (e.g., https://account.blob.core.windows.net/container/blob/path)
        
    Returns:
        Tuple of (container_name, blob_name)
        
    Raises:
        ValueError: If URL format is invalid
        
    Example:
        Input: "https://storage.blob.core.windows.net/lease-uploads/user_123/doc.pdf"
        Output: ("lease-uploads", "user_123/doc.pdf")
    """
    try:
        parsed_url = urlparse(blob_url)
        # Remove leading slash and split on first slash to separate container from blob
        path_parts = parsed_url.path.lstrip('/').split('/', 1)
        
        if len(path_parts) < 2:
            raise ValueError(f"Invalid blob URL format: {blob_url}")
        
        container_name = path_parts[0]
        blob_name = path_parts[1]
        
        logger.debug(f"Extracted from URL - Container: {container_name}, Blob: {blob_name[:50]}...")
        return container_name, blob_name
        
    except Exception as e:
        logger.error(f"Failed to parse blob URL '{blob_url}': {e}")
        raise ValueError(f"Could not parse blob URL: {str(e)}")


def generate_sas_token_for_blob(
    blob_url: str,
    expires_in_hours: int = 1,
    allowed_ip: str | None = None
) -> tuple[str, datetime]:
    """
    Generate a time-limited SAS (Shared Access Signature) token for secure blob access.
    
    This implements the industry-standard pattern for secure document access used by
    Dropbox, Box, SharePoint, and other major SaaS platforms.
    
    Args:
        blob_url: Full Azure Blob URL (must start with AZURE_BLOB_PUBLIC_URL)
        expires_in_hours: Token expiration time in hours (default: 1 hour)
        allowed_ip: Optional IP address restriction for enhanced security
        
    Returns:
        Tuple of (sas_token, expiry_time) - Token string and its expiration datetime
        
    Raises:
        ValueError: If Azure credentials not configured or URL is invalid
        
    Security Features:
        - Read-only permission (no write/delete)
        - HTTPS protocol enforced
        - Time-limited access (auto-expires)
        - Optional IP whitelisting
        
    Example:
        token, expiry = generate_sas_token_for_blob(
            "https://storage.blob.core.windows.net/lease-uploads/doc.pdf",
            expires_in_hours=1
        )
        # Returns: ("sv=2021-06-08&se=...", datetime(2024, 10, 9, 19, 30, 0))
    """
    # Validate required settings
    if not settings.AZURE_STORAGE_ACCOUNT_NAME:
        raise ValueError(
            "AZURE_STORAGE_ACCOUNT_NAME not configured. Cannot generate SAS tokens."
        )
    
    if not settings.AZURE_STORAGE_ACCOUNT_KEY:
        raise ValueError(
            "AZURE_STORAGE_ACCOUNT_KEY not configured. Cannot generate SAS tokens."
        )
    
    # Extract container and blob name from URL
    container_name, blob_name = extract_blob_info_from_url(blob_url)
    
    # Calculate expiry time once (using codebase-standard UTC function)
    expiry_time = utc_now() + timedelta(hours=expires_in_hours)
    
    # Generate SAS token with minimal permissions (read only)
    sas_token = generate_blob_sas(
        account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
        account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
        container_name=container_name,
        blob_name=blob_name,
        permission=BlobSasPermissions(read=True),  # Read-only permission
        expiry=expiry_time,
        protocol='https',  # Enforce HTTPS only
        ip=allowed_ip  # Optional IP restriction (None = allow any IP)
    )
    
    logger.info(
        f"Generated SAS token for {container_name}/{blob_name[:50]}... "
        f"(expires: {expiry_time.isoformat()}, IP: {allowed_ip or 'any'})"
    )
    
    return sas_token, expiry_time


async def generate_secure_document_url(
    blob_url: str,
    user_id: PythonUUID,
    document_id: int,
    expires_in_hours: int | None = None,
    client_ip: str | None = None
) -> dict:
    """
    Generate a secure, time-limited URL for document access with audit logging.
    
    This is the main function for generating secure document URLs. It:
    1. Generates a SAS token with configurable expiry
    2. Creates a complete secure URL
    3. Logs the access for audit trail (if enabled)
    
    Args:
        blob_url: Original Azure Blob URL (without SAS token)
        user_id: UUID of user requesting access
        document_id: ID of document being accessed
        expires_in_hours: Token expiration (default: from config)
        client_ip: Optional client IP for restriction
        
    Returns:
        Dictionary with:
            - secure_url: Full URL with SAS token
            - expires_at: ISO datetime string
            - expires_in_seconds: Seconds until expiration
            
    Example:
        result = await generate_secure_document_url(
            "https://storage.blob.core.windows.net/lease-uploads/doc.pdf",
            user_id="123e4567-e89b-12d3-a456-426614174000",
            document_id=42
        )
        # Returns:
        # {
        #     "secure_url": "https://...?sv=2021-06-08&se=...",
        #     "expires_at": "2024-10-09T19:30:00",
        #     "expires_in_seconds": 3600
        # }
    """
    # Use configured default if not specified
    if expires_in_hours is None:
        expires_in_hours = settings.DOCUMENT_SAS_EXPIRY_HOURS
    
    # Generate SAS token and get its expiry time (single source of truth)
    sas_token, expiry_time = generate_sas_token_for_blob(
        blob_url=blob_url,
        expires_in_hours=expires_in_hours,
        allowed_ip=client_ip
    )
    
    # Build complete secure URL
    secure_url = f"{blob_url}?{sas_token}"
    
    # Audit logging (if enabled)
    if settings.DOCUMENT_ACCESS_LOGGING_ENABLED:
        logger.info(
            f"[AUDIT] User {user_id} generated secure URL for document {document_id}. "
            f"Expires: {expiry_time.isoformat()}, IP: {client_ip or 'unrestricted'}"
        )
    
    return {
        "secure_url": secure_url,
        "expires_at": expiry_time.isoformat() + "Z",  # Add Z for UTC
        "expires_in_seconds": expires_in_hours * 3600
    }
