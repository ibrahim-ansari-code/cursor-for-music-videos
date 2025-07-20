"""
Unit tests for LLM agent service.
"""
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import json

from Backend.llm.agent_service import BrikliAgentService
from Backend.config import settings


@pytest.fixture
def agent_service():
    """Create a BrikliAgentService instance."""
    with patch.object(settings, 'AZURE_AGENT_ENDPOINT', 'https://test.endpoint.com'), \
         patch.object(settings, 'AZURE_ASSISTANT_ID', 'test-assistant-id'):
        return BrikliAgentService()


@pytest.fixture
def mock_ai_client():
    """Create a mock AI project client."""
    client = MagicMock()
    client.agents = MagicMock()
    client.agents.threads = MagicMock()
    client.agents.messages = MagicMock()
    client.agents.runs = MagicMock()
    return client


class TestBrikliAgentService:
    """Test cases for BrikliAgentService."""

    def test_init_validates_configuration(self):
        """Test that initialization validates required configuration."""
        # Test with missing configuration
        with patch.object(settings, 'AZURE_AGENT_ENDPOINT', None):
            with pytest.raises(ValueError, match="Azure AI Agent is not fully configured"):
                BrikliAgentService()

    @patch('Backend.llm.agent_service.AIProjectClient')
    def test_init_with_valid_configuration(self, mock_client_class):
        """Test successful initialization with valid configuration."""
        # Arrange
        with patch.object(settings, 'AZURE_AGENT_ENDPOINT', 'https://test.com'), \
             patch.object(settings, 'AZURE_ASSISTANT_ID', 'test-id'):
            
            # Act
            service = BrikliAgentService()
            
            # Assert
            assert service.endpoint == 'https://test.com'
            assert service.assistant_id == 'test-id'
            mock_client_class.assert_called_once()

    async def test_create_thread_success(self, agent_service, mock_ai_client):
        """Test successful thread creation."""
        # Arrange
        mock_thread = MagicMock()
        mock_thread.id = "thread_123"
        mock_ai_client.agents.threads.create.return_value = mock_thread
        
        with patch.object(agent_service, 'client', mock_ai_client):
            # Act
            thread_id = await agent_service.create_thread()
            
            # Assert
            assert thread_id == "thread_123"
            mock_ai_client.agents.threads.create.assert_called_once()

    async def test_create_thread_failure(self, agent_service, mock_ai_client):
        """Test thread creation failure."""
        # Arrange
        mock_ai_client.agents.threads.create.side_effect = Exception("API error")
        
        with patch.object(agent_service, 'client', mock_ai_client):
            # Act & Assert
            with pytest.raises(Exception, match="API error"):
                await agent_service.create_thread()

    async def test_delete_thread_success(self, agent_service, mock_ai_client):
        """Test successful thread deletion."""
        # Arrange
        thread_id = "thread_123"
        
        with patch.object(agent_service, 'client', mock_ai_client):
            # Act
            result = await agent_service.delete_thread(thread_id)
            
            # Assert
            assert result is True
            mock_ai_client.agents.threads.delete.assert_called_once_with(thread_id)

    async def test_delete_thread_failure_returns_false(self, agent_service, mock_ai_client):
        """Test thread deletion failure returns False."""
        # Arrange
        thread_id = "thread_123"
        mock_ai_client.agents.threads.delete.side_effect = Exception("Not found")
        
        with patch.object(agent_service, 'client', mock_ai_client):
            # Act
            result = await agent_service.delete_thread(thread_id)
            
            # Assert
            assert result is False

    async def test_add_message_and_run_success(self, agent_service, mock_ai_client):
        """Test adding message and creating run."""
        # Arrange
        thread_id = "thread_123"
        message = "Hello"
        mock_run = MagicMock()
        mock_run.id = "run_123"
        mock_run.status = "in_progress"
        mock_ai_client.agents.runs.create.return_value = mock_run
        
        with patch.object(agent_service, 'client', mock_ai_client):
            # Act
            result = await agent_service.add_message_and_run(thread_id, message)
            
            # Assert
            assert result["thread_id"] == thread_id
            assert result["run_id"] == "run_123"
            assert result["status"] == "in_progress"
            mock_ai_client.agents.messages.create.assert_called_once()
            mock_ai_client.agents.runs.create.assert_called_once()

    async def test_get_messages_success(self, agent_service, mock_ai_client):
        """Test getting messages from thread."""
        # Arrange
        thread_id = "thread_123"
        
        # Create mock messages
        mock_msg1 = MagicMock()
        mock_msg1.id = "msg_1"
        mock_msg1.role = "user"
        mock_msg1.created_at = datetime.now(UTC)
        mock_msg1.content = [MagicMock()]
        mock_msg1.content[0].type = "text"
        mock_msg1.content[0].text = MagicMock()
        mock_msg1.content[0].text.value = "Hello"
        
        mock_msg2 = MagicMock()
        mock_msg2.id = "msg_2"
        mock_msg2.role = "assistant"
        mock_msg2.created_at = datetime.now(UTC)
        mock_msg2.content = [MagicMock()]
        mock_msg2.content[0].type = "text"
        mock_msg2.content[0].text = MagicMock()
        mock_msg2.content[0].text.value = "Hi there!"
        
        mock_ai_client.agents.messages.list.return_value = [mock_msg1, mock_msg2]
        
        with patch.object(agent_service, 'client', mock_ai_client):
            # Act
            messages = await agent_service.get_messages(thread_id)
            
            # Assert
            assert len(messages) == 2
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "Hello"
            assert messages[1]["role"] == "assistant"
            assert messages[1]["content"] == "Hi there!"

    def test_register_tools_with_assistant_success(self, agent_service, mock_ai_client):
        """Test registering tools with assistant."""
        # Arrange
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_properties",
                    "description": "Search properties"
                }
            }
        ]
        
        # Mock the update_agent method to return a successful response
        mock_ai_client.agents.update_agent.return_value = MagicMock()
        
        with patch('Backend.llm.tools.get_tool_definitions', return_value=mock_tools):
            with patch.object(agent_service, 'client', mock_ai_client):
                # Act
                result = agent_service.register_tools_with_assistant()
                
                # Assert
                mock_ai_client.agents.update_agent.assert_called_once_with(
                    agent_id=agent_service.assistant_id,
                    tools=mock_tools
                )

    async def test_ensure_thread_ready_cancels_active_runs(self, agent_service, mock_ai_client):
        """Test ensuring thread is ready by canceling active runs."""
        # Arrange
        thread_id = "thread_123"
        
        # Create mock run that needs canceling
        mock_run = MagicMock()
        mock_run.id = "run_123"
        mock_run.status = "in_progress"
        
        mock_ai_client.agents.runs.list.return_value = [mock_run]
        
        with patch.object(agent_service, 'client', mock_ai_client):
            # Act
            result = await agent_service._ensure_thread_ready(thread_id)
            
            # Assert
            assert result is True
            mock_ai_client.agents.runs.cancel.assert_called_once_with(
                thread_id=thread_id,
                run_id="run_123"
            )