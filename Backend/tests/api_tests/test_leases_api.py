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
