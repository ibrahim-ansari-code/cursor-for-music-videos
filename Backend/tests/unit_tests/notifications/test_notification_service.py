"""
Unit tests for NotificationService.

Tests the core business logic for notification creation, retrieval, and management.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from Backend.api.notifications.service import NotificationService
from Backend.models.notification import Notification, NotificationPreference
from Backend.models.user import User

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_notification():
    """Create a mock notification."""
    user_id = uuid4()
    return Notification(
        id=uuid4(),
        user_id=user_id,
        type='rent_reminder',
        title='Rent Due Soon',
        message='Your rent is due in 3 days',
        link='/properties/123',
        is_read=False,
        is_archived=False,
        priority='high',
        delivery_channels=['in_app', 'email'],
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_preferences():
    """Create mock notification preferences."""
    return NotificationPreference(
        id=uuid4(),
        user_id=uuid4(),
        enabled=True,
        preferences={
            'rent_reminder': {'enabled': True, 'channels': ['in_app', 'email']},
            'lease_expiring': {'enabled': True, 'channels': ['in_app', 'email']},
            'system_update': {'enabled': False, 'channels': []}
        },
        email_digest_frequency='immediate',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


class TestCreateNotification:
    """Tests for create_notification function."""
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.service.NotificationService.get_user_preferences')
    async def test_create_notification_success(self, mock_get_prefs, mock_db_session, mock_preferences):
        """Test successful notification creation."""
        user_id = uuid4()
        
        # Mock get_user_preferences to return preferences
        mock_get_prefs.return_value = mock_preferences
        
        # Mock notification creation
        mock_db_session.add = Mock()
        mock_db_session.flush = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        result = await NotificationService.create_notification(
            user_id=user_id,
            type='rent_reminder',
            title='Test Notification',
            message='Test message',
            session=mock_db_session,
            link='/test',
            priority='high'
        )
        
        # Verify notification was added to session
        assert mock_db_session.add.called
        assert mock_db_session.flush.called
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.service.NotificationService.get_user_preferences')
    async def test_create_notification_disabled_category(self, mock_get_prefs, mock_db_session):
        """Test notification creation when category is disabled."""
        user_id = uuid4()
        
        # Mock preferences with disabled category
        disabled_prefs = NotificationPreference(
            id=uuid4(),
            user_id=user_id,
            enabled=True,
            preferences={
                'rent_reminder': {'enabled': False, 'channels': []},
            },
            email_digest_frequency='immediate',
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        mock_get_prefs.return_value = disabled_prefs
        
        result = await NotificationService.create_notification(
            user_id=user_id,
            type='rent_reminder',
            title='Test',
            message='Test',
            session=mock_db_session
        )
        
        # Should return None when notification is skipped
        assert result is None


class TestGetNotifications:
    """Tests for get_notifications function."""
    
    @pytest.mark.asyncio
    async def test_get_notifications_success(self, mock_db_session, mock_notification):
        """Test successful retrieval of notifications."""
        user_id = uuid4()
        
        # Mock count query (first)
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 1
        
        # Mock notifications query (second)
        mock_notifs_result = Mock()
        mock_notifs_result.scalars.return_value.all.return_value = [mock_notification]
        
        # Set up execute to return different results based on call order
        # First call: count query, Second call: notifications query
        mock_db_session.execute.side_effect = [mock_count_result, mock_notifs_result]
        
        notifications, count = await NotificationService.get_notifications(
            user_id=user_id,
            session=mock_db_session,
            limit=10,
            offset=0
        )
        
        assert len(notifications) == 1
        assert count == 1
        assert mock_db_session.execute.called
    
    @pytest.mark.asyncio
    async def test_get_notifications_with_filters(self, mock_db_session):
        """Test notification retrieval with filters."""
        user_id = uuid4()
        
        # Mock empty results
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 0
        
        mock_notifs_result = Mock()
        mock_notifs_result.scalars.return_value.all.return_value = []
        
        mock_db_session.execute.side_effect = [mock_count_result, mock_notifs_result]
        
        notifications, count = await NotificationService.get_notifications(
            user_id=user_id,
            session=mock_db_session,
            is_read=False,
            type='rent_reminder',
            limit=10,
            offset=0
        )
        
        assert len(notifications) == 0
        assert count == 0
        assert mock_db_session.execute.called


class TestMarkAsRead:
    """Tests for mark_as_read function."""
    
    @pytest.mark.asyncio
    async def test_mark_as_read_success(self, mock_db_session):
        """Test marking notifications as read."""
        user_id = uuid4()
        notification_ids = [uuid4(), uuid4()]
        
        # Mock update result
        mock_result = Mock()
        mock_result.rowcount = 2
        mock_db_session.execute.return_value = mock_result
        
        count = await NotificationService.mark_as_read(
            notification_ids=notification_ids,
            user_id=user_id,
            session=mock_db_session
        )
        
        assert count == 2
        assert mock_db_session.execute.called
        assert mock_db_session.commit.called


class TestGetUnreadCount:
    """Tests for get_unread_count function."""
    
    @pytest.mark.asyncio
    async def test_get_unread_count_success(self, mock_db_session):
        """Test getting unread notification count."""
        user_id = uuid4()
        
        # Mock count result
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_db_session.execute.return_value = mock_result
        
        count = await NotificationService.get_unread_count(
            user_id=user_id,
            session=mock_db_session
        )
        
        assert count == 5
        assert mock_db_session.execute.called


class TestMarkAllAsRead:
    """Tests for mark_all_as_read function."""
    
    @pytest.mark.asyncio
    async def test_mark_all_as_read_success(self, mock_db_session):
        """Test marking all notifications as read."""
        user_id = uuid4()
        
        # Mock update result
        mock_result = Mock()
        mock_result.rowcount = 10
        mock_db_session.execute.return_value = mock_result
        
        count = await NotificationService.mark_all_as_read(
            user_id=user_id,
            session=mock_db_session
        )
        
        assert count == 10
        assert mock_db_session.execute.called
        assert mock_db_session.commit.called


class TestDeleteNotification:
    """Tests for delete_notification function."""
    
    @pytest.mark.asyncio
    async def test_delete_notification_success(self, mock_db_session):
        """Test deleting a notification."""
        user_id = uuid4()
        notification_id = uuid4()
        
        # Mock UPDATE result with rowcount
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()
        
        success = await NotificationService.delete_notification(
            notification_id=notification_id,
            user_id=user_id,
            session=mock_db_session
        )
        
        assert success is True
        assert mock_db_session.execute.called
        assert mock_db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_delete_notification_not_found(self, mock_db_session):
        """Test deleting non-existent notification."""
        user_id = uuid4()
        notification_id = uuid4()
        
        # Mock UPDATE result with no rows affected
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()
        
        success = await NotificationService.delete_notification(
            notification_id=notification_id,
            user_id=user_id,
            session=mock_db_session
        )
        
        assert success is False


class TestUserPreferences:
    """Tests for user preference management."""
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_exists(self, mock_db_session, mock_preferences):
        """Test getting existing user preferences."""
        user_id = uuid4()
        
        # Mock preferences retrieval
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_preferences
        mock_db_session.execute.return_value = mock_result
        
        prefs = await NotificationService.get_user_preferences(
            user_id=user_id,
            session=mock_db_session
        )
        
        assert prefs is not None
        assert prefs.enabled is True
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.service.NotificationService.create_default_preferences')
    async def test_get_user_preferences_not_exists(self, mock_create_default, mock_db_session):
        """Test getting preferences when none exist - creates defaults."""
        user_id = uuid4()
        
        # Mock no preferences initially
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Mock default preferences creation
        default_prefs = NotificationPreference(
            id=uuid4(),
            user_id=user_id,
            enabled=True,
            preferences={},
            email_digest_frequency='immediate',
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_create_default.return_value = default_prefs
        
        prefs = await NotificationService.get_user_preferences(
            user_id=user_id,
            session=mock_db_session
        )
        
        # Should create default preferences when none exist
        assert mock_create_default.called
    
    @pytest.mark.asyncio
    async def test_create_default_preferences(self, mock_db_session):
        """Test creating default preferences."""
        user_id = uuid4()
        
        # Mock session operations
        mock_db_session.add = Mock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        prefs = await NotificationService.create_default_preferences(
            user_id=user_id,
            session=mock_db_session
        )
        
        assert prefs is not None
        assert prefs.user_id == user_id
        assert prefs.enabled is True
        assert mock_db_session.add.called
        assert mock_db_session.commit.await_count > 0
        assert mock_db_session.refresh.await_count > 0
    
    @pytest.mark.asyncio
    async def test_update_preferences(self, mock_db_session, mock_preferences):
        """Test updating user preferences."""
        user_id = uuid4()
        
        # Mock preferences retrieval
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_preferences
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        updated_prefs = await NotificationService.update_preferences(
            user_id=user_id,
            enabled=False,
            preferences={'rent_reminder': {'enabled': False, 'channels': []}},
            email_digest_frequency='daily',
            session=mock_db_session
        )
        
        assert updated_prefs.enabled is False
        assert updated_prefs.email_digest_frequency == 'daily'
        assert mock_db_session.commit.called


class TestCleanupOperations:
    """Tests for cleanup operations."""
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_notifications(self, mock_db_session):
        """Test cleaning up expired notifications."""
        # Mock delete result
        mock_result = Mock()
        mock_result.rowcount = 5
        mock_db_session.execute.return_value = mock_result
        
        count = await NotificationService.cleanup_expired_notifications(
            session=mock_db_session
        )
        
        assert count == 5
        assert mock_db_session.execute.called
        assert mock_db_session.commit.called
    


class TestGetDeliveryChannels:
    """Tests for _get_delivery_channels helper."""
    
    @pytest.mark.asyncio
    async def test_get_delivery_channels_enabled(self, mock_db_session, mock_preferences):
        """Test getting delivery channels when enabled."""
        user_id = uuid4()
        
        channels = await NotificationService._get_delivery_channels(
            user_id=user_id,
            notification_type='rent_reminder',
            preferences=mock_preferences,
            session=mock_db_session
        )
        
        assert 'in_app' in channels
        assert 'email' in channels
    
    @pytest.mark.asyncio
    async def test_get_delivery_channels_disabled(self, mock_db_session):
        """Test getting delivery channels when disabled."""
        user_id = uuid4()
        
        disabled_prefs = NotificationPreference(
            id=uuid4(),
            user_id=user_id,
            enabled=False,
            preferences={},
            email_digest_frequency='never',
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        channels = await NotificationService._get_delivery_channels(
            user_id=user_id,
            notification_type='rent_reminder',
            preferences=disabled_prefs,
            session=mock_db_session
        )
        
        assert len(channels) == 0

