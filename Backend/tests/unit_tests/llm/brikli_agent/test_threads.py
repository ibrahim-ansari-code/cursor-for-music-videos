"""
Unit tests for ThreadManager class
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from Backend.llm.brikli_agent.threads import ThreadManager


@pytest.fixture
def mock_client():
    """Create mock OpenAI client"""
    client = Mock()
    client.beta = Mock()
    client.beta.threads = Mock()
    client.beta.threads.runs = Mock()
    return client


@pytest.fixture
def thread_manager(mock_client):
    """Create ThreadManager instance with mock client"""
    return ThreadManager(mock_client)


@pytest.fixture
def sample_user_id():
    """Create sample user ID"""
    return uuid4()


class TestThreadManager:
    """Test cases for ThreadManager class"""

    async def test_create_thread_success(self, thread_manager, mock_client):
        """Test successful thread creation"""
        # Arrange
        mock_thread = Mock(id="thread_123")
        mock_client.beta.threads.create.return_value = mock_thread

        # Act
        thread_id = await thread_manager.create_thread()

        # Assert
        assert thread_id == "thread_123"
        mock_client.beta.threads.create.assert_called_once()

    async def test_create_thread_failure(self, thread_manager, mock_client):
        """Test thread creation failure"""
        # Arrange
        mock_client.beta.threads.create.side_effect = Exception("API error")

        # Act & Assert
        with pytest.raises(Exception, match="API error"):
            await thread_manager.create_thread()

    async def test_delete_thread_success(self, thread_manager, mock_client):
        """Test successful thread deletion"""
        # Arrange
        thread_id = "thread_123"

        # Act
        result = await thread_manager.delete_thread(thread_id)

        # Assert
        assert result is True
        mock_client.beta.threads.delete.assert_called_once_with(thread_id)

    async def test_delete_thread_failure_returns_false(self, thread_manager, mock_client):
        """Test thread deletion failure returns False instead of raising"""
        # Arrange
        thread_id = "thread_123"
        mock_client.beta.threads.delete.side_effect = Exception("Delete failed")

        # Act
        result = await thread_manager.delete_thread(thread_id)

        # Assert
        assert result is False
        mock_client.beta.threads.delete.assert_called_once_with(thread_id)

    async def test_ensure_thread_ready_no_active_runs(self, thread_manager, mock_client):
        """Test ensuring thread readiness when no active runs exist"""
        # Arrange
        thread_id = "thread_123"
        mock_client.beta.threads.runs.list.return_value = []

        # Act
        result = await thread_manager.ensure_thread_ready(thread_id)

        # Assert
        assert result is True
        mock_client.beta.threads.runs.list.assert_called_once_with(
            thread_id=thread_id,
            limit=10,
            order="desc"
        )

    async def test_ensure_thread_ready_with_completed_runs(self, thread_manager, mock_client):
        """Test ensuring thread readiness with only completed runs"""
        # Arrange
        thread_id = "thread_123"
        completed_run = Mock(id="run_1", status="completed")
        failed_run = Mock(id="run_2", status="failed")
        cancelled_run = Mock(id="run_3", status="cancelled")
        expired_run = Mock(id="run_4", status="expired")

        mock_client.beta.threads.runs.list.return_value = [
            completed_run, failed_run, cancelled_run, expired_run
        ]

        # Act
        result = await thread_manager.ensure_thread_ready(thread_id)

        # Assert
        assert result is True
        # Should not cancel any runs since they're already in terminal states
        mock_client.beta.threads.runs.cancel.assert_not_called()

    async def test_ensure_thread_ready_cancels_active_runs(self, thread_manager, mock_client):
        """Test ensuring thread readiness cancels active runs"""
        # Arrange
        thread_id = "thread_123"
        active_run = Mock(id="run_active", status="in_progress")
        queued_run = Mock(id="run_queued", status="queued")
        completed_run = Mock(id="run_completed", status="completed")

        mock_client.beta.threads.runs.list.return_value = [
            active_run, queued_run, completed_run
        ]

        # Act
        result = await thread_manager.ensure_thread_ready(thread_id)

        # Assert
        assert result is True

        # Should cancel the non-completed runs
        expected_cancel_calls = [
            (thread_id, "run_active"),
            (thread_id, "run_queued")
        ]

        actual_cancel_calls = [
            (call.kwargs['thread_id'], call.kwargs['run_id'])
            for call in mock_client.beta.threads.runs.cancel.call_args_list
        ]

        assert len(actual_cancel_calls) == 2
        assert all(call in expected_cancel_calls for call in actual_cancel_calls)

    async def test_ensure_thread_ready_cancel_failure_continues(self, thread_manager, mock_client):
        """Test that cancellation failures don't stop the process"""
        # Arrange
        thread_id = "thread_123"
        active_run = Mock(id="run_active", status="in_progress")

        mock_client.beta.threads.runs.list.return_value = [active_run]
        mock_client.beta.threads.runs.cancel.side_effect = Exception("Cancel failed")

        # Act
        result = await thread_manager.ensure_thread_ready(thread_id)

        # Assert
        assert result is True  # Should still return True despite cancellation failure
        mock_client.beta.threads.runs.cancel.assert_called_once()

    async def test_ensure_thread_ready_list_failure(self, thread_manager, mock_client):
        """Test ensure thread readiness when listing runs fails"""
        # Arrange
        thread_id = "thread_123"
        mock_client.beta.threads.runs.list.side_effect = Exception("List failed")

        # Act
        result = await thread_manager.ensure_thread_ready(thread_id)

        # Assert
        assert result is False

    async def test_ensure_thread_ready_waits_after_cancellation(self, thread_manager, mock_client):
        """Test that ensure_thread_ready waits after cancelling runs"""
        # Arrange
        thread_id = "thread_123"
        active_run = Mock(id="run_active", status="in_progress")
        mock_client.beta.threads.runs.list.return_value = [active_run]

        # Track if sleep was called
        sleep_called = False
        original_sleep = asyncio.sleep

        async def mock_sleep(duration):
            nonlocal sleep_called
            sleep_called = True
            assert duration == 0.5  # Should wait 0.5 seconds
            # Don't actually sleep in the test

        # Act
        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await thread_manager.ensure_thread_ready(thread_id)

        # Assert
        assert result is True
        assert sleep_called
        mock_client.beta.threads.runs.cancel.assert_called_once()

    async def test_get_user_id_from_thread_success(self, thread_manager, sample_user_id):
        """Test successful user ID retrieval from thread mapping"""
        # Arrange
        thread_id = "thread_123"
        mock_session = AsyncMock()

        # Mock UserAgentThread
        from Backend.models.agent import UserAgentThread
        mock_thread_mapping = UserAgentThread(
            id=uuid4(),
            user_id=sample_user_id,
            thread_id=thread_id,
            is_active=True
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_thread_mapping
        mock_session.execute.return_value = mock_result

        # Act
        user_id = await thread_manager.get_user_id_from_thread(thread_id, mock_session)

        # Assert
        assert user_id == sample_user_id
        mock_session.execute.assert_called_once()

    async def test_get_user_id_from_thread_not_found(self, thread_manager):
        """Test user ID retrieval when thread mapping is not found"""
        # Arrange
        thread_id = "thread_123"
        mock_session = AsyncMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ValueError, match="No user found for thread thread_123"):
            await thread_manager.get_user_id_from_thread(thread_id, mock_session)

    async def test_ensure_thread_ready_mixed_run_statuses(self, thread_manager, mock_client):
        """Test ensuring thread readiness with mixed run statuses"""
        # Arrange
        thread_id = "thread_123"
        runs = [
            Mock(id="run_1", status="in_progress"),      # Should be cancelled
            Mock(id="run_2", status="queued"),           # Should be cancelled
            Mock(id="run_3", status="requires_action"),  # Should be cancelled
            Mock(id="run_4", status="completed"),        # Should NOT be cancelled
            Mock(id="run_5", status="failed"),           # Should NOT be cancelled
            Mock(id="run_6", status="cancelled"),        # Should NOT be cancelled
            Mock(id="run_7", status="expired"),          # Should NOT be cancelled
        ]

        mock_client.beta.threads.runs.list.return_value = runs

        # Act
        result = await thread_manager.ensure_thread_ready(thread_id)

        # Assert
        assert result is True

        # Should cancel exactly 3 runs (in_progress, queued, requires_action)
        assert mock_client.beta.threads.runs.cancel.call_count == 3

        # Check which runs were cancelled
        cancelled_run_ids = [
            call.kwargs['run_id']
            for call in mock_client.beta.threads.runs.cancel.call_args_list
        ]

        expected_cancelled = ["run_1", "run_2", "run_3"]
        assert sorted(cancelled_run_ids) == sorted(expected_cancelled)

    async def test_ensure_thread_ready_concurrent_cancellation(self, thread_manager, mock_client):
        """Test that multiple runs are cancelled concurrently"""
        # Arrange
        thread_id = "thread_123"
        active_runs = [
            Mock(id=f"run_{i}", status="in_progress")
            for i in range(5)
        ]

        mock_client.beta.threads.runs.list.return_value = active_runs

        # Track cancellation calls
        cancel_calls = []

        def mock_cancel(thread_id, run_id):
            cancel_calls.append((thread_id, run_id))

        mock_client.beta.threads.runs.cancel.side_effect = mock_cancel

        # Act
        result = await thread_manager.ensure_thread_ready(thread_id)

        # Assert
        assert result is True
        assert len(cancel_calls) == 5

        # All should be for the same thread
        assert all(call[0] == thread_id for call in cancel_calls)

        # Should have cancelled all 5 runs
        cancelled_run_ids = [call[1] for call in cancel_calls]
        expected_run_ids = [f"run_{i}" for i in range(5)]
        assert sorted(cancelled_run_ids) == sorted(expected_run_ids)