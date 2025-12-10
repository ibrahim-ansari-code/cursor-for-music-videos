"""
Unit tests for AzureAIClient class
"""
import pytest
from unittest.mock import Mock, patch

from Backend.llm.brikli_agent.client import AzureAIClient


class TestAzureAIClient:
    """Test cases for AzureAIClient class"""

    def test_validate_configuration_missing_endpoint(self):
        """Test configuration validation with missing endpoint"""
        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_OPENAI_ENDPOINT = ""
            mock_settings.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
            mock_settings.AZURE_OPENAI_API_VERSION = "2025-01-01-preview"
            mock_settings.AZURE_ASSISTANT_ID = "test-id"

            with pytest.raises(ValueError, match="Azure OpenAI is not fully configured"):
                AzureAIClient()

    def test_validate_configuration_missing_assistant_id(self):
        """Test configuration validation with missing assistant ID"""
        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
            mock_settings.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
            mock_settings.AZURE_OPENAI_API_VERSION = "2025-01-01-preview"
            mock_settings.AZURE_ASSISTANT_ID = ""

            with pytest.raises(ValueError, match="Azure Assistant is not configured"):
                AzureAIClient()

    @patch('Backend.llm.brikli_agent.client.AzureOpenAI')
    def test_successful_initialization(self, mock_azure_openai, caplog):
        """Test successful client initialization"""
        # Arrange
        mock_client_instance = Mock()
        mock_beta = Mock()
        mock_assistants = Mock()
        mock_beta.assistants = mock_assistants
        mock_client_instance.beta = mock_beta
        mock_azure_openai.return_value = mock_client_instance

        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
            mock_settings.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
            mock_settings.AZURE_OPENAI_API_VERSION = "2025-01-01-preview"
            mock_settings.AZURE_ASSISTANT_ID = "asst_test123"

            # Act
            client = AzureAIClient()

            # Assert
            assert client.assistant_id == "asst_test123"
            assert client.client == mock_client_instance
            assert client.agents_client == mock_assistants
            assert "Azure OpenAI Assistants client initialized successfully" in caplog.text
            assert "Using assistant: asst_test123" in caplog.text

            mock_azure_openai.assert_called_once_with(
                api_key="test-key",
                api_version="2025-01-01-preview",
                azure_endpoint="https://test.openai.azure.com/"
            )

    @patch('Backend.llm.brikli_agent.client.AzureOpenAI')
    def test_client_initialization_failure(self, mock_azure_openai):
        """Test client initialization failure handling"""
        # Arrange
        mock_azure_openai.side_effect = Exception("Authentication failed")

        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
            mock_settings.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
            mock_settings.AZURE_OPENAI_API_VERSION = "2025-01-01-preview"
            mock_settings.AZURE_ASSISTANT_ID = "asst_test123"

            # Act & Assert
            with pytest.raises(Exception, match="Authentication failed"):
                AzureAIClient()
