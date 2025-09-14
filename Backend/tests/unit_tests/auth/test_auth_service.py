"""
Unit tests for the AuthService class.

These tests focus on the business logic of authentication services,
mocking external dependencies like database sessions and Supabase client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth.service import AuthService
from Backend.api.auth.schemas import (
    ProfileUpdateRequest,
    UserResponse,
    SupabaseWebhookPayload,
    AvatarUploadResponse
)
from Backend.models.user import User
from Backend.models.enums import UserType


def create_auth_api_error(message, status=None):
    """Create a mock AuthApiError that matches the service's expectations."""
    # Import the actual exception class from supabase_auth
    from supabase_auth.errors import AuthApiError, AuthWeakPasswordError
    
    # Return AuthWeakPasswordError for weak password messages
    if "weak" in message.lower() or ("password" in message.lower() and ("requirements" in message.lower() or "too weak" in message.lower())):
        class MockAuthWeakPasswordError(AuthWeakPasswordError):
            def __init__(self, msg, status_code=None, reasons=None):
                super().__init__(msg, status_code or 400, reasons or ["Password is too weak"])
                self.message = msg
                self.status = status_code or 400
                self.reasons = reasons or ["Password is too weak"]
        return MockAuthWeakPasswordError(message, status)
    
    # Return regular AuthApiError for other cases
    class MockAuthApiError(AuthApiError):
        def __init__(self, msg, status_code=None):
            # Map message to appropriate error code
            if "not found" in msg.lower() or "user not found" in msg.lower():
                error_code = "user_not_found"
            elif "invalid" in msg.lower() or "credentials" in msg.lower():
                error_code = "invalid_credentials"
            elif "too many" in msg.lower() or "rate" in msg.lower():
                error_code = "over_request_rate_limit"
            else:
                error_code = "unexpected_failure"
                
            super().__init__(msg, status_code or 400, error_code)
            self.message = msg
            self.status = status_code or 400
    
    return MockAuthApiError(message, status)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        user_type=UserType.LANDLORD,
        is_active=True,
        is_admin=False,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
        phone="1234567890",
        address="123 Test St",
        city="Test City",
        province="TC",
        postal_code="12345",
        profile_image_url="https://example.com/avatar.jpg"
    )


@pytest.mark.asyncio
async def test_get_user_by_id_success(mock_session, sample_user):
    """Test successful user retrieval by ID."""
    # Arrange
    user_id = sample_user.id
    mock_session.get.return_value = sample_user
    
    # Act
    result = await AuthService.get_user_by_id(user_id, mock_session)
    
    # Assert
    assert result == sample_user
    mock_session.get.assert_called_once_with(User, user_id)


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(mock_session):
    """Test user retrieval when user doesn't exist."""
    # Arrange
    user_id = uuid4()
    mock_session.get.return_value = None
    
    # Act
    result = await AuthService.get_user_by_id(user_id, mock_session)
    
    # Assert
    assert result is None
    mock_session.get.assert_called_once_with(User, user_id)


