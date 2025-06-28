"""
Authentication helper functions.

This module contains utility functions used across authentication endpoints,
including type protocols and helper functions for common operations.
"""

from datetime import datetime
from typing import Protocol

from Backend.utils.datetime_utils import create_audit_datetime


# === Type Protocols ===

class HasUpdatedAt(Protocol):
    """Protocol for objects that have an updated_at attribute."""
    updated_at: datetime


# === Helper Functions ===

def touch_updated_at(obj: HasUpdatedAt) -> None:
    """
    Helper function to set the updated_at field to the current UTC time.

    Args:
        obj: Any object with an updated_at attribute to be updated.
    """
    # Use our datetime utility for consistent audit timestamp handling
    obj.updated_at = create_audit_datetime()


def extract_user_metadata_from_supabase(user_metadata: dict) -> dict:
    """
    Extract and normalize user metadata from Supabase user object.
    
    Handles various formats of user metadata including full_name splitting
    and ensures consistent field naming.
    
    Args:
        user_metadata: The raw user metadata from Supabase.
        
    Returns:
        A dictionary with normalized user fields.
    """
    full_name = user_metadata.get("full_name", "")
    first_name = user_metadata.get("first_name")
    last_name = user_metadata.get("last_name")
    
    # If first/last name not provided, try to extract from full_name
    if not first_name and full_name:
        parts = full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone": user_metadata.get("phone"),
        "is_email_verified": user_metadata.get("email_verified", False)
    }


def validate_webhook_secret(provided_secret: str | None, expected_secret: str | None) -> bool:
    """
    Validate webhook secret for Supabase webhooks.
    
    Args:
        provided_secret: The secret provided in the request header.
        expected_secret: The expected secret from configuration.
        
    Returns:
        True if the secrets match, False otherwise.
    """
    if not expected_secret:
        # No secret configured means webhook validation is disabled
        return False
    
    if not provided_secret:
        # No secret provided but one is expected
        return False
    
    # Constant-time comparison to prevent timing attacks
    return provided_secret == expected_secret