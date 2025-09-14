"""
Unit tests for StreamingManager class
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from contextlib import asynccontextmanager

from Backend.llm.brikli_agent.streaming import StreamingManager
from Backend.llm.brikli_agent.constants import StreamEventTypes


@pytest.fixture
def mock_agents_client():
    """Create mock Azure AI agents client"""
    client = Mock()

    # Mock streaming context manager
    mock_stream = Mock()
    mock_stream.__enter__ = Mock(return_value=mock_stream)
    mock_stream.__exit__ = Mock(return_value=None)

    # Mock stream events iterator
    def mock_stream_events():
        yield (StreamEventTypes.RUN_CREATED, Mock(id='run_123'), None)
        yield (StreamEventTypes.MESSAGE_DELTA, Mock(delta=Mock(content=[Mock(text=Mock(value='Hello'))])), None)
        yield (StreamEventTypes.RUN_COMPLETED, Mock(), None)
        yield ("done", None, None)

    mock_stream.__iter__ = lambda self: mock_stream_events()

    client.runs.stream = Mock(return_value=mock_stream)
    client.runs.get = Mock(return_value=Mock(status="completed"))
    client.messages.list = Mock(return_value=[
        Mock(
            role=Mock(value="assistant"),
            content=[Mock(type="text", text=Mock(value="Complete response"))]
        )
    ])

    return client


@pytest.fixture
def mock_message_handler():
    """Create mock message handler"""
    handler = AsyncMock()
    handler.add_user_message_to_thread.return_value = True
    return handler


@pytest.fixture
def mock_tool_manager():
    """Create mock tool manager"""
    manager = AsyncMock()
    manager.handle_tool_calls_streaming = AsyncMock()
    return manager


@pytest.fixture
def streaming_manager(mock_agents_client, mock_message_handler, mock_tool_manager):
    """Create StreamingManager instance with mocks"""
    return StreamingManager(
        agents_client=mock_agents_client,
        assistant_id="assistant_123",
        message_handler=mock_message_handler,
        tool_manager=mock_tool_manager
    )


class TestStreamingManager:
    """Test cases for StreamingManager class"""

    async def test_stream_chat_success(self, streaming_manager, mock_message_handler):
        """Test successful chat streaming"""
        # Arrange
        thread_id = "thread_123"
        message_content = "Hello, assistant!"

        # Act
        chunks = []
        async for chunk in streaming_manager.stream_chat(thread_id, message_content):
            chunks.append(chunk)

        # Assert
        assert len(chunks) > 0
        mock_message_handler.add_user_message_to_thread.assert_called_once_with(thread_id, message_content)

        # Check that we get content chunks
        content_chunks = [chunk for chunk in chunks if '"type": "content"' in chunk]
        assert len(content_chunks) > 0

    async def test_stream_chat_message_add_failure(self, streaming_manager, mock_message_handler):
        """Test streaming when message addition fails"""
        # Arrange
        thread_id = "thread_123"
        message_content = "Hello!"
        mock_message_handler.add_user_message_to_thread.return_value = False

        # Act
        chunks = []
        async for chunk in streaming_manager.stream_chat(thread_id, message_content):
            chunks.append(chunk)

        # Assert
        assert len(chunks) == 1
        assert '"type": "error"' in chunks[0]
        assert "Failed to add message to thread" in chunks[0]

    async def test_stream_from_azure_basic_flow(self, streaming_manager):
        """Test basic Azure AI streaming flow"""
        # Act
        chunks = []
        async for chunk in streaming_manager._stream_from_azure("thread_123"):
            chunks.append(chunk)

        # Assert
        assert len(chunks) > 0

        # Should have content chunks
        content_chunks = [chunk for chunk in chunks if '"type": "content"' in chunk]
        assert len(content_chunks) > 0

        # Should have completion chunk
        done_chunks = [chunk for chunk in chunks if '"type": "done"' in chunk]
        assert len(done_chunks) == 1

    async def test_stream_from_azure_with_tool_execution(self, streaming_manager, mock_agents_client, mock_tool_manager):
        """Test streaming with tool execution"""
        # Arrange - Mock stream with tool execution
        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)

        def mock_stream_with_tools():
            yield (StreamEventTypes.RUN_CREATED, Mock(id='run_123'), None)
            yield (StreamEventTypes.RUN_REQUIRES_ACTION, Mock(id='run_123', required_action=Mock()), None)

        mock_stream.__iter__ = lambda self: mock_stream_with_tools()
        mock_agents_client.runs.stream.return_value = mock_stream

        # Mock run polling after tool execution
        mock_completed_run = Mock(status="completed")
        mock_agents_client.runs.get.return_value = mock_completed_run

        # Act
        chunks = []
        async for chunk in streaming_manager._stream_from_azure("thread_123"):
            chunks.append(chunk)

        # Assert
        mock_tool_manager.handle_tool_calls_streaming.assert_called_once()

        # Should have status updates for tool execution
        status_chunks = [chunk for chunk in chunks if '"status"' in chunk]
        assert any("Executing tools" in chunk for chunk in status_chunks)

    async def test_stream_from_azure_run_failure(self, streaming_manager, mock_agents_client):
        """Test streaming with run failure"""
        # Arrange - Mock stream with failure
        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)

        def mock_stream_with_failure():
            yield (StreamEventTypes.RUN_CREATED, Mock(id='run_123'), None)
            yield (StreamEventTypes.RUN_FAILED, Mock(last_error="Processing failed"), None)

        mock_stream.__iter__ = lambda self: mock_stream_with_failure()
        mock_agents_client.runs.stream.return_value = mock_stream

        # Act
        chunks = []
        async for chunk in streaming_manager._stream_from_azure("thread_123"):
            chunks.append(chunk)

        # Assert
        error_chunks = [chunk for chunk in chunks if '"type": "error"' in chunk]
        assert len(error_chunks) > 0
        assert any("Run failed" in chunk for chunk in error_chunks)

    async def test_stream_from_azure_cancelled_run(self, streaming_manager, mock_agents_client):
        """Test streaming with cancelled run"""
        # Arrange - Mock stream with cancellation
        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)

        def mock_stream_with_cancellation():
            yield (StreamEventTypes.RUN_CREATED, Mock(id='run_123'), None)
            yield (StreamEventTypes.RUN_CANCELLED, Mock(), None)

        mock_stream.__iter__ = lambda self: mock_stream_with_cancellation()
        mock_agents_client.runs.stream.return_value = mock_stream

        # Act
        chunks = []
        async for chunk in streaming_manager._stream_from_azure("thread_123"):
            chunks.append(chunk)

        # Assert
        error_chunks = [chunk for chunk in chunks if '"type": "error"' in chunk]
        assert len(error_chunks) > 0
        assert any("cancelled" in chunk for chunk in error_chunks)

    async def test_stream_from_azure_step_delta(self, streaming_manager, mock_agents_client):
        """Test streaming with step delta events"""
        # Arrange - Mock stream with step delta
        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)

        # Mock step delta event
        mock_step_delta = Mock()
        mock_step_delta.delta = Mock()
        mock_step_delta.delta.step_details = Mock()
        mock_step_delta.delta.step_details.type = "message_creation"
        mock_step_delta.delta.step_details.message_creation = Mock()
        mock_step_delta.delta.step_details.message_creation.message = Mock()
        mock_step_delta.delta.step_details.message_creation.message.content = [
            Mock(text=Mock(value="Step content"))
        ]

        def mock_stream_with_step():
            yield (StreamEventTypes.RUN_CREATED, Mock(id='run_123'), None)
            yield ("thread.run.step.delta", mock_step_delta, None)
            yield (StreamEventTypes.RUN_COMPLETED, Mock(), None)
            yield ("done", None, None)

        mock_stream.__iter__ = lambda self: mock_stream_with_step()
        mock_agents_client.runs.stream.return_value = mock_stream

        # Act
        chunks = []
        async for chunk in streaming_manager._stream_from_azure("thread_123"):
            chunks.append(chunk)

        # Assert
        content_chunks = [chunk for chunk in chunks if '"type": "content"' in chunk]
        assert any("Step content" in chunk for chunk in content_chunks)

    async def test_stream_from_azure_tool_execution_polling(self, streaming_manager, mock_agents_client, mock_tool_manager):
        """Test polling after tool execution completion"""
        # Arrange - Mock stream with tool execution
        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)

        def mock_stream_with_tools():
            yield (StreamEventTypes.RUN_CREATED, Mock(id='run_123'), None)
            yield (StreamEventTypes.RUN_REQUIRES_ACTION, Mock(id='run_123', required_action=Mock()), None)

        mock_stream.__iter__ = lambda self: mock_stream_with_tools()
        mock_agents_client.runs.stream.return_value = mock_stream

        # Mock run polling progression
        polling_responses = [
            Mock(status="in_progress"),
            Mock(status="completed")
        ]
        mock_agents_client.runs.get.side_effect = polling_responses

        # Mock message retrieval
        mock_message = Mock()
        mock_message.role = Mock(value="assistant")
        mock_message.content = [Mock(type="text", text=Mock(value="Tool response"))]
        mock_agents_client.messages.list.return_value = [mock_message]

        # Act
        chunks = []
        async for chunk in streaming_manager._stream_from_azure("thread_123"):
            chunks.append(chunk)

        # Assert
        # Should poll twice (in_progress, then completed)
        assert mock_agents_client.runs.get.call_count == 2

        # Should get the assistant response
        content_chunks = [chunk for chunk in chunks if '"type": "content"' in chunk]
        assert any("Tool response" in chunk for chunk in content_chunks)

    async def test_stream_from_azure_tool_polling_timeout(self, streaming_manager, mock_agents_client, mock_tool_manager):
        """Test tool execution polling timeout"""
        # Arrange - Mock stream with tool execution
        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)

        def mock_stream_with_tools():
            yield (StreamEventTypes.RUN_CREATED, Mock(id='run_123'), None)
            yield (StreamEventTypes.RUN_REQUIRES_ACTION, Mock(id='run_123', required_action=Mock()), None)

        mock_stream.__iter__ = lambda self: mock_stream_with_tools()
        mock_agents_client.runs.stream.return_value = mock_stream

        # Mock run that never completes (always in_progress)
        mock_agents_client.runs.get.return_value = Mock(status="in_progress")

        # Act with proper timeout mechanism
        chunks = []
        
        async def collect_chunks_with_timeout():
            async for chunk in streaming_manager._stream_from_azure("thread_123"):
                chunks.append(chunk)
        
        # Use asyncio.wait_for with proper timeout handling (longer timeout to allow multiple polling attempts)
        try:
            await asyncio.wait_for(collect_chunks_with_timeout(), timeout=5.0)
        except asyncio.TimeoutError:
            # Expected to timeout since run never completes
            pass

        # Assert
        # Should have made multiple polling attempts before timeout
        assert mock_agents_client.runs.get.call_count >= 3

    async def test_add_message_and_stream_convenience_method(self, streaming_manager):
        """Test the convenience method that combines message and streaming"""
        # Act
        chunks = []
        async for chunk in streaming_manager.add_message_and_stream("thread_123", "Hello!"):
            chunks.append(chunk)

        # Assert
        assert len(chunks) > 0
        # Should have same behavior as stream_chat
        content_chunks = [chunk for chunk in chunks if '"type": "content"' in chunk]
        assert len(content_chunks) > 0

    async def test_streaming_exception_handling(self, streaming_manager, mock_message_handler):
        """Test exception handling in streaming"""
        # Arrange
        mock_message_handler.add_user_message_to_thread.side_effect = Exception("Connection error")

        # Act
        chunks = []
        async for chunk in streaming_manager.stream_chat("thread_123", "Hello!"):
            chunks.append(chunk)

        # Assert
        assert len(chunks) == 1
        assert '"type": "error"' in chunks[0]
        assert "Streaming failed" in chunks[0]

    async def test_stream_from_azure_event_processing_error(self, streaming_manager, mock_agents_client):
        """Test error handling during event processing"""
        # Arrange - Mock stream that raises exception during event processing
        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)

        def mock_stream_with_error():
            yield (StreamEventTypes.RUN_CREATED, Mock(id='run_123'), None)
            # This will cause an error in event processing
            yield ("invalid_event_type", "invalid_data", None)
            yield (StreamEventTypes.RUN_COMPLETED, Mock(), None)

        mock_stream.__iter__ = lambda self: mock_stream_with_error()
        mock_agents_client.runs.stream.return_value = mock_stream

        # Act
        chunks = []
        async for chunk in streaming_manager._stream_from_azure("thread_123"):
            chunks.append(chunk)

        # Assert
        # Should continue processing despite the error
        # (error is caught and logged, but streaming continues)
        assert len(chunks) > 0

    async def test_stream_from_azure_no_content_accumulated(self, streaming_manager, mock_agents_client):
        """Test streaming when no content is accumulated"""
        # Arrange - Mock stream with no content
        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)

        def mock_stream_no_content():
            yield (StreamEventTypes.RUN_CREATED, Mock(id='run_123'), None)
            yield (StreamEventTypes.RUN_COMPLETED, Mock(), None)
            yield ("done", None, None)

        mock_stream.__iter__ = lambda self: mock_stream_no_content()
        mock_agents_client.runs.stream.return_value = mock_stream

        # Act
        chunks = []
        async for chunk in streaming_manager._stream_from_azure("thread_123"):
            chunks.append(chunk)

        # Assert
        error_chunks = [chunk for chunk in chunks if '"type": "error"' in chunk]
        assert len(error_chunks) > 0
        assert any("No response received" in chunk for chunk in error_chunks)