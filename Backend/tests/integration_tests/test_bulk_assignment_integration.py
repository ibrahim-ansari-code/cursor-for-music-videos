"""
Integration tests for bulk unit assignment feature.

Tests both CSV-based and UI-based bulk assignment workflows with proper cleanup.
"""

import logging
import uuid
from collections.abc import AsyncGenerator

import pytest

from Backend.tests.integration_tests.conftest import assert_api_error, assert_valid_json_response

logger = logging.getLogger(__name__)

# Test data constants
UNIT_CONFIGS = [
    {"name": "Unit-A01", "monthly_rent": "1200.00", "bedrooms": 1, "bathrooms": 1.0},
    {"name": "Unit-A02", "monthly_rent": "1350.00", "bedrooms": 2, "bathrooms": 1.0},
    {"name": "Unit-B01", "monthly_rent": "1500.00", "bedrooms": 2, "bathrooms": 2.0},
    {"name": "Unit-B02", "monthly_rent": "1600.00", "bedrooms": 3, "bathrooms": 2.0},
    {"name": "Unit-C01", "monthly_rent": "1800.00", "bedrooms": 3, "bathrooms": 2.5},
]

TENANT_CONFIGS = [
    {
        "first_name": "John",
        "last_name": "BulkTest",
        "phone": "555-001-1001"
    },
    {
        "first_name": "Jane", 
        "last_name": "BulkTest",
        "phone": "555-001-1002"
    },
    {
        "first_name": "BulkTest",
        "last_name": "Corporation",
        "phone": "555-001-1003",
        "tenant_type": "Company",
        "company_name": "BulkTest Corp"
    }
]


# Helper functions
def create_property_data(user_id: str) -> dict:
    """Create test property data."""
    return {
        "name": f"BulkTest_Property_{uuid.uuid4().hex[:8]}",
        "address": "100 Bulk Test Ave",
        "city": "Test City",
        "province": "TS",
        "postal_code": "T1B 2C3",
        "property_type": "Apartment Complex",
        "description": "Property for bulk assignment integration tests",
        "user_id": user_id
    }


def create_unit_data(property_id: int, config: dict) -> dict:
    """Create test unit data."""
    return {
        "property_id": property_id,
        "size": 850.0,
        **config
    }


def create_tenant_data(property_id: int, config: dict) -> dict:
    """Create test tenant data."""
    # Generate safe email prefix handling both individual and company tenants
    if config.get('first_name'):
        email_prefix = config['first_name'].lower()
    elif config.get('company_name'):
        # Use company name for email, replacing spaces and special chars
        email_prefix = config['company_name'].lower().replace(' ', '').replace('-', '')[:20]
    else:
        email_prefix = "tenant"
    
    return {
        "status": "Active", 
        "current_property_id": property_id,
        "email": f"{email_prefix}.bulktest.{uuid.uuid4().hex[:8]}@example.com",
        **config
    }


def create_lease_data(property_id: int, unit_id: int, tenant_id: int) -> dict:
    """Create test lease data."""
    return {
        "property_id": property_id,
        "unit_id": unit_id,
        "tenant_id": tenant_id,
        "start_date": "2025-08-01",
        "end_date": "2026-07-31",
        "monthly_rent": "1200.00",
        "security_deposit": "1200.00",
        "status": "ACTIVE"
    }