@pytest.mark.asyncio
async def test_create_user_from_supabase_success(mock_session):
    """Test successful user creation from Supabase data."""
    # Arrange
    supabase_user_id = str(uuid4())
    email = "newuser@example.com"
    metadata = {
        "first_name": "New",
        "last_name": "User",
        "phone": "9876543210",
        "is_email_verified": True
    }
    
    # Mock the nested transaction and SELECT FOR UPDATE
    mock_nested_transaction = AsyncMock()
    mock_session.begin_nested.return_value.__aenter__ = AsyncMock(return_value=mock_nested_transaction)
    mock_session.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)
    
    # Mock the SELECT FOR UPDATE query result (no existing user)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Create a user object for the result
    from uuid import UUID as PythonUUID
    created_user = User(
        id=PythonUUID(supabase_user_id),
        email=email,
        first_name=metadata["first_name"],
        last_name=metadata["last_name"],
        phone=metadata["phone"],
        user_type=UserType.LANDLORD,
        is_email_verified=metadata["is_email_verified"]
    )
    
    # Act
    result = await AuthService.create_user_from_supabase(
        supabase_user_id, email, metadata, mock_session
    )
    
    # Assert
    assert result.email == email
    assert result.first_name == metadata["first_name"]
    assert result.last_name == metadata["last_name"]
    assert result.phone == metadata["phone"]
    assert result.is_email_verified == metadata["is_email_verified"]
    assert result.user_type == UserType.LANDLORD
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()  # Uses flush instead of commit in nested transaction
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_from_supabase_already_exists(mock_session, sample_user):
    """Test user creation when user already exists."""
    # Arrange
    supabase_user_id = str(sample_user.id)
    email = sample_user.email
    metadata = {}
    
    # Mock the nested transaction
    mock_nested_transaction = AsyncMock()
    mock_session.begin_nested.return_value.__aenter__ = AsyncMock(return_value=mock_nested_transaction)
    mock_session.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)
    
    # Mock the SELECT FOR UPDATE query result (user exists)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_user
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await AuthService.create_user_from_supabase(
        supabase_user_id, email, metadata, mock_session
    )
    
    # Assert
    assert result == sample_user
    mock_session.add.assert_not_called()
    mock_session.flush.assert_not_called()  # No flush since user already exists


@pytest.mark.asyncio
async def test_create_user_from_supabase_invalid_id_format(mock_session):
    """Test user creation with invalid UUID format."""
    # Arrange
    supabase_user_id = "not-a-uuid"
    email = "test@example.com"
    metadata = {}
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await AuthService.create_user_from_supabase(
            supabase_user_id, email, metadata, mock_session
        )
    
    assert exc_info.value.status_code == 400
    assert "Invalid user ID format" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_user_from_supabase_database_error(mock_session):
    """Test user creation with database error."""
    # Arrange
    supabase_user_id = str(uuid4())
    email = "test@example.com"
    metadata = {}
    
    # Mock the nested transaction
    mock_nested_transaction = AsyncMock()
    mock_session.begin_nested.return_value.__aenter__ = AsyncMock(return_value=mock_nested_transaction)
    mock_session.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)
    
    # Mock the SELECT FOR UPDATE query result (no existing user)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Make session.flush() raise an exception
    mock_session.flush.side_effect = Exception("Database error")
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await AuthService.create_user_from_supabase(
            supabase_user_id, email, metadata, mock_session
        )
    
    assert exc_info.value.status_code == 500
    assert "Failed to create user" in exc_info.value.detail
    # Note: Nested transactions automatically rollback on exception, so no explicit rollback call


@pytest.mark.asyncio
@patch('Backend.api.auth.service.get_supabase_client')
async def test_verify_user_password_success(mock_get_supabase):
    """Test successful password verification."""
    # Arrange
    email = "test@example.com"
    password = "correct_password"
    mock_supabase = MagicMock()
    mock_auth = MagicMock()
    mock_response = MagicMock()
    mock_response.session = MagicMock()
    
    mock_supabase.auth = mock_auth
    mock_auth.sign_in_with_password.return_value = mock_response
    mock_get_supabase.return_value = mock_supabase
    
    # Act
    result = await AuthService.verify_user_password(email, password)
    
    # Assert
    assert result is True
    mock_auth.sign_in_with_password.assert_called_once_with({
        "email": email,
        "password": password
    })
    mock_auth.sign_out.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.auth.service.get_supabase_client')
async def test_verify_user_password_incorrect(mock_get_supabase):
    """Test password verification with incorrect password."""
    # Arrange
    email = "test@example.com"
    password = "wrong_password"
    mock_supabase = MagicMock()
    mock_auth = MagicMock()
    
    # Create a mock exception that looks like GoTrueApiError
    mock_error = create_auth_api_error("Invalid login credentials")
    
    mock_supabase.auth = mock_auth
    mock_auth.sign_in_with_password.side_effect = mock_error
    mock_get_supabase.return_value = mock_supabase
    
    # Act
    result = await AuthService.verify_user_password(email, password)
    
    # Assert
    assert result is False
    mock_auth.sign_out.assert_not_called()


