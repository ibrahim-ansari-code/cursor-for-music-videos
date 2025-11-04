"""
Unit tests for auth dependencies JIT (Just-In-Time) user creation.

Tests error handling for database schema mismatches and JIT failures.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from Backend.api.auth.dependencies import get_current_user
from Backend.models.user import User

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_supabase_jwt():
    """Create a mock Supabase JWT token as HTTPAuthorizationCredentials."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock.jwt.token")


@pytest.fixture
def mock_supabase_user():
    """Create a mock Supabase user."""
    mock_user = Mock()
    mock_user.id = str(uuid4())
    mock_user.email = "test@example.com"
    mock_user.user_metadata = {
        "first_name": "Test",
        "last_name": "User",
        "user_type": "LANDLORD"
    }
    return mock_user


class TestJITUserCreation:
    """Tests for Just-In-Time user creation error handling."""
    
    @pytest.mark.asyncio
    async def test_jit_schema_mismatch_notification_table(self, mock_session, mock_supabase_jwt, mock_supabase_user):
        """Test JIT failure due to missing notification_preferences table."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # User doesn't exist
        mock_session.execute.return_value = mock_result
        mock_session.get = AsyncMock(return_value=None)  # User still doesn't exist on recheck
        
        # Mock the nested transaction context manager
        mock_nested = AsyncMock()
        mock_nested.__aenter__ = AsyncMock(return_value=mock_nested)
        mock_nested.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin_nested = Mock(return_value=mock_nested)
        
        mock_session.add = Mock()
        mock_session.flush = AsyncMock(side_effect=Exception("relation \"notification_preferences\" does not exist"))
        
        mock_supabase_client = Mock()
        mock_supabase_client.auth.get_user.return_value = Mock(user=mock_supabase_user)
        
        with patch('Backend.api.auth.dependencies.get_supabase_client', return_value=mock_supabase_client):
            with pytest.raises(HTTPException) as exc_info:
                # Act
                await get_current_user(mock_supabase_jwt, mock_session)
            
            # Assert
            assert exc_info.value.status_code == 503
            assert "X-Error-Type" in exc_info.value.headers
            assert exc_info.value.headers["X-Error-Type"] == "schema_mismatch"
            assert "Retry-After" in exc_info.value.headers
    
    @pytest.mark.asyncio
    async def test_jit_schema_mismatch_trigger_error(self, mock_session, mock_supabase_jwt, mock_supabase_user):
        """Test JIT failure due to database trigger error."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.get = AsyncMock(return_value=None)
        
        # Mock the nested transaction context manager
        mock_nested = AsyncMock()
        mock_nested.__aenter__ = AsyncMock(return_value=mock_nested)
        mock_nested.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin_nested = Mock(return_value=mock_nested)
        
        mock_session.add = Mock()
        mock_session.flush = AsyncMock(side_effect=Exception("trigger function failed: undefined table"))
        
        mock_supabase_client = Mock()
        mock_supabase_client.auth.get_user.return_value = Mock(user=mock_supabase_user)
        
        with patch('Backend.api.auth.dependencies.get_supabase_client', return_value=mock_supabase_client):
            with pytest.raises(HTTPException) as exc_info:
                # Act
                await get_current_user(mock_supabase_jwt, mock_session)
            
            # Assert
            assert exc_info.value.status_code == 503
    
    @pytest.mark.asyncio
    async def test_jit_generic_failure(self, mock_session, mock_supabase_jwt, mock_supabase_user):
        """Test JIT failure due to generic database error."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.get = AsyncMock(return_value=None)
        
        # Mock the nested transaction context manager
        mock_nested = AsyncMock()
        mock_nested.__aenter__ = AsyncMock(return_value=mock_nested)
        mock_nested.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin_nested = Mock(return_value=mock_nested)
        
        mock_session.add = Mock()
        mock_session.flush = AsyncMock(side_effect=Exception("Generic database error"))
        
        mock_supabase_client = Mock()
        mock_supabase_client.auth.get_user.return_value = Mock(user=mock_supabase_user)
        
        with patch('Backend.api.auth.dependencies.get_supabase_client', return_value=mock_supabase_client):
            with pytest.raises(HTTPException) as exc_info:
                # Act
                await get_current_user(mock_supabase_jwt, mock_session)
            
            # Assert
            assert exc_info.value.status_code == 500
            assert exc_info.value.headers["X-Error-Type"] == "jit_creation_failed"
    
    @pytest.mark.asyncio
    async def test_jit_success(self, mock_session, mock_supabase_jwt, mock_supabase_user):
        """Test successful JIT user creation."""
        # Arrange
        user_id = uuid4()
        created_user = User(
            id=user_id,
            email="test@example.com",
            first_name="Test",
            last_name="User",
            user_type="LANDLORD",
            is_active=True,
            is_admin=False,
            is_email_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.get = AsyncMock(return_value=None)  # User doesn't exist on recheck
        
        # Mock the nested transaction context manager
        mock_nested = AsyncMock()
        mock_nested.__aenter__ = AsyncMock(return_value=mock_nested)
        mock_nested.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin_nested = Mock(return_value=mock_nested)
        
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Patch User creation to return our created_user
        mock_supabase_client = Mock()
        mock_supabase_client.auth.get_user.return_value = Mock(user=mock_supabase_user)
        
        with patch('Backend.api.auth.dependencies.get_supabase_client', return_value=mock_supabase_client):
            with patch('Backend.api.auth.dependencies.User.model_validate', return_value=created_user):
                # Act
                result = await get_current_user(mock_supabase_jwt, mock_session)
                
                # Assert
                assert result.id == user_id
                assert result.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_existing_user_no_jit(self, mock_session, mock_supabase_jwt, mock_supabase_user):
        """Test retrieving existing user without JIT."""
        # Arrange
        user_id = uuid4()
        existing_user = User(
            id=user_id,
            email="test@example.com",
            first_name="Test",
            last_name="User",
            user_type="LANDLORD",
            is_active=True,
            is_admin=False,
            is_email_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_session.execute.return_value = mock_result
        mock_session.get = AsyncMock(return_value=existing_user)
        
        mock_supabase_client = Mock()
        mock_supabase_client.auth.get_user.return_value = Mock(user=mock_supabase_user)
        
        with patch('Backend.api.auth.dependencies.get_supabase_client', return_value=mock_supabase_client):
            # Act
            result = await get_current_user(mock_supabase_jwt, mock_session)
            
            # Assert
            assert result.id == user_id
            assert result.email == "test@example.com"
            # JIT should not have been triggered
            assert not mock_session.add.called

