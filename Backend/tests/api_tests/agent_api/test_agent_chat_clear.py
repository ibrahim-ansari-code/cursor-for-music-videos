"""
Unit tests for the agent chat clear endpoint using hybrid API testing pattern.
"""
from datetime import datetime, timezone
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
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
# CHAT CLEAR TESTS
# =============================================================================

def test_clear_chat_success():
    """Test successful chat clear."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.clear_chat.return_value = True
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/agent/chat/clear")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Chat history cleared successfully"
        
        # Verify service was called correctly
        mock_service.clear_chat.assert_called_once_with(user_id)


def test_clear_chat_no_history():
    """Test clearing chat when user has no history."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.clear_chat.return_value = True  # Still returns True even if no thread
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/agent/chat/clear")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Chat history cleared successfully"


def test_clear_chat_tenant_user():
    """Test that tenant users can clear their chat history."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="tenant@example.com", user_type=UserType.TENANT.value)
    
    mock_service = AsyncMock()
    mock_service.clear_chat.return_value = True
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/agent/chat/clear")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify tenant's chat was cleared
        mock_service.clear_chat.assert_called_once_with(user_id)


def test_clear_chat_service_error():
    """Test chat clear when service raises an error."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.clear_chat.side_effect = Exception("Azure AI service error")
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/agent/chat/clear")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to clear chat history" in response.json()["detail"]


def test_clear_chat_azure_failure():
    """Test chat clear when Azure deletion fails."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.clear_chat.return_value = False  # Azure deletion failed
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/agent/chat/clear")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False  # Failure indicated in response
        assert data["message"] == "Chat history partially cleared (Azure deletion failed)"


def test_clear_chat_multiple_calls():
    """Test clearing chat multiple times in succession."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.clear_chat.return_value = True
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act - clear multiple times
            response1 = client.post("/api/agent/chat/clear")
            response2 = client.post("/api/agent/chat/clear")
            response3 = client.post("/api/agent/chat/clear")

        # Assert - all should succeed
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        assert response3.status_code == status.HTTP_200_OK
        
        # Verify service was called 3 times
        assert mock_service.clear_chat.call_count == 3


def test_clear_chat_with_active_session():
    """Test clearing chat when there's an active streaming session."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    # Simulate clearing while streaming is active
    mock_service.clear_chat.return_value = True
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/agent/chat/clear")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True


def test_clear_chat_database_error():
    """Test chat clear when database operation fails."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    # Simulate database error during clear operation
    mock_service.clear_chat.side_effect = Exception("Database connection error")
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/agent/chat/clear")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to clear chat history" in response.json()["detail"]


def test_clear_chat_admin_user():
    """Test admin users can clear their chat history."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="admin@example.com", is_admin=True)
    
    mock_service = AsyncMock()
    mock_service.clear_chat.return_value = True
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post("/api/agent/chat/clear")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify admin's own chat was cleared
        mock_service.clear_chat.assert_called_once_with(user_id)


def test_clear_chat_unauthenticated():
    """Test chat clear without authentication."""
    # Don't override get_current_user to simulate unauthenticated request
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post("/api/agent/chat/clear")

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN