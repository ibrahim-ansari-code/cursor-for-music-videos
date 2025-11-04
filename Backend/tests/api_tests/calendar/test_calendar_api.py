"""
API tests for calendar endpoints using mocked dependencies.

These tests follow the hybrid API testing pattern with FastAPI TestClient
and mocked database/service dependencies.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, Mock
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.calendar import CustomReminder, CalendarEvent, CalendarEventType, CalendarEventStatus, CalendarEventPriority
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


def create_test_reminder(user_id: UUID, reminder_id=None):
    """Helper function to create a test custom reminder."""
    now = datetime.now(timezone.utc)
    return CustomReminder(
        id=reminder_id or uuid4(),
        user_id=user_id,
        title='Test Reminder',
        description='Test description',
        reminder_date=now + timedelta(days=1),
        all_day=False,
        is_completed=False,
        notify_before_hours=24,
        created_at=now,
        updated_at=now
    )


def create_test_calendar_event():
    """Helper function to create a test calendar event."""
    now = datetime.now(timezone.utc)
    return CalendarEvent(
        id="test_1",
        type=CalendarEventType.RENT_DUE,
        title="Test Event",
        description="Test description",
        start_at=now + timedelta(days=1),
        end_at=None,
        all_day=False,
        status=CalendarEventStatus.UPCOMING,
        priority=CalendarEventPriority.MEDIUM,
        property_id=1,
        property_name="Test Property",
        unit_id=None,
        tenant_id=None,
        tenant_name=None,
        lease_id=None,
        source_type="invoice",
        source_id=1,
        color="green",
        quick_actions=[],
        metadata={}
    )


class TestGetCalendarEvents:
    """Tests for GET /api/calendar/events endpoint."""
    
    def test_get_events_success(self):
        """Test successful calendar events retrieval."""
        # Arrange
        test_user = create_test_user()
        test_event = create_test_calendar_event()
        
        mock_service = AsyncMock()
        mock_service.get_events.return_value = Mock(
            events=[test_event],
            total=1,
            from_date=datetime.now(timezone.utc),
            to_date=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        with patch('Backend.api.calendar.router.CalendarService', return_value=mock_service):
            client = TestClientWithHost(app)
            
            # Act
            response = client.get("/api/calendar/events")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data["events"]) == 1
            assert data["total"] == 1
            assert data["events"][0]["title"] == "Test Event"
    
    def test_get_events_with_filters(self):
        """Test getting events with query filters."""
        # Arrange
        test_user = create_test_user()
        test_event = create_test_calendar_event()
        
        mock_service = AsyncMock()
        mock_service.get_events.return_value = Mock(
            events=[test_event],
            total=1,
            from_date=datetime.now(timezone.utc),
            to_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        with patch('Backend.api.calendar.router.CalendarService', return_value=mock_service):
            client = TestClientWithHost(app)
            
            # Act
            now = datetime.now(timezone.utc)
            from_date = now.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
            to_date = (now + timedelta(days=7)).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
            response = client.get(
                f"/api/calendar/events?from_date={from_date}&to_date={to_date}&property_id=1"
            )
            
            # Assert
            assert response.status_code == 200
    
    def test_get_events_invalid_date_range(self):
        """Test error when to_date is before from_date."""
        # Arrange
        test_user = create_test_user()
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        client = TestClientWithHost(app)
        
        # Act
        now = datetime.now(timezone.utc)
        from_date = (now + timedelta(days=7)).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        to_date = now.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        response = client.get(
            f"/api/calendar/events?from_date={from_date}&to_date={to_date}"
        )
        
        # Assert
        assert response.status_code == 400
    
    def test_get_events_date_range_too_large(self):
        """Test error when date range exceeds maximum."""
        # Arrange
        test_user = create_test_user()
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        client = TestClientWithHost(app)
        
        # Act
        now = datetime.now(timezone.utc)
        from_date = now.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        to_date = (now + timedelta(days=366)).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        response = client.get(
            f"/api/calendar/events?from_date={from_date}&to_date={to_date}"
        )
        
        # Assert
        assert response.status_code == 400
        assert "Date range cannot exceed" in response.json()["detail"]
    
    def test_get_events_service_error(self):
        """Test handling of service errors."""
        # Arrange
        test_user = create_test_user()
        
        mock_service = AsyncMock()
        mock_service.get_events.side_effect = Exception("Database error")
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        with patch('Backend.api.calendar.router.CalendarService', return_value=mock_service):
            client = TestClientWithHost(app)
            
            # Act
            response = client.get("/api/calendar/events")
            
            # Assert
            assert response.status_code == 500
            assert "Failed to fetch calendar events" in response.json()["detail"]


class TestCreateCustomReminder:
    """Tests for POST /api/calendar/reminders endpoint."""
    
    def test_create_reminder_success(self):
        """Test successful reminder creation."""
        # Arrange
        test_user = create_test_user()
        test_reminder = create_test_reminder(test_user.id)
        
        mock_service = AsyncMock()
        mock_service.create_custom_reminder.return_value = test_reminder
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        with patch('Backend.api.calendar.router.CalendarService', return_value=mock_service):
            client = TestClientWithHost(app)
            
            # Act
            reminder_data = {
                "title": "Test Reminder",
                "description": "Test description",
                "reminder_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "all_day": False,
                "notify_before_hours": 24
            }
            response = client.post("/api/calendar/reminders", json=reminder_data)
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["title"] == "Test Reminder"
    
    def test_create_reminder_service_error(self):
        """Test handling of service errors during creation."""
        # Arrange
        test_user = create_test_user()
        
        mock_service = AsyncMock()
        mock_service.create_custom_reminder.side_effect = Exception("Database error")
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        with patch('Backend.api.calendar.router.CalendarService', return_value=mock_service):
            client = TestClientWithHost(app)
            
            # Act
            reminder_data = {
                "title": "Test Reminder",
                "reminder_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            }
            response = client.post("/api/calendar/reminders", json=reminder_data)
            
            # Assert
            assert response.status_code == 500


class TestGetCustomReminder:
    """Tests for GET /api/calendar/reminders/{reminder_id} endpoint."""
    
    def test_get_reminder_success(self):
        """Test successful reminder retrieval."""
        # Arrange
        test_user = create_test_user()
        reminder_id = uuid4()
        test_reminder = create_test_reminder(test_user.id, reminder_id)
        
        mock_service = AsyncMock()
        mock_service.get_custom_reminder.return_value = test_reminder
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        with patch('Backend.api.calendar.router.CalendarService', return_value=mock_service):
            client = TestClientWithHost(app)
            
            # Act
            response = client.get(f"/api/calendar/reminders/{reminder_id}")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Test Reminder"
    
    def test_get_reminder_not_found(self):
        """Test 404 error when reminder doesn't exist."""
        # Arrange
        test_user = create_test_user()
        reminder_id = uuid4()
        
        mock_service = AsyncMock()
        mock_service.get_custom_reminder.return_value = None
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        with patch('Backend.api.calendar.router.CalendarService', return_value=mock_service):
            client = TestClientWithHost(app)
            
            # Act
            response = client.get(f"/api/calendar/reminders/{reminder_id}")
            
            # Assert
            assert response.status_code == 404


