import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # PostgreSQL Database Settings
    POSTGRES_USER: str = os.getenv("PGUSER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("PGPASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("PGDATABASE", "propertymanagement")
    POSTGRES_HOST: str = os.getenv("PGHOST", "localhost")
    POSTGRES_PORT: str = os.getenv("PGPORT", "5432")
    
    # SQLAlchemy Database URL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # AI Integration (placeholder for future integration)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Azure Storage Connection String and Blob Public URL
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_BLOB_PUBLIC_URL: str = os.getenv("AZURE_BLOB_PUBLIC_URL", "")
    
    class Config:
        env_file = ".env"
        extra = "allow"
        
settings = Settings()
