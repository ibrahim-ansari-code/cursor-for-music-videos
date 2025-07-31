"""
Shared pytest fixtures for Integration tests.

This conftest.py provides specialized fixtures for integration testing.
Basic Python path setup and environment loading is handled by the parent conftest.py
"""

import inspect
import asyncio
import os
import sys
import logging
import pytest
import httpx
import json
from collections.abc import Iterator, AsyncGenerator
from typing import Any, Callable, Coroutine
import time
import uuid
from datetime import datetime, timedelta, UTC

logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Import authentication helper
get_test_jwt: Callable[[bool], Coroutine[Any, Any, str | None]] | None
try:
    from Backend.tests.integration_tests.test_auth_helper import get_test_jwt
except ImportError:
    logger.warning("Failed to import get_test_jwt from test_auth_helper")
    get_test_jwt = None


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """
    Provides a session-scoped asyncio event loop for pytest tests.
    
    On Windows, sets a compatible event loop policy for stability. Closes the event loop after the test session.
    """
    # Set Windows-compatible event loop policy for better stability
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.info("Set Windows SelectorEventLoopPolicy for compatibility")

    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def shared_auth_token(event_loop) -> str:
    """
    Obtains a valid JWT token to be shared across all tests in the session.
    
    Returns:
        The JWT token string for authenticating API requests during the test session.
    
    Exits pytest if token retrieval fails.
    """
    from Backend.tests.shared_auth_utils import get_primary_user_jwt
    logger.info("SHARED_AUTH_TOKEN FIXTURE: Requesting single JWT for test session...")
    token = await get_primary_user_jwt(prompt_for_password=False) # CI should use env vars
    if not token:
        pytest.exit("Failed to get a valid auth token for the test session. Aborting.", returncode=1)
    
    logger.info("SHARED_AUTH_TOKEN FIXTURE: Successfully obtained shared JWT.")
    return token


@pytest.fixture(scope="function")
async def current_user_id(shared_auth_token: str) -> str:
    """
    Retrieves the current user's ID at the beginning of the session.
    """
    headers = {"Authorization": f"Bearer {shared_auth_token}"}
    timeout = httpx.Timeout(30.0, connect=5.0)
    async with httpx.AsyncClient(
        base_url=BASE_URL, headers=headers, timeout=timeout
    ) as client:
        response = await client.get("/api/auth/me")
        if response.status_code != 200:
            pytest.exit("Could not retrieve current user details. Aborting.", returncode=1)
        user_data = response.json()
        if not user_data.get("id"):
             pytest.exit("User ID not found in /api/auth/me response. Aborting.", returncode=1)
        return user_data["id"]