async def cleanup_property_and_leases(api_client, property_id: int) -> None:
    """Clean up property and all associated leases."""
    cleanup_errors = []
    
    try:
        # Get and delete all leases for this property
        leases_response = await api_client.get(f"/api/leases/?property_id={property_id}")
        if leases_response.status_code == 200:
            leases = leases_response.json()
            for lease in leases:
                if lease.get("property_id") == property_id:
                    try:
                        delete_response = await api_client.delete(f"/api/leases/{lease['id']}")
                        if delete_response.status_code not in [200, 204, 404]:
                            logger.error(f"Failed to delete lease {lease['id']}: HTTP {delete_response.status_code}")
                            cleanup_errors.append(f"Lease {lease['id']}: HTTP {delete_response.status_code}")
                    except Exception as lease_error:
                        logger.error(f"Error deleting lease {lease['id']}: {lease_error}")
                        cleanup_errors.append(f"Lease {lease['id']}: {str(lease_error)}")
        elif leases_response.status_code != 404:
            logger.error(f"Failed to fetch leases for property {property_id}: HTTP {leases_response.status_code}")
            cleanup_errors.append(f"Lease fetch: HTTP {leases_response.status_code}")
        
        # Delete the property
        try:
            property_response = await api_client.delete(f"/api/properties/{property_id}")
            if property_response.status_code not in [200, 204, 404]:
                logger.error(f"Failed to delete property {property_id}: HTTP {property_response.status_code}")
                cleanup_errors.append(f"Property: HTTP {property_response.status_code}")
        except Exception as property_error:
            logger.error(f"Error deleting property {property_id}: {property_error}")
            cleanup_errors.append(f"Property: {str(property_error)}")
        
    except Exception as e:
        logger.error(f"Critical cleanup failure for property {property_id}: {e}", exc_info=True)
        cleanup_errors.append(f"Critical failure: {str(e)}")
    
    # Log summary of cleanup issues if any occurred
    if cleanup_errors:
        logger.warning(f"Cleanup completed with {len(cleanup_errors)} issues for property {property_id}: {'; '.join(cleanup_errors)}")
    else:
        logger.debug(f"Cleanup completed successfully for property {property_id}")


# Fixtures
@pytest.fixture
async def bulk_test_data(api_client, current_user_id: str) -> AsyncGenerator[dict, None]:
    """Creates complete test data set for bulk assignment tests."""
    # Create property
    property_data = create_property_data(current_user_id)
    response = await api_client.post("/api/properties/", json=property_data)
    property_obj = assert_valid_json_response(response, dict, 201)
    property_id = property_obj["id"]
    
    # Create units
    units = []
    for config in UNIT_CONFIGS:
        unit_data = create_unit_data(property_id, config)
        response = await api_client.post(f"/api/properties/{property_id}/units", json=unit_data)
        unit = assert_valid_json_response(response, dict, 201)
        units.append(unit)
    
    # Create tenants
    tenants = []
    for config in TENANT_CONFIGS:
        tenant_data = create_tenant_data(property_id, config)
        response = await api_client.post("/api/tenants/", json=tenant_data)
        tenant = assert_valid_json_response(response, dict, 201)
        tenants.append(tenant)
    
    yield {
        "property": property_obj,
        "units": units,
        "tenants": tenants
    }
    
    # Cleanup
    await cleanup_property_and_leases(api_client, property_id)


# Test classes
class TestCSVBulkAssignment:
    """Tests for CSV-based bulk assignment functionality."""
    
    async def test_successful_assignment(self, api_client, bulk_test_data):
        """Test successful CSV bulk assignment."""
        data = bulk_test_data
        property_id = data["property"]["id"]
        
        csv_data = {
            "assignments": [
                {
                    "unit_number": data["units"][0]["name"],
                    "tenant_email": data["tenants"][0]["email"],
                    "monthly_rent": "1200.00",
                    "lease_start_date": "2025-08-01"
                },
                {
                    "unit_number": data["units"][1]["name"],
                    "tenant_email": data["tenants"][1]["email"],
                    "monthly_rent": "1350.00",
                    "lease_start_date": "2025-09-01"
                }
            ]
        }
        
        response = await api_client.post(
            f"/api/properties/{property_id}/units/bulk-assign-csv",
            json=csv_data
        )
        
        result = assert_valid_json_response(response, dict, 200)
        
        # Verify results
        assert result["total_rows"] == 2
        assert result["successful_assignments"] == 2
        assert result["failed_assignments"] == 0
        assert len(result["created_leases"]) == 2
        
        # Verify units are rented
        for i in range(2):
            unit_response = await api_client.get(f"/api/units/{data['units'][i]['id']}")
            unit = assert_valid_json_response(unit_response, dict, 200)
            assert unit["is_rented"] is True

    async def test_validation_errors(self, api_client, bulk_test_data):
        """Test CSV bulk assignment with validation errors."""
        data = bulk_test_data
        property_id = data["property"]["id"]
        
        csv_data = {
            "assignments": [
                {
                    "unit_number": "NonExistentUnit",
                    "tenant_email": f"test.{uuid.uuid4().hex[:8]}@example.com",
                    "monthly_rent": "1350.00",
                    "lease_start_date": "2025-08-01"
                }
            ]
        }
        
        response = await api_client.post(
            f"/api/properties/{property_id}/units/bulk-assign-csv",
            json=csv_data
        )
        
        result = assert_valid_json_response(response, dict, 200)
        assert result["successful_assignments"] == 0
        assert result["failed_assignments"] == 1
        assert len(result["errors"]) == 1

    async def test_occupied_units(self, api_client, bulk_test_data):
        """Test CSV bulk assignment with occupied units."""
        data = bulk_test_data
        property_id = data["property"]["id"]
        
        # Create a lease to occupy one unit
        lease_data = create_lease_data(property_id, data["units"][0]["id"], data["tenants"][0]["id"])
        await api_client.post("/api/leases/", json=lease_data)
        
        csv_data = {
            "assignments": [
                {
                    "unit_number": data["units"][0]["name"],
                    "tenant_email": f"different.{uuid.uuid4().hex[:8]}@example.com",
                    "monthly_rent": "1200.00",
                    "lease_start_date": "2025-08-01"
                }
            ]
        }
        
        response = await api_client.post(
            f"/api/properties/{property_id}/units/bulk-assign-csv",
            json=csv_data
        )
        
        result = assert_valid_json_response(response, dict, 200)
        assert result["failed_assignments"] == 1
        assert len(result["errors"]) == 1

    async def test_empty_data(self, api_client, bulk_test_data):
        """Test CSV bulk assignment with empty data."""
        property_id = bulk_test_data["property"]["id"]
        
        response = await api_client.post(
            f"/api/properties/{property_id}/units/bulk-assign-csv",
            json={"assignments": []}
        )
        
        assert_api_error(response, 422, "at least 1 item")

    async def test_invalid_date(self, api_client, bulk_test_data):
        """Test CSV bulk assignment with invalid date."""
        data = bulk_test_data
        property_id = data["property"]["id"]
        
        csv_data = {
            "assignments": [
                {
                    "unit_number": data["units"][0]["name"],
                    "tenant_email": f"test.{uuid.uuid4().hex[:8]}@example.com",
                    "monthly_rent": "1200.00",
                    "lease_start_date": "invalid-date"
                }
            ]
        }
        
        response = await api_client.post(
            f"/api/properties/{property_id}/units/bulk-assign-csv",
            json=csv_data
        )
        
        assert_api_error(response, 422, "invalid")


