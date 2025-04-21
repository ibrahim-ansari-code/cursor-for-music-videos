from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
import uuid
import logging

from Backend.config import settings

logger = logging.getLogger(__name__)

# Initialize BlobServiceClient only if connection string is present
blob_service_client = None
if settings.AZURE_STORAGE_CONNECTION_STRING:
    try:
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        logger.info("Azure Blob Service Client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Azure Blob Service Client: {e}")
else:
    logger.warning("AZURE_STORAGE_CONNECTION_STRING not set. Azure Blob Storage functionality will be disabled.")

async def upload_avatar_to_blob(file, user_id: int) -> str:
    if not blob_service_client:
        raise ConnectionError("Azure Blob Storage client is not initialized. Check connection string.")

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
        logger.error(f"Failed to create or access container '{container_name}': {e}")
        raise

    blob_client = container_client.get_blob_client(blob_name)
    
    try:
        file_content = await file.read()
        await blob_client.upload_blob(file_content, overwrite=True)
        logger.info(f"Successfully uploaded avatar to {container_name}/{blob_name}")
    except Exception as e:
        logger.error(f"Failed to upload blob '{blob_name}' to container '{container_name}': {e}")
        raise

    # Construct the public URL - Assume AZURE_BLOB_PUBLIC_URL might already contain container
    # or is just the base URL (e.g., https://<account>.blob.core.windows.net)
    # We append the blob_name which includes the folder structure.
    public_url = f"{settings.AZURE_BLOB_PUBLIC_URL.rstrip('/')}/{blob_name}"
    logger.info(f"Avatar public URL: {public_url}")
    return public_url 