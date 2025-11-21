"""
Unit tests for billing router endpoints.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException

from Backend.api.billing.router import (
    get_subscription_plans,
    get_subscription_status,
    create_checkout_session,
    create_customer_portal_session,
    cancel_subscription,
    resume_subscription
)
from Backend.api.billing.schemas import CreateCheckoutSessionRequest, CreateCustomerPortalRequest
from Backend.models.user import User
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


class TestGetSubscriptionPlans:
    """Tests for get_subscription_plans endpoint."""
    
    @patch('Backend.api.billing.router.BillingService.get_subscription_plans')
    async def test_get_plans_success(self, mock_get_plans, mock_session):
        """Test getting subscription plans."""
        # Arrange
        mock_get_plans.return_value = []
        
        # Act
        result = await get_subscription_plans(mock_session)
        
        # Assert
        assert result == []
        mock_get_plans.assert_called_once()


class TestGetSubscriptionStatus:
    """Tests for get_subscription_status endpoint."""
    
    @patch('Backend.api.billing.router.BillingService.get_subscription_status')
    async def test_get_status_success(self, mock_get_status, mock_user, mock_session):
        """Test getting subscription status."""
        # Arrange
        mock_response = MagicMock()
        mock_get_status.return_value = mock_response
        
        # Act
        result = await get_subscription_status(mock_user, mock_session)
        
        # Assert
        assert result == mock_response
        mock_get_status.assert_called_once()


class TestCreateCheckoutSession:
    """Tests for create_checkout_session endpoint."""
    
    @patch('Backend.api.billing.router.BillingService.create_checkout_session')
    async def test_create_checkout_success(
        self, mock_create_checkout, mock_user, mock_session
    ):
        """Test creating checkout session."""
        # Arrange
        request = CreateCheckoutSessionRequest(
            success_url="https://app.brikli.com/success",
            cancel_url="https://app.brikli.com/cancel"
        )
        mock_response = MagicMock()
        mock_response.checkout_url = "https://checkout.stripe.com/test"
        mock_create_checkout.return_value = mock_response
        
        # Act
        result = await create_checkout_session(request, mock_user, mock_session)
        
        # Assert
        assert result.checkout_url == "https://checkout.stripe.com/test"
        mock_create_checkout.assert_called_once()
    
    @patch('Backend.api.billing.router.BillingService.create_checkout_session')
    async def test_create_checkout_value_error(
        self, mock_create_checkout, mock_user, mock_session
    ):
        """Test checkout session creation with value error."""
        # Arrange
        request = CreateCheckoutSessionRequest()
        mock_create_checkout.side_effect = ValueError("Invalid request")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_checkout_session(request, mock_user, mock_session)
        
        assert exc_info.value.status_code == 400
    
    @patch('Backend.api.billing.router.BillingService.create_checkout_session')
    async def test_create_checkout_general_error(
        self, mock_create_checkout, mock_user, mock_session
    ):
        """Test checkout session creation with general error."""
        # Arrange
        request = CreateCheckoutSessionRequest()
        mock_create_checkout.side_effect = Exception("Unexpected error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_checkout_session(request, mock_user, mock_session)
        
        assert exc_info.value.status_code == 500


class TestCreateCustomerPortalSession:
    """Tests for create_customer_portal_session endpoint."""
    
    @patch('Backend.api.billing.router.BillingService.create_customer_portal_session')
    async def test_create_portal_success(
        self, mock_create_portal, mock_user, mock_session
    ):
        """Test creating customer portal session."""
        # Arrange
        request = CreateCustomerPortalRequest(
            return_url="https://app.brikli.com/settings"
        )
        mock_response = MagicMock()
        mock_response.portal_url = "https://billing.stripe.com/test"
        mock_create_portal.return_value = mock_response
        
        # Act
        result = await create_customer_portal_session(request, mock_user, mock_session)
        
        # Assert
        assert result.portal_url == "https://billing.stripe.com/test"
        mock_create_portal.assert_called_once()
    
    @patch('Backend.api.billing.router.BillingService.create_customer_portal_session')
    async def test_create_portal_error(
        self, mock_create_portal, mock_user, mock_session
    ):
        """Test portal session creation with error."""
        # Arrange
        request = CreateCustomerPortalRequest()
        mock_create_portal.side_effect = Exception("Portal error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_customer_portal_session(request, mock_user, mock_session)
        
        assert exc_info.value.status_code == 500


class TestCancelSubscription:
    """Tests for cancel_subscription endpoint."""
    
    @patch('Backend.api.billing.router.BillingService.cancel_subscription')
    async def test_cancel_subscription_success(
        self, mock_cancel, mock_user, mock_session
    ):
        """Test canceling subscription."""
        # Arrange
        mock_response = MagicMock()
        mock_cancel.return_value = mock_response
        
        # Act
        result = await cancel_subscription(mock_user, mock_session)
        
        # Assert
        assert result == mock_response
        mock_cancel.assert_called_once()
    
    @patch('Backend.api.billing.router.BillingService.cancel_subscription')
    async def test_cancel_subscription_no_subscription(
        self, mock_cancel, mock_user, mock_session
    ):
        """Test canceling when no subscription exists."""
        # Arrange
        mock_cancel.side_effect = ValueError("No subscription")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await cancel_subscription(mock_user, mock_session)
        
        assert exc_info.value.status_code == 400


class TestResumeSubscription:
    """Tests for resume_subscription endpoint."""
    
    @patch('Backend.api.billing.router.BillingService.resume_subscription')
    async def test_resume_subscription_success(
        self, mock_resume, mock_user, mock_session
    ):
        """Test resuming subscription."""
        # Arrange
        mock_response = MagicMock()
        mock_resume.return_value = mock_response
        
        # Act
        result = await resume_subscription(mock_user, mock_session)
        
        # Assert
        assert result == mock_response
        mock_resume.assert_called_once()
    
    @patch('Backend.api.billing.router.BillingService.resume_subscription')
    async def test_resume_subscription_error(
        self, mock_resume, mock_user, mock_session
    ):
        """Test resuming subscription with error."""
        # Arrange
        mock_resume.side_effect = ValueError("Cannot resume")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await resume_subscription(mock_user, mock_session)
        
        assert exc_info.value.status_code == 400

