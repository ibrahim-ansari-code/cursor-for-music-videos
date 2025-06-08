"""
API tests for Tenant management operations.
"""

import pytest
import logging
import httpx
import pytest_asyncio
import time
import uuid

logger = logging.getLogger(__name__)

# Helper functions for API testing


def assert_api_success(response: httpx.Response, expected_status: int = 200):
    """
    Asserts that the HTTP response status code matches the expected value.
    
    Raises an assertion error if the response status does not match, including the status code and up to 500 characters of the response text for debugging.
    """
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text[:500]}"
    )


def assert_valid_json_response(response: httpx.Response, expected_type=None, expected_status=200):
    """
    Asserts that an HTTP response contains valid JSON data and matches the expected type.
    
    Calls `assert_api_success` to verify the response status code. Attempts to parse the response as JSON and, if `expected_type` is provided, asserts that the parsed data matches the specified type. Fails the test with an error message if the response is not valid JSON.
    
    Args:
        response: The HTTP response to validate.
        expected_type: Optional type to check against the parsed JSON data.
        expected_status: The expected HTTP status code (default is 200).
    
    Returns:
        The parsed JSON data from the response.
    """
    assert_api_success(response, expected_status)
    try:
        data = response.json()
        if expected_type:
            assert isinstance(
                data, expected_type), f"Expected {expected_type}, got {type(data)}"
        return data
    except Exception as e:
        pytest.fail(
            f"Invalid JSON response: {e}. Response text: {response.text[:500]}")


@pytest_asyncio.fixture
async def created_tenant(api_client, created_landlord_property: int):
    """
    Asynchronously creates a test tenant linked to a landlord-owned property for use in tests, and ensures the tenant is deleted after the test completes.
    
    Yields:
        The created tenant as a dictionary.
    """
    property_id = created_landlord_property

    tenant_data = {
         "first_name": "TestFixture",
         "last_name": "TenantTest",
        "email": f"test_fixture_{uuid.uuid4()}@example.com",
        "status": "Active",
        "current_property_id": property_id
    }

    # Create tenant
    response = await api_client.post("/api/tenants/", json_data=tenant_data)
    tenant = assert_valid_json_response(response, dict, expected_status=201)

    yield tenant

    # Cleanup - this runs after the test regardless of test outcome
    try:
        delete_response = await api_client.delete(f"/api/tenants/{tenant['id']}")
        if delete_response.status_code == 204:
            logger.info(f"✅ Fixture cleanup: deleted tenant {tenant['id']}")
        elif delete_response.status_code == 403:
            logger.warning(
                f"⚠️ Fixture cleanup: tenant {tenant['id']} deletion blocked by permissions (RLS issue)")
        elif delete_response.status_code == 404:
            logger.info(
                f"✅ Fixture cleanup: tenant {tenant['id']} already deleted")
        else:
            logger.error(
                f"❌ Fixture cleanup failed: DELETE returned {delete_response.status_code}")
    except Exception as e:
        logger.error(f"❌ Fixture cleanup exception: {e}")


