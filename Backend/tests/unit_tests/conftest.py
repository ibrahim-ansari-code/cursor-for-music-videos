"""
Shared pytest fixtures for unit tests.

This conftest.py provides fixtures specifically for unit testing.
Basic Python path setup and environment loading is handled by the parent conftest.py
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, UTC
from typing import Any, Dict
import uuid

# Import shared utilities
from tests.shared_fixtures import ( # type: ignore
    generate_test_email,
    generate_test_name,
)


# Time-related fixtures
@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing."""
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_utcnow(mock_datetime):
    """Mock datetime.utcnow() to return consistent time."""
    with patch('datetime.datetime') as mock_dt:
        mock_dt.now.return_value = mock_datetime
        mock_dt.utcnow.return_value = mock_datetime
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield mock_datetime


# Database fixtures
@pytest.fixture
def mock_db_session():
    """Mock database session for unit tests."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.add = Mock()  # Synchronous add (not async)
    session.flush = AsyncMock()
    session.get = AsyncMock()
    
    # Add context manager support
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    
    return session


# User-related fixtures
@pytest.fixture
def mock_user(mock_datetime):
    """Mock user object for unit tests."""
    return Mock(
        id=str(uuid.uuid4()),
        email="test@example.com",
        user_type="LANDLORD",
        is_active=True,
        is_verified=True,
        created_at=mock_datetime,
        updated_at=mock_datetime,
    )


@pytest.fixture
def mock_admin_user(mock_datetime):
    """Mock admin user object for unit tests."""
    return Mock(
        id=str(uuid.uuid4()),
        email="admin@example.com",
        user_type="ADMIN",
        is_active=True,
        is_verified=True,
        created_at=mock_datetime,
        updated_at=mock_datetime,
    )


@pytest.fixture
def mock_tenant_user(mock_datetime):
    """Mock tenant user object for unit tests."""
    return Mock(
        id=str(uuid.uuid4()),
        email="tenant@example.com",
        user_type="TENANT",
        is_active=True,
        is_verified=True,
        created_at=mock_datetime,
        updated_at=mock_datetime,
    )


# Property-related fixtures
@pytest.fixture
def mock_property(mock_datetime):
    """Mock property object for unit tests."""
    return Mock(
        id=1,
        name="Test Property",
        address="123 Test St",
        city="Test City",
        province="TC",
        postal_code="T1T 1T1",
        property_type="Residential",
        user_id=str(uuid.uuid4()),
        status="ACTIVE",
        created_at=mock_datetime,
        updated_at=mock_datetime,
    )


@pytest.fixture
def mock_unit(mock_datetime):
    """Mock unit object for unit tests."""
    return Mock(
        id=1,
        property_id=1,
        unit_number="101",
        bedrooms=2,
        bathrooms=1.5,
        size_sqft=850,
        rent_amount=1500.00,
        is_rented=False,
        current_tenant_id=None,
        created_at=mock_datetime,
        updated_at=mock_datetime,
    )


@pytest.fixture
def mock_tenant(mock_datetime):
    """Mock tenant object for unit tests."""
    return Mock(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="555-0123",
        tenant_type="INDIVIDUAL",
        current_property_id=None,
        user_id=str(uuid.uuid4()),
        created_at=mock_datetime,
        updated_at=mock_datetime,
    )


# Service mocks
@pytest.fixture
def mock_azure_blob_service():
    """Mock Azure Blob Storage service."""
    service = AsyncMock()
    service.upload_blob = AsyncMock(return_value="https://blob.example.com/test.pdf")
    service.delete_blob = AsyncMock(return_value=True)
    service.get_blob_url = Mock(return_value="https://blob.example.com/test.pdf")
    return service


@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service for LLM operations."""
    service = AsyncMock()
    service.parse_receipt = AsyncMock(return_value={
        "vendor": "Test Vendor",
        "amount": 100.00,
        "date": "2024-01-01",
        "category": "Utilities"
    })
    return service


# HTTP/API mocks
@pytest.fixture
def mock_http_response():
    """Factory for creating mock HTTP responses."""
    def _create_response(status_code: int = 200, json_data: Dict[str, Any] | None = None):
        response = Mock()
        response.status_code = status_code
        response.json = Mock(return_value=json_data or {})
        response.text = str(json_data) if json_data else ""
        return response
    return _create_response


# Unit test specific configuration
@pytest.fixture(autouse=True)
def unit_test_environment(monkeypatch):
    """Set up unit test environment variables."""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")


# Unit test specific markers
pytestmark = [
    pytest.mark.unit,  # Mark all tests in unit_tests as unit tests
]