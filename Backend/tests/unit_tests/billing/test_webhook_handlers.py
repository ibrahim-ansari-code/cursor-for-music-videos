"""
Unit tests for billing webhook handlers.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from Backend.api.billing.webhook_handlers import (
    handle_subscription_created,
    handle_subscription_updated,
    handle_subscription_deleted,
    handle_payment_succeeded,
    handle_payment_failed,
    handle_trial_will_end
)


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_background_tasks():
    """Create mock background tasks."""
    return MagicMock()


class TestSubscriptionHandlers:
    """Tests for subscription webhook handlers."""
    
    @patch('Backend.api.billing.webhook_handlers.sync_subscription_from_stripe')
    async def test_handle_created(self, mock_sync, mock_session, mock_background_tasks):
        """Test handle_subscription_created."""
        # Arrange
        event = MagicMock()
        event.data.object = {'id': 'sub_123'}
        
        mock_sub = MagicMock(user_id='user_123', plan_id='plan_123')
        mock_sync.return_value = mock_sub
        
        # Mock database queries
        mock_user = MagicMock(email='test@example.com', first_name='Test', last_name='User')
        mock_plan = MagicMock(name='Pro', amount=1000, currency='usd')
        mock_session.execute.side_effect = [
            MagicMock(scalar_one=lambda: mock_user),
            MagicMock(scalar_one=lambda: mock_plan)
        ]
        
        # Act
        await handle_subscription_created(event, mock_session, mock_background_tasks)
        
        # Assert
        mock_sync.assert_called_once()
        mock_background_tasks.add_task.assert_called()
    
    @patch('Backend.api.billing.webhook_handlers.sync_subscription_from_stripe')
    async def test_handle_updated(self, mock_sync, mock_session, mock_background_tasks):
        """Test handle_subscription_updated."""
        # Arrange
        event = MagicMock()
        event.data.object = {'id': 'sub_123'}
        
        # Act
        await handle_subscription_updated(event, mock_session, mock_background_tasks)
        
        # Assert
        mock_sync.assert_called_once()
    
    @patch('Backend.api.billing.webhook_handlers.sync_subscription_from_stripe')
    async def test_handle_deleted(self, mock_sync, mock_session, mock_background_tasks):
        """Test handle_subscription_deleted."""
        # Arrange
        event = MagicMock()
        event.data.object = {'id': 'sub_123'}
        
        # Act
        await handle_subscription_deleted(event, mock_session, mock_background_tasks)
        
        # Assert
        mock_sync.assert_called_once()


class TestPaymentHandlers:
    """Tests for payment webhook handlers."""
    
    @patch('Backend.api.billing.webhook_handlers.sync_subscription_from_stripe')
    async def test_handle_payment_succeeded(self, mock_sync, mock_session, mock_background_tasks):
        """Test handle_payment_succeeded."""
        # Arrange
        event = MagicMock()
        event.data.object = {
            'id': 'in_123',
            'number': 'INV-123',  # Added number
            'subscription': 'sub_123',
            'amount_paid': 1000,
            'currency': 'usd',
            'hosted_invoice_url': 'url'
        }
        
        mock_sub = MagicMock(user_id='user_123', plan_id='plan_123')
        mock_sync.return_value = mock_sub
        
        # Mock database queries
        mock_user = MagicMock(email='test@example.com')
        mock_plan = MagicMock(name='Pro')
        mock_session.execute.side_effect = [
            MagicMock(scalar_one=lambda: mock_user),
            MagicMock(scalar_one=lambda: mock_plan)
        ]
        
        # Act
        await handle_payment_succeeded(event, mock_session, mock_background_tasks)
        
        # Assert
        mock_sync.assert_called_once()
        mock_background_tasks.add_task.assert_called()
    
    @patch('Backend.api.billing.webhook_handlers.sync_subscription_from_stripe')
    async def test_handle_payment_failed(self, mock_sync, mock_session, mock_background_tasks):
        """Test handle_payment_failed."""
        # Arrange
        event = MagicMock()
        event.data.object = {
            'id': 'in_123',
            'number': 'INV-123',  # Added number
            'subscription': 'sub_123',
            'amount_due': 1000,
            'currency': 'usd',
            'hosted_invoice_url': 'url',
            'attempt_count': 1
        }
        
        # Mock subscription query
        mock_sub = MagicMock(user_id='user_123', plan_id='plan_123')
        mock_sync.return_value = mock_sub
        
        # Mock user and plan queries
        mock_user = MagicMock(email='test@example.com')
        mock_plan = MagicMock(name='Pro')
        mock_session.execute.side_effect = [
            MagicMock(scalar_one=lambda: mock_user),
            MagicMock(scalar_one=lambda: mock_plan)
        ]
        
        # Act
        await handle_payment_failed(event, mock_session, mock_background_tasks)
        
        # Assert
        mock_background_tasks.add_task.assert_called()


class TestTrialHandler:
    """Tests for trial webhook handler."""
    
    @patch('Backend.api.billing.webhook_handlers.sync_subscription_from_stripe')
    async def test_handle_trial_will_end(self, mock_sync, mock_session, mock_background_tasks):
        """Test handle_trial_will_end."""
        # Arrange
        event = MagicMock()
        event.data.object = {'id': 'sub_123'}
        
        mock_sub = MagicMock(user_id='user_123', plan_id='plan_123')
        mock_sync.return_value = mock_sub
        
        # Mock database queries
        mock_user = MagicMock(email='test@example.com')
        mock_plan = MagicMock(name='Pro', amount=1000, currency='usd')
        mock_session.execute.side_effect = [
            MagicMock(scalar_one=lambda: mock_user),
            MagicMock(scalar_one=lambda: mock_plan)
        ]
        
        # Act
        await handle_trial_will_end(event, mock_session, mock_background_tasks)
        
        # Assert
        mock_background_tasks.add_task.assert_called()
