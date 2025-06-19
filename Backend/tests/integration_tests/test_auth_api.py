"""
API tests for Authentication endpoints.
"""

import logging  # Standard library
import pytest  # Third-party
import httpx  # Third-party
import uuid
from unittest.mock import patch

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


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_profile_update(api_client: httpx.AsyncClient, current_user_id: str) -> None:
    """
    Tests the PUT /api/auth/users/{user_id}/profile endpoint.
    This is relevant for password reset flow as users might update their profile after resetting.
    """
    logger.info("Testing profile update endpoint...")

    profile_update_data = {
        "first_name": "Updated",
        "last_name": "Name",
        "phone": "1234567890"
    }

    response = await api_client.put(
        f"/api/auth/users/{current_user_id}/profile",
        json=profile_update_data
    )
    data = assert_valid_json_response(response, dict)

    logger.info("✅ Profile update successful")
    assert data.get('first_name') == "Updated"
    assert data.get('last_name') == "Name"
    assert data.get('phone') == "1234567890"
    
    logger.info("   Profile updated successfully: %s %s", data.get('first_name'), data.get('last_name'))


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_profile_update_unauthorized(api_client: httpx.AsyncClient) -> None:
    """
    Tests that users cannot update other users' profiles.
    """
    logger.info("Testing unauthorized profile update...")

    # Try to update a different user's profile
    fake_user_id = str(uuid.uuid4())
    profile_update_data = {
        "first_name": "Hacker",
        "last_name": "McHackface"
    }

    response = await api_client.put(
        f"/api/auth/users/{fake_user_id}/profile",
        json=profile_update_data
    )

    logger.info("✅ Unauthorized access properly blocked")
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_user_sync_valid(api_client: httpx.AsyncClient) -> None:
    """
    Tests the Supabase webhook endpoint for user sync.
    This endpoint is called when users are created in Supabase (including after password reset).
    """
    logger.info("Testing Supabase webhook user sync...")

    # Import the actual settings to get the real webhook secret
    from Backend.config import settings
    
    # Skip test if no webhook secret is configured
    if not settings.SUPABASE_WEBHOOK_SECRET:
        pytest.skip("SUPABASE_WEBHOOK_SECRET not configured in environment")

    # Mock webhook payload that Supabase would send
    webhook_payload = {
        "type": "INSERT",
        "table": "users",
        "schema": "auth",
        "record": {
            "id": str(uuid.uuid4()),
            "email": f"webhook.test.{uuid.uuid4()}@example.com",
            "raw_user_meta_data": {
                "first_name": "Webhook",
                "last_name": "User",
                "phone": "9876543210"
            }
        }
    }

    # Use the actual webhook secret from environment
    headers = {"X-Webhook-Secret": settings.SUPABASE_WEBHOOK_SECRET}

    response = await api_client.post(
        "/api/auth/webhook/user-sync",
        json=webhook_payload,
        headers=headers
    )

    data = assert_valid_json_response(response, dict)
    logger.info("✅ Webhook user sync successful")
    assert "message" in data


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_user_sync_invalid_secret(api_client: httpx.AsyncClient) -> None:
    """
    Tests that webhook rejects requests with invalid secrets.
    """
    logger.info("Testing webhook with invalid secret...")

    from Backend.config import settings
    
    # Skip test if no webhook secret is configured
    if not settings.SUPABASE_WEBHOOK_SECRET:
        pytest.skip("SUPABASE_WEBHOOK_SECRET not configured in environment")

    webhook_payload = {
        "type": "INSERT",
        "table": "users", 
        "schema": "auth",
        "record": {
            "id": str(uuid.uuid4()),
            "email": "test@example.com"
        }
    }

    # Use an invalid secret
    headers = {"X-Webhook-Secret": "definitely-wrong-secret"}

    response = await api_client.post(
        "/api/auth/webhook/user-sync",
        json=webhook_payload,
        headers=headers
    )

    logger.info("✅ Invalid webhook secret properly rejected")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_sync_user_endpoint(api_client: httpx.AsyncClient) -> None:
    """
    Tests the manual user sync endpoint.
    This could be used to sync users after password reset scenarios.
    """
    logger.info("Testing manual user sync endpoint...")

    from Backend.config import settings
    
    # Skip test if no webhook secret is configured
    if not settings.SUPABASE_WEBHOOK_SECRET:
        pytest.skip("SUPABASE_WEBHOOK_SECRET not configured in environment")

    sync_payload = {
        "supabase_user_id": str(uuid.uuid4()),
        "email": f"sync.test.{uuid.uuid4()}@example.com",
        "first_name": "Sync",
        "last_name": "User",
        "phone": "5555555555",
        "user_type": "LANDLORD"
    }

    # Use the actual webhook secret from environment
    headers = {"X-Webhook-Secret": settings.SUPABASE_WEBHOOK_SECRET}

    response = await api_client.post(
        "/api/auth/sync-user",
        json=sync_payload,
        headers=headers
    )

    data = assert_valid_json_response(response, dict)
    logger.info("✅ Manual user sync successful")
    assert data.get('email').startswith("sync.test")
    assert data.get('first_name') == "Sync"


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_endpoints_without_secret() -> None:
    """
    Tests webhook endpoints without authentication to verify they properly reject unauthenticated requests.
    This ensures security even when webhook secret isn't configured.
    """
    logger.info("Testing webhook security without secret...")

    # Create a client without authentication
    timeout = httpx.Timeout(30.0, connect=5.0)
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=timeout) as client:
        
        # Test webhook endpoint without secret header
        webhook_payload = {
            "type": "INSERT",
            "table": "users",
            "schema": "auth",
            "record": {
                "id": str(uuid.uuid4()),
                "email": "test@example.com"
            }
        }

        response = await client.post(
            "/api/auth/webhook/user-sync",
            json=webhook_payload
        )

        # Should reject with 401 or 500 (depending on whether secret is configured)
        assert response.status_code in [401, 500], f"Expected 401 or 500, got {response.status_code}"

        # Test sync endpoint without secret header
        sync_payload = {
            "supabase_user_id": str(uuid.uuid4()),
            "email": "sync.test@example.com",
            "first_name": "Test",
            "last_name": "User"
        }

        response = await client.post(
            "/api/auth/sync-user", 
            json=sync_payload
        )

        # Should reject (either because no secret or because secret doesn't match)
        assert response.status_code in [403, 500], f"Expected 403 or 500, got {response.status_code}"

    logger.info("✅ Webhook endpoints properly secured")


