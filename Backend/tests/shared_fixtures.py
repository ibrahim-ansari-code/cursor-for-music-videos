"""
Shared fixtures and utilities for all test types.

This module provides common fixtures and helper functions that can be imported
by any test type (unit, integration, api) without circular dependencies.
"""

import json
import logging
from typing import Any

import httpx
import pytest
from httpx import Response

logger = logging.getLogger(__name__)


# Helper functions for API assertions
def assert_api_success(response: Response, expected_status: int | tuple[int, ...] = 200) -> None:
    """
    Assert that the API response has the expected status code.
    
    Args:
        response: The httpx Response object
        expected_status: Expected status code(s) - can be int or tuple of ints
        
    Raises:
        AssertionError: If status code doesn't match expected
    """
    if isinstance(expected_status, tuple):
        assert response.status_code in expected_status, (
            f"Expected status in {expected_status}, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )
    else:
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )


def assert_api_error(
    response: Response, 
    expected_status: int, 
    expected_message: str | None = None
) -> None:
    """
    Assert that the API response has an error status and optionally contains a message.
    
    Args:
        response: The httpx Response object
        expected_status: Expected error status code
        expected_message: Optional expected error message to find in response
        
    Raises:
        AssertionError: If status or message doesn't match expected
    """
    assert response.status_code == expected_status, (
        f"Expected error status {expected_status}, got {response.status_code}. "
        f"Response: {response.text[:500]}"
    )
    
    if expected_message:
        try:
            data = response.json()
            # Handle both {"detail": "message"} and {"message": "message"} formats
            error_content = str(data.get("detail", "") or data.get("message", ""))
            assert expected_message in error_content, (
                f"Expected message '{expected_message}' not found in response: {error_content}"
            )
        except json.JSONDecodeError:
            pytest.fail(f"Expected JSON error response but got non-JSON: {response.text[:500]}")


def assert_valid_json_response(
    response: Response, 
    expected_type: type | None = None, 
    expected_status: int = 200
) -> Any:
    """
    Assert that response has expected status and valid JSON, optionally of expected type.
    
    Args:
        response: The httpx Response object
        expected_type: Optional expected type for the JSON data
        expected_status: Expected status code (default 200)
        
    Returns:
        The parsed JSON data
        
    Raises:
        AssertionError: If status, JSON parsing, or type doesn't match expected
    """
    assert_api_success(response, expected_status)
    
    try:
        data = response.json()
        if expected_type:
            assert isinstance(data, expected_type), (
                f"Expected {expected_type}, got {type(data)}"
            )
        return data
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON response: {e}. Response text: {response.text[:500]}")


# Common test data generators
def generate_test_email(prefix: str = "test") -> str:
    """Generate a unique test email address."""
    import time
    import uuid
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    return f"{prefix}_{timestamp}_{unique_id}@example.com"


def generate_test_name(prefix: str = "Test") -> str:
    """Generate a unique test name."""
    import time
    import uuid
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    return f"{prefix}_{timestamp}_{unique_id}"


# Response validation helpers
def validate_datetime_field(data: dict, field_name: str) -> None:
    """Validate that a field contains a valid ISO datetime string."""
    assert field_name in data, f"Missing required field: {field_name}"
    assert isinstance(data[field_name], str), f"{field_name} must be a string"
    
    # Basic ISO datetime validation
    from datetime import datetime
    try:
        datetime.fromisoformat(data[field_name].replace('Z', '+00:00'))
    except ValueError:
        pytest.fail(f"{field_name} is not a valid ISO datetime: {data[field_name]}")


def validate_uuid_field(data: dict, field_name: str) -> None:
    """Validate that a field contains a valid UUID."""
    assert field_name in data, f"Missing required field: {field_name}"
    
    import uuid
    try:
        uuid.UUID(str(data[field_name]))
    except ValueError:
        pytest.fail(f"{field_name} is not a valid UUID: {data[field_name]}")


# Common test markers
def mark_slow_test():
    """Mark a test as slow if it's expected to take more than N seconds."""
    return pytest.mark.slow