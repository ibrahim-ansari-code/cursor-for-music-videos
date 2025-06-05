# Backend API Test Suite Guide

## Overview

This test suite uses **pytest** with full async support. The tests use **pytest-asyncio** for proper async test execution and provide comprehensive API coverage.

## 🚀 **Quick Start**

### **Prerequisites**
1. **Running API server** at `http://localhost:8000`
2. **Valid credentials** (see Setup section below)
3. **Python dependencies** installed (see pyproject.toml)

### **Run All Tests**
```bash
cd Backend/tests
python run_all_api_tests_pytest.py
```

### **Run Specific Test Modules**
```bash
# From the Backend/tests directory:
cd Backend/tests

# Run accounting tests only
python -m pytest api_tests/test_accounting_api.py -v

# Run authentication tests only  
python -m pytest api_tests/test_auth_api.py -v

# Run with specific markers
python -m pytest -m "not slow" -v  # Skip slow tests
python -m pytest -m "auth" -v      # Run only authenticated tests
```

### **Run Individual Tests**
```bash
# From the Backend/tests directory:
cd Backend/tests

# Run a specific test method
python -m pytest api_tests/test_accounting_api.py::TestAccountingAPI::test_get_payments -v
```

## 🔧 **Setup & Configuration**

### **Authentication Setup**
The test suite requires valid Supabase credentials for authentication. Create these files in the `Backend/tests/` directory:

1. **`.test_credentials.json`** - Create this file with your Supabase credentials:
```json
{
  "SUPABASE_URL": "your_supabase_url",
  "SUPABASE_ANON_KEY": "your_supabase_anon_key",
  "SUPABASE_SERVICE_ROLE_KEY": "your_service_role_key",
  "TEST_USER_EMAIL": "your_test_user_email",
  "TEST_USER_PASSWORD": "your_test_user_password"
}
```

2. **`.test_jwt_token`** - This file will be automatically created when tests run successfully.

**Note:** These files are in `.gitignore` for security. Contact your team lead or check your team's credential management system for the actual values.

### **Environment Variables**
Ensure your `.env` file contains the necessary configuration for the API server to run properly.

### **Pytest Configuration** (`pytest.ini`)
```ini
[pytest]
# Test discovery
testpaths = Backend/tests/api_tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Async support - EXPLICIT configuration to fix deprecation warning
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function

# Test markers
markers = 
    auth: marks tests that require authentication
    slow: marks tests as slow  
    integration: marks tests as integration tests
    unit: marks tests as unit tests

# Logging configuration
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# Output configuration  
addopts = -v --tb=short --strict-markers --asyncio-mode=auto

# Minimum Python version
minversion = 3.11 
```

## 🏗️ **Test Architecture**

### **Core Components:**

1. **`conftest.py`** - Shared fixtures and configuration
   - `api_client` fixture - Authenticated HTTP client
   - Helper functions - Response validation utilities
   - Authentication management - JWT token handling

2. **Test Modules:**
   - `test_accounting_api.py` - Financial operations (payments, expenses, invoices)
   - `test_auth_api.py` - Authentication endpoints
   - `test_dashboard_api.py` - Dashboard data retrieval
   - `test_generic_api_behaviors.py` - HTTP behavior testing
   - `test_leases_api.py` - Lease management operations
   - `test_properties_api.py` - Property CRUD operations
   - `test_reports_api.py` - Reporting endpoints
   - `test_tenants_api.py` - Tenant management operations

3. **Authentication Helper** (`test_auth_helper.py`)
   - Automatic JWT token acquisition
   - Supabase integration
   - Token refresh and validation

## 🔐 **Authentication**

The test suite uses **automatic JWT authentication**:

- Tokens are automatically acquired and refreshed
- Authentication state is managed per test session
- Tests requiring auth use the `@pytest.mark.auth` marker
- No manual token management required during test execution

## 📝 **Writing New Tests**

### **Test Structure:**
```python
import pytest
import logging

logger = logging.getLogger(__name__)

@pytest.mark.auth
@pytest.mark.integration
class TestYourAPI:
    """Test suite for Your API endpoints"""

    @pytest.mark.asyncio
    async def test_your_endpoint(self, api_client):
        """Test description"""
        logger.info("Testing your endpoint...")
        
        response = await api_client.get("/api/your/endpoint")
        data = assert_valid_json_response(response, dict)
        
        assert "expected_field" in data
        logger.info("✅ Test successful")
```

### **Best Practices:**
- Use descriptive test names that explain what is being tested
- Add logging for test progress and debugging
- Use appropriate markers (`@pytest.mark.auth`, `@pytest.mark.slow`)
- Clean up test data when possible (create/delete patterns)
- Handle expected failures gracefully with proper error messages
- Use helper functions from `conftest.py` for common operations

## 📊 **Test Markers**

- `@pytest.mark.auth` - Requires authentication
- `@pytest.mark.slow` - Long-running tests  
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.asyncio` - Async test functions (required for all async tests)

## 🔧 **Troubleshooting**

### **Common Issues:**

1. **"No JWT token available"**
   - Ensure API server is running on `http://localhost:8000`
   - Check network connectivity
   - Verify `.test_credentials.json` file exists and has correct values
   - Try deleting `.test_jwt_token` to force a fresh login

2. **"Authentication verification failed"**
   - Token may be expired - delete `.test_jwt_token` to force refresh
   - Check user permissions in Supabase dashboard
   - Verify test user account is active

3. **"Module not found" or Import Errors**
   - Ensure you're in the correct directory (`Backend/tests`)
   - Check Python path configuration
   - Verify all dependencies are installed

4. **"Connection refused" or Network Errors**
   - Confirm API server is running: `poetry run uvicorn Backend.api.app:app --reload`
   - Check that server is accessible at `http://localhost:8000`
   - Verify no firewall or network issues

### **Debug Mode:**
```bash
# From the Backend/tests directory:
cd Backend/tests

# Run tests with verbose output and no capture
python -m pytest api_tests/ -v -s

# Run with debug logging
python -m pytest api_tests/ -v --log-cli-level=DEBUG

# Run a single test with maximum verbosity
python -m pytest api_tests/test_auth_api.py::TestAuthAPI::test_verify_token -v -s --log-cli-level=DEBUG
```

## 📈 **Test Reporting**

The test suite generates:
- **Console output** with real-time progress and colored results
- **JSON reports** (`pytest_report.json`) with detailed test metadata
- **Detailed logging** with timestamps for debugging
- **Pass/fail statistics** and execution duration metrics

## 🛠️ **Development Guidelines**

### **Adding New API Tests:**
1. Create test class in appropriate module (or create new module)
2. Use `@pytest.mark.auth` for authenticated endpoints
3. Follow the naming convention: `test_<operation>_<endpoint>`
4. Include proper cleanup for created test data
5. Add appropriate assertions and logging

### **Modifying Existing Tests:**
1. Ensure changes don't break existing functionality
2. Update documentation if test behavior changes
3. Run full test suite before committing changes
4. Consider backward compatibility with different API versions

## 🚀 **Future Enhancements**

Potential improvements for the test suite:
1. **Expanded test coverage** for edge cases and error conditions
2. **Performance testing** for high-load scenarios  
3. **Test data fixtures** for consistent test environments
4. **API contract testing** to validate request/response schemas
5. **CI/CD integration** for automated testing pipelines
6. **Mock testing** for isolated unit tests
7. **Load testing** for stress testing API endpoints

--

**Happy Testing!** 🧪✨ 