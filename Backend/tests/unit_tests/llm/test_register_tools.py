"""
Unit tests for tool registration.
"""
import pytest
from unittest.mock import patch, MagicMock

from Backend.llm.register_tools import register_tools


class TestRegisterTools:
    """Test cases for tool registration."""

    @patch('Backend.llm.register_tools.BrikliAgentService')
    @patch('Backend.llm.register_tools.logger')
    async def test_register_tools_success(self, mock_logger, mock_agent_service_class):
        """Test successful tool registration."""
        # Arrange
        mock_service = MagicMock()
        mock_updated_agent = MagicMock()
        mock_updated_agent.id = "test-agent-id"
        mock_updated_agent.tools = ["tool1", "tool2"]
        mock_service.register_tools_with_assistant.return_value = mock_updated_agent
        mock_agent_service_class.return_value = mock_service
        
        # Act
        result = await register_tools()
        
        # Assert
        assert result is True
        mock_agent_service_class.assert_called_once()
        mock_service.register_tools_with_assistant.assert_called_once()

    @patch('Backend.llm.register_tools.BrikliAgentService')
    @patch('Backend.llm.register_tools.logger')
    async def test_register_tools_initialization_error(self, mock_logger, mock_agent_service_class):
        """Test tool registration with initialization error."""
        # Arrange
        mock_agent_service_class.side_effect = Exception("Config error")
        
        # Act
        result = await register_tools()
        
        # Assert
        assert result is False
        mock_logger.error.assert_called()

    @patch('Backend.llm.register_tools.BrikliAgentService')
    @patch('Backend.llm.register_tools.logger')
    async def test_register_tools_registration_error(self, mock_logger, mock_agent_service_class):
        """Test tool registration with registration error."""
        # Arrange
        mock_service = MagicMock()
        mock_service.register_tools_with_assistant.side_effect = Exception("API error")
        mock_agent_service_class.return_value = mock_service
        
        # Act
        result = await register_tools()
        
        # Assert
        assert result is False
        mock_logger.error.assert_called()