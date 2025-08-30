"""
Unit tests for the units search functionality using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal


from Backend.api.app import app
from Backend.api.units.schemas import UnitSearchFilters, UnitResponse
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

def create_mock_unit_response(unit_id, property_id, **kwargs):
    """Helper to create a UnitResponse with defaults."""
    now = datetime.now(timezone.utc)
    return UnitResponse(
        id=unit_id,
        property_id=property_id,
        name=kwargs.get('name', f'Unit {unit_id}'),
        description=kwargs.get('description', None),
        size=kwargs.get('size', None),
        monthly_rent=kwargs.get('monthly_rent', None),
        is_rented=kwargs.get('is_rented', False),
        bedrooms=kwargs.get('bedrooms', None),
        bathrooms=kwargs.get('bathrooms', None),
        floor=kwargs.get('floor', None),
        tenant=kwargs.get('tenant', None),
        created_at=kwargs.get('created_at', now),
        updated_at=kwargs.get('updated_at', now)
    )

# =============================================================================
# UNIT SEARCH TESTS
# =============================================================================

def test_search_units_no_filters():
    """Test searching units without any filters returns all user's units."""
    # Arrange
    fake_user = create_test_user()
    
    search_filters = {}
    
    # Mock units from different properties
    mock_units = [
        create_mock_unit_response(1, 1, name="Unit A", monthly_rent=Decimal("1000"), bedrooms=1),
        create_mock_unit_response(2, 1, name="Unit B", monthly_rent=Decimal("1500"), bedrooms=2),
        create_mock_unit_response(3, 2, name="Unit 101", monthly_rent=Decimal("2000"), bedrooms=3),
    ]
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.search_units', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_units
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/units/search",
            json=search_filters,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 3
        
        # Verify service was called with empty filters
        mock_search.assert_called_once()
        args = mock_search.call_args[0]
        assert isinstance(args[0], UnitSearchFilters)
        assert args[1] == mock_session
        assert args[2] == fake_user
        assert args[3] == 0  # skip
        assert args[4] == 100  # limit

def test_search_units_with_rent_range():
    """Test searching units with rent range filter."""
    # Arrange
    fake_user = create_test_user()
    
    search_filters = {
        "min_rent": "1000.00",
        "max_rent": "1500.00"
    }
    
    # Mock units within rent range
    mock_units = [
        create_mock_unit_response(1, 1, name="Unit A", monthly_rent=Decimal("1000"), bedrooms=1),
        create_mock_unit_response(2, 1, name="Unit B", monthly_rent=Decimal("1250"), bedrooms=2),
        create_mock_unit_response(3, 2, name="Unit C", monthly_rent=Decimal("1500"), bedrooms=2),
    ]
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.search_units', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_units
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/units/search",
            json=search_filters,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 3
        assert all(1000 <= float(unit["monthly_rent"]) <= 1500 for unit in response_data)

def test_search_units_by_bedroom_count():
    """Test searching units by bedroom count."""
    # Arrange
    fake_user = create_test_user()
    
    search_filters = {
        "min_bedrooms": 2,
        "max_bedrooms": 3
    }
    
    # Mock units with 2-3 bedrooms
    mock_units = [
        create_mock_unit_response(1, 1, name="Unit A", bedrooms=2, monthly_rent=Decimal("1500")),
        create_mock_unit_response(2, 1, name="Unit B", bedrooms=3, monthly_rent=Decimal("2000")),
        create_mock_unit_response(3, 2, name="Unit C", bedrooms=2, monthly_rent=Decimal("1600")),
    ]
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.search_units', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_units
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/units/search",
            json=search_filters,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 3
        assert all(2 <= unit["bedrooms"] <= 3 for unit in response_data)

def test_search_units_by_rental_status():
    """Test searching units by rental status."""
    # Arrange
    fake_user = create_test_user()
    
    search_filters = {
        "is_rented": False  # Only available units
    }
    
    # Mock only available units
    mock_units = [
        create_mock_unit_response(1, 1, name="Unit A", is_rented=False, monthly_rent=Decimal("1200")),
        create_mock_unit_response(2, 2, name="Unit B", is_rented=False, monthly_rent=Decimal("1400")),
    ]
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.search_units', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_units
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/units/search",
            json=search_filters,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        assert all(unit["is_rented"] is False for unit in response_data)

