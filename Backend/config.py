import os
import warnings

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import field_validator, Field

# Load from .env by default
env_path = os.getenv("DOTENV_KEY", ".env")
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """Application settings"""

    # PostgreSQL Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # JWT Settings
    SECRET_KEY: str = Field(min_length=1, description="JWT secret key - must not be empty")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # AI Integration (placeholder for future integration)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv(
        "AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_BLOB_PUBLIC_URL: str = os.getenv("AZURE_BLOB_PUBLIC_URL", "")

    # Apideck Integration Settings (REQUIRED for QuickBooks/Xero integrations)
    # To enable accounting integrations, you must set these environment variables:
    # - APIDECK_API_KEY: Your Apideck API key (get from https://app.apideck.com)
    # - APIDECK_APP_ID: Your Apideck Application ID
    # Without these values, accounting integrations will fail at runtime.
    APIDECK_API_KEY: str = os.getenv("APIDECK_API_KEY", "")
    APIDECK_APP_ID: str = os.getenv("APIDECK_APP_ID", "")
    APIDECK_ENVIRONMENT: str = os.getenv("APIDECK_ENVIRONMENT", "sandbox")  # sandbox or production

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
            # Use logical order (development progression) for error messaging
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

    class Config:
        env_file = env_path
        extra = "allow"

# Initialize settings with default values
settings = Settings(
    SECRET_KEY=os.getenv("SECRET_KEY", "")
)
