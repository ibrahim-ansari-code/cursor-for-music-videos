"""
API tests for Property management operations.
"""

# Standard library imports
import logging
from typing import Any
from uuid import uuid4

# Third-party imports
import pytest
import httpx

# Local application/library specific imports
from .conftest import assert_api_success, assert_valid_json_response

logger = logging.getLogger(__name__)

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_property_basic(api_client: httpx.AsyncClient) -> None:
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
        "property_type": "Residential",
        "description": "A test property for pytest"
    }

    response = await api_client.post("/api/properties/", json=property_data)
    property_obj = assert_valid_json_response(response, dict, expected_status=201)
    property_id = property_obj["id"]

    assert property_obj["name"] == property_data["name"]
    assert property_obj["address"] == property_data["address"]
    assert property_obj["status"] == "ACTIVE"  # Default status
    assert property_obj["owner"] is not None
    assert property_obj["units"] == []  # No units created
    logger.info("✅ POST /api/properties/ successful, created property ID: %s", property_id)

    # Cleanup
    delete_response = await api_client.delete(f"/api/properties/{property_id}")
    assert_api_success(delete_response, 204)

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_property_with_units(api_client: httpx.AsyncClient) -> None:
    """
    Creates a property with multiple units and verifies floor assignment logic.
    """
    logger.info("Testing POST /api/properties/ with units...")

    property_data = {
        "name": "Multi-Unit Property",
        "address": "456 Unit Street",
        "city": "Unit City",
        "province": "Unit Province",
        "postal_code": "54321",
        "property_type": "Residential",
        "description": "A property with multiple units",
        "units": ["101", "201", "301", "Basement", "PH"]  # Test floor derivation
    }

    response = await api_client.post("/api/properties/", json=property_data)
    property_obj = assert_valid_json_response(response, dict, expected_status=201)
    property_id = property_obj["id"]

    assert len(property_obj["units"]) == 5
    
    # Check floor assignment logic
    unit_floors = {unit["name"]: unit["floor"] for unit in property_obj["units"]}
    assert unit_floors["101"] == 1  # First digit is 1
    assert unit_floors["201"] == 2  # First digit is 2
    assert unit_floors["301"] == 3  # First digit is 3
    assert unit_floors["Basement"] == 0  # No digit, default to 0
    assert unit_floors["PH"] == 0  # No digit, default to 0
    
    # All units should be unrented initially
    assert all(not unit["is_rented"] for unit in property_obj["units"])
    
    # Status should be VACANT since no units are rented
    assert property_obj["status"] == "VACANT"
    
    logger.info("✅ Property with units created successfully")

    # Cleanup
    delete_response = await api_client.delete(f"/api/properties/{property_id}")
    assert_api_success(delete_response, 204)

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_property_validation_errors(api_client: httpx.AsyncClient) -> None:
    """
    Tests property creation with invalid data to verify validation.
    """
    logger.info("Testing POST /api/properties/ with invalid data...")

    # Test missing required fields
    invalid_data = {
        "name": "",  # Empty name should fail validation
        "address": "123 Test Street",
        "city": "Test City",
        "province": "Test Province",
        "postal_code": "12345",
        "property_type": "Residential"
    }

    response = await api_client.post("/api/properties/", json=invalid_data)
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("name must not be empty" in str(error) for error in error_detail)

    # Test completely missing required field
    missing_field_data = {
        # Missing 'name' field entirely
        "address": "123 Test Street",
        "city": "Test City",
        "province": "Test Province",
        "postal_code": "12345",
        "property_type": "Residential"
    }

    response = await api_client.post("/api/properties/", json=missing_field_data)
    assert response.status_code == 422

    logger.info("✅ Validation errors working correctly")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_all_properties_with_filters(api_client: httpx.AsyncClient) -> None:
    """
    Tests retrieving properties with various filters.
    """
    logger.info("Testing GET /api/properties/ with filters...")
    
    # Create test properties with different statuses and types
    properties_to_create = [
        {
            "name": "Active Residential",
            "address": "111 Active St",
            "city": "Test City",
            "province": "Test Province",
            "postal_code": "11111",
            "property_type": "Residential",
            "status": "ACTIVE"
        },
        {
            "name": "Inactive Commercial",
            "address": "222 Inactive Ave",
            "city": "Test City",
            "province": "Test Province",
            "postal_code": "22222",
            "property_type": "Commercial",
            "status": "INACTIVE"
        }
    ]
    
    created_ids = []
    for prop_data in properties_to_create:
        response = await api_client.post("/api/properties/", json=prop_data)
        prop = assert_valid_json_response(response, dict, expected_status=201)
        created_ids.append(prop["id"])
    
    # Test filter by status
    response = await api_client.get("/api/properties/?status_filter=ACTIVE")
    active_properties = assert_valid_json_response(response, list)
    assert any(p["name"] == "Active Residential" for p in active_properties)
    
    # Test filter by property type
    response = await api_client.get("/api/properties/?property_type=Commercial")
    commercial_properties = assert_valid_json_response(response, list)
    assert any(p["name"] == "Inactive Commercial" for p in commercial_properties)
    
    logger.info("✅ Property filtering working correctly")
    
    # Cleanup
    for prop_id in created_ids:
        await api_client.delete(f"/api/properties/{prop_id}")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_specific_property_with_details(created_property: dict[str, Any], api_client: httpx.AsyncClient) -> None:
    """
    Retrieves a specific property by ID and verifies all details including owner info.
    """
    logger.info("Testing GET /api/properties/{id} with full details...")
    property_id = created_property["id"]
    response = await api_client.get(f"/api/properties/{property_id}")
    property_obj = assert_valid_json_response(response, dict)

    assert property_obj["id"] == property_id
    assert property_obj["name"] == created_property["name"]
    
    # Verify owner information is included
    assert "owner" in property_obj
    assert property_obj["owner"] is not None
    assert "email" in property_obj["owner"]
    assert "id" in property_obj["owner"]
    
    # Verify units array is included (even if empty)
    assert "units" in property_obj
    assert isinstance(property_obj["units"], list)
    
    logger.info(f"✅ GET /api/properties/{property_id} successful with full details")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_property_partial(created_property: dict[str, Any], api_client: httpx.AsyncClient) -> None:
    """
    Tests partial update of a property (only updating specific fields).
    """
    logger.info("Testing PUT /api/properties/{id} with partial update...")
    property_id = created_property["id"]
    
    # Only update name and description, leave other fields unchanged
    update_data = {
        "name": "Partially Updated Property",
        "description": "This description was updated"
    }
    
    update_response = await api_client.put(f"/api/properties/{property_id}", json=update_data)
    updated_property = assert_valid_json_response(update_response, dict)

    assert updated_property["name"] == "Partially Updated Property"
    assert updated_property["description"] == "This description was updated"
    # Other fields should remain unchanged
    assert updated_property["address"] == created_property["address"]
    assert updated_property["city"] == created_property["city"]
    
    logger.info(f"✅ Partial update of property {property_id} successful")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_property_validation(created_property: dict[str, Any], api_client: httpx.AsyncClient) -> None:
    """
    Tests property update with invalid data.
    """
    logger.info("Testing PUT /api/properties/{id} with validation errors...")
    property_id = created_property["id"]
    
    # Try to update with empty name
    invalid_update = {
        "name": ""  # Should fail validation
    }
    
    response = await api_client.put(f"/api/properties/{property_id}", json=invalid_update)
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("name must not be an empty string" in str(error) for error in error_detail)
    
    # Try to update with unexpected field (should be forbidden by schema)
    unexpected_field_update = {
        "name": "Valid Name",
        "units": ["101", "102"]  # Units cannot be updated through this endpoint
    }
    
    response = await api_client.put(f"/api/properties/{property_id}", json=unexpected_field_update)
    assert response.status_code == 422
    
    logger.info("✅ Update validation working correctly")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_property_status_derivation(api_client: httpx.AsyncClient) -> None:
    """
    Tests that property status is correctly derived based on unit occupancy.
    """
    logger.info("Testing property status derivation...")
    
    # Create property with units
    property_data = {
        "name": "Status Test Property",
        "address": "789 Status St",
        "city": "Status City",
        "province": "Status Province",
        "postal_code": "77777",
        "property_type": "Residential",
        "units": ["101", "102", "103"]
    }
    
    response = await api_client.post("/api/properties/", json=property_data)
    property_obj = assert_valid_json_response(response, dict, expected_status=201)
    property_id = property_obj["id"]
    
    # Initially all units are vacant, so status should be VACANT
    assert property_obj["status"] == "VACANT"
    
    # TODO: When unit update endpoints are available, test:
    # - Update one unit to rented -> status should be PARTIALLY_RENTED
    # - Update all units to rented -> status should be RENTED
    # - Update all back to vacant -> status should be VACANT
    
    logger.info("✅ Property status derivation working correctly")
    
    # Cleanup
    await api_client.delete(f"/api/properties/{property_id}")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_property_with_constraints(api_client: httpx.AsyncClient) -> None:
    """
    Tests property deletion with various constraints.
    """
    logger.info("Testing DELETE /api/properties/{id} with constraints...")
    
    # Create a property
    property_data = {
        "name": "Delete Constraint Test",
        "address": "999 Delete St",
        "city": "Delete City",
        "province": "Delete Province",
        "postal_code": "99999",
        "property_type": "Residential"
    }
    
    response = await api_client.post("/api/properties/", json=property_data)
    property_obj = assert_valid_json_response(response, dict, expected_status=201)
    property_id = property_obj["id"]
    
    # TODO: When lease creation is available, test:
    # - Create an active lease for this property
    # - Attempt to delete property (should fail with 400)
    # - Change lease to EXPIRED status
    # - Delete should now succeed
    
    # For now, just test successful deletion without constraints
    delete_response = await api_client.delete(f"/api/properties/{property_id}")
    assert_api_success(delete_response, 204)
    
    # Verify property is actually deleted
    get_response = await api_client.get(f"/api/properties/{property_id}")
    assert get_response.status_code == 404
    
    logger.info("✅ Property deletion working correctly")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_property_not_found_errors(api_client: httpx.AsyncClient) -> None:
    """
    Tests proper 404 error handling for non-existent properties.
    """
    logger.info("Testing 404 errors for non-existent properties...")
    
    non_existent_id = 999999
    
    # Test GET
    response = await api_client.get(f"/api/properties/{non_existent_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    
    # Test PUT
    response = await api_client.put(f"/api/properties/{non_existent_id}", json={"name": "Update"})
    assert response.status_code == 404
    
    # Test DELETE
    response = await api_client.delete(f"/api/properties/{non_existent_id}")
    assert response.status_code == 404
    
    logger.info("✅ 404 error handling working correctly")

# TODO: Additional tests to implement when other endpoints are ready:
# - Test property-tenant relationships through units
# - Test property financial summaries (rent collection, expenses)
# - Test property maintenance request associations
# - Test bulk property operations
# - Test property search with complex filters
# - Test property status transitions with lease lifecycle
