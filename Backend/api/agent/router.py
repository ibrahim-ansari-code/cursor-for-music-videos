"""
Agent API endpoints
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.api.auth.dependencies import get_current_user_sse
from Backend.database import get_session
from Backend.models.user import User
from Backend.api.agent.schemas import (
    ChatMessageRequest,
    ChatStartResponse,
    ChatStatusResponse,
    ChatHistoryResponse,
    ConversationListResponse
)
from Backend.api.agent.service import AgentService
from Backend.llm.agent_service import BrikliAgentService

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


# Main agent endpoints
@router.post("/chat", response_model=ChatStartResponse)
async def start_chat(
    request: ChatMessageRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Start a new chat with the AI agent or continue existing conversation
    
    This endpoint:
    1. Creates or retrieves a conversation thread for the user
    2. Sends the user's message to the Azure AI Agent
    3. Returns thread and run IDs for status polling
    """
    service = AgentService(session)
    
    try:
        result = await service.start_chat(current_user.id, request.content)
        return ChatStartResponse(**result)
    except Exception as e:
        logger.error(f"Error starting chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start chat. Please try again."
        )


@router.get("/chat/status", response_model=ChatStatusResponse)
async def get_chat_status(
    thread_id: str,
    run_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Check the status of a chat run and get the response when ready
    
    Poll this endpoint to check if the agent has completed processing.
    Returns the agent's response when status is 'completed'.
    """
    service = AgentService(session)
    
    try:
        result = await service.get_chat_status(
            current_user.id,
            thread_id,
            run_id
        )
        return ChatStatusResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting chat status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat status"
        )

@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get chat history for the current user
    
    Returns the most recent messages from the user's active conversation.
    """
    service = AgentService(session)
    
    try:
        result = await service.get_chat_history(current_user.id, limit)
        return ChatHistoryResponse(**result)
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat history"
        )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    List all conversations for the current user
    
    Returns a summary of all chat threads, ordered by most recent activity.
    """
    service = AgentService(session)
    
    try:
        result = await service.list_conversations(current_user.id)
        return ConversationListResponse(**result)
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list conversations"
        )

# Streaming endpoint
@router.post("/chat/stream")
async def stream_chat(
    request: ChatMessageRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user_sse)
):
    """
    Stream chat response in real-time using Server-Sent Events
    
    This endpoint provides real-time streaming of Azure AI agent responses
    using native Azure AI Foundry streaming capabilities.
    """
    try:
        # Get or create user's thread
        service = AgentService(session)
        user_thread = await service.get_or_create_thread(current_user.id)
        
        # Initialize streaming service
        streaming_service = BrikliAgentService()
        
        # Stream the response
        async def generate_stream():
            try:
                # Set SSE headers
                yield f"data: {json.dumps({'type': 'start', 'message': 'Starting stream...'})}\n\n"
                
                # Stream chat response
                async for chunk in streaming_service.add_message_and_stream(
                    user_thread,
                    request.content
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"Error during streaming: {str(e)}")
                # Send error message to client before closing connection
                yield f"data: {json.dumps({'type': 'error', 'message': 'Streaming error occurred'})}\n\n"
                # Ensure connection is properly closed
                return
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in streaming chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start streaming chat"
        )


@router.post("/chat/clear")
async def clear_chat(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Clear chat history for the current user
    
    This endpoint deletes the user's current thread from Azure AI
    and removes the thread mapping from the database.
    """
    try:
        service = AgentService(session)
        success = await service.clear_chat(current_user.id)
        
        message = "Chat history cleared successfully" if success else "Chat history partially cleared (Azure deletion failed)"
        return {"success": success, "message": message}
        
    except Exception as e:
        logger.error(f"Error clearing chat for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear chat history"
        )


# Health check endpoint
@router.get("/health")
async def agent_health():
    """Check if the agent service is healthy"""
    return {
        "status": "healthy",
        "service": "agent",
        "message": "Agent service is operational"
    }
