"""
API tests for Accounting Insights operations.
"""

import pytest
import logging
import httpx

from .conftest import assert_valid_json_response

logger = logging.getLogger(__name__)

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_accounting_overview(api_client: httpx.AsyncClient):
    """
    Tests that the accounting overview endpoint returns a JSON object with expected financial summary fields.
    """
    logger.info("Testing GET /api/accounting/insights/overview...")
    
    response = await api_client.get("/api/accounting/insights/overview")
    overview = assert_valid_json_response(response, dict)

    # Verify overview contains expected keys
    expected_keys = ["monthly_revenue", "monthly_expenses",
                        "monthly_net_income", "average_rent"]
    for key in expected_keys:
        assert key in overview, f"Overview should contain '{key}' field"
    
    logger.info(f"✅ GET /api/accounting/insights/overview successful, status 200")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_occupancy_rates(api_client: httpx.AsyncClient):
    """
    Tests retrieval of occupancy rates from the accounting insights API.
    """
    logger.info("Testing GET /api/accounting/insights/occupancy...")
    
    response = await api_client.get("/api/accounting/insights/occupancy")
    assert_valid_json_response(response, list)
    
    logger.info(f"✅ GET /api/accounting/insights/occupancy successful, status 200")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_endpoint_returns_404(api_client: httpx.AsyncClient):
    """
    Verifies that a request to a nonexistent accounting API endpoint returns a 404 status code.
    """
    logger.info("Testing invalid accounting endpoint...")
    
    response = await api_client.get("/api/accounting/insights/nonexistent")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    logger.info("✅ Invalid endpoint correctly returned 404")
