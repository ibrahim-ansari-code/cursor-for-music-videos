"""
Unit tests for subscription synchronization logic.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from Backend.api.billing.helpers import sync_subscription_from_stripe
from Backend.models.user import User
from Backend.models.billing import SubscriptionPlan, UserSubscription
from Backend.models.enums import UserType


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_user():
    """Create mock user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        user_type=UserType.LANDLORD,
        stripe_customer_id="cus_test123",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_plan():
    """Create mock subscription plan."""
    return SubscriptionPlan(
        id=uuid4(),
        name="Brikli Premium",
        stripe_product_id="prod_test123",
        stripe_price_id="price_test456",
        amount=4900,
        currency="CAD",
        interval="month",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_stripe_subscription():
    """Create mock Stripe subscription data."""
    return {
        'id': 'sub_test123',
        'customer': 'cus_test123',
        'status': 'active',
        'current_period_start': int(datetime.now(timezone.utc).timestamp()),
        'current_period_end': int(datetime.now(timezone.utc).timestamp()) + 2592000,
        'cancel_at_period_end': False,
        'items': {
            'data': [
                {
                    'price': {
                        'id': 'price_test456'
                    }
                }
            ]
        },
        'metadata': {},
        'trial_start': None,
        'trial_end': None,
        'canceled_at': None,
        'ended_at': None
    }


class TestSyncSubscriptionFromStripe:
    """Tests for sync_subscription_from_stripe."""
    
    @patch('Backend.api.billing.helpers.get_stripe_client')
    async def test_sync_creates_new_subscription(
        self, mock_get_client, mock_session, mock_user, mock_plan, mock_stripe_subscription
    ):
        """Test creating a new subscription from Stripe data."""
        # Arrange
        # Mock user query
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        
        # Mock plan query
        mock_plan_result = MagicMock()
        mock_plan_result.scalar_one_or_none.return_value = mock_plan
        
        # Mock existing subscription query (None for new)
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none.return_value = None
        
        mock_session.execute = AsyncMock(side_effect=[
            mock_user_result, 
            mock_plan_result, 
            mock_sub_result
        ])
        
        # Act
        result = await sync_subscription_from_stripe(
            "sub_test123", mock_session, stripe_sub_data=mock_stripe_subscription
        )
        
        # Assert
        assert result.stripe_subscription_id == "sub_test123"
        assert result.status == "active"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @patch('Backend.api.billing.helpers.get_stripe_client')
    async def test_sync_updates_existing_subscription(
        self, mock_get_client, mock_session, mock_user, mock_plan, mock_stripe_subscription
    ):
        """Test updating an existing subscription."""
        # Arrange
        existing_sub = UserSubscription(
            id=uuid4(),
            user_id=mock_user.id,
            plan_id=mock_plan.id,
            stripe_subscription_id="sub_test123",
            status="incomplete",
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Mock queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        
        mock_plan_result = MagicMock()
        mock_plan_result.scalar_one_or_none.return_value = mock_plan
        
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none.return_value = existing_sub
        
        mock_session.execute = AsyncMock(side_effect=[
            mock_user_result, 
            mock_plan_result, 
            mock_sub_result
        ])
        
        # Update status in Stripe data
        mock_stripe_subscription['status'] = 'active'
        
        # Act
        result = await sync_subscription_from_stripe(
            "sub_test123", mock_session, stripe_sub_data=mock_stripe_subscription
        )
        
        # Assert
        assert result.status == "active"
        assert result.id == existing_sub.id
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @patch('Backend.api.billing.helpers.get_stripe_client')
    async def test_sync_fetches_from_stripe_api(
        self, mock_get_client, mock_session, mock_user, mock_plan, mock_stripe_subscription
    ):
        """Test fetching data from Stripe API when not provided."""
        # Arrange
        mock_stripe_client = MagicMock()
        mock_stripe_client.subscriptions.retrieve = AsyncMock(return_value=mock_stripe_subscription)
        mock_get_client.return_value = mock_stripe_client
        
        # Mock queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        
        mock_plan_result = MagicMock()
        mock_plan_result.scalar_one_or_none.return_value = mock_plan
        
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none.return_value = None
        
        mock_session.execute = AsyncMock(side_effect=[
            mock_user_result, 
            mock_plan_result, 
            mock_sub_result
        ])
        
        # Act
        result = await sync_subscription_from_stripe(
            "sub_test123", mock_session
        )
        
        # Assert
        assert result.stripe_subscription_id == "sub_test123"
        mock_stripe_client.subscriptions.retrieve.assert_called_once_with("sub_test123")
    
    @patch('Backend.api.billing.helpers.get_stripe_client')
    async def test_sync_raises_error_if_user_not_found(
        self, mock_get_client, mock_session, mock_stripe_subscription
    ):
        """Test error when user not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await sync_subscription_from_stripe(
                "sub_test123", mock_session, stripe_sub_data=mock_stripe_subscription
            )
        
        assert "User not found" in str(exc_info.value)

