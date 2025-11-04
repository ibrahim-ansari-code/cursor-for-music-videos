"""
Unit tests for CalendarService.

Tests event fetching, filtering, and custom reminder management.
"""
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from Backend.api.calendar.service import CalendarService
from Backend.api.calendar.schemas import CalendarFilters
from Backend.models.calendar import CustomReminder, CalendarEvent, CalendarEventType
from Backend.models.property import Property
from Backend.models.accounting.invoice import Invoice
from Backend.models.accounting.common import PaymentStatus
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.maintenance import MaintenanceRequest, MaintenanceStatus

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def calendar_service(mock_session):
    """Create a CalendarService instance with mock session."""
    return CalendarService(mock_session)


@pytest.fixture
def test_user_id():
    """Generate a test user ID."""
    return uuid4()


@pytest.fixture
def test_filters():
    """Create test calendar filters."""
    now = datetime.now(timezone.utc)
    return CalendarFilters(
        from_date=now,
        to_date=now + timedelta(days=30),
        property_id=None,
        unit_id=None,
        tenant_id=None,
        event_type=None,
        status=None
    )


class TestGetUserPropertyIds:
    """Tests for _get_user_property_ids helper method."""
    
    @pytest.mark.asyncio
    async def test_get_user_properties(self, calendar_service, mock_session, test_user_id):
        """Test getting user's property IDs."""
        # Arrange
        mock_prop1 = Mock()
        mock_prop1.id = 1
        mock_prop2 = Mock()
        mock_prop2.id = 2
        mock_prop3 = Mock()
        mock_prop3.id = 3
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_prop1, mock_prop2, mock_prop3]
        mock_session.execute.return_value = mock_result
        
        # Act
        property_ids = await calendar_service._get_user_property_ids(test_user_id, None)
        
        # Assert
        assert property_ids == [1, 2, 3]
        assert mock_session.execute.called
    
    @pytest.mark.asyncio
    async def test_get_specific_property(self, calendar_service, mock_session, test_user_id):
        """Test getting specific property ID if provided."""
        # Arrange
        mock_prop = Mock()
        mock_prop.id = 1
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_prop]
        mock_session.execute.return_value = mock_result
        
        # Act
        property_ids = await calendar_service._get_user_property_ids(test_user_id, 1)
        
        # Assert
        assert property_ids == [1]
    
    @pytest.mark.asyncio
    async def test_property_not_found(self, calendar_service, mock_session, test_user_id):
        """Test empty list when specific property not found."""
        # Arrange
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        # Act
        property_ids = await calendar_service._get_user_property_ids(test_user_id, 999)
        
        # Assert
        assert property_ids == []


class TestGetEvents:
    """Tests for get_events method."""
    
    @pytest.mark.asyncio
    async def test_get_events_no_properties(self, calendar_service, test_user_id, test_filters):
        """Test getting events when user has no properties."""
        # Arrange
        with patch.object(calendar_service, '_get_user_property_ids', return_value=[]):
            # Act
            result = await calendar_service.get_events(test_user_id, test_filters)
            
            # Assert
            assert result.total == 0
            assert len(result.events) == 0
    
    @pytest.mark.asyncio
    async def test_get_events_with_properties(self, calendar_service, test_user_id, test_filters, mock_session):
        """Test getting events when user has properties."""
        # Arrange
        with patch.object(calendar_service, '_get_user_property_ids', return_value=[1, 2]):
            with patch('Backend.api.calendar.event_builders.build_invoice_events', return_value=[]):
                with patch('Backend.api.calendar.event_builders.build_lease_events', return_value=[]):
                    with patch('Backend.api.calendar.event_builders.build_maintenance_events', return_value=[]):
                        with patch('Backend.api.calendar.event_builders.build_property_expiry_events', return_value=[]):
                            with patch('Backend.api.calendar.event_builders.build_custom_reminder_events', return_value=[]):
                                # Act
                                result = await calendar_service.get_events(test_user_id, test_filters)
                                
                                # Assert
                                assert result.total == 0
                                assert len(result.events) == 0
    
    @pytest.mark.asyncio
    async def test_get_events_with_filter(self, calendar_service, test_user_id, mock_session):
        """Test getting events with event type filter."""
        # Arrange
        filters = CalendarFilters(
            from_date=datetime.now(timezone.utc),
            to_date=datetime.now(timezone.utc) + timedelta(days=30),
            property_id=None,
            unit_id=None,
            tenant_id=None,
            event_type=CalendarEventType.INVOICE_DUE,
            status=None
        )
        
        with patch.object(calendar_service, '_get_user_property_ids', return_value=[1]):
            with patch('Backend.api.calendar.service.build_invoice_events', return_value=[]):
                # Act
                result = await calendar_service.get_events(test_user_id, filters)
                
                # Assert
                assert result.total == 0


