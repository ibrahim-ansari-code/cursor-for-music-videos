"""
API tests for Property management operations.
"""

# Standard library imports
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

# Third-party imports
import pytest
import pytest_asyncio

# Local application/library specific imports
from .conftest import assert_api_success, assert_valid_json_response, APITestClient

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def created_property(api_client: APITestClient) -> AsyncGenerator[dict[str, Any], None]:
    """
    Asynchronously creates a test property for use in API tests and ensures its deletion after the test completes.
    
    Yields:
        A dictionary representing the created property.
    """
    property_data = {
        "name": f"Test Fixture Property {int(time.time())}",
        "address": "999 Fixture Street",
        "city": "Test City",
        "province": "Test Province",
        "postal_code": "T5T5T5",
        "property_type": "Apartment",
        "description": "A test property created by fixture"
    }

    # Create property
    response = await api_client.post("/api/properties/", json=property_data)
    property_obj = assert_valid_json_response(
        response, dict, expected_status=201)

    yield property_obj

    # Cleanup - this runs after the test regardless of test outcome
    try:
        delete_response = await api_client.delete(f"/api/properties/{property_obj['id']}")
        if delete_response.status_code == 204:
            logger.info(
                "✅ Fixture cleanup: deleted property %s", property_obj['id'])
        elif delete_response.status_code == 404:
            logger.info(
                "✅ Fixture cleanup: property %s already deleted", property_obj['id'])
        else:
            logger.error(
                "❌ Fixture cleanup failed: DELETE returned %s", delete_response.status_code)
    except Exception:
        logger.exception("❌ Fixture cleanup exception:")


@pytest.mark.auth
@pytest.mark.integration
class TestPropertiesAPI:
    """Test suite for Properties API endpoints"""

    @pytest.mark.asyncio
    async def test_create_property(self, api_client: APITestClient) -> None:
        """
        Creates a new property via the API and verifies the response fields and values.
        
        Sends a POST request to create a property with test data, asserts the response contains the expected fields, and deletes the created property to maintain test isolation.
        """
        logger.info("Testing POST /api/properties/...")

        property_data = {
            "name": f"CreateTest Property {id(self)}",
            "address": "123 Test Street",
            "city": "Test City",
            "province": "Test Province",
            "postal_code": "12345",
            "property_type": "Apartment",
            "description": "A test property for pytest"
        }

        response = await api_client.post("/api/properties/", json=property_data)
        property_obj = assert_valid_json_response(
            response, dict, expected_status=201)

        # Store property ID for cleanup tracking
        property_id = property_obj["id"]

        # Verify property was created with expected data
        assert property_obj["name"] == property_data["name"]
        assert property_obj["address"] == property_data["address"]
        assert property_obj["city"] == property_data["city"]
        assert "id" in property_obj

        logger.info(
            "✅ POST /api/properties/ successful, created property ID: %s", property_id)

        # Immediate cleanup
        try:
            delete_response = await api_client.delete(f"/api/properties/{property_id}")
            if delete_response.status_code == 204:
                logger.info(
                    "✅ Immediate cleanup: deleted property %s", property_id)
            else:
                logger.warning(
                    "⚠️ Delete returned %s for property %s", delete_response.status_code, property_id)
        except Exception:
            logger.exception("❌ Cleanup failed for property %s:", property_id)

    @pytest.mark.asyncio
    async def test_get_all_properties(self, api_client: APITestClient) -> None:
        """
        Tests retrieving all properties from the API.
        
        Sends a GET request to the /api/properties/ endpoint and asserts that the response is a valid JSON list of properties.
        """
        logger.info("Testing GET /api/properties/...")

        response = await api_client.get("/api/properties/")
        properties = assert_valid_json_response(response, list)

        logger.info(
            f"✅ GET /api/properties/ successful, returned {len(properties)} properties")

    @pytest.mark.asyncio
    async def test_get_specific_property(self, created_property: dict[str, Any], api_client: APITestClient) -> None:
        """
        Retrieves a specific property by ID and verifies the response matches the expected data.
        
        Uses a fixture to ensure the property exists, sends a GET request to fetch it, and asserts that the returned property data matches the fixture.
        """
        logger.info("Testing GET /api/properties/{id}...")

        # Use the property from the fixture instead of searching for existing ones
        property_id = created_property["id"]
        response = await api_client.get(f"/api/properties/{property_id}")
        property_obj = assert_valid_json_response(response, dict)

        # Verify response contains property data
        assert property_obj["id"] == property_id
        assert "name" in property_obj
        assert "address" in property_obj

        # Verify the fixture data matches response
        assert property_obj["name"] == created_property["name"]
        assert property_obj["address"] == created_property["address"]

        logger.info(f"✅ GET /api/properties/{property_id} successful")

    @pytest.mark.asyncio
    async def test_update_property(self, created_property: dict[str, Any], api_client: APITestClient) -> None:
        """
        Updates an existing property and verifies that the name and description are changed while the property ID remains the same.
        
        Uses a fixture property to perform the update and asserts that the response reflects the intended modifications.
        """
        logger.info("Testing PUT /api/properties/{id}...")

        property_id = created_property["id"]

        # Update data
        update_data = {
            "name": "Updated Property Name via Test",
            "description": "Updated description via test"
        }

        update_response = await api_client.put(f"/api/properties/{property_id}", json=update_data)
        updated_property = assert_valid_json_response(update_response, dict)

        # Verify updates were applied
        assert updated_property["name"] == "Updated Property Name via Test"
        assert updated_property["description"] == "Updated description via test"
        assert updated_property["id"] == property_id

        logger.info(f"✅ PUT /api/properties/{property_id} successful")

    @pytest.mark.asyncio
    async def test_delete_property(self, api_client: APITestClient) -> None:
        """
        Tests deletion of a property via the API.
        
        Creates a new property, deletes it using the DELETE endpoint, and verifies that subsequent retrieval returns a 404 status code to confirm successful deletion.
        """
        logger.info("Testing DELETE /api/properties/{id}...")

        # Create property specifically for deletion test
        property_data = {
            "name": f"DeleteTest Property {id(self)}",
            "address": "789 Delete Street",
            "city": "Delete City",
            "province": "Delete Province",
            "postal_code": "98765",
            "property_type": "Condo",
            "description": "A test property for deletion"
        }

        create_response = await api_client.post("/api/properties/", json=property_data)
        property_obj = assert_valid_json_response(
            create_response, dict, expected_status=201)
        property_id = property_obj["id"]

        # Delete the property
        delete_response = await api_client.delete(f"/api/properties/{property_id}")
        # 204 No Content for successful delete
        assert_api_success(delete_response, 204)

        # Verify property was deleted by trying to get it
        get_response = await api_client.get(f"/api/properties/{property_id}")
        assert get_response.status_code == 404, f"Deleted property should return 404, got {get_response.status_code}"

        logger.info(f"✅ DELETE /api/properties/{property_id} successful")

    # TODO: Add more property tests:
    # - Test property creation with invalid data (validation errors)
    # - Test property search/filtering
    # - Test property-unit relationships
    # - Test property owner associations
    # - Test property status updates
