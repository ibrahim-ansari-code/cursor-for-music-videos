"""
API tests for Authentication endpoints.
"""

import logging  # Standard library

import pytest  # Third-party

# Import helper functions and types from conftest.py explicitly
# as they are not fixtures and pytest doesn't auto-inject plain functions
# if conftest is in a different directory (though for same-directory it often works).
# Being explicit is safer.
from .conftest import assert_valid_json_response, APITestClient  # Local application

logger = logging.getLogger(__name__)

@pytest.mark.auth
@pytest.mark.integration
class TestAuthAPI:
    """Test suite for Authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_auth_me_endpoint(self, api_client: APITestClient) -> None:
        """Test /api/auth/me endpoint with JWT"""
        logger.info("Testing /api/auth/me endpoint...")
        
        # The api_client fixture in conftest.py handles token acquisition 
        # and skips the test if no token is available or if the initial /api/auth/me check fails.
        # Thus, we can assume api_client is authenticated if the test reaches this point.

        response = await api_client.get("/api/auth/me")
        data = assert_valid_json_response(response, dict)
        
        logger.info("✅ /api/auth/me successful")
        assert "id" in data, "/api/auth/me response missing 'id'"
        assert "email" in data, "/api/auth/me response missing 'email'"
        
        if api_client.current_user: # current_user is set in the api_client fixture
            assert data.get('email') == api_client.current_user.get('email')
            assert data.get('id') == api_client.current_user.get('id')
            logger.info("   Authenticated as: %s", api_client.current_user.get('email'))
            logger.info("   User ID: %s", api_client.current_user.get('id'))
        else:
            # This case should ideally not be hit if the fixture's initial check passes
            logger.warning("   api_client.current_user was not set by the fixture during /auth/me call by the fixture itself.")
            logger.info("   Authenticated user details from current test call: id=%s, email=%s", data.get('id'), data.get('email'))

    # TODO: Add more authentication tests:
    # - Test /api/auth/token with valid credentials (requires a way to get test user password securely or a dedicated fixture)
    # - Test /api/auth/token with invalid credentials
    # - Test /api/auth/register (might need a new, temporary user, data, and cleanup)
    # - Test token refresh mechanisms if not implicitly covered by long-running tests using the client
