"""
Shared authentication utilities for test suite.

This module provides authentication utilities that can be shared across
all test types (unit, integration, api) without circular dependencies.
Extracted from test_auth_helper.py to avoid circular imports.
"""

import asyncio
import getpass
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv
from supabase import Client, create_client

logger = logging.getLogger(__name__)

# Load environment variables from the root .env file
dotenv_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '../../.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f"Loaded .env from {dotenv_path} in shared_auth_utils.py")
elif load_dotenv():  # Try default .env in CWD as fallback
    logger.info(
        "Loaded .env from current working directory for shared_auth_utils.py")
else:
    logger.error(
        f"CRITICAL: Root .env file not found by shared_auth_utils.py. Tried {dotenv_path} and CWD. SUPABASE_URL/KEY will be missing.")

PRIMARY_TEST_USER_TYPE = "LANDLORD"
CREDENTIALS_FILE_NAME = ".test_credentials.json"
ACCESS_TOKEN_FILE_NAME = ".test_jwt_token"


class AuthTestManager:
    """Helper class for managing test authentication. Renamed to avoid pytest collection."""

    def __init__(self) -> None:
        """
        Initializes the AuthTestManager by loading Supabase and backend configuration, determining the primary test user email, and preparing authentication and HTTP clients.
        
        Raises:
            ValueError: If required environment variables or the primary test user email cannot be determined.
        """
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.backend_url = "http://localhost:8000"  # Hardcoded

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.credentials_file_path = os.path.join(
            self.script_dir, CREDENTIALS_FILE_NAME)
        self.access_token_file_path = os.path.join(
            self.script_dir, ACCESS_TOKEN_FILE_NAME)

        # Determine the primary user email
        self.primary_user_email = os.getenv("TEST_USER_EMAIL")
        if not self.primary_user_email:
            try:
                self.primary_user_email = self._get_primary_user_email_from_creds()
            except ValueError:
                if sys.stdin.isatty():  # Interactive shell
                    logger.warning(
                        "No TEST_USER_EMAIL in env or creds file.")
                    self.primary_user_email = input(
                        "Please enter the primary test user email: ")
                else:
                    raise  # Re-raise the ValueError if not in an interactive shell

        if not self.primary_user_email:
            raise ValueError(
                "Primary test user email could not be determined. "
                "Set TEST_USER_EMAIL environment variable, "
                "or run in an interactive shell to be prompted.")

        if not self.supabase_url or not self.supabase_anon_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")

        self.supabase: Client = create_client(
        self.supabase_url, self.supabase_anon_key)
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        """
        Enters the asynchronous context manager for the AuthTestManager instance.
        
        Returns:
            The AuthTestManager instance itself for use within an async context.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Closes the asynchronous HTTP client when exiting the context manager.
        """
        await self.http_client.aclose()

    def _save_credentials(self, creds: Dict[str, Any]) -> None:
        """
        Saves user credentials to a file, excluding the password, and writes the access token to a separate file with restricted permissions.
        
        If an access token is present, it is saved to a standalone file with permissions set to 600 for security.
        """
        try:
            # Create a copy of creds to avoid modifying the original dict in memory
            creds_to_save = creds.copy()
            # Remove password before saving to file for security
            if "password" in creds_to_save:
                del creds_to_save["password"]
                logger.info(
                    "Password field removed from credentials before saving to file.")

            with open(self.credentials_file_path, 'w', encoding='utf-8') as f:
                json.dump(creds_to_save, f, indent=2)
            logger.info(
                f"Saved credentials (without password) to {self.credentials_file_path}")

            if creds.get("access_token"):
                try:
                    # Open the file with flags to create, truncate, and write-only, setting permissions to 600
                    fd = os.open(self.access_token_file_path,
                                 os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                    with os.fdopen(fd, 'w', encoding='utf-8') as f:
                        f.write(creds["access_token"])
                    logger.info(
                        f"Access token also saved to {self.access_token_file_path}")
                except IOError as e:
                    logger.error(
                        f"Failed to save token to {self.access_token_file_path}: {e}")

        except Exception as e:
            logger.error(f"Error saving credentials: {str(e)}")

    def _load_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Loads stored credentials from the credentials file.
        
        Returns:
            A dictionary containing the credentials if the file exists and is valid, or None if the file is missing or an error occurs during loading.
        """
        if not os.path.exists(self.credentials_file_path):
            return None
        try:
            with open(self.credentials_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(
                f"Error loading credentials from {self.credentials_file_path}: {str(e)}")
            return None

    def _get_primary_user_email_from_creds(self) -> str:
        """
        Retrieves the primary test user email from the credentials file.
        
        Raises:
            ValueError: If the credentials file is missing, invalid, or does not contain the test user email.
        
        Returns:
            The primary test user email as a string.
        """
        creds = self._load_credentials()
        if not creds:
            raise ValueError(
                f"Could not load credentials from {self.credentials_file_path}. Please ensure it exists and is valid.")
        email = creds.get("TEST_USER_EMAIL")
        if not email:
            raise ValueError(
                f"TEST_USER_EMAIL not found in {self.credentials_file_path}")
        return email

    async def get_or_refresh_jwt(
        self,
        prompt_for_password_if_needed: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Obtains a JWT for the primary test user by refreshing the session or signing in.
        
        Attempts to refresh the session using a stored refresh token. If refreshing fails or no refresh token is available, tries to sign in with the user's password, which may be sourced from credentials, environment variables, or interactively prompted if allowed. On successful authentication, saves updated credentials and tokens.
        
        Args:
            prompt_for_password_if_needed: If True, prompts for the user's password interactively if not found in credentials or environment variables.
        
        Returns:
            A dictionary containing updated credentials and tokens if authentication succeeds, or None if all attempts fail.
        """
        email = self.primary_user_email
        creds = self._load_credentials()

        if creds and creds.get("email") != email:
            logger.info(
                f"Loaded credentials for {creds.get('email')}, but requesting for {email}. Discarding.")
            creds = None

        # 1. Try to use existing refresh token
        if creds and creds.get("refresh_token"):
            logger.info(
                f"Attempting to refresh token for {email} using saved refresh token...")
            try:
                session_response = await asyncio.to_thread(
                    self.supabase.auth.refresh_session,
                    refresh_token=creds["refresh_token"],
                )
                if session_response.session and session_response.user:
                    logger.info(f"Token refreshed successfully for {email}.")
                    
                    user_id = str(session_response.user.id)
                    
                    updated_creds = {
                        "email": email,
                        "TEST_USER_EMAIL": email,
                        "access_token": session_response.session.access_token,
                        "refresh_token": session_response.session.refresh_token,
                        "user_id": user_id,
                        "expires_at": session_response.session.expires_at
                    }
                    self._save_credentials(updated_creds)
                    return updated_creds
                else:
                    logger.warning(
                        f"Refresh token for {email} did not return a valid session/user. Will attempt sign-in.")
            except Exception as e:
                logger.warning(
                    f"Error refreshing token for {email}: {str(e)}. Will attempt sign-in.")

        # 2. Try to sign in
        logger.info(f"Attempting to sign in as {email}...")
        password_to_use = creds.get("password") if creds else None

        # Prefer environment variable for CI/non-interactive
        if not password_to_use:
            password_to_use = os.environ.get("TEST_USER_PASSWORD")

        # Only prompt if allowed and in interactive mode
        if not password_to_use and prompt_for_password_if_needed and sys.stdin.isatty():
            try:
                password_to_use = getpass.getpass(
                    f"Password for {email} (will be saved to {self.credentials_file_path}): ")
            except Exception as e:
                logger.warning(
                    f"Could not read password interactively for {email}: {e}. This is fine if running non-interactively and password is in creds file.")

        if not password_to_use:
            logger.error(
                f"No password available for {email} (not in {self.credentials_file_path} and not provided/prompted). Cannot sign in.")
            return None

        try:
            # Create credentials with explicit string types
            email_str: str = str(email) if email is not None else ""
            password_str: str = str(password_to_use)

            # Wrap the synchronous Supabase call in asyncio.to_thread
            session_response = await asyncio.to_thread(
                self.supabase.auth.sign_in_with_password,
                {"email": email_str, "password": password_str}
            )
            if session_response.session and session_response.user:
                logger.info(f"Signed in successfully as {email}.")
                user_id = str(session_response.user.id)

                new_creds = {
                    "email": email,
                    "TEST_USER_EMAIL": email,
                    "access_token": session_response.session.access_token,
                    "refresh_token": session_response.session.refresh_token,
                    "user_id": user_id,
                    "expires_at": session_response.session.expires_at
                }
                self._save_credentials(new_creds)
                return new_creds
            else:
                logger.error(
                    f"Sign-in failed for {email}: No session or user returned by Supabase.")
                return None
        except Exception as e:
            logger.error(f"Error signing in as {email}: {str(e)}")
            return None

    async def verify_token_with_supabase(self, token: Optional[str]) -> bool:
        """
        Checks whether the provided access token is valid by querying Supabase for the associated user.
        
        Args:
            token: The access token to verify.
        
        Returns:
            True if the token is valid and corresponds to a Supabase user, False otherwise.
        """
        if not token:
            return False
        logger.info(f"Verifying token with Supabase: {token[:30]}...")
        try:
            user_response = await asyncio.to_thread(self.supabase.auth.get_user, token)
            if user_response and user_response.user:
                logger.info(
                    f"Token VERIFIED for Supabase user: {user_response.user.email} (ID: {user_response.user.id})")
                return True
            else:
                logger.warning(
                    f"Token verification FAILED. Supabase get_user returned no user. Token: {token[:30]}...")
                return False
        except Exception as e:
            logger.warning(
                f"Token verification FAILED with error: {e}. Token: {token[:30]}...")
            return False


async def get_primary_user_jwt(prompt_for_password: bool = False) -> Optional[str]:
    """
    Obtains a valid JWT access token for the primary test user, refreshing or prompting for credentials as needed.
    
    Attempts to retrieve or refresh the JWT using stored credentials. If necessary and allowed, prompts for the user's password. Verifies the token with Supabase before returning it. If verification fails, clears invalid tokens from the credentials file.
    
    Args:
        prompt_for_password: If True, prompts interactively for the user's password if required.
    
    Returns:
        The valid JWT access token as a string, or None if unable to obtain or verify the token.
    """
    async with AuthTestManager() as auth_manager:
        credentials = await auth_manager.get_or_refresh_jwt(
            prompt_for_password_if_needed=prompt_for_password
        )
        if credentials and credentials.get("access_token"):
            access_token = credentials["access_token"]
            if await auth_manager.verify_token_with_supabase(access_token):
                return access_token
            else:
                logger.error(
                    f"Obtained token for {auth_manager.primary_user_email} but it FAILED Supabase verification.")
                if os.path.exists(auth_manager.credentials_file_path):
                    loaded_creds = auth_manager._load_credentials()
                    if loaded_creds:
                        loaded_creds.pop("access_token", None)
                        loaded_creds.pop("refresh_token", None)
                        loaded_creds.pop("expires_at", None)
                        auth_manager._save_credentials(loaded_creds)
                        logger.info(
                            "Cleared invalid tokens from .test_credentials.json")
        return None


# Alias for test scripts
get_test_jwt = get_primary_user_jwt