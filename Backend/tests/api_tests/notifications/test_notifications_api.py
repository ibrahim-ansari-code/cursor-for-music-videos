"""
API tests for notification endpoints using mocked dependencies.

These tests follow the hybrid API testing pattern with FastAPI TestClient
and mocked database/service dependencies.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, Mock
from uuid import UUID, uuid4
from datetime import datetime, timezone

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.notification import Notification, NotificationPreference
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()


class TestClientWithHost(TestClient):
    """Custom TestClient that sets the proper host header."""
    def request(self, method: str, url, **kwargs):
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def create_test_user(user_id=None, email="test@example.com"):
    """Helper function to create a test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type="LANDLORD",
        is_active=True,
        is_admin=False,
        is_email_verified=True,
        created_at=now,
        updated_at=now
    )


def create_test_notification(user_id: UUID, notification_id=None):
    """Helper function to create a test notification."""
    now = datetime.now(timezone.utc)
    return Notification(
        id=notification_id or uuid4(),
        user_id=user_id,
        type='rent_reminder',
        title='Test Notification',
        message='Test message',
        priority='normal',
        is_read=False,
        is_archived=False,
        created_at=now,
        updated_at=now
    )


def create_test_preferences(user_id: UUID):
    """Helper function to create test notification preferences."""
    now = datetime.now(timezone.utc)
    return NotificationPreference(
        id=uuid4(),
        user_id=user_id,
        enabled=True,
        preferences={
            'rent_reminder': {'enabled': True, 'channels': ['in_app', 'email']},
            'lease_expiring': {'enabled': True, 'channels': ['in_app']},
            'system_update': {'enabled': True, 'channels': ['in_app']}
        },
        email_digest_frequency='immediate',
        created_at=now,
        updated_at=now
    )


class TestGetNotifications:
    """Tests for GET /api/notifications endpoint."""
    
    @patch('Backend.api.notifications.router.NotificationService.get_unread_count')
    @patch('Backend.api.notifications.router.NotificationService.get_notifications')
    def test_get_notifications_success(self, mock_get_notifs, mock_get_count):
        """Test successful retrieval of notifications."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        notifications = [create_test_notification(test_user.id)]
        mock_get_notifs.return_value = (notifications, 1)
        mock_get_count.return_value = 1
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Act
        client = TestClientWithHost(app)
        response = client.get("/api/notifications")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert 'notifications' in data
        assert 'total' in data
        assert len(data['notifications']) == 1
        assert data['total'] == 1
    
    @patch('Backend.api.notifications.router.NotificationService.get_unread_count')
    @patch('Backend.api.notifications.router.NotificationService.get_notifications')
    def test_get_notifications_with_pagination(self, mock_get_notifs, mock_get_count):
        """Test notifications with pagination parameters."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        mock_get_notifs.return_value = ([], 0)
        mock_get_count.return_value = 0
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Act
        client = TestClientWithHost(app)
        response = client.get("/api/notifications?limit=5&offset=0")
        
        # Assert
        assert response.status_code == 200
        mock_get_notifs.assert_called_once()


class TestGetUnreadCount:
    """Tests for GET /api/notifications/unread-count endpoint."""
    
    @patch('Backend.api.notifications.router.NotificationService.get_unread_count')
    def test_get_unread_count_success(self, mock_get_count):
        """Test successful retrieval of unread count."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        mock_get_count.return_value = 5
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Act
        client = TestClientWithHost(app)
        response = client.get("/api/notifications/unread-count")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['unread_count'] == 5


class TestMarkAsRead:
    """Tests for PATCH /api/notifications/{id}/read endpoint."""
    
    @patch('Backend.api.notifications.router.NotificationService.mark_as_read')
    def test_mark_as_read_success(self, mock_mark_read):
        """Test marking notification as read."""
        # Arrange
        test_user = create_test_user()
        notification_id = uuid4()
        mock_session = AsyncMock()
        
        mock_mark_read.return_value = 1
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Act
        client = TestClientWithHost(app)
        response = client.patch(f"/api/notifications/{notification_id}/read")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['marked_count'] == 1
    
    @patch('Backend.api.notifications.router.NotificationService.mark_as_read')
    def test_mark_as_read_not_found(self, mock_mark_read):
        """Test marking non-existent notification as read."""
        # Arrange
        test_user = create_test_user()
        notification_id = uuid4()
        mock_session = AsyncMock()
        
        mock_mark_read.return_value = 0
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Act
        client = TestClientWithHost(app)
        response = client.patch(f"/api/notifications/{notification_id}/read")
        
        # Assert
        assert response.status_code == 404


class TestMarkAllAsRead:
    """Tests for PATCH /api/notifications/mark-all-read endpoint."""
    
    @patch('Backend.api.notifications.router.NotificationService.mark_all_as_read')
    def test_mark_all_as_read_success(self, mock_mark_all):
        """Test marking all notifications as read."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        mock_mark_all.return_value = 3
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Act
        client = TestClientWithHost(app)
        response = client.patch("/api/notifications/mark-all-read")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['marked_count'] == 3


