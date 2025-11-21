"""
Unit tests for billing webhook tasks.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from Backend.api.billing.webhook_tasks import (
    send_subscription_created_email,
    send_payment_succeeded_email,
    send_payment_failed_email,
    send_trial_ending_email
)


pytestmark = pytest.mark.unit


class TestEmailTasks:
    """Tests for email sending tasks."""
    
    @patch('Backend.api.notifications.sendgrid_service.SendGridService.send_raw_email')
    @patch('Backend.api.billing.email_templates.BillingEmailTemplates')
    async def test_send_subscription_created_email(
        self, mock_templates, mock_send
    ):
        """Test send_subscription_created_email."""
        # Arrange
        mock_templates.create_subscription_created_email.return_value = ("Subject", "Body")
        
        # Act
        await send_subscription_created_email(
            'test@example.com', 'Test', 'User', 'Pro', 1000, 'usd',
            'sub_123', None, None, 'evt_123'
        )
        
        # Assert
        mock_send.assert_called_once()
    
    @patch('Backend.api.notifications.sendgrid_service.SendGridService.send_raw_email')
    @patch('Backend.api.billing.email_templates.BillingEmailTemplates')
    async def test_send_payment_succeeded_email(
        self, mock_templates, mock_send
    ):
        """Test send_payment_succeeded_email."""
        # Arrange
        mock_templates.create_payment_succeeded_email.return_value = ("Subject", "Body")
        
        # Act
        await send_payment_succeeded_email(
            'test@example.com', 'Test', 'User', 'Pro', 1000, 'usd',
            'in_123', 'url', None, 'evt_123',
            stripe_invoice_id='in_123', event_id='evt_123'
        )
        
        # Assert
        mock_send.assert_called_once()
    
    @patch('Backend.api.notifications.sendgrid_service.SendGridService.send_raw_email')
    @patch('Backend.api.billing.email_templates.BillingEmailTemplates')
    async def test_send_payment_failed_email(
        self, mock_templates, mock_send
    ):
        """Test send_payment_failed_email."""
        # Arrange
        mock_templates.create_payment_failed_email.return_value = ("Subject", "Body")
        
        # Act
        await send_payment_failed_email(
            'test@example.com', 'Test', 'User', 'Pro', 1000, 'usd',
            1, 'url', 'evt_123',
            stripe_invoice_id='in_123', event_id='evt_123'
        )
        
        # Assert
        mock_send.assert_called_once()
    
    @patch('Backend.api.notifications.sendgrid_service.SendGridService.send_raw_email')
    @patch('Backend.api.billing.email_templates.BillingEmailTemplates')
    async def test_send_trial_ending_email(
        self, mock_templates, mock_send
    ):
        """Test send_trial_ending_email."""
        # Arrange
        mock_templates.create_trial_ending_email.return_value = ("Subject", "Body")
        
        # Act
        await send_trial_ending_email(
            'test@example.com', 'Test', 'User', 3, 'Pro', 1000, 'usd',
            'sub_123', 'evt_123'
        )
        
        # Assert
        mock_send.assert_called_once()
