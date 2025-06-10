"""
API tests for Lease management operations, including creation, status changes, and side effects.
"""

import pytest
import logging
from .conftest import assert_valid_json_response, assert_api_error, APITestClient

logger = logging.getLogger(__name__)


@pytest.mark.auth
@pytest.mark.integration
class TestLeasesAPI:
    """Test suite for Leases API endpoints"""

    @pytest.mark.asyncio
    async def test_create_active_lease_and_verify_side_effects(self, api_client: APITestClient, created_landlord_property: int, created_unit: dict, created_tenant: dict):
        """
        Creates an ACTIVE lease and verifies that related tenant and unit records are updated accordingly.
        
        This test ensures that upon lease creation, the tenant's `current_property_id` is set to the lease's property, and the unit's `is_rented`, `tenant_id`, and `monthly_rent` fields reflect the new lease. The created lease is deleted at the end of the test.
        """
        logger.info("Testing POST /api/leases/ and side effects...")
        
        lease_data = {
            "property_id": created_landlord_property,
            "unit_id": created_unit["id"],
            "tenant_id": created_tenant["id"],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "monthly_rent": 1600.00,
            "security_deposit": 1600.00,
            "status": "ACTIVE" 
        }

        # Create the lease
        create_response = await api_client.post("/api/leases/", json=lease_data)
        lease = assert_valid_json_response(create_response, dict, 201)
        assert lease["status"] == "ACTIVE"

        # --- Verification ---
        # 1. Verify tenant's current_property_id is set
        tenant_response = await api_client.get(f"/api/tenants/{created_tenant['id']}")
        tenant = assert_valid_json_response(tenant_response, dict)
        assert tenant['current_property_id'] == created_landlord_property
        logger.info(f"✅ Tenant {tenant['id']} correctly assigned to property {tenant['current_property_id']}")

        # 2. Verify unit is updated
        unit_response = await api_client.get(f"/api/units/{created_unit['id']}")
        unit = assert_valid_json_response(unit_response, dict)
        assert unit['is_rented'] is True
        assert unit['tenant_id'] == created_tenant['id']
        assert unit['monthly_rent'] == lease_data['monthly_rent']
        logger.info(f"✅ Unit {unit['id']} correctly marked as rented by tenant {unit['tenant_id']}")

        # Cleanup will be handled by fixtures
        await api_client.delete(f"/api/leases/{lease['id']}")


    @pytest.mark.asyncio
    async def test_update_lease_status_and_verify_side_effects_revoked(self, api_client: APITestClient, created_lease: dict):
        """
        Updates a lease status from ACTIVE to EXPIRED and verifies that related side effects are revoked.
        
        This test ensures that when a lease is marked as EXPIRED, the associated unit is set as not rented with its tenant assignment cleared, and the tenant's current property association is removed.
        """
        logger.info("Testing lease status update and side-effect revocation...")
        lease_id = created_lease['id']
        unit_id = created_lease['unit_id']
        tenant_id = created_lease['tenant_id']

        # --- Verification Step 1: Ensure initial state is correct ---
        initial_unit_res = await api_client.get(f"/api/units/{unit_id}")
        initial_unit = assert_valid_json_response(initial_unit_res, dict)
        assert initial_unit['is_rented'] is True
        assert initial_unit['tenant_id'] == tenant_id

        # --- Update lease status to EXPIRED ---
        status_update_data = {"status": "EXPIRED"}
        update_response = await api_client.post(f"/api/leases/{lease_id}/status", json=status_update_data)
        updated_lease = assert_valid_json_response(update_response, dict)
        assert updated_lease['status'] == 'EXPIRED'
        logger.info(f"✅ Lease {lease_id} status updated to EXPIRED")

        # --- Verification Step 2: Check side effects are revoked ---
        # 1. Verify unit is now vacant
        final_unit_res = await api_client.get(f"/api/units/{unit_id}")
        final_unit = assert_valid_json_response(final_unit_res, dict)
        assert final_unit['is_rented'] is False
        assert final_unit['tenant_id'] is None
        logger.info(f"✅ Unit {unit_id} correctly marked as vacant.")

        # 2. Verify tenant's current_property_id is cleared
        final_tenant_res = await api_client.get(f"/api/tenants/{tenant_id}")
        final_tenant = assert_valid_json_response(final_tenant_res, dict)
        assert final_tenant['current_property_id'] is None
        logger.info(f"✅ Tenant {tenant_id} current_property_id correctly cleared.")


    @pytest.mark.asyncio
    async def test_create_lease_with_invalid_data(self, api_client: APITestClient, created_landlord_property: int, created_tenant: dict):
        """
        Verifies that lease creation fails with invalid tenant or property IDs.
        
        Attempts to create leases using a non-existent tenant and a non-existent property, asserting that the API returns 400 errors with appropriate messages for each invalid case.
        """
        logger.info("Testing lease creation with invalid data...")

        # Test with non-existent tenant
        invalid_tenant_data = {
            "property_id": created_landlord_property, "tenant_id": 999999,
            "start_date": "2024-01-01", "end_date": "2024-12-31", "monthly_rent": 1000, "security_deposit": 1000
        }
        response = await api_client.post("/api/leases/", json=invalid_tenant_data)
        assert_api_error(response, 400, "Invalid tenant ID")

        # Test with non-existent property
        invalid_property_data = {
            "property_id": 999999, "tenant_id": created_tenant["id"],
            "start_date": "2024-01-01", "end_date": "2024-12-31", "monthly_rent": 1000, "security_deposit": 1000
        }
        response = await api_client.post("/api/leases/", json=invalid_property_data)
        assert_api_error(response, 400, "Invalid property ID")
        
        logger.info("✅ Correctly handled invalid data on lease creation.")

    @pytest.mark.asyncio
    async def test_lease_get_operations(self, api_client: APITestClient) -> None:
        """
        Tests lease-related GET API endpoints for listing, retrieving, and filtering leases.
        
        This test verifies that the API correctly returns all leases, retrieves individual lease details with expected fields, fetches associated documents, and filters leases by status. Assertions confirm the structure and types of the returned data.
        """
        logger.info("Testing GET /api/leases/...")

        # Test basic lease listing
        response = await api_client.get("/api/leases/")
        leases = assert_valid_json_response(response, list)

        logger.info(
            "✅ GET /api/leases/ successful, returned %d leases", len(leases))

        # If we have leases, test individual lease retrieval
        if leases:
            lease_id = leases[0]["id"]

            # Test getting specific lease
            logger.info("Testing GET /api/leases/%s...", lease_id)
            specific_response = await api_client.get(f"/api/leases/{lease_id}")
            lease_detail = assert_valid_json_response(specific_response, dict)