@pytest.mark.auth
@pytest.mark.integration
class TestTenantsAPI:
    """Test suite for Tenants API endpoints"""

    @pytest.mark.asyncio
    async def test_create_tenant(self, api_client, created_landlord_property: int):
        """
        Tests tenant creation via POST /api/tenants/ with association to a landlord-owned property.
        
        Creates a tenant using the provided API client and verifies that the response contains the correct tenant data and property association. Immediately deletes the created tenant to ensure test isolation, failing the test if cleanup is unsuccessful.
        """
        logger.info("Testing POST /api/tenants/...")
        property_id = created_landlord_property

        tenant_data = {
            "first_name": "CreateTest",
            "last_name": "Tenant",
            "email": f"create_test_{id(self)}_{property_id}@example.com",
            "phone": "+1-555-0123",
            "status": "Active",
            "current_property_id": property_id  # Associate with landlord-owned property
        }

        response = await api_client.post("/api/tenants/", json_data=tenant_data)
        tenant = assert_valid_json_response(
            response, dict, expected_status=201)

        tenant_id = tenant["id"]

        assert tenant["first_name"] == tenant_data["first_name"]
        assert tenant["last_name"] == tenant_data["last_name"]
        assert tenant["email"] == tenant_data["email"]
        assert "id" in tenant
        assert tenant.get("current_property_id") == property_id

        logger.info(
            f"✅ POST /api/tenants/ successful, created tenant ID: {tenant_id} associated with prop: {property_id}")

        # Immediate cleanup
        try:
            delete_response = await api_client.delete(f"/api/tenants/{tenant_id}")
            assert_api_success(delete_response, expected_status=204)
            logger.info("✅ Immediate cleanup: deleted %s", tenant_id)
        except Exception as e:
            logger.error(f"❌ Cleanup exception for tenant {tenant_id}: {e}")
            pytest.fail(f"Cleanup exception for tenant {tenant_id}: {e}")

    @pytest.mark.asyncio
    async def test_get_all_tenants(self, api_client):
        """
        Tests retrieval of all tenants via the GET /api/tenants/ endpoint.
        
        Asserts that the response status is 200 and the returned data is a list of tenants.
        """
        logger.info("Testing GET /api/tenants/...")

        response = await api_client.get("/api/tenants/")
        tenants = assert_valid_json_response(response, list)

        logger.info(
            f"✅ GET /api/tenants/ successful, returned {len(tenants)} tenants")

    @pytest.mark.asyncio
    async def test_get_specific_tenant(self, created_tenant, api_client):
        """
        Tests retrieval of a specific tenant by ID using the created_tenant fixture.
        
        Verifies that the GET /api/tenants/{id} endpoint returns status 200 and that the returned tenant data matches the fixture.
        """
        logger.info("Testing GET /api/tenants/{id}...")

        tenant_id = created_tenant["id"]

        response = await api_client.get(f"/api/tenants/{tenant_id}")

        # Expect 200 OK as tenant should be accessible via property link from created_tenant fixture
        tenant = assert_valid_json_response(
            response, dict, expected_status=200)
        assert tenant["id"] == tenant_id
        assert tenant["first_name"] == created_tenant["first_name"]
        assert tenant["last_name"] == created_tenant["last_name"]
        logger.info(f"✅ GET /api/tenants/{tenant_id} successful")

    @pytest.mark.asyncio
    async def test_update_tenant(self, created_tenant, api_client):
        """
        Tests updating a tenant's information via PATCH /api/tenants/{id}.
        
        Uses a fixture-created tenant to ensure cleanup. Verifies that the tenant's first name and phone number are updated correctly and that the tenant ID remains unchanged.
        """
        logger.info("Testing PATCH /api/tenants/{id}...")

        tenant_id = created_tenant["id"]

        update_data = {
            "first_name": "UpdatedByTest",
            "phone": "+1-555-9999"
        }

        update_response = await api_client.patch(f"/api/tenants/{tenant_id}", json_data=update_data)

        # Expect 200 OK as tenant should be accessible for update
        updated_tenant = assert_valid_json_response(
            update_response, dict, expected_status=200)
        assert updated_tenant["first_name"] == "UpdatedByTest"
        assert updated_tenant["phone"] == "+1-555-9999"
        assert updated_tenant["id"] == tenant_id
        logger.info(f"✅ PATCH /api/tenants/{tenant_id} successful")

    @pytest.mark.asyncio
    async def test_delete_tenant(self, api_client, created_landlord_property: int):
        """
        Tests deletion of a tenant associated with a landlord-owned property and verifies access is forbidden after deletion.
        
        Creates a tenant linked to a specific property, deletes the tenant via the API, asserts successful deletion with status 204, and confirms that subsequent retrieval attempts return a 403 Forbidden status due to row-level security.
        """
        logger.info("Testing DELETE /api/tenants/{id}...")
        property_id = created_landlord_property

        tenant_data = {
            "first_name": "DeleteTest",
            "last_name": "Tenant",
            "email": f"delete_test_{id(self)}_{property_id}@example.com",
            "phone": "+1-555-0789",
            "status": "Active",
            "current_property_id": property_id  # Associate with landlord-owned property
        }

        create_response = await api_client.post("/api/tenants/", json_data=tenant_data)
        tenant = assert_valid_json_response(
            create_response, dict, expected_status=201)
        tenant_id = tenant["id"]

        delete_response = await api_client.delete(f"/api/tenants/{tenant_id}")

        # Expect 204 No Content as tenant should be deletable
        assert_api_success(delete_response, expected_status=204)
        logger.info(f"✅ DELETE /api/tenants/{tenant_id} successful")

        # Verify tenant is no longer accessible (expect 403 due to RLS)
        get_response = await api_client.get(f"/api/tenants/{tenant_id}")
        assert get_response.status_code == 403, f"GETting deleted tenant should return 403 (Forbidden by RLS), got {get_response.status_code}"

    # TODO: Add more tenant tests:
    # - Test tenant creation with invalid data (validation errors)
    # - Test duplicate email handling
    # - Test tenant search/filtering
    # - Test tenant status updates
    # - Test tenant-property associations