class TestUIBulkAssignment:
    """Tests for UI-based bulk assignment functionality."""
    
    async def test_successful_assignment(self, api_client, bulk_test_data):
        """Test successful UI bulk assignment."""
        data = bulk_test_data
        property_id = data["property"]["id"]
        
        bulk_data = {
            "unit_ids": [unit["id"] for unit in data["units"][:3]],
            "tenant_id": data["tenants"][0]["id"],
            "lease_start_date": "2025-08-01",
            "end_date": "2026-07-31",
            "security_deposit": "2000.00"
        }
        
        response = await api_client.post("/api/units/bulk-assign", json=bulk_data)
        result = assert_valid_json_response(response, dict, 200)
        
        # Verify results
        assert result["total_units"] == 3
        assert result["successful_assignments"] == 3
        assert result["failed_assignments"] == 0
        assert len(result["created_leases"]) == 3
        
        # Verify leases
        for lease_id in result["created_leases"]:
            lease_response = await api_client.get(f"/api/leases/{lease_id}")
            lease = assert_valid_json_response(lease_response, dict, 200)
            assert lease["tenant_id"] == data["tenants"][0]["id"]
            assert lease["property_id"] == property_id

    async def test_invalid_tenant(self, api_client, bulk_test_data):
        """Test UI bulk assignment with invalid tenant."""
        bulk_data = {
            "unit_ids": [bulk_test_data["units"][0]["id"]],
            "tenant_id": 99999,
            "lease_start_date": "2025-08-01",
            "end_date": "2026-07-31",
            "security_deposit": "1500.00"
        }
        
        response = await api_client.post("/api/units/bulk-assign", json=bulk_data)
        assert_api_error(response, 404, "Tenant with ID")

    async def test_mixed_availability(self, api_client, bulk_test_data):
        """Test UI bulk assignment with mixed unit availability."""
        data = bulk_test_data
        property_id = data["property"]["id"]
        
        # Occupy one unit
        lease_data = create_lease_data(property_id, data["units"][0]["id"], data["tenants"][0]["id"])
        await api_client.post("/api/leases/", json=lease_data)
        
        # Try to assign all three units (including occupied one)
        bulk_data = {
            "unit_ids": [unit["id"] for unit in data["units"][:3]],
            "tenant_id": data["tenants"][1]["id"],
            "lease_start_date": "2025-09-01",
            "end_date": "2026-01-31",
            "security_deposit": "1800.00"
        }
        
        response = await api_client.post("/api/units/bulk-assign", json=bulk_data)
        result = assert_valid_json_response(response, dict, 200)
        
        # Verify mixed results
        assert result["total_units"] == 3
        assert result["successful_assignments"] == 2  # 2 available units
        assert result["failed_assignments"] == 1     # 1 occupied unit
        assert len(result["errors"]) == 1

    async def test_empty_unit_list(self, api_client, bulk_test_data):
        """Test UI bulk assignment with empty unit list."""
        bulk_data = {
            "unit_ids": [],
            "tenant_id": bulk_test_data["tenants"][0]["id"],
            "lease_start_date": "2025-08-01",
            "end_date": "2026-07-31",
            "security_deposit": "1500.00"
        }
        
        response = await api_client.post("/api/units/bulk-assign", json=bulk_data)
        assert_api_error(response, 422, "at least 1 item")


