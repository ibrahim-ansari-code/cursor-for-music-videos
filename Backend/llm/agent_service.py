"""
Azure AI Agent Service Client

This module provides the interface to Azure AI Foundry's Agent (Assistant) service.
It handles all communication with the Azure AI Agent API.
"""
import asyncio
import json
import logging
import os
from typing import Any, AsyncGenerator, Optional, Union
from datetime import datetime, UTC

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.core.credentials import TokenCredential

from Backend.config import settings

logger = logging.getLogger(__name__)

# Event type constants
class StreamEventTypes:
    """Constants for Azure AI streaming event types"""
    MESSAGE_DELTA = 'thread.message.delta'
    RUN_CREATED = 'thread.run.created'
    RUN_QUEUED = 'thread.run.queued'
    RUN_IN_PROGRESS = 'thread.run.in_progress'
    RUN_COMPLETED = 'thread.run.completed'
    RUN_REQUIRES_ACTION = 'thread.run.requires_action'  # Added this!
    MESSAGE_COMPLETED = 'thread.message.completed'
    RUN_FAILED = 'thread.run.failed'
    RUN_CANCELLED = 'thread.run.cancelled'

# SSE message type constants
class SSEMessageTypes:
    """Constants for Server-Sent Event message types"""
    CONTENT = 'content'
    STATUS = 'status'
    DONE = 'done'
    ERROR = 'error'