class TestUpdateCustomReminder:
    """Tests for PATCH /api/calendar/reminders/{reminder_id} endpoint."""
    
    def test_update_reminder_success(self):
        """Test successful reminder update."""
        # Arrange
        test_user = create_test_user()
        reminder_id = uuid4()
        test_reminder = create_test_reminder(test_user.id, reminder_id)
        test_reminder.title = "Updated Title"
        
        mock_service = AsyncMock()
        mock_service.update_custom_reminder.return_value = test_reminder
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        with patch('Backend.api.calendar.router.CalendarService', return_value=mock_service):
            client = TestClientWithHost(app)
            
            # Act
            update_data = {"title": "Updated Title"}
            response = client.patch(f"/api/calendar/reminders/{reminder_id}", json=update_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Updated Title"
    
    def test_update_reminder_not_found(self):
        """Test 404 error when updating non-existent reminder."""
        # Arrange
        test_user = create_test_user()
        reminder_id = uuid4()
        
        mock_service = AsyncMock()
        mock_service.update_custom_reminder.return_value = None
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        with patch('Backend.api.calendar.router.CalendarService', return_value=mock_service):
            client = TestClientWithHost(app)
            
            # Act
            update_data = {"title": "Updated Title"}
            response = client.patch(f"/api/calendar/reminders/{reminder_id}", json=update_data)
            
            # Assert
            assert response.status_code == 404


class TestDeleteCustomReminder:
    """Tests for DELETE /api/calendar/reminders/{reminder_id} endpoint."""
    
    def test_delete_reminder_success(self):
        """Test successful reminder deletion."""
        # Arrange
        test_user = create_test_user()
        reminder_id = uuid4()
        
        mock_service = AsyncMock()
        mock_service.delete_custom_reminder.return_value = True
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        with patch('Backend.api.calendar.router.CalendarService', return_value=mock_service):
            client = TestClientWithHost(app)
            
            # Act
            response = client.delete(f"/api/calendar/reminders/{reminder_id}")
            
            # Assert
            assert response.status_code == 204
    
    def test_delete_reminder_not_found(self):
        """Test 404 error when deleting non-existent reminder."""
        # Arrange
        test_user = create_test_user()
        reminder_id = uuid4()
        
        mock_service = AsyncMock()
        mock_service.delete_custom_reminder.return_value = False
        
        def mock_get_user():
            return test_user
        
        async def mock_session():
            yield AsyncMock()
        
        app.dependency_overrides[get_current_user] = mock_get_user
        app.dependency_overrides[get_session] = mock_session
        
        with patch('Backend.api.calendar.router.CalendarService', return_value=mock_service):
            client = TestClientWithHost(app)
            
            # Act
            response = client.delete(f"/api/calendar/reminders/{reminder_id}")
            
            # Assert
            assert response.status_code == 404

