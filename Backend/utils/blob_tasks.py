"""
This module contains background tasks related to blob storage operations,
such as resiliently deleting blobs with retries.
"""
import asyncio
import logging
from Backend.utils.azure_blob import delete_blob_by_url

logger = logging.getLogger(__name__)

async def delete_blob_in_background(blob_url: str | None) -> None:
    """
    Asynchronously deletes a blob from storage by URL with up to three retry attempts.
    
    If the blob URL is not provided, the function exits immediately. Retries deletion 
    up to three times with a delay between attempts if failures occur.
    """
    if not blob_url:
        return

    max_retries = 3
    retry_delay_seconds = 5

    for attempt in range(max_retries):
        try:
            # The retry loop now checks the return value of delete_blob_by_url.
            # If it returns False, the loop continues to the next attempt.
            if await delete_blob_by_url(blob_url):
                logger.info("Successfully deleted blob %s on attempt %d.", blob_url, attempt + 1)
                return  # Exit successfully
            
            logger.warning("Attempt %d/%d to delete blob %s failed.", 
                         attempt + 1, max_retries, blob_url)

        except Exception:
            logger.warning(
                "Exception on attempt %d/%d to delete blob %s.",
                attempt + 1, max_retries, blob_url, exc_info=True
            )
            if attempt >= max_retries - 1:
                logger.exception("Failed to delete blob %s after final attempt.", blob_url)
                raise

        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay_seconds)

    logger.error("Failed to delete blob %s after %d attempts.", blob_url, max_retries)