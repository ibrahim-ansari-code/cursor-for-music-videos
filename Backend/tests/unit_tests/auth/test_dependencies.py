"""
Unit tests for auth dependencies.
"""
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException, Request, Depends
import jwt
from fastapi.security import HTTPAuthorizationCredentials

from Backend.api.auth.dependencies import (
    get_current_user,
    get_current_user_sse,
    get_current_active_user,
    get_current_admin_user,
    get_current_verified_user,
)
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.config import settings


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create a mock user with active subscription for testing."""
    return User(
        id=uuid4(),
        email="test@example.com",
        user_type=UserType.LANDLORD,
        is_active=True,
        is_email_verified=True,
        subscription_status='active',  # Active subscription for tests
        subscription_tier='premium',
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def valid_token(mock_user):
    """Create a valid JWT token."""
    payload = {
        "sub": str(mock_user.id),
        "email": mock_user.email,
        "exp": datetime.now(UTC).timestamp() + 3600
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.fixture
def expired_token(mock_user):
    """Create an expired JWT token."""
    payload = {
        "sub": str(mock_user.id),
        "email": mock_user.email,
        "exp": datetime.now(UTC).timestamp() - 3600
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.fixture
def mock_request():
    """Create a mock request."""
    request = MagicMock(spec=Request)
    request.headers = {}
    return request


class TestAuthDependencies:
    """Test cases for auth dependencies."""

    @patch('Backend.api.auth.dependencies.get_supabase_client')
    async def test_get_current_user_success(self, mock_get_supabase_client, mock_session, mock_user, valid_token, mock_request):
        """Test successful retrieval of an existing user."""
        # Arrange
        mock_supabase = MagicMock()
        mock_user_response = MagicMock()
        mock_user_response.user = MagicMock(id=mock_user.id, email=mock_user.email, user_metadata={})
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_get_supabase_client.return_value = mock_supabase

        mock_session.get = AsyncMock(return_value=mock_user)
        
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = valid_token

        # Act
        user = await get_current_user(mock_request, credentials, mock_session)

        # Assert
        assert user == mock_user
        mock_session.get.assert_called_once_with(User, mock_user.id)
        mock_supabase.auth.get_user.assert_called_once_with(valid_token)

    @patch('Backend.api.auth.dependencies.get_supabase_client')
    @patch('Backend.api.auth.dependencies.sentry_sdk')
    async def test_get_current_user_not_synced_from_webhook(self, mock_sentry, mock_get_supabase_client, mock_session, mock_user, valid_token, mock_request):
        """Test user not found returns 401 when webhook hasn't synced user yet."""
        # Arrange
        mock_supabase = MagicMock()
        mock_user_response = MagicMock()
        mock_user_response.user = MagicMock(
            id=mock_user.id, 
            email=mock_user.email,
            user_metadata={"full_name": "Test User"}
        )
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_get_supabase_client.return_value = mock_supabase

        # User not found in local DB (webhook hasn't synced yet)
        mock_session.get = AsyncMock(return_value=None)
        
        # Mock the scalar result for the select query fallback
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock Sentry
        mock_scope = MagicMock()
        mock_sentry.push_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sentry.push_scope.return_value.__exit__ = MagicMock(return_value=None)

        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = valid_token
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, credentials, mock_session)
        
        # Verify error details
        assert exc_info.value.status_code == 401
        assert "not been properly synchronized" in exc_info.value.detail
        assert "support@brikli.com" in exc_info.value.detail
        assert exc_info.value.headers["X-Error-Type"] == "user_not_synced"
        
        # Verify Sentry was called
        mock_sentry.capture_message.assert_called_once()
        assert "not synced from Supabase" in mock_sentry.capture_message.call_args[0][0]
        
    @patch('Backend.api.auth.dependencies.get_supabase_client')
    async def test_get_current_user_sse_success(self, mock_get_supabase_client, mock_session, mock_user, valid_token, mock_request):
        """Test getting current user for SSE endpoint."""
        # Arrange
        mock_request.headers = {"authorization": f"Bearer {valid_token}"}
        
        mock_supabase = MagicMock()
        mock_user_response = MagicMock()
        mock_user_response.user = MagicMock(id=mock_user.id, email=mock_user.email, user_metadata={})
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_get_supabase_client.return_value = mock_supabase

        mock_session.get.return_value = mock_user

        # Act
        user = await get_current_user_sse(mock_request, mock_session)

        # Assert
        assert user == mock_user
        mock_supabase.auth.get_user.assert_called_once_with(valid_token)


    async def test_get_current_active_user_success(self, mock_user):
        """Test getting current active user."""
        # Act
        user = await get_current_active_user(mock_user)
        
        # Assert
        assert user == mock_user

    async def test_get_current_active_user_inactive(self, mock_user):
        """Test getting inactive user raises exception."""
        # Arrange
        mock_user.is_active = False
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(mock_user)
        
        assert exc_info.value.status_code == 400
        assert "Inactive user" in str(exc_info.value.detail)

    @patch('Backend.api.auth.dependencies.get_supabase_client')
    async def test_get_current_user_invalid_token(self, mock_get_supabase_client, mock_session, mock_request):
        """Test get_current_user with invalid token."""
        # Arrange
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.side_effect = Exception("Invalid token")
        mock_get_supabase_client.return_value = mock_supabase
        
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "invalid_token"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, credentials, mock_session)
        
        assert exc_info.value.status_code == 500  # It's 500 because we caught a generic Exception
        assert "Authentication service temporarily unavailable. Please try again." in str(exc_info.value.detail)

    @patch('Backend.api.auth.dependencies.get_supabase_client')
    async def test_get_current_user_supabase_error(self, mock_get_supabase_client, mock_session, mock_request):
        """Test get_current_user with Supabase returning None."""
        # Arrange
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value = None
        mock_get_supabase_client.return_value = mock_supabase
        
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, credentials, mock_session)
        
        assert exc_info.value.status_code == 401

    @patch('Backend.api.auth.dependencies.get_supabase_client')
    async def test_get_current_user_unexpected_error(self, mock_get_supabase_client, mock_session, mock_request):
        """Test get_current_user with unexpected error."""
        # Arrange
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.side_effect = RuntimeError("Unexpected error")
        mock_get_supabase_client.return_value = mock_supabase
        
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, credentials, mock_session)
        
        assert exc_info.value.status_code == 500
        assert "Authentication service temporarily unavailable. Please try again." in str(exc_info.value.detail)

    @patch('Backend.api.auth.dependencies.get_token_from_request')
    async def test_get_current_user_sse_no_auth_header(self, mock_get_token, mock_session, mock_request):
        """Test get_current_user_sse without authorization header."""
        # Arrange
        mock_request.headers = {}
        mock_get_token.side_effect = HTTPException(
            status_code=401, 
            detail="No valid authentication token provided. Use Authorization header or 'token' query parameter.",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_sse(mock_request, mock_session)
        
        assert exc_info.value.status_code == 401  # get_token_from_request raises 401
        assert "No valid authentication token provided" in str(exc_info.value.detail)

    @patch('Backend.api.auth.dependencies.get_token_from_request')
    async def test_get_current_user_sse_invalid_header_format(self, mock_get_token, mock_session, mock_request):
        """Test get_current_user_sse with invalid header format."""
        # Arrange
        mock_request.headers = {"authorization": "InvalidFormat"}
        mock_get_token.side_effect = HTTPException(
            status_code=401, 
            detail="No valid authentication token provided. Use Authorization header or 'token' query parameter.",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_sse(mock_request, mock_session)
        
        assert exc_info.value.status_code == 401  # get_token_from_request raises 401
        assert "No valid authentication token provided" in str(exc_info.value.detail)