@pytest.mark.asyncio
@patch('Backend.api.auth.service.get_supabase_client')
async def test_verify_user_password_unexpected_error(mock_get_supabase):
    """Test password verification with unexpected error."""
    # Arrange
    email = "test@example.com"
    password = "password"
    mock_supabase = MagicMock()
    mock_auth = MagicMock()
    
    mock_supabase.auth = mock_auth
    mock_auth.sign_in_with_password.side_effect = Exception("Network error")
    mock_get_supabase.return_value = mock_supabase
    
    # Act
    result = await AuthService.verify_user_password(email, password)
    
    # Assert
    assert result is False


@pytest.mark.asyncio
@patch('Backend.api.auth.service.AuthService.verify_user_password')
@patch('Backend.api.auth.service.get_supabase_client')
async def test_change_user_password_success(mock_get_supabase, mock_verify):
    """Test successful password change."""
    # Arrange
    email = "test@example.com"
    current_password = "old_password"
    new_password = "new_password"
    
    mock_verify.return_value = True  # Current password is correct
    
    mock_supabase = MagicMock()
    mock_auth = MagicMock()
    mock_session = MagicMock()
    mock_auth_response = MagicMock()
    mock_auth_response.session = mock_session
    
    mock_supabase.auth = mock_auth
    mock_auth.sign_in_with_password.return_value = mock_auth_response
    mock_auth.update_user.return_value = MagicMock()
    mock_get_supabase.return_value = mock_supabase
    
    # Act
    result = await AuthService.change_user_password(
        email, current_password, new_password
    )
    
    # Assert
    assert result is True
    mock_verify.assert_called_once_with(email, current_password)
    mock_auth.sign_in_with_password.assert_called_once()
    mock_auth.update_user.assert_called_once_with({"password": new_password})
    mock_auth.sign_out.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.auth.service.AuthService.verify_user_password')
async def test_change_user_password_wrong_current(mock_verify):
    """Test password change with incorrect current password."""
    # Arrange
    email = "test@example.com"
    current_password = "wrong_password"
    new_password = "new_password"
    
    mock_verify.return_value = False  # Current password is incorrect
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await AuthService.change_user_password(
            email, current_password, new_password
        )
    
    assert exc_info.value.status_code == 401
    assert "Current password is incorrect" in exc_info.value.detail


@pytest.mark.asyncio
@patch('Backend.api.auth.service.AuthService.verify_user_password')
@patch('Backend.api.auth.service.get_supabase_client')
async def test_change_user_password_weak_new_password(mock_get_supabase, mock_verify):
    """Test password change with weak new password."""
    # Arrange
    email = "test@example.com"
    current_password = "old_password"
    new_password = "weak"
    
    mock_verify.return_value = True
    
    mock_supabase = MagicMock()
    mock_auth = MagicMock()
    mock_session = MagicMock()
    mock_auth_response = MagicMock()
    mock_auth_response.session = mock_session
    
    # Create a mock exception for weak password
    mock_error = create_auth_api_error("Password is too weak")
    
    mock_supabase.auth = mock_auth
    mock_auth.sign_in_with_password.return_value = mock_auth_response
    mock_auth.update_user.side_effect = mock_error
    mock_get_supabase.return_value = mock_supabase
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await AuthService.change_user_password(
            email, current_password, new_password
        )
    
    assert exc_info.value.status_code == 400
    assert "does not meet security requirements" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_user_profile_success(mock_session, sample_user):
    """Test successful profile update."""
    # Arrange
    profile_update = ProfileUpdateRequest(
        first_name="Updated",
        last_name="Name",
        phone="5555555555"
    )
    
    # Act
    result = await AuthService.update_user_profile(
        sample_user, profile_update, mock_session
    )
    
    # Assert
    assert isinstance(result, UserResponse)
    assert sample_user.first_name == "Updated"
    assert sample_user.last_name == "Name"
    assert sample_user.phone == "5555555555"
    mock_session.add.assert_called_once_with(sample_user)
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once_with(sample_user)


