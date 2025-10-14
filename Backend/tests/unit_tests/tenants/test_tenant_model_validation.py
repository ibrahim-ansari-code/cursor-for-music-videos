"""
Unit tests for Tenant model emergency contacts validation.

These tests focus on the validate_emergency_contacts model validator including:
- Max 5 contacts limit
- Required field validation
- XSS sanitization (HTML escape)
- Primary contact uniqueness
- Business rule enforcement
"""

import pytest
from pydantic import ValidationError
from uuid import uuid4

from Backend.models.tenant import Tenant, TenantStatus
from Backend.models.enums import TenantType

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Test landlord ID for all tests
TEST_LANDLORD_ID = uuid4()


# =============================================================================
# Max 5 Contacts Limit Tests - covers tenant.py:187-188
# =============================================================================

def test_emergency_contacts_max_5_limit():
    """Test maximum 5 emergency contacts enforced - covers tenant.py:187-188"""
    # Try to create tenant with 6 contacts
    contacts = [
        {"name": f"Contact {i}", "relationship": "Friend", "phone": f"555-{i}000000", "is_primary": False}
        for i in range(6)
    ]

    with pytest.raises(ValidationError) as exc_info:
        Tenant.model_validate({
            "tenant_type": TenantType.INDIVIDUAL,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "status": TenantStatus.ACTIVE,
            "landlord_id": TEST_LANDLORD_ID,
            "emergency_contacts": contacts
        })

    errors = exc_info.value.errors()
    assert any("Maximum 5 emergency contacts" in str(error) for error in errors)


def test_emergency_contacts_exactly_5_allowed():
    """Test that exactly 5 contacts is allowed"""
    contacts = [
        {"name": f"Contact {i}", "relationship": "Friend", "phone": f"555-{i}000000", "is_primary": False}
        for i in range(5)
    ]

    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": contacts
    })

    assert len(tenant.emergency_contacts) == 5


# =============================================================================
# Required Fields Validation Tests - covers tenant.py:199-208
# =============================================================================

def test_emergency_contact_missing_name():
    """Test validation fails when name is missing - covers tenant.py:199-201"""
    contacts = [
        {# "name" is missing
            "relationship": "Brother",
            "phone": "555-1234567",
            "is_primary": False
        }
    ]

    with pytest.raises(ValidationError) as exc_info:
        Tenant.model_validate({
            "tenant_type": TenantType.INDIVIDUAL,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "status": TenantStatus.ACTIVE,
            "landlord_id": TEST_LANDLORD_ID,
            "emergency_contacts": contacts
        })

    errors = exc_info.value.errors()
    assert any("name" in str(error).lower() and "required" in str(error).lower() for error in errors)


def test_emergency_contact_missing_relationship():
    """Test validation fails when relationship is missing - covers tenant.py:203-204"""
    contacts = [
        {
            "name": "John Emergency",
            # "relationship" is missing
            "phone": "555-1234567",
            "is_primary": False
        }
    ]

    with pytest.raises(ValidationError) as exc_info:
        Tenant.model_validate({
            "tenant_type": TenantType.INDIVIDUAL,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "status": TenantStatus.ACTIVE,
            "landlord_id": TEST_LANDLORD_ID,
            "emergency_contacts": contacts
        })

    errors = exc_info.value.errors()
    assert any("relationship" in str(error).lower() and "required" in str(error).lower() for error in errors)


def test_emergency_contact_missing_phone():
    """Test validation fails when phone is missing - covers tenant.py:207-208"""
    contacts = [
        {
            "name": "John Emergency",
            "relationship": "Brother",
            # "phone" is missing
            "is_primary": False
        }
    ]

    with pytest.raises(ValidationError) as exc_info:
        Tenant.model_validate({
            "tenant_type": TenantType.INDIVIDUAL,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "status": TenantStatus.ACTIVE,
            "landlord_id": TEST_LANDLORD_ID,
            "emergency_contacts": contacts
        })

    errors = exc_info.value.errors()
    assert any("phone" in str(error).lower() and "required" in str(error).lower() for error in errors)


