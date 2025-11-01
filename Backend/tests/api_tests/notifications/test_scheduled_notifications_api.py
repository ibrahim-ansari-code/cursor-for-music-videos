"""
API tests for scheduled notification endpoints.

Tests the internal scheduled job endpoints called by pg_cron.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, Mock
from datetime import date, timedelta

from Backend.api.app import app
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


class TestScheduledRentReminders:
    """Tests for POST /api/notifications/scheduled/rent-reminders endpoint."""
    
    @patch('Backend.api.notifications.router.ScheduledNotificationService.send_rent_reminders')
    @patch('Backend.config.settings.INTERNAL_CRON_API_KEY', 'test-api-key')
    def test_rent_reminders_success(self, mock_send_reminders):
        """Test successful rent reminder trigger with valid API key."""
        # Arrange
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        mock_send_reminders.return_value = {
            'success': True,
            'notifications_created': 5,
            'leases_processed': 10,
            'leases_skipped_already_paid': 5,
            'target_date': (date.today() + timedelta(days=3)).isoformat()
        }
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.post(
            "/api/notifications/scheduled/rent-reminders",
            headers={"X-Internal-API-Key": "test-api-key"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['notifications_created'] == 5
        assert data['leases_processed'] == 10
        assert data['leases_skipped_already_paid'] == 5
        assert 'target_date' in data
        
        # Verify service was called
        mock_send_reminders.assert_called_once()
    
    @patch('Backend.config.settings.INTERNAL_CRON_API_KEY', 'test-api-key')
    def test_rent_reminders_unauthorized_no_key(self):
        """Test rent reminder trigger without API key."""
        # Arrange
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.post(
            "/api/notifications/scheduled/rent-reminders"
        )
        
        # Assert
        assert response.status_code == 401
    
    @patch('Backend.config.settings.INTERNAL_CRON_API_KEY', 'correct-key')
    def test_rent_reminders_unauthorized_wrong_key(self):
        """Test rent reminder trigger with wrong API key."""
        # Arrange
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.post(
            "/api/notifications/scheduled/rent-reminders",
            headers={"X-Internal-API-Key": "wrong-key"}
        )
        
        # Assert
        assert response.status_code == 401
    
    @patch('Backend.api.notifications.router.ScheduledNotificationService.send_rent_reminders')
    @patch('Backend.config.settings.INTERNAL_CRON_API_KEY', 'test-api-key')
    def test_rent_reminders_no_notifications_created(self, mock_send_reminders):
        """Test rent reminder trigger when no notifications need to be sent."""
        # Arrange
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        mock_send_reminders.return_value = {
            'success': True,
            'notifications_created': 0,
            'leases_processed': 3,
            'leases_skipped_already_paid': 3,
            'target_date': (date.today() + timedelta(days=3)).isoformat()
        }
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.post(
            "/api/notifications/scheduled/rent-reminders",
            headers={"X-Internal-API-Key": "test-api-key"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['notifications_created'] == 0
        assert data['leases_skipped_already_paid'] == 3
    
    @patch('Backend.api.notifications.router.ScheduledNotificationService.send_rent_reminders')
    @patch('Backend.config.settings.INTERNAL_CRON_API_KEY', 'test-api-key')
    def test_rent_reminders_service_error(self, mock_send_reminders):
        """Test rent reminder trigger when service raises exception."""
        # Arrange
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        mock_send_reminders.side_effect = Exception("Database connection failed")
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.post(
            "/api/notifications/scheduled/rent-reminders",
            headers={"X-Internal-API-Key": "test-api-key"}
        )
        
        # Assert
        assert response.status_code == 500


class TestScheduledLeaseExpiring:
    """Tests for POST /api/notifications/scheduled/lease-expiring endpoint."""
    
    @patch('Backend.api.notifications.router.ScheduledNotificationService.send_lease_expiring_notifications')
    @patch('Backend.config.settings.INTERNAL_CRON_API_KEY', 'test-api-key')
    def test_lease_expiring_success(self, mock_send_expiring):
        """Test successful lease expiring trigger with valid API key."""
        # Arrange
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        today = date.today()
        mock_send_expiring.return_value = {
            'success': True,
            'notifications_created': 3,
            'leases_processed': 3,
            'check_dates': [
                (today + timedelta(days=30)).isoformat(),
                (today + timedelta(days=60)).isoformat()
            ]
        }
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.post(
            "/api/notifications/scheduled/lease-expiring",
            headers={"X-Internal-API-Key": "test-api-key"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['notifications_created'] == 3
        assert data['leases_processed'] == 3
        assert 'check_dates' in data
        assert len(data['check_dates']) == 2
        
        # Verify service was called
        mock_send_expiring.assert_called_once()
    
    @patch('Backend.config.settings.INTERNAL_CRON_API_KEY', 'test-api-key')
    def test_lease_expiring_unauthorized_no_key(self):
        """Test lease expiring trigger without API key."""
        # Arrange
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.post(
            "/api/notifications/scheduled/lease-expiring"
        )
        
        # Assert
        assert response.status_code == 401
    
    @patch('Backend.api.notifications.router.ScheduledNotificationService.send_lease_expiring_notifications')
    @patch('Backend.config.settings.INTERNAL_CRON_API_KEY', 'test-api-key')
    def test_lease_expiring_no_leases_found(self, mock_send_expiring):
        """Test lease expiring trigger when no leases are expiring."""
        # Arrange
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        mock_send_expiring.return_value = {
            'success': True,
            'notifications_created': 0,
            'leases_processed': 0,
            'check_dates': []
        }
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.post(
            "/api/notifications/scheduled/lease-expiring",
            headers={"X-Internal-API-Key": "test-api-key"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['notifications_created'] == 0
        assert data['leases_processed'] == 0
    
    @patch('Backend.api.notifications.router.ScheduledNotificationService.send_lease_expiring_notifications')
    @patch('Backend.config.settings.INTERNAL_CRON_API_KEY', 'test-api-key')
    def test_lease_expiring_service_error(self, mock_send_expiring):
        """Test lease expiring trigger when service raises exception."""
        # Arrange
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        
        mock_send_expiring.side_effect = Exception("Query timeout")
        
        client = TestClientWithHost(app)
        
        # Act
        response = client.post(
            "/api/notifications/scheduled/lease-expiring",
            headers={"X-Internal-API-Key": "test-api-key"}
        )
        
        # Assert
        assert response.status_code == 500


class TestEndpointNotInSchema:
    """Test that scheduled endpoints are not exposed in OpenAPI schema."""
    
    def test_scheduled_endpoints_not_in_openapi(self):
        """Verify scheduled endpoints are excluded from OpenAPI schema."""
        client = TestClientWithHost(app)
        
        # Act
        response = client.get("/openapi.json")
        
        # Assert
        assert response.status_code == 200
        openapi_spec = response.json()
        
        # Verify scheduled endpoints are not documented
        paths = openapi_spec.get('paths', {})
        assert '/api/notifications/scheduled/rent-reminders' not in paths
        assert '/api/notifications/scheduled/lease-expiring' not in paths

