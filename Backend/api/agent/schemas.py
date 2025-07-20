"""
Pydantic schemas for Agent API endpoints
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any, Literal, Union
from datetime import datetime
from uuid import UUID
from enum import Enum


# Type definitions
MessageRole = Literal["user", "assistant", "system", "tool"]

def validate_run_status(v):
    """Shared validator for Azure AI run status - allows string status from Azure API"""
    if isinstance(v, str):
        # Map known Azure statuses to our enum where possible
        status_map = {status.value: status for status in RunStatus}
        return status_map.get(v, v)  # Return original string if not in enum
    return v

class RunStatus(str, Enum):
    """Allowed status values for agent runs"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    REQUIRES_ACTION = "requires_action"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"
    EXPIRED = "expired"
    PROCESSING_TOOLS = "processing_tools"


# Tool-related models
class ToolCall(BaseModel):
    """Model for tool call information"""
    id: str = Field(..., description="Unique identifier for the tool call")
    type: str = Field(..., description="Type of tool call (e.g., 'function')")
    function: dict[str, Any] = Field(..., description="Function call details including name and arguments")


class ToolResponse(BaseModel):
    """Model for tool response information"""
    tool_call_id: str = Field(..., description="ID of the tool call this response is for")
    output: str = Field(..., description="Output from the tool execution")
    error: Optional[str] = Field(None, description="Error message if tool execution failed")


# Request schemas
class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message"""
    content: str = Field(..., min_length=1, max_length=4000, description="User message content to send to the agent")




# Response schemas
class ChatMessage(BaseModel):
    """Individual chat message"""
    role: MessageRole = Field(..., description="Message role: 'user', 'assistant', 'system', or 'tool'")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="When the message was created")
    tool_calls: Optional[list[ToolCall]] = Field(None, description="Tool calls made by the assistant")
    tool_responses: Optional[list[ToolResponse]] = Field(None, description="Responses from tool calls")

    @field_validator('role', mode='before')
    def normalize_role(cls, v):
        """Normalize various role representations from Azure into allowed literals"""
        # Handle enum-like objects from Azure by extracting the 'value' attribute
        if hasattr(v, 'value') and not isinstance(v, str):
            v = str(v.value)

        if isinstance(v, str):
            lowered = v.lower().strip()
            # Handle Azure enum like 'messagerole.user' by taking the last part
            if '.' in lowered:
                lowered = lowered.split('.')[-1]

            # Use exact matching for roles
            if lowered == 'user':
                return 'user'
            if lowered in ['assistant', 'agent']:
                return 'assistant'
            if lowered == 'system':
                return 'system'
            if lowered == 'tool':
                return 'tool'
        
        # If the value is not a string or doesn't match, Pydantic will raise a validation error
        return v


class ChatStartResponse(BaseModel):
    """Response when starting a new chat"""
    thread_id: str = Field(..., description="Azure thread ID for the conversation")
    run_id: str = Field(..., description="Azure run ID for the current execution")
    status: Union[RunStatus, str] = Field(..., description="Current status of the run")
    message: str = Field(default="Chat started successfully", description="Status message")
    
    @field_validator('status', mode='before')
    @classmethod
    def validate_status(cls, v):
        return validate_run_status(v)


class ChatStatusResponse(BaseModel):
    """Response when checking chat status"""
    status: Union[RunStatus, str] = Field(..., description="Current run status: queued, in_progress, completed, failed, etc.")
    thread_id: str = Field(..., description="Azure thread ID")
    run_id: str = Field(..., description="Azure run ID")
    message: Optional[str] = Field(None, description="Assistant's response message when completed")
    error: Optional[dict[str, Any]] = Field(None, description="Error details if failed")
    required_action: Optional[dict[str, Any]] = Field(None, description="Action requiring confirmation")
    
    @field_validator('status', mode='before')
    @classmethod
    def validate_status(cls, v):
        return validate_run_status(v)


class ChatHistoryResponse(BaseModel):
    """Response containing chat history"""
    messages: list[ChatMessage] = Field(..., description="List of chat messages")
    thread_id: Optional[str] = Field(None, description="Azure thread ID if available")
    total: int = Field(..., description="Total number of messages")


class ConversationListResponse(BaseModel):
    """Response containing list of user's conversations"""
    conversations: list[dict[str, Any]] = Field(..., description="List of conversation summaries")
    total: int = Field(..., description="Total number of conversations")
