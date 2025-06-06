"""
API tests for Accounting operations.
"""

import pytest
import logging
import httpx

logger = logging.getLogger(__name__)

# Helper functions for API testing


def assert_api_success(response: httpx.Response, expected_status: int = 200) -> None:
    """Helper to assert API response success"""
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text[:500]}"
    )


def assert_valid_json_response(response: httpx.Response, expected_type=None):
    """Helper to assert valid JSON response"""
    assert_api_success(response)
    try:
        data = response.json()
        if expected_type:
            assert isinstance(
                data, expected_type), f"Expected {expected_type}, got {type(data)}"
        return data
    except Exception as e:
        pytest.fail(
            f"Invalid JSON response: {e}. Response text: {response.text[:500]}")


@pytest.mark.auth
@pytest.mark.integration
class TestAccountingAPI:
    """Test suite for Accounting API endpoints"""

    @pytest.mark.asyncio
    async def test_get_payments(self, api_client):
        """Test GET /api/accounting/payments"""
        logger.info("Testing GET /api/accounting/payments...")

        response = await api_client.get("/api/accounting/payments")
        payments = assert_valid_json_response(response, list)

        logger.info(
            "✅ GET /api/accounting/payments successful, status 200, returned %d payments",
            len(payments))

    @pytest.mark.asyncio
    async def test_get_expenses(self, api_client):
        """Test GET /api/accounting/expenses"""
        logger.info("Testing GET /api/accounting/expenses...")

        response = await api_client.get("/api/accounting/expenses")
        expenses = assert_valid_json_response(response, list)

        logger.info(
            "✅ GET /api/accounting/expenses successful, status 200, returned %d expenses",
            len(expenses))

    @pytest.mark.asyncio
    async def test_get_outstanding_payments(self, api_client):
        """Test GET /api/accounting/outstanding-payments"""
        logger.info("Testing GET /api/accounting/outstanding-payments...")

        response = await api_client.get("/api/accounting/outstanding-payments")
        outstanding = assert_valid_json_response(response, list)

        logger.info(
            "✅ GET /api/accounting/outstanding-payments successful, status 200, returned %d items",
            len(outstanding))

    @pytest.mark.asyncio
    async def test_get_invoices(self, api_client):
        """Test GET /api/accounting/invoices"""
        logger.info("Testing GET /api/accounting/invoices...")

        response = await api_client.get("/api/accounting/invoices")
        invoices = assert_valid_json_response(response, list)

        logger.info(
            "✅ GET /api/accounting/invoices successful, status 200, returned %d invoices",
            len(invoices))

    @pytest.mark.asyncio
    async def test_get_accounting_overview(self, api_client):
        """Test GET /api/accounting/overview"""
        logger.info("Testing GET /api/accounting/overview...")

        response = await api_client.get("/api/accounting/overview")
        overview = assert_valid_json_response(response, dict)

        # Verify overview contains expected keys (updated to match actual API response)
        expected_keys = ["monthly_revenue", "monthly_expenses",
                         "monthly_net_income", "average_rent"]
        for key in expected_keys:
            assert key in overview, f"Overview should contain '{key}' field"

        logger.info("✅ GET /api/accounting/overview successful, status 200")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_generate_due_payments(self, api_client):
        """Test POST /api/accounting/generate-due-payments"""
        logger.info("Testing POST /api/accounting/generate-due-payments...")

        response = await api_client.post("/api/accounting/generate-due-payments")
        assert_api_success(response)

        logger.info(
            "✅ POST /api/accounting/generate-due-payments successful, status 200")

    @pytest.mark.asyncio
    async def test_get_occupancy_rates(self, api_client):
        """Test GET /api/accounting/occupancy"""
        logger.info("Testing GET /api/accounting/occupancy...")

        response = await api_client.get("/api/accounting/occupancy")
        occupancy = assert_valid_json_response(response, (dict, list))

        logger.info("✅ GET /api/accounting/occupancy successful, status 200")

    @pytest.mark.asyncio
    async def test_invalid_endpoint_returns_404(self, api_client):
        """Test that invalid accounting endpoints return 404"""
        logger.info("Testing invalid accounting endpoint...")

        response = await api_client.get("/api/accounting/nonexistent")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

        logger.info("✅ Invalid endpoint correctly returned 404")

    # TODO: Add POST/PUT/DELETE tests for:
    # - Creating payments
    # - Creating expenses
    # - Creating invoices
    # - Updating payment status
    # These would need proper test data setup and cleanup
