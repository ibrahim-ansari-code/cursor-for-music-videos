import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load from .env.production by default
env_path = os.getenv("DOTENV_KEY", ".env.production")
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    """Application settings"""

    # PostgreSQL Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # JWT Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # AI Integration (placeholder for future integration)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_BLOB_PUBLIC_URL: str = os.getenv("AZURE_BLOB_PUBLIC_URL", "")

    class Config:
        env_file = env_path
        extra = "allow"

settings = Settings()
