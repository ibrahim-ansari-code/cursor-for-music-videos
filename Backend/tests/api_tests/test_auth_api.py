"""
API tests for Authentication endpoints.
"""

import logging  # Standard library
import pytest  # Third-party
import httpx  # Third-party

# Import helper functions and types from conftest.py explicitly
# as they are not fixtures and pytest doesn't auto-inject plain functions
# if conftest is in a different directory (though for same-directory it often works).
# Being explicit is safer.
from .conftest import assert_valid_json_response  # Local application

logger = logging.getLogger(__name__)

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_me_endpoint(api_client: httpx.AsyncClient, current_user_id: str) -> None:
    """
    Tests the /api/auth/me endpoint to verify authenticated user identity.
    """
    logger.info("Testing /api/auth/me endpoint...")

    response = await api_client.get("/api/auth/me")
    data = assert_valid_json_response(response, dict)

    logger.info("✅ /api/auth/me successful")
    assert "id" in data, "/api/auth/me response missing 'id'"
    assert "email" in data, "/api/auth/me response missing 'email'"
    assert data.get('id') == current_user_id
    
    logger.info("   Authenticated user ID matches fixture: %s", data.get('id'))

    # TODO: Add more authentication tests:
    # - Test /api/auth/token with valid credentials (requires a way to get test user password securely or a dedicated fixture)
    # - Test /api/auth/token with invalid credentials
    # - Test /api/auth/register (might need a new, temporary user, data, and cleanup)
    # - Test token refresh mechanisms if not implicitly covered by long-running tests using the client