@pytest.mark.asyncio
async def test_update_user_profile_partial(mock_session, sample_user):
    """Test partial profile update."""
    # Arrange
    original_last_name = sample_user.last_name
    profile_update = ProfileUpdateRequest(first_name="OnlyFirst")
    
    # Act
    result = await AuthService.update_user_profile(
        sample_user, profile_update, mock_session
    )
    
    # Assert
    assert sample_user.first_name == "OnlyFirst"
    assert sample_user.last_name == original_last_name  # Unchanged
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.auth.service.get_supabase_client')
async def test_resend_verification_email_success(mock_get_supabase):
    """Test successful email verification resend."""
    # Arrange
    email = "test@example.com"
    mock_supabase = MagicMock()
    mock_auth = MagicMock()
    mock_supabase.auth = mock_auth
    mock_auth.resend.return_value = None  # Success
    mock_get_supabase.return_value = mock_supabase
    
    # Act
    result = await AuthService.resend_verification_email(email)
    
    # Assert
    assert result["success"] is True
    assert "verification email has been sent" in result["message"]
    mock_auth.resend.assert_called_once_with({
        "type": "signup",
        "email": email
    })


@pytest.mark.asyncio
@patch('Backend.api.auth.service.get_supabase_client')
async def test_resend_verification_email_rate_limit(mock_get_supabase):
    """Test email verification resend with rate limiting."""
    # Arrange
    email = "test@example.com"
    mock_supabase = MagicMock()
    mock_auth = MagicMock()
    
    # Create a mock exception that looks like GoTrueApiError
    mock_error = create_auth_api_error("Too many requests", status=429)
    
    mock_supabase.auth = mock_auth
    mock_auth.resend.side_effect = mock_error
    mock_get_supabase.return_value = mock_supabase
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await AuthService.resend_verification_email(email)
    
    assert exc_info.value.status_code == 429
    assert "Too many requests" in exc_info.value.detail


@pytest.mark.asyncio
@patch('Backend.api.auth.service.get_supabase_client')
async def test_resend_verification_email_user_not_found(mock_get_supabase):
    """Test email verification resend for non-existent user."""
    # Arrange
    email = "nonexistent@example.com"
    mock_supabase = MagicMock()
    mock_auth = MagicMock()
    
    # Create user not found error
    mock_error = create_auth_api_error("User not found", status=404)
    
    mock_supabase.auth = mock_auth
    mock_auth.resend.side_effect = mock_error
    mock_get_supabase.return_value = mock_supabase
    
    # Act
    result = await AuthService.resend_verification_email(email)
    
    # Assert - Should return generic message for security
    assert result["success"] is True
    assert "verification email has been sent" in result["message"]


@pytest.mark.asyncio
@patch('Backend.api.auth.service.upload_avatar_to_blob')
async def test_upload_user_avatar_success(mock_upload, mock_session, sample_user):
    """Test successful avatar upload."""
    # Arrange
    file = MagicMock(spec=UploadFile)
    file.filename = "avatar.jpg"
    new_avatar_url = "https://storage.blob.core.windows.net/avatars/123.jpg"
    mock_upload.return_value = new_avatar_url
    
    # Act
    result = await AuthService.upload_user_avatar(
        sample_user, file, mock_session
    )
    
    # Assert
    assert isinstance(result, AvatarUploadResponse)
    assert result.profile_image_url == new_avatar_url
    assert sample_user.profile_image_url == new_avatar_url
    mock_upload.assert_called_once_with(file, sample_user.id)
    mock_session.add.assert_called_once_with(sample_user)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('Backend.api.auth.service.upload_avatar_to_blob')
async def test_upload_user_avatar_failure(mock_upload, mock_session, sample_user):
    """Test avatar upload failure."""
    # Arrange
    file = MagicMock(spec=UploadFile)
    mock_upload.side_effect = Exception("Upload failed")
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await AuthService.upload_user_avatar(
            sample_user, file, mock_session
        )
    
    assert exc_info.value.status_code == 500
    assert "Failed to upload avatar" in exc_info.value.detail