@pytest.fixture(scope="function")
async def api_client(shared_auth_token: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Yields an authenticated httpx.AsyncClient using a session-scoped token.
    """
    headers = {
        "Authorization": f"Bearer {shared_auth_token}",
        "Content-Type": "application/json"
    }
    timeout = httpx.Timeout(30.0, connect=5.0)  # 30-second timeout for all operations
    async with httpx.AsyncClient(base_url=BASE_URL, headers=headers, timeout=timeout) as client:
        yield client


# This is a simplified version for tests that don't need the user context
@pytest.fixture(scope="function")
async def fresh_api_client(shared_auth_token: str) -> AsyncGenerator[httpx.AsyncClient, None]:
     headers = {
        "Authorization": f"Bearer {shared_auth_token}",
        "Content-Type": "application/json"
    }
     timeout = httpx.Timeout(30.0, connect=5.0)
     async with httpx.AsyncClient(base_url=BASE_URL, headers=headers, timeout=timeout) as client:
        yield client


@pytest.fixture(scope="function")
async def created_landlord_property(api_client: httpx.AsyncClient, current_user_id: str) -> AsyncGenerator[int, None]:
    """
    Creates a test property for the authenticated user and yields its ID.
    
    Posts a new property to the API as the current user, yields the created property's ID for use in tests, and ensures the property is deleted after the test completes. Aborts the test session if the user is not authenticated or property creation fails.
    """
    property_name = f"TestProp_Landlord_{current_user_id[:8]}_{int(time.time())}"

    property_data = {
        "name": property_name,
        "address": "123 Test St",
        "city": "Testville",
        "province": "TS",
        "postal_code": "T3S T3S",
        "property_type": "Residential",
        "user_id": current_user_id
    }

    response = await api_client.post("/api/properties/", json=property_data)

    if response.status_code != 201:
        error_message = f"Failed to create landlord property: {response.status_code} - {response.text[:200]}"
        logger.error(error_message)
        pytest.fail(error_message)

    created_property = response.json()
    property_id = created_property["id"]
    logger.info(
        "✅ Landlord property created: ID %s, Name: %s", property_id, property_name)

    yield property_id

    # Cleanup
    logger.info(
        "[CLEANUP START] Attempting to delete landlord property: ID %s", property_id)
    try:
        delete_response = await api_client.delete(f"/api/properties/{property_id}")
        if delete_response.status_code == 204:
            logger.info(
                "✅ Fixture cleanup: deleted landlord property %s", property_id)
        elif delete_response.status_code == 404:
            logger.info(
                "✅ Fixture cleanup: landlord property %s already deleted.", property_id)
        else:
            logger.error(
                "❌ Fixture cleanup failed for landlord property %s: DELETE returned %s - %s",
                property_id, delete_response.status_code, delete_response.text[:200])
    except Exception:
        logger.exception(
            "❌ Fixture cleanup exception for landlord property %s", property_id)
    logger.info(
        "[CLEANUP END] Finished attempt to delete landlord property: ID %s", property_id)


@pytest.fixture(autouse=True)
def configure_logging():
    """
    Configures logging with a consistent format and INFO level before each test.
    
    This fixture is automatically used to ensure all test logs have timestamps and standardized formatting.
    """
    # This runs before each test to ensure consistent logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


# Custom markers for better test organization
pytestmark = [
    pytest.mark.asyncio,  # All tests in api_tests are async
]


def pytest_configure(config):
    """
    Registers custom pytest markers for authentication, slow, and integration tests.
    
    Adds the 'auth', 'slow', and 'integration' markers to the pytest configuration, allowing these markers to be used in test files for categorizing tests.
    """
    # Add custom markers
    config.addinivalue_line(
        "markers", "auth: mark test as requiring authentication")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(config, items):
    """
    Automatically adds the 'auth' marker to tests using API client fixtures.
    
    Tests that use the 'api_client' fixture are marked as requiring authentication.
    """
    for item in items:
        if "api_client" in item.fixturenames:
            item.add_marker(pytest.mark.auth)


# Import helper functions from shared module
from Backend.tests.shared_fixtures import (
    assert_api_success,
    assert_api_error,
    assert_valid_json_response,
)

# Re-export for backward compatibility
__all__ = [
    'assert_api_success',
    'assert_api_error',
    'assert_valid_json_response',
    'shared_auth_token',
    'api_client',
    'current_user_id',
    'created_landlord_property',
    'cleanup_test_data',
]


async def cleanup_test_data(api_client: httpx.AsyncClient):
    """
    Deletes test tenants and properties created during testing that match specific naming or email patterns.
    
    Identifies and removes tenants and properties used for tests, skipping protected accounts. Logs the outcome of each deletion attempt and handles network or request errors gracefully.
    """
    logger.info("🧹 Starting test data cleanup...")

    try:
        # Get all test tenants
        response = await api_client.get("/api/tenants/")
        if response.status_code == 200:
            tenants = response.json()
            test_tenants = [
                t for t in tenants
                if (
                    (t.get('first_name', '').startswith(('Test', 'CreateTest', 'UpdateTest', 'DeleteTest')) or
                     t.get('email', '').endswith('@example.com') or
                     'test' in t.get('email', '').lower()) and
                    # Don't delete production test user
                    t.get('email') != 'test@gmail.com'
                )
            ]

            for tenant in test_tenants:
                try:
                    delete_response = await api_client.delete(f"/api/tenants/{tenant['id']}")
                    if delete_response.status_code == 204:
                        logger.info(
                            f"✅ Cleaned up test tenant {tenant['id']} ({tenant.get('email')})")
                    elif delete_response.status_code == 403:
                        logger.info(
                            f"⚠️ Test tenant {tenant['id']} cleanup blocked by RLS (expected)")
                    else:
                        logger.warning(
                            f"⚠️ Test tenant {tenant['id']} cleanup returned {delete_response.status_code}")
                except httpx.RequestError as exc:
                    logger.warning(
                        f"⚠️ Failed to cleanup test tenant {tenant['id']} due to network/request error: {exc}")
                except Exception:
                    logger.exception(
                        f"⚠️ Failed to cleanup test tenant {tenant['id']}:")

        # Get all test properties
        response = await api_client.get("/api/properties/")
        if response.status_code == 200:
            properties = response.json()
            test_properties = [
                p for p in properties
                if p.get('name', '').startswith(('Test', 'CreateTest', 'UpdateTest', 'DeleteTest'))
            ]

            for prop in test_properties:
                try:
                    delete_response = await api_client.delete(f"/api/properties/{prop['id']}")
                    if delete_response.status_code == 204:
                        logger.info(
                            f"✅ Cleaned up test property {prop['id']} ({prop.get('name')})")
                    else:
                        logger.warning(
                            f"⚠️ Test property {prop['id']} cleanup returned {delete_response.status_code}")
                except httpx.RequestError as exc:
                    logger.warning(
                        f"⚠️ Failed to cleanup test property {prop['id']} due to network/request error: {exc}")
                except Exception:
                    logger.exception(
                        f"⚠️ Failed to cleanup test property {prop['id']}:")

    except httpx.RequestError as exc:
        logger.warning(
            f"⚠️ Global test data cleanup failed due to network/request error: {exc}")
    except Exception:
        logger.exception("⚠️ Global test data cleanup failed:")


@pytest.fixture(scope="session", autouse=True)
async def session_cleanup(shared_auth_token: str):
    """
    Performs a final cleanup of test data after all tests in the session have completed.
    
    This session-scoped, autouse fixture ensures that any orphaned test tenants and properties created during testing are deleted from the database at the end of the test session.
    """
    # This part of the fixture does nothing and yields control to the tests.
    yield

    # This part runs after all tests in the session have completed.
    logger.info("---" * 10)
    logger.info("🏁 FINAL SESSION CLEANUP: Deleting all test data...")
    logger.info("---" * 10)

    headers = {
        "Authorization": f"Bearer {shared_auth_token}",
        "Content-Type": "application/json"
    }
    timeout = httpx.Timeout(60.0, connect=10.0)
    
    async with httpx.AsyncClient(base_url=BASE_URL, headers=headers, timeout=timeout) as client:
        await cleanup_test_data(client)
    
    logger.info("---" * 10)
    logger.info("✅ FINAL SESSION CLEANUP COMPLETE.")
    logger.info("---" * 10)


@pytest.fixture
async def created_property_id(api_client: httpx.AsyncClient) -> AsyncGenerator[int, None]:
    """
    Creates a test property and yields its ID for use in tests.
    
    After the test completes, deletes the created property to ensure cleanup.
    
    Yields:
        The ID of the created test property.
    """
    property_data = {
        "name": f"Test Property {int(time.time())}",
        "address": "123 Test St",
        "city": "Testville",
        "province": "TS",
        "postal_code": "T5T5T5",
        "property_type": "Apartment"
    }
    response = await api_client.post("/api/properties/", json=property_data)
    assert response.status_code == 201
    property_obj = response.json()
    property_id = property_obj["id"]

    yield property_id

    # Cleanup
    delete_response = await api_client.delete(f"/api/properties/{property_id}")
    assert delete_response.status_code in [204, 404]


@pytest.fixture
async def created_property(api_client: httpx.AsyncClient) -> AsyncGenerator[dict[str, Any], None]:
    """
    Creates a test property for use in API tests and deletes it after the test completes.
    
    Yields:
        dict: The created property's data as a dictionary.
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
    property_obj = assert_valid_json_response(response, dict, 201)

    yield property_obj

    # Cleanup
    try:
        delete_response = await api_client.delete(f"/api/properties/{property_obj['id']}")
        if delete_response.status_code in [204, 404]:
            logger.info("✅ Fixture cleanup: deleted property %s", property_obj['id'])
        else:
            logger.error("❌ Fixture cleanup failed for property: DELETE returned %s", delete_response.status_code)
    except Exception:
        logger.exception("❌ Fixture cleanup exception for property:")


@pytest.fixture
async def created_unit(api_client: httpx.AsyncClient, created_landlord_property: int) -> AsyncGenerator[dict[str, Any], None]:
    """
    Creates a test unit associated with a specified property and yields its data.
    
    The unit is created with randomized name and default attributes. After the test completes, the unit is deleted to ensure cleanup.
    
    Yields:
        dict: The created unit's data as returned by the API.
    """
    unit_data = {
        "name": f"Unit-{uuid.uuid4().hex[:6]}",
        "property_id": created_landlord_property,
        "monthly_rent": "1250.00",
        "size": 800
    }
    response = await api_client.post(f"/api/properties/{created_landlord_property}/units", json=unit_data)
    unit = assert_valid_json_response(response, dict, 201)
    yield unit
    # Cleanup
    await api_client.delete(f"/api/units/{unit['id']}")


@pytest.fixture
async def created_tenant(api_client: httpx.AsyncClient, created_landlord_property: int) -> AsyncGenerator[dict[str, Any], None]:
    """
    Creates a test tenant linked to a landlord property for use in API tests.
    
    Yields:
        The created tenant as a dictionary. After the test, attempts to delete the tenant; deletion failures due to existing leases (HTTP 400) are tolerated and logged.
    """
    tenant_data = {
        "first_name": "Fixture",
        "last_name": "Tenant",
        "email": f"fixture_tenant_{uuid.uuid4()}@example.com",
        "phone": "555-123-4567",
        "status": "Active",
        "current_property_id": created_landlord_property
    }
    response = await api_client.post("/api/tenants/", json=tenant_data)
    tenant = assert_valid_json_response(response, dict, 201)
    yield tenant
    # Cleanup - tenant deletion may fail with 400 if tied to a lease, which is acceptable during cleanup.
    logger.info("[CLEANUP] Deleting tenant fixture: ID %s", tenant['id'])
    try:
        delete_response = await api_client.delete(f"/api/tenants/{tenant['id']}")
        if delete_response.status_code not in [204, 404, 400]:
            logger.warning("Tenant fixture cleanup for ID %s failed. Status: %s", tenant['id'], delete_response.status_code)
        else:
            logger.info("Tenant fixture cleanup for ID %s successful (Status: %s)", tenant['id'], delete_response.status_code)
    except Exception:
        logger.exception("Error during tenant fixture %s cleanup", tenant['id'])


@pytest.fixture
async def created_lease(api_client: httpx.AsyncClient, created_landlord_property: int, created_unit: dict, created_tenant: dict) -> AsyncGenerator[dict[str, Any], None]:
    """
    Creates a test lease linking a property, unit, and tenant, and yields the lease data.
    
    The lease is created with fixed start and end dates, rent, and deposit values for testing. After yielding the lease dictionary, the fixture attempts to delete the lease to ensure test data cleanup.
    
    Yields:
        dict: The created lease object.
    """
    start_date = datetime.now(UTC) - timedelta(days=30)
    end_date = datetime.now(UTC) + timedelta(days=365)

    lease_data = {
        "property_id": created_landlord_property,
        "unit_id": created_unit["id"],
        "tenant_id": created_tenant["id"],
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "monthly_rent": "1550.00",
        "security_deposit": "1550.00",
        "status": "ACTIVE"
    }
    response = await api_client.post("/api/leases/", json=lease_data)
    lease = assert_valid_json_response(response, dict, 201)
    yield lease
    # Cleanup
    logger.info("[CLEANUP] Deleting lease fixture: ID %s", lease['id'])
    try:
        delete_response = await api_client.delete(f"/api/leases/{lease['id']}")
        if delete_response.status_code not in [204, 404]:
             logger.warning("Lease fixture cleanup for ID %s failed. Status: %s", lease['id'], delete_response.status_code)
        else:
            logger.info("Lease fixture cleanup for ID %s successful (Status: %s)", lease['id'], delete_response.status_code)
    except Exception:
        logger.exception("Error during lease fixture %s cleanup", lease['id'])
