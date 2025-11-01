"""
Unit tests for ScheduledNotificationService.

Tests the business logic for scheduled notification jobs including
payment status checks and notification creation.
"""
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from Backend.api.notifications.scheduled_service import ScheduledNotificationService
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.user import User
from Backend.models.accounting.payment import Payment
from Backend.models.accounting.common import PaymentStatus
from Backend.api.accounting.rent_tracker.schemas import RentStatus

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_lease():
    """Create a mock lease."""
    return Lease(
        id=1,
        property_id=1,
        tenant_id=1,
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
        monthly_rent=Decimal("1500.00"),
        security_deposit=Decimal("1500.00"),
        rent_due_day=3,
        status=LeaseStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_property():
    """Create a mock property."""
    user_id = uuid4()
    return Property(
        id=1,
        name="Test Property",
        address="123 Test St",
        city="Test City",
        province="TC",
        postal_code="T1T1T1",
        property_type="Residential",
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_landlord():
    """Create a mock landlord user."""
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        email="landlord@example.com",
        first_name="Land",
        last_name="Lord",
        user_type="LANDLORD",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now
    )


class TestCalculateLeasePaymentsForMonth:
    """Tests for _calculate_lease_payments_for_month helper method."""
    
    @pytest.mark.asyncio
    async def test_calculate_payments_no_payments(self, mock_db_session):
        """Test calculating payments when no payments exist."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar.return_value = Decimal("0.00")
        mock_db_session.execute.return_value = mock_result
        
        # Act
        amount = await ScheduledNotificationService._calculate_lease_payments_for_month(
            session=mock_db_session,
            lease_id=1,
            target_month=11,
            target_year=2024
        )
        
        # Assert
        assert amount == Decimal("0.00")
        assert mock_db_session.execute.called
    
    @pytest.mark.asyncio
    async def test_calculate_payments_with_full_payment(self, mock_db_session):
        """Test calculating payments when rent is fully paid."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar.return_value = Decimal("1500.00")
        mock_db_session.execute.return_value = mock_result
        
        # Act
        amount = await ScheduledNotificationService._calculate_lease_payments_for_month(
            session=mock_db_session,
            lease_id=1,
            target_month=11,
            target_year=2024
        )
        
        # Assert
        assert amount == Decimal("1500.00")
    
    @pytest.mark.asyncio
    async def test_calculate_payments_with_partial_payment(self, mock_db_session):
        """Test calculating payments when rent is partially paid."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar.return_value = Decimal("500.00")
        mock_db_session.execute.return_value = mock_result
        
        # Act
        amount = await ScheduledNotificationService._calculate_lease_payments_for_month(
            session=mock_db_session,
            lease_id=1,
            target_month=11,
            target_year=2024
        )
        
        # Assert
        assert amount == Decimal("500.00")


class TestSendRentReminders:
    """Tests for send_rent_reminders method."""
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.scheduled_service.NotificationService.create_notification')
    @patch('Backend.api.notifications.scheduled_service.determine_rent_status')
    async def test_send_rent_reminders_no_payment_sent(
        self, mock_determine_status, mock_create_notif, mock_db_session, mock_lease, mock_property, mock_landlord
    ):
        """Test sending rent reminders when rent is not paid."""
        # Arrange
        today = date.today()
        target_date = today + timedelta(days=3)
        
        # Set up relationships for eager loading
        mock_property.owner = mock_landlord
        mock_lease.property = mock_property
        
        # Mock lease query (with eager loaded relationships)
        lease_result = Mock()
        lease_result.scalars.return_value.all.return_value = [mock_lease]
        
        # Mock payment calculation (no payment)
        payment_result = Mock()
        payment_result.scalar.return_value = Decimal("0.00")
        
        # Set up execute to return results (lease query + payment query only)
        mock_db_session.execute.side_effect = [
            lease_result,  # Lease query with eager loaded relationships
            payment_result,  # Payment calculation
        ]
        
        mock_db_session.commit = AsyncMock()
        
        # Mock rent status determination
        mock_determine_status.return_value = (RentStatus.DUE, None)
        
        # Mock notification creation
        mock_notification = Mock(id=uuid4())
        mock_create_notif.return_value = mock_notification
        
        # Act
        result = await ScheduledNotificationService.send_rent_reminders(mock_db_session)
        
        # Assert
        assert result['success'] is True
        assert result['notifications_created'] == 1
        assert result['leases_processed'] == 1
        assert result['leases_skipped_already_paid'] == 0
        
        # Verify notification was created
        mock_create_notif.assert_called_once()
        call_kwargs = mock_create_notif.call_args.kwargs
        assert call_kwargs['user_id'] == mock_landlord.id
        assert call_kwargs['type'] == 'rent_reminder'
        assert call_kwargs['priority'] == 'high'
        assert 'metadata' in call_kwargs
        assert call_kwargs['metadata']['rent_status'] == RentStatus.DUE.value
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.scheduled_service.NotificationService.create_notification')
    @patch('Backend.api.notifications.scheduled_service.determine_rent_status')
    async def test_send_rent_reminders_fully_paid_skipped(
        self, mock_determine_status, mock_create_notif, mock_db_session, mock_lease, mock_property, mock_landlord
    ):
        """Test rent reminders are skipped when rent is fully paid."""
        # Arrange
        today = date.today()
        target_date = today + timedelta(days=3)
        
        # Set up relationships for eager loading
        mock_property.owner = mock_landlord
        mock_lease.property = mock_property
        
        # Mock lease query
        lease_result = Mock()
        lease_result.scalars.return_value.all.return_value = [mock_lease]
        
        # Mock payment calculation (full payment)
        payment_result = Mock()
        payment_result.scalar.return_value = Decimal("1500.00")
        
        mock_db_session.execute.side_effect = [
            lease_result,
            payment_result,
        ]
        
        mock_db_session.commit = AsyncMock()
        
        # Mock rent status determination (PAID)
        mock_determine_status.return_value = (RentStatus.PAID, None)
        
        # Act
        result = await ScheduledNotificationService.send_rent_reminders(mock_db_session)
        
        # Assert
        assert result['success'] is True
        assert result['notifications_created'] == 0
        assert result['leases_processed'] == 1
        assert result['leases_skipped_already_paid'] == 1
        
        # Verify notification was NOT created
        mock_create_notif.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.scheduled_service.NotificationService.create_notification')
    @patch('Backend.api.notifications.scheduled_service.determine_rent_status')
    async def test_send_rent_reminders_partial_payment(
        self, mock_determine_status, mock_create_notif, mock_db_session, mock_lease, mock_property, mock_landlord
    ):
        """Test sending rent reminders with partial payment shows remaining amount."""
        # Arrange
        today = date.today()
        
        # Set up relationships for eager loading
        mock_property.owner = mock_landlord
        mock_lease.property = mock_property
        
        # Mock lease query
        lease_result = Mock()
        lease_result.scalars.return_value.all.return_value = [mock_lease]
        
        # Mock partial payment
        payment_result = Mock()
        payment_result.scalar.return_value = Decimal("500.00")
        
        mock_db_session.execute.side_effect = [
            lease_result,
            payment_result,
        ]
        
        mock_db_session.commit = AsyncMock()
        
        # Mock rent status determination (PARTIAL)
        mock_determine_status.return_value = (RentStatus.PARTIAL, None)
        
        # Mock notification creation
        mock_notification = Mock(id=uuid4())
        mock_create_notif.return_value = mock_notification
        
        # Act
        result = await ScheduledNotificationService.send_rent_reminders(mock_db_session)
        
        # Assert
        assert result['notifications_created'] == 1
        
        # Verify notification message includes partial payment info
        call_kwargs = mock_create_notif.call_args.kwargs
        message = call_kwargs['message']
        assert '$500' in message or '500' in str(message)  # Amount paid mentioned
        assert '$1000' in message or '1000' in str(message)  # Remaining mentioned
        assert call_kwargs['metadata']['rent_status'] == RentStatus.PARTIAL.value
        assert call_kwargs['metadata']['amount_paid'] == '500.00'
        assert call_kwargs['metadata']['remaining_amount'] == '1000.00'
    
    @pytest.mark.asyncio
    async def test_send_rent_reminders_no_leases_found(self, mock_db_session):
        """Test rent reminders when no leases match criteria."""
        # Arrange
        lease_result = Mock()
        lease_result.scalars.return_value.all.return_value = []
        
        mock_db_session.execute.return_value = lease_result
        mock_db_session.commit = AsyncMock()
        
        # Act
        result = await ScheduledNotificationService.send_rent_reminders(mock_db_session)
        
        # Assert
        assert result['success'] is True
        assert result['notifications_created'] == 0
        assert result['leases_processed'] == 0
        assert result['leases_skipped_already_paid'] == 0
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.scheduled_service.NotificationService.create_notification')
    async def test_send_rent_reminders_property_not_found(
        self, mock_create_notif, mock_db_session, mock_lease
    ):
        """Test rent reminders when property is not found."""
        # Arrange
        # Set property to None (simulating missing relationship)
        mock_lease.property = None
        
        lease_result = Mock()
        lease_result.scalars.return_value.all.return_value = [mock_lease]
        
        mock_db_session.execute.side_effect = [
            lease_result,
        ]
        
        mock_db_session.commit = AsyncMock()
        
        # Act
        result = await ScheduledNotificationService.send_rent_reminders(mock_db_session)
        
        # Assert
        assert result['notifications_created'] == 0
        mock_create_notif.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.scheduled_service.NotificationService.create_notification')
    async def test_send_rent_reminders_landlord_not_found(
        self, mock_create_notif, mock_db_session, mock_lease, mock_property
    ):
        """Test rent reminders when landlord user is not found."""
        # Arrange
        # Set up relationships with no owner
        mock_property.owner = None
        mock_lease.property = mock_property
        
        lease_result = Mock()
        lease_result.scalars.return_value.all.return_value = [mock_lease]
        
        mock_db_session.execute.side_effect = [
            lease_result,
        ]
        
        mock_db_session.commit = AsyncMock()
        
        # Act
        result = await ScheduledNotificationService.send_rent_reminders(mock_db_session)
        
        # Assert
        assert result['notifications_created'] == 0
        mock_create_notif.assert_not_called()


class TestSendLeaseExpiringNotifications:
    """Tests for send_lease_expiring_notifications method."""
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.scheduled_service.NotificationService.create_notification')
    async def test_send_lease_expiring_30_days(
        self, mock_create_notif, mock_db_session, mock_lease, mock_property, mock_landlord
    ):
        """Test sending lease expiring notification for lease expiring in 30 days."""
        # Arrange
        today = date.today()
        mock_lease.end_date = today + timedelta(days=30)
        
        # Set up relationships for eager loading
        mock_property.owner = mock_landlord
        mock_lease.property = mock_property
        
        lease_result = Mock()
        lease_result.scalars.return_value.all.return_value = [mock_lease]
        
        mock_db_session.execute.side_effect = [
            lease_result,
        ]
        
        mock_db_session.commit = AsyncMock()
        
        # Mock notification creation
        mock_notification = Mock(id=uuid4())
        mock_create_notif.return_value = mock_notification
        
        # Act
        result = await ScheduledNotificationService.send_lease_expiring_notifications(mock_db_session)
        
        # Assert
        assert result['success'] is True
        assert result['notifications_created'] == 1
        assert result['leases_processed'] == 1
        
        # Verify notification was created with high priority (30 days)
        call_kwargs = mock_create_notif.call_args.kwargs
        assert call_kwargs['user_id'] == mock_landlord.id
        assert call_kwargs['type'] == 'lease_expiring'
        assert call_kwargs['priority'] == 'high'
        assert '30 Days' in call_kwargs['title']
        assert call_kwargs['metadata']['days_until_expiry'] == 30
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.scheduled_service.NotificationService.create_notification')
    async def test_send_lease_expiring_60_days(
        self, mock_create_notif, mock_db_session, mock_lease, mock_property, mock_landlord
    ):
        """Test sending lease expiring notification for lease expiring in 60 days."""
        # Arrange
        today = date.today()
        mock_lease.end_date = today + timedelta(days=60)
        
        # Set up relationships for eager loading
        mock_property.owner = mock_landlord
        mock_lease.property = mock_property
        
        lease_result = Mock()
        lease_result.scalars.return_value.all.return_value = [mock_lease]
        
        mock_db_session.execute.side_effect = [
            lease_result,
        ]
        
        mock_db_session.commit = AsyncMock()
        
        # Mock notification creation
        mock_notification = Mock(id=uuid4())
        mock_create_notif.return_value = mock_notification
        
        # Act
        result = await ScheduledNotificationService.send_lease_expiring_notifications(mock_db_session)
        
        # Assert
        assert result['notifications_created'] == 1
        
        # Verify notification was created with normal priority (60 days)
        call_kwargs = mock_create_notif.call_args.kwargs
        assert call_kwargs['priority'] == 'normal'
        assert '60 Days' in call_kwargs['title']
        assert call_kwargs['metadata']['days_until_expiry'] == 60
    
    @pytest.mark.asyncio
    async def test_send_lease_expiring_no_leases_found(self, mock_db_session):
        """Test lease expiring when no leases match criteria."""
        # Arrange
        lease_result = Mock()
        lease_result.scalars.return_value.all.return_value = []
        
        mock_db_session.execute.return_value = lease_result
        mock_db_session.commit = AsyncMock()
        
        # Act
        result = await ScheduledNotificationService.send_lease_expiring_notifications(mock_db_session)
        
        # Assert
        assert result['success'] is True
        assert result['notifications_created'] == 0
        assert result['leases_processed'] == 0
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.scheduled_service.NotificationService.create_notification')
    async def test_send_lease_expiring_continues_on_error(
        self, mock_create_notif, mock_db_session, mock_lease, mock_property, mock_landlord
    ):
        """Test lease expiring continues processing after an error."""
        # Arrange - Create two leases
        today = date.today()
        lease1 = mock_lease
        lease1.id = 1
        lease1.end_date = today + timedelta(days=30)
        lease1.property = None  # First lease - property not found
        
        lease2 = Lease(
            id=2,
            property_id=2,
            tenant_id=2,
            start_date=date(2024, 1, 1),
            end_date=today + timedelta(days=30),
            monthly_rent=Decimal("2000.00"),
            security_deposit=Decimal("2000.00"),
            rent_due_day=5,
            status=LeaseStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        # Second lease - succeeds with proper relationships
        mock_property.owner = mock_landlord
        lease2.property = mock_property
        
        lease_result = Mock()
        lease_result.scalars.return_value.all.return_value = [lease1, lease2]
        
        mock_db_session.execute.side_effect = [
            lease_result,
        ]
        
        mock_db_session.commit = AsyncMock()
        
        # Mock notification creation for second lease
        mock_notification = Mock(id=uuid4())
        mock_create_notif.return_value = mock_notification
        
        # Act
        result = await ScheduledNotificationService.send_lease_expiring_notifications(mock_db_session)
        
        # Assert - Should process both but only create notification for second
        assert result['notifications_created'] == 1
        assert result['leases_processed'] == 2
        mock_create_notif.assert_called_once()

