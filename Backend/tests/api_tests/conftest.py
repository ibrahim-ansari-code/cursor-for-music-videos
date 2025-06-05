"""
Shared pytest fixtures for API tests.
"""

import asyncio
import os
import sys
import logging
import pytest
import httpx
import json
from typing import Dict, Any, Optional
import pytest_asyncio
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

from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
PRIMARY_TEST_USER_EMAIL = "zubinsingh05@gmail.com"

# Import authentication helper
try:
    from Backend.tests.api_tests.test_auth_helper import get_test_jwt
except ImportError:
    logger.warning("Failed to import get_test_jwt from test_auth_helper")
    get_test_jwt = None


class APITestClient:
    """Enhanced test client with authentication handling for pytest"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token: str | None = None
        self.current_user: dict[str, Any] | None = None
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
    
    async def __aenter__(self):
        await self._authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _authenticate(self):
        """Authenticate and obtain JWT token"""
        logger.info("APITestClient: Attempting to acquire authentication token...")
        
        # Try to get fresh token from auth helper
        if get_test_jwt:
            try:
                fresh_token = await get_test_jwt()
                if fresh_token:
                    self.auth_token = fresh_token
                    os.environ["TEST_USER_JWT"] = fresh_token
                    logger.info(f"✅ Token obtained via get_test_jwt: {self.auth_token[:20]}...")
                    return
            except Exception as e:
                logger.warning(f"⚠️ Error getting token from auth helper: {e}")
        
        # Fallback to environment variable
        self.auth_token = os.getenv("TEST_USER_JWT")
        if self.auth_token:
            logger.info(f"✅ Using JWT from TEST_USER_JWT env var: {self.auth_token[:20]}...")
            return
        
        # Fallback to token file
        token_file_path = os.path.join(self.script_dir, '.test_jwt_token')
        if os.path.exists(token_file_path):
            try:
                async with aiofiles.open(token_file_path, 'r', encoding='utf-8') as f:
                    self.auth_token = (await f.read()).strip()
                if self.auth_token:
                    logger.info(f"✅ Loaded JWT from {token_file_path}: {self.auth_token[:20]}...")
                    return
            except Exception as e:
                logger.warning(f"⚠️ Error loading token from {token_file_path}: {e}")
        
        logger.error("❌ CRITICAL: No JWT token available!")
        
    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self.client.get(f"{self.base_url}{endpoint}", headers=self._get_headers(), **kwargs)
    
    async def post(self, endpoint: str, json_data: dict[str, Any] | None = None, **kwargs) -> httpx.Response:
        return await self.client.post(f"{self.base_url}{endpoint}", json=json_data, headers=self._get_headers(), **kwargs)
    
    async def put(self, endpoint: str, json_data: dict[str, Any] | None = None, **kwargs) -> httpx.Response:
        return await self.client.put(f"{self.base_url}{endpoint}", json=json_data, headers=self._get_headers(), **kwargs)
    
    async def patch(self, endpoint: str, json_data: dict[str, Any] | None = None, **kwargs) -> httpx.Response:
        return await self.client.patch(f"{self.base_url}{endpoint}", json=json_data, headers=self._get_headers(), **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self.client.delete(f"{self.base_url}{endpoint}", headers=self._get_headers(), **kwargs)


@pytest_asyncio.fixture(scope="function")
async def api_client():
    """Function-scoped API client fixture with authentication"""
    async with APITestClient(BASE_URL) as client:
        # Verify authentication works
        if not client.auth_token:
            pytest.skip("No JWT token available for authenticated tests")
        
        # Test the token with /api/auth/me
        try:
            me_response = await client.get("/api/auth/me")
            if me_response.status_code != 200:
                pytest.skip(f"Authentication verification failed: {me_response.status_code}")
            
            user_data = me_response.json()
            client.current_user = user_data
            logger.info(f"✅ Authenticated as: {user_data.get('email')}")
            
        except Exception as e:
            pytest.skip(f"Authentication verification error: {e}")
        
        yield client


@pytest_asyncio.fixture(scope="function")  
async def fresh_api_client():
    """Function-scoped API client fixture for tests that need isolation"""
    async with APITestClient(BASE_URL) as client:
        if not client.auth_token:
            pytest.skip("No JWT token available for authenticated tests")
        yield client


@pytest_asyncio.fixture(scope="function")
async def created_landlord_property(api_client: APITestClient):
    """Fixture to create a property owned by the current authenticated test user."""
    if not api_client.current_user or not api_client.current_user.get("id"):
        pytest.skip("Cannot create landlord property without authenticated user ID.")

    user_id = api_client.current_user["id"]
    property_name = f"TestProp_Landlord_{user_id[:8]}_{int(time.time())}"
    
    property_data = {
        "name": property_name,
        "address": "123 Test St",
        "city": "Testville",
        "province": "TS", # Assuming TS is a valid province/state code
        "postal_code": "T3S T3S",
        "property_type": "Residential", # Ensure this is property_type
        "user_id": user_id # Explicitly set user_id for clarity, though backend might infer
    }
    
    logger.info(f"Attempting to create property: {property_name} for user {user_id} with data: {property_data}")
    response = await api_client.post("/api/properties/", json_data=property_data)
    
    if response.status_code != 201:
        # If property creation fails, log and skip tests that depend on it
        logger.error(f"Failed to create landlord property: {response.status_code} - {response.text[:200]}")
        pytest.skip(f"Failed to create landlord property, status: {response.status_code}")

    created_property = response.json()
    property_id = created_property["id"]
    logger.info(f"✅ Landlord property created: ID {property_id}, Name: {property_name}")
    
    yield property_id # Yield only the ID as that's what's usually needed
    
    # Cleanup
    logger.info(f"Attempting to delete landlord property: ID {property_id}")
    try:
        delete_response = await api_client.delete(f"/api/properties/{property_id}")
        if delete_response.status_code == 204:
            logger.info(f"✅ Fixture cleanup: deleted landlord property {property_id}")
        elif delete_response.status_code == 404:
            logger.info(f"✅ Fixture cleanup: landlord property {property_id} already deleted.")
        else:
            logger.error(f"❌ Fixture cleanup failed for landlord property {property_id}: DELETE returned {delete_response.status_code} - {delete_response.text[:200]}")
    except Exception as e:
        logger.error(f"❌ Fixture cleanup exception for landlord property {property_id}: {e}")


@pytest.fixture(autouse=True)
def configure_logging():
    """Auto-used fixture to configure logging for each test"""
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
    """Pytest configuration hook"""
    # Add custom markers
    config.addinivalue_line("markers", "auth: mark test as requiring authentication")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test") 


def pytest_collection_modifyitems(config, items):
    """Modify test items during collection"""
    # Add auth marker to all tests by default (since API tests require auth)
    for item in items:
        if "api_client" in item.fixturenames or "fresh_api_client" in item.fixturenames:
            item.add_marker(pytest.mark.auth)


# Helper functions for tests
def assert_api_success(response: httpx.Response, expected_status: int = 200):
    """Helper to assert API response success"""
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text[:500]}"
    )


def assert_valid_json_response(response: httpx.Response, expected_type=None, expected_status=200):
    """Helper to assert valid JSON response"""
    assert_api_success(response, expected_status)
    try:
        data = response.json()
        if expected_type:
            assert isinstance(data, expected_type), f"Expected {expected_type}, got {type(data)}"
        return data
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON response: {e}. Response text: {response.text[:500]}")


async def cleanup_test_data(api_client: APITestClient):
    """Helper function to clean up test data"""
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
                    t.get('email') != 'test@gmail.com'  # Don't delete production test user
                )
            ]
            
            for tenant in test_tenants:
                try:
                    delete_response = await api_client.delete(f"/api/tenants/{tenant['id']}")
                    if delete_response.status_code == 204:
                        logger.info(f"✅ Cleaned up test tenant {tenant['id']} ({tenant.get('email')})")
                    elif delete_response.status_code == 403:
                        logger.info(f"⚠️ Test tenant {tenant['id']} cleanup blocked by RLS (expected)")
                    else:
                        logger.warning(f"⚠️ Test tenant {tenant['id']} cleanup returned {delete_response.status_code}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup test tenant {tenant['id']}: {e}")
        
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
                        logger.info(f"✅ Cleaned up test property {prop['id']} ({prop.get('name')})")
                    else:
                        logger.warning(f"⚠️ Test property {prop['id']} cleanup returned {delete_response.status_code}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup test property {prop['id']}: {e}")
                    
    except Exception as e:
        logger.warning(f"⚠️ Global test data cleanup failed: {e}")


# Explicitly provide an event loop fixture for pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    # Set Windows-compatible event loop policy for better stability
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.info("Set Windows SelectorEventLoopPolicy for compatibility")
    
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 