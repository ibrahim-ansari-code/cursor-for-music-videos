#!/usr/bin/env python3
"""
Environment Checker for Test Suite

This script checks if all required environment variables are properly configured
for running the API test suite.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file in the project root
# Assumes this script is in Backend/tests/, so ../../.env is the root .env
dotenv_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '../../.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    # Fallback for running from root if needed, or print a more specific error.
    # This case should ideally not happen if script is run from root as `python Backend/tests/check_test_env.py`
    # or if CWD is Backend/tests.
    if os.path.exists(".env"):
        load_dotenv()  # Try loading .env from current working dir if root .env not found by relative path
    else:
        print(
            f"WARNING: Root .env file not found at {dotenv_path} and no .env in current directory. Environment variables might not be fully loaded.")


def check_env() -> bool:
    """
    Checks for the presence of all required environment variables needed to run the API test suite.
    
    Prints the status of each required and optional environment variable, masking sensitive values for security. If any required variables are missing, lists them and advises updating the `.env` file. If all are present, provides instructions for running the test suite.
    
    Returns:
        True if all required environment variables are set, False otherwise.
    """

    print("🔍 Checking Test Environment Configuration")
    print("=" * 50)

    required_vars = {
        "SUPABASE_URL": "Required for test user creation",
        "SUPABASE_ANON_KEY": "Required for Supabase authentication",
        "DATABASE_URL": "Required for backend database connection",
        "SECRET_KEY": "Required for JWT signing",
    }

    optional_vars = {
        "BACKEND_URL": "Backend API URL (defaults to http://localhost:8000)",
        "TEST_USER_JWT": "Pre-existing JWT token for tests",
        "DEBUG": "Debug mode flag",
        "SUPABASE_SERVICE_KEY": "Service key for admin operations",
    }

    missing_required = []
    found_vars = []

    print("\n📋 Required Environment Variables:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var or "SECRET" in var:
                masked_value = f"{value[:8]}...{value[-4:]}" if len(
                    value) > 12 else "***"
            elif "URL" in var:
                masked_value = value.split("@")[-1] if "@" in value else value
            else:
                masked_value = value

            print(f"  ✅ {var}: {masked_value}")
            found_vars.append(var)
        else:
            print(f"  ❌ {var}: NOT SET - {description}")
            missing_required.append(var)

    print("\n📋 Optional Environment Variables:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var or "JWT" in var:
                masked_value = f"{value[:10]}..." if len(value) > 10 else "***"
            else:
                masked_value = value

            print(f"  ✅ {var}: {masked_value}")
        else:
            print(f"  ℹ️  {var}: Not set - {description}")

    print("\n" + "=" * 50)

    if missing_required:
        print("❌ Missing required environment variables:")
        for var in missing_required:
            print(f"   - {var}")
        print("\n⚠️  Please add these to your .env file before running tests.")
        return False
    else:
        print("✅ All required environment variables set in the loaded .env file!")
        print("\n🚀 To run the test suite from the project root (C:\\Brikli-V2):")
        print("1. Ensure your FastAPI backend is running (e.g., `python -m uvicorn Backend.api.app:app --reload --port 8000`)")
        print("2. If it's your first time or tokens might be expired, run the auth helper to set/refresh credentials:")
        print("   `python Backend/tests/test_auth_helper.py` (and enter password for the test user if prompted)")
        print("3. Then, run the desired test suite(s):")
        print("   `python Backend/tests/test_api_suite.py` (comprehensive tests)")
        print("   `python Backend/tests/test_datetime_fixes.py` (focused datetime regression tests)")
        print("4. (Optional but Recommended) Pre-authenticate for integration tests:")
        print("   - This avoids having to enter your password on the first test run.")
        print("   - Run the command:")
        print("   `python Backend/tests/api_tests/test_auth_helper.py` (and enter password for the test user if prompted)")
        print("\nIf all checks pass, you are ready to run the tests.")
        return True


if __name__ == "__main__":
    success = check_env()
    sys.exit(0 if success else 1)
