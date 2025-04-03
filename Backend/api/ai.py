import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.database import get_session
from backend.models.user import User, UserType
from backend.api.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/ai",
    tags=["ai"],
)

# API models
class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[str] = None  # Additional context for the AI
    document_ids: Optional[List[str]] = None  # IDs of documents to reference

class ChatResponse(BaseModel):
    response: str
    messages: List[ChatMessage]

# AI endpoints
@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    chat_request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """AI chat endpoint for general property management assistance"""
    # This is a placeholder/stub for connecting to an AI service later
    # In a real implementation, this would connect to an AI model or service
    
    if not chat_request.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages provided"
        )
    
    # Get the last user message
    last_message = chat_request.messages[-1]
    
    # Simple response based on keywords in the last message
    query = last_message.content.lower()
    
    # Mock responses based on keywords
    responses = {
        "rent": "Rent payments are due on the 1st of each month. Late fees apply after the 5th. You can pay through the tenant portal or send a check to the management office.",
        "maintenance": "For maintenance requests, please use the maintenance form in the tenant portal. For emergencies, call our 24/7 maintenance hotline at 555-123-4567.",
        "lease": "Your lease agreement contains all terms and conditions of your tenancy. You can view and download your lease documents from your account portal.",
        "amenities": "Our properties offer various amenities including gym facilities, communal spaces, and parking. Check your specific property details for the amenities available to you.",
        "contact": "You can reach our property management team at contact@propertymanager.com or call 555-987-6543 during business hours (9AM-5PM, Monday-Friday).",
        "payment": "We accept payments via direct deposit, credit card, or check. Processing fees may apply for credit card payments.",
        "how do i": "You can find step-by-step guides for most common tasks in our Help Center. Is there a specific task you need help with?",
        "default": "Thank you for your question. Our AI assistant is currently being integrated. Please contact your property manager for specific help with your question."
    }
    
    # Find a response based on keywords
    response_text = responses["default"]
    for keyword, response in responses.items():
        if keyword in query:
            response_text = response
            break
    
    # Add response to chat history
    updated_messages = chat_request.messages.copy()
    updated_messages.append(ChatMessage(role="assistant", content=response_text))
    
    logger.info(f"AI chat response generated for user {current_user.id}")
    return ChatResponse(
        response=response_text,
        messages=updated_messages
    )

@router.post("/document-qa", response_model=ChatResponse)
async def document_qa(
    chat_request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """AI endpoint for answering questions about specific documents"""
    # This is a placeholder/stub for connecting to an AI service later
    # In a real implementation, this would connect to a document Q&A model
    
    if not chat_request.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages provided"
        )
    
    if not chat_request.document_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No document IDs provided for Q&A"
        )
    
    # Get the last user message
    last_message = chat_request.messages[-1]
    
    # Placeholder response
    response_text = f"I've analyzed the documents you referenced (IDs: {', '.join(chat_request.document_ids)}). In the future, I'll provide specific answers based on their content. For now, please contact your property manager for assistance with document-specific questions."
    
    # Add response to chat history
    updated_messages = chat_request.messages.copy()
    updated_messages.append(ChatMessage(role="assistant", content=response_text))
    
    logger.info(f"Document Q&A response generated for user {current_user.id}")
    return ChatResponse(
        response=response_text,
        messages=updated_messages
    )

@router.post("/tenant-support", response_model=ChatResponse)
async def tenant_support(
    chat_request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """AI endpoint specifically for tenant support"""
    # Verify user is a tenant
    if current_user.user_type != UserType.TENANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only for tenant users"
        )
    
    if not chat_request.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages provided"
        )
    
    # Get the last user message
    last_message = chat_request.messages[-1]
    query = last_message.content.lower()
    
    # Tenant-specific responses
    tenant_responses = {
        "repair": "For repair requests, please go to the Maintenance section and submit a new request. For emergency repairs, please call our 24/7 hotline at 555-123-4567.",
        "noise": "If you're experiencing noise issues from neighbors, first try to speak with them directly. If the issue persists, you can file a complaint through your tenant portal or contact the property manager.",
        "rent increase": "Rent increases are governed by your lease agreement and local regulations. Typically, you will be notified in writing at least 30 days before any increase takes effect.",
        "renew": "To renew your lease, please contact your property manager or use the lease renewal option in your tenant portal at least 30 days before your current lease expires.",
        "move out": "When planning to move out, please provide written notice according to your lease terms (typically 30-60 days). Schedule a move-out inspection and ensure the unit is clean to receive your full security deposit.",
        "key": "If you've lost your keys, contact the property manager during business hours for a replacement. There may be a fee for key replacement.",
        "pet": "Our pet policy is detailed in your lease agreement. Generally, pets require approval and may incur additional fees or deposits.",
        "default": "As your tenant support assistant, I'm here to help with any questions about your tenancy. For specific account issues, please contact your property manager directly."
    }
    
    # Find a response based on keywords
    response_text = tenant_responses["default"]
    for keyword, response in tenant_responses.items():
        if keyword in query:
            response_text = response
            break
    
    # Add response to chat history
    updated_messages = chat_request.messages.copy()
    updated_messages.append(ChatMessage(role="assistant", content=response_text))
    
    logger.info(f"Tenant support response generated for user {current_user.id}")
    return ChatResponse(
        response=response_text,
        messages=updated_messages
    )
