"""
Unit tests for the tenant send-reminder endpoint using hybrid API testing pattern.
"""
from datetime import datetime, timezone
import pytest
from fastapi import status, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.tenants.schemas import TenantReminderResponse
from Backend.models.tenant import TenantStatus, Tenant
from Backend.models.enums import TenantType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()

# Create a custom TestClient that sets the proper host header
class TestClientWithHost(TestClient):
    def request(self, method: str, url, **kwargs):
        # Always add localhost to headers if not present
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)

def create_test_user(user_id=None, email="test@example.com", user_type="LANDLORD", is_admin=False):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=is_admin,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )

# =============================================================================
# SEND REMINDER TESTS - POST /api/tenants/{tenant_id}/send-reminder
# =============================================================================

def test_send_tenant_reminder_success():
    """Test successful tenant reminder email sending."""
    # Arrange
    tenant_id = 42
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    reminder_data = {
        "event_type": "rent",
        "event_title": "Rent Due Soon",
        "event_subtitle": "Your rent payment is due",
        "event_date": None,
        "event_amount": 1500.00,
        "days_remaining": 3
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:
        
        mock_check_permission.return_value = mock_tenant
        mock_send_email.return_value = True
        
        # Mock session for property/unit queries (return None for simplicity)
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "Reminder email sent successfully" in data["message"]
        assert mock_send_email.called
        
        # Verify email service was called with correct parameters
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs['tenant_email'] == "john.doe@example.com"
        assert call_kwargs['tenant_name'] == "John Doe"
        assert call_kwargs['event_type'] == "rent"
        assert call_kwargs['event_title'] == "Rent Due Soon"
        assert call_kwargs['event_amount'] == 1500.00
        assert call_kwargs['days_remaining'] == 3


def test_send_tenant_reminder_lease_expiry():
    """Test sending reminder for lease expiry event."""
    # Arrange
    tenant_id = 43
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@example.com",
        phone="555-111-1111",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=100,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    reminder_data = {
        "event_type": "lease_expiry",
        "event_title": "Lease Expiring Soon",
        "event_subtitle": "Your lease will expire soon",
        "event_date": "2024-12-31T00:00:00Z",
        "event_amount": None,
        "days_remaining": 30
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:
        
        mock_check_permission.return_value = mock_tenant
        mock_send_email.return_value = True
        
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs['event_type'] == "lease_expiry"
        assert call_kwargs['days_remaining'] == 30


def test_send_tenant_reminder_permission_denied():
    """Test sending reminder when user doesn't have permission."""
    # Arrange
    tenant_id = 44
    landlord_id = uuid4()
    other_landlord_id = uuid4()
    mock_user = create_test_user(user_id=other_landlord_id)  # Different landlord
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        reminder_data = {
            "event_type": "rent",
            "event_title": "Test",
            "event_subtitle": "Test"
        }
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_send_tenant_reminder_tenant_not_found():
    """Test sending reminder when tenant doesn't exist."""
    # Arrange
    tenant_id = 999
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        reminder_data = {
            "event_type": "rent",
            "event_title": "Test",
            "event_subtitle": "Test"
        }
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_send_tenant_reminder_no_email():
    """Test sending reminder when tenant has no email address."""
    # Arrange
    tenant_id = 45
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="No",
        last_name="Email",
        email=None,  # No email
        phone="555-222-2222",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    reminder_data = {
        "event_type": "rent",
        "event_title": "Rent Due",
        "event_subtitle": "Your rent is due"
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "email" in data["detail"].lower()


def test_send_tenant_reminder_invalid_email_format():
    """Test sending reminder when tenant has invalid email format."""
    # Arrange
    tenant_id = 50
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Invalid",
        last_name="Email",
        email="not-a-valid-email",  # Invalid email format
        phone="555-555-5555",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    reminder_data = {
        "event_type": "rent",
        "event_title": "Rent Due",
        "event_subtitle": "Your rent is due"
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
        mock_check_permission.return_value = mock_tenant
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "invalid email" in data["detail"].lower() or "email address format" in data["detail"].lower()
        assert "not-a-valid-email" in data["detail"]


def test_send_tenant_reminder_malformed_email():
    """Test sending reminder with various malformed email addresses."""
    # Arrange
    tenant_id = 51
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)
    
    invalid_emails = [
        "missing@domain",
        "@missinglocal.com",
        "missingdomain@",
        "spaces in@email.com",
        "no-at-sign.com",
        "missing@.com",
        "@.com"
    ]
    
    for invalid_email in invalid_emails:
        mock_tenant = Tenant(
            id=tenant_id,
            first_name="Test",
            last_name="Tenant",
            email=invalid_email,
            phone="555-555-5555",
            status=TenantStatus.ACTIVE,
            landlord_id=landlord_id,
            current_property_id=None,
            tenant_type=TenantType.INDIVIDUAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        reminder_data = {
            "event_type": "rent",
            "event_title": "Rent Due",
            "event_subtitle": "Your rent is due"
        }
        
        with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission:
            mock_check_permission.return_value = mock_tenant
            
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Should reject invalid email: {invalid_email}"
            data = response.json()
            assert "invalid email" in data["detail"].lower() or "email address format" in data["detail"].lower()


def test_send_tenant_reminder_email_failure():
    """Test sending reminder when email service fails."""
    # Arrange
    tenant_id = 46
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Test",
        last_name="Tenant",
        email="test@example.com",
        phone="555-333-3333",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    reminder_data = {
        "event_type": "rent",
        "event_title": "Rent Due",
        "event_subtitle": "Your rent is due"
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:
        
        mock_check_permission.return_value = mock_tenant
        mock_send_email.return_value = False  # Email service fails
        
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to send reminder email" in data["detail"]


def test_send_tenant_reminder_company_tenant():
    """Test sending reminder to company tenant."""
    # Arrange
    tenant_id = 47
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name=None,
        last_name=None,
        company_name="Test Company",
        contact_person="John Manager",
        email="company@example.com",
        phone="555-444-4444",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.COMPANY,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    reminder_data = {
        "event_type": "invoice",
        "event_title": "Invoice Due",
        "event_subtitle": "You have an outstanding invoice",
        "event_amount": 500.00
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:
        
        mock_check_permission.return_value = mock_tenant
        mock_send_email.return_value = True
        
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_send_email.call_args[1]
        # Company tenant should use company_name or contact_person
        assert call_kwargs['tenant_name'] in ["Test Company", "John Manager", "Tenant"]


def test_send_tenant_reminder_unknown_event_type():
    """Test sending reminder with unknown event type (should default to system_update)."""
    # Arrange
    tenant_id = 48
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)
    
    # Mock tenant for permission check
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Test",
        last_name="Tenant",
        email="test@example.com",
        phone="555-555-5555",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    reminder_data = {
        "event_type": "unknown_type",  # Unknown event type - email service handles gracefully
        "event_title": "Test",
        "event_subtitle": "Test"
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:
        
        mock_check_permission.return_value = mock_tenant
        mock_send_email.return_value = True  # Email service accepts any event_type
        
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        # Should succeed - email service handles unknown event types gracefully
        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs['event_type'] == "unknown_type"


def test_send_tenant_reminder_missing_required_fields():
    """Test sending reminder with missing required fields."""
    # Arrange
    tenant_id = 49
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id)
    
    reminder_data = {
        # Missing event_title and event_subtitle
        "event_type": "rent"
    }
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
    
    # Should fail validation
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# CUSTOM SUBJECT AND MESSAGE TESTS - Confirmation Modal Feature
# =============================================================================

def test_send_tenant_reminder_with_custom_subject():
    """Test sending reminder with custom subject line."""
    # Arrange
    tenant_id = 52
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    reminder_data = {
        "event_type": "rent",
        "event_title": "Rent Due Soon",
        "event_subtitle": "Your rent payment is due",
        "event_date": None,
        "event_amount": 1500.00,
        "days_remaining": 3,
        "custom_subject": "Urgent: Rent Payment Reminder"
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:
        
        mock_check_permission.return_value = mock_tenant
        mock_send_email.return_value = True
        
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify custom subject was passed to email service
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs['custom_subject'] == "Urgent: Rent Payment Reminder"
        assert call_kwargs['custom_message'] is None


def test_send_tenant_reminder_with_custom_message():
    """Test sending reminder with custom message body."""
    # Arrange
    tenant_id = 53
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@example.com",
        phone="555-111-1111",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    custom_message = "This is a personalized reminder message from your landlord."
    
    reminder_data = {
        "event_type": "rent",
        "event_title": "Rent Due Soon",
        "event_subtitle": "Your rent payment is due",
        "event_date": None,
        "event_amount": 1500.00,
        "days_remaining": 3,
        "custom_message": custom_message
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:
        
        mock_check_permission.return_value = mock_tenant
        mock_send_email.return_value = True
        
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify custom message was passed to email service
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs['custom_message'] == custom_message
        assert call_kwargs['custom_subject'] is None


def test_send_tenant_reminder_with_both_custom_fields():
    """Test sending reminder with both custom subject and message."""
    # Arrange
    tenant_id = 54
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Bob",
        last_name="Johnson",
        email="bob.johnson@example.com",
        phone="555-222-2222",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    custom_subject = "Important: Payment Due This Week"
    custom_message = "Please note that your rent payment is due in 3 days. We appreciate your timely payment."
    
    reminder_data = {
        "event_type": "rent",
        "event_title": "Rent Due Soon",
        "event_subtitle": "Your rent payment is due",
        "event_date": "2024-11-15T00:00:00Z",
        "event_amount": 1500.00,
        "days_remaining": 3,
        "custom_subject": custom_subject,
        "custom_message": custom_message
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:
        
        mock_check_permission.return_value = mock_tenant
        mock_send_email.return_value = True
        
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify both custom fields were passed to email service
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs['custom_subject'] == custom_subject
        assert call_kwargs['custom_message'] == custom_message


def test_send_tenant_reminder_with_null_custom_fields():
    """Test sending reminder with null custom fields (should use defaults)."""
    # Arrange
    tenant_id = 55
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Test",
        last_name="Tenant",
        email="test@example.com",
        phone="555-333-3333",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    reminder_data = {
        "event_type": "rent",
        "event_title": "Rent Due Soon",
        "event_subtitle": "Your rent payment is due",
        "event_date": None,
        "event_amount": 1500.00,
        "days_remaining": 3,
        "custom_subject": None,
        "custom_message": None
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:
        
        mock_check_permission.return_value = mock_tenant
        mock_send_email.return_value = True
        
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify null custom fields were passed (email service will use defaults)
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs['custom_subject'] is None
        assert call_kwargs['custom_message'] is None


def test_send_tenant_reminder_with_empty_string_custom_fields():
    """Test sending reminder with empty string custom fields (should be treated as null)."""
    # Arrange
    tenant_id = 56
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Test",
        last_name="Tenant",
        email="test@example.com",
        phone="555-444-4444",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    reminder_data = {
        "event_type": "rent",
        "event_title": "Rent Due Soon",
        "event_subtitle": "Your rent payment is due",
        "event_date": None,
        "event_amount": 1500.00,
        "days_remaining": 3,
        "custom_subject": "",
        "custom_message": ""
    }
    
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:
        
        mock_check_permission.return_value = mock_tenant
        mock_send_email.return_value = True
        
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session
        
        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
        
        # Assert - should succeed (empty strings are valid, email service will handle)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify empty strings were passed (email service will treat as None/use defaults)
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs['custom_subject'] == ""
        assert call_kwargs['custom_message'] == ""


def test_send_tenant_reminder_custom_fields_with_all_event_types():
    """Test custom fields work with all supported event types."""
    # Arrange
    tenant_id = 57
    landlord_id = uuid4()
    mock_user = create_test_user(user_id=landlord_id, email="landlord@example.com")
    
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Test",
        last_name="Tenant",
        email="test@example.com",
        phone="555-555-5555",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        tenant_type=TenantType.INDIVIDUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    event_types = ["rent", "lease_expiry", "invoice", "maintenance", "insurance"]
    
    for event_type in event_types:
        reminder_data = {
            "event_type": event_type,
            "event_title": f"{event_type.title()} Reminder",
            "event_subtitle": f"Your {event_type} is due",
            "event_date": None,
            "event_amount": 100.00 if event_type in ["rent", "invoice"] else None,
            "days_remaining": 5,
            "custom_subject": f"Custom Subject for {event_type}",
            "custom_message": f"Custom message for {event_type} reminder"
        }
        
        with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
             patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:
            
            mock_check_permission.return_value = mock_tenant
            mock_send_email.return_value = True
            
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
            
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session
            
            with TestClientWithHost(app) as client:
                response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)
            
            # Assert
            assert response.status_code == status.HTTP_200_OK, f"Failed for event_type: {event_type}"
            data = response.json()
            assert data["success"] is True
            
            # Verify custom fields were passed for each event type
            call_kwargs = mock_send_email.call_args[1]
            assert call_kwargs['custom_subject'] == f"Custom Subject for {event_type}"
            assert call_kwargs['custom_message'] == f"Custom message for {event_type} reminder"
            assert call_kwargs['event_type'] == event_type


# ========================================================================
# SECURITY TESTS
# ========================================================================

def test_send_reminder_xss_injection_attempt():
    """SECURITY TEST: Verify XSS injection attempts are properly escaped."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    tenant_id = 123

    mock_tenant = Tenant(
        id=tenant_id,
        email="tenant@example.com",
        first_name="John",
        last_name="Doe",
        tenant_type=TenantType.INDIVIDUAL,
        status=TenantStatus.ACTIVE,
        landlord_id=mock_user.id
    )

    # XSS payload attempts
    xss_payloads = [
        "<script>alert('xss')</script>",
        "<img src=x onerror='alert(1)'>",
        "<iframe src='javascript:alert(1)'></iframe>",
        "javascript:alert(document.cookie)",
        "<svg onload=alert('xss')>"
    ]

    for xss_payload in xss_payloads:
        reminder_data = {
            "event_type": "rent",
            "event_title": f"Rent Due {xss_payload}",
            "event_subtitle": f"Please pay your rent {xss_payload}",
            "custom_subject": f"Reminder {xss_payload}",
            "custom_message": f"Dear tenant, {xss_payload} please pay rent",
            "event_amount": 1200.00,
            "days_remaining": 5
        }

        with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
             patch("Backend.api.tenants.router.check_reminder_rate_limit", new_callable=AsyncMock) as mock_rate_limit, \
             patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:

            mock_check_permission.return_value = mock_tenant
            mock_rate_limit.return_value = True
            mock_send_email.return_value = True

            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_session

            with TestClientWithHost(app) as client:
                response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)

            # Assert - Should succeed but XSS should be escaped in email generation
            assert response.status_code == status.HTTP_200_OK
            assert mock_send_email.called

            # Verify the XSS payload was passed (escaping happens in email template generation)
            call_kwargs = mock_send_email.call_args[1]
            assert xss_payload in call_kwargs['event_title']


def test_send_reminder_invalid_event_type_rejected():
    """SECURITY TEST: Verify invalid event_type values are rejected."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    tenant_id = 123

    # Test cases that should fail validation
    invalid_event_types = [
        ("A" * 51, "too long (>50 chars)"),  # Exceeds max_length
        ("", "empty string"),  # Empty string
        (123, "not a string"),  # Not a string
        (None, "None"),  # None
    ]

    for invalid_type, description in invalid_event_types:
        reminder_data = {
            "event_type": invalid_type,
            "event_title": "Test",
            "event_subtitle": "Test subtitle"
        }

        mock_session = AsyncMock()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)

        # Assert - Should fail validation (422)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            f"Invalid event_type '{description}' should be rejected, got {response.status_code}"


def test_send_reminder_exceeds_max_length():
    """SECURITY TEST: Verify excessively long inputs are rejected."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    tenant_id = 123

    test_cases = [
        {
            "field": "event_title",
            "max_length": 200,
            "value": "A" * 201
        },
        {
            "field": "event_subtitle",
            "max_length": 500,
            "value": "B" * 501
        },
        {
            "field": "custom_subject",
            "max_length": 200,
            "value": "C" * 201
        },
        {
            "field": "custom_message",
            "max_length": 2000,
            "value": "D" * 2001
        }
    ]

    for test_case in test_cases:
        reminder_data = {
            "event_type": "rent",
            "event_title": "Valid Title",
            "event_subtitle": "Valid Subtitle",
            test_case["field"]: test_case["value"]
        }

        mock_session = AsyncMock()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)

        # Assert - Should fail validation (422)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            f"Field '{test_case['field']}' exceeding {test_case['max_length']} chars should be rejected"


def test_send_reminder_rate_limit_enforced():
    """SECURITY TEST: Verify rate limiting prevents email spam."""
    # Arrange
    mock_user = create_test_user(user_type=UserType.LANDLORD)
    tenant_id = 123

    mock_tenant = Tenant(
        id=tenant_id,
        email="tenant@example.com",
        first_name="John",
        last_name="Doe",
        tenant_type=TenantType.INDIVIDUAL,
        status=TenantStatus.ACTIVE,
        landlord_id=mock_user.id
    )

    reminder_data = {
        "event_type": "rent",
        "event_title": "Rent Due",
        "event_subtitle": "Please pay your rent",
        "event_amount": 1200.00,
        "days_remaining": 5
    }

    # Act - First request should succeed
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.check_reminder_rate_limit", new_callable=AsyncMock) as mock_rate_limit, \
         patch("Backend.api.tenants.router.EmailService.send_tenant_reminder_email", new_callable=AsyncMock) as mock_send_email:

        mock_check_permission.return_value = mock_tenant
        mock_rate_limit.return_value = True  # First request allowed
        mock_send_email.return_value = True

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)

        assert response.status_code == status.HTTP_200_OK

    # Act - Subsequent request should fail rate limit
    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
         patch("Backend.api.tenants.router.check_reminder_rate_limit", new_callable=AsyncMock) as mock_rate_limit:

        mock_check_permission.return_value = mock_tenant
        mock_rate_limit.return_value = False  # Rate limit exceeded

        mock_session = AsyncMock()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: mock_session

        with TestClientWithHost(app) as client:
            response = client.post(f"/api/tenants/{tenant_id}/send-reminder", json=reminder_data)

        # Assert - Should fail with 429 Too Many Requests
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "rate limit" in response.json()["detail"].lower()
