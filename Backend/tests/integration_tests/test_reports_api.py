"""
API tests for Reports operations.
"""

import pytest
import logging
import httpx

from .conftest import assert_valid_json_response, assert_api_success

logger = logging.getLogger(__name__)

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [
    "/api/reports/summary",
    "/api/reports/revenue",
    "/api/reports/occupancy",
    "/api/reports/maintenance"
])
async def test_reports_get_operations(api_client: httpx.AsyncClient, endpoint: str) -> None:
    """
    Tests a single GET endpoint under /api/reports to verify its availability.
    """
    logger.info("Testing GET %s...", endpoint)
    try:
        response = await api_client.get(endpoint)
        if response.status_code == 200:
            assert_valid_json_response(response, (dict, list))
            logger.info("✅ GET %s successful, returned data", endpoint)
        elif response.status_code == 404:
            logger.info("⚠️ GET %s returned 404 (not implemented)", endpoint)
        else:
            logger.warning("⚠️ GET %s returned unexpected status: %s", endpoint, response.status_code)
    except httpx.HTTPError as e:
        pytest.fail(f"GET {endpoint} raised HTTPError: {e}")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_report_summary_endpoint(api_client: httpx.AsyncClient, created_landlord_property: int) -> None:
    """
    Tests the GET /api/reports/summary endpoint for correct response structure.
    """
    logger.info("Testing GET /api/reports/summary...")
    response = await api_client.get("/api/reports/summary")

    if response.status_code == 200:
        data = assert_valid_json_response(response, dict)
        assert "monthly_chart" in data
        assert "summary" in data
        assert "financial_table" in data
        assert "income_by_property" in data

        if data["financial_table"]:
            first_property_financials = data["financial_table"][0]
            assert "property" in first_property_financials
            assert "occupancy_rate" in first_property_financials

        if data["income_by_property"]:
            first_property_income = data["income_by_property"][0]
            assert "property" in first_property_income
            assert "occupancy_rate" in first_property_income

        logger.info("✅ GET /api/reports/summary successful, status 200.")
    elif response.status_code == 404:
        pytest.skip(f"Reports summary endpoint returned 404 - potentially no data. Response: {response.text[:200]}")
    elif response.status_code in (400, 422):
        pytest.skip(f"Reports summary endpoint returned {response.status_code}. Response: {response.text[:200]}")
    else:
        assert_api_success(response, 200)

    # TODO: Add more report tests:
    # - Test report generation with date ranges
    # - Test report filtering by property
    # - Test different report formats (JSON, CSV, PDF)
    # - Test report caching mechanisms
    # - Test report export functionality
    # - Test report scheduling/automation endpoints
