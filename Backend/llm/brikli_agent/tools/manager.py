"""
Tool execution coordination for Azure AI Assistant
"""
import json
import logging
from typing import Any, Dict, List
import asyncio

from azure.ai.agents.models import ToolOutput
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ToolManager:
    """
    Manages tool registration and execution for Azure AI Assistant

    This class handles tool registration with the Azure Assistant
    and coordinates tool execution during conversations.
    """

    def __init__(self, client: Any, assistant_id: str, thread_manager: Any) -> None:
        """Initialize with Azure OpenAI client and assistant ID"""
        self.client = client
        self.assistant_id = assistant_id
        self.thread_manager = thread_manager

    def register_tools_with_assistant(self) -> Any:
        """
        Register tools with the Azure Assistant

        This method updates the Assistant configuration to include our custom tools
        for property management operations.
        """
        try:
            from .definitions import get_tool_definitions

            logger.info("Registering tools with Azure Assistant")
            tools = get_tool_definitions()

            # Update the existing assistant with tools using Azure AI Agents SDK
            # The update_agent method is used to update the assistant
            updated_agent = self.client.beta.assistants.update(
                assistant_id=self.assistant_id,
                tools=tools
            )

            logger.info(f"Successfully registered {len(tools)} tools with assistant {self.assistant_id}")
            logger.info(f"Registered tools: {[tool['function']['name'] for tool in tools]}")

            return updated_agent

        except Exception as e:
            logger.error(f"Failed to register tools: {str(e)}")
            raise

    async def execute_tool_call(self, tool_call: Any, thread_id: str, session: AsyncSession) -> Dict[str, Any]:
        """
        Execute a single tool call

        Args:
            tool_call: The tool call object from Azure AI
            thread_id: The conversation thread ID
            session: Database session for tool execution

        Returns:
            Dict containing the tool execution result
        """
        try:
            from .handlers import ToolHandlers

            # Get user ID and execute tool using the database session
            user_id = await self.thread_manager.get_user_id_from_thread(thread_id, session)

            # Parse tool call arguments
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

            # Use handler registry pattern for better maintainability
            return await self._execute_tool_with_registry(function_name, arguments, user_id, session)

        except Exception as e:
            logger.error(f"Error executing tool {tool_call.function.name}: {e}")
            return {"error": f"Error executing {tool_call.function.name}: {str(e)}"}

    async def _execute_tool_with_registry(
        self, 
        function_name: str, 
        arguments: Dict[str, Any], 
        user_id: Any, 
        session: Any
    ) -> Dict[str, Any]:
        """
        Execute tool using registry pattern for better maintainability
        
        Args:
            function_name: Name of the tool function to execute
            arguments: Tool function arguments
            user_id: User ID for authorization
            session: Database session
            
        Returns:
            Tool execution result
        """
        # Lazy import to avoid circular imports
        from .handlers import ToolHandlers
        
        # Tool handler registry - maps function names to handler methods
        tool_registry = {
            "search_properties": ToolHandlers.search_properties,
            "get_tenant_info": ToolHandlers.get_tenant_info,
            "get_financial_summary": ToolHandlers.get_financial_summary,
            "get_maintenance_requests": ToolHandlers.get_maintenance_requests,
            "get_lease_expiry_info": ToolHandlers.get_lease_expiry_info,
            "get_payment_status": ToolHandlers.get_payment_status,
            "search_lease_documents": ToolHandlers.search_lease_documents,
        }
        
        # Execute tool using registry lookup
        handler = tool_registry.get(function_name)
        if handler:
            return await handler(arguments, user_id, session)
        else:
            logger.warning(f"Unknown tool requested: {function_name}")
            return {"error": f"Unknown tool: {function_name}"}

    async def handle_tool_calls_streaming(
        self,
        thread_id: str,
        run_id: str,
        required_action: Any
    ) -> None:
        """
        Handle tool calls during streaming according to Azure AI Projects pattern

        Args:
            thread_id: The conversation thread ID
            run_id: The run ID requiring tool execution
            required_action: The required action object containing tool calls
        """
        try:
            from .handlers import ToolHandlers
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

            tool_outputs: List[ToolOutput] = []

            # Create session and execute tools concurrently for performance
            async for db_session in get_session():
                user_id = await self.thread_manager.get_user_id_from_thread(thread_id, db_session)

                # Execute tool calls concurrently
                tasks = [
                    ToolHandlers.handle_tool_call(
                        tool_name=tool_call.function.name,
                        arguments=tool_call.function.arguments,
                        user_id=user_id,
                        session=db_session
                    ) for tool_call in tool_calls
                ]
                
                # Execute all tools concurrently using asyncio.gather
                tool_results = await asyncio.gather(*tasks)

                # Format outputs for Azure AI
                for tool_call, tool_result in zip(tool_calls, tool_results):
                    tool_outputs.append(
                        ToolOutput(
                            tool_call_id=tool_call.id,
                            output=json.dumps(tool_result, default=str)
                        )
                    )

                # Submit tool outputs back to Azure AI
                self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs
                )

                break  # Exit the async for loop after first session

        except Exception as e:
            logger.error(f"Failed to handle tool calls in streaming: {str(e)}")
            raise
