"""
Unit tests for the units delete service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException

from Backend.api.app import app
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

# =============================================================================
# DELETE UNIT TESTS
# =============================================================================

def test_delete_unit_success():
    """Test successful unit deletion."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.delete_unit', new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = None  # delete_unit returns None on success
        
        # Act
        client = TestClientWithHost(app)
        response = client.delete(
            f"/api/units/{unit_id}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 204
        assert response.content == b''  # No content for 204 response
        
        # Verify service was called correctly
        mock_delete.assert_called_once_with(unit_id, mock_session, fake_user)

def test_delete_unit_not_found():
    """Test deleting a unit that doesn't exist."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 999
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.delete_unit', new_callable=AsyncMock) as mock_delete:
        mock_delete.side_effect = HTTPException(status_code=404, detail="Unit not found")
        
        # Act
        client = TestClientWithHost(app)
        response = client.delete(
            f"/api/units/{unit_id}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Unit not found"

def test_delete_unit_forbidden():
    """Test deleting a unit the user doesn't have permission to delete."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.delete_unit', new_callable=AsyncMock) as mock_delete:
        mock_delete.side_effect = HTTPException(
            status_code=403, 
            detail="You don't have permission to access this unit"
        )
        
        # Act
        client = TestClientWithHost(app)
        response = client.delete(
            f"/api/units/{unit_id}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 403
        assert response.json()["detail"] == "You don't have permission to access this unit"

def test_delete_unit_with_active_lease():
    """Test deleting a unit that has an active lease."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise HTTPException
    with patch('Backend.api.units.service.UnitService.delete_unit', new_callable=AsyncMock) as mock_delete:
        mock_delete.side_effect = HTTPException(
            status_code=400, 
            detail="Cannot delete unit with an active lease."
        )
        
        # Act
        client = TestClientWithHost(app)
        response = client.delete(
            f"/api/units/{unit_id}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Cannot delete unit with an active lease."

def test_delete_unit_unauthorized():
    """Test deleting unit without authentication."""
    # Arrange
    unit_id = 1
    
    # Act
    client = TestClientWithHost(app)
    response = client.delete(f"/api/units/{unit_id}")
    # No authorization header
    
    # Assert - Accept either 401 or 403 as both indicate lack of proper auth
    assert response.status_code in [401, 403], f"Expected 401 or 403 for unauthorized access, got {response.status_code}"

def test_delete_unit_admin_can_delete_any():
    """Test that admin users can delete any unit."""
    # Arrange
    fake_admin = create_test_user(is_admin=True)
    unit_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_admin
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.delete_unit', new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = None
        
        # Act
        client = TestClientWithHost(app)
        response = client.delete(
            f"/api/units/{unit_id}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 204
        
        # Verify admin was passed to service
        mock_delete.assert_called_once_with(unit_id, mock_session, fake_admin)

def test_delete_unit_server_error():
    """Test handling of unexpected server errors during deletion."""
    # Arrange
    fake_user = create_test_user()
    unit_id = 1
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer to raise a generic exception
    with patch('Backend.api.units.service.UnitService.delete_unit', new_callable=AsyncMock) as mock_delete:
        mock_delete.side_effect = Exception("Database connection lost")
        
        # Act
        client = TestClientWithHost(app)
        response = client.delete(
            f"/api/units/{unit_id}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assert
        assert response.status_code == 500
        assert "An unexpected error occurred while deleting the unit" in response.json()["detail"]

def test_delete_multiple_units_sequentially():
    """Test deleting multiple units in sequence."""
    # Arrange
    fake_user = create_test_user()
    unit_ids = [1, 2, 3]
    
    # Mock dependencies
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    
    # Mock the service layer
    with patch('Backend.api.units.service.UnitService.delete_unit', new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = None
        
        # Act & Assert
        client = TestClientWithHost(app)
        for unit_id in unit_ids:
            response = client.delete(
                f"/api/units/{unit_id}",
                headers={"Authorization": "Bearer fake-token"}
            )
            assert response.status_code == 204
        
        # Verify all deletions were called
        assert mock_delete.call_count == 3
        for i, unit_id in enumerate(unit_ids):
            assert mock_delete.call_args_list[i][0][0] == unit_id