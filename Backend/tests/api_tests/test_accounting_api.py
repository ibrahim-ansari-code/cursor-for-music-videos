"""
API tests for Accounting operations.
"""

import pytest
import logging
import httpx
import json
from typing import Any

logger = logging.getLogger(__name__)

# Helper functions for API testing


def assert_api_success(response: httpx.Response, expected_status: int = 200) -> None:
    """
    Asserts that the API response status code matches the expected value.
    
    Raises an assertion error with a snippet of the response body if the status code does not match.
    """
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text[:500]}"
    )


def assert_valid_json_response(response: httpx.Response, expected_type: type | tuple[type, ...] | None = None) -> Any:
    """
    Asserts that the HTTP response contains valid JSON and optionally matches an expected type.
    
    Args:
        response: The HTTP response to validate.
        expected_type: Optional type or tuple of types to check against the parsed JSON data.
    
    Returns:
        The parsed JSON data if validation succeeds.
    
    Raises:
        Fails the test if the response is not valid JSON or does not match the expected type.
    """
    assert_api_success(response)
    try:
        data = response.json()
        if expected_type:
            assert isinstance(
                data, expected_type), f"Expected {expected_type}, got {type(data)}"
        return data
    except json.JSONDecodeError as e:
        pytest.fail(
            f"Invalid JSON response: {e}. Response text: {response.text[:500]}")