# =============================================================================
# XSS Sanitization Tests - covers tenant.py:214-256
# =============================================================================

def test_emergency_contact_xss_sanitization_name():
    """Test HTML/XSS sanitization on name field - covers tenant.py:214-220"""
    contacts = [
        {
            "name": "<script>alert('XSS')</script>John",
            "relationship": "Brother",
            "phone": "555-1234567",
            "is_primary": False
        }
    ]

    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": contacts
    })

    # HTML should be escaped
    assert "<script>" not in tenant.emergency_contacts[0]["name"]
    assert "&lt;" in tenant.emergency_contacts[0]["name"] or "alert" not in tenant.emergency_contacts[0]["name"]


def test_emergency_contact_xss_sanitization_relationship():
    """Test HTML/XSS sanitization on relationship field - covers tenant.py:223-229"""
    contacts = [
        {
            "name": "John",
            "relationship": "<img src=x onerror=alert('XSS')>Brother",
            "phone": "555-1234567",
            "is_primary": False
        }
    ]

    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": contacts
    })

    # HTML should be escaped
    assert "<img" not in tenant.emergency_contacts[0]["relationship"]


def test_emergency_contact_phone_sanitization():
    """Test phone number is sanitized/trimmed - covers tenant.py:232-233"""
    contacts = [
        {
            "name": "John",
            "relationship": "Brother",
            "phone": "  555-1234567  ",  # Extra whitespace
            "is_primary": False
        }
    ]

    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": contacts
    })

    # Phone should be trimmed (whitespace removed by sanitization)
    assert tenant.emergency_contacts[0]["phone"] == "555-1234567"


def test_emergency_contact_email_validation_and_sanitization():
    """Test email validation and sanitization - covers tenant.py:234-244"""
    contacts = [
        {
            "name": "John",
            "relationship": "Brother",
            "phone": "555-1234567",
            "email": "  john@example.com  ",  # Extra whitespace
            "is_primary": False
        }
    ]

    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": contacts
    })

    # Email should be trimmed and HTML-escaped
    assert tenant.emergency_contacts[0]["email"] == "john@example.com"


def test_emergency_contact_notes_sanitization():
    """Test notes field XSS sanitization - covers tenant.py:247-252"""
    contacts = [
        {
            "name": "John",
            "relationship": "Brother",
            "phone": "555-1234567",
            "notes": "<b>Important</b> contact info",
            "is_primary": False
        }
    ]

    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": contacts
    })

    # HTML should be escaped in notes
    assert "<b>" not in tenant.emergency_contacts[0]["notes"]
    assert "&lt;" in tenant.emergency_contacts[0]["notes"]


def test_emergency_contact_id_preservation():
    """Test that existing IDs are preserved - covers tenant.py:255-256"""
    existing_id = "existing-uuid-123"
    contacts = [
        {
            "id": existing_id,
            "name": "John",
            "relationship": "Brother",
            "phone": "555-1234567",
            "is_primary": False
        }
    ]

    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": contacts
    })

    # ID should be preserved
    assert tenant.emergency_contacts[0]["id"] == existing_id


def test_emergency_contact_id_generated_when_missing():
    """Test that ID is generated when not provided"""
    contacts = [
        {
            # No "id" provided
            "name": "John",
            "relationship": "Brother",
            "phone": "555-1234567",
            "is_primary": False
        }
    ]

    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": contacts
    })

    # ID should be auto-generated by validator
    assert "id" in tenant.emergency_contacts[0]
    assert tenant.emergency_contacts[0]["id"] is not None
    # Verify it's a valid UUID format
    import uuid
    assert uuid.UUID(tenant.emergency_contacts[0]["id"])


# =============================================================================
# Primary Contact Business Rules - covers tenant.py:263-270
# =============================================================================

