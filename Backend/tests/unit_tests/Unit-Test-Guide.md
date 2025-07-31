# Unit Tests

## Overview

This directory contains **pure unit tests** that test individual functions and methods in isolation. These tests focus on business logic and do not involve any HTTP requests, database connections, or external dependencies.

## Purpose

Unit tests are designed to:

- Test individual functions and methods in isolation
- Verify business logic correctness
- Run extremely fast (milliseconds per test)
- Provide immediate feedback during development
- Be easy to debug when they fail

## Characteristics

- **No HTTP calls**: Tests call functions directly, not through API endpoints
- **No database**: All database interactions are mocked
- **No external services**: All external dependencies are mocked
- **Fast execution**: Tests run in milliseconds
- **Isolated**: Each test is independent and can run in any order

## Test Structure

```text
unit_tests/
├── auth/
│   ├── __init__.py
│   └── test_service.py    # Tests for auth service functions
├── leases/
│   ├── test_service.py    # Tests for lease service functions
│   └── test_router.py     # Tests for lease router functions
├── properties/
│   └── test_service.py    # Tests for property service functions
├── tenants/
│   └── test_router.py     # Tests for tenant router functions
└── Unit-Test-Guide.md
```

### Test Organization

Unit tests should be organized as **standalone functions**, not classes. This matches pytest's discovery patterns and keeps tests simple:

```python
# ✅ Good - standalone function
@pytest.mark.asyncio
async def test_get_user_by_id_success(mock_session, sample_user):
    """Test successful user retrieval by ID."""
    # test implementation

# ❌ Avoid - class-based structure
class TestUserService:
    async def test_get_user_by_id_success(self):
        # test implementation
```

## Writing Unit Tests

### Example: Testing a Service Function

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from Backend.api.leases.service import check_lease_permission
from Backend.models.user import User
from Backend.models.lease import Lease

@pytest.mark.asyncio
async def test_check_lease_permission_success():
    # Arrange
    mock_session = AsyncMock()
    mock_user = User(id=uuid4(), email="test@example.com", user_type="LANDLORD")
    mock_lease = Lease(id=123, property_id=1, landlord_id=mock_user.id)
    
    # Mock the database query
    mock_session.scalar.return_value = mock_lease
    
    # Act
    result = await check_lease_permission(123, mock_user, mock_session)
    
    # Assert
    assert result.id == 123
    assert mock_session.scalar.called
```

### Example: Testing a Router Function

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from Backend.api.tenants.router import create_tenant
from Backend.api.tenants.schemas import TenantCreate, TenantResponse

@pytest.mark.asyncio
async def test_create_tenant_success(mocker):
    # Arrange
    mock_user = User(id=uuid4(), email="landlord@example.com", user_type="LANDLORD")
    mock_session = AsyncMock()
    tenant_data = TenantCreate(
        first_name="John",
        last_name="Doe",
        email="john@example.com"
    )
    
    # Mock all service functions
    mocker.patch("Backend.api.tenants.router._validate_user_permissions", new=AsyncMock())
    mocker.patch("Backend.api.tenants.router.create_and_save_tenant", new=AsyncMock(return_value=mock_tenant))
    
    # Act
    result = await create_tenant(tenant_data, mock_user, mock_session)
    
    # Assert
    assert isinstance(result, TenantResponse)
    assert result.email == "john@example.com"
```

## Best Practices

1. **Mock all dependencies**: Use `unittest.mock` to mock databases, external services, etc.
2. **Test one thing**: Each test should verify a single behavior
3. **Use descriptive names**: Test names should describe what they test
4. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
5. **Keep tests simple**: If a test is complex, the code being tested might need refactoring

## Running Unit Tests

```bash
# Run all unit tests
pytest Backend/tests/unit_tests/ -v

# Run tests for a specific module
pytest Backend/tests/unit_tests/leases/ -v

# Run with coverage
pytest Backend/tests/unit_tests/ --cov=Backend.api --cov-report=html

# Run a specific test
pytest Backend/tests/unit_tests/leases/test_service.py::test_check_lease_permission -v
```

## Mocking Guidelines

### Database Sessions

```python
mock_session = AsyncMock()
mock_session.scalar.return_value = mock_object
mock_session.execute.return_value.scalars.return_value.all.return_value = [obj1, obj2]
```

### External Services

```python
mocker.patch("Backend.utils.azure_blob.upload_file", return_value="https://blob.url/file.pdf")
mocker.patch("Backend.utils.llm_utils.parse_lease", return_value={"rent": 1500})
```

### External Service Exceptions

When mocking exceptions from external services (like Supabase's GoTrueApiError), create proper mock exceptions:

```python
def create_gotrue_api_error(message, status=None):
    """Create a mock GoTrueApiError that matches the service's expectations."""
    class GoTrueApiError(Exception):
        def __init__(self, msg, status_code=None):
            super().__init__(msg)
            self.message = msg
            if status_code:
                self.status = status_code
    
    return GoTrueApiError(message, status)

# Usage in tests
mock_error = create_gotrue_api_error("Too many requests", status=429)
mock_auth.resend.side_effect = mock_error
```

### Background Tasks

```python
mock_background_tasks = MagicMock()
# Verify task was added
assert mock_background_tasks.add_task.called
```

## Common Patterns

### Testing Validation Errors

```python
with pytest.raises(HTTPException) as exc_info:
    await function_under_test(invalid_data)
assert exc_info.value.status_code == 422
assert "validation error" in str(exc_info.value.detail)
```

### Testing Permission Checks

```python
# Mock permission check to fail
mocker.patch("check_permission", side_effect=HTTPException(status_code=403))

with pytest.raises(HTTPException) as exc_info:
    await function_under_test()
assert exc_info.value.status_code == 403
```

### Testing Database Transactions

```python
# Verify rollback on error
mock_session.rollback = AsyncMock()
with pytest.raises(Exception):
    await function_that_fails()
assert mock_session.rollback.called
```

## Tips

- Use `pytest.mark.unit` to mark all unit tests
- Use `pytest.mark.asyncio` for async functions
- Keep test data minimal but realistic
- Use fixtures for common test data
- Mock at the boundary (database, external APIs)
- Don't test implementation details, test behavior

## Pydantic v2 Validation Error Format

With Pydantic v2, validation error messages now include a "Value error, " prefix. When testing validation errors, update your assertions accordingly:

```python
# Pydantic v1 format
assert "Monthly rent cannot be negative" in str(error["msg"])

# Pydantic v2 format
assert "Value error, Monthly rent cannot be negative" in str(error["msg"])
```

This change affects all custom validators that raise `ValueError`. The prefix helps distinguish between different types of validation errors (value errors, type errors, etc.).
