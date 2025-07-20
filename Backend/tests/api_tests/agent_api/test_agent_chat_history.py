"""
Unit tests for the agent chat history endpoint using hybrid API testing pattern.
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
# CHAT HISTORY TESTS
# =============================================================================

def test_get_chat_history_success():
    """Test successful chat history retrieval."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.get_chat_history.return_value = {
        "messages": [
            {
                "role": "user",
                "content": "Show me vacant properties",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "id": "msg_1"
            },
            {
                "role": "assistant",
                "content": "Here are your vacant properties...",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "id": "msg_2"
            }
        ],
        "thread_id": "thread_123",
        "total": 2
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/chat/history")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"
        assert data["thread_id"] == "thread_123"
        assert data["total"] == 2
        
        # Verify service was called correctly
        mock_service.get_chat_history.assert_called_once_with(user_id, 20)


def test_get_chat_history_with_limit():
    """Test chat history with custom limit."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.get_chat_history.return_value = {
        "messages": [
            {
                "role": "user",
                "content": f"Message {i}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "id": f"msg_{i}"
            }
            for i in range(50)
        ],
        "thread_id": "thread_123",
        "total": 50
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/chat/history?limit=50")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["messages"]) == 50
        
        # Verify service was called with correct limit
        mock_service.get_chat_history.assert_called_once_with(user_id, 50)


def test_get_chat_history_empty():
    """Test chat history when no messages exist."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.get_chat_history.return_value = {
        "messages": [],
        "thread_id": None,
        "total": 0
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/chat/history")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["messages"] == []
        assert data["thread_id"] is None
        assert data["total"] == 0


def test_get_chat_history_invalid_limit():
    """Test chat history with invalid limit values."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    # Service should handle negative/zero limits gracefully
    mock_service.get_chat_history.return_value = {
        "messages": [],
        "thread_id": None,
        "total": 0
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act - negative limit (service will handle this)
            response = client.get("/api/agent/chat/history?limit=-1")
            
            # Assert - FastAPI doesn't validate, so it passes to service
            assert response.status_code == status.HTTP_200_OK


def test_get_chat_history_max_limit():
    """Test chat history with limit exceeding maximum."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.get_chat_history.return_value = {
        "messages": [],
        "thread_id": "thread_123",
        "total": 0
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act - limit exceeding 100 (no validation in router)
            response = client.get("/api/agent/chat/history?limit=150")

        # Assert - No validation, so it passes to service
        assert response.status_code == status.HTTP_200_OK
        # Verify service was called with the high limit
        mock_service.get_chat_history.assert_called_once_with(user_id, 150)


def test_get_chat_history_tenant_user():
    """Test that tenant users can get their chat history."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="tenant@example.com", user_type=UserType.TENANT.value)
    
    mock_service = AsyncMock()
    mock_service.get_chat_history.return_value = {
        "messages": [
            {
                "role": "user",
                "content": "When is my lease expiring?",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "id": "msg_tenant_1"
            },
            {
                "role": "assistant",
                "content": "Your lease expires on...",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "id": "msg_tenant_2"
            }
        ],
        "thread_id": "tenant_thread",
        "total": 2
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/chat/history")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["messages"]) == 2
        assert data["thread_id"] == "tenant_thread"


def test_get_chat_history_service_error():
    """Test chat history when service raises an error."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.get_chat_history.side_effect = Exception("Database connection error")
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/chat/history")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to get chat history" in response.json()["detail"]


def test_get_chat_history_with_unicode():
    """Test chat history containing unicode characters."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.get_chat_history.return_value = {
        "messages": [
            {
                "role": "user",
                "content": "Show properties in 北京 with rent ≥ €1000",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "id": "msg_unicode_1"
            },
            {
                "role": "assistant",
                "content": "I found properties in 北京 with rent ≥ €1000...",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "id": "msg_unicode_2"
            }
        ],
        "thread_id": "thread_unicode",
        "total": 2
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/chat/history")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "北京" in data["messages"][0]["content"]
        assert "€1000" in data["messages"][1]["content"]


def test_get_chat_history_unauthenticated():
    """Test chat history without authentication."""
    # Don't override get_current_user to simulate unauthenticated request
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.get("/api/agent/chat/history")

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_chat_history_non_numeric_limit():
    """Test chat history with non-numeric limit."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        # Act
        response = client.get("/api/agent/chat/history?limit=abc")

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY