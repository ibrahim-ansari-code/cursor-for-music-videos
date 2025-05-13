import os
from supabase import create_client, Client
from Backend.config import settings

def get_supabase_client() -> Client:
    """Get a Supabase client instance."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for admin operations
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set")
    
    return create_client(url, key) 