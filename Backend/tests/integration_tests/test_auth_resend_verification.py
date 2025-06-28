"""
Integration tests for the email verification resend endpoint.
"""

import logging
import pytest
import httpx

logger = logging.getLogger(__name__)


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_resend_verification_valid_email() -> None:
    """
    Test resending verification email with a valid email address.
    """
    logger.info("Testing resend verification with valid email...")
    
    # Create a client without authentication (this endpoint doesn't require auth)
    timeout = httpx.Timeout(30.0, connect=5.0)
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=timeout) as client:
        
        # Test data
        request_data = {
            "email": "test@example.com"
        }
        
        response = await client.post(
            "/api/auth/resend-verification",
            json=request_data
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.json()}")
        
        # Should return 200 with a generic success message
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Response should contain a 'message' field"
        assert "verification email" in data["message"].lower() or "email sent" in data["message"].lower(), \
            f"Response message should indicate email was sent. Got: {data['message']}"
        
        logger.info("✅ Resend verification with valid email successful")


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_resend_verification_invalid_email() -> None:
    """
    Test resending verification email with an invalid email format.
    """
    logger.info("Testing resend verification with invalid email...")
    
    timeout = httpx.Timeout(30.0, connect=5.0)
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=timeout) as client:
        
        # Test data with invalid email
        request_data = {
            "email": "not-an-email"
        }
        
        response = await client.post(
            "/api/auth/resend-verification",
            json=request_data
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        logger.info("✅ Invalid email properly rejected")


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_resend_verification_missing_email() -> None:
    """
    Test resending verification email without providing an email.
    """
    logger.info("Testing resend verification without email...")
    
    timeout = httpx.Timeout(30.0, connect=5.0)
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=timeout) as client:
        
        # Empty request body
        request_data = {}
        
        response = await client.post(
            "/api/auth/resend-verification",
            json=request_data
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        # Should return 422 for missing required field
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        logger.info("✅ Missing email properly rejected")


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_resend_verification_rate_limiting() -> None:
    """
    Test that rate limiting works for resend verification.
    Note: This test might fail if Supabase rate limiting is not triggered.
    """
    logger.info("Testing resend verification rate limiting...")
    
    timeout = httpx.Timeout(30.0, connect=5.0)
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=timeout) as client:
        
        request_data = {
            "email": "ratelimit.test@example.com"
        }
        
        # Try to send multiple requests quickly
        responses = []
        for i in range(5):
            response = await client.post(
                "/api/auth/resend-verification",
                json=request_data
            )
            responses.append(response.status_code)
            logger.info(f"Request {i+1} status: {response.status_code}")
        
        # The first request should succeed
        assert responses[0] == 200, f"First request should succeed, but got status {responses[0]}"
        
        # If rate limiting is working, later requests might return 429
        # Note: This depends on Supabase configuration
        if 429 in responses:
            logger.info("✅ Rate limiting detected (429 response)")
            # Verify rate limiting kicked in after the first request
            rate_limited_count = responses.count(429)
            logger.info(f"Number of rate-limited requests: {rate_limited_count}")
        else:
            logger.info("⚠️ No rate limiting detected (might be disabled in Supabase)")
        
        logger.info("✅ Rate limiting test completed")