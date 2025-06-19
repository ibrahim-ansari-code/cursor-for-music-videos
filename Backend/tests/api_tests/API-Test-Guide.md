# API Tests (Mocked) - Hybrid Testing Pattern

## Overview

This directory contains **hybrid API tests** that use FastAPI's TestClient to test HTTP endpoints while mocking service layer dependencies. These tests combine the benefits of unit tests (speed, isolation) with API tests (testing the full HTTP stack).

## Purpose

Hybrid API tests are designed to:
- Test the complete HTTP request/response cycle
- Verify FastAPI routing, middleware, and dependency injection
- Test request/response validation and serialization
- Ensure authentication and authorization work correctly
- Run fast with mocked service layer
- Catch integration issues between API and service layers

## Key Characteristics

- **Uses TestClient**: Makes real HTTP requests to the FastAPI application
- **Mocks service layer**: Service functions are mocked, not database calls
- **Tests full stack**: Includes routing, middleware, validation, serialization
- **Fast execution**: No database or external service calls
- **Realistic testing**: Tests behave like real API calls

## Test Structure

```
api_tests/
├── leases/
│   ├── __init__.py
│   ├── test_create.py      # POST endpoint tests
│   ├── test_delete.py      # DELETE endpoint tests
│   ├── test_get.py         # GET endpoint tests
│   ├── test_update.py      # PUT/PATCH endpoint tests
│   └── test_service.py     # Miscellaneous service tests
├── properties/
├── tenants/
└── API-Test-Guide.md
```

## Blueprint for Creating Hybrid API Tests

### 1. Basic Test File Structure

Every test file should follow this structure:

```python
"""
Unit tests for the [module] [operation] service functions.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException

from Backend.api.app import app
from Backend.api.[module].schemas import [SchemaClasses]
from Backend.models.user import User
from Backend.models.[module] import [ModelClasses]
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()

# Create a custom TestClient that sets the proper host header
class TestClientWithHost(TestClient):
    def request(self, method: str, url, **kwargs):
        # Always add localhost to headers if not present
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)
```

### 2. Helper Functions

Create reusable helper functions for test data:

```python
def create_test_user(user_id=None, email="test@example.com", user_type="LANDLORD"):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=False,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )

def create_mock_[model](id=1, **kwargs):
    """Helper function to create a mock [Model] ORM object with defaults."""
    mock_obj = MagicMock(spec=[Model])
    
    # Set default values
    mock_obj.id = id
    # Add all model fields with sensible defaults
    # Override with kwargs as needed
    
    return mock_obj
```

### 3. Test Patterns by HTTP Method

#### GET Endpoint Tests

```python
def test_get_[resource]_success(mocker):
    # Arrange
    resource_id = 123
    fake_user = create_test_user()
    fake_resource = create_mock_[model](resource_id)
    
    # Mock the service layer
    mocker.patch(
        "Backend.api.[module].service.get_[resource]",
        new=AsyncMock(return_value=fake_resource)
    )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.get(f"/api/[resources]/{resource_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == resource_id
```

#### POST Endpoint Tests

```python
def test_create_[resource]_success(mocker):
    # Arrange
    fake_user = create_test_user()
    
    # Request data as dict (will be JSON serialized)
    request_data = {
        "field1": "value1",
        "field2": "2024-01-01",  # Dates as strings
        "field3": "100.00",      # Decimals as strings
    }
    
    # Create mock response
    fake_resource = create_mock_[model](id=123, **converted_values)
    
    # Mock the service layer
    mocker.patch(
        "Backend.api.[module].service.create_[resource]",
        new=AsyncMock(return_value=fake_resource)
    )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/[resources]/", json=request_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 123
```

#### PUT/PATCH Endpoint Tests

```python
def test_update_[resource]_success(mocker):
    # Arrange
    resource_id = 123
    fake_user = create_test_user()
    
    update_data = {
        "field1": "updated_value"
    }
    
    # Create updated resource
    fake_updated = create_mock_[model](id=resource_id, field1="updated_value")
    
    # Mock the service layer
    mocker.patch(
        "Backend.api.[module].service.update_[resource]",
        new=AsyncMock(return_value=fake_updated)
    )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.put(f"/api/[resources]/{resource_id}", json=update_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["field1"] == "updated_value"
```

#### DELETE Endpoint Tests

