"""
Service layer for Agent functionality
"""
import logging
import asyncio
from typing import Any, Optional, cast
from uuid import UUID
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc

from Backend.models.agent import UserAgentThread
from Backend.llm.brikli_agent import BrikliAgentService
from Backend.api.agent.schemas import ChatMessage, MessageRole

logger = logging.getLogger(__name__)

class AgentService:
    """Service class for agent-related operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.agent_client: Optional[BrikliAgentService] = None
        self._agent_client_lock = asyncio.Lock()
        
    async def _get_agent_client(self) -> BrikliAgentService:
        """Lazy initialization of agent client with thread-safe access"""
        if self.agent_client is None:
            async with self._agent_client_lock:
                # Double-check pattern to avoid unnecessary locking
                if self.agent_client is None:
                    self.agent_client = BrikliAgentService()
        return self.agent_client
    
    async def start_chat(self, user_id: UUID, message: str) -> dict[str, Any]:
        """
        Start a new chat or continue existing conversation
        
        Args:
            user_id: The user's ID
            message: The user's message
            
        Returns:
            Dict containing thread_id, run_id, and status
        """
        try:
            agent = await self._get_agent_client()
            
            # Get or create thread for user
            thread_id = await self.get_or_create_thread(user_id)
            
            # Add message and create run
            result = await agent.add_message_and_run(thread_id, message)
            
            return result
            
        except Exception as e:
            logger.error(f"Error starting chat for user {user_id}: {str(e)}")
            raise
    
    async def get_chat_status(
        self, 
        user_id: UUID, 
        thread_id: str, 
        run_id: str
    ) -> dict[str, Any]:
        """
        Get the status of a chat run
        
        Args:
            user_id: The user's ID (for verification)
            thread_id: The Azure thread ID
            run_id: The Azure run ID
            
        Returns:
            Dict containing status and optional message/error
        """
        # Verify thread ownership
        await self._verify_thread_ownership(user_id, thread_id)
        
        agent = await self._get_agent_client()
        return await agent.get_run_status(thread_id, run_id, self.session)
    
    async def get_chat_history(
        self, 
        user_id: UUID, 
        limit: int = 20
    ) -> dict[str, Any]:
        """
        Get chat history for a user
        
        Args:
            user_id: The user's ID
            limit: Maximum number of messages to return
            
        Returns:
            Dict containing messages and metadata
        """
        # Get user's active thread
        thread_mapping = await self._get_active_thread(user_id)
        
        if not thread_mapping:
            return {
                "messages": [],
                "thread_id": None,
                "total": 0
            }
        
        agent = await self._get_agent_client()
        raw_messages = await agent.get_messages(thread_mapping.thread_id, limit)
        
        # Convert raw messages to ChatMessage format using Pydantic validation
        formatted_messages = []
        for msg in raw_messages:
            try:
                # Let Pydantic handle the validation, which is safer
                formatted_messages.append(ChatMessage.model_validate(msg))
            except Exception:
                # Skip any messages that fail validation to avoid crashing
                continue
        
        return {
            "messages": formatted_messages,
            "thread_id": thread_mapping.thread_id,
            "total": len(formatted_messages)
        }
    
    async def list_conversations(self, user_id: UUID) -> dict[str, Any]:
        """
        List all conversations for a user
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict containing list of conversations
        """
        result = await self.session.execute(
            select(UserAgentThread)
            .where(UserAgentThread.user_id == user_id)
            .order_by(desc(UserAgentThread.last_active))
        )
        threads = result.scalars().all()
        
        conversations = []
        for thread in threads:
            conversations.append({
                "id": str(thread.id),
                "thread_id": thread.thread_id,
                "created_at": thread.created_at.isoformat(),
                "last_active": thread.last_active.isoformat(),
                "is_active": thread.is_active
            })
        
        return {
            "conversations": conversations,
            "total": len(conversations)
        }
    
    async def get_or_create_thread(self, user_id: UUID) -> str:
        """Get existing thread or create new one for user"""
        
        # Check for existing active thread
        thread_mapping = await self._get_active_thread(user_id)
        
        if thread_mapping:
            # Update last active timestamp
            thread_mapping.last_active = datetime.now(UTC)
            await self.session.commit()
            return thread_mapping.thread_id
        
        # Create new thread
        agent = await self._get_agent_client()
        thread_id = await agent.create_thread()
        
        # Save mapping
        thread_mapping = UserAgentThread(
            user_id=user_id,
            thread_id=thread_id
        )
        self.session.add(thread_mapping)
        await self.session.commit()
        
        return thread_id
    
    async def _get_active_thread(self, user_id: UUID) -> Optional[UserAgentThread]:
        """Get active thread for user"""
        result = await self.session.execute(
            select(UserAgentThread).where(
                UserAgentThread.user_id == user_id,
                UserAgentThread.is_active == True  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
    
    async def _verify_thread_ownership(self, user_id: UUID, thread_id: str) -> None:
        """Verify that a thread belongs to the user"""
        result = await self.session.execute(
            select(UserAgentThread).where(
                UserAgentThread.thread_id == thread_id,
                UserAgentThread.user_id == user_id
            )
        )
        if not result.scalar_one_or_none():
            raise ValueError("Thread not found or access denied")
    
    async def clear_chat(self, user_id: UUID) -> bool:
        """
        Clear chat history for a user by deleting the current thread
        
        Args:
            user_id: The user's ID
            
        Returns:
            bool: True if chat was cleared successfully
        """
        try:
            # Get current active thread
            thread_mapping = await self._get_active_thread(user_id)
            
            if not thread_mapping:
                return True  # Nothing to clear
            
            # Delete thread from Azure AI
            agent = await self._get_agent_client()
            deleted = await agent.delete_thread(thread_mapping.thread_id)
            
            # Remove thread mapping from database (regardless of Azure deletion result)
            await self.session.delete(thread_mapping)
            await self.session.commit()
            
            return deleted  # Return the actual result of Azure deletion
            
        except Exception as e:
            logger.error(f"Failed to clear chat for user {user_id}: {str(e)}")
            raise
    