"""
Unit tests for MessageHandler class
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from Backend.llm.brikli_agent.messages import MessageHandler


@pytest.fixture
def mock_agents_client():
    """Create mock Azure AI agents client"""
    client = Mock()
    client.messages = Mock()
    return client


@pytest.fixture
def mock_thread_manager():
    """Create mock thread manager"""
    manager = AsyncMock()
    return manager


@pytest.fixture
def message_handler(mock_agents_client, mock_thread_manager):
    """Create MessageHandler instance with mocks"""
    return MessageHandler(mock_agents_client, mock_thread_manager)


class TestMessageHandler:
    """Test cases for MessageHandler class"""

    async def test_get_messages_success(self, message_handler, mock_agents_client):
        """Test successful message retrieval"""
        # Arrange
        thread_id = "thread_123"

        mock_message = Mock()
        mock_message.id = "msg_123"
        mock_message.role = "assistant"
        mock_message.content = [Mock(type="text", text=Mock(value="Hello!"))]
        mock_message.created_at = datetime.now()

        mock_agents_client.messages.list.return_value = [mock_message]

        # Act
        messages = await message_handler.get_messages(thread_id, limit=10)

        # Assert
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"] == "Hello!"
        assert messages[0]["id"] == "msg_123"

        mock_agents_client.messages.list.assert_called_once_with(
            thread_id=thread_id,
            order="asc",
            limit=10
        )

    async def test_get_messages_filters_duplicates(self, message_handler, mock_agents_client):
        """Test that duplicate messages are filtered out"""
        # Arrange
        thread_id = "thread_123"

        # Create two messages with the same ID
        mock_message1 = Mock()
        mock_message1.id = "msg_123"
        mock_message1.role = "user"
        mock_message1.content = [Mock(type="text", text=Mock(value="First"))]
        mock_message1.created_at = datetime.now()

        mock_message2 = Mock()
        mock_message2.id = "msg_123"  # Same ID
        mock_message2.role = "user"
        mock_message2.content = [Mock(type="text", text=Mock(value="Duplicate"))]
        mock_message2.created_at = datetime.now()

        mock_agents_client.messages.list.return_value = [mock_message1, mock_message2]

        # Act
        messages = await message_handler.get_messages(thread_id)

        # Assert
        assert len(messages) == 1  # Duplicate should be filtered
        assert messages[0]["content"] == "First"

    async def test_get_messages_handles_different_content_types(self, message_handler, mock_agents_client):
        """Test handling different message content types"""
        # Arrange
        thread_id = "thread_123"

        # Message with text content
        text_message = Mock()
        text_message.id = "msg_1"
        text_message.role = "assistant"
        text_message.content = [Mock(type="text", text=Mock(value="Text message"))]
        text_message.created_at = datetime.now()

        # Message with direct string content
        string_message = Mock()
        string_message.id = "msg_2"
        string_message.role = "user"
        string_message.content = ["Direct string"]
        string_message.created_at = datetime.now()

        # Message with non-text content (should be filtered out due to empty content)
        other_message = Mock()
        other_message.id = "msg_3"
        other_message.role = "assistant"
        other_message.content = [Mock(type="image")]
        other_message.created_at = datetime.now()

        mock_agents_client.messages.list.return_value = [text_message, string_message, other_message]

        # Act
        messages = await message_handler.get_messages(thread_id)

        # Assert
        # Non-text content produces empty string, so it gets filtered out
        assert len(messages) == 2
        assert messages[0]["content"] == "Text message"
        assert messages[1]["content"] == "Direct string"

    async def test_get_messages_skips_empty_content(self, message_handler, mock_agents_client):
        """Test that messages with empty content are skipped"""
        # Arrange
        thread_id = "thread_123"

        # Message with content
        valid_message = Mock()
        valid_message.id = "msg_1"
        valid_message.role = "assistant"
        valid_message.content = [Mock(type="text", text=Mock(value="Valid content"))]
        valid_message.created_at = datetime.now()

        # Message with empty content
        empty_message = Mock()
        empty_message.id = "msg_2"
        empty_message.role = "user"
        empty_message.content = [Mock(type="text", text=Mock(value=""))]
        empty_message.created_at = datetime.now()

        mock_agents_client.messages.list.return_value = [valid_message, empty_message]

        # Act
        messages = await message_handler.get_messages(thread_id)

        # Assert
        assert len(messages) == 1
        assert messages[0]["content"] == "Valid content"

    async def test_get_messages_failure(self, message_handler, mock_agents_client):
        """Test message retrieval failure handling"""
        # Arrange
        thread_id = "thread_123"
        mock_agents_client.messages.list.side_effect = Exception("API error")

        # Act & Assert
        with pytest.raises(Exception, match="API error"):
            await message_handler.get_messages(thread_id)

    async def test_add_user_message_to_thread_success(self, message_handler, mock_agents_client, mock_thread_manager):
        """Test successful user message addition"""
        # Arrange
        thread_id = "thread_123"
        message_content = "Hello assistant!"
        mock_thread_manager.ensure_thread_ready.return_value = True

        # Act
        result = await message_handler.add_user_message_to_thread(thread_id, message_content)

        # Assert
        assert result is True
        mock_thread_manager.ensure_thread_ready.assert_called_once_with(thread_id)
        mock_agents_client.messages.create.assert_called_once_with(
            thread_id=thread_id,
            role="user",
            content=message_content
        )

    async def test_add_user_message_thread_not_ready(self, message_handler, mock_thread_manager):
        """Test message addition when thread is not ready"""
        # Arrange
        thread_id = "thread_123"
        message_content = "Hello!"
        mock_thread_manager.ensure_thread_ready.return_value = False

        # Act
        result = await message_handler.add_user_message_to_thread(thread_id, message_content)

        # Assert
        assert result is False

    async def test_add_user_message_creation_failure(self, message_handler, mock_agents_client, mock_thread_manager):
        """Test message addition when creation fails"""
        # Arrange
        thread_id = "thread_123"
        message_content = "Hello!"
        mock_thread_manager.ensure_thread_ready.return_value = True
        mock_agents_client.messages.create.side_effect = Exception("Creation failed")

        # Act
        result = await message_handler.add_user_message_to_thread(thread_id, message_content)

        # Assert
        assert result is False

    async def test_get_messages_handles_missing_attributes(self, message_handler, mock_agents_client):
        """Test handling messages with missing attributes"""
        # Arrange
        thread_id = "thread_123"

        # Message missing ID
        message_no_id = Mock()
        message_no_id.id = None
        message_no_id.role = "user"
        message_no_id.content = [Mock(type="text", text=Mock(value="No ID"))]
        message_no_id.created_at = datetime.now()

        # Message with valid attributes
        valid_message = Mock()
        valid_message.id = "msg_1"
        valid_message.role = "assistant"
        valid_message.content = [Mock(type="text", text=Mock(value="Valid"))]
        valid_message.created_at = datetime.now()

        mock_agents_client.messages.list.return_value = [message_no_id, valid_message]

        # Act
        messages = await message_handler.get_messages(thread_id)

        # Assert
        # Should only include message with valid ID (messages without IDs are now properly filtered)
        assert len(messages) == 1
        assert messages[0]["content"] == "Valid"

    async def test_get_messages_with_complex_content_structure(self, message_handler, mock_agents_client):
        """Test handling complex content structures"""
        # Arrange
        thread_id = "thread_123"

        # Message with nested text structure
        complex_message = Mock()
        complex_message.id = "msg_1"
        complex_message.role = "assistant"

        # Create nested text object
        text_obj = Mock()
        text_obj.value = "Nested content"
        content_part = Mock()
        content_part.type = "text"
        content_part.text = text_obj
        complex_message.content = [content_part]
        complex_message.created_at = datetime.now()

        mock_agents_client.messages.list.return_value = [complex_message]

        # Act
        messages = await message_handler.get_messages(thread_id)

        # Assert
        assert len(messages) == 1
        assert messages[0]["content"] == "Nested content"

    async def test_get_messages_empty_response(self, message_handler, mock_agents_client):
        """Test handling empty message list response"""
        # Arrange
        thread_id = "thread_123"
        mock_agents_client.messages.list.return_value = []

        # Act
        messages = await message_handler.get_messages(thread_id)

        # Assert
        assert messages == []