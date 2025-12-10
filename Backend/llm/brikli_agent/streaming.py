"""
Streaming operations and event handling for Azure AI conversations
"""
import asyncio
import logging
from typing import Any, AsyncGenerator

from .constants import StreamEventTypes
from .formatters import SSEFormatter
from .extractors import EventExtractor

logger = logging.getLogger(__name__)


class StreamingManager:
    """
    Manages Azure AI streaming operations and event processing

    This class handles streaming chat responses, event processing,
    and SSE formatting for real-time communication.
    """

    def __init__(
        self,
        client: Any,
        assistant_id: str,
        message_handler: Any,
        tool_manager: Any
    ) -> None:
        """Initialize with required components"""
        self.client = client
        self.assistant_id = assistant_id
        self.message_handler = message_handler
        self.tool_manager = tool_manager
        self.formatter = SSEFormatter()
        self.extractor = EventExtractor()

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
            success = await self.message_handler.add_user_message_to_thread(thread_id, message_content)
            if not success:
                yield self.formatter.format_error("Failed to add message to thread")
                return

            # Start streaming from Azure AI
            async for chunk in self._stream_from_azure(thread_id):
                yield chunk

        except Exception as e:
            logger.error(f"Streaming error for thread {thread_id}: {str(e)}")
            yield self.formatter.format_error(f"Streaming failed: {str(e)}")

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

            # Use OpenAI Assistants API streaming pattern
            with self.client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
            ) as stream:

                # Process stream events until done or tool execution
                for event in stream:
                    event_type = event.event
                    event_data = event.data
                    try:
                        # Capture run ID for later use
                        if event_type == StreamEventTypes.RUN_CREATED:
                            current_run_id = getattr(event_data, 'id', None)

                        # Handle direct message content deltas (for non-tool responses)
                        elif event_type == StreamEventTypes.MESSAGE_DELTA:
                            content_chunk = self.extractor.extract_message_delta(event_data)
                            if content_chunk:
                                accumulated_content += content_chunk
                                yield self.formatter.format_content(content_chunk)

                        # Handle step-based content deltas
                        elif event_type == "thread.run.step.delta":
                            content_chunk = self.extractor.extract_step_delta(event_data)
                            if content_chunk:
                                accumulated_content += content_chunk
                                yield self.formatter.format_content(content_chunk)

                        # Handle tool calls
                        elif event_type == StreamEventTypes.RUN_REQUIRES_ACTION:
                            yield self.formatter.format_status("🔧 Executing tools...")

                            run_id = getattr(event_data, 'id', current_run_id or '')
                            if not run_id:
                                logger.error("No run ID in requires_action event")
                                yield self.formatter.format_error("Failed to get run ID")
                                return

                            await self.tool_manager.handle_tool_calls_streaming(
                                thread_id,
                                run_id,
                                getattr(event_data, 'required_action', None)
                            )

                            yield self.formatter.format_status("🤖 Processing results...")
                            tool_execution_completed = True
                            current_run_id = run_id

                        # Handle run completion (for non-tool flows)
                        elif event_type == StreamEventTypes.RUN_COMPLETED:
                            logger.info(f"Run completed successfully with {len(accumulated_content)} characters")
                            break

                        # Handle errors
                        elif event_type == StreamEventTypes.RUN_FAILED:
                            error_msg = getattr(event_data, 'last_error', 'Unknown error')
                            logger.error(f"Run failed: {error_msg}")
                            yield self.formatter.format_error(f"Run failed: {error_msg}")
                            return

                        elif event_type == StreamEventTypes.RUN_CANCELLED:
                            logger.warning("Run was cancelled")
                            yield self.formatter.format_error("Run was cancelled")
                            return

                        # Handle done event - stream ends here
                        elif event_type == "done":
                            logger.info("Stream done event received")
                            break

                    except Exception as event_error:
                        logger.error(f"Error processing event {event_type}: {event_error}")
                        # Continue processing other events - individual event failures shouldn't stop the stream
                        continue

            # After tool execution, poll for run completion and get response
            if tool_execution_completed and current_run_id:
                logger.info("Tool execution completed, polling for run completion...")

                # Poll for run to complete
                max_attempts = 30
                for attempt in range(max_attempts):
                    await asyncio.sleep(1.0)

                    try:
                        run = self.client.beta.threads.runs.retrieve(
                            thread_id=thread_id,
                            run_id=current_run_id
                        )

                        logger.info(f"Run status: {run.status} (attempt {attempt + 1})")

                        if run.status == "completed":
                            # Get the assistant's response message
                            messages = list(self.client.beta.threads.messages.list(
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
                                        yield self.formatter.format_content(content_text.strip())
                                        accumulated_content = content_text.strip()
                                        logger.info(f"Retrieved assistant response: {len(accumulated_content)} characters")
                                        break
                            break

                        elif run.status in ["failed", "cancelled", "expired"]:
                            error_msg = f"Run {run.status}"
                            if hasattr(run, 'last_error'):
                                error_msg += f": {run.last_error}"
                            logger.error(error_msg)
                            yield self.formatter.format_error(error_msg)
                            return

                    except Exception as e:
                        logger.error(f"Error polling run status: {e}")
                        if attempt == max_attempts - 1:
                            yield self.formatter.format_error("Failed to get response")
                            return

            # Final validation
            if accumulated_content.strip():
                logger.info(f"Successfully completed with {len(accumulated_content)} characters")
                yield self.formatter.format_done(accumulated_content)
            else:
                logger.error("No content accumulated")
                yield self.formatter.format_error("No response received")

        except Exception as e:
            logger.error(f"Error in Azure AI Projects streaming: {e}")
            yield self.formatter.format_error(f"Streaming error: {str(e)}")
            # Don't re-raise - error has been communicated to client via SSE

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