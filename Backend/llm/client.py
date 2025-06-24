"""Azure OpenAI client management and configuration."""
import logging
import os
import threading
from typing import Any, Dict

from dotenv import find_dotenv, load_dotenv
from openai import AzureOpenAI

# Configure logging
logger = logging.getLogger(__name__)

# Required environment variables
REQUIRED_ENV_VARS = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION"
]

# Global client variable for lazy initialization
CLIENT: AzureOpenAI | None = None
CLIENT_LOCK = threading.Lock()


def load_env_vars() -> None:
    """Load environment variables from .env file with improved error handling."""
    try:
        # Try to find .env file in current directory and parent directories
        env_path = find_dotenv()
        if env_path:
            logger.info("Loading environment variables from: %s", env_path)
            load_dotenv(env_path)
        else:
            logger.warning(
                "No .env file found in current or parent directories")
    except Exception as e:
        logger.error("Error loading .env file: %s", str(e))
        raise


def validate_env_vars() -> None:
    """Validate that all required environment variables are set."""
    missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise OSError(error_msg)

    # Log that all required variables are present (without logging sensitive values)
    logger.info("All required environment variables are present")
    logger.info("Azure OpenAI Endpoint: %s",
                os.getenv('AZURE_OPENAI_ENDPOINT'))
    logger.info("Azure OpenAI Deployment: %s",
                os.getenv('AZURE_OPENAI_DEPLOYMENT'))
    logger.info("Azure OpenAI API Version: %s",
                os.getenv('AZURE_OPENAI_API_VERSION'))


def get_azure_client() -> AzureOpenAI:
    """
    Initializes and returns an Azure OpenAI client using validated environment credentials.

    Loads and validates required environment variables before creating the client. Raises an
    OSError if any required variable is missing, or propagates other exceptions on failure.
    """
    try:
        # Load environment variables
        load_env_vars()

        # Validate required variables
        validate_env_vars()

        # Get environment variables (already validated above)
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

        # Initialize client (variables are guaranteed to be non-None after validation)
        client = AzureOpenAI(
            api_key=api_key,  # type: ignore[arg-type]
            api_version=api_version,  # type: ignore[arg-type]
            azure_endpoint=azure_endpoint  # type: ignore[arg-type]
        )

        logger.info("Azure OpenAI client initialized successfully")
        return client
    except Exception as e:
        logger.error("Failed to initialize Azure OpenAI client: %s", str(e))
        raise


def get_client() -> AzureOpenAI:
    """
    Returns a lazily initialized, thread-safe Azure OpenAI client instance.

    Initializes the client on first use to avoid import-time errors from missing environment 
    variables. Uses a lock to ensure thread safety during initialization. Subsequent calls 
    return the cached client. Raises an exception if initialization fails.
    """
    global CLIENT
    # First check without a lock for performance
    if CLIENT is None:
        with CLIENT_LOCK:
            # Double-check inside the lock to prevent race conditions
            if CLIENT is None:
                try:
                    CLIENT = get_azure_client()
                except Exception:
                    logger.exception(
                        "Failed to initialize Azure OpenAI client")
                    raise
    return CLIENT


async def test_azure_openai_connection() -> Dict[str, Any]:
    """
    Test the Azure OpenAI connection with a simple request.
    Returns a dictionary with connection status and details.
    """
    try:
        azure_client = get_client()
        
        # Simple test request
        response = azure_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "Lease-Parser-GPT-4o"),
            messages=[
                {"role": "user", "content": "Reply with just the word 'test'"}
            ],
            max_tokens=10,
            temperature=0.0
        )
        
        content = response.choices[0].message.content
        
        return {
            "status": "success",
            "response": content,
            "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "Lease-Parser-GPT-4o"),
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "Not set")
        }
        
    except Exception as e:
        logger.exception("Azure OpenAI connection test failed")
        return {
            "status": "error",
            "error": str(e),
            "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "Lease-Parser-GPT-4o"),
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "Not set")
        }
