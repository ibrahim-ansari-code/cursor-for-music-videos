"""
Unit tests for ToolManager class
"""
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from Backend.llm.brikli_agent.tools.manager import ToolManager


@pytest.fixture
def mock_agents_client():
    """Create mock Azure AI agents client"""
    client = Mock()
    client.update_agent = Mock()
    client.runs = Mock()
    return client


@pytest.fixture
def mock_thread_manager():
    """Create mock thread manager"""
    manager = AsyncMock()
    manager.get_user_id_from_thread = AsyncMock(return_value=uuid4())
    return manager


@pytest.fixture
def tool_manager(mock_agents_client, mock_thread_manager):
    """Create ToolManager instance with mocks"""
    return ToolManager(mock_agents_client, "assistant_123", mock_thread_manager)


class TestToolManager:
    """Test cases for ToolManager class"""

    def test_register_tools_with_assistant_success(self, tool_manager, mock_agents_client):
        """Test successful tool registration"""
        # Arrange
        mock_tools = [
            {"function": {"name": "search_properties"}},
            {"function": {"name": "get_tenant_info"}}
        ]

        mock_updated_agent = Mock(id="assistant_123")
        mock_agents_client.update_agent.return_value = mock_updated_agent

        with patch('Backend.llm.brikli_agent.tools.definitions.get_tool_definitions') as mock_get_tools:
            mock_get_tools.return_value = mock_tools

            # Act
            result = tool_manager.register_tools_with_assistant()

            # Assert
            assert result == mock_updated_agent
            mock_agents_client.update_agent.assert_called_once_with(
                agent_id="assistant_123",
                tools=mock_tools
            )

    def test_register_tools_with_assistant_failure(self, tool_manager, mock_agents_client):
        """Test tool registration failure"""
        # Arrange
        mock_tools = [{"function": {"name": "search_properties"}}]
        mock_agents_client.update_agent.side_effect = Exception("Update failed")

        with patch('Backend.llm.brikli_agent.tools.definitions.get_tool_definitions') as mock_get_tools:
            mock_get_tools.return_value = mock_tools

            # Act & Assert
            with pytest.raises(Exception, match="Update failed"):
                tool_manager.register_tools_with_assistant()

    async def test_execute_tool_call_search_properties(self, tool_manager, mock_thread_manager):
        """Test executing search_properties tool call"""
        # Arrange
        mock_tool_call = Mock()
        mock_tool_call.function.name = "search_properties"
        mock_tool_call.function.arguments = '{"status": "Active"}'

        thread_id = "thread_123"
        mock_session = AsyncMock()

        with patch('Backend.llm.brikli_agent.tools.handlers.ToolHandlers.search_properties') as mock_search:
            mock_search.return_value = {"properties": []}

            # Act
            result = await tool_manager.execute_tool_call(mock_tool_call, thread_id, mock_session)

            # Assert
            assert "properties" in result
            mock_search.assert_called_once_with(
                {"status": "Active"},
                mock_thread_manager.get_user_id_from_thread.return_value,
                mock_session
            )

    async def test_execute_tool_call_get_tenant_info(self, tool_manager, mock_thread_manager):
        """Test executing get_tenant_info tool call"""
        # Arrange
        mock_tool_call = Mock()
        mock_tool_call.function.name = "get_tenant_info"
        mock_tool_call.function.arguments = '{"tenant_name": "John Doe"}'

        thread_id = "thread_123"
        mock_session = AsyncMock()

        with patch('Backend.llm.brikli_agent.tools.handlers.ToolHandlers.get_tenant_info') as mock_get_tenant:
            mock_get_tenant.return_value = {"tenants": []}

            # Act
            result = await tool_manager.execute_tool_call(mock_tool_call, thread_id, mock_session)

            # Assert
            assert "tenants" in result
            mock_get_tenant.assert_called_once_with(
                {"tenant_name": "John Doe"},
                mock_thread_manager.get_user_id_from_thread.return_value,
                mock_session
            )

    async def test_execute_tool_call_all_supported_tools(self, tool_manager, mock_thread_manager):
        """Test executing all supported tool calls"""
        # Arrange
        supported_tools = [
            ("search_properties", '{"status": "Active"}'),
            ("get_tenant_info", '{"tenant_name": "John"}'),
            ("get_financial_summary", '{"period": "current_month"}'),
            ("get_maintenance_requests", '{"status": "Pending"}'),
            ("get_lease_expiry_info", '{"days_ahead": 90}'),
            ("get_payment_status", '{"status": "overdue"}'),
            ("search_lease_documents", '{"query": "pet policy"}')
        ]

        thread_id = "thread_123"
        mock_session = AsyncMock()

        for tool_name, arguments in supported_tools:
            mock_tool_call = Mock()
            mock_tool_call.function.name = tool_name
            mock_tool_call.function.arguments = arguments

            patch_path = f'Backend.llm.brikli_agent.tools.handlers.ToolHandlers.{tool_name}'
            with patch(patch_path) as mock_method:
                mock_method.return_value = {"result": "success"}

                # Act
                result = await tool_manager.execute_tool_call(mock_tool_call, thread_id, mock_session)

                # Assert
                assert result["result"] == "success"
                mock_method.assert_called_once()

    async def test_execute_tool_call_unknown_tool(self, tool_manager):
        """Test executing unknown tool call"""
        # Arrange
        mock_tool_call = Mock()
        mock_tool_call.function.name = "unknown_tool"
        mock_tool_call.function.arguments = "{}"

        # Act
        result = await tool_manager.execute_tool_call(mock_tool_call, "thread_123", AsyncMock())

        # Assert
        assert "error" in result
        assert "Unknown tool: unknown_tool" in result["error"]

    async def test_execute_tool_call_invalid_arguments(self, tool_manager):
        """Test executing tool call with invalid arguments"""
        # Arrange
        mock_tool_call = Mock()
        mock_tool_call.function.name = "search_properties"
        mock_tool_call.function.arguments = "invalid json"

        # Act
        result = await tool_manager.execute_tool_call(mock_tool_call, "thread_123", AsyncMock())

        # Assert
        assert "error" in result
        assert "Error executing search_properties" in result["error"]

    async def test_execute_tool_call_execution_error(self, tool_manager, mock_thread_manager):
        """Test tool call execution error handling"""
        # Arrange
        mock_tool_call = Mock()
        mock_tool_call.function.name = "search_properties"
        mock_tool_call.function.arguments = '{"status": "Active"}'

        thread_id = "thread_123"
        mock_session = AsyncMock()

        with patch('Backend.llm.brikli_agent.tools.handlers.ToolHandlers.search_properties') as mock_search:
            mock_search.side_effect = Exception("Database error")

            # Act
            result = await tool_manager.execute_tool_call(mock_tool_call, thread_id, mock_session)

            # Assert
            assert "error" in result
            assert "Error executing search_properties: Database error" in result["error"]

    async def test_handle_tool_calls_streaming_success(self, tool_manager, mock_agents_client, mock_thread_manager):
        """Test successful streaming tool calls handling"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"

        mock_tool_call = Mock()
        mock_tool_call.id = "tool_call_1"
        mock_tool_call.function.name = "search_properties"
        mock_tool_call.function.arguments = '{"status": "Active"}'

        mock_required_action = Mock()
        mock_required_action.submit_tool_outputs = Mock()
        mock_required_action.submit_tool_outputs.tool_calls = [mock_tool_call]

        with patch('Backend.llm.brikli_agent.tools.handlers.ToolHandlers.handle_tool_call') as mock_handle:
            mock_handle.return_value = {"properties": []}

            with patch('Backend.database.get_session') as mock_get_session:
                mock_session = AsyncMock()

                async def mock_session_generator():
                    yield mock_session

                mock_get_session.return_value = mock_session_generator()

                # Act
                await tool_manager.handle_tool_calls_streaming(thread_id, run_id, mock_required_action)

                # Assert
                mock_handle.assert_called_once_with(
                    tool_name="search_properties",
                    arguments='{"status": "Active"}',
                    user_id=mock_thread_manager.get_user_id_from_thread.return_value,
                    session=mock_session
                )

                mock_agents_client.runs.submit_tool_outputs.assert_called_once()

    async def test_handle_tool_calls_streaming_no_tool_calls(self, tool_manager):
        """Test streaming tool calls handling with no tool calls"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"

        # Mock required action with no tool calls
        mock_required_action = Mock()
        mock_required_action.submit_tool_outputs = Mock()
        mock_required_action.submit_tool_outputs.tool_calls = []

        # Act
        await tool_manager.handle_tool_calls_streaming(thread_id, run_id, mock_required_action)

        # Assert - should return early without error

    async def test_handle_tool_calls_streaming_alternative_structure(self, tool_manager, mock_agents_client, mock_thread_manager):
        """Test streaming tool calls with alternative required_action structure"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"

        mock_tool_call = Mock()
        mock_tool_call.id = "tool_call_1"
        mock_tool_call.function.name = "get_tenant_info"
        mock_tool_call.function.arguments = '{"tenant_name": "John"}'

        # Alternative structure - tool_calls directly on required_action
        mock_required_action = Mock(spec=['tool_calls'])
        mock_required_action.tool_calls = [mock_tool_call]

        with patch('Backend.llm.brikli_agent.tools.handlers.ToolHandlers.handle_tool_call') as mock_handle:
            mock_handle.return_value = {"tenants": []}

            with patch('Backend.database.get_session') as mock_get_session:
                mock_session = AsyncMock()

                async def mock_session_generator():
                    yield mock_session

                mock_get_session.return_value = mock_session_generator()

                # Act
                await tool_manager.handle_tool_calls_streaming(thread_id, run_id, mock_required_action)

                # Assert
                mock_handle.assert_called_once_with(
                    tool_name="get_tenant_info",
                    arguments='{"tenant_name": "John"}',
                    user_id=mock_thread_manager.get_user_id_from_thread.return_value,
                    session=mock_session
                )

    async def test_handle_tool_calls_streaming_execution_error(self, tool_manager):
        """Test streaming tool calls with execution error"""
        # Arrange
        thread_id = "thread_123"
        run_id = "run_123"

        mock_tool_call = Mock()
        mock_tool_call.function.name = "search_properties"
        mock_tool_call.function.arguments = '{"status": "Active"}'

        mock_required_action = Mock()
        mock_required_action.submit_tool_outputs = Mock()
        mock_required_action.submit_tool_outputs.tool_calls = [mock_tool_call]

        with patch('Backend.database.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            # Act & Assert
            with pytest.raises(Exception, match="Database connection failed"):
                await tool_manager.handle_tool_calls_streaming(thread_id, run_id, mock_required_action)

    async def test_tool_manager_initialization(self, mock_agents_client, mock_thread_manager):
        """Test ToolManager initialization"""
        # Act
        tool_manager = ToolManager(mock_agents_client, "test-assistant", mock_thread_manager)

        # Assert
        assert tool_manager.agents_client == mock_agents_client
        assert tool_manager.assistant_id == "test-assistant"
        assert tool_manager.thread_manager == mock_thread_manager

    async def test_execute_tool_call_empty_arguments(self, tool_manager, mock_thread_manager):
        """Test executing tool call with empty arguments"""
        # Arrange
        mock_tool_call = Mock()
        mock_tool_call.function.name = "search_properties"
        mock_tool_call.function.arguments = None  # No arguments

        thread_id = "thread_123"
        mock_session = AsyncMock()

        with patch('Backend.llm.brikli_agent.tools.handlers.ToolHandlers.search_properties') as mock_search:
            mock_search.return_value = {"properties": []}

            # Act
            result = await tool_manager.execute_tool_call(mock_tool_call, thread_id, mock_session)

            # Assert
            assert "properties" in result
            # Should be called with empty dict when arguments is None
            mock_search.assert_called_once_with(
                {},  # Empty arguments
                mock_thread_manager.get_user_id_from_thread.return_value,
                mock_session
            )