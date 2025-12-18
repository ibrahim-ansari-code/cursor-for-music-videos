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
    
    # Document security settings
    DOCUMENT_SAS_EXPIRY_HOURS: int = int(os.getenv("DOCUMENT_SAS_EXPIRY_HOURS", "1"))
    DOCUMENT_ACCESS_LOGGING_ENABLED: bool = os.getenv("DOCUMENT_ACCESS_LOGGING_ENABLED", "true").lower() == "true"
    
    # Parse account name and key from connection string for SAS token generation
    @property
    def AZURE_STORAGE_ACCOUNT_NAME(self) -> str:
        """Extract account name from connection string"""
        if not self.AZURE_STORAGE_CONNECTION_STRING:
            return ""
        for part in self.AZURE_STORAGE_CONNECTION_STRING.split(';'):
            if part.startswith('AccountName='):
                return part.split('=', 1)[1]
        return ""
    
    @property
    def AZURE_STORAGE_ACCOUNT_KEY(self) -> str:
        """Extract account key from connection string"""
        if not self.AZURE_STORAGE_CONNECTION_STRING:
            return ""
        for part in self.AZURE_STORAGE_CONNECTION_STRING.split(';'):
            if part.startswith('AccountKey='):
                return part.split('=', 1)[1]
        return ""

    # === OpenAI API ===
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # === Azure OpenAI Configuration ===
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    AZURE_ASSISTANT_ID: str = os.getenv("AZURE_ASSISTANT_ID", "")

    # === JWT Settings ===
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    
    # === Email Correlation Secret (separate from JWT secret for security isolation) ===
    # Used only for generating opaque correlation IDs in email metadata
    # If not set, derives from SECRET_KEY with domain separation
    @property
    def EMAIL_CORRELATION_SECRET(self) -> str:
        """Get email-specific secret for correlation ID generation."""
        env_secret = os.getenv("EMAIL_CORRELATION_SECRET", "")
        if env_secret:
            return env_secret
        # Derive from SECRET_KEY with domain separation to isolate secrets
        import hashlib
        return hashlib.sha256(f"email_correlation:{self.SECRET_KEY}".encode()).hexdigest()

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
        # Using accounting-only scope to avoid forced QuickBooks Payments onboarding
        # This is especially important for Canadian users who may not be eligible for Payments
        return "com.intuit.quickbooks.accounting"
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
    
    # === Stripe Billing Configuration ===
    STRIPE_API_KEY: str = os.getenv("STRIPE_API_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_ID_PLATFORM: str = os.getenv("STRIPE_PRICE_ID_PLATFORM", "")
    STRIPE_BILLING_PORTAL_RETURN_URL: str = os.getenv(
        "STRIPE_BILLING_PORTAL_RETURN_URL",
        "https://app.brikli.com/settings?tab=billing"
    )
    STRIPE_TRIAL_PERIOD_DAYS: int = int(os.getenv("STRIPE_TRIAL_PERIOD_DAYS", "14"))
    
    # === Stripe Connect (Rent Payments) ===
    # Separate webhook secret for Connect events (account.updated)
    STRIPE_CONNECT_WEBHOOK_SECRET: str = os.getenv("STRIPE_CONNECT_WEBHOOK_SECRET", "")
    # Webhook secret for rent payment events (payment_intent.*, charge.*)
    STRIPE_RENT_PAYMENT_WEBHOOK_SECRET: str = os.getenv("STRIPE_RENT_PAYMENT_WEBHOOK_SECRET", "")
    
    # === SendGrid Email Configuration ===
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL: str = os.getenv("SENDGRID_FROM_EMAIL", "noreply@brikli.com")
    SENDGRID_FROM_NAME: str = os.getenv("SENDGRID_FROM_NAME", "Brikli Property Management")
    
    # === Frontend URL ===
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://app.brikli.com")

    # === Tenant Portal URL ===
    TENANT_PORTAL_URL: str = os.getenv("TENANT_PORTAL_URL", "https://tenant.brikli.com")

    # === Internal API Key for Scheduled Jobs ===
    # Used by pg_cron to authenticate scheduled notification jobs
    INTERNAL_CRON_API_KEY: str = os.getenv("INTERNAL_CRON_API_KEY", "")

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
        
        # Validate SendGrid configuration
        if not self.SENDGRID_API_KEY:
            warnings.warn(
                "SENDGRID_API_KEY is not configured. "
                "Email notifications will not be sent.",
                RuntimeWarning,
                stacklevel=2,
            )
        
        # Validate Azure AI Assistant configuration (warning - optional until fully implemented)
        if not self.AZURE_ASSISTANT_ID:
            warnings.warn(
                "Azure AI Assistant is not configured. "
                "AZURE_ASSISTANT_ID must be set. "
                "The AI Assistant feature will not work until this is configured.",
                RuntimeWarning,
                stacklevel=2
            )
        
        # Validate Stripe Billing configuration
        if not self.STRIPE_API_KEY or not self.STRIPE_WEBHOOK_SECRET:
            warnings.warn(
                "Stripe billing is not fully configured. "
                "STRIPE_API_KEY and STRIPE_WEBHOOK_SECRET must both be set. "
                "Subscription and billing features will not work until these are configured.",
                RuntimeWarning,
                stacklevel=2
            )

    # === Additional Settings ===
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    model_config = SettingsConfigDict(env_file=env_path, extra="allow")


# Initialize settings with default values
settings = Settings(
    SECRET_KEY=os.getenv("SECRET_KEY", "")
)
