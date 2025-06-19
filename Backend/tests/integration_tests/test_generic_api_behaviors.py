"""
API tests for generic behaviors and utility endpoints.
"""

import logging
from datetime import datetime

import pytest
import httpx

logger = logging.getLogger(__name__)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_check(api_client: httpx.AsyncClient) -> None:
    """
    Verifies that the API health check endpoint is reachable and returns a 200 OK status.
    """
    logger.info("Testing API health check...")

    response = await api_client.get("/api/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    logger.info(
        f"✅ API health check successful, status {response.status_code}")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_datetime_validation_in_response(api_client: httpx.AsyncClient) -> None:
    """
    Verifies that datetime fields in the API response are properly formatted in ISO 8601.
    """
    logger.info("Testing datetime format validation...")

    response = await api_client.get("/api/accounting/payments")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    paginated_response = response.json()
    payments = paginated_response.get("items", [])
    
    if payments:
        payment = payments[0]
        datetime_fields = ['created_at',
                            'updated_at', 'payment_date', 'due_date']
        for field in datetime_fields:
            field_value = payment.get(field)
            if field_value:
                try:
                    datetime.fromisoformat(
                        field_value.replace('Z', '+00:00'))
                    logger.info(
                        f"   ✅ {field} is properly formatted: {field_value}")
                except (ValueError, TypeError):
                    pytest.fail(
                        f"Invalid datetime format for {field}: {field_value}")

    logger.info(f"✅ Datetime validation successful")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_datetime_query_param_edge_cases(api_client: httpx.AsyncClient) -> None:
    """
    Verifies that the API accepts various valid datetime formats as query parameters.
    """
    logger.info("Testing datetime query parameter edge cases...")

    test_cases = [
        ("start_date", "2024-01-01"),
        ("end_date", "2024-12-31"),
        ("start_date", "2024-01-01T00:00:00Z"),
    ]

    for param_name, param_value in test_cases:
        response = await api_client.get("/api/accounting/payments", params={param_name: param_value})
        assert response.status_code != 400, f"Valid datetime {param_value} should not return 400"
        logger.info(f"   ✅ {param_name}={param_value} handled correctly")

    logger.info(f"✅ Datetime query parameter edge cases successful")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_timezone_string_handling_in_query(api_client: httpx.AsyncClient) -> None:
    """
    Verifies that the API correctly handles timezone-aware datetime strings in query parameters.
    """
    logger.info("Testing timezone handling in query parameters...")

    timezone_cases = [
        "2024-01-01T00:00:00+00:00",
        "2024-01-01T00:00:00-05:00",
        "2024-01-01T00:00:00+09:00",
    ]

    for tz_datetime in timezone_cases:
        response = await api_client.get("/api/accounting/payments", params={"start_date": tz_datetime})
        assert response.status_code in [
            200, 400], f"Timezone datetime should return 200 or 400, got {response.status_code}"
        if response.status_code == 400:
            logger.info(
                f"   ⚠️ {tz_datetime} rejected (might be expected)")
        else:
            logger.info(f"   ✅ {tz_datetime} accepted")

    logger.info(f"✅ Timezone handling test completed")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_method_not_allowed(api_client: httpx.AsyncClient) -> None:
    """
    Verifies that sending an unsupported HTTP method to an endpoint returns 405 or 404.
    """
    logger.info("Testing HTTP method not allowed...")

    endpoint = "/api/accounting/payments"
    patch_response = await api_client.patch(endpoint)

    assert patch_response.status_code in [
        405, 404], f"PATCH should return 405 or 404, got {patch_response.status_code}"

    logger.info(
        f"✅ Method not allowed test successful, status {patch_response.status_code}")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_malformed_json_payload(api_client: httpx.AsyncClient) -> None:
    """
    Tests that the API returns a 400 or 422 status code when receiving a malformed JSON payload.
    """
    logger.info("Testing malformed JSON payload handling...")

    malformed_json = '{"invalid": json, missing quotes}'
    headers = {"Content-Type": "application/json"}
    # Need to build request manually to send malformed content
    request = api_client.build_request("POST", "/api/accounting/payments", content=malformed_json, headers=headers)
    response = await api_client.send(request)
    
    assert response.status_code in [
        400, 422], f"Malformed JSON should return 400 or 422, got {response.status_code}"

    logger.info(
        f"✅ Malformed JSON handling successful, status {response.status_code}")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_nonexistent_endpoint_returns_404(api_client: httpx.AsyncClient) -> None:
    """
    Verifies that a request to a nonexistent API endpoint returns a 404 status code.
    """
    logger.info("Testing nonexistent endpoint...")

    response = await api_client.get("/api/nonexistent/endpoint/12345")
    assert response.status_code == 404, f"Nonexistent endpoint should return 404, got {response.status_code}"

    logger.info(f"✅ Nonexistent endpoint correctly returned 404")
