"""
Shared pytest fixtures for API tests.
"""

import inspect
from dotenv import load_dotenv
import asyncio
import os
import sys
import logging
import pytest
import httpx
import json
from collections.abc import Iterator, AsyncGenerator
from typing import Any
import time
import aiofiles

# Standard Project Root Setup
_THIS_SCRIPT_ABSPATH = os.path.abspath(__file__)
_API_TESTS_DIR = os.path.dirname(_THIS_SCRIPT_ABSPATH)
_TESTS_DIR = os.path.dirname(_API_TESTS_DIR)
_BACKEND_DIR = os.path.dirname(_TESTS_DIR)
PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Load environment variables
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Import authentication helper
try:
    from Backend.tests.api_tests.test_auth_helper import get_test_jwt
except ImportError:
    logger.warning("Failed to import get_test_jwt from test_auth_helper")
    get_test_jwt = None


class APITestClient:
    """Enhanced test client with authentication handling for pytest"""

    def __init__(self, base_url: str):
        """
        Initializes the APITestClient with a base URL for API requests.
        
        Args:
            base_url: The root URL to which all API requests will be sent.
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token: str | None = None
        self.current_user: dict[str, Any] | None = None
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

    async def __aenter__(self):
        """
        Authenticates the API client and returns itself for use in an async context manager.
        """
        await self._authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the HTTP client when exiting the asynchronous context manager.
        """
        await self.client.aclose()

    async def _authenticate(self):
        """
        Attempts to authenticate the API client by acquiring a JWT token.
        
        Tries to obtain a token using a helper function, then falls back to an environment variable, and finally to a local token file. Sets the token for use in authenticated requests and logs the outcome. If no token is found, logs a critical error.
        """
        logger.info(
            "APITestClient: Attempting to acquire authentication token...")

        # Try to get fresh token from auth helper
        if get_test_jwt:
            try:
                fresh_token = (
                    await get_test_jwt()
                    if inspect.iscoroutinefunction(get_test_jwt)
                    else get_test_jwt()
                )
                if fresh_token:
                    if isinstance(fresh_token, str):
                        self.auth_token = fresh_token
                        os.environ["TEST_USER_JWT"] = fresh_token
                        logger.info(
                            "✅ Token obtained via get_test_jwt: %s...", self.auth_token[:20])
                        return
                    else:
                        logger.warning("⚠️ Invalid token type received from get_test_jwt")
            except Exception as e:
                logger.warning(
                    "⚠️ Error getting token from auth helper: %s", e)

        # Fallback to environment variable
        self.auth_token = os.getenv("TEST_USER_JWT")
        if self.auth_token:
            logger.info(
                "✅ Using JWT from TEST_USER_JWT env var: %s...", self.auth_token[:20])
            return

        # Fallback to token file
        token_file_path = os.path.join(self.script_dir, '.test_jwt_token')
        if os.path.exists(token_file_path):
            try:
                async with aiofiles.open(token_file_path, 'r', encoding='utf-8') as f:
                    self.auth_token = (await f.read()).strip()
                if self.auth_token:
                    logger.info(
                        "✅ Loaded JWT from %s: %s...", token_file_path, self.auth_token[:20])
                    return
            except OSError as e:
                logger.exception(
                    "⚠️ Error loading token from %s:", token_file_path)

        logger.error("❌ CRITICAL: No JWT token available!")

    def _get_headers(self) -> dict[str, str]:
        """
        Returns HTTP headers for API requests, including authorization if a token is set.
        
        The headers always include 'Content-Type: application/json' and add an 'Authorization' header with the bearer token if available.
        """
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """
        Sends an authenticated asynchronous GET request to the specified API endpoint.
        
        Args:
            endpoint: The API endpoint path, relative to the base URL.
        
        Returns:
            The HTTP response object from the API.
        """
        return await self.client.get(f"{self.base_url}{endpoint}", headers=self._get_headers(), **kwargs)

    async def post(self, endpoint: str, json_data: dict[str, Any] | None = None, **kwargs) -> httpx.Response:
        """
        Sends an authenticated asynchronous POST request to the specified API endpoint.
        
        Args:
            endpoint: The API endpoint path relative to the base URL.
            json_data: Optional dictionary to include as JSON in the request body.
        
        Returns:
            The HTTP response from the POST request.
        """
        return await self.client.post(f"{self.base_url}{endpoint}", json=json_data, headers=self._get_headers(), **kwargs)

    async def put(self, endpoint: str, json_data: dict[str, Any] | None = None, **kwargs) -> httpx.Response:
        """
        Sends an authenticated HTTP PUT request to the specified API endpoint.
        
        Args:
            endpoint: Relative path of the API endpoint.
            json_data: Optional dictionary to include as JSON in the request body.
        
        Returns:
            The HTTP response object from the API.
        """
        return await self.client.put(f"{self.base_url}{endpoint}", json=json_data, headers=self._get_headers(), **kwargs)

    async def patch(self, endpoint: str, json_data: dict[str, Any] | None = None, **kwargs) -> httpx.Response:
        """
        Sends an authenticated HTTP PATCH request to a specified API endpoint.
        
        Args:
            endpoint: The API endpoint path, relative to the base URL.
            json_data: Optional dictionary to include as JSON in the request body.
        
        Returns:
            The HTTP response from the API.
        """
        return await self.client.patch(f"{self.base_url}{endpoint}", json=json_data, headers=self._get_headers(), **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """
        Sends an authenticated HTTP DELETE request to the specified API endpoint.
        
        Args:
            endpoint: The API endpoint path, relative to the base URL.
        
        Returns:
            The HTTP response object resulting from the DELETE request.
        """
        return await self.client.delete(f"{self.base_url}{endpoint}", headers=self._get_headers(), **kwargs)


@pytest.fixture(scope="function")
async def api_client():
    """
    Yields an authenticated asynchronous API client for use in tests.
    
    This function-scoped pytest fixture provides an API client with a valid JWT token, verifying authentication before yielding. If authentication fails or no token is available, the test is skipped. Authentication is cached per session for efficiency. For isolated authentication, use the `fresh_api_client` fixture.
    """
    async with APITestClient(BASE_URL) as client:
        # Verify authentication works
        if not client.auth_token:
            pytest.skip("No JWT token available for authenticated tests")

        # Test the token with /api/auth/me
        try:
            me_response = await client.get("/api/auth/me")
            if me_response.status_code != 200:
                pytest.skip(
                    f"Authentication verification failed: {me_response.status_code}")

            user_data = me_response.json()
            client.current_user = user_data
            logger.info(f"✅ Authenticated as: {user_data.get('email')}")

        except Exception as e:
            pytest.skip(f"Authentication verification error: {e}")

        yield client


@pytest.fixture(scope="function")
async def fresh_api_client():
    """
    Yields a fresh, function-scoped authenticated API client for isolated tests.
    
    Skips the test if authentication cannot be established.
    """
    async with APITestClient(BASE_URL) as client:
        if not client.auth_token:
            pytest.skip("No JWT token available for authenticated tests")
        yield client


@pytest.fixture(scope="function")
async def created_landlord_property(api_client: APITestClient):
    """
    Creates a test property for the authenticated user and yields its ID.
    
    Posts a new property to the API as the current user, yields the created property's ID for use in tests, and ensures the property is deleted after the test completes. Skips the test if the user is not authenticated or property creation fails.
    """
    if not api_client.current_user or not api_client.current_user.get("id"):
        pytest.skip(
            "Cannot create landlord property without authenticated user ID.")

    user_id = api_client.current_user["id"]
    property_name = f"TestProp_Landlord_{user_id[:8]}_{int(time.time())}"

    property_data = {
        "name": property_name,
        "address": "123 Test St",
        "city": "Testville",
        "province": "TS",  # Assuming TS is a valid province/state code
        "postal_code": "T3S T3S",
        "property_type": "Residential",  # Ensure this is property_type
        "user_id": user_id  # Explicitly set user_id for clarity, though backend might infer
    }

    logger.info(
        f"Attempting to create property: {property_name} for user {user_id} with data: {property_data}")
    response = await api_client.post("/api/properties/", json_data=property_data)

    if response.status_code != 201:
        # If property creation fails, log and fail the test
        error_message = f"Failed to create landlord property: {response.status_code} - {response.text[:200]}"
        logger.error(error_message)
        pytest.fail(error_message)

    created_property = response.json()
    property_id = created_property["id"]
    logger.info(
        f"✅ Landlord property created: ID {property_id}, Name: {property_name}")

    yield property_id  # Yield only the ID as that's what's usually needed

    # Cleanup
    logger.info(
        f"[CLEANUP START] Attempting to delete landlord property: ID {property_id}")
    try:
        delete_response = await api_client.delete(f"/api/properties/{property_id}")
        if delete_response.status_code == 204:
            logger.info(
                f"✅ Fixture cleanup: deleted landlord property {property_id}")
        elif delete_response.status_code == 404:
            logger.info(
                f"✅ Fixture cleanup: landlord property {property_id} already deleted.")
        else:
            logger.error(
                f"❌ Fixture cleanup failed for landlord property {property_id}: DELETE returned {delete_response.status_code} - {delete_response.text[:200]}")
    except Exception as e:
        logger.error(
            f"❌ Fixture cleanup exception for landlord property {property_id}: {e}")
    logger.info(
        f"[CLEANUP END] Finished attempt to delete landlord property: ID {property_id}")


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
    
    Tests that use the 'api_client' or 'fresh_api_client' fixture are marked as requiring authentication.
    """
    # Add auth marker to all tests by default (since API tests require auth)
    for item in items:
        if "api_client" in item.fixturenames or "fresh_api_client" in item.fixturenames:
            item.add_marker(pytest.mark.auth)


# Helper functions for tests
def assert_api_success(response: httpx.Response, expected_status: int = 200):
    """
    Asserts that the API response status code matches the expected value.
    
    Raises an assertion error if the response status code does not equal the expected status.
    """
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text[:500]}"
    )


def assert_valid_json_response(response: httpx.Response, expected_type=None, expected_status=200):
    """
    Asserts that an HTTP response has the expected status and contains valid JSON.
    
    If `expected_type` is provided, also asserts that the parsed JSON matches the specified type. Fails the test if the response is not valid JSON or does not match the expected type.
    
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
    except json.JSONDecodeError as e:
        pytest.fail(
            f"Invalid JSON response: {e}. Response text: {response.text[:500]}")


async def cleanup_test_data(api_client: APITestClient):
    """
    Asynchronously deletes test tenants and properties created during testing.
    
    Identifies and removes tenants and properties whose names or emails match test patterns, while skipping protected accounts. Logs the outcome of each deletion attempt and handles network or request errors gracefully.
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


# Explicitly provide an event loop fixture for pytest-asyncio
@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """
    Provides a session-scoped asyncio event loop for pytest.
    
    On Windows, sets a compatible event loop policy for stability. Closes the event loop after the test session.
    """
    # Set Windows-compatible event loop policy for better stability
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.info("Set Windows SelectorEventLoopPolicy for compatibility")

    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
async def created_property_id(api_client: APITestClient) -> AsyncGenerator[int, None]:
    """
    Creates a test property and yields its ID, deleting the property after the test.
    
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
    response = await api_client.post("/api/properties/", json_data=property_data)
    assert response.status_code == 201
    property_obj = response.json()
    property_id = property_obj["id"]

    yield property_id

    # Cleanup
    delete_response = await api_client.delete(f"/api/properties/{property_id}")
    assert delete_response.status_code in [204, 404]


@pytest.fixture
async def created_property(api_client: APITestClient) -> AsyncGenerator[dict[str, Any], None]:
    """
    Creates a test property asynchronously for use in API tests and deletes it after the test.
    
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
    response = await api_client.post("/api/properties/", json_data=property_data)
    property_obj = response.json()

    yield property_obj

    # Cleanup
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
