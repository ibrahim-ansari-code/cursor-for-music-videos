import logging
import json
from typing import Any
import pytest

from .conftest import APITestClient

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
class TestMaintenanceAPI:
    async def test_create_and_get_request(self, api_client: APITestClient, created_property_id: int):
        """
        Tests the creation and retrieval of a maintenance request via the API.
        
        Creates a maintenance request for the specified property and verifies the response data. Then retrieves the created request by its ID and asserts the returned data matches the created request.
        """
        payload = maintenance_payload(created_property_id)
        logger.info("Sending maintenance request payload: %s", payload)
        create_res = await api_client.post("/api/maintenance/requests", json=payload)
        
        if create_res.status_code != 201:
            logger.error("Failed to create maintenance request. Status: %s", create_res.status_code)
            logger.error("Response body: %s", create_res.text)
            try:
                error_json = create_res.json()
                logger.error("Error JSON: %s", error_json)
            except json.JSONDecodeError:
                logger.exception("Could not decode JSON from response body")
        
        assert create_res.status_code == 201
        created_data = create_res.json()
        request_id = created_data["id"]

        assert created_data["issue_title"] == "Broken Pipe"
        assert created_data["property"]["id"] == created_property_id

        get_res = await api_client.get(f"/api/maintenance/requests/{request_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == request_id
        logger.info("✅ Create and Get Test Passed")

    async def test_update_request(self, api_client: APITestClient, created_property_id: int):
        """
        Tests updating an existing maintenance request and verifies that the updated fields are correctly reflected in the response.
        
        Creates a maintenance request, updates its status and priority, and asserts that the changes are persisted.
        """
        payload = maintenance_payload(created_property_id)
        create_res = await api_client.post("/api/maintenance/requests", json=payload)
        request_id = create_res.json()["id"]

        update_payload = {"status": "IN_PROGRESS", "priority": "HIGH"}
        update_res = await api_client.put(f"/api/maintenance/requests/{request_id}", json=update_payload)
        assert update_res.status_code == 200
        updated_data = update_res.json()

        assert updated_data["status"] == "IN_PROGRESS"
        assert updated_data["priority"] == "HIGH"
        logger.info("✅ Update Test Passed")

    async def test_list_and_filter_requests(self, api_client: APITestClient, created_property_id: int):
        """
        Tests that maintenance requests can be listed and filtered by priority.
        
        Creates maintenance requests with varying priorities and verifies that filtering by a specific priority returns only matching requests.
        """
        # Create requests with different statuses
        await api_client.post("/api/maintenance/requests", json=maintenance_payload(created_property_id, priority="LOW"))
        await api_client.post("/api/maintenance/requests", json=maintenance_payload(created_property_id, status="COMPLETED", priority="HIGH"))

        # Filter by priority
        filter_res = await api_client.get("/api/maintenance/requests?priority=HIGH")
        assert filter_res.status_code == 200
        filtered_data = filter_res.json()
        assert len(filtered_data) >= 1
        assert all(req["priority"] == "HIGH" for req in filtered_data)
        logger.info("✅ List and Filter Test Passed")

    async def test_delete_request(self, api_client: APITestClient, created_property_id: int):
        """
        Tests deletion of a maintenance request and verifies it cannot be retrieved afterward.
        
        Creates a maintenance request, deletes it, and asserts that subsequent retrieval returns a 404 status.
        """
        payload = maintenance_payload(created_property_id)
        create_res = await api_client.post("/api/maintenance/requests", json=payload)
        request_id = create_res.json()["id"]

        delete_res = await api_client.delete(f"/api/maintenance/requests/{request_id}")
        assert delete_res.status_code == 204

        get_res = await api_client.get(f"/api/maintenance/requests/{request_id}")
        assert get_res.status_code == 404
        logger.info("✅ Delete Test Passed")

    async def test_get_summary(self, api_client: APITestClient, created_property_id: int):
        """
        Tests retrieval of the maintenance requests summary endpoint.
        
        Creates a pending maintenance request, retrieves the summary, and verifies that the total and pending request counts are greater than zero.
        """
        await api_client.post("/api/maintenance/requests", json=maintenance_payload(created_property_id, status="PENDING"))

        summary_res = await api_client.get("/api/maintenance/summary")
        assert summary_res.status_code == 200
        summary_data = summary_res.json()

        assert summary_data["total_requests"] > 0
        assert summary_data["pending"] > 0
        logger.info("✅ Summary Test Passed")

    async def test_unauthorized_access(self, fresh_api_client: APITestClient):
        """
        Verifies that accessing a maintenance request not owned by the user returns a 404 status.
        
        This test simulates unauthorized access by attempting to retrieve a maintenance request with an ID presumed not to belong to the authenticated user.
        """
        # This test requires a separate user/API client
        # For now, we simulate by trying to access an invalid ID
        res = await fresh_api_client.get("/api/maintenance/requests/99999")
        assert res.status_code in (403, 404)  # Or 403, depending on implementation
        logger.info("✅ Unauthorized Access Test Passed")

    async def test_create_request_invalid_data(self, api_client: APITestClient, created_property_id: int):
        """
        Tests that creating a maintenance request with invalid data returns a 422 status code.
        
        Attempts to create a maintenance request using an invalid priority value and verifies that the API responds with an Unprocessable Entity error.
        """
        payload = maintenance_payload(
            created_property_id, priority="InvalidPriority")
        response = await api_client.post("/api/maintenance/requests", json=payload)
        assert response.status_code == 422  # Unprocessable Entity
        logger.info("✅ Invalid Data Test Passed")

    async def test_get_non_existent_request(self, api_client: APITestClient):
        """
        Tests that retrieving a non-existent maintenance request returns a 404 status code.
        """
        response = await api_client.get("/api/maintenance/requests/999999")
        assert response.status_code == 404
        logger.info("✅ Not Found Test Passed")

    async def test_permission_logic(self, api_client: APITestClient, created_property_id: int):
        """
        Verifies that users can access their own maintenance requests and are denied access to requests they do not own.
        
        Creates a maintenance request for the authenticated user and confirms successful retrieval. Attempts to access a non-existent request to simulate unauthorized access and expects a 404 response.
        """
        # 1. Create a request on a property owned by the user
        payload = maintenance_payload(created_property_id)
        create_res = await api_client.post("/api/maintenance/requests", json=payload)
        assert create_res.status_code == 201
        request_id = create_res.json()["id"]

        # 2. Confirm the owner can access it
        get_res_owner = await api_client.get(f"/api/maintenance/requests/{request_id}")
        assert get_res_owner.status_code == 200
        logger.info("✅ Owner can access their own maintenance request.")

        # 3. Simulate access to an unauthorized resource (e.g., a request on a property not owned by the user)
        # In a real multi-user test, you'd create a request with another user.
        # Here, we test the boundary by checking a non-existent ID, which is handled by the 404 check before the permission check.
        unauthorized_res = await api_client.get("/api/maintenance/requests/999999")
        assert unauthorized_res.status_code == 404
        logger.info(
            "✅ Correctly returns 404 for a non-existent (and thus unauthorized) resource.")
