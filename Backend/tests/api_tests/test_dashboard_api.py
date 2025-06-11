"""
API tests for Dashboard operations.
"""

import pytest
import logging
import httpx

from .conftest import assert_valid_json_response

logger = logging.getLogger(__name__)


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_dashboard_get_operations(api_client: httpx.AsyncClient) -> None:
    """
    Tests that the GET /api/dashboard endpoint returns a valid JSON response with required sections.
    
    Asserts that the response is a dictionary containing the keys: "summary", "occupancy", "revenue", and "payments_due".
    """
    logger.info("Testing GET /api/dashboard...")

    response = await api_client.get("/api/dashboard")
    data = assert_valid_json_response(response, dict)

    logger.info(
        "✅ GET /api/dashboard successful. Received sections: %s", ', '.join(data.keys()))
    assert "summary" in data, "Dashboard response missing 'summary' key"
    assert "occupancy" in data, "Dashboard response missing 'occupancy' key"
    assert "revenue" in data, "Dashboard response missing 'revenue' key"
    assert "payments_due" in data, "Dashboard response missing 'payments_due' key"

    # TODO: Add tests for /api/dashboard with query parameters if applicable (e.g., property_id, time_period)
    # Example:
    # async def test_dashboard_with_property_filter(self, api_client, test_property_id):
    #     logger.info(f"Testing GET /api/dashboard?property_id={test_property_id}...")
    #     response = await api_client.get(f"/api/dashboard?property_id={test_property_id}")
    #     data = assert_valid_json_response(response, dict)
    #     logger.info("✅ GET /api/dashboard with property filter successful")
    #     # Add assertions specific to filtered data

    # TODO: Add more dashboard tests:
    # - Test dashboard with time period filters
    # - Test dashboard data accuracy (if test data is available)
    # - Test dashboard performance metrics
    # - Test dashboard with invalid filters
    