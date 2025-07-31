# Brikli Backend Test Suite Guide

## Overview

The Brikli backend test suite follows a **3-tier testing pyramid** approach using **pytest** with full async support. This guide covers all aspects of testing from unit tests to integration tests, providing comprehensive coverage while maintaining fast feedback loops.

```text
                    Integration Tests
                   /                  \
                  /    (Slowest)       \
                 /    Full Stack        \
                /------------------------\
               /                          \
              /      API Tests             \
             /      (Medium Speed)          \
            /        HTTP Layer              \
           /----------------------------------\
          /                                    \
         /            Unit Tests                \
        /            (Fastest)                   \
       /          Business Logic                  \
      /____________________________________________\
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **Poetry** for dependency management
3. **Running API server** at `http://localhost:8000` (for integration/API tests)
4. **Valid credentials** for authenticated tests (see Setup section)

### Install Dependencies

```bash
# From Backend directory
cd Backend
poetry install
```

### Run Tests by Type

```bash
# Run ALL tests
poetry run pytest tests/ -v

# Run only unit tests (fastest)
poetry run pytest tests/unit_tests/ -v

# Run only API tests 
poetry run pytest tests/api_tests/ -v

# Run only integration tests
poetry run pytest tests/integration_tests/ -v

# Run tests with coverage
poetry run pytest tests/ --cov=Backend --cov-report=html
```

## 📁 Directory Structure

```text
Backend/tests/
├── conftest.py                      # Root configuration (Python path, env loading)
├── shared_fixtures.py               # Shared utilities and helpers
├── pytest.ini                       # Pytest configuration
├── unit_tests/                      # Isolated business logic tests
│   ├── conftest.py                  # Unit test fixtures (mocks)
│   ├── __init__.py
│   ├── accounting/
│   │   └── payments/
│   ├── agent/
│   ├── auth/
│   ├── leases/
│   ├── llm/
│   ├── properties/
│   ├── tenants/
│   └── units/
├── api_tests/                       # HTTP endpoint tests
│   ├── conftest.py                  # API test fixtures
│   ├── __init__.py
│   ├── accounting_api/
│   │   ├── expenses/
│   │   ├── invoices/
│   │   └── payments/
│   ├── agent_api/
│   ├── auth/
│   ├── leases_api/
│   ├── properties_api/
│   ├── tenants_api/
│   └── units_api/
└── integration_tests/               # Full stack tests
    ├── conftest.py                  # Integration fixtures
    ├── __init__.py
    ├── test_auth_helper.py          # Auth utilities
    └── test_*.py                    # Integration test files
```

## 🧪 Test Types

### 1. Unit Tests (`/unit_tests/`)

**Purpose**: Test business logic in isolation
- **Speed**: Milliseconds per test
- **Dependencies**: All external dependencies mocked
- **Database**: In-memory SQLite or mocked
- **Focus**: Functions, methods, algorithms, data transformations
- **Run frequently**: After every code change

**Example**:
```python
@pytest.mark.unit
async def test_calculate_payment_with_reduction(mock_payment):
    """Test payment calculation with reduction amount"""
    payment = Payment(
        amount=1000.00,
        reduction_amount=100.00,
        reduction_reason="Early payment discount"
    )
    assert payment.net_amount == 900.00
```

### 2. API Tests (`/api_tests/`)

**Purpose**: Test HTTP endpoints with mocked external services
- **Speed**: Tens of milliseconds per test  
- **Dependencies**: Real FastAPI app, mocked database/services
- **Focus**: HTTP behavior, request/response validation, authentication
- **Run frequently**: Before commits

**Example**:
```python
@pytest.mark.asyncio
async def test_create_property_success(api_client):
    """Test creating a property via API"""
    response = await api_client.post("/api/properties/", json={
        "name": "Test Property",
        "address": "123 Test St"
    })
    assert_api_success(response, 201)
    data = response.json()
    assert data["name"] == "Test Property"
```

### 3. Integration Tests (`/integration_tests/`)

**Purpose**: Test complete workflows with real dependencies
- **Speed**: Seconds per test
- **Dependencies**: Real database, real authentication, external services
- **Focus**: End-to-end scenarios, data persistence, system integration
- **Run**: Before merges, in CI/CD pipeline

