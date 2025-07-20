"""
Unit tests for LLM agent service.
"""
import pytest
from unittest.mock import Mock, patch

from Backend.llm.agent_service import BrikliAgentService

@pytest.fixture
def mock_azure_client():
    """Mock the Azure AI client to prevent network calls"""
    with patch('Backend.llm.agent_service.AIProjectClient') as mock_client_class:
        # Create mock client instance
        mock_client = Mock()
        mock_agents_client = Mock()
        
        # Mock the agents property
        mock_client.agents = mock_agents_client
        
        # Mock thread operations
        mock_agents_client.threads = Mock()
        mock_agents_client.threads.create = Mock(return_value=Mock(id='thread_123'))
        mock_agents_client.threads.delete = Mock()
        
        # Mock message operations
        mock_agents_client.messages = Mock()
        mock_agents_client.messages.create = Mock()
        mock_agents_client.messages.list = Mock(return_value=[])
        
        # Mock run operations
        mock_agents_client.runs = Mock()
        mock_agents_client.runs.create = Mock(return_value=Mock(id='run_123', status='queued'))
        mock_agents_client.runs.get = Mock(return_value=Mock(status='completed'))
        mock_agents_client.runs.list = Mock(return_value=[])
        mock_agents_client.runs.cancel = Mock()
        mock_agents_client.runs.stream = Mock()
        mock_agents_client.runs.submit_tool_outputs = Mock()
        
        # Mock agent operations
        mock_agents_client.update_agent = Mock(return_value=Mock(id='assistant_123'))
        
        # Set up the client class to return our mock
        mock_client_class.return_value = mock_client
        
        yield mock_agents_client

@pytest.fixture
def agent_service(mock_azure_client):
    """Create agent service with mocked dependencies"""
    with patch('Backend.llm.agent_service.settings') as mock_settings:
        mock_settings.AZURE_AGENT_ENDPOINT = 'https://test.endpoint.com'
        mock_settings.AZURE_ASSISTANT_ID = 'test-assistant-id'
        return BrikliAgentService()

class TestBrikliAgentService:
    """Test cases for BrikliAgentService"""
    
    def test_init_validates_configuration(self):
        """Test that initialization validates required configuration"""
        with patch('Backend.llm.agent_service.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = None
            mock_settings.AZURE_ASSISTANT_ID = None
            with pytest.raises(ValueError, match="Azure AI Agent is not fully configured"):
                BrikliAgentService()

    def test_init_with_valid_configuration(self, mock_azure_client):
        """Test successful initialization with valid configuration"""
        with patch('Backend.llm.agent_service.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = 'https://test.endpoint.com'
            mock_settings.AZURE_ASSISTANT_ID = 'test-assistant-id'
            service = BrikliAgentService()
            assert service.endpoint == 'https://test.endpoint.com'
            assert service.assistant_id == 'test-assistant-id'
            assert service.agents_client is not None

    async def test_create_thread_success(self, agent_service, mock_azure_client):
        """Test successful thread creation"""
        # Setup
        mock_azure_client.threads.create.return_value = Mock(id='thread_123')
        
        # Execute
        thread_id = await agent_service.create_thread()
        
        # Verify
        assert thread_id == 'thread_123'
        mock_azure_client.threads.create.assert_called_once()

    async def test_create_thread_failure(self, agent_service, mock_azure_client):
        """Test thread creation failure handling"""
        # Setup
        mock_azure_client.threads.create.side_effect = Exception("Network error")
        
        # Execute & Verify
        with pytest.raises(Exception, match="Network error"):
            await agent_service.create_thread()

    async def test_delete_thread_success(self, agent_service, mock_azure_client):
        """Test successful thread deletion"""
        # Setup
        thread_id = "thread_123"
        
        # Execute
        result = await agent_service.delete_thread(thread_id)
        
        # Verify
        assert result is True
        mock_azure_client.threads.delete.assert_called_once_with(thread_id)

    async def test_delete_thread_failure_returns_false(self, agent_service, mock_azure_client):
        """Test that thread deletion failure returns False instead of raising"""
        # Setup
        thread_id = "thread_123"
        mock_azure_client.threads.delete.side_effect = Exception("Network error")
        
        # Execute
        result = await agent_service.delete_thread(thread_id)
        
        # Verify
        assert result is False

    async def test_add_message_and_run_success(self, agent_service, mock_azure_client):
        """Test successful message addition and run creation"""
        # Setup
        thread_id = "thread_123"
        message = "Hello, assistant!"
        mock_run = Mock(id='run_123', status='queued')
        mock_azure_client.runs.create.return_value = mock_run
        
        # Execute
        result = await agent_service.add_message_and_run(thread_id, message)
        
        # Verify
        assert result['thread_id'] == thread_id
        assert result['run_id'] == 'run_123'
        assert result['status'] == 'queued'
        mock_azure_client.messages.create.assert_called_once_with(
            thread_id=thread_id,
            role="user",
            content=message
        )
        mock_azure_client.runs.create.assert_called_once()

    async def test_get_messages_success(self, agent_service, mock_azure_client):
        """Test successful message retrieval"""
        # Setup
        thread_id = "thread_123"
        mock_message = Mock()
        mock_message.role = "assistant"
        mock_message.content = [Mock(type='text', text=Mock(value='Hello!'))]
        mock_message.created_at = "2023-01-01T00:00:00Z"
        mock_message.id = "msg_123"
        
        mock_azure_client.messages.list.return_value = [mock_message]
        
        # Execute
        messages = await agent_service.get_messages(thread_id)
        
        # Verify
        assert len(messages) == 1
        assert messages[0]['role'] == 'assistant'
        assert messages[0]['content'] == 'Hello!'
        assert messages[0]['id'] == 'msg_123'
        
        mock_azure_client.messages.list.assert_called_once_with(
            thread_id=thread_id,
            order="asc",
            limit=20
        )

    @patch('Backend.llm.tools.get_tool_definitions')
    def test_register_tools_with_assistant_success(self, mock_get_tools, agent_service, mock_azure_client):
        """Test successful tool registration"""
        # Setup
        mock_tools = [{'function': {'name': 'test_tool'}}]
        mock_get_tools.return_value = mock_tools
        mock_updated_agent = Mock(id='assistant_123')
        mock_azure_client.update_agent.return_value = mock_updated_agent
        
        # Execute
        result = agent_service.register_tools_with_assistant()
        
        # Verify
        assert result.id == 'assistant_123'
        mock_azure_client.update_agent.assert_called_once_with(
            agent_id=agent_service.assistant_id,
            tools=mock_tools
        )

    async def test_ensure_thread_ready_cancels_active_runs(self, agent_service, mock_azure_client):
        """Test that active runs are canceled to ensure thread readiness"""
        # Setup
        thread_id = "thread_123"
        active_run = Mock(id='run_active', status='in_progress')
        completed_run = Mock(id='run_completed', status='completed')
        mock_azure_client.runs.list.return_value = [active_run, completed_run]
        
        # Execute
        result = await agent_service._ensure_thread_ready(thread_id)
        
        # Verify
        assert result is True
        mock_azure_client.runs.list.assert_called_once()
        mock_azure_client.runs.cancel.assert_called_once_with(
            thread_id=thread_id,
            run_id='run_active'
        )