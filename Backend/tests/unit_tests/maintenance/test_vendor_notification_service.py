"""
Unit tests for vendor notification service.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import date

from Backend.api.maintenance.vendor_notification_service import VendorNotificationService
from Backend.models.maintenance import MaintenanceRequest
from Backend.models.vendor import Vendor
from Backend.models.user import User
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.enums import MaintenancePriority, MaintenanceStatus


# =============================================================================
# Vendor Assignment Notification Tests
# =============================================================================
# Note: Private _load_* methods are tested indirectly through public methods

@pytest.mark.asyncio
async def test_notify_vendor_of_assignment_success():
    """Test successful vendor assignment notification."""
    mock_session = AsyncMock()
    
    # Create mock request
    mock_request = MagicMock()
    mock_request.id = 1
    mock_request.vendor_id = 1
    mock_request.user_id = "user123"
    mock_request.property_id = 1
    mock_request.unit_id = 1
    mock_request.tenant_id = 1
    mock_request.issue_title = "Leaking Faucet"
    mock_request.description = "Kitchen faucet leaking"
    mock_request.priority = MaintenancePriority.HIGH
    mock_request.estimated_cost = Decimal("250.00")
    mock_request.scheduled_date = date(2024, 12, 15)
    mock_request.photos = ["https://example.com/photo.jpg"]
    
    # Create mocks for loaded entities
    mock_vendor = MagicMock()
    mock_vendor.company_name = "Test Plumbing"
    mock_vendor.contact_person = "John"
    mock_vendor.email = "vendor@example.com"
    
    mock_user = MagicMock()
    mock_user.first_name = "Jane"
    mock_user.last_name = "Landlord"
    mock_user.email = "landlord@example.com"
    mock_user.phone = "+1234567890"
    
    mock_property = MagicMock()
    mock_property.address = "123 Main St"
    
    mock_unit = MagicMock()
    mock_unit.name = "5A"
    
    mock_tenant = MagicMock()
    mock_tenant.first_name = "Bob"
    mock_tenant.last_name = "Tenant"
    mock_tenant.phone = "+0987654321"
    
    with patch.object(VendorNotificationService, '_load_vendor', return_value=mock_vendor), \
         patch.object(VendorNotificationService, '_load_user', return_value=mock_user), \
         patch.object(VendorNotificationService, '_load_property', return_value=mock_property), \
         patch.object(VendorNotificationService, '_load_unit', return_value=mock_unit), \
         patch.object(VendorNotificationService, '_load_tenant', return_value=mock_tenant), \
         patch('Backend.api.maintenance.vendor_notification_service.SendGridService.send_raw_email', new=AsyncMock()) as mock_send:
        
        await VendorNotificationService.notify_vendor_of_assignment(mock_request, mock_session)
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[1]
        assert call_args['to_email'] == "vendor@example.com"
        assert "Test Plumbing" in call_args['to_name'] or "John" in call_args['to_name']
        assert "123 Main St" in call_args['subject']  # Subject includes property address


@pytest.mark.asyncio
async def test_notify_vendor_of_assignment_vendor_not_found():
    """Test vendor assignment notification when vendor not found."""
    mock_session = AsyncMock()
    mock_request = MagicMock()
    mock_request.vendor_id = 999
    
    with patch.object(VendorNotificationService, '_load_vendor', return_value=None):
        # Should not crash, just log and return
        await VendorNotificationService.notify_vendor_of_assignment(mock_request, mock_session)


@pytest.mark.asyncio
async def test_notify_vendor_of_assignment_no_vendor_email():
    """Test vendor assignment notification when vendor has no email."""
    mock_session = AsyncMock()
    mock_request = MagicMock()
    mock_request.vendor_id = 1
    mock_request.user_id = "user123"
    mock_request.property_id = 1
    
    mock_vendor = MagicMock()
    mock_vendor.email = None
    
    with patch.object(VendorNotificationService, '_load_vendor', return_value=mock_vendor):
        # Should not crash
        await VendorNotificationService.notify_vendor_of_assignment(mock_request, mock_session)


@pytest.mark.asyncio
async def test_notify_vendor_of_assignment_minimal_data():
    """Test vendor notification with minimal required data."""
    mock_session = AsyncMock()
    
    mock_request = MagicMock()
    mock_request.id = 1
    mock_request.vendor_id = 1
    mock_request.user_id = "user123"
    mock_request.property_id = 1
    mock_request.unit_id = None
    mock_request.tenant_id = None
    mock_request.issue_title = "Issue"
    mock_request.description = None
    mock_request.priority = MaintenancePriority.MEDIUM
    mock_request.estimated_cost = None
    mock_request.scheduled_date = None
    mock_request.photos = None
    
    mock_vendor = MagicMock()
    mock_vendor.contact_person = "Vendor"
    mock_vendor.email = "vendor@example.com"
    
    mock_user = MagicMock()
    mock_user.first_name = "User"
    mock_user.last_name = "Name"
    mock_user.email = "user@example.com"
    mock_user.phone = None
    
    mock_property = MagicMock()
    mock_property.address = "Address"
    
    with patch.object(VendorNotificationService, '_load_vendor', return_value=mock_vendor), \
         patch.object(VendorNotificationService, '_load_user', return_value=mock_user), \
         patch.object(VendorNotificationService, '_load_property', return_value=mock_property), \
         patch.object(VendorNotificationService, '_load_unit', return_value=None), \
         patch.object(VendorNotificationService, '_load_tenant', return_value=None), \
         patch('Backend.api.maintenance.vendor_notification_service.SendGridService.send_raw_email', new=AsyncMock()) as mock_send:
        
        await VendorNotificationService.notify_vendor_of_assignment(mock_request, mock_session)
        
        mock_send.assert_called_once()


# =============================================================================
# Landlord Confirmation Notification Tests
# =============================================================================

@pytest.mark.asyncio
async def test_notify_landlord_of_assignment_success():
    """Test successful landlord confirmation notification."""
    mock_session = AsyncMock()
    
    mock_request = MagicMock()
    mock_request.id = 1
    mock_request.vendor_id = 1
    mock_request.user_id = "user123"
    mock_request.property_id = 1
    mock_request.unit_id = 1
    mock_request.tenant_id = 1
    mock_request.issue_title = "Repair"
    mock_request.description = "Needs fixing"
    mock_request.priority = MaintenancePriority.HIGH
    mock_request.estimated_cost = Decimal("500.00")
    mock_request.scheduled_date = date(2024, 12, 20)
    
    mock_vendor = MagicMock()
    mock_vendor.company_name = "Vendor Co"
    mock_vendor.email = "vendor@example.com"
    mock_vendor.phone = "+1111111111"
    
    mock_user = MagicMock()
    mock_user.first_name = "Jane"
    mock_user.last_name = "Landlord"
    mock_user.email = "landlord@example.com"
    
    mock_property = MagicMock()
    mock_property.address = "123 Main St"
    
    mock_unit = MagicMock()
    mock_unit.name = "1A"
    
    mock_tenant = MagicMock()
    mock_tenant.first_name = "Bob"
    mock_tenant.last_name = "Tenant"
    
    with patch.object(VendorNotificationService, '_load_vendor', return_value=mock_vendor), \
         patch.object(VendorNotificationService, '_load_user', return_value=mock_user), \
         patch.object(VendorNotificationService, '_load_property', return_value=mock_property), \
         patch.object(VendorNotificationService, '_load_unit', return_value=mock_unit), \
         patch.object(VendorNotificationService, '_load_tenant', return_value=mock_tenant), \
         patch('Backend.api.maintenance.vendor_notification_service.SendGridService.send_raw_email', new=AsyncMock()) as mock_send:
        
        await VendorNotificationService.notify_landlord_of_assignment(mock_request, mock_session)
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[1]
        assert call_args['to_email'] == "landlord@example.com"


@pytest.mark.asyncio
async def test_notify_landlord_of_assignment_no_user_email():
    """Test landlord notification when user has no email."""
    mock_session = AsyncMock()
    mock_request = MagicMock()
    mock_request.user_id = "user123"
    
    mock_user = MagicMock()
    mock_user.email = None
    
    with patch.object(VendorNotificationService, '_load_user', return_value=mock_user):
        # Should not crash
        await VendorNotificationService.notify_landlord_of_assignment(mock_request, mock_session)


# =============================================================================
# Tenant Status Change Notification Tests
# =============================================================================

@pytest.mark.asyncio
async def test_notify_tenant_of_status_change_success():
    """Test successful tenant status change notification."""
    mock_session = AsyncMock()
    
    mock_request = MagicMock()
    mock_request.id = 1
    mock_request.property_id = 1
    mock_request.unit_id = 1
    mock_request.tenant_id = 1
    mock_request.vendor_id = 1
    mock_request.issue_title = "Repair"
    mock_request.status = MaintenanceStatus.IN_PROGRESS
    
    mock_tenant = MagicMock()
    mock_tenant.first_name = "Bob"
    mock_tenant.last_name = "Tenant"
    mock_tenant.email = "tenant@example.com"
    
    mock_property = MagicMock()
    mock_property.address = "123 Main St"
    
    mock_unit = MagicMock()
    mock_unit.name = "5A"
    
    mock_vendor = MagicMock()
    mock_vendor.company_name = "Vendor Co"
    
    with patch.object(VendorNotificationService, '_load_tenant', return_value=mock_tenant), \
         patch.object(VendorNotificationService, '_load_property', return_value=mock_property), \
         patch.object(VendorNotificationService, '_load_unit', return_value=mock_unit), \
         patch.object(VendorNotificationService, '_load_vendor', return_value=mock_vendor), \
         patch('Backend.api.maintenance.vendor_notification_service.SendGridService.send_raw_email', new=AsyncMock()) as mock_send:
        
        await VendorNotificationService.notify_tenant_of_status_change(
            mock_request,
            MaintenanceStatus.PENDING,
            mock_request.status,
            mock_session
        )
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[1]
        assert call_args['to_email'] == "tenant@example.com"


@pytest.mark.asyncio
async def test_notify_tenant_of_status_change_tenant_not_found():
    """Test tenant notification when tenant not found."""
    mock_session = AsyncMock()
    mock_request = MagicMock()
    mock_request.tenant_id = 999
    
    with patch.object(VendorNotificationService, '_load_tenant', return_value=None):
        # Should not crash
        await VendorNotificationService.notify_tenant_of_status_change(
            mock_request,
            MaintenanceStatus.PENDING,
            mock_request.status,
            mock_session
        )


@pytest.mark.asyncio
async def test_notify_tenant_of_status_change_no_tenant_email():
    """Test tenant notification when tenant has no email."""
    mock_session = AsyncMock()
    mock_request = MagicMock()
    mock_request.tenant_id = 1
    mock_request.property_id = 1
    
    mock_tenant = MagicMock()
    mock_tenant.first_name = "Bob"
    mock_tenant.email = None
    
    with patch.object(VendorNotificationService, '_load_tenant', return_value=mock_tenant):
        # Should not crash
        await VendorNotificationService.notify_tenant_of_status_change(
            mock_request,
            MaintenanceStatus.PENDING,
            mock_request.status,
            mock_session
        )


@pytest.mark.asyncio
async def test_notify_tenant_status_change_to_completed():
    """Test tenant notification when status changes to completed."""
    mock_session = AsyncMock()
    
    mock_request = MagicMock()
    mock_request.id = 1
    mock_request.property_id = 1
    mock_request.unit_id = None
    mock_request.tenant_id = 1
    mock_request.vendor_id = None
    mock_request.issue_title = "Fixed"
    mock_request.status = MaintenanceStatus.COMPLETED
    
    mock_tenant = MagicMock()
    mock_tenant.first_name = "Tenant"
    mock_tenant.last_name = "Name"
    mock_tenant.email = "tenant@example.com"
    
    mock_property = MagicMock()
    mock_property.address = "Address"
    
    with patch.object(VendorNotificationService, '_load_tenant', return_value=mock_tenant), \
         patch.object(VendorNotificationService, '_load_property', return_value=mock_property), \
         patch.object(VendorNotificationService, '_load_unit', return_value=None), \
         patch.object(VendorNotificationService, '_load_vendor', return_value=None), \
         patch('Backend.api.maintenance.vendor_notification_service.SendGridService.send_raw_email', new=AsyncMock()) as mock_send:
        
        await VendorNotificationService.notify_tenant_of_status_change(
            mock_request,
            MaintenanceStatus.IN_PROGRESS,
            MaintenanceStatus.COMPLETED,
            mock_session
        )
        
        mock_send.assert_called_once()


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
async def test_notify_vendor_email_send_failure():
    """Test vendor notification handles email send failures gracefully."""
    mock_session = AsyncMock()
    
    mock_request = MagicMock()
    mock_request.vendor_id = 1
    mock_request.user_id = "user123"
    mock_request.property_id = 1
    mock_request.issue_title = "Test"
    mock_request.priority = MaintenancePriority.MEDIUM
    
    mock_vendor = MagicMock()
    mock_vendor.email = "vendor@example.com"
    mock_vendor.contact_person = "Vendor"
    
    mock_user = MagicMock()
    mock_user.first_name = "User"
    mock_user.last_name = "Name"
    mock_user.email = "user@example.com"
    
    mock_property = MagicMock()
    mock_property.address = "Address"
    
    with patch.object(VendorNotificationService, '_load_vendor', return_value=mock_vendor), \
         patch.object(VendorNotificationService, '_load_user', return_value=mock_user), \
         patch.object(VendorNotificationService, '_load_property', return_value=mock_property), \
         patch.object(VendorNotificationService, '_load_unit', return_value=None), \
         patch.object(VendorNotificationService, '_load_tenant', return_value=None), \
         patch('Backend.api.maintenance.vendor_notification_service.SendGridService.send_raw_email', new=AsyncMock(side_effect=Exception("Email failed"))):
        
        # Should not raise exception, just log error
        await VendorNotificationService.notify_vendor_of_assignment(mock_request, mock_session)

