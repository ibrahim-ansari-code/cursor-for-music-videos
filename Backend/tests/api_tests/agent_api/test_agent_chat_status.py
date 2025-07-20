"""
Unit tests for the agent chat status endpoint using hybrid API testing pattern.
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
# CHAT STATUS TESTS
# =============================================================================

def test_get_chat_status_success():
    """Test successful chat status retrieval."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    thread_id = "thread_123"
    run_id = "run_456"
    
    mock_service = AsyncMock()
    mock_service.get_chat_status.return_value = {
        "status": "completed",
        "thread_id": thread_id,
        "run_id": run_id,
        "message": "Here are your vacant properties..."
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/agent/chat/status?thread_id={thread_id}&run_id={run_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "completed"
        assert data["thread_id"] == thread_id
        assert data["run_id"] == run_id
        assert data["message"] == "Here are your vacant properties..."
        
        # Verify service was called correctly
        mock_service.get_chat_status.assert_called_once_with(user_id, thread_id, run_id)


def test_get_chat_status_in_progress():
    """Test chat status when still in progress."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    thread_id = "thread_in_progress"
    run_id = "run_in_progress"
    
    mock_service = AsyncMock()
    mock_service.get_chat_status.return_value = {
        "status": "in_progress",
        "thread_id": thread_id,
        "run_id": run_id
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/agent/chat/status?thread_id={thread_id}&run_id={run_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["message"] is None  # Message is None when still in progress


def test_get_chat_status_requires_action():
    """Test chat status when tool execution is required."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    thread_id = "thread_tools"
    run_id = "run_tools"
    
    mock_service = AsyncMock()
    mock_service.get_chat_status.return_value = {
        "status": "processing_tools",
        "thread_id": thread_id,
        "run_id": run_id,
        "message": "Executing tools and processing results..."
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/agent/chat/status?thread_id={thread_id}&run_id={run_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processing_tools"
        assert data["message"] == "Executing tools and processing results..."


def test_get_chat_status_failed():
    """Test chat status when run has failed."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    thread_id = "thread_failed"
    run_id = "run_failed"
    
    mock_service = AsyncMock()
    # Service raises ValueError for failed status
    mock_service.get_chat_status.side_effect = ValueError("Run failed")
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/agent/chat/status?thread_id={thread_id}&run_id={run_id}")

        # Assert - ValueError returns 403
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Run failed" in response.json()["detail"]


def test_get_chat_status_thread_not_found():
    """Test chat status with non-existent thread."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    thread_id = "non_existent_thread"
    run_id = "run_123"
    
    mock_service = AsyncMock()
    # Service raises ValueError when thread doesn't belong to user
    mock_service.get_chat_status.side_effect = ValueError("Thread not found or access denied")
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/agent/chat/status?thread_id={thread_id}&run_id={run_id}")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Thread not found or access denied" in response.json()["detail"]


def test_get_chat_status_service_error():
    """Test chat status when service raises an unexpected error."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    thread_id = "thread_error"
    run_id = "run_error"
    
    mock_service = AsyncMock()
    mock_service.get_chat_status.side_effect = Exception("Azure AI service error")
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/agent/chat/status?thread_id={thread_id}&run_id={run_id}")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to get chat status" in response.json()["detail"]


def test_get_chat_status_tenant_user():
    """Test that tenant users can check their own chat status."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="tenant@example.com", user_type=UserType.TENANT.value)
    thread_id = "tenant_thread"
    run_id = "tenant_run"
    
    mock_service = AsyncMock()
    mock_service.get_chat_status.return_value = {
        "status": "completed",
        "thread_id": thread_id,
        "run_id": run_id,
        "message": "Your lease expires on..."
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/agent/chat/status?thread_id={thread_id}&run_id={run_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "completed"
        assert "message" in data


def test_get_chat_status_invalid_thread_id():
    """Test chat status with invalid thread ID format."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    invalid_thread_id = ""  # Empty thread ID
    run_id = "run_123"
    
    mock_service = AsyncMock()
    # Service should raise ValueError for invalid thread access
    mock_service.get_chat_status.side_effect = ValueError("Thread not found or access denied")
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/agent/chat/status?thread_id={invalid_thread_id}&run_id={run_id}")

        # Assert - Invalid thread_id causes access denied error (403)
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_chat_status_invalid_run_id():
    """Test chat status with invalid run ID format."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    thread_id = "thread_123"
    invalid_run_id = ""  # Empty run ID
    
    mock_service = AsyncMock()
    # Service should raise ValueError for invalid run access
    mock_service.get_chat_status.side_effect = ValueError("Thread not found or access denied")
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get(f"/api/agent/chat/status?thread_id={thread_id}&run_id={invalid_run_id}")

        # Assert - Invalid run_id causes access denied error (403)
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_chat_status_unauthenticated():
    """Test chat status without authentication."""
    # Don't override auth dependencies - FastAPI returns 403 without valid token
    thread_id = "thread_123"
    run_id = "run_456"
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.get(f"/api/agent/chat/status?thread_id={thread_id}&run_id={run_id}")

    # Assert - Supabase auth returns 403 for missing auth
    assert response.status_code == status.HTTP_403_FORBIDDEN