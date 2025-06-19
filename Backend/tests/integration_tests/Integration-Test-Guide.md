# Integration Tests

## Overview

This directory contains **full integration tests** that test the complete application stack including real database interactions, authentication, and external services. These tests verify that all components work together correctly in a production-like environment.

## Purpose

Integration tests are designed to:
- Test complete user workflows end-to-end
- Verify database operations and data integrity
- Test real authentication and authorization
- Ensure API contracts are maintained
- Catch integration issues between components
- Validate business rules across the full stack

## Characteristics

- **Real database**: Tests use a test database with actual data
- **Real HTTP requests**: Full API calls through httpx AsyncClient
- **Real authentication**: Uses actual JWT tokens and auth flow
- **Fixtures for test data**: Automated setup and teardown of test data
- **Slower execution**: Tests take seconds due to database operations
- **Comprehensive**: Tests full user scenarios

## Test Structure

```
integration_tests/
├── conftest.py                        # Shared fixtures and configuration
├── test_auth_api.py                   # Authentication flow tests
├── test_properties_api.py             # Property management tests
├── test_tenants_api.py               # Tenant management tests
├── test_leases_api.py                # Lease lifecycle tests
├── test_payments_api.py              # Payment processing tests
├── test_maintenance_api.py           # Maintenance request tests
├── test_accounting_insights_api.py   # Financial reporting tests
└── README.md
```

## Key Components

### Authentication Setup

The tests use real JWT authentication with a shared token across the session:

```python
@pytest.fixture(scope="session")
async def shared_auth_token(event_loop) -> str:
    """Obtains a valid JWT token to be shared across all tests in the session."""
    from Backend.tests.api_tests.test_auth_helper import get_primary_user_jwt
    token = await get_primary_user_jwt(prompt_for_password=False)
    if not token:
        pytest.exit("Failed to get auth token", returncode=1)
    return token
```

### Test Client Setup

```python
@pytest.fixture(scope="function")
async def api_client(shared_auth_token: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Yields an authenticated httpx.AsyncClient."""
    headers = {
        "Authorization": f"Bearer {shared_auth_token}",
        "Content-Type": "application/json"
    }
    timeout = httpx.Timeout(30.0, connect=5.0)
    async with httpx.AsyncClient(base_url=BASE_URL, headers=headers, timeout=timeout) as client:
        yield client
```

## Writing Integration Tests

### Example: Complete Property Lifecycle Test

```python
@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.asyncio
async def test_property_lifecycle(api_client: httpx.AsyncClient) -> None:
    """Test creating, updating, and deleting a property with units."""
    
    # Create property with units
    property_data = {
        "name": "Test Property",
        "address": "123 Test St",
        "city": "Test City",
        "province": "TS",
        "postal_code": "12345",
        "property_type": "Apartment",
        "units": ["101", "102", "103"]
    }
    
    response = await api_client.post("/api/properties/", json=property_data)
    assert response.status_code == 201
    property_obj = response.json()
    property_id = property_obj["id"]
    
    # Verify units were created
    assert len(property_obj["units"]) == 3
    assert property_obj["status"] == "VACANT"
    
    # Update property
    update_data = {"name": "Updated Property Name"}
    response = await api_client.put(f"/api/properties/{property_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Property Name"
    
    # Create tenant and lease
    tenant_response = await api_client.post("/api/tenants/", json={
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "555-1234"
    })
    tenant_id = tenant_response.json()["id"]
    
    lease_response = await api_client.post("/api/leases/", json={
        "property_id": property_id,
        "tenant_id": tenant_id,
        "unit_id": property_obj["units"][0]["id"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "monthly_rent": "1500.00",
        "status": "ACTIVE"
    })
    assert lease_response.status_code == 201
    
    # Verify property status changed
    response = await api_client.get(f"/api/properties/{property_id}")
    assert response.json()["status"] == "PARTIALLY_RENTED"
    
    # Cleanup
    await api_client.delete(f"/api/leases/{lease_response.json()['id']}")
    await api_client.delete(f"/api/tenants/{tenant_id}")
    await api_client.delete(f"/api/properties/{property_id}")
```

## Fixtures