@pytest.mark.asyncio
@patch('Backend.api.auth.service.AuthService.resend_verification_email')
async def test_request_email_verification_unverified_user(mock_resend, mock_session):
    """Test email verification request for unverified user."""
    # Arrange
    user_id = uuid4()
    user = MagicMock()
    user.email = "test@example.com"
    user.is_email_verified = False
    mock_session.get.return_value = user
    mock_resend.return_value = {"success": True, "message": "Email sent"}
    
    # Act
    result = await AuthService.request_email_verification(user_id, mock_session)
    
    # Assert
    assert result is True
    mock_resend.assert_called_once_with(user.email)


@pytest.mark.asyncio
async def test_request_email_verification_already_verified(mock_session):
    """Test email verification request for already verified user."""
    # Arrange
    user_id = uuid4()
    user = MagicMock()
    user.is_email_verified = True
    mock_session.get.return_value = user
    
    # Act
    result = await AuthService.request_email_verification(user_id, mock_session)
    
    # Assert
    assert result is True  # Returns True without sending email


@pytest.mark.asyncio
async def test_request_email_verification_user_not_found(mock_session):
    """Test email verification request for non-existent user."""
    # Arrange
    user_id = uuid4()
    mock_session.get.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await AuthService.request_email_verification(user_id, mock_session)
    
    assert exc_info.value.status_code == 404
    assert "User not found" in exc_info.value.detail


@pytest.mark.asyncio
@patch('Backend.api.auth.service.AuthService.create_user_from_supabase')
@patch('Backend.api.auth.service.extract_user_metadata_from_supabase')
async def test_webhook_user_sync_new_user(mock_extract, mock_create, mock_session):
    """Test webhook sync for new user creation."""
    # Arrange
    user_id = str(uuid4())
    payload = SupabaseWebhookPayload(
        type="INSERT",
        table="users",
        schema="auth",
        record={
            "id": user_id,
            "email": "new@example.com",
            "raw_user_meta_data": {
                "first_name": "New",
                "last_name": "User"
            }
        }
    )
    mock_session.get.return_value = None  # User doesn't exist
    mock_extract.return_value = {
        "first_name": "New",
        "last_name": "User"
    }
    mock_create.return_value = MagicMock()
    
    # Act
    result = await AuthService.handle_webhook_user_sync(payload, mock_session)
    
    # Assert
    assert result["message"] == "User created successfully"
    mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_user_sync_existing_user(mock_session):
    """Test webhook sync for existing user."""
    # Arrange
    user_id = str(uuid4())
    payload = SupabaseWebhookPayload(
        type="INSERT",
        table="users",
        schema="auth",
        record={
            "id": user_id,
            "email": "existing@example.com"
        }
    )
    mock_session.get.return_value = MagicMock()  # User exists
    
    # Act
    result = await AuthService.handle_webhook_user_sync(payload, mock_session)
    
    # Assert
    assert result["message"] == "User already exists"


@pytest.mark.asyncio
async def test_webhook_user_sync_wrong_event_type(mock_session):
    """Test webhook sync with non-INSERT event."""
    # Arrange
    payload = SupabaseWebhookPayload(
        type="UPDATE",
        table="users",
        schema="auth"
    )
    
    # Act
    result = await AuthService.handle_webhook_user_sync(payload, mock_session)
    
    # Assert
    assert result["message"] == "Event ignored"


@pytest.mark.asyncio
async def test_webhook_user_sync_missing_data(mock_session):
    """Test webhook sync with missing record data."""
    # Arrange
    payload = SupabaseWebhookPayload(
        type="INSERT",
        table="users",
        schema="auth",
        record=None
    )
    
    # Act
    result = await AuthService.handle_webhook_user_sync(payload, mock_session)
    
    # Assert
    assert result["message"] == "No record data"