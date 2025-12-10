"""
Unit tests for RunManager class
"""
import pytest
from unittest.mock import AsyncMock, Mock

from Backend.llm.brikli_agent.runs import RunManager


@pytest.fixture
def mock_client():
    """Create mock OpenAI client"""
    client = Mock()
    client.beta = Mock()
    client.beta.threads = Mock()
    client.beta.threads.messages = Mock()
    client.beta.threads.runs = Mock()
    return client


@pytest.fixture
def mock_tool_manager():
    """Create mock tool manager"""
    manager = AsyncMock()
    return manager


@pytest.fixture
def run_manager(mock_client, mock_tool_manager):
    """Create RunManager instance with mocks"""
    return RunManager(mock_client, "asst_123", mock_tool_manager)


class TestRunManager:
    """Test cases for RunManager class"""

    async def test_add_message_and_run_success(self, run_manager, mock_client):
        """Test successful message addition and run creation"""
        # Arrange
        thread_id = "thread_123"
        message_content = "Hello assistant!"

        mock_run = Mock()
        mock_run.id = "run_123"
        mock_run.status = "queued"

        mock_client.beta.threads.runs.create.return_value = mock_run

        # Act
        result = await run_manager.add_message_and_run(thread_id, message_content)

        # Assert
        assert result["thread_id"] == thread_id
        assert result["run_id"] == "run_123"
        assert result["status"] == "queued"

        mock_client.beta.threads.messages.create.assert_called_once_with(
            thread_id=thread_id,
            role="user",
            content=message_content
        )
        mock_client.beta.threads.runs.create.assert_called_once_with(
            thread_id=thread_id,
            assistant_id="asst_123"
        )

    async def test_add_message_and_run_failure(self, run_manager, mock_client):
        """Test failure during message addition and run creation"""
        # Arrange
        thread_id = "thread_123"
        message_content = "Hello!"
        mock_client.beta.threads.runs.create.side_effect = Exception("Run creation failed")

        # Act & Assert
        with pytest.raises(Exception, match="Run creation failed"):
            await run_manager.add_message_and_run(thread_id, message_content)

    async def test_get_run_status_completed(self, run_manager, mock_client):
        """Test getting run status for completed run"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"

        mock_run = Mock()
        mock_run.status = "completed"
        mock_client.beta.threads.runs.retrieve.return_value = mock_run

        # Act
        result = await run_manager.get_run_status(thread_id, run_id)

        # Assert
        assert result["status"] == "completed"
        assert result["thread_id"] == thread_id
        assert result["run_id"] == run_id

        mock_client.beta.threads.runs.retrieve.assert_called_once_with(
            thread_id=thread_id,
            run_id=run_id
        )

    async def test_get_run_status_requires_action(self, run_manager, mock_client, mock_tool_manager):
        """Test getting run status for run requiring action (tool execution)"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"
        mock_session = AsyncMock()

        mock_required_action = Mock()
        mock_run = Mock()
        mock_run.status = "requires_action"
        mock_run.required_action = mock_required_action

        mock_client.beta.threads.runs.retrieve.return_value = mock_run

        # Act
        result = await run_manager.get_run_status(thread_id, run_id, session=mock_session)

        # Assert
        assert result["status"] == "processing_tools"
        assert result["message"] == "Executing tools and processing results..."

        mock_tool_manager.handle_tool_calls_streaming.assert_called_once_with(
            thread_id, run_id, mock_required_action
        )

    async def test_get_run_status_requires_action_no_session(self, run_manager, mock_client):
        """Test run requiring action without database session"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"

        mock_run = Mock()
        mock_run.status = "requires_action"
        mock_client.beta.threads.runs.retrieve.return_value = mock_run

        # Act
        result = await run_manager.get_run_status(thread_id, run_id, session=None)

        # Assert
        assert result["status"] == "requires_action"
        assert result["requires_action"] is True
        assert "database session" in result["message"]

    async def test_get_run_status_failed(self, run_manager, mock_client):
        """Test getting run status for failed run"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"

        mock_run = Mock()
        mock_run.status = "failed"
        mock_run.last_error = "Processing failed due to timeout"
        mock_client.beta.threads.runs.retrieve.return_value = mock_run

        # Act
        result = await run_manager.get_run_status(thread_id, run_id)

        # Assert
        assert result["status"] == "failed"
        assert result["error"] == "Processing failed due to timeout"

    async def test_get_run_status_failed_no_error_details(self, run_manager, mock_client):
        """Test getting run status for failed run without error details"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"

        mock_run = Mock()
        mock_run.status = "failed"
        # No last_error attribute
        del mock_run.last_error
        mock_client.beta.threads.runs.retrieve.return_value = mock_run

        # Act
        result = await run_manager.get_run_status(thread_id, run_id)

        # Assert
        assert result["status"] == "failed"
        assert result["error"] == "Unknown error occurred"

    async def test_get_run_status_in_progress(self, run_manager, mock_client):
        """Test getting run status for in-progress run"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"

        mock_run = Mock()
        mock_run.status = "in_progress"
        mock_client.beta.threads.runs.retrieve.return_value = mock_run

        # Act
        result = await run_manager.get_run_status(thread_id, run_id)

        # Assert
        assert result["status"] == "in_progress"
        assert "error" not in result
        assert "message" not in result

    async def test_get_run_status_api_failure(self, run_manager, mock_client):
        """Test failure when getting run status"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"
        mock_client.beta.threads.runs.retrieve.side_effect = Exception("API error")

        # Act & Assert
        with pytest.raises(Exception, match="API error"):
            await run_manager.get_run_status(thread_id, run_id)

    async def test_tool_execution_integration(self, run_manager, mock_client, mock_tool_manager):
        """Test integration with tool manager for tool execution"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"
        mock_session = AsyncMock()

        # Mock required action with tool calls
        mock_tool_call = Mock()
        mock_tool_call.function.name = "search_properties"
        mock_tool_call.function.arguments = '{"status": "Active"}'

        mock_required_action = Mock()
        mock_required_action.submit_tool_outputs = Mock()
        mock_required_action.submit_tool_outputs.tool_calls = [mock_tool_call]

        mock_run = Mock()
        mock_run.status = "requires_action"
        mock_run.required_action = mock_required_action

        mock_client.beta.threads.runs.retrieve.return_value = mock_run

        # Act
        result = await run_manager.get_run_status(thread_id, run_id, session=mock_session)

        # Assert
        assert result["status"] == "processing_tools"
        mock_tool_manager.handle_tool_calls_streaming.assert_called_once_with(
            thread_id, run_id, mock_required_action
        )

    async def test_various_run_statuses(self, run_manager, mock_client):
        """Test handling various run status values"""
        # Test different status values
        statuses = ["queued", "in_progress", "completed", "cancelled", "expired"]

        for status in statuses:
            # Arrange
            mock_run = Mock()
            mock_run.status = status
            mock_client.beta.threads.runs.retrieve.return_value = mock_run

            # Act
            result = await run_manager.get_run_status("thread_123", "run_123")

            # Assert
            assert result["status"] == status
            assert result["thread_id"] == "thread_123"
            assert result["run_id"] == "run_123"

    async def test_message_creation_failure(self, run_manager, mock_client):
        """Test failure during message creation"""
        # Arrange
        thread_id = "thread_123"
        message_content = "Hello!"
        mock_client.beta.threads.messages.create.side_effect = Exception("Message creation failed")

        # Act & Assert
        with pytest.raises(Exception, match="Message creation failed"):
            await run_manager.add_message_and_run(thread_id, message_content)

        # Should still attempt to create message
        mock_client.beta.threads.messages.create.assert_called_once_with(
            thread_id=thread_id,
            role="user",
            content=message_content
        )

        # Should not attempt to create run if message creation fails
        mock_client.beta.threads.runs.create.assert_not_called()

    async def test_run_status_with_tool_execution_failure(self, run_manager, mock_client, mock_tool_manager):
        """Test run status when tool execution fails"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"
        mock_session = AsyncMock()

        mock_required_action = Mock()
        mock_run = Mock()
        mock_run.status = "requires_action"
        mock_run.required_action = mock_required_action

        mock_client.beta.threads.runs.retrieve.return_value = mock_run

        # Make tool manager fail
        mock_tool_manager.handle_tool_calls_streaming.side_effect = Exception("Tool execution failed")

        # Act
        result = await run_manager.get_run_status(thread_id, run_id, session=mock_session)

        # Assert - Tool execution failure should be handled gracefully, not raise
        assert result["status"] == "failed"
        assert "Tool execution failed" in result["error"]

    async def test_run_manager_initialization(self, mock_client, mock_tool_manager):
        """Test RunManager initialization"""
        # Act
        run_manager = RunManager(mock_client, "test-assistant", mock_tool_manager)

        # Assert
        assert run_manager.client == mock_client
        assert run_manager.assistant_id == "test-assistant"
        assert run_manager.tool_manager == mock_tool_manager