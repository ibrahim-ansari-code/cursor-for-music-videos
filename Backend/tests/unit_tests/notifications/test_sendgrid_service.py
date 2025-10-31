"""
Unit tests for SendGrid email service.

Tests HTML template generation and email sending functionality.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from Backend.api.notifications.sendgrid_service import SendGridService

pytestmark = pytest.mark.unit


class TestGetNotificationIcon:
    """Tests for _get_notification_icon helper."""
    
    def test_get_icon_rent_reminder(self):
        """Test icon for rent reminder."""
        icon = SendGridService._get_notification_icon('rent_reminder')
        assert icon == '💰'
    
    def test_get_icon_lease_expiring(self):
        """Test icon for lease expiring."""
        icon = SendGridService._get_notification_icon('lease_expiring')
        assert icon == '📅'
    
    def test_get_icon_system_update(self):
        """Test icon for system update."""
        icon = SendGridService._get_notification_icon('system_update')
        assert icon == 'ℹ️'
    
    def test_get_icon_unknown_type(self):
        """Test icon for unknown type defaults to bell."""
        icon = SendGridService._get_notification_icon('unknown_type')
        assert icon == '🔔'


class TestCreateHTMLTemplate:
    """Tests for _create_html_template function."""
    
    def test_create_html_template_with_link(self):
        """Test HTML email generation with action link."""
        html = SendGridService._create_html_template(
            notification_type='rent_reminder',
            title='Rent Due',
            message='Your rent is due soon',
            link='/properties/123',
            icon='💰'
        )
        
        assert '💰' in html  # Icon
        assert 'Rent Due' in html  # Title
        assert 'Your rent is due soon' in html  # Message
        assert 'View Details' in html  # Button text
        assert '/properties/123' in html  # Link
        assert 'Brikli Property Management' in html  # Branding
    
    def test_create_html_template_without_link(self):
        """Test HTML email generation without action link."""
        html = SendGridService._create_html_template(
            notification_type='system_update',
            title='System Maintenance',
            message='Scheduled maintenance tonight',
            icon='ℹ️'
        )
        
        assert 'System Maintenance' in html
        assert 'Scheduled maintenance tonight' in html
        assert 'View Details' not in html  # No button without link
    
    def test_create_html_template_relative_link(self):
        """Test HTML email with relative link gets full URL."""
        html = SendGridService._create_html_template(
            notification_type='lease_expiring',
            title='Lease Expiring',
            message='Lease expires in 30 days',
            link='/leases/456',
            icon='📅'
        )
        
        # Should contain full URL with http or https
        assert 'http' in html
        assert '/leases/456' in html
    
    def test_create_html_template_responsive_design(self):
        """Test HTML includes responsive meta tags."""
        html = SendGridService._create_html_template(
            notification_type='rent_reminder',
            title='Test',
            message='Test',
            icon='🔔'
        )
        
        assert 'viewport' in html
        assert 'meta' in html
        assert 'table' in html  # Uses table layout for email compatibility


class TestSendEmail:
    """Tests for send_email function."""
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.sendgrid_service.SendGridAPIClient')
    @patch('Backend.api.notifications.sendgrid_service.settings')
    async def test_send_email_success(self, mock_settings, mock_sendgrid_client):
        """Test successful email sending."""
        # Configure mocks
        mock_settings.SENDGRID_API_KEY = 'test_key'
        mock_settings.SENDGRID_FROM_EMAIL = 'test@example.com'
        mock_settings.SENDGRID_FROM_NAME = 'Test'
        mock_settings.FRONTEND_URL = 'https://app.test.com'
        
        # Mock SendGrid client
        mock_client_instance = Mock()
        mock_response = Mock()
        mock_response.status_code = 202
        mock_client_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_client_instance
        
        # Send email
        success = await SendGridService.send_email(
            to_email='user@example.com',
            to_name='Test User',
            subject='Test Subject',
            notification_type='rent_reminder',
            title='Test Title',
            message='Test Message'
        )
        
        assert success is True
        assert mock_client_instance.send.called
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.sendgrid_service.settings')
    async def test_send_email_no_api_key(self, mock_settings):
        """Test email sending without API key configured."""
        mock_settings.SENDGRID_API_KEY = None
        
        success = await SendGridService.send_email(
            to_email='user@example.com',
            to_name='Test User',
            subject='Test',
            notification_type='rent_reminder',
            title='Test',
            message='Test'
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.sendgrid_service.SendGridAPIClient')
    @patch('Backend.api.notifications.sendgrid_service.settings')
    async def test_send_email_failure(self, mock_settings, mock_sendgrid_client):
        """Test email sending failure."""
        # Configure mocks
        mock_settings.SENDGRID_API_KEY = 'test_key'
        mock_settings.SENDGRID_FROM_EMAIL = 'test@example.com'
        mock_settings.SENDGRID_FROM_NAME = 'Test'
        
        # Mock SendGrid error response
        mock_client_instance = Mock()
        mock_response = Mock()
        mock_response.status_code = 400
        mock_client_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_client_instance
        
        success = await SendGridService.send_email(
            to_email='user@example.com',
            to_name='Test User',
            subject='Test',
            notification_type='rent_reminder',
            title='Test',
            message='Test'
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.sendgrid_service.SendGridAPIClient')
    @patch('Backend.api.notifications.sendgrid_service.settings')
    async def test_send_email_with_link(self, mock_settings, mock_sendgrid_client):
        """Test email sending with action link."""
        # Configure mocks
        mock_settings.SENDGRID_API_KEY = 'test_key'
        mock_settings.SENDGRID_FROM_EMAIL = 'test@example.com'
        mock_settings.SENDGRID_FROM_NAME = 'Test'
        
        mock_client_instance = Mock()
        mock_response = Mock()
        mock_response.status_code = 202
        mock_client_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_client_instance
        
        success = await SendGridService.send_email(
            to_email='user@example.com',
            to_name='Test User',
            subject='Test',
            notification_type='rent_reminder',
            title='Test',
            message='Test',
            link='/properties/123'
        )
        
        assert success is True
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.sendgrid_service.SendGridAPIClient')
    @patch('Backend.api.notifications.sendgrid_service.settings')
    async def test_send_email_exception_handling(self, mock_settings, mock_sendgrid_client):
        """Test email sending with exception."""
        # Configure mocks
        mock_settings.SENDGRID_API_KEY = 'test_key'
        mock_settings.SENDGRID_FROM_EMAIL = 'test@example.com'
        mock_settings.SENDGRID_FROM_NAME = 'Test'
        
        # Mock client to raise exception
        mock_sendgrid_client.side_effect = Exception('SendGrid error')
        
        success = await SendGridService.send_email(
            to_email='user@example.com',
            to_name='Test User',
            subject='Test',
            notification_type='rent_reminder',
            title='Test',
            message='Test'
        )
        
        assert success is False

