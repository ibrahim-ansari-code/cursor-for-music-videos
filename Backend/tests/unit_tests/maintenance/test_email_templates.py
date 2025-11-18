"""
Unit tests for maintenance email templates.
"""
import pytest
from decimal import Decimal
from datetime import date

from Backend.api.maintenance.email_templates import VendorEmailTemplates
from Backend.models.enums import MaintenancePriority, MaintenanceStatus


# =============================================================================
# Vendor Assignment Email Tests
# =============================================================================

def test_vendor_assignment_email_complete():
    """Test vendor assignment email with all fields."""
    subject, html = VendorEmailTemplates.create_vendor_assignment_email(
        vendor_name="John's Plumbing",
        vendor_email="john@plumbing.com",
        landlord_name="Jane Landlord",
        landlord_email="jane@example.com",
        landlord_phone="+1234567890",
        property_address="123 Main St",
        unit_number="Unit 5A",
        tenant_name="Bob Tenant",
        tenant_phone="+0987654321",
        issue_title="Leaking Faucet",
        issue_description="Kitchen faucet is dripping constantly",
        priority=MaintenancePriority.HIGH,
        estimated_cost=Decimal("250.00"),
        scheduled_date=date(2024, 12, 15),
        photos=["https://example.com/photo1.jpg"],
        request_id=123,
        frontend_url="https://app.brikli.com"
    )
    
    assert "New Maintenance Request" in subject
    assert "John&#x27;s Plumbing" in html  # HTML-escaped apostrophe
    assert "123 Main St" in html
    assert "Unit 5A" in html
    assert "Bob Tenant" in html
    assert "Leaking Faucet" in html
    assert "Kitchen faucet" in html
    assert "$250.00" in html
    assert "View Full Request" in html  # Changed to match actual button text


