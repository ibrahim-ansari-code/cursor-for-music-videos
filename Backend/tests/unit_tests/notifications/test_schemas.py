"""
Unit tests for notification schemas.

Tests Pydantic schema validation and serialization.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from pydantic import ValidationError

from Backend.api.notifications.schemas import (
    NotificationCreateRequest,
    NotificationResponse,
    NotificationListResponse,
    NotificationPreferenceUpdateRequest,
    NotificationPreferenceResponse,
    MarkAsReadRequest,
    MarkAsReadResponse,
    UnreadCountResponse,
)

pytestmark = pytest.mark.unit


class TestNotificationCreateRequest:
    """Tests for NotificationCreateRequest schema."""
    
    def test_notification_create_valid(self):
        """Test valid notification creation schema."""
        data = {
            'user_id': str(uuid4()),
            'type': 'rent_reminder',
            'title': 'Test Notification',
            'message': 'Test message',
            'priority': 'high'
        }
        
        schema = NotificationCreateRequest(**data)
        assert schema.type == 'rent_reminder'
        assert schema.title == 'Test Notification'
        assert schema.priority == 'high'
    
    def test_notification_create_with_optional_fields(self):
        """Test notification with optional fields."""
        data = {
            'user_id': str(uuid4()),
            'type': 'lease_expiring',
            'title': 'Lease Expiring',
            'message': 'Your lease expires in 30 days',
            'link': '/leases/123',
            'priority': 'normal',
            'metadata': {'lease_id': '123', 'days': '30'}
        }
        
        schema = NotificationCreateRequest(**data)
        assert schema.link == '/leases/123'
        assert schema.metadata is not None
    
    def test_notification_create_defaults(self):
        """Test default values."""
        data = {
            'user_id': str(uuid4()),
            'type': 'system_update',
            'title': 'Test',
            'message': 'Test'
        }
        
        schema = NotificationCreateRequest(**data)
        assert schema.priority == 'normal'  # Default


class TestNotificationResponse:
    """Tests for NotificationResponse schema."""
    
    def test_notification_response_valid(self):
        """Test valid notification response."""
        data = {
            'id': str(uuid4()),
            'user_id': str(uuid4()),
            'type': 'rent_reminder',
            'title': 'Test',
            'message': 'Test message',
            'is_read': False,
            'is_archived': False,
            'priority': 'high',
            'delivery_channels': ['in_app', 'email'],
            'metadata_': {},
            'created_at': datetime.now(timezone.utc)
        }
        
        schema = NotificationResponse(**data)
        assert schema.is_read is False
        assert schema.priority == 'high'


class TestNotificationListResponse:
    """Tests for NotificationListResponse schema."""
    
    def test_notification_list_response(self):
        """Test notification list response."""
        notifications = [
            NotificationResponse(
                id=str(uuid4()),
                user_id=str(uuid4()),
                type='rent_reminder',
                title='Test 1',
                message='Message 1',
                is_read=False,
                is_archived=False,
                priority='high',
                delivery_channels=['in_app'],
                metadata_={},
                created_at=datetime.now(timezone.utc)
            ),
            NotificationResponse(
                id=str(uuid4()),
                user_id=str(uuid4()),
                type='lease_expiring',
                title='Test 2',
                message='Message 2',
                is_read=True,
                is_archived=False,
                priority='normal',
                delivery_channels=['in_app', 'email'],
                metadata_={},
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        data = {
            'notifications': notifications,
            'total': 2,
            'unread_count': 1,
            'limit': 10,
            'offset': 0
        }
        
        schema = NotificationListResponse(**data)
        assert len(schema.notifications) == 2
        assert schema.total == 2


class TestNotificationPreferenceUpdateRequest:
    """Tests for NotificationPreferenceUpdateRequest schema."""
    
    def test_preference_update_valid(self):
        """Test valid preference update."""
        data = {
            'enabled': True,
            'preferences': {
                'rent_reminder': {
                    'enabled': True,
                    'channels': ['in_app', 'email']
                }
            },
            'email_digest_frequency': 'daily'
        }
        
        schema = NotificationPreferenceUpdateRequest(**data)
        assert schema.enabled is True
        assert schema.email_digest_frequency == 'daily'
    
    def test_preference_update_disable_all(self):
        """Test disabling all notifications."""
        data = {
            'enabled': False,
            'preferences': {},
            'email_digest_frequency': 'never'
        }
        
        schema = NotificationPreferenceUpdateRequest(**data)
        assert schema.enabled is False
        assert schema.email_digest_frequency == 'never'


class TestNotificationPreferenceResponse:
    """Tests for NotificationPreferenceResponse schema."""
    
    def test_preference_response_valid(self):
        """Test valid preference response."""
        data = {
            'id': str(uuid4()),
            'user_id': str(uuid4()),
            'enabled': True,
            'preferences': {
                'rent_reminder': {
                    'enabled': True,
                    'channels': ['in_app', 'email'],
                    'frequency': 'immediate'
                }
            },
            'email_digest_frequency': 'immediate',
            'email_digest_time': '09:00',
            'timezone': 'America/New_York',
            'quiet_hours_enabled': False,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        schema = NotificationPreferenceResponse(**data)
        assert schema.enabled is True
        assert 'rent_reminder' in schema.preferences


class TestMarkAsReadRequest:
    """Tests for MarkAsReadRequest schema."""
    
    def test_mark_as_read_request_valid(self):
        """Test valid mark as read request."""
        data = {
            'notification_ids': [str(uuid4()), str(uuid4())]
        }
        
        schema = MarkAsReadRequest(**data)
        assert len(schema.notification_ids) == 2
    
    def test_mark_as_read_request_single(self):
        """Test mark as read with single ID."""
        data = {
            'notification_ids': [str(uuid4())]
        }
        
        schema = MarkAsReadRequest(**data)
        assert len(schema.notification_ids) == 1


class TestMarkAsReadResponse:
    """Tests for MarkAsReadResponse schema."""
    
    def test_mark_as_read_response(self):
        """Test mark as read response."""
        data = {
            'success': True,
            'marked_count': 5,
            'message': '5 notifications marked as read'
        }
        
        schema = MarkAsReadResponse(**data)
        assert schema.success is True
        assert schema.marked_count == 5


class TestUnreadCountResponse:
    """Tests for UnreadCountResponse schema."""
    
    def test_unread_count_response(self):
        """Test unread count response."""
        data = {'unread_count': 10}
        
        schema = UnreadCountResponse(**data)
        assert schema.unread_count == 10
    
    def test_unread_count_response_zero(self):
        """Test unread count with zero."""
        data = {'unread_count': 0}
        
        schema = UnreadCountResponse(**data)
        assert schema.unread_count == 0



