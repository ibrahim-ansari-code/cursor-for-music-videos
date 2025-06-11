"""
API tests for Accounting Payments operations.
"""

import pytest
import logging
import httpx
from decimal import Decimal

from .conftest import assert_api_success, assert_valid_json_response

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_get_payments(api_client: httpx.AsyncClient):
    """
    Tests retrieval of all payments via the GET /api/accounting/payments endpoint.
    """
    logger.info("Testing GET /api/accounting/payments...")

    response = await api_client.get("/api/accounting/payments")
    paginated_response = assert_valid_json_response(response, dict)

    assert "items" in paginated_response
    assert "has_more" in paginated_response
    assert isinstance(paginated_response["items"], list)
    
    payments = paginated_response["items"]

    logger.info(
        "✅ GET /api/accounting/payments successful, status 200, returned %d payments",
        len(payments))

@pytest.mark.asyncio
async def test_get_outstanding_payments(api_client: httpx.AsyncClient):
    """
    Tests retrieval of outstanding payments via the accounting API.
    """
    logger.info("Testing GET /api/accounting/payments/outstanding...")
    
    response = await api_client.get("/api/accounting/payments/outstanding")
    outstanding = assert_valid_json_response(response, list)
    
    logger.info(f"✅ GET /api/accounting/payments/outstanding successful, status 200, returned {len(outstanding)} items")

@pytest.mark.slow
@pytest.mark.asyncio
async def test_generate_due_payments(api_client: httpx.AsyncClient, created_lease: dict):
    """
    Tests that the POST /api/accounting/payments/generate-due endpoint successfully generates due payments.
    This test uses a fixture to ensure at least one active lease exists.
    """
    logger.info("Testing POST /api/accounting/payments/generate-due...")

    # Get initial set of payment IDs
    initial_response = await api_client.get("/api/accounting/payments")
    initial_payments = assert_valid_json_response(initial_response, dict)
    initial_ids = {p["id"] for p in initial_payments.get("items", [])}

    # Generate due payments
    response = await api_client.post("/api/accounting/payments/generate-due")
    assert_api_success(response)

    # Verify that the set of payments has grown
    final_response = await api_client.get("/api/accounting/payments")
    final_payments = assert_valid_json_response(final_response, dict)
    final_ids = {p["id"] for p in final_payments.get("items", [])}

    newly_created_ids = final_ids - initial_ids
    
    # This assertion is now robust against race conditions from other tests.
    # Note: It assumes the `created_lease` fixture results in a due payment.
    # If no payment is generated, this might indicate an issue with generation logic
    # or the test environment's date.
    assert len(newly_created_ids) > 0, "Expected at least one new payment to be generated"
    
    logger.info(f"✅ POST /api/accounting/payments/generate-due successful, created {len(newly_created_ids)} new payments.")

@pytest.mark.asyncio
async def test_create_update_delete_payment(api_client: httpx.AsyncClient, created_lease: dict):
    """
    Tests creating, updating, and deleting a payment.
    """
    logger.info("Testing POST/PUT/DELETE for /api/accounting/payments...")
    # Create payment using the lease from the fixture
    payment_data = {
        "lease_id": created_lease["id"],
        "amount": "123.45",
        "payment_date": "2023-01-01T00:00:00Z",
        "payment_method": "Cash",
        "status": "Pending"
    }
    create_resp = await api_client.post("/api/accounting/payments", json=payment_data)
    assert_api_success(create_resp, 201)
    payment = create_resp.json()
    payment_id = payment.get("id")
    assert payment_id, "Payment ID should be present in response"

    # Update payment
    update_data = {"amount": "200.00", "status": "Paid"}
    update_resp = await api_client.put(f"/api/accounting/payments/{payment_id}", json=update_data)
    assert_api_success(update_resp)
    updated = update_resp.json()
    assert Decimal(updated["amount"]) == Decimal("200.00")
    assert updated["status"] == "Paid"

    # Delete payment
    del_resp = await api_client.delete(f"/api/accounting/payments/{payment_id}")
    assert_api_success(del_resp, 204)

@pytest.mark.asyncio
async def test_update_payment_status(api_client: httpx.AsyncClient, created_lease: dict):
    """
    Tests updating the status of a payment.
    """
    logger.info("Testing payment status update...")
    # Create payment first
    payment_data = {
        "lease_id": created_lease["id"],
        "amount": "50.00",
        "payment_date": "2023-01-01T00:00:00Z",
        "payment_method": "Cash",
        "status": "Pending"
    }
    create_resp = await api_client.post("/api/accounting/payments", json=payment_data)
    assert_api_success(create_resp, 201)
    payment = create_resp.json()
    payment_id = payment.get("id")
    assert payment_id, "Payment ID should be present in response"
    
    # Update status
    status_update = {"status": "Paid"}
    update_resp = await api_client.put(f"/api/accounting/payments/{payment_id}", json=status_update)
    assert_api_success(update_resp)
    updated = update_resp.json()
    assert updated["status"] == "Paid"
    
    # Cleanup
    del_resp = await api_client.delete(f"/api/accounting/payments/{payment_id}")
    assert_api_success(del_resp, 204) 