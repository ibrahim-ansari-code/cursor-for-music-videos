"""
API tests for bulk unit assignment endpoints.

Tests the HTTP endpoints for both CSV-based and UI-based bulk assignment
of tenants to units.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from uuid import uuid4
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal

from Backend.api.app import app
from Backend.api.units.schemas import (
    CSVBulkAssignRequest, CSVBulkAssignResponse, CSVAssignmentRow,
    BulkAssignmentRequest, BulkAssignmentResponse, CSVAssignmentError
)
from Backend.models.property import Property, PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User
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


def create_test_user(user_id=None, email="test@example.com", user_type="LANDLORD", is_admin=False):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=is_admin,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )


def get_future_date_str(days_ahead=30):
    """Helper function to generate future date strings for tests."""
    future_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)
    return future_date.strftime('%Y-%m-%d')  # Date only, no time component

# =============================================================================
# CSV BULK ASSIGNMENT TESTS
# =============================================================================

def test_bulk_assign_csv_success():
    """Test successful CSV bulk assignment."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    # Mock service response
    mock_response = CSVBulkAssignResponse(
        total_rows=2,
        successful_assignments=2,
        failed_assignments=0,
        errors=[],
        created_leases=[1, 2]
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Test data
    future_date_1 = get_future_date_str(30)  # 30 days in the future
    future_date_2 = get_future_date_str(45)  # 45 days in the future
    csv_data = {
        "assignments": [
            {
                "unit_number": "101",
                "tenant_email": "tenant1@example.com",
                "lease_start_date": future_date_1,
                "monthly_rent": "1200.00"
            },
            {
                "unit_number": "102",
                "tenant_email": "tenant2@example.com",
                "lease_start_date": future_date_2,
                "monthly_rent": "1300.00"
            }
        ]
    }
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.bulk_assign_from_csv', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            f"/api/properties/{property_id}/units/bulk-assign-csv",
            json=csv_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["total_rows"] == 2
        assert result["successful_assignments"] == 2
        assert result["failed_assignments"] == 0
        assert result["errors"] == []
        assert result["created_leases"] == [1, 2]
        
        # Verify service was called correctly
        mock_service.assert_called_once_with(property_id, ANY, mock_session, fake_user)


def test_bulk_assign_csv_with_errors():
    """Test CSV bulk assignment with validation errors."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    # Mock service response with errors
    mock_response = CSVBulkAssignResponse(
        total_rows=2,
        successful_assignments=1,
        failed_assignments=1,
        errors=[
            CSVAssignmentError(
                row_number=2,
                unit_number="999",
                error_message="Unit not found",
                error_type="unit_not_found"
            )
        ],
        created_leases=[1]
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Test data
    future_date_1 = get_future_date_str(30)  # 30 days in the future
    future_date_2 = get_future_date_str(45)  # 45 days in the future
    csv_data = {
        "assignments": [
            {
                "unit_number": "101",
                "tenant_email": "tenant1@example.com",
                "lease_start_date": future_date_1,
                "monthly_rent": "1200.00"
            },
            {
                "unit_number": "999",
                "tenant_email": "invalid@example.com",
                "lease_start_date": future_date_2,
                "monthly_rent": "1300.00"
            }
        ]
    }
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.bulk_assign_from_csv', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            f"/api/properties/{property_id}/units/bulk-assign-csv",
            json=csv_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["successful_assignments"] == 1
        assert result["failed_assignments"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["unit_number"] == "999"
        assert result["errors"][0]["error_message"] == "Unit not found"


def test_bulk_assign_csv_invalid_data():
    """Test CSV bulk assignment with invalid request data."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Test data with missing required fields
    csv_data = {
        "assignments": [
            {
                "unit_number": "101",
                # Missing tenant_email and lease_start_date
                "monthly_rent": "1200.00"
            }
        ]
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/properties/{property_id}/units/bulk-assign-csv",
        json=csv_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422
    error_detail = response.json()
    assert "detail" in error_detail
    # Verify that validation errors are present
    assert len(error_detail["detail"]) > 0


def test_bulk_assign_csv_service_error():
    """Test CSV bulk assignment when service raises an error."""
    # Arrange
    fake_user = create_test_user()
    property_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Test data
    future_date = get_future_date_str(30)  # 30 days in the future
    csv_data = {
        "assignments": [
            {
                "unit_number": "101",
                "tenant_email": "tenant1@example.com",
                "lease_start_date": future_date,
                "monthly_rent": "1200.00"
            }
        ]
    }
    
    # Mock the service layer to raise an error
    with patch('Backend.api.units.service.UnitService.bulk_assign_from_csv', new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = Exception("Database error")
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            f"/api/properties/{property_id}/units/bulk-assign-csv",
            json=csv_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 500
        response_data = response.json()
        assert "detail" in response_data


# =============================================================================
# BULK TENANT ASSIGNMENT TESTS
# =============================================================================

def test_bulk_assign_tenant_success():
    """Test successful bulk tenant assignment."""
    # Arrange
    fake_user = create_test_user()
    
    # Mock service response
    mock_response = BulkAssignmentResponse(
        total_units=3,
        successful_assignments=3,
        failed_assignments=0,
        errors=[],
        created_leases=[1, 2, 3]
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Test data
    future_start_date = get_future_date_str(30)  # 30 days in the future
    future_end_date = get_future_date_str(395)   # ~1 year and 1 month in the future
    bulk_data = {
        "unit_ids": [1, 2, 3],
        "tenant_id": 1,
        "lease_start_date": future_start_date,
        "end_date": future_end_date,
        "monthly_rent": 1200.00,
        "security_deposit": 1200.00,
        "rent_due_day": 1,
        "late_fee_amount": 50.00,
        "late_fee_after_days": 5,
        "special_terms": "Pet allowed"
    }
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.bulk_assign_tenant', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/units/bulk-assign",
            json=bulk_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["total_units"] == 3
        assert result["successful_assignments"] == 3
        assert result["failed_assignments"] == 0
        assert result["errors"] == []
        assert result["created_leases"] == [1, 2, 3]
        
        # Verify service was called
        mock_service.assert_called_once()


def test_bulk_assign_tenant_partial_success():
    """Test bulk tenant assignment with some failures."""
    # Arrange
    fake_user = create_test_user()
    
    # Mock service response with errors
    mock_response = BulkAssignmentResponse(
        total_units=3,
        successful_assignments=2,
        failed_assignments=1,
        errors=[
            CSVAssignmentError(
                row_number=0,
                unit_number="Unit 3",
                error_message="Unit already occupied",
                error_type="unit_occupied"
            )
        ],
        created_leases=[1, 2]
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Test data
    future_start_date = get_future_date_str(30)  # 30 days in the future
    future_end_date = get_future_date_str(395)   # ~1 year and 1 month in the future
    bulk_data = {
        "unit_ids": [1, 2, 3],
        "tenant_id": 1,
        "lease_start_date": future_start_date,
        "end_date": future_end_date,
        "security_deposit": 1200.00
    }
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.bulk_assign_tenant', new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_response
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/units/bulk-assign",
            json=bulk_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["successful_assignments"] == 2
        assert result["failed_assignments"] == 1
        assert len(result["errors"]) == 1


def test_bulk_assign_tenant_invalid_data():
    """Test bulk tenant assignment with invalid request data."""
    # Arrange
    fake_user = create_test_user()
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Test data with missing required fields
    bulk_data = {
        "unit_ids": [1, 2, 3],
        "tenant_id": 1,
        # Missing lease_start_date and end_date
        "security_deposit": 1200.00
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/units/bulk-assign",
        json=bulk_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422


def test_bulk_assign_tenant_empty_unit_list():
    """Test bulk tenant assignment with empty unit list."""
    # Arrange
    fake_user = create_test_user()
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Test data with empty unit_ids
    future_start_date = get_future_date_str(30)  # 30 days in the future
    future_end_date = get_future_date_str(395)   # ~1 year and 1 month in the future
    bulk_data = {
        "unit_ids": [],
        "tenant_id": 1,
        "lease_start_date": future_start_date,
        "end_date": future_end_date,
        "security_deposit": 1200.00
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/units/bulk-assign",
        json=bulk_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422


def test_bulk_assign_tenant_invalid_dates():
    """Test bulk tenant assignment with invalid date range."""
    # Arrange
    fake_user = create_test_user()
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Test data with end_date before start_date
    future_start_date = get_future_date_str(60)  # 60 days in the future
    future_end_date = get_future_date_str(30)    # 30 days in the future (before start date)
    bulk_data = {
        "unit_ids": [1, 2, 3],
        "tenant_id": 1,
        "lease_start_date": future_start_date,
        "end_date": future_end_date,  # Before start date
        "security_deposit": 1200.00
    }
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/units/bulk-assign",
        json=bulk_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422


def test_bulk_assign_tenant_service_error():
    """Test bulk tenant assignment when service raises an error."""
    # Arrange
    fake_user = create_test_user()
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Test data
    future_start_date = get_future_date_str(30)  # 30 days in the future
    future_end_date = get_future_date_str(395)   # ~1 year and 1 month in the future
    bulk_data = {
        "unit_ids": [1, 2, 3],
        "tenant_id": 1,
        "lease_start_date": future_start_date,
        "end_date": future_end_date,
        "security_deposit": 1200.00
    }
    
    # Mock the service layer to raise an error
    with patch('Backend.api.units.service.UnitService.bulk_assign_tenant', new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = Exception("Database error")
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/units/bulk-assign",
            json=bulk_data,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 500
        response_data = response.json()
        assert "detail" in response_data


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

def test_bulk_assign_csv_requires_auth():
    """Test that CSV bulk assignment requires authentication."""
    # Arrange
    property_id = 1
    
    # Test data
    future_date = get_future_date_str(30)  # 30 days in the future
    csv_data = {
        "assignments": [
            {
                "unit_number": "101",
                "tenant_email": "tenant1@example.com",
                "lease_start_date": future_date,
                "monthly_rent": "1200.00"
            }
        ]
    }
    
    # Act - no authentication header
    client = TestClientWithHost(app)
    response = client.post(
        f"/api/properties/{property_id}/units/bulk-assign-csv",
        json=csv_data
    )
    
    # Assert
    assert response.status_code == 403


def test_bulk_assign_tenant_requires_auth():
    """Test that bulk tenant assignment requires authentication."""
    # Test data
    future_start_date = get_future_date_str(30)  # 30 days in the future
    future_end_date = get_future_date_str(395)   # ~1 year and 1 month in the future
    bulk_data = {
        "unit_ids": [1, 2, 3],
        "tenant_id": 1,
        "lease_start_date": future_start_date,
        "end_date": future_end_date,
        "security_deposit": 1200.00
    }
    
    # Act - no authentication header
    client = TestClientWithHost(app)
    response = client.post(
        "/api/units/bulk-assign",
        json=bulk_data
    )
    
    # Assert
    assert response.status_code == 403