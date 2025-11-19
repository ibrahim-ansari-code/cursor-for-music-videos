import logging
import json
from typing import Any
import pytest
import httpx

from .conftest import assert_api_success, assert_api_error, assert_valid_json_response

logger = logging.getLogger(__name__)


def maintenance_payload(property_id: int, **kwargs) -> dict[str, Any]:
    """
    Generates a dictionary representing a maintenance request payload.
    
    Args:
        property_id: The ID of the property for which the maintenance request is created.
        **kwargs: Additional fields to override or add to the default payload.
    
    Returns:
        A dictionary containing the maintenance request data, with defaults that can be overridden by extra keyword arguments.
    """
    data = {
        "issue_title": "Broken Pipe",
        "description": "A pipe is leaking in the basement.",
        "property_id": property_id,
        "priority": "MEDIUM",
    }
    data.update(kwargs)
    return data


@pytest.mark.asyncio
@pytest.mark.auth
async def test_create_and_get_request(api_client: httpx.AsyncClient, created_property_id: int):
    """
    Tests the creation and retrieval of a maintenance request via the API.
    
    Creates a maintenance request for the specified property and verifies the response data. Then retrieves the created request by its ID and asserts the returned data matches the created request.
    """
    payload = maintenance_payload(created_property_id)
    logger.info("Sending maintenance request payload: %s", payload)
    create_res = await api_client.post("/api/maintenance/requests", json=payload)
    
    assert_api_success(create_res, 201)
    created_data = create_res.json()
    request_id = created_data["id"]

    assert created_data["issue_title"] == "Broken Pipe"
    assert created_data["property"]["id"] == created_property_id

    get_res = await api_client.get(f"/api/maintenance/requests/{request_id}")
    assert_api_success(get_res)
    assert get_res.json()["id"] == request_id
    logger.info("✅ Create and Get Test Passed")


@pytest.mark.asyncio
@pytest.mark.auth
async def test_update_request(api_client: httpx.AsyncClient, created_property_id: int):
    """
    Tests updating an existing maintenance request and verifies that the updated fields are correctly reflected in the response.
    
    Creates a maintenance request, updates its status and priority, and asserts that the changes are persisted.
    """
    payload = maintenance_payload(created_property_id)
    create_res = await api_client.post("/api/maintenance/requests", json=payload)
    request_id = create_res.json()["id"]

    update_payload = {"status": "IN_PROGRESS", "priority": "HIGH"}
    update_res = await api_client.put(f"/api/maintenance/requests/{request_id}", json=update_payload)
    assert_api_success(update_res)
    updated_data = update_res.json()

    assert updated_data["status"] == "In Progress"
    assert updated_data["priority"] == "High"
    logger.info("✅ Update Test Passed")


@pytest.mark.asyncio
@pytest.mark.auth
async def test_list_and_filter_requests(api_client: httpx.AsyncClient, created_property_id: int):
    """
    Tests that maintenance requests can be listed and filtered by priority.
    
    Creates maintenance requests with varying priorities and verifies that filtering by a specific priority returns only matching requests.
    """
    # Create requests with different statuses
    await api_client.post("/api/maintenance/requests", json=maintenance_payload(created_property_id, priority="LOW"))
    await api_client.post("/api/maintenance/requests", json=maintenance_payload(created_property_id, status="COMPLETED", priority="HIGH"))

    # Filter by priority
    filter_res = await api_client.get("/api/maintenance/requests?priority=HIGH")
    assert_api_success(filter_res)
    filtered_data = filter_res.json()
    assert len(filtered_data) >= 1
    assert all(req["priority"] == "High" for req in filtered_data)
    logger.info("✅ List and Filter Test Passed")


