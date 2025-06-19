"""
API tests for Accounting Invoices operations.
"""

import pytest
import logging
import httpx

from .conftest import assert_valid_json_response

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_get_invoices(api_client: httpx.AsyncClient):
    """
    Tests retrieval of invoices from the accounting API.
    """
    logger.info("Testing GET /api/accounting/invoices...")

    response = await api_client.get("/api/accounting/invoices")
    invoices = assert_valid_json_response(response, list)

    logger.info(
        "✅ GET /api/accounting/invoices successful, status 200, returned %d invoices",
        len(invoices))

# @pytest.mark.asyncio
# async def test_create_update_delete_invoice(api_client: httpx.AsyncClient, created_lease: dict):
#     """
#     Tests creating, updating, and deleting an invoice.
#     """
#     logger.info("Testing POST/PUT/DELETE for /api/accounting/invoices...")
#     invoice_data = {
#         "tenant_id": created_lease["tenant_id"],
#         "property_id": created_lease["property_id"],
#         "invoice_number": f"INV-{int(time.time())}",
#         "amount": "100.00",
#         "description": "Test Invoice",
#         "issue_date": "2023-01-01T00:00:00Z",
#         "due_date": "2023-01-10T00:00:00Z",
#         "status": "Pending"
#     }
#     create_resp = await api_client.post("/api/accounting/invoices", json=invoice_data)
#     assert_api_success(create_resp, 201)
#     invoice = create_resp.json()
#     invoice_id = invoice.get("id")
#     assert invoice_id, "Invoice ID should be present in response"
    
#     # Update invoice
#     update_data = {"amount": "150.00", "status": "Paid"}
#     update_resp = await api_client.put(f"/api/accounting/invoices/{invoice_id}", json=update_data)
#     assert_api_success(update_resp)
#     updated = update_resp.json()
#     assert Decimal(updated["amount"]) == Decimal("150.00")
#     assert updated["status"] == "Paid"
    
#     # Delete invoice
#     del_resp = await api_client.delete(f"/api/accounting/invoices/{invoice_id}")
#     assert_api_success(del_resp, 204) 