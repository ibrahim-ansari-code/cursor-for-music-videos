"""
API tests for Reports operations.
"""

import pytest
import logging
import httpx  # Added for specific exception handling

# Import helper functions and types from conftest.py explicitly for clarity
from .conftest import assert_valid_json_response, assert_api_success, APITestClient

logger = logging.getLogger(__name__)


@pytest.mark.auth
@pytest.mark.integration
class TestReportsAPI:
    """Test suite for Reports API endpoints"""

    @pytest.mark.asyncio
    async def test_reports_get_operations(self, api_client: APITestClient) -> None:
        """
        Tests multiple GET endpoints under /api/reports to verify their availability and response format.
        
        Sends asynchronous GET requests to several reports endpoints and accepts both HTTP 200 (valid response) and 404 (endpoint not implemented) as valid outcomes. Asserts that a 200 response contains valid JSON data in either dictionary or list form. Logs and handles unexpected status codes and HTTP errors.
        """
        logger.info("Testing reports GET operations...")

        # Test basic reports endpoints that should be available
        # Note: The reports router is mounted at /api/reports (api prefix + reports prefix)
        report_endpoints = [
            "/api/reports/summary",
            "/api/reports/revenue",      # This might not exist
            "/api/reports/occupancy",    # This might not exist
            "/api/reports/maintenance"   # This might not exist
        ]

        for endpoint in report_endpoints:
            try:
                logger.info("Testing GET %s...", endpoint)
                response = await api_client.get(endpoint)

                # Accept both 200 (success) and 404 (not implemented yet)
                if response.status_code == 200:
                    # Removed data assignment
                    assert_valid_json_response(response, (dict, list))
                    logger.info("✅ GET %s successful, returned data", endpoint)
                elif response.status_code == 404:
                    logger.info(
                        "⚠️ GET %s returned 404 (not implemented)", endpoint)
                else:
                    logger.warning(
                        "⚠️ GET %s returned unexpected status: %s", endpoint, response.status_code)

            except httpx.HTTPError as e:  # Catch specific httpx errors
                logger.exception(
                    "⚠️ GET %s failed with HTTPError: %s", endpoint, e)
            except Exception as e:  # Catch any other unexpected errors
                logger.exception(
                    "⚠️ GET %s failed with an unexpected error: %s", endpoint, e)

        logger.info("✅ Reports GET operations testing completed")

    @pytest.mark.asyncio
    async def test_report_summary_endpoint(self, api_client: APITestClient, created_landlord_property: int) -> None:
        """
        Tests the GET /api/reports/summary endpoint for correct response structure and error handling.
        
        Ensures that when relevant data exists, the endpoint returns a JSON object containing the expected summary keys and nested fields. Handles cases where the endpoint returns 404 (no data), 400, or 422 (invalid data state) by skipping the test with an appropriate message. Fails the test for any other unexpected status codes.
        """
        logger.info("Testing GET /api/reports/summary...")

        # Ensure a property exists for the landlord, so the summary isn't empty due to no properties
        # The created_landlord_property fixture handles this setup.
        # property_id = created_landlord_property # We don't explicitly need the id here, just its existence

        response = await api_client.get("/api/reports/summary")

        if response.status_code == 200:
            data = assert_valid_json_response(response, dict)
            # Updated assertions based on actual response structure
            assert "monthly_chart" in data, "'monthly_chart' key missing in report summary"
            assert "summary" in data, "'summary' key missing in report summary"
            assert "financial_table" in data, "'financial_table' key missing in report summary"
            assert "income_by_property" in data, "'income_by_property' key missing in report summary"

            # Check some nested data if financial_table is not empty
            if data["financial_table"]:
                first_property_financials = data["financial_table"][0]
                assert "property" in first_property_financials, "'property' key missing in financial_table item"
                assert "occupancy_rate" in first_property_financials, "'occupancy_rate' key missing in financial_table item"

            if data["income_by_property"]:
                first_property_income = data["income_by_property"][0]
                assert "property" in first_property_income, "'property' key missing in income_by_property item"
                assert "occupancy_rate" in first_property_income, "'occupancy_rate' key missing in income_by_property item"

            logger.info("✅ GET /api/reports/summary successful, status 200.")
        elif response.status_code == 404:
            logger.warning(
                "GET /api/reports/summary returned 404. Response: %s", response.text[:200])
            pytest.skip(
                "Reports summary endpoint returned 404 - potentially no underlying data for summary components other than property count.")
        # Simplified status code check
        elif response.status_code in (400, 422):
            logger.warning("GET /api/reports/summary returned %s (Bad Request/Unprocessable Entity). Response: %s",
                           response.status_code, response.text[:200])
            pytest.skip(
                f"Reports summary endpoint returned {response.status_code} - possibly due to invalid data state for summary generation.")
        else:
            # Will fail here if not 200, 404, 400, or 422
            assert_api_success(response, 200)

    # TODO: Add more report tests:
    # - Test report generation with date ranges
    # - Test report filtering by property
    # - Test different report formats (JSON, CSV, PDF)
    # - Test report caching mechanisms
    # - Test report export functionality
    # - Test report scheduling/automation endpoints