### Property Fixture
```python
@pytest.fixture
async def created_property(api_client: httpx.AsyncClient) -> AsyncGenerator[dict[str, Any], None]:
    """Creates a test property and cleans it up after the test."""
    property_data = {
        "name": f"Test Property {int(time.time())}",
        "address": "999 Fixture Street",
        "city": "Test City",
        "province": "TS",
        "postal_code": "12345",
        "property_type": "Apartment"
    }
    
    response = await api_client.post("/api/properties/", json=property_data)
    property_obj = response.json()
    
    yield property_obj
    
    # Cleanup
    await api_client.delete(f"/api/properties/{property_obj['id']}")
```

### Using Fixtures in Tests
```python
async def test_with_fixtures(
    api_client: httpx.AsyncClient,
    created_property: dict,
    created_tenant: dict
) -> None:
    """Test using pre-created test data."""
    lease_data = {
        "property_id": created_property["id"],
        "tenant_id": created_tenant["id"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "monthly_rent": "1500.00"
    }
    
    response = await api_client.post("/api/leases/", json=lease_data)
    assert response.status_code == 201
```

## Best Practices

1. **Use fixtures for test data**: Ensures cleanup and reduces boilerplate
2. **Test complete workflows**: Don't just test CRUD, test business scenarios
3. **Verify side effects**: Check that related data is updated correctly
4. **Use descriptive test names**: `test_tenant_cannot_delete_property_with_active_lease`
5. **Group related tests**: Use classes or modules to organize scenarios
6. **Handle async properly**: Use `pytest.mark.asyncio` and async fixtures

## Running Integration Tests

```bash
# Run all integration tests
pytest Backend/tests/integration_tests/ -v

# Run specific test file
pytest Backend/tests/integration_tests/test_leases_api.py -v

# Run with specific markers
pytest Backend/tests/integration_tests/ -m "auth and not slow" -v

# Run in parallel (be careful with database state)
pytest Backend/tests/integration_tests/ -n 4 -v

# Run with detailed output
pytest Backend/tests/integration_tests/ -vv -s
```

## Test Data Management

### Session Cleanup
```python
@pytest.fixture(scope="session", autouse=True)
async def session_cleanup(shared_auth_token: str):
    """Cleanup all test data after the session."""
    yield
    
    async with httpx.AsyncClient(base_url=BASE_URL, headers=headers) as client:
        await cleanup_test_data(client)
```

### Test Data Patterns
- Use unique identifiers: `f"Test_{uuid4()}"` or `f"Test_{int(time.time())}"`
- Mark test data clearly: Prefix with "Test" or include "test" in emails
- Clean up in reverse order: Delete leases before tenants before properties

## Common Test Scenarios

### Permission Tests
```python
async def test_tenant_cannot_create_property(api_client_tenant: httpx.AsyncClient):
    """Verify tenants cannot create properties."""
    response = await api_client_tenant.post("/api/properties/", json={...})
    assert response.status_code == 403
```

### Constraint Tests
```python
async def test_cannot_delete_property_with_active_lease(
    api_client: httpx.AsyncClient,
    property_with_active_lease: dict
):
    """Verify business rule enforcement."""
    response = await api_client.delete(f"/api/properties/{property_with_active_lease['id']}")
    assert response.status_code == 400
    assert "active lease" in response.json()["detail"].lower()
```

### Workflow Tests
```python
async def test_lease_payment_workflow(api_client: httpx.AsyncClient):
    """Test complete payment lifecycle."""
    # Create lease
    lease = await create_test_lease(api_client)
    
    # Generate invoice
    invoice_response = await api_client.post("/api/accounting/invoices/", json={
        "lease_id": lease["id"],
        "amount": lease["monthly_rent"]
    })
    
    # Record payment
    payment_response = await api_client.post("/api/accounting/payments/", json={
        "invoice_id": invoice_response.json()["id"],
        "amount": lease["monthly_rent"],
        "payment_date": str(date.today())
    })
    
    # Verify invoice marked as paid
    invoice = await api_client.get(f"/api/accounting/invoices/{invoice_response.json()['id']}")
    assert invoice.json()["status"] == "PAID"
```

## Tips

- Use `pytest.mark.integration` to identify integration tests
- Set appropriate timeouts for long-running operations
- Use transaction rollback for faster test isolation (if supported)
- Monitor test database size and clean up old test data periodically
- Consider using factory patterns for complex test data creation
- Log important steps in complex test scenarios for debugging 