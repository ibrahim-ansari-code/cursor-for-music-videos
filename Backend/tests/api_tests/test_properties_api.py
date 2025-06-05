"""
API tests for Property management operations.
"""

# Standard library imports
import logging
import time
from typing import Any, AsyncGenerator, Dict

# Third-party imports
import httpx
import pytest
import pytest_asyncio

# Local application/library specific imports
from .conftest import assert_api_success, assert_valid_json_response, APITestClient

logger = logging.getLogger(__name__)

@pytest_asyncio.fixture
async def created_property(api_client: APITestClient) -> AsyncGenerator[Dict[str, Any], None]:
    """Fixture that creates a test property and ensures cleanup"""
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
    response = await api_client.post("/api/properties/", json_data=property_data)
    property_obj = assert_valid_json_response(response, dict, expected_status=201)
    
    yield property_obj
    
    # Cleanup - this runs after the test regardless of test outcome
    try:
        delete_response = await api_client.delete(f"/api/properties/{property_obj['id']}")
        if delete_response.status_code == 204:
            logger.info(f"✅ Fixture cleanup: deleted property {property_obj['id']}")
        elif delete_response.status_code == 404:
            logger.info(f"✅ Fixture cleanup: property {property_obj['id']} already deleted")
        else:
            logger.error(f"❌ Fixture cleanup failed: DELETE returned {delete_response.status_code}")
    except Exception as e:
        logger.error(f"❌ Fixture cleanup exception: {e}")

@pytest.mark.auth
@pytest.mark.integration
class TestPropertiesAPI:
    """Test suite for Properties API endpoints"""

    @pytest.mark.asyncio
    async def test_create_property(self, api_client: APITestClient) -> None:
        """Test POST /api/properties/ with immediate cleanup"""
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
        
        response = await api_client.post("/api/properties/", json_data=property_data)
        property_obj = assert_valid_json_response(response, dict, expected_status=201)
        
        # Store property ID for cleanup tracking
        property_id = property_obj["id"]
        
        # Verify property was created with expected data
        assert property_obj["name"] == property_data["name"]
        assert property_obj["address"] == property_data["address"]
        assert property_obj["city"] == property_data["city"]
        assert "id" in property_obj
        
        logger.info(f"✅ POST /api/properties/ successful, created property ID: {property_id}")
        
        # Immediate cleanup
        try:
            delete_response = await api_client.delete(f"/api/properties/{property_id}")
            if delete_response.status_code == 204:
                logger.info(f"✅ Immediate cleanup: deleted property {property_id}")
            else:
                logger.warning(f"⚠️ Delete returned {delete_response.status_code} for property {property_id}")
        except Exception as e:
            logger.error(f"❌ Cleanup failed for property {property_id}: {e}")

    @pytest.mark.asyncio
    async def test_get_all_properties(self, api_client: APITestClient) -> None:
        """Test GET /api/properties/ (read-only, no cleanup needed)"""
        logger.info("Testing GET /api/properties/...")
        
        response = await api_client.get("/api/properties/")
        properties = assert_valid_json_response(response, list)
        
        logger.info(f"✅ GET /api/properties/ successful, returned {len(properties)} properties")

    @pytest.mark.asyncio
    async def test_get_specific_property(self, created_property: Dict[str, Any], api_client: APITestClient) -> None:
        """Test GET /api/properties/{id} using fixture for guaranteed property"""
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
    async def test_update_property(self, created_property: Dict[str, Any], api_client: APITestClient) -> None:
        """Test PUT /api/properties/{id} using fixture for guaranteed cleanup"""
        logger.info("Testing PUT /api/properties/{id}...")
        
        property_id = created_property["id"]
        
        # Update data
        update_data = {
            "name": "Updated Property Name via Test",
            "description": "Updated description via test"
        }
        
        update_response = await api_client.put(f"/api/properties/{property_id}", json_data=update_data)
        updated_property = assert_valid_json_response(update_response, dict)
        
        # Verify updates were applied
        assert updated_property["name"] == "Updated Property Name via Test"
        assert updated_property["description"] == "Updated description via test"
        assert updated_property["id"] == property_id
        
        logger.info(f"✅ PUT /api/properties/{property_id} successful")

    @pytest.mark.asyncio
    async def test_delete_property(self, api_client: APITestClient) -> None:
        """Test DELETE /api/properties/{id} - self-contained test"""
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
        
        create_response = await api_client.post("/api/properties/", json_data=property_data)
        property_obj = assert_valid_json_response(create_response, dict, expected_status=201)
        property_id = property_obj["id"]
        
        # Delete the property
        delete_response = await api_client.delete(f"/api/properties/{property_id}")
        assert_api_success(delete_response, 204)  # 204 No Content for successful delete
        
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
