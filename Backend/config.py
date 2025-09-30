import os
import warnings
import logging

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

logger = logging.getLogger(__name__)

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


    # === Intuit (QuickBooks Online) OAuth ===
    INTUIT_CLIENT_ID: str = os.getenv("INTUIT_CLIENT_ID", "")
    INTUIT_CLIENT_SECRET: str = os.getenv("INTUIT_CLIENT_SECRET", "")
    INTUIT_REDIRECT_URI: str = os.getenv("INTUIT_REDIRECT_URI", "")
    INTUIT_ENV: str = os.getenv("INTUIT_ENV", "sandbox")  # sandbox or production

    # The following QuickBooks settings are intentionally hard-coded to avoid
    # configuration sprawl. Update here only if Intuit changes their endpoints
    # or if we intentionally bump versions/scopes.
    @property
    def INTUIT_AUTH_URL(self) -> str:  # OAuth authorize endpoint
        return "https://appcenter.intuit.com/connect/oauth2"

    @property
    def INTUIT_TOKEN_URL(self) -> str:  # OAuth token endpoint
        return "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

    @property
    def INTUIT_SCOPES(self) -> str:  # OAuth scopes
        # QuickBooks automatically provides refresh tokens with these standard scopes
        return "com.intuit.quickbooks.accounting com.intuit.quickbooks.payment"
    @property
    def QBO_MINOR_VERSION(self) -> int:  # QuickBooks API minor version
        return 73

    @property
    def INTUIT_STATE_TTL_MINUTES(self) -> int:  # OAuth state lifetime
        return 15

    # Internal rate limits for connect flow protection (not env-driven)
    @property
    def QB_RATE_LIMIT_REQUESTS(self) -> int:
        return 10

    @property
    def QB_RATE_LIMIT_WINDOW_HOURS(self) -> int:
        return 1

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

    # === reCAPTCHA (Google) ===
    # Secret key from Google reCAPTCHA admin (v3 recommended)
    # When set, reCAPTCHA verification is automatically enabled
    RECAPTCHA_SECRET_KEY: str = os.getenv("RECAPTCHA_SECRET_KEY", "")
    # Minimum acceptable score for v3 (0.0 - 1.0). Typical defaults: 0.5
    RECAPTCHA_MIN_SCORE: float = float(os.getenv("RECAPTCHA_MIN_SCORE", 0.5))
    # Verification endpoint (override only for testing)
    RECAPTCHA_VERIFY_URL: str = os.getenv("RECAPTCHA_VERIFY_URL", "https://www.google.com/recaptcha/api/siteverify")

    @field_validator('RECAPTCHA_MIN_SCORE')
    @classmethod
    def validate_recaptcha_min_score(cls, v: float) -> float:
        """
        Validates that the RECAPTCHA_MIN_SCORE is between 0.0 and 1.0.
        """
        if not 0.0 <= v <= 1.0:
            raise ValueError(
                f"Invalid RECAPTCHA_MIN_SCORE: '{v}'. Must be between 0.0 and 1.0."
            )
        return v


    @field_validator('INTUIT_ENV')
    @classmethod
    def validate_intuit_environment(cls, v: str) -> str:
        """
        Validates that the INTUIT_ENV value is either 'sandbox' or 'production'.
        """
        allowed = {"sandbox", "production"}
        if v not in allowed:
            raise ValueError(
                f"Invalid INTUIT_ENV: '{v}'. Must be one of: 'sandbox', 'production'."
            )
        return v

    def model_post_init(self, __context) -> None:
        """
        Validates configuration and emits warnings for missing critical settings.
        """
        # Warn if Intuit credentials are missing
        if not self.INTUIT_CLIENT_ID or not self.INTUIT_CLIENT_SECRET or not self.INTUIT_REDIRECT_URI:
            warnings.warn(
                "INTUIT_CLIENT_ID/INTUIT_CLIENT_SECRET/INTUIT_REDIRECT_URI are not fully configured. "
                "QuickBooks integration will not work until these are set.",
                RuntimeWarning,
                stacklevel=2,
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