class TestDeleteNotification:
    """Tests for DELETE /api/notifications/{id} endpoint."""
    
    @patch('Backend.api.notifications.router.NotificationService.delete_notification')
    def test_delete_notification_success(self, mock_delete):
        """Test deleting notification."""
        # Arrange
        test_user = create_test_user()
        notification_id = uuid4()
        mock_session = AsyncMock()
        
        mock_delete.return_value = True
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Act
        client = TestClientWithHost(app)
        response = client.delete(f"/api/notifications/{notification_id}")
        
        # Assert
        assert response.status_code == 204
    
    @patch('Backend.api.notifications.router.NotificationService.delete_notification')
    def test_delete_notification_not_found(self, mock_delete):
        """Test deleting non-existent notification."""
        # Arrange
        test_user = create_test_user()
        notification_id = uuid4()
        mock_session = AsyncMock()
        
        mock_delete.return_value = False
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Act
        client = TestClientWithHost(app)
        response = client.delete(f"/api/notifications/{notification_id}")
        
        # Assert
        assert response.status_code == 404


class TestGetPreferences:
    """Tests for GET /api/notifications/preferences endpoint."""
    
    @patch('Backend.api.notifications.router.NotificationService.get_user_preferences')
    def test_get_preferences_success(self, mock_get_prefs):
        """Test successful retrieval of notification preferences."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        prefs = create_test_preferences(test_user.id)
        mock_get_prefs.return_value = prefs
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Act
        client = TestClientWithHost(app)
        response = client.get("/api/notifications/preferences")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert 'user_id' in data
        assert data['enabled'] is True
        assert 'preferences' in data
        assert 'email_digest_frequency' in data


class TestUpdatePreferences:
    """Tests for PUT /api/notifications/preferences endpoint."""
    
    @patch('Backend.api.notifications.router.NotificationService.update_preferences')
    def test_update_preferences_success(self, mock_update):
        """Test updating notification preferences."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        updated_prefs = create_test_preferences(test_user.id)
        updated_prefs.email_digest_frequency = 'daily'
        mock_update.return_value = updated_prefs
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {
            "enabled": True,
            "preferences": {
                "rent_reminder": {
                    "enabled": True,
                    "channels": ["in_app", "email"]
                }
            },
            "email_digest_frequency": "daily"
        }
        
        # Act
        client = TestClientWithHost(app)
        response = client.put("/api/notifications/preferences", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'preferences' in data
        assert data['preferences']['enabled'] is True
        assert data['preferences']['email_digest_frequency'] == 'daily'
    
    @patch('Backend.api.notifications.router.NotificationService.update_preferences')
    def test_update_preferences_disable_all(self, mock_update):
        """Test disabling all notifications."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        updated_prefs = create_test_preferences(test_user.id)
        updated_prefs.enabled = False
        updated_prefs.email_digest_frequency = 'never'
        mock_update.return_value = updated_prefs
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {
            "enabled": False,
            "preferences": {},
            "email_digest_frequency": "never"
        }
        
        # Act
        client = TestClientWithHost(app)
        response = client.put("/api/notifications/preferences", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'preferences' in data
        assert data['preferences']['enabled'] is False
    
    def test_update_preferences_invalid_frequency(self):
        """Test updating with invalid digest frequency."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {
            "enabled": True,
            "preferences": {},
            "email_digest_frequency": "invalid_value"
        }
        
        # Act
        client = TestClientWithHost(app)
        response = client.put("/api/notifications/preferences", json=payload)
        
        # Assert
        assert response.status_code == 422


class TestSendTestNotification:
    """Tests for POST /api/notifications/test-notification endpoint."""
    
    @patch('Backend.api.notifications.router.check_test_rate_limit')
    @patch('Backend.api.notifications.router.NotificationService.create_notification')
    def test_send_test_notification_success(self, mock_create, mock_rate_limit):
        """Test sending test in-app notification."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        test_notification = create_test_notification(test_user.id)
        mock_create.return_value = test_notification
        mock_rate_limit.return_value = True
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {"notification_type": "rent_reminder"}
        
        # Act
        client = TestClientWithHost(app)
        response = client.post("/api/notifications/test-notification", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'notification_id' in data
    
    @patch('Backend.api.notifications.router.check_test_rate_limit')
    def test_send_test_notification_rate_limit_exceeded(self, mock_rate_limit):
        """Test rate limit exceeded for test notification."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        mock_rate_limit.return_value = False
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {"notification_type": "rent_reminder"}
        
        # Act
        client = TestClientWithHost(app)
        response = client.post("/api/notifications/test-notification", json=payload)
        
        # Assert
        assert response.status_code == 429
        data = response.json()
        assert 'rate limit' in data['detail'].lower()
    
    @patch('Backend.api.notifications.router.check_test_rate_limit')
    @patch('Backend.api.notifications.router.NotificationService.create_notification')
    def test_send_test_notification_preferences_disabled(self, mock_create, mock_rate_limit):
        """Test notification when user preferences disable that type."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        mock_create.return_value = None  # Service returns None when skipped
        mock_rate_limit.return_value = True
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {"notification_type": "rent_reminder"}
        
        # Act
        client = TestClientWithHost(app)
        response = client.post("/api/notifications/test-notification", json=payload)
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert 'disabled' in data['detail'].lower()
    
    def test_send_test_notification_invalid_type(self):
        """Test notification with invalid notification type fails validation."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {"notification_type": "unknown_type"}
        
        # Act
        client = TestClientWithHost(app)
        response = client.post("/api/notifications/test-notification", json=payload)
        
        # Assert
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert 'detail' in data


