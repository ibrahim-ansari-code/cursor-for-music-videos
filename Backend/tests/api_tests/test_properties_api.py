"""
API tests for Property management operations.
"""

# Standard library imports
import logging
from typing import Any

# Third-party imports
import pytest
import httpx

# Local application/library specific imports
from .conftest import assert_api_success, assert_valid_json_response

logger = logging.getLogger(__name__)

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_property(api_client: httpx.AsyncClient) -> None:
    """
    Creates a new property via the API and verifies the response.
    """
    logger.info("Testing POST /api/properties/...")

    property_data = {
        "name": "CreateTest Property",
        "address": "123 Test Street",
        "city": "Test City",
        "province": "Test Province",
        "postal_code": "12345",
        "property_type": "Apartment",
        "description": "A test property for pytest"
    }

    response = await api_client.post("/api/properties/", json=property_data)
    property_obj = assert_valid_json_response(response, dict, expected_status=201)
    property_id = property_obj["id"]

    assert property_obj["name"] == property_data["name"]
    assert property_obj["address"] == property_data["address"]
    logger.info("✅ POST /api/properties/ successful, created property ID: %s", property_id)

    delete_response = await api_client.delete(f"/api/properties/{property_id}")
    assert_api_success(delete_response, 204)

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_all_properties(api_client: httpx.AsyncClient) -> None:
    """
    Tests retrieving all properties from the API.
    """
    logger.info("Testing GET /api/properties/...")
    response = await api_client.get("/api/properties/")
    properties = assert_valid_json_response(response, list)
    logger.info(f"✅ GET /api/properties/ successful, returned {len(properties)} properties")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_specific_property(created_property: dict[str, Any], api_client: httpx.AsyncClient) -> None:
    """
    Retrieves a specific property by ID and verifies the response.
    """
    logger.info("Testing GET /api/properties/{id}...")
    property_id = created_property["id"]
    response = await api_client.get(f"/api/properties/{property_id}")
    property_obj = assert_valid_json_response(response, dict)

    assert property_obj["id"] == property_id
    assert property_obj["name"] == created_property["name"]
    logger.info(f"✅ GET /api/properties/{property_id} successful")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_property(created_property: dict[str, Any], api_client: httpx.AsyncClient) -> None:
    """
    Updates an existing property and verifies the changes.
    """
    logger.info("Testing PUT /api/properties/{id}...")
    property_id = created_property["id"]
    update_data = {
        "name": "Updated Property Name via Test",
        "description": "Updated description via test"
    }
    update_response = await api_client.put(f"/api/properties/{property_id}", json=update_data)
    updated_property = assert_valid_json_response(update_response, dict)

    assert updated_property["name"] == "Updated Property Name via Test"
    assert updated_property["description"] == "Updated description via test"
    assert updated_property["id"] == property_id
    logger.info(f"✅ PUT /api/properties/{property_id} successful")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_property(api_client: httpx.AsyncClient) -> None:
    """
    Tests deletion of a property via the API.
    """
    logger.info("Testing DELETE /api/properties/{id}...")
    property_data = {
        "name": "DeleteTest Property",
        "address": "789 Delete Street",
        "city": "Delete City",
        "province": "Delete Province",
        "postal_code": "98765",
        "property_type": "Condo",
        "description": "A test property for deletion"
    }
    create_response = await api_client.post("/api/properties/", json=property_data)
    property_obj = assert_valid_json_response(create_response, dict, expected_status=201)
    property_id = property_obj["id"]

    delete_response = await api_client.delete(f"/api/properties/{property_id}")
    assert_api_success(delete_response, 204)

    get_response = await api_client.get(f"/api/properties/{property_id}")
    assert get_response.status_code == 404
    logger.info(f"✅ DELETE /api/properties/{property_id} successful")

    # TODO: Add more property tests:
    # - Test property creation with invalid data (validation errors)
    # - Test property search/filtering
    # - Test property-unit relationships
    # - Test property owner associations
    # - Test property status updates