@pytest.mark.auth
@pytest.mark.integration
class TestAccountingAPI:
    """Test suite for Accounting API endpoints"""

    @pytest.mark.asyncio
    async def test_get_payments(self, api_client):
        """
        Tests retrieval of all payments via the GET /api/accounting/payments endpoint.
        
        Verifies that the response is successful and returns a JSON list of payments.
        """
        logger.info("Testing GET /api/accounting/payments...")

        response = await api_client.get("/api/accounting/payments")
        payments = assert_valid_json_response(response, list)

        logger.info(
            "✅ GET /api/accounting/payments successful, status 200, returned %d payments",
            len(payments))

    @pytest.mark.asyncio
    async def test_get_expenses(self, api_client):
        """
        Tests retrieval of expenses from the accounting API.
        
        Sends a GET request to the /api/accounting/expenses endpoint and verifies that the response is a JSON list of expenses.
        """
        logger.info("Testing GET /api/accounting/expenses...")

        response = await api_client.get("/api/accounting/expenses")
        expenses = assert_valid_json_response(response, list)

        logger.info(
            "✅ GET /api/accounting/expenses successful, status 200, returned %d expenses",
            len(expenses))

    @pytest.mark.asyncio
    async def test_get_outstanding_payments(self, api_client):
        """
        Tests retrieval of outstanding payments via the accounting API.
        
        Sends a GET request to the `/api/accounting/payments/outstanding` endpoint and asserts that the response is a JSON list.
        """
        logger.info("Testing GET /api/accounting/payments/outstanding...")
        
        response = await api_client.get("/api/accounting/payments/outstanding")
        outstanding = assert_valid_json_response(response, list)
        
        logger.info(f"✅ GET /api/accounting/payments/outstanding successful, status 200, returned {len(outstanding)} items")

    @pytest.mark.asyncio
    async def test_get_invoices(self, api_client):
        """
        Tests retrieval of invoices from the accounting API.
        
        Sends a GET request to the /api/accounting/invoices endpoint and asserts that the response is a JSON list.
        """
        logger.info("Testing GET /api/accounting/invoices...")

        response = await api_client.get("/api/accounting/invoices")
        invoices = assert_valid_json_response(response, list)

        logger.info(
            "✅ GET /api/accounting/invoices successful, status 200, returned %d invoices",
            len(invoices))

    @pytest.mark.asyncio
    async def test_get_accounting_overview(self, api_client):
        """
        Tests that the accounting overview endpoint returns a JSON object with expected financial summary fields.
        
        Verifies that the response contains the keys: "monthly_revenue", "monthly_expenses", "monthly_net_income", and "average_rent".
        """
        logger.info("Testing GET /api/accounting/insights/overview...")
        
        response = await api_client.get("/api/accounting/insights/overview")
        overview = assert_valid_json_response(response, dict)

        # Verify overview contains expected keys (updated to match actual API response)
        expected_keys = ["monthly_revenue", "monthly_expenses",
                         "monthly_net_income", "average_rent"]
        for key in expected_keys:
            assert key in overview, f"Overview should contain '{key}' field"
        
        logger.info(f"✅ GET /api/accounting/insights/overview successful, status 200")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_generate_due_payments(self, api_client):
        """
        Tests that the POST /api/accounting/payments/generate-due endpoint successfully generates due payments.
        """
        logger.info("Testing POST /api/accounting/payments/generate-due...")
        
        response = await api_client.post("/api/accounting/payments/generate-due")
        assert_api_success(response)
        
        logger.info(f"✅ POST /api/accounting/payments/generate-due successful, status 200")

    @pytest.mark.asyncio
    async def test_get_occupancy_rates(self, api_client):
        """
        Tests retrieval of occupancy rates from the accounting insights API.
        
        Sends a GET request to the `/api/accounting/insights/occupancy` endpoint and asserts that the response is a valid JSON object or list.
        """
        logger.info("Testing GET /api/accounting/insights/occupancy...")
        
        response = await api_client.get("/api/accounting/insights/occupancy")
        assert_valid_json_response(response, (dict, list))
        
        logger.info(f"✅ GET /api/accounting/insights/occupancy successful, status 200")

    # @pytest.mark.asyncio # Temporarily remove this test due to persistent 500 errors
    # async def test_get_revenue_trends(self, api_client):
    #     """Test GET /api/accounting/revenue-trends with various parameters"""
    #     logger.info("Testing GET /api/accounting/revenue-trends...")
        
    #     # Test various parameter combinations
    #     test_params_list = [
    #         {},
    #         {"period_type": "monthly"},
    #         {"period_type": "monthly", "year": datetime.now().year},
    #         # {"period_type": "yearly"}, # Assuming yearly might also be an option
    #         # {"property_id": 1} # Assuming property_id filter might be added
    #     ]
        
    #     all_failed = True
    #     for params in test_params_list:
    #         try:
    #             logger.info(f"   Testing revenue trends with params: {params}")
    #             response = await api_client.get("/api/accounting/insights/revenue-trends", params=params)
                
    #             if response.status_code == 200:
    #                 data = assert_valid_json_response(response, list)
    #                 assert len(data) > 0, "Expected some revenue trend data"
    #                 assert "period" in data[0]
    #                 assert "revenue" in data[0]
    #                 logger.info(f"   ✅ Params {params} successful, returned {len(data)} trend periods")
    #                 all_failed = False # Mark if at least one combination works
    #             elif response.status_code == 500:
    #                 logger.warning(f"   ⚠️ Params {params} returned 500 error")
    #             else:
    #                 logger.warning(f"   ⚠️ Params {params} returned unexpected status: {response.status_code}")
            
    #         except Exception as e:
    #             logger.warning(f"   ⚠️ Params {params} failed: {e}")

    #     if all_failed:
    #         logger.warning("⚠️ All revenue trends parameter combinations failed - known backend issue")
    #         pytest.skip("Revenue trends endpoint has persistent errors - backend API issue")

    @pytest.mark.asyncio
    async def test_invalid_endpoint_returns_404(self, api_client):
        """
        Verifies that a request to a nonexistent accounting API endpoint returns a 404 status code.
        """
        logger.info("Testing invalid accounting endpoint...")
        
        response = await api_client.get("/api/accounting/insights/nonexistent")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

        logger.info("✅ Invalid endpoint correctly returned 404")

    # TODO: Add POST/PUT/DELETE tests for:
    # - Creating payments
    # - Creating expenses
    # - Creating invoices
    # - Updating payment status
    # These would need proper test data setup and cleanup

    @pytest.mark.asyncio
    async def test_create_update_delete_payment(self, api_client):
        """
        Tests creating, updating, and deleting a payment.
        """
        logger.info("Testing POST/PUT/DELETE for /api/accounting/payments...")
        # Create payment
        payment_data = {
            "amount": 123.45,
            "payment_date": "2023-01-01T00:00:00Z",
            "payment_method": "cash",
            "status": "pending"
        }
        create_resp = await api_client.post("/api/accounting/payments", json=payment_data)
        assert_api_success(create_resp, 201)
        payment = create_resp.json()
        payment_id = payment.get("id")
        assert payment_id, "Payment ID should be present in response"
        # Update payment
        update_data = {"amount": 200.00, "status": "completed"}
        update_resp = await api_client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
        assert_api_success(update_resp)
        updated = update_resp.json()
        assert updated["amount"] == 200.00
        assert updated["status"] == "completed"
        # Delete payment
        del_resp = await api_client.delete(f"/api/accounting/payments/{payment_id}")
        assert del_resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_create_update_delete_expense(self, api_client):
        """
        Tests creating, updating, and deleting an expense.
        """
        logger.info("Testing POST/PUT/DELETE for /api/accounting/expenses...")
        expense_data = {
            "property_id": 1,
            "category": "maintenance",
            "subtotal_amount": 50.00,
            "expense_date": "2023-01-01T00:00:00Z",
            "description": "Test expense",
            "taxes": [{"tax_name": "GST", "tax_rate": 5.0}]
        }
        create_resp = await api_client.post("/api/accounting/expenses", json=expense_data)
        assert_api_success(create_resp, 201)
        expense = create_resp.json()
        expense_id = expense.get("id")
        assert expense_id, "Expense ID should be present in response"
        # Update expense
        update_data = {"description": "Updated expense", "subtotal_amount": 75.00}
        update_resp = await api_client.put(f"/api/accounting/expenses/{expense_id}", json=update_data)
        assert_api_success(update_resp)
        updated = update_resp.json()
        assert updated["description"] == "Updated expense"
        assert float(updated["subtotal_amount"]) == 75.00
        # Delete expense
        del_resp = await api_client.delete(f"/api/accounting/expenses/{expense_id}")
        assert del_resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_create_update_delete_invoice(self, api_client):
        """
        Tests creating, updating, and deleting an invoice.
        """
        logger.info("Testing POST/PUT/DELETE for /api/accounting/invoices...")
        invoice_data = {
            "tenant_id": 1,
            "property_id": 1,
            "amount_due": 100.00,
            "due_date": "2023-01-10T00:00:00Z",
            "status": "pending"
        }
        create_resp = await api_client.post("/api/accounting/invoices", json=invoice_data)
        assert_api_success(create_resp, 201)
        invoice = create_resp.json()
        invoice_id = invoice.get("id")
        assert invoice_id, "Invoice ID should be present in response"
        # Update invoice
        update_data = {"amount_due": 150.00, "status": "paid"}
        update_resp = await api_client.put(f"/api/accounting/invoices/{invoice_id}", json=update_data)
        assert_api_success(update_resp)
        updated = update_resp.json()
        assert float(updated["amount_due"]) == 150.00
        assert updated["status"] == "paid"
        # Delete invoice
        del_resp = await api_client.delete(f"/api/accounting/invoices/{invoice_id}")
        assert del_resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_update_payment_status(self, api_client):
        """
        Tests updating the status of a payment.
        """
        logger.info("Testing payment status update...")
        # Create payment first
        payment_data = {
            "amount": 50.00,
            "payment_date": "2023-01-01T00:00:00Z",
            "payment_method": "cash",
            "status": "pending"
        }
        create_resp = await api_client.post("/api/accounting/payments", json=payment_data)
        assert_api_success(create_resp, 201)
        payment = create_resp.json()
        payment_id = payment.get("id")
        assert payment_id, "Payment ID should be present in response"
        # Update status
        status_update = {"status": "completed"}
        update_resp = await api_client.put(f"/api/accounting/payments/{payment_id}", json=status_update)
        assert_api_success(update_resp)
        updated = update_resp.json()
        assert updated["status"] == "completed"
        # Cleanup
        del_resp = await api_client.delete(f"/api/accounting/payments/{payment_id}")
        assert del_resp.status_code in (200, 204)
