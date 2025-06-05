"""
API tests for Dashboard operations.
"""

import pytest
import logging

# Import helper functions from conftest.py explicitly for clarity
from .conftest import assert_valid_json_response, APITestClient

logger = logging.getLogger(__name__)

@pytest.mark.auth
@pytest.mark.integration
class TestDashboardAPI:
    """Test suite for Dashboard API endpoints."""

    @pytest.mark.asyncio
    async def test_dashboard_get_operations(self, api_client: APITestClient) -> None:
        """Test GET /api/dashboard endpoint."""
        logger.info("Testing GET /api/dashboard...")
        
        # api_client fixture from conftest.py handles authentication and initial checks.
        response = await api_client.get("/api/dashboard") 
        data = assert_valid_json_response(response, dict)
        
        logger.info("✅ GET /api/dashboard successful. Received sections: %s", ', '.join(data.keys()))
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