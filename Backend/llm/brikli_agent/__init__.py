"""
Azure AI Agent Service Client

This module provides the interface to Azure AI Foundry's Agent (Assistant) service.
It handles all communication with the Azure AI Agent API.
"""
import logging
from typing import Any, AsyncGenerator, Dict, List

from .client import AzureAIClient
from .threads import ThreadManager
from .messages import MessageHandler
from .runs import RunManager
from .tools import ToolManager
from .streaming import StreamingManager

logger = logging.getLogger(__name__)


class BrikliAgentService:
    """
    Service class for interacting with Azure AI Agent (Assistant API)

    This class manages:
    - Thread creation and management
    - Message sending and retrieval
    - Run creation and status monitoring
    - Tool execution handling
    - Streaming operations
    """

    def __init__(self) -> None:
        """Initialize the agent service with Azure OpenAI client and components"""
        # Initialize Azure OpenAI client
        self.azure_client = AzureAIClient()
        # Use the full OpenAI client for threads/messages/runs
        self.client = self.azure_client.client

        # Set assistant_id early for component initialization
        self.assistant_id = self.azure_client.assistant_id

        # Initialize component managers with the full client
        self.thread_manager = ThreadManager(self.client)
        self.message_handler = MessageHandler(self.client, self.thread_manager)
        self.tool_manager = ToolManager(self.client, self.assistant_id, self.thread_manager)
        self.run_manager = RunManager(self.client, self.assistant_id, self.tool_manager)
        self.streaming_manager = StreamingManager(
            self.client,
            self.assistant_id,
            self.message_handler,
            self.tool_manager
        )

        logger.info("BrikliAgentService initialized successfully")

    # Thread management methods
    async def create_thread(self) -> str:
        """Create a new conversation thread"""
        return await self.thread_manager.create_thread()

    async def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread from Azure AI"""
        return await self.thread_manager.delete_thread(thread_id)

    # Message handling methods
    async def get_messages(self, thread_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get messages from a thread"""
        return await self.message_handler.get_messages(thread_id, limit)

    # Run management methods
    async def add_message_and_run(
        self,
        thread_id: str,
        message_content: str
    ) -> Dict[str, Any]:
        """Add a user message to the thread and create a run"""
        return await self.run_manager.add_message_and_run(thread_id, message_content)

    async def get_run_status(
        self,
        thread_id: str,
        run_id: str,
        session=None
    ) -> Dict[str, Any]:
        """Get the status of a run and handle tool execution when needed"""
        return await self.run_manager.get_run_status(thread_id, run_id, session)

    # Tool management methods
    def register_tools_with_assistant(self) -> Any:
        """Register tools with the Azure Assistant"""
        return self.tool_manager.register_tools_with_assistant()

    # Streaming methods
    async def stream_chat(
        self,
        thread_id: str,
        message_content: str
    ) -> AsyncGenerator[str, None]:
        """Stream chat response using Azure AI Foundry's native streaming"""
        async for chunk in self.streaming_manager.stream_chat(thread_id, message_content):
            yield chunk

    async def add_message_and_stream(
        self,
        thread_id: str,
        message_content: str
    ) -> AsyncGenerator[str, None]:
        """Convenience method that combines message addition and streaming"""
        async for chunk in self.streaming_manager.add_message_and_stream(thread_id, message_content):
            yield chunk

    # Legacy compatibility methods (delegating to internal managers)
    async def _get_user_id_from_thread(self, thread_id: str, session):
        """Get user ID from thread mapping (legacy compatibility)"""
        return await self.thread_manager.get_user_id_from_thread(thread_id, session)

    async def _execute_tool_call(self, tool_call, thread_id: str) -> Dict[str, Any]:
        """Execute a single tool call (legacy compatibility)"""
        from Backend.database import get_session

        async for session in get_session():
            return await self.tool_manager.execute_tool_call(tool_call, thread_id, session)

        return {"error": "No database session available"}

    async def _handle_tool_calls_streaming(self, thread_id: str, run_id: str, required_action) -> None:
        """Handle tool calls during streaming (legacy compatibility)"""
        await self.tool_manager.handle_tool_calls_streaming(thread_id, run_id, required_action)

    async def _ensure_thread_ready(self, thread_id: str) -> bool:
        """Ensure thread is ready for new messages (legacy compatibility)"""
        return await self.thread_manager.ensure_thread_ready(thread_id)