**Example**:
```python
@pytest.mark.integration
async def test_complete_lease_lifecycle(api_client, created_property):
    """Test creating, updating, and terminating a lease"""
    # Create tenant
    tenant_response = await api_client.post("/api/tenants/", json={...})
    tenant_id = tenant_response.json()["id"]
    
    # Create lease
    lease_response = await api_client.post("/api/leases/", json={
        "property_id": created_property,
        "tenant_id": tenant_id,
        "rent_amount": 1500
    })
    assert_api_success(lease_response, 201)
    
    # Verify database state
    # ... additional assertions
```

## 🔧 Setup & Configuration

### Authentication Setup

For integration and authenticated API tests, create these files:

1. **`.test_credentials.json`** in `Backend/tests/`:
```json
{
  "SUPABASE_URL": "your_supabase_url",
  "SUPABASE_ANON_KEY": "your_supabase_anon_key", 
  "SUPABASE_SERVICE_ROLE_KEY": "your_service_role_key",
  "TEST_USER_EMAIL": "your_test_user_email",
  "TEST_USER_PASSWORD": "your_test_user_password"
}
```

2. **`.test_jwt_token`** - Auto-created when tests run successfully

**Note**: These files are in `.gitignore`. Contact your team for credentials.

### Environment Variables

Ensure your `.env` file contains necessary configuration:
```env
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
API_BASE_URL=http://localhost:8000
```

### Pytest Configuration (`pytest.ini`)

```ini
[pytest]
# Test discovery
testpaths = Backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Async support
asyncio_mode = auto

# Test markers
markers = 
    asyncio: marks tests as async tests
    auth: marks tests that require authentication
    slow: marks tests as slow  
    integration: marks tests as integration tests
    unit: marks tests as unit tests

# Logging
log_cli = true
log_cli_level = INFO

# Performance settings
addopts = -v --tb=short --strict-markers --durations=10 --maxfail=100
```

## 📝 Writing Tests

### Test Structure

```python
import pytest
from tests.shared_fixtures import assert_api_success

@pytest.mark.unit  # or @pytest.mark.asyncio for async tests
class TestYourFeature:
    """Test suite for Your Feature"""
    
    def test_unit_logic(self, mock_db_session):
        """Test specific business logic"""
        # Arrange
        service = YourService(session=mock_db_session)
        
        # Act
        result = service.calculate_something(input_data)
        
        # Assert
        assert result == expected_value
    
    @pytest.mark.asyncio
    async def test_api_endpoint(self, api_client):
        """Test API endpoint behavior"""
        # Act
        response = await api_client.get("/api/your/endpoint")
        
        # Assert
        assert_api_success(response)
        data = response.json()
        assert "expected_field" in data
```

### Choosing Test Type

| Scenario | Test Type | Example |
|----------|-----------|---------|
| Business logic calculation | Unit | `test_calculate_late_fee()` |
| Data validation | Unit | `test_validate_phone_number()` |
| HTTP status codes | API | `test_get_property_returns_404()` |
| Authentication flow | API | `test_unauthorized_returns_401()` |
| Complete user journey | Integration | `test_tenant_lease_payment_flow()` |
| Database constraints | Integration | `test_unique_email_constraint()` |

### Best Practices

1. **Test Naming**: Use descriptive names that explain the scenario
   - ✅ `test_create_payment_with_invalid_amount_returns_422()`
   - ❌ `test_payment_error()`

2. **Test Independence**: Each test should be isolated
   - Use fixtures for setup/teardown
   - Don't depend on test execution order
   - Clean up test data

3. **Assertions**: Be specific and test one thing
   ```python
   # Good
   assert response.status_code == 201
   assert data["status"] == "active"
   
   # Bad
   assert response.status_code in [200, 201, 202]
   ```

4. **Mocking**: Mock at appropriate boundaries
   - Unit tests: Mock all external dependencies
   - API tests: Mock database and external services
   - Integration tests: Minimal mocking

## 🏃 Running Tests

### Development Workflow

