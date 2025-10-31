"""
Unit tests for Email Service.

Tests the email notification sending wrapper service.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from Backend.api.notifications.email_service import EmailService
from Backend.models.user import User
from Backend.models.notification import Notification

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_user():
    """Create a mock user."""
    return User(
        id=uuid4(),
        email='test@example.com',
        first_name='Test',
        last_name='User',
        user_type='LANDLORD',
        is_active=True,
        is_email_verified=True
    )


@pytest.fixture
def mock_notification():
    """Create a mock notification."""
    return Notification(
        id=uuid4(),
        user_id=uuid4(),
        type='rent_reminder',
        title='Rent Due Soon',
        message='Your rent of $1,500 is due in 3 days',
        link='/properties/123',
        priority='high',
        metadata={'amount': '1500', 'property_id': '123'},
        delivery_channels=['in_app', 'email']
    )


class TestSendNotificationEmail:
    """Tests for send_notification_email function."""
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_success(self, mock_send_email, mock_user):
        """Test successful email sending."""
        mock_send_email.return_value = True
        
        success = await EmailService.send_notification_email(
            user=mock_user,
            notification_type='rent_reminder',
            title='Rent Due Soon',
            message='Your rent is due in 3 days',
            link='/properties/123'
        )
        
        assert success is True
        assert mock_send_email.called
        
        # Verify correct parameters passed
        call_args = mock_send_email.call_args
        assert call_args[1]['to_email'] == mock_user.email
        assert call_args[1]['notification_type'] == 'rent_reminder'
        assert call_args[1]['title'] == 'Rent Due Soon'
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_failure(self, mock_send_email, mock_user):
        """Test email sending failure."""
        mock_send_email.return_value = False
        
        success = await EmailService.send_notification_email(
            user=mock_user,
            notification_type='rent_reminder',
            title='Test',
            message='Test message'
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_with_link(self, mock_send_email, mock_user):
        """Test email sending with action link."""
        mock_send_email.return_value = True
        
        success = await EmailService.send_notification_email(
            user=mock_user,
            notification_type='lease_expiring',
            title='Lease Expiring',
            message='Your lease expires soon',
            link='/leases/456'
        )
        
        assert success is True
        call_args = mock_send_email.call_args
        assert call_args[1]['link'] == '/leases/456'
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_without_link(self, mock_send_email, mock_user):
        """Test email sending without action link."""
        mock_send_email.return_value = True
        
        success = await EmailService.send_notification_email(
            user=mock_user,
            notification_type='system_update',
            title='System Update',
            message='We have updates'
        )
        
        assert success is True
        call_args = mock_send_email.call_args
        assert call_args[1].get('link') is None
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_user_name_formatting(self, mock_send_email, mock_user):
        """Test user name formatting in email."""
        mock_send_email.return_value = True
        mock_user.first_name = 'John'
        mock_user.last_name = 'Doe'
        
        success = await EmailService.send_notification_email(
            user=mock_user,
            notification_type='rent_reminder',
            title='Test',
            message='Test'
        )
        
        assert success is True
        call_args = mock_send_email.call_args
        assert call_args[1]['to_name'] == 'John Doe'
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_exception_handling(self, mock_send_email, mock_user):
        """Test email sending with exception."""
        mock_send_email.side_effect = Exception('SendGrid error')
        
        success = await EmailService.send_notification_email(
            user=mock_user,
            notification_type='rent_reminder',
            title='Test',
            message='Test'
        )
        
        assert success is False


class TestSendTestEmail:
    """Tests for send_test_email function."""
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_test_email_success(self, mock_send_email, mock_user):
        """Test successful test email sending."""
        mock_send_email.return_value = True
        
        success = await EmailService.send_test_email(user=mock_user)
        
        assert success is True
        assert mock_send_email.called
        
        # Verify test email parameters
        call_args = mock_send_email.call_args
        assert 'Test' in call_args[1]['title']
        assert call_args[1]['notification_type'] == 'system_update'
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_test_email_failure(self, mock_send_email, mock_user):
        """Test test email sending failure."""
        mock_send_email.return_value = False
        
        success = await EmailService.send_test_email(user=mock_user)
        
        assert success is False

