"""
API tests for generic behaviors and utility endpoints.
"""

import pytest
import logging
from datetime import datetime

# Import helper functions from conftest.py explicitly for clarity

logger = logging.getLogger(__name__)


@pytest.mark.integration  # Most generic tests are integration-level
class TestGenericAPIBehaviors:
    """Test suite for generic API behaviors and utility endpoints."""

    @pytest.mark.asyncio
    # No auth needed, but api_client can be used
    async def test_health_check(self, api_client):
        """
        Verifies that the API health check endpoint is reachable and returns a 200 OK status.
        """
        logger.info("Testing API health check...")

        # Use a basic endpoint to test API availability
        response = await api_client.get("/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        logger.info(
            f"✅ API health check successful, status {response.status_code}")

    @pytest.mark.asyncio
    async def test_datetime_validation_in_response(self, api_client):
        """
        Verifies that datetime fields in the API response are properly formatted in ISO 8601.
        
        Sends a GET request to the payments endpoint and checks that any present datetime fields
        ('created_at', 'updated_at', 'payment_date', 'due_date') in the first payment object
        are valid ISO 8601 strings. Fails the test if any field is not properly formatted.
        """
        logger.info("Testing datetime format validation...")

        # Use an endpoint that returns datetime fields
        response = await api_client.get("/api/accounting/payments")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        payments = response.json()
        if payments and len(payments) > 0:
            payment = payments[0]
            # Check for common datetime fields
            datetime_fields = ['created_at',
                               'updated_at', 'payment_date', 'due_date']
            for field in datetime_fields:
                if field in payment:
                    # Validate ISO format
                    try:
                        datetime.fromisoformat(
                            payment[field].replace('Z', '+00:00'))
                        logger.info(
                            f"   ✅ {field} is properly formatted: {payment[field]}")
                    except ValueError:
                        pytest.fail(
                            f"Invalid datetime format for {field}: {payment[field]}")

        logger.info(f"✅ Datetime validation successful")

    @pytest.mark.asyncio
    async def test_datetime_query_param_edge_cases(self, api_client):
        """
        Verifies that the API accepts various valid datetime formats as query parameters without returning a 400 Bad Request error.
        
        Tests multiple datetime representations for `start_date` and `end_date` parameters on the payments endpoint to ensure proper handling of edge cases.
        """
        logger.info("Testing datetime query parameter edge cases...")

        # Test various datetime formats in query params
        test_cases = [
            ("start_date", "2024-01-01"),
            ("end_date", "2024-12-31"),
            ("start_date", "2024-01-01T00:00:00Z"),
        ]

        for param_name, param_value in test_cases:
            response = await api_client.get("/api/accounting/payments", params={param_name: param_value})
            # Should not return 400 for valid datetime formats
            assert response.status_code != 400, f"Valid datetime {param_value} should not return 400"
            logger.info(f"   ✅ {param_name}={param_value} handled correctly")

        logger.info(f"✅ Datetime query parameter edge cases successful")

    @pytest.mark.asyncio
    async def test_timezone_string_handling_in_query(self, api_client):
        """
        Verifies that the API correctly handles timezone-aware datetime strings in query parameters.
        
        Sends GET requests to the payments endpoint with various timezone-aware datetime strings as the `start_date` parameter, asserting that the API responds with either 200 OK or 400 Bad Request to indicate acceptance or rejection of each format.
        """
        logger.info("Testing timezone handling in query parameters...")

        # Test timezone-aware datetime strings
        timezone_cases = [
            "2024-01-01T00:00:00+00:00",  # UTC
            "2024-01-01T00:00:00-05:00",  # EST
            "2024-01-01T00:00:00+09:00",  # JST
        ]

        for tz_datetime in timezone_cases:
            response = await api_client.get("/api/accounting/payments", params={"start_date": tz_datetime})
            # Should handle timezone-aware datetime strings gracefully
            assert response.status_code in [
                200, 400], f"Timezone datetime should return 200 or 400, got {response.status_code}"
            if response.status_code == 400:
                logger.info(
                    f"   ⚠️ {tz_datetime} rejected (might be expected)")
            else:
                logger.info(f"   ✅ {tz_datetime} accepted")

        logger.info(f"✅ Timezone handling test completed")

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, api_client):
        """
        Verifies that sending an unsupported HTTP method to an endpoint returns 405 or 404.
        
        Sends a PATCH request to the payments endpoint and asserts that the response status code indicates the method is not allowed or the endpoint is not found.
        """
        logger.info("Testing HTTP method not allowed...")

        # Test unsupported methods on a known endpoint
        endpoint = "/api/accounting/payments"

        # Test unsupported PATCH method using the public API client method
        patch_response = await api_client.patch(endpoint)

        # Should return 405 Method Not Allowed or 404 (depends on framework routing)
        assert patch_response.status_code in [
            405, 404], f"PATCH should return 405 or 404, got {patch_response.status_code}"

        logger.info(
            f"✅ Method not allowed test successful, status {patch_response.status_code}")

    @pytest.mark.asyncio
    async def test_malformed_json_payload(self, api_client):
        """
        Tests that the API returns a 400 or 422 status code when receiving a malformed JSON payload in a POST request to the payments endpoint.
        """
        logger.info("Testing malformed JSON payload handling...")

        # Send malformed JSON to a POST endpoint using a custom request method
        malformed_json = '{"invalid": json, missing quotes}'

        # Use the public method to send raw malformed JSON with custom content
        response = await api_client.request(
            method="POST",
            endpoint="/api/accounting/payments",
            content=malformed_json,
            content_type="application/json"
        )

        # Should return 400 or 422 for malformed JSON (422 is also acceptable for validation errors)
        assert response.status_code in [
            400, 422], f"Malformed JSON should return 400 or 422, got {response.status_code}"

        logger.info(
            f"✅ Malformed JSON handling successful, status {response.status_code}")

    @pytest.mark.asyncio
    async def test_nonexistent_endpoint_returns_404(self, api_client):
        """
        Verifies that a request to a nonexistent API endpoint returns a 404 status code.
        """
        logger.info("Testing nonexistent endpoint...")

        response = await api_client.get("/api/nonexistent/endpoint/12345")
        assert response.status_code == 404, f"Nonexistent endpoint should return 404, got {response.status_code}"

        logger.info(f"✅ Nonexistent endpoint correctly returned 404")

    # TODO: Add tests for other generic behaviors:
    # - Security headers (X-Content-Type-Options, X-Frame-Options, etc.) if implemented
    # - CORS headers if applicable and testable from this client
    # - Rate limiting if implemented (might be hard to test reliably without specific setup)
    # - Large payload handling (e.g., exceeding server limits)
    # - Specific error code responses for common issues (e.g., 401 for bad token, 403 for forbidden)
