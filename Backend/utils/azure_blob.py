import logging
import uuid

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob.aio import BlobServiceClient
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
        logger.error(f"Failed to initialize Azure Blob Service Client: {e}")
else:
    logger.warning(
        "AZURE_STORAGE_CONNECTION_STRING not set. Azure Blob Storage functionality will be disabled.")


async def upload_avatar_to_blob(file: UploadFile, user_id: str) -> str:
    """
    Uploads a user avatar file to the Azure Blob Storage "avatars" container
    and returns its public URL.

    Generates a unique blob name using the user ID and a UUID to prevent
    filename collisions. Creates the container if it does not exist, uploads
    the file content asynchronously, and constructs the public URL of the
    uploaded avatar.

    Args:
        file: The file-like object representing the avatar to upload.
        user_id (str): The string ID of the user whose avatar is being
            uploaded.

    Returns:
        str: The public URL of the uploaded avatar file.

    Raises:
        ConnectionError: If the Azure Blob Storage client is not initialized.
        Exception: If container creation or file upload fails.
    """
    if not blob_service_client:
        raise ConnectionError(
            "Azure Blob Storage client is not initialized. Check connection string.")

    container_name = "avatars"
    # Use a unique identifier to prevent filename collisions and potential overwrites
    blob_name = f"user_{user_id}/{uuid.uuid4()}_{file.filename}"

    container_client = blob_service_client.get_container_client(container_name)
    try:
        await container_client.create_container()
        logger.info(f"Container '{container_name}' created.")
    except ResourceExistsError:
        logger.debug(f"Container '{container_name}' already exists.")
        pass  # container already exists
    except Exception as e:
        logger.error(
            f"Failed to create or access container '{container_name}': {e}")
        raise

    blob_client = container_client.get_blob_client(blob_name)

    try:
        file_content = await file.read()
        await blob_client.upload_blob(file_content, overwrite=True)
        logger.info(
            f"Successfully uploaded avatar to {container_name}/{blob_name}")
    except Exception as e:
        logger.error(
            f"Failed to upload blob '{blob_name}' to container '{container_name}': {e}")
        raise

    # Construct the public URL - Assume AZURE_BLOB_PUBLIC_URL might already contain container
    # or is just the base URL (e.g., https://<account>.blob.core.windows.net)
    # We append the blob_name which includes the folder structure.
    public_url = f"{settings.AZURE_BLOB_PUBLIC_URL.rstrip('/')}/{blob_name}"
    logger.info(f"Avatar public URL: {public_url}")
    return public_url


async def upload_lease_to_blob(file: UploadFile, user_id: str) -> str:
    """
    Asynchronously uploads a lease file to Azure Blob Storage and returns its
    public URL.

    Uploads the provided file to the 'lease-uploads' container, generating a
    unique blob name using the user ID and a UUID to prevent collisions.
    Creates the container if it does not exist. Returns the public URL of the
    uploaded file.

    Args:
        file (UploadFile): The lease file to upload.
        user_id (str): The user identifier used to namespace the uploaded file.

    Returns:
        str: The public URL of the uploaded lease file.

    Raises:
        ConnectionError: If the Azure Blob Storage client is not initialized.
        Exception: If container creation or file upload fails.
    """
    if not blob_service_client:
        raise ConnectionError(
            "Azure Blob Storage client is not initialized. Check connection string.")

    container_name = "lease-uploads"
    # Use a unique identifier to prevent filename collisions and potential overwrites
    blob_name = f"user_{user_id}/{uuid.uuid4()}_{file.filename}"

    container_client = blob_service_client.get_container_client(container_name)
    try:
        await container_client.create_container()
        logger.info(f"Container '{container_name}' created.")
    except ResourceExistsError:
        logger.debug(f"Container '{container_name}' already exists.")
        pass  # container already exists
    except Exception as e:
        logger.error(
            f"Failed to create or access container '{container_name}': {e}")
        raise

    blob_client = container_client.get_blob_client(blob_name)

    try:
        file_content = await file.read()
        await blob_client.upload_blob(file_content, overwrite=True)
        logger.info(
            f"Successfully uploaded lease PDF to {container_name}/{blob_name}")
    except Exception as e:
        logger.error(
            f"Failed to upload blob '{blob_name}' to container '{container_name}': {e}")
        raise

    # Construct the public URL
    public_url = f"{settings.AZURE_BLOB_PUBLIC_URL.rstrip('/')}/{blob_name}"
    logger.info(f"Lease PDF public URL: {public_url}")

    return public_url
