"""
Shared pytest fixtures for API tests.

This conftest.py provides fixtures specifically for API endpoint testing.
Basic Python path setup and environment loading is handled by the parent conftest.py
"""

import os
import pytest
import httpx
from typing import AsyncGenerator
from unittest.mock import patch, AsyncMock

# Import shared utilities
from tests.shared_fixtures import (
    assert_api_success,
    assert_api_error,
    assert_valid_json_response,
)

# Re-export for backward compatibility
__all__ = [
    'assert_api_success',
    'assert_api_error',
    'assert_valid_json_response',
    'api_client',
    'shared_auth_token',
    'current_user_id',
    'mock_recaptcha_success',
    'mock_recaptcha_bypass',
]

# Test configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = httpx.Timeout(10.0, connect=5.0)  # Shorter timeout for API tests


@pytest.fixture(scope="session")
async def shared_auth_token() -> str:
    """Get shared auth token for API tests."""
    # Import here to avoid circular dependencies
    from Backend.tests.shared_auth_utils import get_primary_user_jwt
    
    token = await get_primary_user_jwt(prompt_for_password=False)
    if not token:
        pytest.exit("Failed to get auth token for API tests", returncode=1)
    return token


@pytest.fixture(scope="function")
async def current_user_id(shared_auth_token: str) -> str:
    """Get current user ID from auth endpoint."""
    headers = {"Authorization": f"Bearer {shared_auth_token}"}
    
    async with httpx.AsyncClient(
        base_url=BASE_URL, 
        headers=headers, 
        timeout=API_TIMEOUT
    ) as client:
        response = await client.get("/api/auth/me")
        assert_api_success(response)
        
        user_data = response.json()
        user_id = user_data.get("id")
        if not user_id:
            pytest.fail("User ID not found in /api/auth/me response")
        return user_id


@pytest.fixture(scope="function")
async def api_client(shared_auth_token: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Provide an authenticated httpx client for API tests.
    
    This client includes:
    - Base URL configuration
    - Authentication headers
    - Appropriate timeout settings
    - JSON content type
    """
    headers = {
        "Authorization": f"Bearer {shared_auth_token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers=headers,
        timeout=API_TIMEOUT,
        follow_redirects=True
    ) as client:
        yield client


@pytest.fixture
def mock_recaptcha_success():
    """
    Mock reCAPTCHA verification to always succeed with high score.

    Use this fixture when you want reCAPTCHA protection enabled but
    always passing verification for testing protected endpoints.
    """
    mock_response = {
        "success": True,
        "score": 0.9,
        "action": None,  # Will be set by the verification function
        "challenge_ts": "2024-01-01T12:00:00Z",
        "hostname": "localhost"
    }

    with patch('Backend.utils.recaptcha._verify_recaptcha', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = mock_response
        yield mock_verify


@pytest.fixture
def mock_recaptcha_bypass():
    """
    Mock reCAPTCHA to be bypassed by setting RECAPTCHA_SECRET_KEY to empty.

    Use this fixture when you want to completely bypass reCAPTCHA
    verification for testing endpoints.
    """
    with patch('Backend.utils.recaptcha.settings') as mock_settings:
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = ""  # This will cause bypass
        yield mock_settings


@pytest.fixture(autouse=True)
def auto_mock_recaptcha_for_api_tests(mock_recaptcha_success):
    """
    Automatically mock reCAPTCHA for all API tests.

    This ensures API tests can run even when reCAPTCHA is enabled,
    by automatically mocking successful verification.
    """
    pass


# API test specific markers
pytestmark = [
    pytest.mark.asyncio,  # All API tests are async
]