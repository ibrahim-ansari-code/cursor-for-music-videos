import os
import logging
from functools import lru_cache
from typing import Tuple

from supabase import Client, create_client

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_supabase_config() -> Tuple[str, str]:
    """
    Cache and validate Supabase configuration.
    
    This function is cached to avoid repeated environment variable lookups
    and validation, improving performance while following best practices.
    
    Returns:
        Tuple[str, str]: A tuple of (url, key) for Supabase configuration
        
    Raises:
        ValueError: If required environment variables are not set
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set"
        )
    
    return url, key


def get_supabase_client() -> Client:
    """
    Creates and returns a new Supabase client instance.
    
    Following Supabase best practices, this function creates a new client instance
    for each call rather than using a singleton pattern. The createClient function
    is lightweight and designed for this usage pattern.
    
    Performance optimizations:
        - Environment variables are cached via lru_cache to avoid repeated lookups
        - Client creation is optimized by Supabase SDK internally
        - Connection pooling is handled by the underlying HTTP client
    
    Returns:
        Client: A new Supabase client instance configured for admin operations
        
    Raises:
        ValueError: If required environment variables are not set
        Exception: If client creation fails
        
    Example:
        >>> client = get_supabase_client()
        >>> user_data = client.auth.get_user(token)
        
    Best Practices:
        - Create a new client for each operation or request
        - Don't store client instances globally
        - Let the SDK handle connection pooling internally
    """
    try:
        url, key = _get_supabase_config()
        
        # Create a new client instance (lightweight operation per Supabase docs)
        client = create_client(url, key)
        
        # Log only in debug mode to avoid log spam
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("📱 Created new Supabase client instance")
            
        return client
        
    except ValueError:
        # Re-raise configuration errors as-is
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create Supabase client: {str(e)}")
        raise
