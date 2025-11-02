"""
Unit tests for Email Service.

Tests the email notification sending wrapper service.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from Backend.api.notifications.email_service import EmailService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_user_data():
    """Create mock user data."""
    return {
        'id': uuid4(),
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User'
    }


class TestSendNotificationEmail:
    """Tests for send_notification_email function."""
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_success(self, mock_send_email, mock_user_data):
        """Test successful email sending."""
        mock_send_email.return_value = True
        
        success = await EmailService.send_notification_email(
            user_id=mock_user_data['id'],
            user_email=mock_user_data['email'],
            user_first_name=mock_user_data['first_name'],
            user_last_name=mock_user_data['last_name'],
            notification_type='rent_reminder',
            title='Rent Due Soon',
            message='Your rent is due in 3 days',
            link='/properties/123'
        )
        
        assert success is True
        assert mock_send_email.called
        
        # Verify correct parameters passed
        call_args = mock_send_email.call_args
        assert call_args[1]['to_email'] == mock_user_data['email']
        assert call_args[1]['notification_type'] == 'rent_reminder'
        assert call_args[1]['title'] == 'Rent Due Soon'
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_failure(self, mock_send_email, mock_user_data):
        """Test email sending failure."""
        mock_send_email.return_value = False
        
        success = await EmailService.send_notification_email(
            user_id=mock_user_data['id'],
            user_email=mock_user_data['email'],
            user_first_name=mock_user_data['first_name'],
            user_last_name=mock_user_data['last_name'],
            notification_type='rent_reminder',
            title='Test',
            message='Test message'
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_with_link(self, mock_send_email, mock_user_data):
        """Test email sending with action link."""
        mock_send_email.return_value = True
        
        success = await EmailService.send_notification_email(
            user_id=mock_user_data['id'],
            user_email=mock_user_data['email'],
            user_first_name=mock_user_data['first_name'],
            user_last_name=mock_user_data['last_name'],
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
    async def test_send_notification_email_without_link(self, mock_send_email, mock_user_data):
        """Test email sending without action link."""
        mock_send_email.return_value = True
        
        success = await EmailService.send_notification_email(
            user_id=mock_user_data['id'],
            user_email=mock_user_data['email'],
            user_first_name=mock_user_data['first_name'],
            user_last_name=mock_user_data['last_name'],
            notification_type='system_update',
            title='System Update',
            message='We have updates'
        )
        
        assert success is True
        call_args = mock_send_email.call_args
        assert call_args[1].get('link') is None
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_user_name_formatting(self, mock_send_email, mock_user_data):
        """Test user name formatting in email."""
        mock_send_email.return_value = True
        
        success = await EmailService.send_notification_email(
            user_id=mock_user_data['id'],
            user_email=mock_user_data['email'],
            user_first_name='John',
            user_last_name='Doe',
            notification_type='rent_reminder',
            title='Test',
            message='Test'
        )
        
        assert success is True
        call_args = mock_send_email.call_args
        assert call_args[1]['to_name'] == 'John Doe'
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_exception_handling(self, mock_send_email, mock_user_data):
        """Test email sending with exception."""
        mock_send_email.side_effect = Exception('SendGrid error')
        
        success = await EmailService.send_notification_email(
            user_id=mock_user_data['id'],
            user_email=mock_user_data['email'],
            user_first_name=mock_user_data['first_name'],
            user_last_name=mock_user_data['last_name'],
            notification_type='rent_reminder',
            title='Test',
            message='Test'
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_email')
    async def test_send_notification_email_with_none_names(self, mock_send_email, mock_user_data):
        """Test email sending with None first/last names."""
        mock_send_email.return_value = True
        
        success = await EmailService.send_notification_email(
            user_id=mock_user_data['id'],
            user_email=mock_user_data['email'],
            user_first_name=None,
            user_last_name=None,
            notification_type='rent_reminder',
            title='Test',
            message='Test'
        )
        
        assert success is True
        call_args = mock_send_email.call_args
        assert call_args[1]['to_name'] == 'Brikli User'

