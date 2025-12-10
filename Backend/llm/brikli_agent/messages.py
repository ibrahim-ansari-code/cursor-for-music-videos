"""
Message handling and formatting for Azure AI conversations
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    Handles Azure AI message operations and formatting

    This class manages message retrieval, processing, and
    addition to conversation threads.
    """

    def __init__(self, client: Any, thread_manager: Any) -> None:
        """Initialize with Azure OpenAI client and thread manager"""
        self.client = client
        self.thread_manager = thread_manager

    async def get_messages(
        self,
        thread_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a thread

        Args:
            thread_id: The thread ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries
        """
        try:
            logger.info(f"Getting messages from thread {thread_id}")

            # Get messages from thread using correct API
            messages_paged = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="asc",
                limit=limit
            )
            messages = list(messages_paged)

            # Convert messages to our format
            result = []
            seen_message_ids = set()  # Track actual message IDs, not content hashes

            for msg in messages:
                # Skip messages without IDs or that we've already processed
                msg_id = getattr(msg, 'id', None)
                if not msg_id or msg_id in seen_message_ids:
                    continue

                # Extract text content from the message (only for messages with valid IDs)
                content_text = ""
                if msg.content:
                    for content in msg.content:
                        # The content structure varies, so we need to handle it dynamically
                        # Check if it's a text content type
                        if hasattr(content, 'type') and getattr(content, 'type', None) == 'text':
                            # Try to extract text value
                            text_obj = getattr(content, 'text', None)
                            if text_obj:
                                # The text object might have a 'value' attribute or be the value itself
                                if hasattr(text_obj, 'value'):
                                    content_text += str(getattr(text_obj, 'value', ''))
                                else:
                                    content_text += str(text_obj)
                        elif isinstance(content, str):
                            # Direct string content
                            content_text += content
                        else:
                            # Skip non-text content types (images, files, etc.)
                            logger.debug(f"Skipping non-text content type: {getattr(content, 'type', 'unknown')}")
                            continue

                # Only add non-empty messages
                if content_text.strip():
                    # Pass the raw role from the message object.
                    # The Pydantic model will handle validation and normalization.
                    final_role = msg.role

                    # Add message ID to seen set
                    seen_message_ids.add(msg_id)

                    result.append({
                        "role": final_role,
                        "content": content_text.strip(),
                        "created_at": msg.created_at,
                        "id": msg_id
                    })

            logger.info(f"Retrieved {len(result)} unique messages from thread {thread_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to get messages: {str(e)}")
            raise

    async def add_user_message_to_thread(self, thread_id: str, message_content: str) -> bool:
        """
        Add user message to thread with error handling and run cleanup

        Args:
            thread_id: The thread ID
            message_content: The user's message content

        Returns:
            bool: True if message was added successfully
        """
        try:
            # Ensure thread is ready (cancel any active runs)
            thread_ready = await self.thread_manager.ensure_thread_ready(thread_id)
            if not thread_ready:
                return False

            # Add the message
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message_content
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add message to thread {thread_id}: {e}")
            return False