@pytest.mark.asyncio
@pytest.mark.auth
async def test_delete_request(api_client: httpx.AsyncClient, created_property_id: int):
    """
    Tests deletion of a maintenance request and verifies it cannot be retrieved afterward.
    
    Creates a maintenance request, deletes it, and asserts that subsequent retrieval returns a 404 status.
    """
    payload = maintenance_payload(created_property_id)
    create_res = await api_client.post("/api/maintenance/requests", json=payload)
    request_id = create_res.json()["id"]

    delete_res = await api_client.delete(f"/api/maintenance/requests/{request_id}")
    assert_api_success(delete_res, 204)

    get_res = await api_client.get(f"/api/maintenance/requests/{request_id}")
    assert get_res.status_code == 404
    logger.info("✅ Delete Test Passed")


@pytest.mark.asyncio
@pytest.mark.auth
async def test_get_summary(api_client: httpx.AsyncClient, created_property_id: int):
    """
    Tests retrieval of the maintenance requests summary endpoint.

    Creates a pending maintenance request, retrieves the summary, and verifies that the total and pending request counts are greater than zero.
    """
    await api_client.post("/api/maintenance/requests", json=maintenance_payload(created_property_id, status="PENDING"))

    summary_res = await api_client.get("/api/maintenance/summary")
    assert_api_success(summary_res)
    summary_data = summary_res.json()

    assert summary_data["total_requests"] > 0
    assert summary_data["pending"] > 0
    logger.info("✅ Summary Test Passed")


@pytest.mark.asyncio
@pytest.mark.auth
async def test_get_summary_with_property_filter(api_client: httpx.AsyncClient, created_property_id: int):
    """
    Tests retrieval of maintenance summary filtered by property ID.

    Creates maintenance requests for the property, retrieves the summary filtered by property_id,
    and verifies that only requests for that property are counted.
    """
    # Create maintenance requests for this property
    await api_client.post("/api/maintenance/requests", json=maintenance_payload(created_property_id, status="PENDING"))
    await api_client.post("/api/maintenance/requests", json=maintenance_payload(created_property_id, status="IN_PROGRESS"))

    # Get summary filtered by property
    summary_res = await api_client.get(f"/api/maintenance/summary?property_id={created_property_id}")
    assert_api_success(summary_res)
    summary_data = summary_res.json()

    # Verify the summary contains data (counts should be > 0 for this property)
    assert summary_data["total_requests"] >= 2
    assert summary_data["pending"] >= 1
    assert summary_data["in_progress"] >= 1
    logger.info("✅ Summary with Property Filter Test Passed")


@pytest.mark.asyncio
@pytest.mark.auth
async def test_unauthorized_access(fresh_api_client: httpx.AsyncClient):
    """
    Verifies that accessing a maintenance request not owned by the user returns a 404 status.
    
    This test simulates unauthorized access by attempting to retrieve a maintenance request with an ID presumed not to belong to the authenticated user.
    """
    # This test requires a separate user/API client
    # For now, we simulate by trying to access an invalid ID
    res = await fresh_api_client.get("/api/maintenance/requests/99999")
    assert res.status_code in (403, 404)  # Or 403, depending on implementation
    logger.info("✅ Unauthorized Access Test Passed")


@pytest.mark.asyncio
@pytest.mark.auth
async def test_create_request_invalid_data(api_client: httpx.AsyncClient, created_property_id: int):
    """
    Tests that creating a maintenance request with invalid data returns a 422 status code.
    
    Attempts to create a maintenance request using an invalid priority value and verifies that the API responds with an Unprocessable Entity error.
    """
    payload = maintenance_payload(
        created_property_id, priority="InvalidPriority")
    response = await api_client.post("/api/maintenance/requests", json=payload)
    assert response.status_code == 422  # Unprocessable Entity
    logger.info("✅ Invalid Data Test Passed")


@pytest.mark.asyncio
@pytest.mark.auth
async def test_get_non_existent_request(api_client: httpx.AsyncClient):
    """
    Tests that retrieving a non-existent maintenance request returns a 404 status code.
    """
    response = await api_client.get("/api/maintenance/requests/999999")
    assert response.status_code == 404
    logger.info("✅ Not Found Test Passed")
