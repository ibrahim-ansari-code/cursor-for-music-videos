# Brikli Backend Testing Strategy

## Overview

Our testing strategy follows a **3-tier pyramid approach** to ensure comprehensive coverage while maintaining fast feedback loops during development. Each tier serves a specific purpose and tests different aspects of the application.

```
                    Integration Tests
                   /                  \
                  /    (Slowest)       \
                 /    Full Stack        \
                /------------------------\
               /                          \
              /      API Tests (Mocked)    \
             /        (Medium Speed)        \
            /          HTTP Layer            \
           /----------------------------------\
          /                                    \
         /            Unit Tests                \
        /            (Fastest)                   \
       /          Business Logic                  \
      /____________________________________________\
```

## Test Types

### 1. Unit Tests (`/unit_tests/`)
- **Purpose**: Test business logic in isolation
- **Speed**: Milliseconds per test
- **Dependencies**: All mocked
- **Focus**: Functions, methods, algorithms
- **Run frequently**: After every code change

### 2. API Tests (`/api_tests/`)
- **Purpose**: Test HTTP endpoints with mocked services
- **Speed**: Tens of milliseconds per test
- **Dependencies**: Database and external services mocked
- **Focus**: HTTP behavior, request/response validation, authentication
- **Run frequently**: Before commits

### 3. Integration Tests (`/integration_tests/`)
- **Purpose**: Test complete workflows with real dependencies
- **Speed**: Seconds per test
- **Dependencies**: Real database, real authentication
- **Focus**: End-to-end scenarios, data integrity
- **Run**: Before merges, in CI/CD pipeline

## Directory Structure

```
tests/
├── unit_tests/              # Pure logic tests
│   ├── leases/
│   ├── properties/
│   ├── tenants/
│   └── README.md
├── api_tests/               # HTTP tests with mocks
│   ├── test_leases_api.py
│   ├── test_properties_api.py
│   └── README.md
├── integration_tests/       # Full stack tests
│   ├── conftest.py
│   ├── test_*.py
│   └── README.md
├── pytest.ini              # Pytest configuration
└── README.md               # This file
```

## Running Tests

### Quick Development Cycle
```bash
# Run unit tests for current module
pytest Backend/tests/unit_tests/leases/ -v

# Run API tests for current feature
pytest Backend/tests/api_tests/test_leases_api.py -v
```

### Before Committing
```bash
# Run all unit and API tests
pytest Backend/tests/unit_tests/ Backend/tests/api_tests/ -v
```

### Before Merging
```bash
# Run all tests including integration
pytest Backend/tests/ -v

# With coverage report
pytest Backend/tests/ --cov=Backend --cov-report=html
```

### Specific Test Selection
```bash
# Run by marker
pytest -m "unit" -v
pytest -m "not slow" -v

# Run specific test
pytest Backend/tests/unit_tests/leases/test_service.py::test_check_lease_permission -v

# Run tests matching pattern
pytest -k "test_create" -v
```

## Test Markers

We use pytest markers to categorize tests:

- `@pytest.mark.unit` - Pure unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.auth` - Tests requiring authentication
- `@pytest.mark.slow` - Tests taking >1 second
- `@pytest.mark.asyncio` - Async tests

## Writing Tests

### Choosing the Right Test Type

1. **Write a Unit Test when:**
   - Testing business logic or algorithms
   - Testing data transformations
   - Testing validation rules
   - You need fast feedback during development

2. **Write an API Test when:**
   - Testing HTTP status codes and headers
   - Testing request/response formats
   - Testing authentication/authorization at HTTP level
   - Testing API error responses

3. **Write an Integration Test when:**
   - Testing complete user workflows
   - Testing database constraints and relationships
   - Testing external service integrations
   - Verifying data consistency across operations

### Test Naming Conventions

- Unit tests: `test_function_name_scenario_expected_result()`
  - Example: `test_calculate_rent_with_discount_returns_reduced_amount()`

- API tests: `test_endpoint_method_scenario()`
  - Example: `test_get_lease_unauthorized_returns_401()`

- Integration tests: `test_workflow_description()`
  - Example: `test_complete_lease_lifecycle_with_payments()`

## Best Practices

### General
1. **Arrange-Act-Assert**: Structure all tests clearly
2. **One assertion per test**: Test one behavior at a time
3. **Descriptive names**: Test names should explain what they test
4. **Independent tests**: Tests should not depend on each other
5. **Clean up**: Always clean up test data

### Performance
1. **Mock expensive operations**: Database calls, API calls, file I/O
2. **Use fixtures**: Share setup code between tests
3. **Parallelize when possible**: Use `pytest-xdist` for integration tests
4. **Minimize test data**: Use only necessary data for each test

### Debugging
1. **Use `-vv` for verbose output**
2. **Use `-s` to see print statements**
3. **Use `--pdb` to drop into debugger on failure**
4. **Check test logs in `pytest.log`**

## CI/CD Integration

Our CI pipeline runs tests in stages:

1. **Fast Feedback** (on every push):
   ```bash
   pytest Backend/tests/unit_tests/ -v --fail-fast
   ```

2. **Comprehensive** (on PR):
   ```bash
   pytest Backend/tests/unit_tests/ Backend/tests/api_tests/ -v
   ```

3. **Full Validation** (before merge):
   ```bash
   pytest Backend/tests/ -v --cov=Backend --cov-report=xml
   ```

## Coverage Goals

- **Unit Tests**: 80%+ coverage of business logic
- **API Tests**: 100% coverage of endpoints
- **Integration Tests**: Critical user paths covered

Check coverage with:
```bash
pytest --cov=Backend --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `PYTHONPATH` includes project root
2. **Database errors**: Check test database configuration
3. **Auth failures**: Verify test credentials are set
4. **Flaky tests**: Look for timing issues or shared state

### Debug Commands

```bash
# Run single test with debugging
pytest path/to/test.py::test_name -vv -s --pdb

# Run with specific log level
pytest --log-cli-level=DEBUG

# Run with test output capture disabled
pytest -s

# Profile slow tests
pytest --durations=10
```

## Contributing

When adding new features:

1. Start with unit tests for business logic
2. Add API tests for new endpoints
3. Add integration tests for critical workflows
4. Ensure all tests pass before submitting PR
5. Maintain or improve code coverage

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Testing Best Practices](https://testdriven.io/blog/modern-tdd/) 