# Verify lease detail contains expected fields
            assert lease_detail["id"] == lease_id
            assert isinstance(lease_detail["tenant_id"], (int, type(None)))
            assert isinstance(lease_detail["property_id"], (int, type(None)))
            assert "tenant_id" in lease_detail
            assert "property_id" in lease_detail
            assert "start_date" in lease_detail
            assert "end_date" in lease_detail

            logger.info("✅ GET /api/leases/%s successful", lease_id)

            # Test lease documents endpoint
            logger.info("Testing GET /api/leases/%s/documents...", lease_id)
            docs_response = await api_client.get(f"/api/leases/{lease_id}/documents")
            documents = assert_valid_json_response(docs_response, list)

            logger.info(
                "✅ GET /api/leases/%s/documents successful, returned %d documents", lease_id, len(documents))

        # Test lease filtering
        logger.info("Testing GET /api/leases/ with status filter...")
        filtered_response = await api_client.get("/api/leases/", params={"status": "ACTIVE"})
        filtered_leases = assert_valid_json_response(filtered_response, list)

        logger.info(
            "✅ GET /api/leases/ with status filter successful, returned %d active leases", len(filtered_leases))

    # TODO: Add more lease tests when proper fixtures are available:
    # - Test lease creation with valid property and tenant
    # - Test lease validation endpoint
    # - Test lease status updates
    # - Test lease document upload
    # - Test lease parsing functionality
    # - Test lease filtering by property, tenant, status
    # - Test error cases (invalid tenant/property IDs, date conflicts)