class TestBulkAssignmentValidation:
    """Tests for validation and authorization scenarios."""
    
    async def test_property_ownership(self, api_client):
        """Test CSV bulk assignment requires property ownership."""
        csv_data = {
            "assignments": [
                {
                    "unit_number": "SomeUnit",
                    "tenant_email": f"test.{uuid.uuid4().hex[:8]}@example.com",
                    "monthly_rent": "1200.00",
                    "lease_start_date": "2025-08-01"
                }
            ]
        }
        
        response = await api_client.post(
            "/api/properties/99999/units/bulk-assign-csv",
            json=csv_data
        )
        
        assert_api_error(response, 404, "Property not found")

    async def test_unit_validation(self, api_client):
        """Test UI bulk assignment validates units and tenant."""
        bulk_data = {
            "unit_ids": [99998, 99999],
            "tenant_id": 99999,
            "lease_start_date": "2025-08-01",
            "end_date": "2026-07-31",
            "security_deposit": "1500.00"
        }
        
        response = await api_client.post("/api/units/bulk-assign", json=bulk_data)
        assert_api_error(response, 404, "Tenant with ID")


class TestBulkAssignmentDataIntegrity:
    """Tests for data integrity and consistency."""
    
    async def test_lease_creation_consistency(self, api_client, bulk_test_data):
        """Test that bulk assignment creates consistent lease data."""
        data = bulk_test_data
        property_id = data["property"]["id"]
        
        csv_data = {
            "assignments": [
                {
                    "unit_number": data["units"][0]["name"],
                    "tenant_email": data["tenants"][0]["email"],
                    "monthly_rent": "1200.00",
                    "lease_start_date": "2025-08-01"
                }
            ]
        }
        
        response = await api_client.post(
            f"/api/properties/{property_id}/units/bulk-assign-csv",
            json=csv_data
        )
        
        result = assert_valid_json_response(response, dict, 200)
        assert result["successful_assignments"] == 1
        
        # Verify lease details
        lease_id = result["created_leases"][0]
        lease_response = await api_client.get(f"/api/leases/{lease_id}")
        lease = assert_valid_json_response(lease_response, dict, 200)
        
        assert lease["property_id"] == property_id
        assert lease["unit_id"] == data["units"][0]["id"]
        assert lease["tenant_id"] == data["tenants"][0]["id"]
        assert str(lease["monthly_rent"]) == "1200.00"
        assert lease["status"] == "ACTIVE"

    async def test_tenant_property_assignment(self, api_client, bulk_test_data):
        """Test that bulk assignment updates tenant's current property."""
        data = bulk_test_data
        property_id = data["property"]["id"]
        
        bulk_data = {
            "unit_ids": [data["units"][1]["id"]],
            "tenant_id": data["tenants"][1]["id"],
            "lease_start_date": "2025-08-01",
            "end_date": "2026-07-31",
            "security_deposit": "1350.00"
        }
        
        response = await api_client.post("/api/units/bulk-assign", json=bulk_data)
        result = assert_valid_json_response(response, dict, 200)
        assert result["successful_assignments"] == 1
        
        # Verify tenant's current property was updated
        tenant_response = await api_client.get(f"/api/tenants/{data['tenants'][1]['id']}")
        tenant = assert_valid_json_response(tenant_response, dict, 200)
        assert tenant["current_property_id"] == property_id


# Test markers
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.slow
]