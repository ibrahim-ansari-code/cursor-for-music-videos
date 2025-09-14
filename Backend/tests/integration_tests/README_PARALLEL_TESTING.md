# Parallel API Testing Guide

## Overview

API tests are configured to run in parallel using `pytest-xdist`, significantly reducing test execution time.

## Running Tests in Parallel

### Default Parallel Execution (Auto-detect CPU cores)

```bash
# Run all API tests in parallel (configured in pytest.ini)
pytest Backend/tests/api_tests/

# The -n auto flag is already set in pytest.ini
```

### Custom Worker Count

```bash
# Run with specific number of workers
pytest Backend/tests/api_tests/ -n 4

# Run with half the CPU cores
pytest Backend/tests/api_tests/ -n 2

# Disable parallel execution (sequential)
pytest Backend/tests/api_tests/ -n 0
```

### Distribution Strategies

```bash
# Default: Each test to any worker
pytest Backend/tests/api_tests/

# Group by module (recommended for fixture-heavy tests)
pytest Backend/tests/api_tests/ --dist loadscope

# All tests in a file to same worker
pytest Backend/tests/api_tests/ --dist loadfile

# Custom grouping by marks
pytest Backend/tests/api_tests/ --dist loadgroup
```

## Best Practices for Parallel Testing

### 1. **Test Isolation**

- Each test should be completely independent
- Use unique identifiers (UUIDs, timestamps) for test data
- Clean up after each test using fixtures

### 2. **Database Considerations**

- Tests create unique entities to avoid conflicts
- Fixture cleanup ensures no orphaned data
- RLS (Row Level Security) helps isolate test data

### 3. **Shared Resources**

- Session-scoped fixtures (like auth tokens) are shared safely
- Function-scoped fixtures create fresh data per test

### 4. **Current Test Architecture**

✅ **Parallel-Ready Features:**

- Unique test data creation (UUIDs, timestamps)
- Proper fixture cleanup
- Independent test cases
- Session-scoped auth token sharing

## Performance Optimization

### Monitoring Test Performance

```bash
# Show slowest 10 tests (already configured)
pytest Backend/tests/api_tests/

# Show all test durations
pytest Backend/tests/api_tests/ --durations=0

# Profile specific slow tests
pytest Backend/tests/api_tests/test_slow_module.py --durations=20
```

### Debugging Parallel Test Issues

#### 1. **Run Failed Tests Sequentially**

```bash
# If tests fail in parallel, try sequential to isolate issue
pytest Backend/tests/api_tests/test_failing.py -n 0 -v
```

#### 2. **Worker-Specific Logs**

```bash
# Enable detailed logging per worker
pytest Backend/tests/api_tests/ -n auto --log-cli-level=DEBUG
```

#### 3. **Test Order Issues**

```bash
# Randomize test order to detect dependencies
pytest Backend/tests/api_tests/ --random-order
```

## Troubleshooting Common Issues

### Issue: "Database connection pool exhausted"

**Solution:** Reduce worker count or increase connection pool size

```bash
pytest Backend/tests/api_tests/ -n 2
```

### Issue: "Test data conflicts"

**Solution:** Ensure unique identifiers in test data

```python
# Good: Unique names
property_name = f"TestProp_{uuid.uuid4().hex[:8]}_{int(time.time())}"

# Bad: Static names
property_name = "TestProperty"
```

### Issue: "Flaky tests in parallel"

**Solution:** Identify and fix race conditions

```bash
# Run suspected flaky test multiple times
pytest Backend/tests/api_tests/test_flaky.py -n 4 --count=10
```

## CI/CD Configuration

### GitHub Actions Example

```yaml
- name: Run API Tests
  run: |
    pytest Backend/tests/api_tests/ \
      -n auto \
      --junit-xml=test-results.xml \
      --cov=Backend \
      --cov-report=xml
```

### Optimal Worker Count by Environment

- **Local Development:** `-n auto` (all CPU cores)
- **CI with 2 cores:** `-n 2`
- **CI with 4+ cores:** `-n 4` (leave headroom)

## Current Configuration Summary

**Location:** `Backend/tests/pytest.ini`

**Key Settings:**

- `-n auto`: Automatic worker count based on CPU cores
- `--maxfail=5`: Stop after 5 failures
- `--durations=10`: Show 10 slowest tests
- `asyncio_mode = auto`: Async test support

## Running Specific Test Categories

```bash
# Run only auth tests in parallel
pytest Backend/tests/api_tests/ -m auth

# Run integration tests in parallel
pytest Backend/tests/api_tests/ -m integration

# Run non-slow tests in parallel
pytest Backend/tests/api_tests/ -m "not slow"
```

## Monitoring Resource Usage

```bash
# Watch system resources during parallel tests (Linux/Mac)
pytest Backend/tests/api_tests/ & 
watch -n 1 'ps aux | grep pytest'

# Windows PowerShell
Start-Process pytest -ArgumentList "Backend/tests/api_tests/"
Get-Process | Where-Object {$_.ProcessName -like "*pytest*"}
```
