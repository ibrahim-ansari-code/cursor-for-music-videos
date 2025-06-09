import os

from supabase import Client, create_client


def get_supabase_client() -> Client:
    """
    Returns a Supabase client instance using credentials from environment variables.
    
    Raises:
        ValueError: If either SUPABASE_URL or SUPABASE_SERVICE_KEY environment variable is not set.
    """
    url = os.getenv("SUPABASE_URL")
    # Use service key for admin operations
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set")

    return create_client(url, key)
