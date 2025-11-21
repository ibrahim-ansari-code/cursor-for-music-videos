"""
Unit tests for billing helpers.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from Backend.api.billing.helpers import (
    get_or_create_stripe_customer,
    get_platform_price,
    get_user_subscription,
    is_subscription_active,
    calculate_days_left_in_trial
)
from Backend.models.user import User
from Backend.models.billing import SubscriptionPlan, UserSubscription
from Backend.models.enums import UserType


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create mock user without Stripe customer."""
    return User(
        id=uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        user_type=UserType.LANDLORD,
        stripe_customer_id=None,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_user_with_customer():
    """Create mock user with existing Stripe customer."""
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
def mock_subscription_plan():
    """Create mock subscription plan."""
    return SubscriptionPlan(
        id=uuid4(),
        name="Brikli Premium",
        stripe_product_id="prod_test123",
        stripe_price_id="price_test456",
        amount=4900,  # $49.00
        currency="CAD",
        interval="month",
        is_active=True,
        features=["Unlimited properties", "Priority support"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


class TestGetOrCreateStripeCustomer:
    """Tests for get_or_create_stripe_customer."""
    
    async def test_returns_existing_customer_id(self, mock_session, mock_user_with_customer):
        """Test returns existing Stripe customer ID."""
        # Act
        customer_id = await get_or_create_stripe_customer(mock_user_with_customer, mock_session)
        
        # Assert
        assert customer_id == "cus_test123"
        mock_session.add.assert_not_called()  # Should not modify user
    
    @patch('Backend.api.billing.helpers.get_stripe_client')
    async def test_creates_new_customer(self, mock_get_stripe_client, mock_session, mock_user):
        """Test creates new Stripe customer."""
        # Arrange
        mock_stripe = MagicMock()
        mock_customer = MagicMock()
        mock_customer.id = "cus_new123"
        mock_stripe.customers.create = AsyncMock(return_value=mock_customer)
        mock_get_stripe_client.return_value = mock_stripe
        
        # Act
        customer_id = await get_or_create_stripe_customer(mock_user, mock_session)
        
        # Assert
        assert customer_id == "cus_new123"
        assert mock_user.stripe_customer_id == "cus_new123"
        mock_session.add.assert_called_once_with(mock_user)
        mock_session.commit.assert_called_once()


class TestGetPlatformPrice:
    """Tests for get_platform_price."""
    
    async def test_returns_active_plan(self, mock_session, mock_subscription_plan):
        """Test returns active subscription plan."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription_plan
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act
        plan = await get_platform_price(mock_session)
        
        # Assert
        assert plan == mock_subscription_plan
        assert plan.name == "Brikli Premium"
    
    async def test_raises_error_if_no_plan(self, mock_session):
        """Test raises ValueError if no plan configured."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await get_platform_price(mock_session)
        
        assert "Platform subscription plan not configured" in str(exc_info.value)


class TestGetUserSubscription:
    """Tests for get_user_subscription."""
    
    async def test_returns_user_subscription(self, mock_session):
        """Test retrieves user subscription."""
        # Arrange
        user_id = uuid4()
        subscription = UserSubscription(
            id=uuid4(),
            user_id=user_id,
            stripe_subscription_id="sub_test123",
            status="active",
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = subscription
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act
        result = await get_user_subscription(user_id, mock_session)
        
        # Assert
        assert result == subscription
        assert result.user_id == user_id
    
    async def test_returns_none_if_no_subscription(self, mock_session):
        """Test returns None if user has no subscription."""
        # Arrange
        user_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Act
        result = await get_user_subscription(user_id, mock_session)
        
        # Assert
        assert result is None


class TestIsSubscriptionActive:
    """Tests for is_subscription_active."""
    
    def test_active_status_returns_true(self):
        """Test subscription with active status."""
        # Arrange
        subscription = UserSubscription(
            id=uuid4(),
            user_id=uuid4(),
            stripe_subscription_id="sub_test123",
            status="active",
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Act
        result = is_subscription_active(subscription)
        
        # Assert
        assert result is True
    
    def test_trialing_status_returns_true(self):
        """Test subscription with trialing status."""
        # Arrange
        subscription = UserSubscription(
            id=uuid4(),
            user_id=uuid4(),
            stripe_subscription_id="sub_test123",
            status="trialing",
            current_period_end=datetime.now(timezone.utc) + timedelta(days=7),
            trial_end=datetime.now(timezone.utc) + timedelta(days=7),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Act
        result = is_subscription_active(subscription)
        
        # Assert
        assert result is True
    
    def test_canceled_status_returns_false(self):
        """Test subscription with canceled status."""
        # Arrange
        subscription = UserSubscription(
            id=uuid4(),
            user_id=uuid4(),
            stripe_subscription_id="sub_test123",
            status="canceled",
            current_period_end=datetime.now(timezone.utc) - timedelta(days=1),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Act
        result = is_subscription_active(subscription)
        
        # Assert
        assert result is False
    
    def test_none_subscription_returns_false(self):
        """Test None subscription."""
        # Act
        result = is_subscription_active(None)
        
        # Assert
        assert result is False


class TestCalculateDaysLeftInTrial:
    """Tests for calculate_days_left_in_trial."""
    
    def test_calculates_days_left(self):
        """Test calculating days left in trial."""
        # Arrange
        trial_end = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Act
        days_left = calculate_days_left_in_trial(trial_end)
        
        # Assert
        # Allow for timing/rounding differences (6 or 7 days is acceptable)
        assert days_left in [6, 7]
    
    def test_returns_zero_for_expired_trial(self):
        """Test returns 0 for expired trial."""
        # Arrange
        trial_end = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Act
        days_left = calculate_days_left_in_trial(trial_end)
        
        # Assert
        assert days_left == 0
    
    def test_returns_none_for_no_trial(self):
        """Test returns None when no trial end date."""
        # Act
        days_left = calculate_days_left_in_trial(None)
        
        # Assert
        assert days_left is None
