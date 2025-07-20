"""
Additional API tests for agent router to improve coverage.
"""
from datetime import datetime, timezone
import json
import pytest
from fastapi import status
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from Backend.api.app import app
from Backend.api.auth.dependencies import get_current_user, get_current_user_sse
from Backend.database import get_session
from Backend.tests.api_tests.utilities import TestClientWithHost, create_test_user


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Clear FastAPI dependency overrides before and after each test."""
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


class TestAgentRouterCoverage:
    """Additional test cases for agent router coverage."""

    def test_streaming_error_handling(self):
        """Test streaming endpoint error handling."""
        # Arrange
        mock_user = create_test_user(email="landlord@example.com")
        mock_service = AsyncMock()
        mock_service.get_or_create_thread.side_effect = Exception("Database error")
        
        with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
            mock_agent_service_class.return_value = mock_service
            
            # Override dependencies
            app.dependency_overrides[get_current_user_sse] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()

            with TestClientWithHost(app) as client:
                # Act
                response = client.post("/api/agent/chat/stream", json={"content": "Hello"})

            # Assert
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to start streaming chat" in response.json()["detail"]

    def test_streaming_generator_error(self):
        """Test streaming generator error during stream."""
        # Arrange
        mock_user = create_test_user(email="landlord@example.com")
        mock_service = AsyncMock()
        mock_service.get_or_create_thread.return_value = "thread_123"
        
        mock_agent = AsyncMock()
        
        async def failing_generator():
            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting...'})}\n\n"
            raise Exception("Stream failed")
        
        mock_agent.add_message_and_stream.return_value = failing_generator()
        
        with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
            mock_agent_service_class.return_value = mock_service
            
            with patch("Backend.api.agent.router.BrikliAgentService") as mock_brikli_service_class:
                mock_brikli_service_class.return_value = mock_agent
                
                # Override dependencies
                app.dependency_overrides[get_current_user_sse] = lambda: mock_user
                app.dependency_overrides[get_session] = lambda: AsyncMock()

                with TestClientWithHost(app) as client:
                    # Act - Stream the response
                    with client.stream("POST", "/api/agent/chat/stream", json={"content": "Hello"}) as response:
                        # Assert
                        assert response.status_code == status.HTTP_200_OK
                        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
                        
                        # Read the stream content
                        content = b""
                        for chunk in response.iter_bytes():
                            content += chunk
                            if b"error" in content:
                                break
                        
                        # Should contain error message
                        assert b"Streaming error occurred" in content or b"error" in content

    def test_clear_chat_service_error(self):
        """Test clear chat with service error."""
        # Arrange
        mock_user = create_test_user(email="landlord@example.com")
        mock_service = AsyncMock()
        mock_service.clear_chat.side_effect = Exception("Failed to delete thread")
        
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

    def test_get_chat_history_empty_messages(self):
        """Test getting chat history with empty message list."""
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
                response = client.get("/api/agent/chat/history?limit=50")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["messages"] == []
            assert data["thread_id"] is None
            assert data["total"] == 0
            
            # Verify service was called correctly
            mock_service.get_chat_history.assert_called_once_with(user_id, 50)

    def test_start_chat_with_long_message(self):
        """Test starting chat with message at max length."""
        # Arrange
        mock_user = create_test_user(email="landlord@example.com")
        long_message = "x" * 4000  # Max length
        
        mock_service = AsyncMock()
        mock_service.start_chat.return_value = {
            "thread_id": "thread_123",
            "run_id": "run_123",
            "status": "queued"
        }
        
        # Create a proper async session mock
        mock_session = AsyncMock()
        
        with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
            mock_agent_service_class.return_value = mock_service
            
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                # Act - Use the correct endpoint
                response = client.post("/api/agent/chat", json={"content": long_message})

            # Assert
            assert response.status_code == status.HTTP_200_OK
            mock_service.start_chat.assert_called_once_with(mock_user.id, long_message)

    def test_get_conversations_empty_list(self):
        """Test getting conversations when user has none."""
        # Arrange
        mock_user = create_test_user(email="landlord@example.com")
        mock_service = AsyncMock()
        mock_service.list_conversations.return_value = {
            "conversations": [],
            "total": 0
        }
        
        # Create a proper async session mock
        mock_session = AsyncMock()
        
        with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
            mock_agent_service_class.return_value = mock_service
            
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                # Act
                response = client.get("/api/agent/conversations")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["conversations"] == []
            assert data["total"] == 0

    def test_chat_status_with_tool_execution_status(self):
        """Test chat status with tool execution in progress."""
        # Arrange
        mock_user = create_test_user(email="landlord@example.com")
        thread_id = "thread_123"
        run_id = "run_123"
        
        mock_service = AsyncMock()
        mock_service.get_chat_status.return_value = {
            "status": "processing_tools",
            "thread_id": thread_id,
            "run_id": run_id,
            "message": "Executing tools and processing results..."
        }
        
        # Create a proper async session mock
        mock_session = AsyncMock()
        
        with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
            mock_agent_service_class.return_value = mock_service
            
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                # Act
                response = client.get(f"/api/agent/chat/status?thread_id={thread_id}&run_id={run_id}")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "processing_tools"
            assert "Executing tools" in data["message"]

    def test_streaming_with_empty_message(self):
        """Test streaming endpoint with empty message content."""
        # Arrange
        mock_user = create_test_user(email="landlord@example.com")
        
        # Override dependencies
        app.dependency_overrides[get_current_user_sse] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Act - Send empty string message (should fail validation)
            response = client.post("/api/agent/chat/stream", json={"content": ""})

        # Assert - Should fail validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_chat_history_with_custom_limit(self):
        """Test getting chat history with custom limit."""
        # Arrange
        user_id = uuid4()
        mock_user = create_test_user(user_id=user_id, email="landlord@example.com")
        mock_service = AsyncMock()
        
        # Create many messages
        messages = []
        for i in range(5):
            messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "id": f"msg_{i}"
            })
        
        mock_service.get_chat_history.return_value = {
            "messages": messages,  # Return 5 messages
            "thread_id": "thread_123",
            "total": 5
        }
        
        with patch("Backend.api.agent.router.AgentService") as mock_agent_service_class:
            mock_agent_service_class.return_value = mock_service
            
            # Override dependencies
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()

            with TestClientWithHost(app) as client:
                # Act
                response = client.get("/api/agent/chat/history?limit=5")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["messages"]) == 5
            assert data["thread_id"] == "thread_123"
            assert data["total"] == 5
            
            # Verify service was called correctly
            mock_service.get_chat_history.assert_called_once_with(user_id, 5)

    def test_agent_health_endpoint(self):
        """Test agent health check endpoint."""
        with TestClientWithHost(app) as client:
            # Act
            response = client.get("/api/agent/health")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "agent"
            assert "message" in data