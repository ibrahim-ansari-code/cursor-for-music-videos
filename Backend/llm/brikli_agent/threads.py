"""
Thread management operations for Azure AI conversations
"""
import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from Backend.models.agent import UserAgentThread

logger = logging.getLogger(__name__)


class ThreadManager:
    """
    Manages Azure AI conversation threads

    This class handles thread lifecycle operations including creation,
    deletion, readiness checks, and user-thread associations.
    """

    def __init__(self, client: Any) -> None:
        """Initialize with Azure OpenAI client"""
        self.client = client

    async def create_thread(self) -> str:
        """
        Create a new conversation thread

        Returns:
            str: The thread ID
        """
        try:
            logger.info("Creating new thread")
            # Use OpenAI Assistants API: client.beta.threads.create()
            thread = self.client.beta.threads.create()
            logger.info(f"Created thread with ID: {thread.id}")
            return thread.id
        except Exception as e:
            logger.error(f"Failed to create thread: {str(e)}")
            raise

    async def delete_thread(self, thread_id: str) -> bool:
        """
        Delete a thread from Azure OpenAI

        Args:
            thread_id: The thread ID to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            logger.info(f"Deleting thread {thread_id}")
            # Delete the thread using OpenAI API
            self.client.beta.threads.delete(thread_id)
            logger.info(f"Successfully deleted thread {thread_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete thread {thread_id}: {str(e)}")
            # Don't raise - thread might already be deleted or not exist
            return False

    async def ensure_thread_ready(self, thread_id: str) -> bool:
        """
        Ensure thread is ready for new messages by canceling any active runs

        Args:
            thread_id: The thread ID to check

        Returns:
            bool: True if thread is ready for new messages
        """
        try:
            # List active runs for this thread
            runs = self.client.beta.threads.runs.list(
                thread_id=thread_id,
                limit=10,  # Check more runs
                order="desc"
            )

            canceled_any = False
            for run in runs:
                # Cancel ANY non-completed run to ensure clean state
                if run.status not in ["completed", "failed", "cancelled", "expired"]:
                    logger.warning(f"Found non-completed run {run.id} with status {run.status}, canceling...")
                    try:
                        self.client.beta.threads.runs.cancel(
                            thread_id=thread_id,
                            run_id=run.id
                        )
                        logger.info(f"Successfully canceled run {run.id}")
                        canceled_any = True
                    except Exception as cancel_error:
                        logger.error(f"Failed to cancel run {run.id}: {cancel_error}")

            # If we canceled runs, wait a moment for cleanup
            if canceled_any:
                await asyncio.sleep(0.5)

            return True

        except Exception as e:
            logger.error(f"Error checking thread readiness: {e}")
            return False

    async def get_user_id_from_thread(self, thread_id: str, session: AsyncSession) -> UUID:
        """
        Get user ID from thread mapping

        Args:
            thread_id: The thread ID to lookup
            session: Database session

        Returns:
            User ID associated with the thread
        """
        result = await session.execute(
            select(UserAgentThread).where(UserAgentThread.thread_id == thread_id)
        )
        thread_mapping = result.scalar_one_or_none()

        if thread_mapping:
            return thread_mapping.user_id
        else:
            logger.error(f"No user found for thread {thread_id}")
            raise ValueError(f"No user found for thread {thread_id}")