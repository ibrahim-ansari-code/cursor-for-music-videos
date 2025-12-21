import os
import logging
from functools import lru_cache
from typing import Tuple

from supabase import Client, create_client

logger = logging.getLogger(__name__)


def _get_supabase_config() -> Tuple[str, str]:
    """
    Get and validate Supabase configuration.

    Returns:
        Tuple[str, str]: A tuple of (url, key) for Supabase configuration

    Raises:
        ValueError: If required environment variables are not set
    """
    # For admin operations, we need the direct Supabase URL (*.supabase.co),
    # not a custom domain like api.brikli.com which doesn't support admin APIs.
    # SUPABASE_DIRECT_URL takes precedence for admin operations.
    url = os.getenv("SUPABASE_DIRECT_URL") or os.getenv("SUPABASE_URL")
    # Try both possible env var names for service role key
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        missing = []
        if not url:
            missing.append("SUPABASE_URL or SUPABASE_DIRECT_URL")
        if not key:
            missing.append("SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_ROLE_KEY")
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    # Log which URL we're using
    logger.debug(f"Using Supabase URL: {url}")

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