def test_search_units_by_property_ids():
    """Test searching units in specific properties."""
    # Arrange
    fake_user = create_test_user()
    
    search_filters = {
        "property_ids": [1, 3]  # Only units from properties 1 and 3
    }
    
    # Mock units from specified properties
    mock_units = [
        create_mock_unit_response(1, 1, name="Unit A", monthly_rent=Decimal("1200")),
        create_mock_unit_response(2, 1, name="Unit B", monthly_rent=Decimal("1400")),
        create_mock_unit_response(3, 3, name="Unit 301", monthly_rent=Decimal("1800")),
    ]
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.search_units', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_units
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/units/search",
            json=search_filters,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 3
        assert all(unit["property_id"] in [1, 3] for unit in response_data)

def test_search_units_combined_filters():
    """Test searching units with multiple filters combined."""
    # Arrange
    fake_user = create_test_user()
    
    search_filters = {
        "min_rent": "1000.00",
        "max_rent": "2000.00",
        "min_bedrooms": 2,
        "is_rented": False,
        "min_bathrooms": 1.5
    }
    
    # Mock units matching all criteria
    mock_units = [
        create_mock_unit_response(
            1, 1, 
            name="Unit A", 
            monthly_rent=Decimal("1500"), 
            bedrooms=2, 
            bathrooms=1.5,
            is_rented=False
        ),
        create_mock_unit_response(
            2, 2, 
            name="Unit B", 
            monthly_rent=Decimal("1800"), 
            bedrooms=3, 
            bathrooms=2.0,
            is_rented=False
        ),
    ]
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.search_units', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_units
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/units/search",
            json=search_filters,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        # Verify all filters are respected
        for unit in response_data:
            assert 1000 <= float(unit["monthly_rent"]) <= 2000
            assert unit["bedrooms"] >= 2
            assert unit["bathrooms"] >= 1.5
            assert unit["is_rented"] is False

def test_search_units_with_pagination():
    """Test searching units with custom pagination."""
    # Arrange
    fake_user = create_test_user()
    
    search_filters = {
        "min_rent": "1000.00"
    }
    skip = 5
    limit = 10
    
    # Mock paginated results
    mock_units = [
        create_mock_unit_response(i, 1, name=f"Unit {i}", monthly_rent=Decimal("1200"))
        for i in range(6, 11)  # Simulating skip=5, getting units 6-10
    ]
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.search_units', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_units
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            f"/api/units/search?skip={skip}&limit={limit}",
            json=search_filters,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 5
        
        # Verify service was called with pagination
        mock_search.assert_called_once()
        args = mock_search.call_args[0]
        assert args[3] == skip
        assert args[4] == limit

def test_search_units_invalid_rent_range():
    """Test searching units with invalid rent range (max < min)."""
    # Arrange
    fake_user = create_test_user()
    
    search_filters = {
        "min_rent": "2000.00",
        "max_rent": "1000.00"  # Invalid: max < min
    }
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/units/search",
        json=search_filters,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Assert
    assert response.status_code == 422  # Validation error

def test_search_units_no_results():
    """Test searching units with filters that return no results."""
    # Arrange
    fake_user = create_test_user()
    
    search_filters = {
        "min_rent": "10000.00"  # Very high rent, no units match
    }
    
    # Mock empty results
    mock_units = []
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.search_units', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_units
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/units/search",
            json=search_filters,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json() == []

def test_search_units_unauthorized():
    """Test searching units without authentication."""
    # Arrange
    search_filters = {}
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/units/search",
        json=search_filters
        # No authorization header
    )
    
    # Assert
    assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"

def test_search_units_admin_sees_all():
    """Test that admin users can search all units, not just their own."""
    # Arrange
    fake_admin = create_test_user(is_admin=True)
    
    search_filters = {}
    
    # Mock units from different owners
    mock_units = [
        create_mock_unit_response(1, 1, name="Unit A"),  # Different owner
        create_mock_unit_response(2, 2, name="Unit B"),  # Different owner
        create_mock_unit_response(3, 3, name="Unit C"),  # Different owner
    ]
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_admin
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.search_units', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_units
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/units/search",
            json=search_filters,
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 3  # Admin sees all units