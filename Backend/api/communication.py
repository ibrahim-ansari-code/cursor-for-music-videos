import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, text
from pydantic import BaseModel

from Backend.database import get_session
from Backend.models.message import Message, Conversation, ConversationParticipant, MessageType
from Backend.models.user import User, UserType
from Backend.api.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/messages",
    tags=["messages"],
)

# API models
class MessageBase(BaseModel):
    content: str
    message_type: MessageType = MessageType.DIRECT
    recipient_id: Optional[int] = None

class MessageCreate(MessageBase):
    conversation_id: Optional[int] = None

class MessageResponse(BaseModel):
    id: int
    content: str
    message_type: MessageType
    is_read: bool
    read_at: Optional[datetime] = None
    conversation_id: int
    sender_id: int
    recipient_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConversationBase(BaseModel):
    title: Optional[str] = None
    is_group: bool = False
    participant_ids: List[int]  # List of user IDs to include in the conversation

class ConversationResponse(BaseModel):
    id: int
    title: Optional[str] = None
    is_group: bool
    created_at: datetime
    updated_at: datetime
    latest_message: Optional[MessageResponse] = None
    participants: List[int]  # List of participant user IDs

    class Config:
        from_attributes = True

# API endpoints
@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationBase,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new conversation"""
    # Make sure current user is included in participants
    if current_user.id not in conversation_data.participant_ids:
        conversation_data.participant_ids.append(current_user.id)
    
    # Create conversation
    new_conversation = Conversation(
        title=conversation_data.title,
        is_group=conversation_data.is_group
    )
    session.add(new_conversation)
    await session.flush()  # To get the conversation ID
    
    # Add participants
    for user_id in conversation_data.participant_ids:
        participant = ConversationParticipant(
            conversation_id=new_conversation.id,
            user_id=user_id
        )
        session.add(participant)
    
    await session.commit()
    await session.refresh(new_conversation)
    
    logger.info(f"Conversation created: {new_conversation.id} by user {current_user.id}")
    
    # Format response
    response = ConversationResponse(
        id=new_conversation.id,
        title=new_conversation.title,
        is_group=new_conversation.is_group,
        created_at=new_conversation.created_at,
        updated_at=new_conversation.updated_at,
        participants=conversation_data.participant_ids,
        latest_message=None
    )
    
    return response

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all conversations for the current user"""
    # SQL query to get conversations with latest message for each
    query = """
    WITH user_conversations AS (
        SELECT c.id
        FROM conversations c
        JOIN conversation_participants cp ON c.id = cp.conversation_id
        WHERE cp.user_id = :user_id AND cp.is_active = True
    ),
    latest_messages AS (
        SELECT 
            m.*,
            ROW_NUMBER() OVER (PARTITION BY m.conversation_id ORDER BY m.created_at DESC) as rn
        FROM 
            messages m
        JOIN 
            user_conversations uc ON m.conversation_id = uc.id
    )
    SELECT 
        c.id,
        c.title,
        c.is_group,
        c.created_at,
        c.updated_at,
        m.id as message_id,
        m.content,
        m.message_type,
        m.is_read,
        m.read_at,
        m.conversation_id,
        m.sender_id,
        m.recipient_id,
        m.created_at as message_created_at,
        m.updated_at as message_updated_at,
        (
            SELECT json_agg(cp.user_id)
            FROM conversation_participants cp
            WHERE cp.conversation_id = c.id AND cp.is_active = True
        ) as participants
    FROM 
        conversations c
    JOIN 
        user_conversations uc ON c.id = uc.id
    LEFT JOIN 
        latest_messages m ON c.id = m.conversation_id AND m.rn = 1
    ORDER BY 
        COALESCE(m.created_at, c.created_at) DESC
    """
    
    result = await session.execute(text(query), {"user_id": current_user.id})
    rows = result.mappings().all()
    
    conversations = []
    for row in rows:
        latest_message = None
        if row['message_id']:
            latest_message = MessageResponse(
                id=row['message_id'],
                content=row['content'],
                message_type=row['message_type'],
                is_read=row['is_read'],
                read_at=row['read_at'],
                conversation_id=row['conversation_id'],
                sender_id=row['sender_id'],
                recipient_id=row['recipient_id'],
                created_at=row['message_created_at'],
                updated_at=row['message_updated_at']
            )
        
        conversation = ConversationResponse(
            id=row['id'],
            title=row['title'],
            is_group=row['is_group'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            latest_message=latest_message,
            participants=row['participants'] if row['participants'] else []
        )
        conversations.append(conversation)
    
    return conversations

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    limit: int = 50,
    before_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get messages for a specific conversation"""
    # Check if user is a participant in the conversation
    query = select(ConversationParticipant).where(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id,
        ConversationParticipant.is_active == True
    )
    result = await session.execute(query)
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )
    
    # Build query for messages
    query = select(Message).where(Message.conversation_id == conversation_id)
    
    # If pagination is requested
    if before_id:
        query = query.where(Message.id < before_id)
    
    # Order by creation time and limit results
    query = query.order_by(Message.created_at.desc()).limit(limit)
    
    result = await session.execute(query)
    messages = result.scalars().all()
    
    # Mark unread messages as read
    unread_messages_query = select(Message).where(
        Message.conversation_id == conversation_id,
        Message.recipient_id == current_user.id,
        Message.is_read == False
    )
    result = await session.execute(unread_messages_query)
    unread_messages = result.scalars().all()
    
    now = datetime.utcnow()
    for message in unread_messages:
        message.is_read = True
        message.read_at = now
    
    await session.commit()
    
    # Sort messages by creation time (newest first)
    return sorted(messages, key=lambda x: x.created_at, reverse=True)

@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Send a new message"""
    # If conversation_id is not provided, create or get a direct conversation
    if not message_data.conversation_id:
        if not message_data.recipient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either conversation_id or recipient_id must be provided"
            )
        
        # Try to find an existing direct conversation between the two users
        direct_conversation_query = """
        SELECT c.id
        FROM conversations c
        JOIN conversation_participants cp1 ON c.id = cp1.conversation_id
        JOIN conversation_participants cp2 ON c.id = cp2.conversation_id
        WHERE c.is_group = False
        AND cp1.user_id = :user_id
        AND cp2.user_id = :recipient_id
        AND cp1.is_active = True
        AND cp2.is_active = True
        """
        
        result = await session.execute(
            text(direct_conversation_query), 
            {"user_id": current_user.id, "recipient_id": message_data.recipient_id}
        )
        existing_conversation = result.scalar_one_or_none()
        
        if existing_conversation:
            conversation_id = existing_conversation
        else:
            # Create a new direct conversation
            new_conversation = Conversation(
                is_group=False
            )
            session.add(new_conversation)
            await session.flush()
            
            # Add participants
            for user_id in [current_user.id, message_data.recipient_id]:
                participant = ConversationParticipant(
                    conversation_id=new_conversation.id,
                    user_id=user_id
                )
                session.add(participant)
            
            conversation_id = new_conversation.id
    else:
        # Use the provided conversation_id
        conversation_id = message_data.conversation_id
        
        # Check if user is a participant in the conversation
        query = select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id,
            ConversationParticipant.is_active == True
        )
        result = await session.execute(query)
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant in this conversation"
            )
    
    # Create the message
    new_message = Message(
        content=message_data.content,
        message_type=message_data.message_type,
        conversation_id=conversation_id,
        sender_id=current_user.id,
        recipient_id=message_data.recipient_id
    )
    
    session.add(new_message)
    await session.commit()
    await session.refresh(new_message)
    
    logger.info(f"Message sent: {new_message.id} in conversation {conversation_id} by user {current_user.id}")
    return new_message