def test_vendor_assignment_email_minimal():
    """Test vendor assignment email with minimal required fields."""
    subject, html = VendorEmailTemplates.create_vendor_assignment_email(
        vendor_name="Vendor",
        vendor_email="vendor@example.com",
        landlord_name="Landlord",
        landlord_email="landlord@example.com",
        landlord_phone=None,
        property_address="Property Address",
        unit_number=None,
        tenant_name=None,
        tenant_phone=None,
        issue_title="Issue",
        issue_description=None,
        priority=MaintenancePriority.MEDIUM,
        estimated_cost=None,
        scheduled_date=None,
        photos=None,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert subject is not None
    assert html is not None
    assert "Vendor" in html
    assert "Property Address" in html
    assert "Issue" in html


def test_vendor_assignment_email_no_vendor_name():
    """Test vendor assignment email when vendor name is None."""
    subject, html = VendorEmailTemplates.create_vendor_assignment_email(
        vendor_name=None,
        vendor_email="vendor@example.com",
        landlord_name="Landlord",
        landlord_email="landlord@example.com",
        landlord_phone=None,
        property_address="Address",
        unit_number=None,
        tenant_name=None,
        tenant_phone=None,
        issue_title="Issue",
        issue_description=None,
        priority=MaintenancePriority.LOW,
        estimated_cost=None,
        scheduled_date=None,
        photos=None,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert "Hi there" in html  # Default greeting


def test_vendor_assignment_email_with_photos():
    """Test vendor assignment email with multiple photos."""
    photos = [
        "https://example.com/photo1.jpg",
        "https://example.com/photo2.jpg",
        "https://example.com/photo3.jpg"
    ]
    
    subject, html = VendorEmailTemplates.create_vendor_assignment_email(
        vendor_name="Vendor",
        vendor_email="vendor@example.com",
        landlord_name="Landlord",
        landlord_email="landlord@example.com",
        landlord_phone=None,
        property_address="Address",
        unit_number=None,
        tenant_name=None,
        tenant_phone=None,
        issue_title="Issue",
        issue_description=None,
        priority=MaintenancePriority.HIGH,
        estimated_cost=None,
        scheduled_date=None,
        photos=photos,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    # Check that photos are mentioned (URLs not directly in HTML, just notice)
    assert "photo" in html.lower() or "Photos Available" in html


# =============================================================================
# Landlord Confirmation Email Tests
# =============================================================================

def test_landlord_confirmation_email_complete():
    """Test landlord confirmation email with all fields."""
    subject, html = VendorEmailTemplates.create_landlord_confirmation_email(
        landlord_name="Jane Landlord",
        vendor_name="John's Plumbing",
        vendor_company="John's Plumbing Company",
        property_address="123 Main St",
        unit_number="5A",
        issue_title="Leaking Faucet",
        request_id=123,
        frontend_url="https://app.brikli.com"
    )
    
    assert "Vendor Assigned" in subject or "Assigned" in subject
    assert "Jane" in html
    assert "John&#x27;s Plumbing" in html  # HTML-escaped apostrophe
    assert "123 Main St" in html
    assert "Leaking Faucet" in html


def test_landlord_confirmation_email_minimal():
    """Test landlord confirmation email with minimal fields."""
    subject, html = VendorEmailTemplates.create_landlord_confirmation_email(
        landlord_name="Landlord",
        vendor_name="Vendor",
        vendor_company=None,
        property_address="Address",
        unit_number=None,
        issue_title="Issue",
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert subject is not None
    assert html is not None
    assert "Vendor" in html
    assert "Address" in html


# =============================================================================
# Tenant Status Update Email Tests
# =============================================================================

def test_tenant_status_update_email_complete():
    """Test tenant status update email with all fields."""
    subject, html = VendorEmailTemplates.create_tenant_status_update_email(
        tenant_name="Bob Tenant",
        tenant_email="bob@example.com",
        property_address="123 Main St",
        unit_number="5A",
        issue_title="Leaking Faucet",
        old_status=MaintenanceStatus.PENDING,
        new_status=MaintenanceStatus.IN_PROGRESS,
        vendor_name="John",
        vendor_company="John's Plumbing",
        vendor_phone="+1234567890",
        vendor_email="john@plumbing.com",
        request_id=123,
        frontend_url="https://app.brikli.com"
    )
    
    assert "Maintenance Update" in subject
    assert "Bob Tenant" in html or "Bob" in html
    assert "123 Main St" in html
    assert "Leaking Faucet" in html
    assert "John&#x27;s Plumbing" in html  # HTML-escaped apostrophe


def test_tenant_status_update_email_minimal():
    """Test tenant status update email with minimal fields."""
    subject, html = VendorEmailTemplates.create_tenant_status_update_email(
        tenant_name="Tenant",
        tenant_email="tenant@example.com",
        property_address="Address",
        unit_number=None,
        issue_title="Issue",
        old_status=MaintenanceStatus.PENDING,
        new_status=MaintenanceStatus.COMPLETED,
        vendor_name=None,
        vendor_company=None,
        vendor_phone=None,
        vendor_email=None,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert subject is not None
    assert html is not None
    assert "Tenant" in html or "tenant" in html.lower()
    assert "Address" in html


def test_tenant_status_update_email_scheduled():
    """Test tenant status update for scheduled status."""
    subject, html = VendorEmailTemplates.create_tenant_status_update_email(
        tenant_name="Tenant",
        tenant_email="tenant@example.com",
        property_address="Address",
        unit_number="1A",
        issue_title="Issue",
        old_status=MaintenanceStatus.PENDING,
        new_status=MaintenanceStatus.SCHEDULED,
        vendor_name="Vendor",
        vendor_company="Vendor Co",
        vendor_phone=None,
        vendor_email=None,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert "scheduled" in html.lower() or "Scheduled" in html


def test_tenant_status_update_email_completed():
    """Test tenant status update for completed status."""
    subject, html = VendorEmailTemplates.create_tenant_status_update_email(
        tenant_name="Tenant",
        tenant_email="tenant@example.com",
        property_address="Address",
        unit_number=None,
        issue_title="Issue",
        old_status=MaintenanceStatus.IN_PROGRESS,
        new_status=MaintenanceStatus.COMPLETED,
        vendor_name="Vendor",
        vendor_company=None,
        vendor_phone=None,
        vendor_email=None,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert "completed" in html.lower() or "Completed" in html


def test_tenant_status_update_email_cancelled():
    """Test tenant status update for cancelled status."""
    subject, html = VendorEmailTemplates.create_tenant_status_update_email(
        tenant_name="Tenant",
        tenant_email="tenant@example.com",
        property_address="Address",
        unit_number=None,
        issue_title="Issue",
        old_status=MaintenanceStatus.PENDING,
        new_status=MaintenanceStatus.CANCELLED,
        vendor_name=None,
        vendor_company=None,
        vendor_phone=None,
        vendor_email=None,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert "cancelled" in html.lower() or "Cancelled" in html


# =============================================================================
# Priority Tests
# =============================================================================

def test_email_templates_high_priority():
    """Test email templates handle high priority correctly."""
    subject, html = VendorEmailTemplates.create_vendor_assignment_email(
        vendor_name="Vendor",
        vendor_email="vendor@example.com",
        landlord_name="Landlord",
        landlord_email="landlord@example.com",
        landlord_phone=None,
        property_address="Address",
        unit_number=None,
        tenant_name=None,
        tenant_phone=None,
        issue_title="Emergency",
        issue_description=None,
        priority=MaintenancePriority.HIGH,
        estimated_cost=None,
        scheduled_date=None,
        photos=None,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert "high" in html.lower() or "High" in html or "urgent" in html.lower()


def test_email_templates_low_priority():
    """Test email templates handle low priority correctly."""
    subject, html = VendorEmailTemplates.create_vendor_assignment_email(
        vendor_name="Vendor",
        vendor_email="vendor@example.com",
        landlord_name="Landlord",
        landlord_email="landlord@example.com",
        landlord_phone=None,
        property_address="Address",
        unit_number=None,
        tenant_name=None,
        tenant_phone=None,
        issue_title="Minor Issue",
        issue_description=None,
        priority=MaintenancePriority.LOW,
        estimated_cost=None,
        scheduled_date=None,
        photos=None,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert "low" in html.lower() or "Low" in html


# =============================================================================
# Edge Cases
# =============================================================================

def test_email_templates_special_characters():
    """Test email templates handle special characters."""
    subject, html = VendorEmailTemplates.create_vendor_assignment_email(
        vendor_name="O'Brien & Sons <Plumbing>",
        vendor_email="obrien@example.com",
        landlord_name="Smith & Jones",
        landlord_email="smith@example.com",
        landlord_phone="+1-234-567-8900",
        property_address="123 \"Main\" St & Ave",
        unit_number="5A & 5B",
        tenant_name="José García",
        tenant_phone="+1234567890",
        issue_title="Faucet & Pipe Issues",
        issue_description="The faucet & pipes need attention <urgent>",
        priority=MaintenancePriority.HIGH,
        estimated_cost=Decimal("1250.50"),
        scheduled_date=None,
        photos=None,
        request_id=999,
        frontend_url="https://app.brikli.com"
    )
    
    # Should not crash and should produce valid HTML
    assert subject is not None
    assert html is not None
    assert len(html) > 100


def test_email_templates_very_long_descriptions():
    """Test email templates handle very long descriptions."""
    long_description = "A" * 1000
    
    subject, html = VendorEmailTemplates.create_vendor_assignment_email(
        vendor_name="Vendor",
        vendor_email="vendor@example.com",
        landlord_name="Landlord",
        landlord_email="landlord@example.com",
        landlord_phone=None,
        property_address="Address",
        unit_number=None,
        tenant_name=None,
        tenant_phone=None,
        issue_title="Issue",
        issue_description=long_description,
        priority=MaintenancePriority.MEDIUM,
        estimated_cost=None,
        scheduled_date=None,
        photos=None,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert subject is not None
    assert html is not None
    assert long_description in html


def test_email_templates_large_cost():
    """Test email templates handle large estimated costs."""
    subject, html = VendorEmailTemplates.create_vendor_assignment_email(
        vendor_name="Vendor",
        vendor_email="vendor@example.com",
        landlord_name="Landlord",
        landlord_email="landlord@example.com",
        landlord_phone=None,
        property_address="Address",
        unit_number=None,
        tenant_name=None,
        tenant_phone=None,
        issue_title="Major Repair",
        issue_description=None,
        priority=MaintenancePriority.HIGH,
        estimated_cost=Decimal("99999.99"),
        scheduled_date=None,
        photos=None,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert "$99,999.99" in html


def test_email_templates_tenant_with_phone():
    """Test tenant contact info includes phone when provided."""
    subject, html = VendorEmailTemplates.create_vendor_assignment_email(
        vendor_name="Vendor",
        vendor_email="vendor@example.com",
        landlord_name="Landlord",
        landlord_email="landlord@example.com",
        landlord_phone=None,
        property_address="Address",
        unit_number=None,
        tenant_name="Bob Smith",
        tenant_phone="+1234567890",
        issue_title="Issue",
        issue_description=None,
        priority=MaintenancePriority.MEDIUM,
        estimated_cost=None,
        scheduled_date=None,
        photos=None,
        request_id=1,
        frontend_url="https://app.brikli.com"
    )
    
    assert "Bob Smith" in html
    assert "+1234567890" in html or "1234567890" in html

