import os

from supabase import Client, create_client

def get_supabase_client() -> Client:
    """Get a Supabase client instance."""
    url = os.getenv("SUPABASE_URL")
    # Use service key for admin operations
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set")

    return create_client(url, key)