class BrikliAgentService:
    """
    Service class for interacting with Azure AI Agent (Assistant API)
    
    This class manages:
    - Thread creation and management
    - Message sending and retrieval
    - Run creation and status monitoring
    - Tool execution handling
    """
    
    def __init__(self):
        """Initialize the agent service with Azure credentials"""
        self.endpoint = settings.AZURE_AGENT_ENDPOINT
        self.assistant_id = settings.AZURE_ASSISTANT_ID
        
        self._validate_configuration()
        
        # Initialize Azure AI Projects client with appropriate credential
        # Authentication priority:
        # 1. Service Principal (most secure for production)
        # 2. Managed Identity (for Azure-hosted apps with IMDS enabled)
        # 3. Azure CLI / DefaultAzureCredential (for local development)
        
        credential: TokenCredential
        
        # Check for Service Principal authentication
        if all([os.getenv("AZURE_CLIENT_ID"), 
                os.getenv("AZURE_CLIENT_SECRET"), 
                os.getenv("AZURE_TENANT_ID")]):
            logger.info("Using Service Principal authentication")
            # Use DefaultAzureCredential which will prioritize environment variables
            # This works regardless of whether IMDS is available
            credential = DefaultAzureCredential()
        
        # Check for User-Assigned Managed Identity (only if IMDS available)
        elif os.getenv("AZURE_CLIENT_ID") and os.getenv("WEBSITE_SITE_NAME"):
            logger.info("Using User-Assigned Managed Identity")
            credential = ManagedIdentityCredential(client_id=os.getenv("AZURE_CLIENT_ID"))
        
        # Check for System-Assigned Managed Identity (only if IMDS available)
        elif os.getenv("WEBSITE_SITE_NAME"):
            logger.info("Using System-Assigned Managed Identity")
            credential = ManagedIdentityCredential()
        
        # Local development - DefaultAzureCredential (includes Azure CLI)
        else:
            logger.info("Using DefaultAzureCredential for local development")
            logger.info("Make sure you are logged in with 'az login'")
            credential = DefaultAzureCredential()
        
        try:
            # Initialize the client with TokenCredential
            self.client = AIProjectClient(
                endpoint=self.endpoint,
                credential=credential
            )
            # Access the agents client
            self.agents_client = self.client.agents
            logger.info("Azure AI Agent client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure AI client: {str(e)}")
            logger.error("Authentication configuration required:")
            logger.error("1. For production: Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID")
            logger.error("2. For Azure hosting: Enable Managed Identity")
            logger.error("3. For local dev: Run 'az login'")
            raise
    
    def _validate_configuration(self):
        """Validate that all required configuration is present"""
        if not all([self.endpoint, self.assistant_id]):
            raise ValueError(
                "Azure AI Agent is not fully configured. "
                "Please set AZURE_AGENT_ENDPOINT and AZURE_ASSISTANT_ID environment variables."
            )
    
    async def create_thread(self) -> str:
        """
        Create a new conversation thread
        
        Returns:
            str: The thread ID
        """
        try:
            logger.info("Creating new thread")
            # Use the correct API: client.agents.threads.create()
            thread = self.agents_client.threads.create()
            logger.info(f"Created thread with ID: {thread.id}")
            return thread.id
        except Exception as e:
            logger.error(f"Failed to create thread: {str(e)}")
            raise
    
    async def delete_thread(self, thread_id: str) -> bool:
        """
        Delete a thread from Azure AI
        
        Args:
            thread_id: The thread ID to delete
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            logger.info(f"Deleting thread {thread_id}")
            # Delete the thread using Azure AI API
            self.agents_client.threads.delete(thread_id)
            logger.info(f"Successfully deleted thread {thread_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete thread {thread_id}: {str(e)}")
            # Don't raise - thread might already be deleted or not exist
            return False
    
    async def add_message_and_run(
        self,
        thread_id: str,
        message_content: str
    ) -> dict[str, Any]:
        """
        Add a user message to the thread and create a run
        
        Args:
            thread_id: The thread ID
            message_content: The user's message
            
        Returns:
            Dict containing thread_id, run_id, and status
        """
        try:
            logger.info(f"Adding message to thread {thread_id} and creating run")
            
            # Add user message to thread using correct API
            self.agents_client.messages.create(
                thread_id=thread_id,
                role="user",
                content=message_content
            )
            
            # Create and return run using correct API
            run = self.agents_client.runs.create(
                thread_id=thread_id,
                agent_id=self.assistant_id
            )
            
            logger.info(f"Created run {run.id} for thread {thread_id}")
            
            return {
                "thread_id": thread_id,
                "run_id": run.id,
                "status": run.status
            }
        except Exception as e:
            logger.error(f"Failed to add message and create run: {str(e)}")
            raise
    
    async def get_run_status(
        self,
        thread_id: str,
        run_id: str,
        session = None
    ) -> dict[str, Any]:
        """
        Get the status of a run and handle tool execution when needed
        
        Args:
            thread_id: The thread ID
            run_id: The run ID
            session: Database session (optional, will be created if not provided)
            
        Returns:
            Dict containing status and optional message/error
        """
        try:
            logger.info(f"Getting status for run {run_id} in thread {thread_id}")
            
            # Get run status using correct API
            run = self.agents_client.runs.get(
                thread_id=thread_id,
                run_id=run_id
            )
            
            result = {
                "status": run.status,
                "thread_id": thread_id,
                "run_id": run_id
            }
            
            # If run requires action (tool calls), handle them
            if run.status == "requires_action":
                logger.info(f"Run {run_id} requires action - handling tool calls")
                
                # Handle tool calls following Microsoft documentation pattern
                if session is not None:
                    await self._handle_tool_calls_streaming(thread_id, run_id, run.required_action)
                    
                    # After submitting tool outputs, the run continues automatically
                    result["status"] = "processing_tools"
                    result["message"] = "Executing tools and processing results..."
                else:
                    logger.warning("No session provided for tool execution")
                    result["requires_action"] = True
                    result["message"] = "Tools execution requires database session"
            
            # If run failed, include error information
            elif run.status == "failed":
                result["error"] = getattr(run, 'last_error', 'Unknown error occurred')
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get run status: {str(e)}")
            raise



    async def _get_user_id_from_thread(self, thread_id: str, session):
        """
        Get user ID from thread mapping
        
        Args:
            thread_id: The thread ID to lookup
            session: Database session
            
        Returns:
            User ID associated with the thread
        """
        from Backend.models.agent import UserAgentThread
        from sqlmodel import select
        
        result = await session.execute(
            select(UserAgentThread).where(UserAgentThread.thread_id == thread_id)
        )
        thread_mapping = result.scalar_one_or_none()
        
        if thread_mapping:
            return thread_mapping.user_id
        else:
            logger.error(f"No user found for thread {thread_id}")
            raise ValueError(f"No user found for thread {thread_id}")

    def register_tools_with_assistant(self):
        """
        Register tools with the Azure Assistant
        
        This method updates the Assistant configuration to include our custom tools
        for property management operations.
        """
        try:
            from Backend.llm.tools import get_tool_definitions
            
            logger.info("Registering tools with Azure Assistant")
            tools = get_tool_definitions()
            
            # Update the existing assistant with tools using Azure AI Agents SDK
            # The update_agent method is used to update the assistant
            updated_agent = self.agents_client.update_agent(
                agent_id=self.assistant_id,
                tools=tools
            )
            
            logger.info(f"Successfully registered {len(tools)} tools with assistant {self.assistant_id}")
            logger.info(f"Registered tools: {[tool['function']['name'] for tool in tools]}")
            
            return updated_agent
            
        except Exception as e:
            logger.error(f"Failed to register tools: {str(e)}")
            raise
    
    async def get_messages(
        self,
        thread_id: str,
        limit: int = 20
    ) -> list[dict[str, Any]]:
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
            messages_paged = self.agents_client.messages.list(
                thread_id=thread_id,
                order="asc",
                limit=limit
            )
            messages = list(messages_paged)
            
            # Convert messages to our format
            result = []
            seen_message_ids = set()  # Track actual message IDs, not content hashes
            
            for msg in messages:
                # Skip if we've already processed this exact message ID
                msg_id = getattr(msg, 'id', None)
                if msg_id and msg_id in seen_message_ids:
                    continue
                
                # Extract text content from the message
                content_text = ""
                if msg.content and len(msg.content) > 0:
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
                            # Fallback: convert to string
                            content_text += str(content)
                
                # Only add non-empty messages
                if content_text.strip():
                    # Pass the raw role from the message object.
                    # The Pydantic model will handle validation and normalization.
                    final_role = msg.role
                    
                    # Add message ID to seen set if it exists
                    if msg_id:
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
    
    async def stream_chat(
        self,
        thread_id: str,
        message_content: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response using Azure AI Foundry's native streaming
        
        Args:
            thread_id: The thread ID
            message_content: The user's message
            
        Yields:
            Server-sent event formatted strings
        """
        try:
            logger.info(f"Starting streaming chat for thread {thread_id}")
            
            # Add user message to thread
            success = await self._add_user_message_to_thread(thread_id, message_content)
            if not success:
                yield self._format_sse_error("Failed to add message to thread")
                return
            
            # Start streaming from Azure AI
            async for chunk in self._stream_from_azure(thread_id):
                yield chunk
                
        except Exception as e:
            logger.error(f"Streaming error for thread {thread_id}: {str(e)}")
            yield self._format_sse_error(f"Streaming failed: {str(e)}")
    
    async def _ensure_thread_ready(self, thread_id: str) -> bool:
        """
        Ensure thread is ready for new messages by canceling any active runs
        
        Args:
            thread_id: The thread ID to check
            
        Returns:
            bool: True if thread is ready for new messages
        """
        try:
            # List active runs for this thread
            runs = self.agents_client.runs.list(
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
                        self.agents_client.runs.cancel(
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
    
    async def _add_user_message_to_thread(self, thread_id: str, message_content: str) -> bool:
        """
        Add user message to thread with error handling and run cleanup
        
        Returns:
            bool: True if message was added successfully
        """
        try:
            # Ensure thread is ready (cancel any active runs)
            await self._ensure_thread_ready(thread_id)
            
            # Add the message
            self.agents_client.messages.create(
                thread_id=thread_id,
                role="user",
                content=message_content
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to add message to thread {thread_id}: {e}")
            return False
    
    async def _stream_from_azure(self, thread_id: str) -> AsyncGenerator[str, None]:
        """
        Handle Azure AI Projects streaming with proper event handling
        
        After tool execution, the stream ends and we need to poll for run completion
        to get the assistant's response. This is the documented behavior.
        """
        try:
            accumulated_content = ""
            tool_execution_completed = False
            current_run_id = None
            
            # Create and start the run with streaming
            logger.info(f"Starting streaming run for thread {thread_id}")
            
            # Use the correct Azure AI Projects streaming pattern (synchronous)
            with self.agents_client.runs.stream(
                thread_id=thread_id,
                agent_id=self.assistant_id,
            ) as stream:
                
                # Process stream events until done or tool execution
                for event_type, event_data, _ in stream:
                    try:
                        # Capture run ID for later use
                        if event_type == "thread.run.created":
                            current_run_id = getattr(event_data, 'id', None)
                        
                        # Handle direct message content deltas (for non-tool responses)
                        elif event_type == "thread.message.delta":
                            content_chunk = self._extract_message_delta(event_data)
                            if content_chunk:
                                accumulated_content += content_chunk
                                yield self._format_sse_content(content_chunk)
                        
                        # Handle step-based content deltas
                        elif event_type == "thread.run.step.delta":
                            content_chunk = self._extract_step_delta(event_data)
                            if content_chunk:
                                accumulated_content += content_chunk
                                yield self._format_sse_content(content_chunk)
                    
                        # Handle tool calls
                        elif event_type == "thread.run.requires_action":
                            yield self._format_sse_status("🔧 Executing tools...")
                            
                            run_id = getattr(event_data, 'id', current_run_id or '')
                            if not run_id:
                                logger.error("No run ID in requires_action event")
                                yield self._format_sse_error("Failed to get run ID")
                                return
                                
                            await self._handle_tool_calls_streaming(
                                thread_id,
                                run_id,
                                getattr(event_data, 'required_action', None)
                            )
                            
                            yield self._format_sse_status("🤖 Processing results...")
                            tool_execution_completed = True
                            current_run_id = run_id
                        
                        # Handle run completion (for non-tool flows)
                        elif event_type == "thread.run.completed":
                            logger.info(f"Run completed successfully with {len(accumulated_content)} characters")
                            break
                        
                        # Handle errors
                        elif event_type == "thread.run.failed":
                            error_msg = getattr(event_data, 'last_error', 'Unknown error')
                            logger.error(f"Run failed: {error_msg}")
                            yield self._format_sse_error(f"Run failed: {error_msg}")
                            return
                            
                        elif event_type == "thread.run.cancelled":
                            logger.warning("Run was cancelled")
                            yield self._format_sse_error("Run was cancelled")
                            return
                        
                        # Handle done event - stream ends here
                        elif event_type == "done":
                            logger.info("Stream done event received")
                            break
                        
                    except Exception as event_error:
                        logger.error(f"Error processing event {event_type}: {event_error}")
                        continue
            
            # After tool execution, poll for run completion and get response
            if tool_execution_completed and current_run_id:
                logger.info("Tool execution completed, polling for run completion...")
                
                # Poll for run to complete
                max_attempts = 30
                for attempt in range(max_attempts):
                    await asyncio.sleep(1.0)
                    
                    try:
                        run = self.agents_client.runs.get(
                            thread_id=thread_id,
                            run_id=current_run_id
                        )
                        
                        logger.info(f"Run status: {run.status} (attempt {attempt + 1})")
                        
                        if run.status == "completed":
                            # Get the assistant's response message
                            messages = list(self.agents_client.messages.list(
                                thread_id=thread_id,
                                order="desc",
                                limit=5
                            ))
                            
                            for msg in messages:
                                msg_role = getattr(msg, 'role', '')
                                # Handle both string roles and enum-like objects
                                if hasattr(msg_role, 'value'):
                                    role_str = str(getattr(msg_role, 'value', ''))
                                else:
                                    role_str = str(msg_role)
                                
                                if role_str.lower() in ["assistant", "agent"]:
                                    content_text = ""
                                    if msg.content and len(msg.content) > 0:
                                        for content in msg.content:
                                            if hasattr(content, 'type') and getattr(content, 'type', None) == 'text':
                                                text_obj = getattr(content, 'text', None)
                                                if text_obj and hasattr(text_obj, 'value'):
                                                    content_text += str(text_obj.value)
                                    
                                    if content_text.strip():
                                        # Stream the complete response
                                        yield self._format_sse_content(content_text.strip())
                                        accumulated_content = content_text.strip()
                                        logger.info(f"Retrieved assistant response: {len(accumulated_content)} characters")
                                        break
                            break
                            
                        elif run.status in ["failed", "cancelled", "expired"]:
                            error_msg = f"Run {run.status}"
                            if hasattr(run, 'last_error'):
                                error_msg += f": {run.last_error}"
                            logger.error(error_msg)
                            yield self._format_sse_error(error_msg)
                            return
                            
                    except Exception as e:
                        logger.error(f"Error polling run status: {e}")
                        if attempt == max_attempts - 1:
                            yield self._format_sse_error("Failed to get response")
                            return
            
            # Final validation
            if accumulated_content.strip():
                logger.info(f"Successfully completed with {len(accumulated_content)} characters")
                yield self._format_sse_done(accumulated_content)
            else:
                logger.error("No content accumulated")
                yield self._format_sse_error("No response received")
                
        except Exception as e:
            logger.error(f"Error in Azure AI Projects streaming: {e}")
            yield self._format_sse_error(f"Streaming error: {str(e)}")
            raise
    
    async def _execute_tool_call(self, tool_call, thread_id: str):
        """Execute a single tool call"""
        try:
            from Backend.llm.tool_handlers import ToolHandlers
            from Backend.database import get_session
            
            # Get user ID and execute tool using a database session
            async for session in get_session():
                user_id = await self._get_user_id_from_thread(thread_id, session)
                
                # Parse tool call arguments
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                
                # Execute the appropriate tool with correct parameter order
                if function_name == "search_properties":
                    return await ToolHandlers.search_properties(arguments, user_id, session)
                elif function_name == "get_tenant_info":
                    return await ToolHandlers.get_tenant_info(arguments, user_id, session)
                elif function_name == "get_financial_summary":
                    return await ToolHandlers.get_financial_summary(arguments, user_id, session)
                elif function_name == "get_maintenance_requests":
                    return await ToolHandlers.get_maintenance_requests(arguments, user_id, session)
                elif function_name == "get_lease_expiry_info":
                    return await ToolHandlers.get_lease_expiry_info(arguments, user_id, session)
                elif function_name == "get_payment_status":
                    return await ToolHandlers.get_payment_status(arguments, user_id, session)
                elif function_name == "search_lease_documents":
                    return await ToolHandlers.search_lease_documents(arguments, user_id, session)
                else:
                    return f"Unknown tool: {function_name}"
                    
        except Exception as e:
            logger.error(f"Error executing tool {tool_call.function.name}: {e}")
            return f"Error executing {tool_call.function.name}: {str(e)}"
    

    
    def _get_status_events(self) -> list[str]:
        """Get list of status event types"""
        return [
            "thread.run.created",
            "thread.run.queued", 
            "thread.run.in_progress"
        ]
    
    def _get_completion_events(self) -> list[str]:
        """Get list of completion event types"""
        return [
            "thread.run.completed",
            "thread.message.completed"
        ]
    
    def _get_error_events(self) -> list[str]:
        """Get list of error event types"""
        return [
            "thread.run.failed",
            "thread.run.cancelled"
        ]
    
    def _format_sse_content(self, content: str) -> str:
        """Format content chunk as SSE message"""
        return f"data: {json.dumps({'type': SSEMessageTypes.CONTENT, 'content': content})}\n\n"
    
    def _format_sse_status(self, status: str) -> str:
        """Format status update as SSE message"""
        return f"data: {json.dumps({'type': SSEMessageTypes.STATUS, 'status': status})}\n\n"
    
    def _format_sse_message(self, message: str) -> str:
        """Format a plain message as SSE content"""
        return f"data: {json.dumps({'type': SSEMessageTypes.CONTENT, 'content': message})}\n\n"
    
    def _format_sse_done(self, total_content: str) -> str:
        """Format completion message as SSE"""
        return f"data: {json.dumps({'type': SSEMessageTypes.DONE, 'total_content': total_content})}\n\n"
    
    def _format_sse_error(self, error_message: str) -> str:
        """Format error message as SSE"""
        return f"data: {json.dumps({'type': SSEMessageTypes.ERROR, 'error': error_message})}\n\n"
    
    def _extract_message_delta(self, event_data) -> str:
        """
        Extract content from Azure AI Projects message delta event
        Handles direct message content deltas
        """
        try:
            if not hasattr(event_data, 'delta'):
                return ""
            
            delta = event_data.delta
            
            # Handle delta content list
            if hasattr(delta, 'content') and delta.content:
                if isinstance(delta.content, list):
                    for content_part in delta.content:
                        if hasattr(content_part, 'text'):
                            text_obj = content_part.text
                            if hasattr(text_obj, 'value'):
                                content = str(text_obj.value)
                                if content:
                                    return content
                            elif isinstance(text_obj, str):
                                if text_obj:
                                    return text_obj
                
                # Handle direct content object
                elif hasattr(delta.content, 'text'):
                    text_obj = delta.content.text
                    if hasattr(text_obj, 'value'):
                        content = str(text_obj.value)
                        if content:
                            return content
                    elif isinstance(text_obj, str):
                        if text_obj:
                            return text_obj
            
            # Handle delta text directly
            elif hasattr(delta, 'text'):
                text_obj = delta.text
                if hasattr(text_obj, 'value'):
                    content = str(text_obj.value)
                    if content:
                        return content
                elif isinstance(text_obj, str):
                    if text_obj:
                        return text_obj
                                
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting message delta: {e}")
            return ""
    
    def _extract_step_delta(self, event_data) -> str:
        """
        Extract content from Azure AI Projects step delta event
        Handles message_creation type step details for assistant responses
        """
        try:
            if not hasattr(event_data, 'delta'):
                return ""
                
            delta = event_data.delta
            
            # Check for step details
            if not hasattr(delta, 'step_details'):
                return ""
                
            step_details = delta.step_details
            step_type = getattr(step_details, 'type', None)
            
            # Only process message_creation type steps (not tool_calls)
            if step_type != 'message_creation':
                return ""
            
            # Extract message creation content
            if hasattr(step_details, 'message_creation'):
                message_creation = step_details.message_creation
                
                if hasattr(message_creation, 'message'):
                    message = message_creation.message
                    
                    if hasattr(message, 'content') and message.content:
                        # Handle content list
                        if isinstance(message.content, list):
                            for content_item in message.content:
                                if hasattr(content_item, 'text'):
                                    text_obj = content_item.text
                                    if hasattr(text_obj, 'value'):
                                        content = str(text_obj.value)
                                        if content:
                                            return content
                                    elif isinstance(text_obj, str):
                                        if text_obj:
                                            return text_obj
                        
                        # Handle direct content object
                        elif hasattr(message.content, 'text'):
                            text_obj = message.content.text
                            if hasattr(text_obj, 'value'):
                                content = str(text_obj.value)
                                if content:
                                    return content
                            elif isinstance(text_obj, str):
                                if text_obj:
                                    return text_obj
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting step delta: {e}")
            return ""
    
    async def _handle_tool_calls_streaming(self, thread_id: str, run_id: str, required_action):
        """
        Handle tool calls during streaming according to Azure AI Projects pattern
        """
        try:
            from Backend.llm.tool_handlers import ToolHandlers
            from Backend.database import get_session
            
            # Extract tool calls from required_action
            tool_calls = []
            if hasattr(required_action, 'submit_tool_outputs') and required_action.submit_tool_outputs:
                if hasattr(required_action.submit_tool_outputs, 'tool_calls'):
                    tool_calls = required_action.submit_tool_outputs.tool_calls
            elif hasattr(required_action, 'tool_calls'):
                tool_calls = required_action.tool_calls
            
            if not tool_calls:
                logger.warning("No tool calls found in required_action")
                return
            
            logger.info(f"Processing {len(tool_calls)} tool calls")
            
            tool_outputs = []
            
            # Create session and execute tools
            async for db_session in get_session():
                user_id = await self._get_user_id_from_thread(thread_id, db_session)
                
                for tool_call in tool_calls:
                    # Execute the tool using our handlers
                    tool_result = await ToolHandlers.handle_tool_call(
                        tool_name=tool_call.function.name,
                        arguments=tool_call.function.arguments,
                        user_id=user_id,
                        session=db_session
                    )
                    
                    # Format output for Azure AI
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps(tool_result, default=str)
                    })
                    
                # Submit tool outputs back to Azure AI
                self.agents_client.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs
                )
                
                break  # Exit the async for loop after first session
                
        except Exception as e:
            logger.error(f"Failed to handle tool calls in streaming: {str(e)}")
            raise
    
    async def add_message_and_stream(
        self,
        thread_id: str,
        message_content: str
    ) -> AsyncGenerator[str, None]:
        """
        Convenience method that combines message addition and streaming
        
        This is the main method to replace the polling-based approach
        """
        async for chunk in self.stream_chat(thread_id, message_content):
            yield chunk