@router.post("/announcements", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_announcement(
    content: str,
    recipient_type: Optional[UserType] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Send an announcement to all users or a specific user type"""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to send announcements"
        )
    
    # Find or create the announcements conversation
    query = select(Conversation).where(
        Conversation.title == "Announcements",
        Conversation.is_group == True
    )
    result = await session.execute(query)
    announcements_conversation = result.scalar_one_or_none()
    
    if not announcements_conversation:
        # Create the announcements conversation
        announcements_conversation = Conversation(
            title="Announcements",
            is_group=True
        )
        session.add(announcements_conversation)
        await session.flush()
        
        # Get all users (optionally filtered by type)
        users_query = select(User)
        if recipient_type:
            users_query = users_query.where(User.user_type == recipient_type)
        
        result = await session.execute(users_query)
        users = result.scalars().all()
        
        # Add all users as participants
        for user in users:
            participant = ConversationParticipant(
                conversation_id=announcements_conversation.id,
                user_id=user.id
            )
            session.add(participant)
    
    # Create the announcement message
    announcement = Message(
        content=content,
        message_type=MessageType.ANNOUNCEMENT,
        conversation_id=announcements_conversation.id,
        sender_id=current_user.id
    )
    
    session.add(announcement)
    await session.commit()
    await session.refresh(announcement)
    
    logger.info(f"Announcement sent: {announcement.id} by user {current_user.id}")
    return announcement

@router.put("/messages/{message_id}/read", response_model=MessageResponse)
async def mark_message_as_read(
    message_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Mark a specific message as read"""
    query = select(Message).where(
        Message.id == message_id,
        Message.recipient_id == current_user.id
    )
    result = await session.execute(query)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message with ID {message_id} not found or you're not the recipient"
        )
    
    if not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()
        await session.commit()
        await session.refresh(message)
    
    return message
