"""
Run creation and status management for Azure AI conversations
"""
import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RunManager:
    """
    Manages Azure AI run operations

    This class handles run creation, status checking, and tool execution
    coordination for Azure AI conversation threads.
    """

    def __init__(self, agents_client: Any, assistant_id: str, tool_manager: Any) -> None:
        """Initialize with Azure AI agents client and assistant ID"""
        self.agents_client = agents_client
        self.assistant_id = assistant_id
        self.tool_manager = tool_manager

    async def add_message_and_run(
        self,
        thread_id: str,
        message_content: str
    ) -> Dict[str, Any]:
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
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
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
                    try:
                        await self.tool_manager.handle_tool_calls_streaming(
                            thread_id, run_id, run.required_action
                        )

                        # After submitting tool outputs, the run continues automatically
                        result["status"] = "processing_tools"
                        result["message"] = "Executing tools and processing results..."
                    except Exception as tool_error:
                        logger.error(f"Tool execution failed for run {run_id}: {tool_error}")
                        result["status"] = "failed"
                        result["error"] = f"Tool execution failed: {str(tool_error)}"
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