```python
def test_delete_[resource]_success(mocker):
    # Arrange
    resource_id = 123
    fake_user = create_test_user()
    
    # Mock the service layer
    mocker.patch(
        "Backend.api.[module].service.delete_[resource]",
        new=AsyncMock(return_value=None)
    )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.delete(f"/api/[resources]/{resource_id}")
        
        # Assert
        assert response.status_code == 204
```

### 4. Common Test Scenarios

#### Authentication Tests

```python
def test_endpoint_requires_authentication():
    # Don't override get_current_user - let it fail
    with TestClientWithHost(app) as client:
        response = client.get("/api/protected-endpoint/")
    assert response.status_code == 401
```

#### Authorization Tests

```python
def test_tenant_cannot_access_landlord_resource():
    fake_user = create_test_user(user_type="TENANT")
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.post("/api/properties/", json={...})
    assert response.status_code == 403
```

#### Validation Error Tests

```python
def test_create_with_invalid_data():
    fake_user = create_test_user()
    
    # Invalid data - missing required fields
    invalid_data = {
        "partial": "data"
        # Missing required fields
    }
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.post("/api/resources/", json=invalid_data)
        
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("field_name" in str(error) for error in error_detail)
```

#### Service Error Tests

```python
def test_service_raises_http_exception(mocker):
    fake_user = create_test_user()
    
    # Mock service to raise HTTPException
    mocker.patch(
        "Backend.api.[module].service.operation",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Not found"))
    )
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.get("/api/resources/123")
        assert response.status_code == 404
        assert "Not found" in response.json()["detail"]
```

#### Database Error Tests

```python
def test_database_error_handling(mocker):
    fake_user = create_test_user()
    
    # Mock service to raise generic exception
    mocker.patch(
        "Backend.api.[module].service.operation",
        new=AsyncMock(side_effect=Exception("Database connection failed"))
    )
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.post("/api/resources/", json={...})
        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]
```

### 5. Important Considerations

#### Data Type Conversions

When sending JSON data to endpoints, remember:
- Dates should be strings: `"2024-01-01"`
- Decimals should be strings: `"100.00"`
- Enums should be strings: `"ACTIVE"`
- UUIDs should be strings: `"123e4567-e89b-12d3-a456-426614174000"`

#### Mock ORM Objects vs Response Schemas

- Service functions typically return ORM objects (SQLModel instances)
- These have relationships that may be accessed (e.g., `lease.property`)
- Mock these relationships appropriately or set them to None
- The API layer handles serialization to response schemas

#### URL Patterns

- Always include the `/api` prefix in URLs
- Use trailing slashes for collection endpoints: `/api/leases/`
- No trailing slash for specific resources: `/api/leases/123`

#### Debug Output

Include debug output when tests fail:

```python
if response.status_code != expected_status:
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    print(f"Response headers: {dict(response.headers)}")
```

### 6. Running Tests

```bash
# Run all API tests
pytest Backend/tests/api_tests/ -v

# Run specific module tests
pytest Backend/tests/api_tests/leases/ -v

# Run with coverage
pytest Backend/tests/api_tests/ --cov=Backend.api --cov-report=term-missing

# Run specific test
pytest Backend/tests/api_tests/leases/test_create.py::test_create_lease_success -v
```

### 7. Best Practices

1. **One assertion focus**: Each test should primarily test one thing
2. **Descriptive names**: Test names should clearly indicate what they test
3. **Arrange-Act-Assert**: Follow the AAA pattern consistently
4. **Mock at service layer**: Don't mock individual database operations
5. **Test edge cases**: Include tests for errors, validation, and edge cases
6. **Use fixtures**: Leverage pytest fixtures for common setup
7. **Keep tests independent**: Each test should be runnable in isolation

### 8. Checklist for New Tests

When creating tests for a new endpoint:

- [ ] Import all necessary modules and models
- [ ] Add `pytestmark = pytest.mark.unit`
- [ ] Include the `clear_dependency_overrides` fixture
- [ ] Create helper functions for test data
- [ ] Test success case
- [ ] Test authentication required
- [ ] Test authorization (if applicable)
- [ ] Test validation errors
- [ ] Test service layer errors (404, 400, etc.)
- [ ] Test database errors (500)
- [ ] Use `TestClientWithHost` for all requests
- [ ] Mock at the service layer, not deeper
- [ ] Include debug output for failed assertions 