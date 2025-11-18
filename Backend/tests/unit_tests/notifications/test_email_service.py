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


class TestSendTenantReminderEmail:
    """Tests for send_tenant_reminder_email function."""
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_success(self, mock_send_raw_email):
        """Test successful tenant reminder email sending."""
        mock_send_raw_email.return_value = True
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='John Doe',
            event_type='rent',
            event_title='Rent Due Soon',
            event_subtitle='Your rent payment is due',
            event_date=None,
            event_amount=1500.00,
            days_remaining=3,
            property_name='Test Property',
            unit_name='Unit 101',
            metadata={'tenant_id': 123}
        )
        
        assert success is True
        assert mock_send_raw_email.called
        
        # Verify correct parameters passed
        call_args = mock_send_raw_email.call_args
        assert call_args[1]['to_email'] == 'tenant@example.com'
        assert call_args[1]['to_name'] == 'John Doe'
        assert 'rent' in call_args[1]['subject'].lower()
        assert call_args[1]['metadata']['event_type'] == 'rent'
        assert call_args[1]['metadata']['event_amount'] == 1500.00
        assert call_args[1]['metadata']['days_remaining'] == 3
        assert 'Test Property' in call_args[1]['html_content']
        assert 'Unit 101' in call_args[1]['html_content']
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_lease_expiry(self, mock_send_raw_email):
        """Test tenant reminder email for lease expiry."""
        mock_send_raw_email.return_value = True
        
        from datetime import datetime, timezone
        expiry_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='Jane Smith',
            event_type='lease_expiry',
            event_title='Lease Expiring Soon',
            event_subtitle='Your lease will expire soon',
            event_date=expiry_date,
            event_amount=None,
            days_remaining=30,
            property_name='Apartment Complex',
            unit_name=None,
            metadata=None
        )
        
        assert success is True
        call_args = mock_send_raw_email.call_args
        assert call_args[1]['metadata']['event_type'] == 'lease_expiry'
        assert 'lease' in call_args[1]['subject'].lower()
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_invoice(self, mock_send_raw_email):
        """Test tenant reminder email for invoice."""
        mock_send_raw_email.return_value = True
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='Bob Johnson',
            event_type='invoice',
            event_title='Invoice Due',
            event_subtitle='You have an outstanding invoice',
            event_date=None,
            event_amount=500.00,
            days_remaining=None,
            property_name=None,
            unit_name=None,
            metadata=None
        )
        
        assert success is True
        call_args = mock_send_raw_email.call_args
        assert call_args[1]['metadata']['event_type'] == 'invoice'
        assert '$500.00' in call_args[1]['html_content'] or '500.00' in call_args[1]['html_content']
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_insurance(self, mock_send_raw_email):
        """Test tenant reminder email for insurance."""
        mock_send_raw_email.return_value = True
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='Insurance Co',
            event_type='insurance',
            event_title='Insurance Renewal',
            event_subtitle='Insurance policy needs renewal',
            event_date=None,
            event_amount=None,
            days_remaining=60,
            property_name='Commercial Building',
            unit_name=None,
            metadata=None
        )
        
        assert success is True
        call_args = mock_send_raw_email.call_args
        assert call_args[1]['metadata']['event_type'] == 'insurance'
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_failure(self, mock_send_raw_email):
        """Test tenant reminder email sending failure."""
        mock_send_raw_email.return_value = False
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='Test Tenant',
            event_type='rent',
            event_title='Test',
            event_subtitle='Test subtitle',
            event_date=None,
            event_amount=None,
            days_remaining=None,
            property_name=None,
            unit_name=None,
            metadata=None
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_exception_handling(self, mock_send_raw_email):
        """Test tenant reminder email with exception."""
        mock_send_raw_email.side_effect = Exception('SendGrid error')
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='Test Tenant',
            event_type='rent',
            event_title='Test',
            event_subtitle='Test subtitle',
            event_date=None,
            event_amount=None,
            days_remaining=None,
            property_name=None,
            unit_name=None,
            metadata=None
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_with_date_and_amount(self, mock_send_raw_email):
        """Test tenant reminder email with date and amount."""
        mock_send_raw_email.return_value = True
        
        from datetime import datetime, timezone
        due_date = datetime(2024, 11, 15, tzinfo=timezone.utc)
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='Test Tenant',
            event_type='rent',
            event_title='Rent Due',
            event_subtitle='Your rent is due',
            event_date=due_date,
            event_amount=2000.00,
            days_remaining=5,
            property_name='Test Property',
            unit_name='Unit 202',
            metadata={'tenant_id': 456}
        )
        
        assert success is True
        call_args = mock_send_raw_email.call_args
        # Verify metadata includes event details
        assert call_args[1]['metadata']['event_type'] == 'rent'
        assert call_args[1]['metadata']['event_amount'] == 2000.00
        assert call_args[1]['metadata']['days_remaining'] == 5
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_with_custom_subject(self, mock_send_raw_email):
        """Test tenant reminder email with custom subject line."""
        mock_send_raw_email.return_value = True
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='John Doe',
            event_type='rent',
            event_title='Rent Due Soon',
            event_subtitle='Your rent payment is due',
            event_date=None,
            event_amount=1500.00,
            days_remaining=3,
            property_name='Test Property',
            unit_name='Unit 101',
            metadata=None,
            custom_subject='Urgent: Rent Payment Reminder'
        )
        
        assert success is True
        call_args = mock_send_raw_email.call_args
        # Verify custom subject is used instead of default
        assert call_args[1]['subject'] == 'Urgent: Rent Payment Reminder'
        assert 'Rent Due Soon' not in call_args[1]['subject']  # Default pattern should not appear
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_with_custom_message(self, mock_send_raw_email):
        """Test tenant reminder email with custom message body."""
        mock_send_raw_email.return_value = True
        
        custom_message = "This is a personalized reminder message from your landlord."
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='Jane Smith',
            event_type='rent',
            event_title='Rent Due Soon',
            event_subtitle='Your rent payment is due',
            event_date=None,
            event_amount=1500.00,
            days_remaining=3,
            property_name='Test Property',
            unit_name='Unit 101',
            metadata=None,
            custom_message=custom_message
        )
        
        assert success is True
        call_args = mock_send_raw_email.call_args
        # Verify custom message appears in HTML content
        assert custom_message in call_args[1]['html_content']
        # Verify default message does not appear
        assert 'This is a friendly reminder that your rent payment is' not in call_args[1]['html_content']
        # Verify metadata rows are still included (amount, due date, etc.)
        assert '1500.00' in call_args[1]['html_content'] or '$1,500.00' in call_args[1]['html_content']
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_with_both_custom_fields(self, mock_send_raw_email):
        """Test tenant reminder email with both custom subject and message."""
        mock_send_raw_email.return_value = True
        
        from datetime import datetime, timezone
        due_date = datetime(2024, 11, 15, tzinfo=timezone.utc)
        custom_subject = "Important: Payment Due This Week"
        custom_message = "Please note that your rent payment is due in 3 days. We appreciate your timely payment."
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='Bob Johnson',
            event_type='rent',
            event_title='Rent Due Soon',
            event_subtitle='Your rent payment is due',
            event_date=due_date,
            event_amount=1500.00,
            days_remaining=3,
            property_name='Test Property',
            unit_name='Unit 202',
            metadata={'tenant_id': 789},
            custom_subject=custom_subject,
            custom_message=custom_message
        )
        
        assert success is True
        call_args = mock_send_raw_email.call_args
        # Verify both custom fields are used
        assert call_args[1]['subject'] == custom_subject
        assert custom_message in call_args[1]['html_content']
        # Verify metadata is still included
        assert call_args[1]['metadata']['event_type'] == 'rent'
        assert call_args[1]['metadata']['event_amount'] == 1500.00
        # Verify property and unit info still appear
        assert 'Test Property' in call_args[1]['html_content']
        assert 'Unit 202' in call_args[1]['html_content']
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_with_null_custom_fields(self, mock_send_raw_email):
        """Test tenant reminder email with null custom fields (should use defaults)."""
        mock_send_raw_email.return_value = True
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='Test Tenant',
            event_type='rent',
            event_title='Rent Due Soon',
            event_subtitle='Your rent payment is due',
            event_date=None,
            event_amount=1500.00,
            days_remaining=3,
            property_name='Test Property',
            unit_name='Unit 101',
            metadata=None,
            custom_subject=None,
            custom_message=None
        )
        
        assert success is True
        call_args = mock_send_raw_email.call_args
        # Verify default subject is used
        assert call_args[1]['subject'] == 'Reminder: Rent Due Soon'
        # Verify default message is used
        assert 'This is a friendly reminder that your rent payment is' in call_args[1]['html_content']
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_custom_message_with_metadata_preserved(self, mock_send_raw_email):
        """Test that metadata rows (amount, date, property, unit) are preserved even with custom message."""
        mock_send_raw_email.return_value = True
        
        from datetime import datetime, timezone
        due_date = datetime(2024, 11, 15, tzinfo=timezone.utc)
        custom_message = "Custom reminder message."
        
        success = await EmailService.send_tenant_reminder_email(
            tenant_email='tenant@example.com',
            tenant_name='Test Tenant',
            event_type='rent',
            event_title='Rent Due',
            event_subtitle='Your rent is due',
            event_date=due_date,
            event_amount=2000.00,
            days_remaining=5,
            property_name='Apartment Complex',
            unit_name='Unit 303',
            metadata=None,
            custom_message=custom_message
        )
        
        assert success is True
        call_args = mock_send_raw_email.call_args
        html_content = call_args[1]['html_content']
        
        # Verify custom message appears
        assert custom_message in html_content
        
        # Verify metadata rows are still included (critical requirement)
        assert 'Apartment Complex' in html_content  # Property name
        assert 'Unit 303' in html_content  # Unit name
        assert '2000.00' in html_content or '$2,000.00' in html_content  # Amount
        assert 'November' in html_content or 'Nov' in html_content  # Date (month)
        assert '15' in html_content or '2024' in html_content  # Date (day/year)
    
    @pytest.mark.asyncio
    @patch('Backend.api.notifications.email_service.SendGridService.send_raw_email')
    async def test_send_tenant_reminder_email_custom_fields_all_event_types(self, mock_send_raw_email):
        """Test custom fields work correctly with all event types."""
        mock_send_raw_email.return_value = True
        
        event_types = ['rent', 'lease_expiry', 'invoice', 'maintenance', 'insurance']
        
        for event_type in event_types:
            custom_subject = f"Custom Subject for {event_type}"
            custom_message = f"Custom message for {event_type} reminder"
            
            success = await EmailService.send_tenant_reminder_email(
                tenant_email='tenant@example.com',
                tenant_name='Test Tenant',
                event_type=event_type,
                event_title=f'{event_type.title()} Reminder',
                event_subtitle=f'Your {event_type} is due',
                event_date=None,
                event_amount=100.00 if event_type in ['rent', 'invoice'] else None,
                days_remaining=5,
                property_name='Test Property',
                unit_name=None,
                metadata=None,
                custom_subject=custom_subject,
                custom_message=custom_message
            )
            
            assert success is True, f"Failed for event_type: {event_type}"
            call_args = mock_send_raw_email.call_args
            
            # Verify custom fields are used
            assert call_args[1]['subject'] == custom_subject
            assert custom_message in call_args[1]['html_content']
            assert call_args[1]['metadata']['event_type'] == event_type

