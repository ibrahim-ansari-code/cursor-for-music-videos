"""
Azure AI client initialization and authentication management
"""
import os
import logging

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential, EnvironmentCredential
from azure.core.credentials import TokenCredential

from Backend.config import settings

logger = logging.getLogger(__name__)


class AzureAIClient:
    """
    Manages Azure AI client initialization and authentication

    This class handles:
    - Azure AI Projects client creation
    - Authentication method selection and configuration
    - Configuration validation
    """

    def __init__(self) -> None:
        """Initialize Azure AI client with appropriate credential"""
        self.endpoint = settings.AZURE_AGENT_ENDPOINT
        self.assistant_id = settings.AZURE_ASSISTANT_ID

        self._validate_configuration()

        # Initialize Azure AI Projects client with appropriate credential
        # Authentication priority:
        # 1. Service Principal (most secure for production)
        # 2. Managed Identity (for Azure-hosted apps with IMDS enabled)
        # 3. Azure CLI / DefaultAzureCredential (for local development)

        credential: TokenCredential

        # Check for Service Principal authentication
        if all([os.getenv("AZURE_CLIENT_ID"),
                os.getenv("AZURE_CLIENT_SECRET"),
                os.getenv("AZURE_TENANT_ID")]):
            logger.info("Using Service Principal authentication")
            # Use EnvironmentCredential for explicit Service Principal authentication
            # This avoids trying other auth methods first
            credential = EnvironmentCredential()

        # Check for User-Assigned Managed Identity (only if IMDS available)
        elif os.getenv("AZURE_CLIENT_ID") and os.getenv("WEBSITE_SITE_NAME"):
            logger.info("Using User-Assigned Managed Identity")
            credential = ManagedIdentityCredential(client_id=os.getenv("AZURE_CLIENT_ID"))

        # Check for System-Assigned Managed Identity (only if IMDS available)
        elif os.getenv("WEBSITE_SITE_NAME"):
            logger.info("Using System-Assigned Managed Identity")
            credential = ManagedIdentityCredential()

        # Local development - DefaultAzureCredential (includes Azure CLI)
        else:
            logger.info("Using DefaultAzureCredential for local development")
            logger.info("Make sure you are logged in with 'az login'")
            credential = DefaultAzureCredential()

        try:
            # Initialize the client with TokenCredential
            self.client = AIProjectClient(
                endpoint=self.endpoint,
                credential=credential
            )
            # Access the agents client
            self.agents_client = self.client.agents
            logger.info("Azure AI Agent client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Azure AI client: {str(e)}")
            logger.error("Authentication configuration required:")
            logger.error("1. For production: Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID")
            logger.error("2. For Azure hosting: Enable Managed Identity")
            logger.error("3. For local dev: Run 'az login'")
            raise

    def _validate_configuration(self) -> None:
        """Validate that all required configuration is present"""
        if not all([self.endpoint, self.assistant_id]):
            raise ValueError(
                "Azure AI Agent is not fully configured. "
                "Please set AZURE_AGENT_ENDPOINT and AZURE_ASSISTANT_ID environment variables."
            )