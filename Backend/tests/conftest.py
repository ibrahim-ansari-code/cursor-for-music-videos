"""
Root conftest.py for all tests.

This file configures the Python path and loads environment variables 
so that tests can import modules from the Backend directory.

This is the ONLY place where basic setup should happen.
Subdirectory conftest.py files should focus on test-specific fixtures.
"""

import os
import sys
import pytest

# Standard Project Root Setup
_THIS_SCRIPT_ABSPATH = os.path.abspath(__file__)
_TESTS_DIR = os.path.dirname(_THIS_SCRIPT_ABSPATH)
_BACKEND_DIR = os.path.dirname(_TESTS_DIR)
PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)

# Add project root to Python path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Add Backend directory to Python path
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Load environment variables from Backend/.env
# This MUST happen before importing any Backend modules
try:
    from dotenv import load_dotenv
    backend_env_path = os.path.join(_BACKEND_DIR, '.env')
    if os.path.exists(backend_env_path):
        load_dotenv(dotenv_path=backend_env_path)
        print(f"✅ Loaded environment variables from {backend_env_path}")
    else:
        print(f"⚠️  No .env file found at {backend_env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed. Environment variables may not load correctly.")
except Exception as e:
    print(f"⚠️  Error loading environment variables: {e}")


# Global test configuration
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Ensure asyncio mode is set (backup for pytest.ini)
    config.option.asyncio_mode = "auto"


@pytest.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test function to prevent unclosed loop warnings."""
    import asyncio
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Clean up pending tasks before closing
    try:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    finally:
        asyncio.set_event_loop(None)
        loop.close()