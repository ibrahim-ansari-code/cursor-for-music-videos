"""
Unit tests for AgentService class.
"""
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from Backend.api.agent.service import AgentService
from Backend.models.agent import UserAgentThread
from Backend.models.user import User
from Backend.models.enums import UserType


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create a mock user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        user_type=UserType.LANDLORD,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def agent_service(mock_session):
    """Create an AgentService instance with mock session."""
    return AgentService(mock_session)


@pytest.fixture
def mock_agent_client():
    """Create a mock BrikliAgentService."""
    client = AsyncMock()
    client.create_thread = AsyncMock(return_value="thread_123")
    client.add_message_and_run = AsyncMock(return_value={
        "thread_id": "thread_123",
        "run_id": "run_123",
        "status": "completed"
    })
    client.get_messages = AsyncMock(return_value=[
        {
            "role": "user",
            "content": "Hello",
            "created_at": datetime.now(UTC),
            "id": "msg_1"
        },
        {
            "role": "assistant",
            "content": "Hi there!",
            "created_at": datetime.now(UTC),
            "id": "msg_2"
        }
    ])
    client.delete_thread = AsyncMock(return_value=True)
    return client


class TestAgentService:
    """Test cases for AgentService."""

    async def test_get_or_create_thread_creates_new(self, agent_service, mock_session, mock_user, mock_agent_client):
        """Test creating a new thread when user has none."""
        # Arrange
        user_id = mock_user.id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(agent_service, '_get_agent_client', return_value=mock_agent_client):
            # Act
            thread_id = await agent_service.get_or_create_thread(user_id)
        
        # Assert
        assert thread_id == "thread_123"
        mock_agent_client.create_thread.assert_called_once()
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_get_or_create_thread_returns_existing(self, agent_service, mock_session, mock_user):
        """Test returning existing thread when user has one."""
        # Arrange
        user_id = mock_user.id
        existing_thread = UserAgentThread(
            id=uuid4(),
            user_id=user_id,
            thread_id="existing_thread_123",
            is_active=True,
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC)
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_thread
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act
        thread_id = await agent_service.get_or_create_thread(user_id)
        
        # Assert
        assert thread_id == "existing_thread_123"
        mock_session.add.assert_not_called()
        mock_session.commit.assert_called_once()  # Called to update last_active

    async def test_start_chat_success(self, agent_service, mock_session, mock_user, mock_agent_client):
        """Test starting a chat successfully."""
        # Arrange
        user_id = mock_user.id
        message = "What properties are vacant?"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(agent_service, '_get_agent_client', return_value=mock_agent_client):
            # Act
            result = await agent_service.start_chat(user_id, message)
        
        # Assert
        assert result["thread_id"] == "thread_123"
        assert result["run_id"] == "run_123"
        assert result["status"] == "completed"
        mock_agent_client.add_message_and_run.assert_called_once_with("thread_123", message)

    async def test_get_chat_status_success(self, agent_service, mock_session, mock_user, mock_agent_client):
        """Test getting chat status successfully."""
        # Arrange
        user_id = mock_user.id
        thread_id = "thread_123"
        run_id = "run_123"
        
        # Mock thread verification
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = True
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        mock_agent_client.get_run_status = AsyncMock(return_value={
            "status": "completed",
            "thread_id": thread_id,
            "run_id": run_id,
            "message": "Here are your vacant properties..."
        })
        
        with patch.object(agent_service, '_get_agent_client', return_value=mock_agent_client):
            # Act
            result = await agent_service.get_chat_status(user_id, thread_id, run_id)
        
        # Assert
        assert result["status"] == "completed"
        assert "message" in result
        mock_agent_client.get_run_status.assert_called_once_with(thread_id, run_id, mock_session)

    async def test_get_chat_status_access_denied(self, agent_service, mock_session, mock_user):
        """Test getting chat status with access denied."""
        # Arrange
        user_id = mock_user.id
        thread_id = "thread_123"
        run_id = "run_123"
        
        # Mock thread verification to fail
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Thread not found or access denied"):
            await agent_service.get_chat_status(user_id, thread_id, run_id)

    async def test_get_chat_history_success(self, agent_service, mock_session, mock_user, mock_agent_client):
        """Test getting chat history successfully."""
        # Arrange
        user_id = mock_user.id
        existing_thread = UserAgentThread(
            id=uuid4(),
            user_id=user_id,
            thread_id="thread_123",
            is_active=True,
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC)
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_thread
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(agent_service, '_get_agent_client', return_value=mock_agent_client):
            # Act
            result = await agent_service.get_chat_history(user_id, limit=10)
        
        # Assert
        assert len(result["messages"]) == 2
        assert result["messages"][0].role == "user"
        assert result["messages"][1].role == "assistant"
        assert result["thread_id"] == "thread_123"
        mock_agent_client.get_messages.assert_called_once_with("thread_123", 10)

    async def test_get_chat_history_no_thread(self, agent_service, mock_session, mock_user):
        """Test getting chat history when user has no thread."""
        # Arrange
        user_id = mock_user.id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act
        result = await agent_service.get_chat_history(user_id)
        
        # Assert
        assert result["messages"] == []
        assert result["thread_id"] is None
        assert result["total"] == 0

    async def test_list_conversations_success(self, agent_service, mock_session, mock_user):
        """Test listing conversations successfully."""
        # Arrange
        user_id = mock_user.id
        threads = [
            UserAgentThread(
                id=uuid4(),
                user_id=user_id,
                thread_id="thread_1",
                is_active=True,
                created_at=datetime.now(UTC),
                last_active=datetime.now(UTC)
            ),
            UserAgentThread(
                id=uuid4(),
                user_id=user_id,
                thread_id="thread_2",
                is_active=False,
                created_at=datetime.now(UTC),
                last_active=datetime.now(UTC)
            )
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = threads
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act
        result = await agent_service.list_conversations(user_id)
        
        # Assert
        assert len(result["conversations"]) == 2
        assert result["total"] == 2
        assert result["conversations"][0]["thread_id"] == "thread_1"
        assert result["conversations"][0]["is_active"] is True

    async def test_clear_chat_success(self, agent_service, mock_session, mock_user, mock_agent_client):
        """Test clearing chat successfully."""
        # Arrange
        user_id = mock_user.id
        active_thread = UserAgentThread(
            id=uuid4(),
            user_id=user_id,
            thread_id="thread_123",
            is_active=True,
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC)
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = active_thread
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(agent_service, '_get_agent_client', return_value=mock_agent_client):
            # Act
            result = await agent_service.clear_chat(user_id)
        
        # Assert
        assert result is True
        mock_agent_client.delete_thread.assert_called_once_with("thread_123")
        mock_session.delete.assert_called_once_with(active_thread)
        mock_session.commit.assert_called_once()

    async def test_clear_chat_no_thread(self, agent_service, mock_session, mock_user):
        """Test clearing chat when user has no thread."""
        # Arrange
        user_id = mock_user.id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act
        result = await agent_service.clear_chat(user_id)
        
        # Assert
        assert result is True
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()

    async def test_agent_client_lazy_initialization(self, agent_service):
        """Test lazy initialization of agent client."""
        # Arrange
        mock_client = AsyncMock()
        
        with patch('Backend.api.agent.service.BrikliAgentService', return_value=mock_client):
            # Act - First access should create client
            client1 = await agent_service._get_agent_client()
            
            # Act - Second access should return same client
            client2 = await agent_service._get_agent_client()
        
        # Assert
        assert client1 is client2
        assert client1 is mock_client

    async def test_verify_thread_ownership_success(self, agent_service, mock_session, mock_user):
        """Test successful thread ownership verification."""
        # Arrange
        user_id = mock_user.id
        thread_id = "thread_123"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = True
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act - Should not raise
        await agent_service._verify_thread_ownership(user_id, thread_id)
        
        # Assert
        mock_session.execute.assert_called_once()

    async def test_verify_thread_ownership_denied(self, agent_service, mock_session, mock_user):
        """Test thread ownership verification failure."""
        # Arrange
        user_id = mock_user.id
        thread_id = "thread_123"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Thread not found or access denied"):
            await agent_service._verify_thread_ownership(user_id, thread_id)