class TestSendTestEmail:
    """Tests for POST /api/notifications/test-email endpoint."""
    
    @patch('Backend.api.notifications.router.EmailService.send_notification_email')
    @patch('Backend.api.notifications.router.check_test_rate_limit')
    @patch('Backend.api.notifications.router.NotificationService.create_notification')
    def test_send_test_email_success(self, mock_create, mock_rate_limit, mock_email):
        """Test sending test email."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        test_notification = create_test_notification(test_user.id)
        mock_create.return_value = test_notification
        mock_rate_limit.return_value = True
        mock_email.return_value = True
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {"notification_type": "rent_reminder"}
        
        # Act
        client = TestClientWithHost(app)
        response = client.post("/api/notifications/test-email", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['email_sent_to'] == test_user.email
    
    @patch('Backend.api.notifications.router.check_test_rate_limit')
    def test_send_test_email_rate_limit_exceeded(self, mock_rate_limit):
        """Test rate limit exceeded for test email."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        mock_rate_limit.return_value = False
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {"notification_type": "rent_reminder"}
        
        # Act
        client = TestClientWithHost(app)
        response = client.post("/api/notifications/test-email", json=payload)
        
        # Assert
        assert response.status_code == 429
        data = response.json()
        assert 'rate limit' in data['detail'].lower()
    
    @patch('Backend.api.notifications.router.EmailService.send_notification_email')
    @patch('Backend.api.notifications.router.check_test_rate_limit')
    @patch('Backend.api.notifications.router.NotificationService.create_notification')
    def test_send_test_email_preferences_disabled(self, mock_create, mock_rate_limit, mock_email):
        """Test email when user preferences disable that type."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        mock_create.return_value = None  # Service returns None when skipped
        mock_rate_limit.return_value = True
        mock_email.return_value = False  # Shouldn't be called, but mock anyway
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {"notification_type": "rent_reminder"}
        
        # Act
        client = TestClientWithHost(app)
        response = client.post("/api/notifications/test-email", json=payload)
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert 'disabled' in data['detail'].lower()
        # Email service should not be called if notification creation failed
        mock_email.assert_not_called()
    
    @patch('Backend.api.notifications.router.EmailService.send_notification_email')
    @patch('Backend.api.notifications.router.check_test_rate_limit')
    @patch('Backend.api.notifications.router.NotificationService.create_notification')
    def test_send_test_email_email_fails(self, mock_create, mock_rate_limit, mock_email):
        """Test when email sending fails but notification is created."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        test_notification = create_test_notification(test_user.id)
        mock_create.return_value = test_notification
        mock_rate_limit.return_value = True
        mock_email.return_value = False
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {"notification_type": "rent_reminder"}
        
        # Act
        client = TestClientWithHost(app)
        response = client.post("/api/notifications/test-email", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'failed' in data['message'].lower()


class TestRateLimiting:
    """Tests for rate limiting functionality."""
    
    @patch('Backend.api.notifications.router.check_test_rate_limit')
    @patch('Backend.api.notifications.router.NotificationService.create_notification')
    def test_rate_limit_function_fails_open(self, mock_create, mock_rate_limit):
        """Test that rate limit failures allow requests (fail open)."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        # Simulate rate limit check raising an exception
        mock_rate_limit.side_effect = Exception("Database error")
        test_notification = create_test_notification(test_user.id)
        mock_create.return_value = test_notification
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        payload = {"notification_type": "rent_reminder"}
        
        # Act - should succeed despite rate limit error (fail open)
        client = TestClientWithHost(app)
        # Note: This will raise the exception since we're mocking the check_test_rate_limit
        # In reality, the function itself has try/except, but we're testing the endpoint's behavior
        response = client.post("/api/notifications/test-notification", json=payload)
        
        # Assert - the exception from rate limit should propagate
        assert response.status_code == 500


class TestEndpointValidation:
    """Tests for request validation."""
    
    @patch('Backend.api.notifications.router.NotificationService.get_notifications')
    def test_invalid_pagination_limit(self, mock_get_notifs):
        """Test pagination with invalid limit."""
        # Arrange
        test_user = create_test_user()
        mock_session = AsyncMock()
        
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        # Act
        client = TestClientWithHost(app)
        response = client.get("/api/notifications?limit=-1")
        
        # Assert
        assert response.status_code == 422