class TestCreateReminder:
    """Tests for create_reminder method."""
    
    @pytest.mark.asyncio
    async def test_create_reminder_success(self, calendar_service, mock_session, test_user_id):
        """Test successful reminder creation."""
        # Arrange
        now = datetime.now(timezone.utc)
        reminder_data = Mock(
            title="Test Reminder",
            description="Test description",
            reminder_date=now + timedelta(days=1),
            all_day=False,
            property_id=None,
            unit_id=None,
            tenant_id=None,
            notify_before_hours=24
        )
        
        created_reminder = CustomReminder(
            id=uuid4(),
            user_id=test_user_id,
            title="Test Reminder",
            description="Test description",
            reminder_date=now + timedelta(days=1),
            all_day=False,
            is_completed=False,
            notify_before_hours=24,
            created_at=now,
            updated_at=now
        )
        
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Act
        with patch('Backend.api.calendar.service.CustomReminder', return_value=created_reminder):
            result = await calendar_service.create_custom_reminder(test_user_id, reminder_data)
            
            # Assert
            assert mock_session.add.called
            assert mock_session.commit.called
            assert mock_session.refresh.called


class TestGetReminder:
    """Tests for get_reminder method."""
    
    @pytest.mark.asyncio
    async def test_get_reminder_found(self, calendar_service, mock_session, test_user_id):
        """Test getting an existing reminder."""
        # Arrange
        reminder_id = uuid4()
        reminder = CustomReminder(
            id=reminder_id,
            user_id=test_user_id,
            title="Test",
            reminder_date=datetime.now(timezone.utc),
            all_day=False,
            is_completed=False,
            notify_before_hours=24,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = reminder
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await calendar_service.get_custom_reminder(test_user_id, reminder_id)
        
        # Assert
        assert result is not None
        assert result.id == reminder_id
    
    @pytest.mark.asyncio
    async def test_get_reminder_not_found(self, calendar_service, mock_session, test_user_id):
        """Test getting non-existent reminder."""
        # Arrange
        reminder_id = uuid4()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await calendar_service.get_custom_reminder(test_user_id, reminder_id)
        
        # Assert
        assert result is None


class TestUpdateReminder:
    """Tests for update_reminder method."""
    
    @pytest.mark.asyncio
    async def test_update_reminder_success(self, calendar_service, mock_session, test_user_id):
        """Test successful reminder update."""
        # Arrange
        reminder_id = uuid4()
        now = datetime.now(timezone.utc)
        existing_reminder = CustomReminder(
            id=reminder_id,
            user_id=test_user_id,
            title="Old Title",
            reminder_date=now,
            all_day=False,
            is_completed=False,
            notify_before_hours=24,
            created_at=now,
            updated_at=now
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_reminder
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        update_data = Mock()
        update_data.dict.return_value = {"title": "New Title"}
        update_data.is_completed = None
        
        # Act
        result = await calendar_service.update_custom_reminder(test_user_id, reminder_id, update_data)
        
        # Assert
        assert result is not None
        assert mock_session.commit.called
    
    @pytest.mark.asyncio
    async def test_update_reminder_mark_completed(self, calendar_service, mock_session, test_user_id):
        """Test marking reminder as completed."""
        # Arrange
        reminder_id = uuid4()
        now = datetime.now(timezone.utc)
        existing_reminder = CustomReminder(
            id=reminder_id,
            user_id=test_user_id,
            title="Test",
            reminder_date=now,
            all_day=False,
            is_completed=False,
            completed_at=None,
            notify_before_hours=24,
            created_at=now,
            updated_at=now
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_reminder
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        update_data = Mock()
        update_data.dict.return_value = {}
        update_data.is_completed = True
        
        # Act
        result = await calendar_service.update_custom_reminder(test_user_id, reminder_id, update_data)
        
        # Assert
        assert existing_reminder.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_update_reminder_mark_uncompleted(self, calendar_service, mock_session, test_user_id):
        """Test marking reminder as uncompleted."""
        # Arrange
        reminder_id = uuid4()
        now = datetime.now(timezone.utc)
        existing_reminder = CustomReminder(
            id=reminder_id,
            user_id=test_user_id,
            title="Test",
            reminder_date=now,
            all_day=False,
            is_completed=True,
            completed_at=now,
            notify_before_hours=24,
            created_at=now,
            updated_at=now
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_reminder
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        update_data = Mock()
        update_data.dict.return_value = {}
        update_data.is_completed = False
        
        # Act
        result = await calendar_service.update_custom_reminder(test_user_id, reminder_id, update_data)
        
        # Assert
        assert existing_reminder.completed_at is None


class TestDeleteReminder:
    """Tests for delete_reminder method."""
    
    @pytest.mark.asyncio
    async def test_delete_reminder_success(self, calendar_service, mock_session, test_user_id):
        """Test successful reminder deletion."""
        # Arrange
        reminder_id = uuid4()
        reminder = CustomReminder(
            id=reminder_id,
            user_id=test_user_id,
            title="Test",
            reminder_date=datetime.now(timezone.utc),
            all_day=False,
            is_completed=False,
            notify_before_hours=24,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = reminder
        mock_session.execute.return_value = mock_result
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # Act
        result = await calendar_service.delete_custom_reminder(test_user_id, reminder_id)
        
        # Assert
        assert result is True
        assert mock_session.delete.called
        assert mock_session.commit.called
    
    @pytest.mark.asyncio
    async def test_delete_reminder_not_found(self, calendar_service, mock_session, test_user_id):
        """Test deleting non-existent reminder."""
        # Arrange
        reminder_id = uuid4()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await calendar_service.delete_custom_reminder(test_user_id, reminder_id)
        
        # Assert
        assert result is False

