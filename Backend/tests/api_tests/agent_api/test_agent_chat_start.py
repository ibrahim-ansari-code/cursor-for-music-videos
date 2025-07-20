"""
Unit tests for the agent chat start endpoint using hybrid API testing pattern.
"""
from datetime import datetime, timezone
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Constants
MAX_MESSAGE_LENGTH = 4000  # Should match ChatMessageRequest.content max_length

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
# CHAT START TESTS
# =============================================================================

def test_start_chat_success():
    """Test successful chat start."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.start_chat.return_value = {
        "thread_id": "thread_123",
        "run_id": "run_456",
        "status": "in_progress"
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat",
                json={"content": "Show me all vacant properties"}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["thread_id"] == "thread_123"
        assert data["run_id"] == "run_456"
        assert data["status"] == "in_progress"
        
        # Verify service was called correctly
        mock_service.start_chat.assert_called_once_with(user_id, "Show me all vacant properties")


def test_start_chat_empty_message():
    """Test chat start with empty message."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        # Act
        response = client.post(
            "/api/agent/chat",
            json={"content": ""}
        )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Check for Pydantic validation error
    error_detail = response.json()["detail"][0]
    assert error_detail["msg"] == "String should have at least 1 character"


def test_start_chat_whitespace_only_message():
    """Test chat start with whitespace-only message."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    # Note: Whitespace-only messages pass Pydantic validation (min_length=1)
    # but should be handled by the service
    mock_service = AsyncMock()
    mock_service.start_chat.return_value = {
        "thread_id": "thread_whitespace",
        "run_id": "run_whitespace",
        "status": "in_progress"
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat",
                json={"content": "   \n\t   "}
            )

        # Assert - whitespace messages are technically valid
        assert response.status_code == status.HTTP_200_OK
        # Service receives the whitespace message
        mock_service.start_chat.assert_called_once_with(user_id, "   \n\t   ")


def test_start_chat_missing_message():
    """Test chat start with missing message field."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        # Act
        response = client.post(
            "/api/agent/chat",
            json={}
        )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_start_chat_tenant_user_allowed():
    """Test that tenant users can start chats."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="tenant@example.com", user_type=UserType.TENANT.value)
    
    mock_service = AsyncMock()
    mock_service.start_chat.return_value = {
        "thread_id": "thread_789",
        "run_id": "run_012",
        "status": "in_progress"
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat",
                json={"content": "When is my lease expiring?"}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "thread_id" in data
        assert "run_id" in data
        assert "status" in data


def test_start_chat_service_error():
    """Test chat start when service raises an error."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.start_chat.side_effect = Exception("Azure AI service unavailable")
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat",
                json={"content": "Hello"}
            )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to start chat" in response.json()["detail"]


def test_start_chat_very_long_message():
    """Test chat start with very long message."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    # Create a very long message (exceeds validation limit)
    long_message = "a" * (MAX_MESSAGE_LENGTH + 1)
    
    mock_service = AsyncMock()
    mock_service.start_chat.return_value = {
        "thread_id": "thread_long",
        "run_id": "run_long",
        "status": "in_progress"
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat",
                json={"content": long_message}
            )

        # Assert - message exceeds 4000 char limit
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        # Service should not be called due to validation failure
        mock_service.start_chat.assert_not_called()


def test_start_chat_special_characters():
    """Test chat start with special characters in message."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    special_message = "What's the rent for unit #5? It's $1,500/month & includes utilities!"
    
    mock_service = AsyncMock()
    mock_service.start_chat.return_value = {
        "thread_id": "thread_special",
        "run_id": "run_special",
        "status": "in_progress"
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat",
                json={"content": special_message}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_service.start_chat.assert_called_once_with(user_id, special_message)


def test_start_chat_unauthenticated():
    """Test chat start without authentication."""
    # Don't override auth dependencies - FastAPI returns 403 without valid token
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post(
            "/api/agent/chat",
            json={"content": "Hello"}
        )

    # Assert - Supabase auth returns 403 for missing auth
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_start_chat_unicode_message():
    """Test chat start with unicode characters."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    unicode_message = "Show properties in 北京 with rent ≥ €1000"
    
    mock_service = AsyncMock()
    mock_service.start_chat.return_value = {
        "thread_id": "thread_unicode",
        "run_id": "run_unicode",
        "status": "in_progress"
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat",
                json={"content": unicode_message}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_service.start_chat.assert_called_once_with(user_id, unicode_message)