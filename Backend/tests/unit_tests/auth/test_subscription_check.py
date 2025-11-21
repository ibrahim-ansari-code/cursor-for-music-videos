"""
Unit tests for subscription check logic in auth dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from Backend.api.auth.dependencies import get_current_user
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.config import settings


@pytest.fixture
def mock_request_get():
    """Create a mock GET request."""
    request = MagicMock()
    request.method = "GET"
    request.headers = {}
    request.url = MagicMock()
    request.url.path = "/api/test"
    return request


@pytest.fixture
def mock_request_post():
    """Create a mock POST request."""
    request = MagicMock()
    request.method = "POST"
    request.headers = {}
    request.url = MagicMock()
    request.url.path = "/api/test"
    return request


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_user_with_active_subscription():
    """Create a mock user with active subscription."""
    return User(
        id=uuid4(),
        email="active@example.com",
        user_type=UserType.LANDLORD,
        is_active=True,
        is_email_verified=True,
        subscription_status='active',
        subscription_tier='premium',
        trial_ends_at=None,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_user_with_trial():
    """Create a mock user with active trial."""
    future_date = datetime.now(timezone.utc) + timedelta(days=7)
    return User(
        id=uuid4(),
        email="trial@example.com",
        user_type=UserType.LANDLORD,
        is_active=True,
        is_email_verified=True,
        subscription_status='trialing',
        subscription_tier='trial',
        trial_ends_at=future_date,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_user_expired_trial():
    """Create a mock user with expired trial."""
    past_date = datetime.now(timezone.utc) - timedelta(days=1)
    return User(
        id=uuid4(),
        email="expired@example.com",
        user_type=UserType.LANDLORD,
        is_active=True,
        is_email_verified=True,
        subscription_status='canceled',
        subscription_tier=None,
        trial_ends_at=past_date,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user without subscription."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        user_type=UserType.LANDLORD,
        is_active=True,
        is_email_verified=True,
        subscription_status=None,
        subscription_tier=None,
        trial_ends_at=None,
        is_admin=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


class TestSubscriptionCheck:
    """Test subscription check logic in get_current_user."""

    @patch('Backend.api.auth.dependencies.get_supabase_client')
    async def test_get_request_bypasses_subscription_check(
        self, mock_get_supabase_client, mock_session, mock_user_expired_trial, mock_request_get
    ):
        """Test that GET requests bypass subscription check."""
        # Arrange
        mock_supabase = MagicMock()
        mock_user_response = MagicMock()
        mock_user_response.user = MagicMock(
            id=mock_user_expired_trial.id,
            email=mock_user_expired_trial.email,
            user_metadata={}
        )
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_get_supabase_client.return_value = mock_supabase

        mock_session.get = AsyncMock(return_value=mock_user_expired_trial)
        
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"

        # Act - Should succeed despite expired trial because it's a GET request
        user = await get_current_user(mock_request_get, credentials, mock_session, check_subscription=True)

        # Assert
        assert user == mock_user_expired_trial

    @patch('Backend.api.auth.dependencies.get_supabase_client')
    async def test_post_request_with_active_subscription_succeeds(
        self, mock_get_supabase_client, mock_session, mock_user_with_active_subscription, mock_request_post
    ):
        """Test that POST request with active subscription succeeds."""
        # Arrange
        mock_supabase = MagicMock()
        mock_user_response = MagicMock()
        mock_user_response.user = MagicMock(
            id=mock_user_with_active_subscription.id,
            email=mock_user_with_active_subscription.email,
            user_metadata={}
        )
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_get_supabase_client.return_value = mock_supabase

        mock_session.get = AsyncMock(return_value=mock_user_with_active_subscription)
        
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"

        # Act
        user = await get_current_user(mock_request_post, credentials, mock_session, check_subscription=True)

        # Assert
        assert user == mock_user_with_active_subscription

    @patch('Backend.api.auth.dependencies.get_supabase_client')
    async def test_post_request_with_active_trial_succeeds(
        self, mock_get_supabase_client, mock_session, mock_user_with_trial, mock_request_post
    ):
        """Test that POST request with active trial succeeds."""
        # Arrange
        mock_supabase = MagicMock()
        mock_user_response = MagicMock()
        mock_user_response.user = MagicMock(
            id=mock_user_with_trial.id,
            email=mock_user_with_trial.email,
            user_metadata={}
        )
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_get_supabase_client.return_value = mock_supabase

        mock_session.get = AsyncMock(return_value=mock_user_with_trial)
        
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"

        # Act
        user = await get_current_user(mock_request_post, credentials, mock_session, check_subscription=True)

        # Assert
        assert user == mock_user_with_trial

    @patch('Backend.api.auth.dependencies.get_supabase_client')
    async def test_post_request_with_expired_trial_fails(
        self, mock_get_supabase_client, mock_session, mock_user_expired_trial, mock_request_post
    ):
        """Test that POST request with expired trial returns 402."""
        # Arrange
        mock_supabase = MagicMock()
        mock_user_response = MagicMock()
        mock_user_response.user = MagicMock(
            id=mock_user_expired_trial.id,
            email=mock_user_expired_trial.email,
            user_metadata={}
        )
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_get_supabase_client.return_value = mock_supabase

        mock_session.get = AsyncMock(return_value=mock_user_expired_trial)
        
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request_post, credentials, mock_session, check_subscription=True)
        
        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["code"] == "SUBSCRIPTION_REQUIRED"
        assert "Active subscription required" in exc_info.value.detail["message"]

    @patch('Backend.api.auth.dependencies.get_supabase_client')
    async def test_admin_bypasses_subscription_check(
        self, mock_get_supabase_client, mock_session, mock_admin_user, mock_request_post
    ):
        """Test that admin users bypass subscription check."""
        # Arrange
        mock_supabase = MagicMock()
        mock_user_response = MagicMock()
        mock_user_response.user = MagicMock(
            id=mock_admin_user.id,
            email=mock_admin_user.email,
            user_metadata={}
        )
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_get_supabase_client.return_value = mock_supabase

        mock_session.get = AsyncMock(return_value=mock_admin_user)
        
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"

        # Act - Should succeed despite no subscription because user is admin
        user = await get_current_user(mock_request_post, credentials, mock_session, check_subscription=True)

        # Assert
        assert user == mock_admin_user

    @patch('Backend.api.auth.dependencies.get_supabase_client')
    async def test_subscription_check_disabled_allows_access(
        self, mock_get_supabase_client, mock_session, mock_user_expired_trial, mock_request_post
    ):
        """Test that check_subscription=False bypasses subscription check."""
        # Arrange
        mock_supabase = MagicMock()
        mock_user_response = MagicMock()
        mock_user_response.user = MagicMock(
            id=mock_user_expired_trial.id,
            email=mock_user_expired_trial.email,
            user_metadata={}
        )
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_get_supabase_client.return_value = mock_supabase

        mock_session.get = AsyncMock(return_value=mock_user_expired_trial)
        
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"

        # Act - Should succeed because check_subscription=False
        user = await get_current_user(mock_request_post, credentials, mock_session, check_subscription=False)

        # Assert
        assert user == mock_user_expired_trial