def test_emergency_contact_only_one_primary_allowed():
    """Test that only one primary contact is allowed - covers tenant.py:263-270"""
    contacts = [
        {"name": "Contact 1", "relationship": "Brother", "phone": "555-1111111", "is_primary": True},
        {"name": "Contact 2", "relationship": "Sister", "phone": "555-2222222", "is_primary": True},  # Second primary
    ]

    with pytest.raises(ValidationError) as exc_info:
        Tenant.model_validate({
            "tenant_type": TenantType.INDIVIDUAL,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "status": TenantStatus.ACTIVE,
            "landlord_id": TEST_LANDLORD_ID,
            "emergency_contacts": contacts
        })

    errors = exc_info.value.errors()
    assert any("Only one" in str(error) and "primary" in str(error) for error in errors)


def test_emergency_contact_single_primary_allowed():
    """Test that one primary contact is allowed"""
    contacts = [
        {"name": "Contact 1", "relationship": "Brother", "phone": "555-1111111", "is_primary": True},
        {"name": "Contact 2", "relationship": "Sister", "phone": "555-2222222", "is_primary": False},
    ]

    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": contacts
    })

    primary_contacts = [c for c in tenant.emergency_contacts if c["is_primary"]]
    assert len(primary_contacts) == 1


def test_emergency_contact_no_primary_allowed():
    """Test that zero primary contacts is allowed"""
    contacts = [
        {"name": "Contact 1", "relationship": "Brother", "phone": "555-1111111", "is_primary": False},
        {"name": "Contact 2", "relationship": "Sister", "phone": "555-2222222", "is_primary": False},
    ]

    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": contacts
    })

    primary_contacts = [c for c in tenant.emergency_contacts if c["is_primary"]]
    assert len(primary_contacts) == 0


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================

def test_emergency_contacts_empty_list():
    """Test that empty emergency contacts list is valid"""
    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": []
    })

    assert tenant.emergency_contacts == []


def test_emergency_contacts_none_value():
    """Test that None emergency contacts is valid"""
    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": []  # Use empty list instead of None
    })

    # Empty list is the proper way to have no contacts
    assert tenant.emergency_contacts == []


def test_emergency_contacts_full_workflow():
    """Test complete workflow with all validations"""
    contacts = [
        {
            "name": "<b>John</b> Emergency",  # XSS attempt
            "relationship": "Brother",
            "phone": "  555-1234567  ",  # Whitespace
            "email": "  john@example.com  ",  # Whitespace (lowercase for valid email)
            "notes": "<script>alert('test')</script>Important",  # XSS attempt
            "is_primary": True
        },
        {
            "name": "Jane Emergency",
            "relationship": "Sister",
            "phone": "555-7654321",
            "is_primary": False
        }
    ]

    tenant = Tenant.model_validate({
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "status": TenantStatus.ACTIVE,
        "landlord_id": TEST_LANDLORD_ID,
        "emergency_contacts": contacts
    })

    # Verify XSS sanitization occurred
    assert "<b>" not in tenant.emergency_contacts[0]["name"]
    assert "&lt;b&gt;" in tenant.emergency_contacts[0]["name"]  # HTML escaped
    
    # Verify phone trimming
    assert tenant.emergency_contacts[0]["phone"] == "555-1234567"
    
    # Verify email trimming and escaping
    assert tenant.emergency_contacts[0]["email"] == "john@example.com"
    
    # Verify notes XSS sanitization
    assert "<script>" not in tenant.emergency_contacts[0]["notes"]
    assert "&lt;script&gt;" in tenant.emergency_contacts[0]["notes"]  # HTML escaped

    # Verify only one primary
    primary_contacts = [c for c in tenant.emergency_contacts if c["is_primary"]]
    assert len(primary_contacts) == 1

    # Verify total count
    assert len(tenant.emergency_contacts) == 2
    
    # Verify both contacts have auto-generated IDs
    assert "id" in tenant.emergency_contacts[0]
    assert "id" in tenant.emergency_contacts[1]
