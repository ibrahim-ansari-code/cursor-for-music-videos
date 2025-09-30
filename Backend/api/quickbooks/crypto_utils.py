"""
Encryption utilities for QuickBooks token management.

This module provides encryption/decryption functions for securely storing
OAuth tokens in the database. Separated from utils.py to avoid circular imports.
"""

import base64
import hashlib
import logging
from cryptography.fernet import Fernet

from Backend.config import settings

logger = logging.getLogger(__name__)


def _get_encryption_key() -> bytes:
    """
    Generates or retrieves the encryption key for token storage.

    Uses the application's SECRET_KEY to derive a consistent Fernet-compatible key.
    This ensures tokens can be decrypted across application restarts.
    """
    # Use SECRET_KEY to derive a consistent encryption key
    key_material = settings.SECRET_KEY.encode('utf-8')
    # Create a 32-byte key using SHA-256
    derived_key = hashlib.sha256(key_material).digest()
    # Convert to Fernet-compatible base64 encoded key
    return base64.urlsafe_b64encode(derived_key)


def encrypt_token(token: str) -> str:
    """
    Encrypts a token for secure storage in the database.

    Args:
        token: The plaintext token to encrypt

    Returns:
        Base64-encoded encrypted token
        
    Raises:
        EncryptionError: If token encryption fails
    """
    if not token:
        return token

    try:
        fernet = Fernet(_get_encryption_key())
        encrypted_bytes = fernet.encrypt(token.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encrypt token: {e}")
        # Re-raise the exception to prevent plaintext tokens from being stored.
        raise


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypts a token from database storage.

    Args:
        encrypted_token: The base64-encoded encrypted token

    Returns:
        Decrypted plaintext token
    """
    if not encrypted_token:
        return encrypted_token

    try:
        fernet = Fernet(_get_encryption_key())
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode('utf-8'))
        decrypted_bytes = fernet.decrypt(encrypted_bytes)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to decrypt token: {e}")
        # Return original value if decryption fails (might be unencrypted legacy data)
        return encrypted_token
