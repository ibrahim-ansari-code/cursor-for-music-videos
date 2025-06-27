"""
API tests for Accounting Expenses operations.
"""

import pytest
import logging
import httpx
from decimal import Decimal

from .conftest import assert_api_success, assert_valid_json_response

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_get_expenses(api_client: httpx.AsyncClient):
    """
    Tests retrieval of expenses from the accounting API.
    """
    logger.info("Testing GET /api/accounting/expenses...")

    response = await api_client.get("/api/accounting/expenses")
    expenses_response = assert_valid_json_response(response, dict)

    # Verify paginated response structure
    assert "items" in expenses_response, "Response should contain 'items' field"
    assert "has_more" in expenses_response, "Response should contain 'has_more' field"
    assert isinstance(
        expenses_response["items"], list), "Items should be a list"
    assert isinstance(
        expenses_response["has_more"], bool), "has_more should be a boolean"

    logger.info(
        "✅ GET /api/accounting/expenses successful, status 200, returned %d expenses",
        len(expenses_response["items"]))


@pytest.mark.asyncio
async def test_get_expenses_with_pagination(api_client: httpx.AsyncClient):
    """
    Tests retrieval of expenses with pagination parameters.
    """
    logger.info("Testing GET /api/accounting/expenses with pagination...")

    # Test with limit and offset
    response = await api_client.get("/api/accounting/expenses", params={"limit": 10, "offset": 0})
    expenses_response = assert_valid_json_response(response, dict)

    # Verify paginated response structure
    assert "items" in expenses_response, "Response should contain 'items' field"
    assert "has_more" in expenses_response, "Response should contain 'has_more' field"
    assert len(expenses_response["items"]
               ) <= 10, "Should return at most 10 items"

    logger.info(
        "✅ GET /api/accounting/expenses with pagination successful, returned %d expenses, has_more: %s",
        len(expenses_response["items"]), expenses_response["has_more"])


@pytest.mark.asyncio
async def test_create_update_delete_expense(api_client: httpx.AsyncClient, created_property_id: int):
    """
    Tests creating, updating, and deleting an expense.
    """
    logger.info("Testing POST/PUT/DELETE for /api/accounting/expenses...")
    expense_data = {
        "property_id": created_property_id,
        "category": "maintenance",
        "subtotal_amount": "50.00",
        "expense_date": "2023-01-01T00:00:00Z",
        "description": "Test expense",
        "taxes": [{"tax_name": "GST", "tax_rate": "5.0"}]
    }
    create_resp = await api_client.post("/api/accounting/expenses", json=expense_data)
    assert_api_success(create_resp, 201)
    expense = create_resp.json()
    expense_id = expense.get("id")
    assert expense_id, "Expense ID should be present in response"

    # Update expense
    update_data = {"description": "Updated expense",
                   "subtotal_amount": "75.00"}
    update_resp = await api_client.put(f"/api/accounting/expenses/{expense_id}", json=update_data)
    assert_api_success(update_resp)
    updated = update_resp.json()
    assert updated["description"] == "Updated expense"
    assert Decimal(updated["subtotal_amount"]) == Decimal("75.00")

    # Delete expense
    del_resp = await api_client.delete(f"/api/accounting/expenses/{expense_id}")
    assert del_resp.status_code in (204, 404)
