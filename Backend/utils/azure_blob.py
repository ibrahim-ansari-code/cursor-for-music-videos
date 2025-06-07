import logging
import uuid
import functools
from uuid import UUID as PythonUUID

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import ContentSettings
from fastapi import UploadFile

from Backend.config import settings

logger = logging.getLogger(__name__)

# Initialize BlobServiceClient only if connection string is present
blob_service_client = None
if settings.AZURE_STORAGE_CONNECTION_STRING:
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING)
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
    """Internal helper to upload a file to Azure Blob Storage."""
    if not blob_service_client:
        raise ConnectionError(
            "Azure Blob Storage client is not initialized. Check connection string.")

    original_filename = file.filename if file.filename is not None else default_filename_prefix
    # Basic sanitization: replace spaces and common problematic characters.
    # For more robust sanitization, consider a library or more extensive regex.
    safe_filename_suffix = "".join(c if c.isalnum() or c in (
        '.', '-', '_') else '_' for c in original_filename)
    safe_filename_suffix = safe_filename_suffix[-safe_filename_suffix_limit:]

    blob_name = f"user_{str(user_id)}/{uuid.uuid4()}_{safe_filename_suffix}"

    container_client = blob_service_client.get_container_client(container_name)
    try:
        await container_client.create_container()
        logger.info("Container '%s' created or already exists.",
                    container_name)
    except ResourceExistsError:
        logger.debug("Container '%s' already exists.", container_name)
    except Exception as e:
        logger.error("Failed to create or access container '%s': %s",
                     container_name, e)
        raise

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
        # FastAPI's UploadFile exposes a synchronous close()
        await file.close()
        logger.info("Successfully uploaded %s to %s/%s",
                    default_filename_prefix, container_name, blob_name)
    except Exception as e:
        logger.error("Failed to upload blob '%s' to container '%s': %s",
                     blob_name, container_name, e)
        raise

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


async def delete_blob_by_url(blob_url: str) -> bool:
    """
    Deletes a blob from Azure Blob Storage given its full public URL.

    Parses the container and blob name from the URL based on the configured
    AZURE_BLOB_PUBLIC_URL. Handles cases where the blob might not exist.

    Args:
        blob_url: The full public URL of the blob to delete.

    Returns:
        True if the blob was deleted or did not exist, False if an error occurred.
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

    except Exception as e:
        logger.error("Failed to delete blob '%s': %s",
                     blob_url, e, exc_info=True)
        return False
