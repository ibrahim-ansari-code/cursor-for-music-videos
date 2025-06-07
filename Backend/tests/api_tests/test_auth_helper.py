"""
Test Authentication Helper

This module provides utilities for managing authentication tokens for the test suite,
focusing on a primary test user. It handles Supabase Auth interactions and
synchronization with the local backend.
"""

import asyncio
import getpass  # For securely getting password input
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
# Assumes this script is in Backend/tests/api_tests/, so ../../../.env is the root .env
dotenv_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '../../../.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f"Loaded .env from {dotenv_path} in test_auth_helper.py")
elif os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../.env')):
    # Fallback if script moved one level up by mistake in path calculation
    dotenv_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), '../../.env')
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(
        f"Loaded .env from {dotenv_path} in test_auth_helper.py (fallback path)")
elif os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env')):
    # Fallback if script moved two levels up
    dotenv_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), '../.env')
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(
        f"Loaded .env from {dotenv_path} in test_auth_helper.py (fallback path 2)")
elif load_dotenv():  # Try default .env in CWD as last resort
    logger.info(
        "Loaded .env from current working directory for test_auth_helper.py")
else:
    logger.error(
        f"CRITICAL: Root .env file not found by test_auth_helper.py. Tried {dotenv_path} and CWD. SUPABASE_URL/KEY will be missing.")

PRIMARY_TEST_USER_TYPE = "LANDLORD"
CREDENTIALS_FILE_NAME = ".test_credentials.json"
ACCESS_TOKEN_FILE_NAME = ".test_jwt_token"


class AuthTestManager:
    """Helper class for managing test authentication. Renamed to avoid pytest collection."""

    def __init__(self):
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
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()

    def _save_credentials(self, creds: Dict[str, Any]):
        """Saves credentials to file and updates the standalone access token file."""
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
        """Loads credentials from file."""
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
        """Loads the primary test user email from the credentials file."""
        creds = self._load_credentials()
        if not creds:
            raise ValueError(
                f"Could not load credentials from {self.credentials_file_path}. Please ensure it exists and is valid.")
        email = creds.get("TEST_USER_EMAIL")
        if not email:
            raise ValueError(
                f"TEST_USER_EMAIL not found in {self.credentials_file_path}")
        return email

    async def _sync_user_to_backend_if_needed(
        self, supabase_user_id: str, email: str,
        first_name: str = "Test", last_name: str = "User05",  # Consistent with primary user
        user_type: str = PRIMARY_TEST_USER_TYPE
    ) -> bool:
        """Syncs Supabase user to backend if not already present or to update."""
        logger.info(
            f"Attempting to sync Supabase user {email} (ID: {supabase_user_id}) to backend...")
        try:
            sync_data = {
                "supabase_user_id": str(supabase_user_id),
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "user_type": user_type,
                "phone": "0000000000"  # Placeholder
            }
            response = await self.http_client.post(
                f"{self.backend_url}/api/auth/sync-user",
                json=sync_data,
                headers={"Content-Type": "application/json"}
            )
            # Check if status code is in the 2xx range for success
            if 200 <= response.status_code < 300:
                logger.info(
                    f"Successfully synced user {email} to backend. Status: {response.status_code}")
                return True
            # Handle 409 Conflict if user already exists and sync endpoint doesn't update
            elif response.status_code == 409:
                logger.info(
                    f"User {email} already exists in backend (Conflict 409). Sync considered successful.")
                return True
            else:
                logger.warning(
                    f"Failed to sync user {email}. Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error syncing user {email} to backend: {str(e)}")
            return False

    async def get_or_refresh_jwt(
        self,
        prompt_for_password_if_needed: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Gets a JWT for the primary test user, prioritizing refresh, then sign-in."""
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
                session_response = self.supabase.auth.refresh_session(
                    refresh_token=creds["refresh_token"])
                if session_response.session and session_response.user:
                    logger.info(f"Token refreshed successfully for {email}.")
                    updated_creds = {
                        "email": email,
                        "TEST_USER_EMAIL": email,
                        "access_token": session_response.session.access_token,
                        "refresh_token": session_response.session.refresh_token,
                        "user_id": str(session_response.user.id),
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

                # Ensure email is not None before syncing
                if email:
                    await self._sync_user_to_backend_if_needed(user_id, email, user_type=PRIMARY_TEST_USER_TYPE)
                else:
                    logger.error("Cannot sync user to backend, email is None.")
                    return None

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
        """Verifies if the given access token is valid with Supabase."""
        if not token:
            return False
        logger.info(f"Verifying token with Supabase: {token[:30]}...")
        try:
            user_response = self.supabase.auth.get_user(token)
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
    """Gets or refreshes JWT for the primary test user."""
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

if __name__ == "__main__":
    # Configure logging for CLI usage only
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    async def main_cli():
        auth_manager_instance = AuthTestManager()
        print(
            f"Attempting to get/refresh JWT for primary test user: {auth_manager_instance.primary_user_email}")
        token = await get_primary_user_jwt(prompt_for_password=True)

        if token:
            print(
                f"\n✅ Successfully obtained/refreshed JWT for {auth_manager_instance.primary_user_email}")
            print(f"   Access Token Preview: {token[:50]}...")

            auth_mngr = AuthTestManager()  # For path construction
            print(
                f"   Credentials (incl. refresh token, and password if entered) saved to: {auth_mngr.credentials_file_path}")
            print(
                f"   Access token also saved to: {auth_mngr.access_token_file_path}")

            os.environ["TEST_USER_JWT"] = token
            print("   Set TEST_USER_JWT environment variable for this session.")
            print(
                "\n💡 You can now run the test suites (e.g., python Backend/tests/test_comprehensive_api.py)")
        else:
            print(
                f"\n❌ Failed to obtain/refresh JWT for {auth_manager_instance.primary_user_email}")
            print(f"   Review logs above for details.")
            print(f"   Ensure Supabase URL/Anon Key are correct in root .env file.")
            print(
                f"   Ensure user {auth_manager_instance.primary_user_email} exists, is confirmed, and you have the correct password.")

    asyncio.run(main_cli())
