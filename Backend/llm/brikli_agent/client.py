"""
Azure OpenAI Assistants API client initialization
"""
import os
import logging

from openai import AzureOpenAI

from Backend.config import settings

logger = logging.getLogger(__name__)


class AzureAIClient:
    """
    Manages Azure OpenAI Assistants API client initialization

    This class handles:
    - Azure OpenAI client creation using API key authentication
    - Configuration validation
    """

    def __init__(self) -> None:
        """Initialize Azure OpenAI client"""
        self.assistant_id = settings.AZURE_ASSISTANT_ID

        self._validate_configuration()

        try:
            # Initialize Azure OpenAI client with standard authentication
            # Uses the same env vars as receipt/lease parsers for consistency
            self.client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )

            # Access the beta assistants client
            self.agents_client = self.client.beta.assistants
            
            logger.info("Azure OpenAI Assistants client initialized successfully")
            logger.info(f"Using assistant: {self.assistant_id}")

        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            logger.error("Required environment variables:")
            logger.error("  - AZURE_OPENAI_API_KEY")
            logger.error("  - AZURE_OPENAI_ENDPOINT")
            logger.error("  - AZURE_OPENAI_API_VERSION (optional, defaults to 2025-01-01-preview)")
            logger.error("  - AZURE_ASSISTANT_ID")
            raise

    def _validate_configuration(self) -> None:
        """Validate that all required configuration is present"""
        if not self.assistant_id:
            raise ValueError(
                "Azure Assistant is not configured. "
                "Please set AZURE_ASSISTANT_ID environment variable."
            )
        
        if not settings.AZURE_OPENAI_API_KEY:
            raise ValueError(
                "Azure OpenAI is not fully configured. "
                "Please set AZURE_OPENAI_API_KEY environment variable."
            )
        
        if not settings.AZURE_OPENAI_ENDPOINT:
            raise ValueError(
                "Azure OpenAI is not fully configured. "
                "Please set AZURE_OPENAI_ENDPOINT environment variable."
            )