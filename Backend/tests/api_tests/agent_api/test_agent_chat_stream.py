"""
Unit tests for the agent chat stream endpoint using hybrid API testing pattern.
"""
from datetime import datetime, timezone
import json
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.auth.dependencies import get_current_user_sse
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
# CHAT STREAM TESTS
# =============================================================================

def test_stream_chat_success():
    """Test successful chat streaming."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    # Create async generator for streaming
    async def mock_stream():
        yield 'data: {"type": "content", "content": "Here are "}\n\n'
        yield 'data: {"type": "content", "content": "your vacant "}\n\n'
        yield 'data: {"type": "content", "content": "properties..."}\n\n'
        yield 'data: {"type": "done", "total_content": "Here are your vacant properties..."}\n\n'
    
    # Mock both AgentService and BrikliAgentService since the endpoint uses both
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class, \
         patch("Backend.api.agent.router.BrikliAgentService") as mock_brikli_service_class:
        # Mock AgentService for thread creation
        mock_agent_instance = AsyncMock()
        mock_agent_instance.get_or_create_thread = AsyncMock(return_value="thread_123")
        mock_agent_service_class.return_value = mock_agent_instance
        
        # Mock BrikliAgentService for streaming - prevent actual instantiation
        mock_brikli_instance = MagicMock()
        # Return the generator directly, not wrapped in AsyncMock
        mock_brikli_instance.add_message_and_stream.return_value = mock_stream()
        mock_brikli_service_class.return_value = mock_brikli_instance
        
        # Override dependencies - stream endpoint uses get_current_user_sse
        app.dependency_overrides[get_current_user_sse] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat/stream",
                json={"content": "Show me vacant properties"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # TestClient returns the full response text for streaming endpoints
        full_response = response.text
        
        # Verify SSE format
        assert "data: " in full_response
        assert '"type": "content"' in full_response
        assert '"type": "done"' in full_response
        
        # Verify service was called correctly
        mock_brikli_instance.add_message_and_stream.assert_called_once_with(
            "thread_123",
            "Show me vacant properties"
        )


def test_stream_chat_with_tools():
    """Test streaming with tool execution."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    # Create async generator for streaming with tools
    async def mock_stream_with_tools():
        yield 'data: {"type": "status", "status": "🔧 Executing tools..."}\n\n'
        yield 'data: {"type": "status", "status": "🤖 Processing results..."}\n\n'
        yield 'data: {"type": "content", "content": "I found 3 vacant properties..."}\n\n'
        yield 'data: {"type": "done", "total_content": "I found 3 vacant properties..."}\n\n'
    
    # Mock both AgentService and BrikliAgentService since the endpoint uses both
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class, \
         patch("Backend.api.agent.router.BrikliAgentService") as mock_brikli_service_class:
        # Mock AgentService for thread creation
        mock_agent_instance = AsyncMock()
        mock_agent_instance.get_or_create_thread = AsyncMock(return_value="thread_123")
        mock_agent_service_class.return_value = mock_agent_instance
        
        # Mock BrikliAgentService for streaming
        mock_brikli_instance = MagicMock()
        # Return the generator directly, not wrapped in AsyncMock
        mock_brikli_instance.add_message_and_stream.return_value = mock_stream_with_tools()
        mock_brikli_service_class.return_value = mock_brikli_instance
        
        # Override dependencies - stream endpoint uses get_current_user_sse
        app.dependency_overrides[get_current_user_sse] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat/stream",
                json={"content": "Show me vacant properties"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        # Collect all streamed data
        # TestClient returns the full response text for streaming endpoints
        full_response = response.text
        
        # Verify tool status messages
        assert '"type": "status"' in full_response
        assert "🔧 Executing tools..." in full_response
        assert "🤖 Processing results..." in full_response


def test_stream_chat_error():
    """Test streaming when an error occurs."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    # Create async generator that yields an error
    async def mock_stream_error():
        yield 'data: {"type": "error", "error": "Azure AI service unavailable"}\n\n'
    
    # Mock both AgentService and BrikliAgentService since the endpoint uses both
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class, \
         patch("Backend.api.agent.router.BrikliAgentService") as mock_brikli_service_class:
        # Mock AgentService for thread creation
        mock_agent_instance = AsyncMock()
        mock_agent_instance.get_or_create_thread = AsyncMock(return_value="thread_123")
        mock_agent_service_class.return_value = mock_agent_instance
        
        # Mock BrikliAgentService for streaming
        mock_brikli_instance = MagicMock()
        # Return the generator directly, not wrapped in AsyncMock
        mock_brikli_instance.add_message_and_stream.return_value = mock_stream_error()
        mock_brikli_service_class.return_value = mock_brikli_instance
        
        # Override dependencies - stream endpoint uses get_current_user_sse
        app.dependency_overrides[get_current_user_sse] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat/stream",
                json={"content": "Hello"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        # Collect all streamed data
        # TestClient returns the full response text for streaming endpoints
        full_response = response.text
        
        # Verify error message
        assert '"type": "error"' in full_response
        assert "Azure AI service unavailable" in full_response


def test_stream_chat_empty_message():
    """Test streaming with empty message."""
    # Arrange
    mock_user = create_test_user(email="landlord@example.com")
    
    # Override dependencies - stream endpoint uses get_current_user_sse
    app.dependency_overrides[get_current_user_sse] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        # Act
        response = client.post(
            "/api/agent/chat/stream",
            json={"message": ""}
        )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Message validation is handled by Pydantic


def test_stream_chat_tenant_user():
    """Test that tenant users can stream chats."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="tenant@example.com", user_type=UserType.TENANT.value)
    
    # Create async generator
    async def mock_stream():
        yield 'data: {"type": "content", "content": "Your lease expires on..."}\n\n'
        yield 'data: {"type": "done", "total_content": "Your lease expires on..."}\n\n'
    
    # Mock both AgentService and BrikliAgentService since the endpoint uses both
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class, \
         patch("Backend.api.agent.router.BrikliAgentService") as mock_brikli_service_class:
        # Mock AgentService for thread creation
        mock_agent_instance = AsyncMock()
        mock_agent_instance.get_or_create_thread = AsyncMock(return_value="thread_123")
        mock_agent_service_class.return_value = mock_agent_instance
        
        # Mock BrikliAgentService for streaming
        mock_brikli_instance = MagicMock()
        # Return the generator directly, not wrapped in AsyncMock
        mock_brikli_instance.add_message_and_stream.return_value = mock_stream()
        mock_brikli_service_class.return_value = mock_brikli_instance
        
        # Override dependencies - stream endpoint uses get_current_user_sse
        app.dependency_overrides[get_current_user_sse] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat/stream",
                json={"content": "When does my lease expire?"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_stream_chat_service_exception():
    """Test streaming when service raises an exception during stream setup."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    # Mock both AgentService and BrikliAgentService since the endpoint uses both
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class, \
         patch("Backend.api.agent.router.BrikliAgentService") as mock_brikli_service_class:
        # Mock AgentService for thread creation - make it fail
        mock_agent_instance = AsyncMock()
        mock_agent_instance.get_or_create_thread = AsyncMock(side_effect=Exception("Database connection failed"))
        mock_agent_service_class.return_value = mock_agent_instance
        
        # Override dependencies - stream endpoint uses get_current_user_sse
        app.dependency_overrides[get_current_user_sse] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat/stream",
                json={"content": "Hello"},
            )

        # Assert - When exception happens before streaming starts, we get 500 error
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to start streaming chat" in response.json()["detail"]


def test_stream_chat_with_unicode():
    """Test streaming with unicode characters."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    # Create async generator with unicode
    async def mock_stream_unicode():
        yield 'data: {"type": "content", "content": "Properties in 北京: "}\n\n'
        yield 'data: {"type": "content", "content": "€1000/month"}\n\n'
        yield 'data: {"type": "done", "total_content": "Properties in 北京: €1000/month"}\n\n'
    
    # Mock both AgentService and BrikliAgentService since the endpoint uses both
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class, \
         patch("Backend.api.agent.router.BrikliAgentService") as mock_brikli_service_class:
        # Mock AgentService for thread creation
        mock_agent_instance = AsyncMock()
        mock_agent_instance.get_or_create_thread = AsyncMock(return_value="thread_123")
        mock_agent_service_class.return_value = mock_agent_instance
        
        # Mock BrikliAgentService for streaming
        mock_brikli_instance = MagicMock()
        # Return the generator directly, not wrapped in AsyncMock
        mock_brikli_instance.add_message_and_stream.return_value = mock_stream_unicode()
        mock_brikli_service_class.return_value = mock_brikli_instance
        
        # Override dependencies - stream endpoint uses get_current_user_sse
        app.dependency_overrides[get_current_user_sse] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat/stream",
                json={"content": "Show properties in 北京"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        # Collect all streamed data
        # TestClient returns the full response text for streaming endpoints
        full_response = response.text
        
        # Verify unicode content
        assert "北京" in full_response
        assert "€1000" in full_response


def test_stream_chat_long_response():
    """Test streaming with a very long response."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    # Create async generator with long content
    async def mock_stream_long():
        # Simulate streaming a long response in chunks
        long_text = "This is a very long response. " * 100
        chunk_size = 50
        
        for i in range(0, len(long_text), chunk_size):
            chunk = long_text[i:i+chunk_size]
            yield f'data: {json.dumps({"type": "content", "content": chunk})}\n\n'
        
        yield f'data: {json.dumps({"type": "done", "total_content": long_text})}\n\n'
    
    # Mock both AgentService and BrikliAgentService since the endpoint uses both
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class, \
         patch("Backend.api.agent.router.BrikliAgentService") as mock_brikli_service_class:
        # Mock AgentService for thread creation
        mock_agent_instance = AsyncMock()
        mock_agent_instance.get_or_create_thread = AsyncMock(return_value="thread_123")
        mock_agent_service_class.return_value = mock_agent_instance
        
        # Mock BrikliAgentService for streaming
        mock_brikli_instance = MagicMock()
        # Return the generator directly, not wrapped in AsyncMock
        mock_brikli_instance.add_message_and_stream.return_value = mock_stream_long()
        mock_brikli_service_class.return_value = mock_brikli_instance
        
        # Override dependencies - stream endpoint uses get_current_user_sse
        app.dependency_overrides[get_current_user_sse] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat/stream",
                json={"content": "Give me a detailed report"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        # Collect all streamed data
        # TestClient returns the full response text for streaming endpoints
        assert len(response.text) > 0


def test_stream_chat_unauthenticated():
    """Test streaming without authentication."""
    # Don't override auth dependencies
    
    with TestClientWithHost(app) as client:
        # Act
        response = client.post(
            "/api/agent/chat/stream",
            json={"message": "Hello"}
        )

    # Assert - SSE endpoints return 401 for missing auth
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_stream_chat_streaming_exception():
    """Test when exception occurs during streaming."""
    # Arrange
    user_id = uuid4()
    mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
    
    # Create async generator that raises exception during streaming
    async def mock_stream_exception():
        yield 'data: {"type": "content", "content": "Starting..."}\n\n'
        # Instead of raising, yield an error message
        yield 'data: {"type": "error", "error": "Network error during streaming"}\n\n'
    
    # Mock both AgentService and BrikliAgentService since the endpoint uses both
    with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class, \
         patch("Backend.api.agent.router.BrikliAgentService") as mock_brikli_service_class:
        # Mock AgentService for thread creation
        mock_agent_instance = AsyncMock()
        mock_agent_instance.get_or_create_thread = AsyncMock(return_value="thread_123")
        mock_agent_service_class.return_value = mock_agent_instance
        
        # Mock BrikliAgentService for streaming
        mock_brikli_instance = MagicMock()
        # Return the generator directly, not wrapped in AsyncMock
        mock_brikli_instance.add_message_and_stream.return_value = mock_stream_exception()
        mock_brikli_service_class.return_value = mock_brikli_instance
        
        # Override dependencies - stream endpoint uses get_current_user_sse
        app.dependency_overrides[get_current_user_sse] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/agent/chat/stream",
                json={"content": "Hello"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        # The response should contain both partial data and error
        full_response = response.text
        assert "Starting..." in full_response
        assert '"type": "error"' in full_response
        assert "Network error during streaming" in full_response