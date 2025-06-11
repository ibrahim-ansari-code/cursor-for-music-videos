"""
API tests for Tenant management operations.
Covers creation, retrieval, updates, deletion, and validation scenarios.
"""

import pytest
import logging
import uuid
import httpx

from .conftest import assert_api_success, assert_valid_json_response, assert_api_error

logger = logging.getLogger(__name__)

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_tenant(api_client: httpx.AsyncClient, created_landlord_property: int):
    """
    Tests creation of a new tenant with valid data.
    """
    logger.info("Testing POST /api/tenants/...")
    property_id = created_landlord_property
    unique_email = f"create_test_{uuid.uuid4()}@example.com"

    tenant_data = {
        "first_name": "CreateTest",
        "last_name": "Tenant",
        "email": unique_email,
        "phone": "123-456-7890",
        "status": "Active",
        "current_property_id": property_id
    }

    response = await api_client.post("/api/tenants/", json=tenant_data)
    data = assert_valid_json_response(response, dict, 201)
    
    assert data["email"] == unique_email.lower()
    assert data["first_name"] == "CreateTest"
    
    tenant_id = data["id"]
    delete_response = await api_client.delete(f"/api/tenants/{tenant_id}")
    assert_api_success(delete_response, (204, 404))

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_all_tenants(api_client: httpx.AsyncClient, created_tenant: dict):
    """
    Retrieves all tenants and verifies the created tenant is present.
    """
    logger.info("Testing GET /api/tenants/...")
    response = await api_client.get("/api/tenants/")
    tenants = assert_valid_json_response(response, list)
    
    assert any(t['id'] == created_tenant['id'] for t in tenants)
    logger.info(f"✅ GET /api/tenants/ successful, returned {len(tenants)} tenants")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_unassigned_tenants(api_client: httpx.AsyncClient, created_tenant: dict, created_lease: dict):
    """
    Tests that the `unassigned_only=true` filter works correctly.
    """
    logger.info("Testing GET /api/tenants/?unassigned_only=true...")
    unassigned_tenant_data = {
        "first_name": "Unassigned", "last_name": "Tester",
        "email": f"unassigned_{uuid.uuid4()}@example.com", "phone": "1112223333"
    }
    create_res = await api_client.post("/api/tenants/", json=unassigned_tenant_data)
    unassigned_tenant = assert_valid_json_response(create_res, dict, 201)

    response = await api_client.get("/api/tenants/", params={"unassigned_only": "true"})
    unassigned_tenants = assert_valid_json_response(response, list)

    assert not any(t['id'] == created_tenant['id'] for t in unassigned_tenants)
    assert any(t['id'] == unassigned_tenant['id'] for t in unassigned_tenants)
    logger.info("✅ Correctly filtered for unassigned tenants.")

    await api_client.delete(f"/api/tenants/{unassigned_tenant['id']}")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_specific_tenant(created_tenant: dict, api_client: httpx.AsyncClient):
    """
    Retrieves a specific tenant by ID.
    """
    logger.info("Testing GET /api/tenants/{id}...")
    tenant_id = created_tenant["id"]
    response = await api_client.get(f"/api/tenants/{tenant_id}")
    
    tenant = assert_valid_json_response(response, dict)
    assert tenant["id"] == tenant_id
    assert tenant["first_name"] == created_tenant["first_name"]
    logger.info(f"✅ GET /api/tenants/{tenant_id} successful")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_tenant(created_tenant: dict, api_client: httpx.AsyncClient):
    """
    Tests that a tenant's information can be updated.
    """
    logger.info("Testing PATCH /api/tenants/{id}...")
    tenant_id = created_tenant["id"]
    update_data = {"first_name": "UpdatedName", "phone": "987-654-3210"}

    response = await api_client.patch(f"/api/tenants/{tenant_id}", json=update_data)
    
    updated_tenant = assert_valid_json_response(response, dict)
    assert updated_tenant["first_name"] == "UpdatedName"
    assert updated_tenant["phone"] == "987-654-3210"
    assert updated_tenant["id"] == tenant_id
    logger.info(f"✅ PATCH /api/tenants/{tenant_id} successful")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_tenant_with_active_lease_fails(api_client: httpx.AsyncClient, created_lease: dict):
    """
    Verifies that deleting a tenant with an active lease fails.
    """
    logger.info("Testing DELETE /api/tenants/{id} with active lease...")
    tenant_id = created_lease['tenant_id']
    
    delete_response = await api_client.delete(f"/api/tenants/{tenant_id}")
    assert_api_error(delete_response, 400, "Cannot delete tenant with active leases")
    logger.info("✅ Correctly prevented deletion of tenant with active lease.")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_tenant_duplicate_email(created_tenant: dict, api_client: httpx.AsyncClient):
    """
    Tests that creating a tenant with a duplicate email fails.
    """
    logger.info("Testing tenant creation with duplicate email (409 Conflict)...")
    tenant_data = {
        "first_name": "Duplicate", "last_name": "Email", "phone": "111-222-3333",
        "email": created_tenant['email'],
    }
    response = await api_client.post("/api/tenants/", json=tenant_data)
    assert_api_error(response, 409, "A tenant with this email address already exists.")
    logger.info("✅ Correctly received 409 for duplicate email")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_tenant_case_insensitive_email(created_tenant: dict, api_client: httpx.AsyncClient):
    """
    Verifies case-insensitive uniqueness for tenant emails.
    """
    logger.info("Testing case-insensitive duplicate email check...")
    tenant_data = {
        "first_name": "Case", "last_name": "Sensitive", "phone": "111-222-4444",
        "email": created_tenant['email'].upper(),
    }
    response = await api_client.post("/api/tenants/", json=tenant_data)
    assert_api_error(response, 409, "A tenant with this email address already exists.")
    logger.info("✅ Correctly received 409 for case-insensitive duplicate email")

@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_phone", ["not-a-phone", "12345", "1234567890123456", "aaaaaaaaaa1234567890"])
async def test_create_tenant_invalid_phone(api_client: httpx.AsyncClient, invalid_phone: str):
    """
    Tests that tenant creation fails with an invalid phone number.
    """
    logger.info(f"Testing invalid phone number: {invalid_phone}")
    tenant_data = {
        "first_name": "Invalid", "last_name": "Phone", "phone": invalid_phone,
        "email": f"invalid_phone_{uuid.uuid4()}@example.com",
    }
    response = await api_client.post("/api/tenants/", json=tenant_data)
    assert_api_error(response, 422, "phone number")
    logger.info(f"✅ Correctly received 422 for invalid phone number '{invalid_phone}'")
    
@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_field, value, error_part", [
    ("first_name", "", "cannot be empty"),
    ("last_name", "  ", "cannot be empty"),
    ("email", "not-an-email", "Invalid email format"),
    ("email", "", "is required"),
])
async def test_create_tenant_validation_errors(api_client: httpx.AsyncClient, invalid_field: str, value: str, error_part: str):
    """
    Tests tenant creation with various invalid field values.
    """
    logger.info(f"Testing validation for field '{invalid_field}' with value '{value}'")
    tenant_data = {
        "first_name": "ValidName", "last_name": "ValidLastName", 
        "email": "valid@example.com", "phone": "1234567890"
    }
    tenant_data[invalid_field] = value
    response = await api_client.post("/api/tenants/", json=tenant_data)
    assert_api_error(response, 422)
    
    error_detail = response.json().get("detail", "")
    assert error_part in str(error_detail).lower()
    logger.info(f"✅ Correctly received validation error for {invalid_field}")