```bash
# While developing a feature
poetry run pytest tests/unit_tests/properties/ -v --fail-fast

# Before committing
poetry run pytest tests/unit_tests tests/api_tests -v

# Run specific test
poetry run pytest tests/api_tests/properties_api/test_properties_create.py::test_create_property_success -v

# Run with pattern matching
poetry run pytest -k "create_property" -v

# Run by marker
poetry run pytest -m "not slow" -v
```

### Debugging Tests

```bash
# Show print statements
poetry run pytest -s

# Drop into debugger on failure
poetry run pytest --pdb

# Verbose output
poetry run pytest -vv

# Show local variables on failure
poetry run pytest -l

# Profile slow tests
poetry run pytest --durations=10
```

### Parallel Execution

```bash
# Run tests in parallel (requires pytest-xdist)
poetry run pytest -n auto

# Run specific number of workers
poetry run pytest -n 4
```

## 📊 Test Coverage

### Coverage Goals

- **Unit Tests**: 80%+ coverage of business logic
- **API Tests**: 100% coverage of endpoints
- **Integration Tests**: Critical user paths

### Generate Coverage Reports

```bash
# Terminal report
poetry run pytest tests/ --cov=Backend --cov-report=term-missing

# HTML report
poetry run pytest tests/ --cov=Backend --cov-report=html
open htmlcov/index.html

# XML report (for CI)
poetry run pytest tests/ --cov=Backend --cov-report=xml
```

## 🔍 Fixtures & Utilities

### Available Fixtures

**Unit Test Fixtures** (`unit_tests/conftest.py`):
- `mock_db_session` - Async mock database session
- `mock_user` - Mock user objects (landlord, admin, tenant)
- `mock_property` - Mock property object
- `mock_datetime` - Consistent datetime for testing
- `mock_azure_blob_service` - Mock file storage
- `mock_openai_service` - Mock AI service

**API Test Fixtures** (`api_tests/conftest.py`):
- `api_client` - Authenticated HTTP client
- `shared_auth_token` - Session-scoped JWT token
- `current_user_id` - Authenticated user's ID

**Shared Utilities** (`shared_fixtures.py`):
- `assert_api_success()` - Validate successful responses
- `assert_api_error()` - Validate error responses
- `assert_valid_json_response()` - Validate JSON responses
- `generate_test_email()` - Create unique test emails
- `validate_datetime_field()` - Validate ISO datetime fields

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the Backend directory
   cd Backend
   poetry run pytest tests/
   ```

2. **Authentication Failures**
   - Delete `.test_jwt_token` to force token refresh
   - Verify `.test_credentials.json` exists and is valid
   - Check API server is running

3. **Database Errors**
   - Check DATABASE_URL in `.env`
   - Ensure test database exists
   - Run migrations: `poetry run alembic upgrade head`

4. **Async Warnings**
   - Add `@pytest.mark.asyncio` to async test functions
   - Ensure `asyncio_mode = auto` in pytest.ini

5. **Missing Dependencies**
   ```bash
   poetry install
   poetry update
   ```

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Poetry
        uses: snok/install-poetry@v1
        
      - name: Install dependencies
        run: poetry install
        
      - name: Run unit tests
        run: poetry run pytest tests/unit_tests/ -v
        
      - name: Run API tests
        run: poetry run pytest tests/api_tests/ -v
        
      - name: Generate coverage report
        run: poetry run pytest tests/ --cov=Backend --cov-report=xml
        
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 📈 Performance Tips

1. **Use Session-Scoped Fixtures**: Share expensive setup across tests
2. **Mock External Services**: Don't make real API calls in unit/API tests
3. **Parallel Execution**: Use `pytest -n auto` for faster runs
4. **Mark Slow Tests**: Use `@pytest.mark.slow` and skip during development
5. **Database Transactions**: Use transaction rollback for test isolation

## 🤝 Contributing

When adding new features:

1. **Start with unit tests** for business logic
2. **Add API tests** for new endpoints
3. **Add integration tests** for critical workflows
4. **Ensure all tests pass** before submitting PR
5. **Maintain or improve** code coverage
6. **Document** any new fixtures or utilities

## 📚 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [Testing Best Practices](https://testdriven.io/blog/modern-tdd/)

---

**Happy Testing!** 🧪✨