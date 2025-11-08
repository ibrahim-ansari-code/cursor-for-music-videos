"""
Unit tests for Supabase webhook user synchronization.

Tests the handle_webhook_user_sync service method that processes
INSERT and UPDATE events from Supabase auth.users table.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from Backend.api.auth.service import AuthService
from Backend.api.auth.schemas import SupabaseWebhookPayload
from Backend.models.user import User


pytestmark = pytest.mark.asyncio


async def test_webhook_ignores_non_auth_tables(mock_db_session):
    """Test that webhook ignores events for tables other than auth.users."""
    payload = SupabaseWebhookPayload(
        type="INSERT",
        table="posts",
        schema="public",
        record={"id": str(uuid4()), "title": "Test Post"}
    )
    
    result = await AuthService.handle_webhook_user_sync(payload, mock_db_session)
    
    assert result["message"] == "Event ignored - not auth.users table"


async def test_webhook_ignores_delete_events(mock_db_session):
    """Test that webhook ignores DELETE events."""
    payload = SupabaseWebhookPayload(
        type="DELETE",
        table="users",
        schema="auth",
        record=None,
        old_record={"id": str(uuid4()), "email": "deleted@example.com"}
    )
    
    result = await AuthService.handle_webhook_user_sync(payload, mock_db_session)
    
    assert "not supported" in result["message"]


async def test_webhook_validates_required_fields(mock_db_session):
    """Test that webhook validates presence of id and email."""
    # Missing email
    payload = SupabaseWebhookPayload(
        type="INSERT",
        table="users",
        schema="auth",
        record={"id": str(uuid4())}
    )
    
    result = await AuthService.handle_webhook_user_sync(payload, mock_db_session)
    
    assert "Invalid user data" in result["message"]


@patch('Backend.api.auth.service.AuthService.create_user_from_supabase', new_callable=AsyncMock)
async def test_webhook_creates_new_user_on_insert(mock_create_user, mock_db_session):
    """Test that webhook creates a new user on INSERT event."""
    from unittest.mock import Mock
    
    user_id = uuid4()
    email = f"newuser-{user_id}@example.com"
    
    # Mock: User doesn't exist
    mock_db_session.get.return_value = None
    mock_result = Mock()  # Use Mock, not AsyncMock
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    payload = SupabaseWebhookPayload(
        type="INSERT",
        table="users",
        schema="auth",
        record={
            "id": str(user_id),
            "email": email,
            "raw_user_meta_data": {
                "first_name": "John",
                "last_name": "Doe",
                "email_verified": True
            }
        }
    )
    
    result = await AuthService.handle_webhook_user_sync(payload, mock_db_session)
    
    assert result["message"] == "User created successfully"
    
    # Verify create_user_from_supabase was called
    mock_create_user.assert_called_once()


async def test_webhook_is_idempotent_for_insert(mock_db_session):
    """Test that webhook handles duplicate INSERT events gracefully."""
    user_id = uuid4()
    email = f"idempotent-{user_id}@example.com"
    
    # Create user manually
    user = User(
        id=user_id,
        email=email,
        first_name="Jane",
        last_name="Smith",
        user_type="LANDLORD",
        is_active=True,
        is_admin=False,
        is_email_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    mock_db_session.add(user)
    await mock_db_session.commit()
    
    # Send INSERT webhook for existing user
    payload = SupabaseWebhookPayload(
        type="INSERT",
        table="users",
        schema="auth",
        record={
            "id": str(user_id),
            "email": email,
            "raw_user_meta_data": {}
        }
    )
    
    result = await AuthService.handle_webhook_user_sync(payload, mock_db_session)
    
    assert "already exists" in result["message"]
    assert "idempotent" in result["message"]


async def test_webhook_updates_user_metadata(mock_db_session):
    """Test that webhook updates user metadata on UPDATE event."""
    user_id = uuid4()
    email = f"update-{user_id}@example.com"
    
    # Create user mock
    user = User(
        id=user_id,
        email=email,
        first_name="Old",
        last_name="Name",
        user_type="LANDLORD",
        is_active=True,
        is_admin=False,
        is_email_verified=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Mock: User exists
    mock_db_session.get.return_value = user
    
    # Send UPDATE webhook
    payload = SupabaseWebhookPayload(
        type="UPDATE",
        table="users",
        schema="auth",
        record={
            "id": str(user_id),
            "email": email,
            "raw_user_meta_data": {
                "first_name": "New",
                "last_name": "Name",
                "phone": "+1234567890",
                "email_verified": True
            }
        }
    )
    
    result = await AuthService.handle_webhook_user_sync(payload, mock_db_session)
    
    assert "metadata updated" in result["message"]
    
    # Verify updates (user object should be modified in place)
    assert user.first_name == "New"
    assert user.phone == "+1234567890"
    assert user.is_email_verified is True


async def test_webhook_rejects_email_conflicts(mock_db_session):
    """Test that webhook rejects email conflicts (Supabase should handle linking natively)."""
    from unittest.mock import Mock
    from fastapi import HTTPException
    
    old_supabase_id = uuid4()
    new_supabase_id = uuid4()
    email = f"conflict-{uuid4()}@example.com"
    
    # Create existing user
    user = User(
        id=old_supabase_id,
        email=email,
        first_name="John",
        last_name="Doe",
        user_type="LANDLORD",
        is_active=True,
        is_admin=False,
        is_email_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Mock: User doesn't exist by new ID, but exists by email (conflict!)
    mock_db_session.get.return_value = None
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db_session.execute.return_value = mock_result
    
    # Webhook receives INSERT with different Supabase ID but same email
    payload = SupabaseWebhookPayload(
        type="INSERT",
        table="users",
        schema="auth",
        record={
            "id": str(new_supabase_id),
            "email": email,
            "raw_user_meta_data": {
                "first_name": "John",
                "last_name": "Doe",
                "email_verified": True
            }
        }
    )
    
    # Should raise 409 Conflict
    with pytest.raises(HTTPException) as exc_info:
        await AuthService.handle_webhook_user_sync(payload, mock_db_session)
    
    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail


@patch('Backend.api.auth.service.AuthService.create_user_from_supabase', new_callable=AsyncMock)
async def test_webhook_handles_full_name_splitting(mock_create_user, mock_db_session):
    """Test that webhook correctly splits full_name into first_name and last_name."""
    from unittest.mock import Mock
    
    user_id = uuid4()
    email = f"fullname-{user_id}@example.com"
    
    # Mock: User doesn't exist
    mock_db_session.get.return_value = None
    mock_result = Mock()  # Use Mock, not AsyncMock
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    payload = SupabaseWebhookPayload(
        type="INSERT",
        table="users",
        schema="auth",
        record={
            "id": str(user_id),
            "email": email,
            "raw_user_meta_data": {
                "full_name": "Alice Wonderland",
                "email_verified": False
            }
        }
    )
    
    result = await AuthService.handle_webhook_user_sync(payload, mock_db_session)
    
    assert result["message"] == "User created successfully"
    mock_create_user.assert_called_once()


@patch('Backend.api.auth.service.AuthService.create_user_from_supabase', new_callable=AsyncMock)
async def test_webhook_handles_json_string_metadata(mock_create_user, mock_db_session):
    """Test that webhook handles raw_user_meta_data as JSON string."""
    import json
    from unittest.mock import Mock
    
    user_id = uuid4()
    email = f"jsonmeta-{user_id}@example.com"
    
    # Mock: User doesn't exist
    mock_db_session.get.return_value = None
    mock_result = Mock()  # Use Mock, not AsyncMock
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    payload = SupabaseWebhookPayload(
        type="INSERT",
        table="users",
        schema="auth",
        record={
            "id": str(user_id),
            "email": email,
            "raw_user_meta_data": json.dumps({
                "first_name": "Bob",
                "last_name": "Builder",
                "email_verified": True
            })
        }
    )
    
    result = await AuthService.handle_webhook_user_sync(payload, mock_db_session)
    
    assert result["message"] == "User created successfully"
    mock_create_user.assert_called_once()


@patch('Backend.api.auth.service.AuthService.create_user_from_supabase', new_callable=AsyncMock)
async def test_webhook_handles_empty_metadata(mock_create_user, mock_db_session):
    """Test that webhook handles empty or missing metadata gracefully."""
    from unittest.mock import Mock
    
    user_id = uuid4()
    email = f"nometa-{user_id}@example.com"
    
    # Mock: User doesn't exist
    mock_db_session.get.return_value = None
    mock_result = Mock()  # Use Mock, not AsyncMock
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    payload = SupabaseWebhookPayload(
        type="INSERT",
        table="users",
        schema="auth",
        record={
            "id": str(user_id),
            "email": email,
            "raw_user_meta_data": {}
        }
    )
    
    result = await AuthService.handle_webhook_user_sync(payload, mock_db_session)
    
    assert result["message"] == "User created successfully"
    mock_create_user.assert_called_once()


async def test_webhook_succeeds_with_supabase_native_linking(mock_db_session):
    """Test that webhook succeeds when Supabase handles account linking (same user_id)."""
    user_id = uuid4()
    email = f"linked-{uuid4()}@example.com"
    
    # User already exists with this Supabase ID (Supabase linked accounts natively)
    user = User(
        id=user_id,
        email=email,
        first_name="Existing",
        last_name="User",
        user_type="LANDLORD",
        phone="+9876543210",
        is_active=True,
        is_admin=False,
        is_email_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Mock: User exists with same ID (Supabase kept ID stable)
    mock_db_session.get.return_value = user
    
    # Webhook receives UPDATE after user linked Microsoft to existing Google account
    payload = SupabaseWebhookPayload(
        type="UPDATE",
        table="users",
        schema="auth",
        record={
            "id": str(user_id),  # Same ID! Supabase handled linking
            "email": email,
            "raw_user_meta_data": {
                "first_name": "Existing",
                "last_name": "User",
                "phone": "+9876543210"
            }
        }
    )
    
    result = await AuthService.handle_webhook_user_sync(payload, mock_db_session)
    
    # Should succeed with metadata update
    assert "metadata updated" in result["message"]
    assert user.phone == "+9876543210"

