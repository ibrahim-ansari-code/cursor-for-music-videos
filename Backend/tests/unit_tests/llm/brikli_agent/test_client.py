"""
Unit tests for AzureAIClient class
"""
import os
import pytest
from unittest.mock import Mock, patch

from Backend.llm.brikli_agent.client import AzureAIClient


class TestAzureAIClient:
    """Test cases for AzureAIClient class"""

    def test_validate_configuration_missing_endpoint(self):
        """Test configuration validation with missing endpoint"""
        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = None
            mock_settings.AZURE_ASSISTANT_ID = "test-id"

            with pytest.raises(ValueError, match="Azure AI Agent is not fully configured"):
                AzureAIClient()

    def test_validate_configuration_missing_assistant_id(self):
        """Test configuration validation with missing assistant ID"""
        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = "https://test.endpoint.com"
            mock_settings.AZURE_ASSISTANT_ID = None

            with pytest.raises(ValueError, match="Azure AI Agent is not fully configured"):
                AzureAIClient()

    @patch.dict(os.environ, {
        "AZURE_CLIENT_ID": "test-client-id",
        "AZURE_CLIENT_SECRET": "test-secret",
        "AZURE_TENANT_ID": "test-tenant-id"
    }, clear=True)
    @patch('Backend.llm.brikli_agent.client.AIProjectClient')
    @patch('Backend.llm.brikli_agent.client.EnvironmentCredential')
    def test_service_principal_authentication(self, mock_credential, mock_client_class, caplog):
        """Test service principal authentication (production scenario)"""
        # Arrange
        mock_credential_instance = Mock()
        mock_credential.return_value = mock_credential_instance

        mock_client_instance = Mock()
        mock_agents_client = Mock()
        mock_client_instance.agents = mock_agents_client
        mock_client_class.return_value = mock_client_instance

        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = "https://test.endpoint.com"
            mock_settings.AZURE_ASSISTANT_ID = "test-assistant-id"

            # Act
            client = AzureAIClient()

            # Assert
            assert client.endpoint == "https://test.endpoint.com"
            assert client.assistant_id == "test-assistant-id"
            assert client.client == mock_client_instance
            assert client.agents_client == mock_agents_client

            mock_credential.assert_called_once()
            mock_client_class.assert_called_once_with(
                endpoint="https://test.endpoint.com",
                credential=mock_credential_instance
            )
            assert "Using Service Principal authentication" in caplog.text

    @patch.dict(os.environ, {
        "AZURE_CLIENT_ID": "test-client-id",
        "WEBSITE_SITE_NAME": "test-app-service"
    }, clear=True)
    @patch('Backend.llm.brikli_agent.client.AIProjectClient')
    @patch('Backend.llm.brikli_agent.client.ManagedIdentityCredential')
    def test_user_assigned_managed_identity(self, mock_credential, mock_client_class, caplog):
        """Test user-assigned managed identity authentication"""
        # Arrange
        mock_credential_instance = Mock()
        mock_credential.return_value = mock_credential_instance

        mock_client_instance = Mock()
        mock_agents_client = Mock()
        mock_client_instance.agents = mock_agents_client
        mock_client_class.return_value = mock_client_instance

        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = "https://test.endpoint.com"
            mock_settings.AZURE_ASSISTANT_ID = "test-assistant-id"

            # Act
            client = AzureAIClient()

            # Assert
            mock_credential.assert_called_once_with(client_id="test-client-id")
            assert "Using User-Assigned Managed Identity" in caplog.text

    @patch.dict(os.environ, {
        "WEBSITE_SITE_NAME": "test-app-service"
    }, clear=True)
    @patch('Backend.llm.brikli_agent.client.AIProjectClient')
    @patch('Backend.llm.brikli_agent.client.ManagedIdentityCredential')
    def test_system_assigned_managed_identity(self, mock_credential, mock_client_class, caplog):
        """Test system-assigned managed identity authentication"""
        # Arrange
        mock_credential_instance = Mock()
        mock_credential.return_value = mock_credential_instance

        mock_client_instance = Mock()
        mock_agents_client = Mock()
        mock_client_instance.agents = mock_agents_client
        mock_client_class.return_value = mock_client_instance

        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = "https://test.endpoint.com"
            mock_settings.AZURE_ASSISTANT_ID = "test-assistant-id"

            # Act
            client = AzureAIClient()

            # Assert
            mock_credential.assert_called_once()
            assert "Using System-Assigned Managed Identity" in caplog.text

    @patch.dict(os.environ, {}, clear=True)
    @patch('Backend.llm.brikli_agent.client.AIProjectClient')
    @patch('Backend.llm.brikli_agent.client.DefaultAzureCredential')
    def test_default_credential_local_development(self, mock_credential, mock_client_class, caplog):
        """Test default credential for local development"""
        # Arrange
        mock_credential_instance = Mock()
        mock_credential.return_value = mock_credential_instance

        mock_client_instance = Mock()
        mock_agents_client = Mock()
        mock_client_instance.agents = mock_agents_client
        mock_client_class.return_value = mock_client_instance

        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = "https://test.endpoint.com"
            mock_settings.AZURE_ASSISTANT_ID = "test-assistant-id"

            # Act
            client = AzureAIClient()

            # Assert
            mock_credential.assert_called_once()
            assert "Using DefaultAzureCredential for local development" in caplog.text
            assert "Make sure you are logged in with 'az login'" in caplog.text

    @patch('Backend.llm.brikli_agent.client.AIProjectClient')
    @patch('Backend.llm.brikli_agent.client.DefaultAzureCredential')
    def test_client_initialization_failure(self, mock_credential, mock_client_class):
        """Test client initialization failure handling"""
        # Arrange
        mock_credential_instance = Mock()
        mock_credential.return_value = mock_credential_instance

        mock_client_class.side_effect = Exception("Authentication failed")

        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = "https://test.endpoint.com"
            mock_settings.AZURE_ASSISTANT_ID = "test-assistant-id"

            # Act & Assert
            with pytest.raises(Exception, match="Authentication failed"):
                AzureAIClient()

    @patch('Backend.llm.brikli_agent.client.AIProjectClient')
    @patch('Backend.llm.brikli_agent.client.DefaultAzureCredential')
    def test_successful_initialization_with_logging(self, mock_credential, mock_client_class, caplog):
        """Test successful client initialization with proper logging"""
        # Arrange
        mock_credential_instance = Mock()
        mock_credential.return_value = mock_credential_instance

        mock_client_instance = Mock()
        mock_agents_client = Mock()
        mock_client_instance.agents = mock_agents_client
        mock_client_class.return_value = mock_client_instance

        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = "https://test.endpoint.com"
            mock_settings.AZURE_ASSISTANT_ID = "test-assistant-id"

            # Act
            client = AzureAIClient()

            # Assert
            assert "Azure AI Agent client initialized successfully" in caplog.text
            assert client.client is not None
            assert client.agents_client is not None

    @patch.dict(os.environ, {
        "AZURE_CLIENT_ID": "test-client-id",
        "AZURE_CLIENT_SECRET": "",  # Empty secret should not count as valid
        "AZURE_TENANT_ID": "test-tenant-id"
    }, clear=True)
    @patch('Backend.llm.brikli_agent.client.AIProjectClient')
    @patch('Backend.llm.brikli_agent.client.DefaultAzureCredential')
    def test_service_principal_incomplete_credentials(self, mock_credential, mock_client_class):
        """Test service principal with incomplete credentials falls back to default"""
        # Arrange
        mock_credential_instance = Mock()
        mock_credential.return_value = mock_credential_instance

        mock_client_instance = Mock()
        mock_agents_client = Mock()
        mock_client_instance.agents = mock_agents_client
        mock_client_class.return_value = mock_client_instance

        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = "https://test.endpoint.com"
            mock_settings.AZURE_ASSISTANT_ID = "test-assistant-id"

            # Act
            client = AzureAIClient()

            # Assert
            # Should fall back to DefaultAzureCredential since secret is empty
            mock_credential.assert_called_once()

    @patch('Backend.llm.brikli_agent.client.AIProjectClient')
    @patch('Backend.llm.brikli_agent.client.DefaultAzureCredential')
    @patch('Backend.llm.brikli_agent.client.ManagedIdentityCredential')
    def test_authentication_priority_order(self, mock_managed_identity, mock_default_credential, mock_client_class, caplog):
        """Test that authentication methods follow correct priority order"""
        # Setup mock instances
        mock_default_instance = Mock()
        mock_managed_instance = Mock()
        mock_default_credential.return_value = mock_default_instance
        mock_managed_identity.return_value = mock_managed_instance

        mock_client_instance = Mock()
        mock_agents_client = Mock()
        mock_client_instance.agents = mock_agents_client
        mock_client_class.return_value = mock_client_instance

        with patch('Backend.llm.brikli_agent.client.settings') as mock_settings:
            mock_settings.AZURE_AGENT_ENDPOINT = "https://test.endpoint.com"
            mock_settings.AZURE_ASSISTANT_ID = "test-assistant-id"

            # Test Service Principal (highest priority)
            with patch('Backend.llm.brikli_agent.client.EnvironmentCredential') as mock_env_credential:
                mock_env_instance = Mock()
                mock_env_credential.return_value = mock_env_instance
                
                with patch.dict(os.environ, {
                    "AZURE_CLIENT_ID": "client",
                    "AZURE_CLIENT_SECRET": "secret", 
                    "AZURE_TENANT_ID": "tenant"
                }, clear=True):
                    caplog.clear()
                    client = AzureAIClient()
                    assert client.client is not None
                    assert "Using Service Principal authentication" in caplog.text
                    mock_env_credential.assert_called_once()

            # Reset mocks
            mock_default_credential.reset_mock()
            mock_managed_identity.reset_mock()

            # Test User-assigned Managed Identity
            with patch.dict(os.environ, {
                "AZURE_CLIENT_ID": "client",
                "WEBSITE_SITE_NAME": "app"
            }, clear=True):
                caplog.clear()
                client = AzureAIClient()
                assert client.client is not None
                assert "Using User-Assigned Managed Identity" in caplog.text
                mock_managed_identity.assert_called_with(client_id="client")

            # Reset mocks
            mock_default_credential.reset_mock()
            mock_managed_identity.reset_mock()

            # Test System-assigned Managed Identity
            with patch.dict(os.environ, {
                "WEBSITE_SITE_NAME": "app"
            }, clear=True):
                caplog.clear()
                client = AzureAIClient()
                assert client.client is not None
                assert "Using System-Assigned Managed Identity" in caplog.text
                mock_managed_identity.assert_called_with()

            # Reset mocks
            mock_default_credential.reset_mock()
            mock_managed_identity.reset_mock()

            # Test Default credential (lowest priority)
            with patch.dict(os.environ, {}, clear=True):
                caplog.clear()
                client = AzureAIClient()
                assert client.client is not None
                assert "Using DefaultAzureCredential for local development" in caplog.text
                mock_default_credential.assert_called()