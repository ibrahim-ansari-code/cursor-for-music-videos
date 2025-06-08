"""
This module contains background tasks related to blob storage operations,
such as resiliently deleting blobs with retries.
"""
import asyncio
import logging
from Backend.utils.azure_blob import delete_blob_by_url

logger = logging.getLogger(__name__)

async def _delete_blob_in_background(blob_url: str | None) -> None:
    """
    Asynchronously deletes a blob from storage by URL with up to three retry attempts.
    
    If the blob URL is not provided, the function exits immediately. Retries deletion 
    up to three times with a delay between attempts if failures occur.
    """
    if not blob_url:
        return

    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5

    for attempt in range(MAX_RETRIES):
        try:
            # Now calling the async function directly
            await delete_blob_by_url(blob_url)
            logger.info("Successfully deleted old blob %s on attempt %d", blob_url, attempt + 1)
            return  # Exit successfully
        except Exception as e:
            logger.warning(
                "Failed to delete blob %s on attempt %d/%d. Retrying in %d seconds...",
                blob_url,
                attempt + 1,
                MAX_RETRIES,
                RETRY_DELAY_SECONDS,
                exc_info=True
            )
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY_SECONDS)
            else:
                logger.error("Failed to delete blob %s after %d attempts.", blob_url, MAX_RETRIES)
                raise e # Re-raise the exception on the final attempt 