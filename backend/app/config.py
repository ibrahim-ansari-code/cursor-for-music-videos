"""
Application configuration using Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "MeloVue API"
    debug: bool = False
    
    # Database
    database_url: str = "sqlite:///./melovue.db"
    
    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    
    # Storage (S3/R2)
    storage_bucket: str = "melovue-uploads"
    storage_region: str = "auto"
    storage_endpoint_url: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    
    # API Keys
    elevenlabs_api_key: str | None = None
    gumloop_api_key: str | None = None
    gumloop_user_id: str | None = None
    gumloop_pipeline_id: str | None = None
    
    # Video generation
    video_gen_api_key: str | None = None
    video_gen_api_url: str | None = None
    
    # File constraints
    max_audio_size_mb: int = 50
    max_image_size_mb: int = 10
    max_audio_duration_s: int = 600  # 10 minutes
    
    # Signed URL expiry
    signed_url_expiry_minutes: int = 60
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
