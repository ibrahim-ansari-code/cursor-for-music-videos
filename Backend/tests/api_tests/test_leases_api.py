"""
API tests for Lease management operations.
"""

import pytest
import logging

# Import helper functions from conftest.py explicitly for clarity
from .conftest import assert_valid_json_response

logger = logging.getLogger(__name__)

@pytest.mark.auth
@pytest.mark.integration
class TestLeasesAPI:
    """Test suite for Leases API endpoints"""

    @pytest.mark.asyncio
    async def test_lease_get_operations(self, api_client):
        """Test GET /api/leases/ operations"""
        logger.info("Testing GET /api/leases/...")
        
        # Test basic lease listing
        response = await api_client.get("/api/leases/")
        leases = assert_valid_json_response(response, list)
        
        logger.info(f"✅ GET /api/leases/ successful, returned {len(leases)} leases")
        
        # If we have leases, test individual lease retrieval
        if leases:
            lease_id = leases[0]["id"]
            
            # Test getting specific lease
            logger.info(f"Testing GET /api/leases/{lease_id}...")
            specific_response = await api_client.get(f"/api/leases/{lease_id}")
            lease_detail = assert_valid_json_response(specific_response, dict)
            
            # Verify lease detail contains expected fields
            assert lease_detail["id"] == lease_id
            assert "tenant_id" in lease_detail
            assert "property_id" in lease_detail
            assert "start_date" in lease_detail
            assert "end_date" in lease_detail
            
            logger.info(f"✅ GET /api/leases/{lease_id} successful")
            
            # Test lease documents endpoint
            logger.info(f"Testing GET /api/leases/{lease_id}/documents...")
            docs_response = await api_client.get(f"/api/leases/{lease_id}/documents")
            documents = assert_valid_json_response(docs_response, list)
            
            logger.info(f"✅ GET /api/leases/{lease_id}/documents successful, returned {len(documents)} documents")
        
        # Test lease filtering
        logger.info("Testing GET /api/leases/ with status filter...")
        filtered_response = await api_client.get("/api/leases/", params={"status": "ACTIVE"})
        filtered_leases = assert_valid_json_response(filtered_response, list)
        
        logger.info(f"✅ GET /api/leases/ with status filter successful, returned {len(filtered_leases)} active leases")

    # Commented out the complex create/manage test as it requires proper test data setup
    # @pytest.mark.asyncio
    # async def test_create_and_manage_lease(self, api_client, created_property, created_tenant):
    #     """Test creating and managing a lease (requires fixtures for property and tenant)"""
    #     logger.info("Testing lease creation and management...")
    #     
    #     # This test would require:
    #     # 1. A valid property_id (from created_property fixture)
    #     # 2. A valid tenant_id (from created_tenant fixture)
    #     # 3. Proper lease data structure
    #     
    #     lease_data = {
    #         "tenant_id": created_tenant["id"],
    #         "property_id": created_property["id"],
    #         "start_date": "2024-01-01",
    #         "end_date": "2024-12-31",
    #         "monthly_rent": 1500.00,
    #         "security_deposit": 1500.00,
    #         "status": "active"
    #     }
    #     
    #     # Create lease
    #     create_response = await api_client.post("/api/leases", json_data=lease_data)
    #     lease = assert_valid_json_response(create_response, dict)
    #     
    #     logger.info(f"✅ Created lease {lease['id']}")
    #     
    #     # Test lease validation
    #     validate_response = await api_client.post(f"/api/leases/{lease['id']}/validate")
    #     assert_api_success(validate_response)
    #     
    #     # Test lease status update
    #     status_response = await api_client.post(
    #         f"/api/leases/{lease['id']}/status", 
    #         json_data={"status": "pending"}
    #     )
    #     assert_api_success(status_response)
    #     
    #     # Cleanup
    #     await api_client.delete(f"/api/leases/{lease['id']}")
    #     logger.info(f"✅ Cleaned up lease {lease['id']}")

    # TODO: Add more lease tests when proper fixtures are available:
    # - Test lease creation with valid property and tenant
    # - Test lease validation endpoint
    # - Test lease status updates
    # - Test lease document upload
    # - Test lease parsing functionality
    # - Test lease filtering by property, tenant, status
    # - Test error cases (invalid tenant/property IDs, date conflicts)