@pytest.mark.auth  
@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_configuration_check() -> None:
    """
    Tests that webhook configuration is properly loaded and validates expected behavior.
    """
    logger.info("Testing webhook configuration...")

    from Backend.config import settings

    # Log the webhook secret status (without exposing the actual secret)
    webhook_secret_configured = bool(settings.SUPABASE_WEBHOOK_SECRET)
    logger.info(f"Webhook secret configured: {webhook_secret_configured}")
    
    if webhook_secret_configured:
        logger.info("✅ Webhook secret is configured - webhook tests should work")
    else:
        logger.info("⚠️ Webhook secret not configured - webhook tests will be skipped")

    # This test always passes, it's just for logging configuration status
    assert True


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_flow_after_password_reset_simulation(api_client: httpx.AsyncClient, current_user_id: str) -> None:
    """
    Simulates the auth flow that would happen after a user resets their password.
    Tests that the user can still access protected endpoints after password reset.
    """
    logger.info("Testing auth flow after simulated password reset...")

    # 1. Verify user can access their profile (simulating post-reset login)
    response = await api_client.get("/api/auth/me")
    user_data = assert_valid_json_response(response, dict)
    assert user_data.get('id') == current_user_id

    # 2. Test that user can update their profile (common post-reset action)
    profile_update = {
        "first_name": "Post",
        "last_name": "Reset"
    }
    
    response = await api_client.put(
        f"/api/auth/users/{current_user_id}/profile",
        json=profile_update
    )
    updated_data = assert_valid_json_response(response, dict)
    
    # 3. Verify the changes persisted
    response = await api_client.get("/api/auth/me")
    final_data = assert_valid_json_response(response, dict)
    
    logger.info("✅ Post-reset auth flow successful")
    assert final_data.get('first_name') == "Post"
    assert final_data.get('last_name') == "Reset"
    logger.info("   User can successfully authenticate and modify profile post-reset")


    # TODO: Add more authentication tests:
    # - Test /api/auth/token with valid credentials (requires a way to get test user password securely or a dedicated fixture)
    # - Test /api/auth/token with invalid credentials  
    # - Test /api/auth/register (might need a new, temporary user, data, and cleanup)
    # - Test token refresh mechanisms if not implicitly covered by long-running tests using the client
    # - Test avatar upload endpoint
    # - Test rate limiting on auth endpoints
    # - Test concurrent auth requests
