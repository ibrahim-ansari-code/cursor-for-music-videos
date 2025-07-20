"""
Unit tests for the agent conversations endpoint using hybrid API testing pattern.
"""
from datetime import datetime, timezone, timedelta
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
# CONVERSATIONS TESTS
# =============================================================================

def test_list_conversations_success():
    """Test successful conversations listing."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.list_conversations.return_value = {
        "conversations": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "thread_id": "thread_1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_active": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "thread_id": "thread_2", 
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_active": datetime.now(timezone.utc).isoformat(),
                "is_active": False
            }
        ],
        "total": 2
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/conversations")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["conversations"]) == 2
        # Verify conversation structure (no title field in actual response)
        assert "thread_id" in data["conversations"][0]
        assert "created_at" in data["conversations"][0]
        assert "last_active" in data["conversations"][0]
        assert "is_active" in data["conversations"][0]
        assert data["total"] == 2
        
        # Verify service was called correctly
        mock_service.list_conversations.assert_called_once_with(user_id)


def test_list_conversations_empty():
    """Test listing conversations when user has none."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.list_conversations.return_value = {
        "conversations": [],
        "total": 0
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/conversations")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conversations"] == []
        assert data["total"] == 0


def test_list_conversations_tenant_user():
    """Test that tenant users can list their conversations."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="tenant@example.com", user_type=UserType.TENANT.value)
    
    mock_service = AsyncMock()
    mock_service.list_conversations.return_value = {
        "conversations": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "thread_id": "tenant_thread_1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_active": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
        ],
        "total": 1
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/conversations")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["thread_id"] == "tenant_thread_1"
        
        # Verify service was called with tenant's user ID
        mock_service.list_conversations.assert_called_once_with(user_id)


def test_list_conversations_service_error():
    """Test conversations listing when service raises an error."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.list_conversations.side_effect = Exception("Database connection error")
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/conversations")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to list conversations" in response.json()["detail"]


def test_list_conversations_many_threads():
    """Test listing conversations with many threads."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    # Create 50 conversations
    conversations = []
    for i in range(50):
        conversations.append({
            "id": f"550e8400-e29b-41d4-a716-44665544{i:04d}",
            "thread_id": f"thread_{i}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_active": datetime.now(timezone.utc).isoformat(),
            "is_active": True
        })
    
    mock_service = AsyncMock()
    mock_service.list_conversations.return_value = {
        "conversations": conversations,
        "total": 50
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/conversations")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["conversations"]) == 50
        assert data["total"] == 50


def test_list_conversations_with_unicode():
    """Test listing conversations with unicode content."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.list_conversations.return_value = {
        "conversations": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "thread_id": "thread_unicode",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_active": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
        ],
        "total": 1
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/conversations")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conversations"][0]["thread_id"] == "thread_unicode"


def test_list_conversations_admin_user():
    """Test that admin users can list their conversations."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="admin@example.com", is_admin=True)
    
    mock_service = AsyncMock()
    mock_service.list_conversations.return_value = {
        "conversations": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440004",
                "thread_id": "admin_thread",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_active": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
        ],
        "total": 1
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/conversations")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conversations"][0]["thread_id"] == "admin_thread"
        
        # Verify admin sees only their own conversations
        mock_service.list_conversations.assert_called_once_with(user_id)


def test_list_conversations_sorted_by_activity():
    """Test that conversations are sorted by last activity."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    now = datetime.now(timezone.utc)
    older = now - timedelta(hours=2)
    oldest = now - timedelta(hours=5)
    
    mock_service = AsyncMock()
    mock_service.list_conversations.return_value = {
        "conversations": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440005",
                "thread_id": "newest",
                "created_at": now.isoformat(),
                "last_active": now.isoformat(),
                "is_active": True
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440006",
                "thread_id": "older",
                "created_at": older.isoformat(),
                "last_active": older.isoformat(),
                "is_active": True
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440007",
                "thread_id": "oldest",
                "created_at": oldest.isoformat(),
                "last_active": oldest.isoformat(),
                "is_active": True
            }
        ],
        "total": 3
    }
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/conversations")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Verify ordering (newest first)
        assert data["conversations"][0]["thread_id"] == "newest"
        assert data["conversations"][1]["thread_id"] == "older"
        assert data["conversations"][2]["thread_id"] == "oldest"


def test_list_conversations_azure_error():
    """Test conversations listing when Azure AI service fails."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    mock_service = AsyncMock()
    mock_service.list_conversations.side_effect = Exception("Azure AI service unavailable")
    
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
        mock_agent_service_class.return_value = mock_service
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/conversations")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to list conversations" in response.json()["detail"]


def test_list_conversations_unauthenticated():
    """Test conversations listing without authentication."""
    # Don't override get_current_user to simulate unauthenticated request
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.get("/api/agent/conversations")

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN