import os
import warnings

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# Load from .env by default
env_path = os.getenv("DOTENV_KEY", ".env")
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    """Application settings"""
    
    # === Environment Settings ===
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development or production
    TESTING: bool = os.getenv("TESTING", "false").lower() in ("true", "1", "yes")

    # === Database Settings ===
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # === Azure Storage ===
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_BLOB_PUBLIC_URL: str = os.getenv("AZURE_BLOB_PUBLIC_URL", "")

    # === OpenAI API ===
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # === JWT Settings ===
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

    # === File Upload Settings ===
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB default
    ALLOWED_RECEIPT_MIME_TYPES: set[str] = {
        'application/pdf', 'image/jpeg', 'image/png', 'image/jpg'
    }
    
    # === CSV Import Settings ===
    MAX_CSV_IMPORT_ROWS: int = int(os.getenv("MAX_CSV_IMPORT_ROWS", 1000))  # Max rows per CSV import
    CSV_IMPORT_BATCH_SIZE: int = int(os.getenv("CSV_IMPORT_BATCH_SIZE", 100))  # Rows to process per batch
    CSV_IMPORT_TIMEOUT_SECONDS: int = int(os.getenv("CSV_IMPORT_TIMEOUT_SECONDS", 300))  # 5 minutes default

    # === Blob Storage Settings ===
    BLOB_CONTAINER_RECEIPTS: str = os.getenv("BLOB_CONTAINER_RECEIPTS", "receipts")
    BLOB_CONTAINER_PAYMENTS: str = os.getenv("BLOB_CONTAINER_PAYMENTS", "payment-receipts")

    # === Apideck API ===
    APIDECK_API_KEY: str = os.getenv("APIDECK_API_KEY", "")
    APIDECK_APP_ID: str = os.getenv("APIDECK_APP_ID", "")
    APIDECK_ENVIRONMENT: str = os.getenv(
        "APIDECK_ENVIRONMENT", "sandbox")  # sandbox or production

    # === Supabase Webhook Security ===
    # This secret is used to secure webhook endpoints. It is required for production.
    SUPABASE_WEBHOOK_SECRET: str = os.getenv("SUPABASE_WEBHOOK_SECRET", "")
    
    # === Azure AI Agent Configuration ===
    # Azure AI Foundry project endpoint for the Brikli Agent
    AZURE_AGENT_ENDPOINT: str = os.getenv("AZURE_AGENT_ENDPOINT", "")
    # Assistant ID from Azure AI Studio
    AZURE_ASSISTANT_ID: str = os.getenv("AZURE_ASSISTANT_ID", "")
    
    # === Azure Authentication Options ===
    # Option 1: Service Principal (Recommended for production)
    AZURE_CLIENT_ID: str = os.getenv("AZURE_CLIENT_ID", "")
    AZURE_CLIENT_SECRET: str = os.getenv("AZURE_CLIENT_SECRET", "")
    AZURE_TENANT_ID: str = os.getenv("AZURE_TENANT_ID", "")
    
    # Option 2: API Key (Simple fallback if Service Principal/Managed Identity not available)
    # DEPRECATED: API Key authentication is no longer supported for Azure AI Agents
    # Please use Service Principal, Managed Identity, or Azure CLI authentication instead
    AZURE_AGENT_API_KEY: str = os.getenv("AZURE_AGENT_API_KEY", "")

    @field_validator('APIDECK_ENVIRONMENT')
    @classmethod
    def validate_apideck_environment(cls, v: str) -> str:
        """
        Validates that the APIDECK_ENVIRONMENT value is either 'sandbox' or 'production'.

        Raises:
            ValueError: If the provided value is not 'sandbox' or 'production'.

        Returns:
            The validated APIDECK_ENVIRONMENT value.
        """
        allowed_environments = {"sandbox", "production"}
        if v not in allowed_environments:
            raise ValueError(
                f"Invalid APIDECK_ENVIRONMENT: '{v}'. Must be one of: 'sandbox', 'production'."
            )
        return v

    def model_post_init(self, __context) -> None:
        """
        Emits a runtime warning if Apideck API credentials are not configured.

        A warning is issued if either `APIDECK_API_KEY` or `APIDECK_APP_ID` is missing, indicating that accounting integrations such as QuickBooks will be unavailable until both are set.
        """
        # Validate Apideck configuration (warning - optional feature)
        if not self.APIDECK_API_KEY or not self.APIDECK_APP_ID:
            warnings.warn(
                "APIDECK_API_KEY and APIDECK_APP_ID are not configured. "
                "QuickBooks and other accounting integrations will not work. "
                "To enable these features, set both environment variables. "
                "Get your credentials from https://app.apideck.com",
                RuntimeWarning,
                stacklevel=2
            )
        # Validate Supabase webhook secret
        if not self.SUPABASE_WEBHOOK_SECRET:
            warnings.warn(
                "SUPABASE_WEBHOOK_SECRET is not configured. "
                "Webhook endpoints are not secure. This is not recommended for production.",
                RuntimeWarning,
                stacklevel=2,
            )
        
        # Validate Azure AI Agent configuration (warning - optional until fully implemented)
        if not self.AZURE_AGENT_ENDPOINT or not self.AZURE_ASSISTANT_ID:
            warnings.warn(
                "Azure AI Agent is not fully configured. "
                "AZURE_AGENT_ENDPOINT and AZURE_ASSISTANT_ID must both be set. "
                "The AI Assistant feature will not work until these are configured.",
                RuntimeWarning,
                stacklevel=2
            )

    # === Additional Settings ===
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")

    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    model_config = SettingsConfigDict(env_file=env_path, extra="allow")


# Initialize settings with default values
settings = Settings(
    SECRET_KEY=os.getenv("SECRET_KEY", "")
)
