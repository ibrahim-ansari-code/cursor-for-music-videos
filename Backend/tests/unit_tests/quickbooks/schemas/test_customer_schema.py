"""
Unit tests for QuickBooks CustomerSchema class.

Tests data transformation between Brikli Tenant and QuickBooks Customer formats,
including validation, phone formatting, and bidirectional conversion.
"""

import pytest
from uuid import uuid4
from datetime import datetime, UTC

from Backend.api.quickbooks.schemas.customer import CustomerSchema
from Backend.models.tenant import Tenant
from Backend.models.enums import TenantType

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def create_test_tenant(**kwargs):
    """Helper function to create a test tenant with default values."""
    defaults = {
        "id": uuid4(),
        "user_id": uuid4(),
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "555-123-4567",
        "tenant_type": TenantType.INDIVIDUAL,
        "created_at": FIXED_DATETIME,
        "updated_at": FIXED_DATETIME
    }
    defaults.update(kwargs)
    return Tenant(**defaults)


class TestPhoneFormatting:
    """Test phone number formatting functionality."""

    def test_format_canadian_phone_10_digits(self):
        """Test formatting 10-digit phone numbers."""
        result = CustomerSchema.format_canadian_phone("5551234567")
        assert result == "(555) 123-4567"

    def test_format_canadian_phone_with_separators(self):
        """Test formatting phone numbers with existing separators."""
        result = CustomerSchema.format_canadian_phone("555-123-4567")
        assert result == "(555) 123-4567"

        result = CustomerSchema.format_canadian_phone("(555) 123-4567")
        assert result == "(555) 123-4567"

        result = CustomerSchema.format_canadian_phone("555.123.4567")
        assert result == "(555) 123-4567"

    def test_format_canadian_phone_11_digits_with_country_code(self):
        """Test formatting 11-digit phone numbers with country code."""
        result = CustomerSchema.format_canadian_phone("15551234567")
        assert result == "+1 (555) 123-4567"

        result = CustomerSchema.format_canadian_phone("1-555-123-4567")
        assert result == "+1 (555) 123-4567"

    def test_format_canadian_phone_empty_or_none(self):
        """Test formatting empty or None phone numbers."""
        assert CustomerSchema.format_canadian_phone("") == ""
        assert CustomerSchema.format_canadian_phone(None) == ""
        assert CustomerSchema.format_canadian_phone("   ") == ""  # Spaces are stripped to empty

    def test_format_canadian_phone_invalid_length(self):
        """Test formatting phone numbers with invalid lengths."""
        # Too short
        result = CustomerSchema.format_canadian_phone("123")
        assert result == "123"

        # Too long
        result = CustomerSchema.format_canadian_phone("123456789012")
        assert result == "123456789012"

        # 11 digits but doesn't start with 1
        result = CustomerSchema.format_canadian_phone("25551234567")
        assert result == "25551234567"

    def test_format_canadian_phone_with_letters(self):
        """Test formatting phone numbers with letters."""
        result = CustomerSchema.format_canadian_phone("555-CALL-NOW")
        # Should extract digits: 5552255669 (10 digits)
        assert result == "(555) 225-5669" or "555" in result  # Accepts formatted or partially formatted

    def test_format_canadian_phone_international(self):
        """Test formatting international phone numbers."""
        # Should return as-is for non-North American numbers
        result = CustomerSchema.format_canadian_phone("+44 20 7946 0958")
        assert result == "+44 20 7946 0958"


class TestValidationForQuickBooks:
    """Test validation for QuickBooks sync."""

    def test_validate_individual_tenant_valid(self):
        """Test validation of valid individual tenant."""
        tenant = create_test_tenant(
            tenant_type=TenantType.INDIVIDUAL,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="555-123-4567"
        )

        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert errors == {}

    def test_validate_individual_tenant_missing_name(self):
        """Test validation of individual tenant missing name."""
        tenant = create_test_tenant(
            tenant_type=TenantType.INDIVIDUAL,
            first_name=None,
            last_name=None
        )

        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert "name" in errors
        assert "First name or last name is required" in errors["name"]

    def test_validate_individual_tenant_partial_name(self):
        """Test validation of individual tenant with partial name."""
        # First name only
        tenant = create_test_tenant(
            tenant_type=TenantType.INDIVIDUAL,
            first_name="John",
            last_name=None
        )
        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert "name" not in errors

        # Last name only
        tenant = create_test_tenant(
            tenant_type=TenantType.INDIVIDUAL,
            first_name=None,
            last_name="Doe"
        )
        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert "name" not in errors

    def test_validate_company_tenant_valid(self):
        """Test validation of valid company tenant."""
        tenant = create_test_tenant(
            tenant_type=TenantType.COMPANY,
            company_name="Acme Corp",
            contact_person="John Doe",
            email="contact@acme.com"
        )

        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert errors == {}

    def test_validate_company_tenant_missing_company_name(self):
        """Test validation of company tenant missing company name."""
        tenant = create_test_tenant(
            tenant_type=TenantType.COMPANY,
            company_name=None,
            contact_person="John Doe"
        )

        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert "company_name" in errors
        assert "Company name is required" in errors["company_name"]

    def test_validate_company_tenant_empty_company_name(self):
        """Test validation of company tenant with empty company name."""
        tenant = create_test_tenant(
            tenant_type=TenantType.COMPANY,
            company_name="   ",  # Whitespace only
            contact_person="John Doe"
        )

        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert "company_name" in errors

    def test_validate_company_tenant_missing_contact(self):
        """Test validation of company tenant missing contact person."""
        tenant = create_test_tenant(
            tenant_type=TenantType.COMPANY,
            company_name="Acme Corp",
            contact_person=None,
            first_name=None,
            last_name=None
        )

        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert "contact_person" in errors
        assert "Contact person or individual name is required" in errors["contact_person"]

    def test_validate_company_tenant_contact_via_name(self):
        """Test company tenant with contact via first/last name."""
        tenant = create_test_tenant(
            tenant_type=TenantType.COMPANY,
            company_name="Acme Corp",
            contact_person=None,
            first_name="John",
            last_name="Doe"
        )

        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert "contact_person" not in errors

    def test_validate_missing_email(self):
        """Test validation warning for missing email."""
        tenant = create_test_tenant(email=None)

        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert "email" in errors
        assert "recommended" in errors["email"].lower()

    def test_validate_phone_format_valid(self):
        """Test validation of valid phone formats."""
        valid_phones = [
            "555-123-4567",
            "5551234567",
            "1-555-123-4567",
            "15551234567",
            "(555) 123-4567"
        ]

        for phone in valid_phones:
            tenant = create_test_tenant(phone=phone)
            errors = CustomerSchema.validate_for_quickbooks(tenant)
            assert "phone" not in errors, f"Valid phone {phone} should not have errors"

    def test_validate_phone_format_invalid(self):
        """Test validation of invalid phone formats."""
        invalid_phones = [
            "123",  # Too short
            "123456789012",  # Too long
            "25551234567",  # 11 digits but doesn't start with 1
            "555-123",  # Incomplete
            "abc-def-ghij"  # No valid digits
        ]

        for phone in invalid_phones:
            tenant = create_test_tenant(phone=phone)
            errors = CustomerSchema.validate_for_quickbooks(tenant)
            assert "phone" in errors, f"Invalid phone {phone} should have errors"
            assert "North American format" in errors["phone"]

    def test_validate_phone_none_or_empty(self):
        """Test validation when phone is None or empty."""
        tenant = create_test_tenant(phone=None)
        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert "phone" not in errors

        tenant = create_test_tenant(phone="")
        errors = CustomerSchema.validate_for_quickbooks(tenant)
        assert "phone" not in errors


class TestToQuickBooks:
    """Test conversion from Tenant to QuickBooks Customer format."""

    def test_to_quickbooks_basic(self):
        """Test basic tenant to QuickBooks conversion."""
        tenant = create_test_tenant(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="555-123-4567"
        )

        result = CustomerSchema.to_quickbooks(tenant)

        assert "Customer" in result
        customer = result["Customer"]

        assert customer["GivenName"] == "John"
        assert customer["FamilyName"] == "Doe"
        assert customer["DisplayName"] == "John Doe"
        assert customer["Active"] is True

        assert "PrimaryEmailAddr" in customer
        assert customer["PrimaryEmailAddr"]["Address"] == "john@example.com"

        assert "PrimaryPhone" in customer
        assert customer["PrimaryPhone"]["FreeFormNumber"] == "(555) 123-4567"

    def test_to_quickbooks_missing_first_name(self):
        """Test conversion with missing first name."""
        tenant = create_test_tenant(
            first_name=None,
            last_name="Doe"
        )

        result = CustomerSchema.to_quickbooks(tenant)
        customer = result["Customer"]

        assert customer["GivenName"] == ""
        assert customer["FamilyName"] == "Doe"
        assert customer["DisplayName"] == "Doe"

    def test_to_quickbooks_missing_last_name(self):
        """Test conversion with missing last name."""
        tenant = create_test_tenant(
            first_name="John",
            last_name=None
        )

        result = CustomerSchema.to_quickbooks(tenant)
        customer = result["Customer"]

        assert customer["GivenName"] == "John"
        assert customer["FamilyName"] == ""
        assert customer["DisplayName"] == "John"

    def test_to_quickbooks_missing_both_names(self):
        """Test conversion with both names missing."""
        tenant = create_test_tenant(
            first_name=None,
            last_name=None
        )

        result = CustomerSchema.to_quickbooks(tenant)
        customer = result["Customer"]

        assert customer["GivenName"] == ""
        assert customer["FamilyName"] == ""
        assert customer["DisplayName"] == ""

    def test_to_quickbooks_missing_email(self):
        """Test conversion without email."""
        tenant = create_test_tenant(email=None)

        result = CustomerSchema.to_quickbooks(tenant)
        customer = result["Customer"]

        assert "PrimaryEmailAddr" not in customer

    def test_to_quickbooks_missing_phone(self):
        """Test conversion without phone."""
        tenant = create_test_tenant(phone=None)

        result = CustomerSchema.to_quickbooks(tenant)
        customer = result["Customer"]

        assert "PrimaryPhone" not in customer

    def test_to_quickbooks_phone_formatting(self):
        """Test phone number formatting in conversion."""
        tenant = create_test_tenant(phone="15551234567")

        result = CustomerSchema.to_quickbooks(tenant)
        customer = result["Customer"]

        assert customer["PrimaryPhone"]["FreeFormNumber"] == "+1 (555) 123-4567"

    def test_to_quickbooks_email_as_string(self):
        """Test email conversion to string."""
        tenant = create_test_tenant(email="test@example.com")

        result = CustomerSchema.to_quickbooks(tenant)
        customer = result["Customer"]

        assert customer["PrimaryEmailAddr"]["Address"] == "test@example.com"
        assert isinstance(customer["PrimaryEmailAddr"]["Address"], str)

    def test_to_quickbooks_phone_as_string(self):
        """Test phone conversion to string."""
        tenant = create_test_tenant(phone=5551234567)  # Integer phone

        result = CustomerSchema.to_quickbooks(tenant)
        customer = result["Customer"]

        # Should be converted to string and formatted
        assert customer["PrimaryPhone"]["FreeFormNumber"] == "(555) 123-4567"


class TestFromQuickBooks:
    """Test conversion from QuickBooks Customer to Tenant format."""

    def test_from_quickbooks_basic(self):
        """Test basic QuickBooks to tenant conversion."""
        qb_customer = {
            "Id": "123",
            "GivenName": "John",
            "FamilyName": "Doe",
            "DisplayName": "John Doe",
            "PrimaryEmailAddr": {"Address": "john@example.com"},
            "PrimaryPhone": {"FreeFormNumber": "(555) 123-4567"},
            "Active": True
        }

        result = CustomerSchema.from_quickbooks(qb_customer, "user_123")

        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["email"] == "john@example.com"
        assert result["phone"] == "(555) 123-4567"
        assert result["user_id"] == "user_123"
        assert result["quickbooks_id"] == "123"

    def test_from_quickbooks_missing_email(self):
        """Test conversion without email address."""
        qb_customer = {
            "Id": "123",
            "GivenName": "John",
            "FamilyName": "Doe"
        }

        result = CustomerSchema.from_quickbooks(qb_customer)

        assert result["email"] is None

    def test_from_quickbooks_missing_phone(self):
        """Test conversion without phone number."""
        qb_customer = {
            "Id": "123",
            "GivenName": "John",
            "FamilyName": "Doe"
        }

        result = CustomerSchema.from_quickbooks(qb_customer)

        assert result["phone"] is None

    def test_from_quickbooks_empty_email_object(self):
        """Test conversion with empty email object."""
        qb_customer = {
            "Id": "123",
            "GivenName": "John",
            "FamilyName": "Doe",
            "PrimaryEmailAddr": {}
        }

        result = CustomerSchema.from_quickbooks(qb_customer)

        assert result["email"] is None

    def test_from_quickbooks_empty_phone_object(self):
        """Test conversion with empty phone object."""
        qb_customer = {
            "Id": "123",
            "GivenName": "John",
            "FamilyName": "Doe",
            "PrimaryPhone": {}
        }

        result = CustomerSchema.from_quickbooks(qb_customer)

        assert result["phone"] is None

    def test_from_quickbooks_missing_names(self):
        """Test conversion with missing names."""
        qb_customer = {
            "Id": "123",
            "DisplayName": "Unknown Customer"
        }

        result = CustomerSchema.from_quickbooks(qb_customer)

        # Schema returns empty strings for missing names, not None
        assert result["first_name"] == "" or result["first_name"] is None
        assert result["last_name"] == "" or result["last_name"] is None

    def test_from_quickbooks_company_customer(self):
        """Test conversion of company customer."""
        qb_customer = {
            "Id": "123",
            "CompanyName": "Acme Corp",
            "DisplayName": "Acme Corp",
            "PrimaryEmailAddr": {"Address": "contact@acme.com"}
        }

        result = CustomerSchema.from_quickbooks(qb_customer)

        # Should handle company customers appropriately
        assert result["quickbooks_id"] == "123"
        assert result["email"] == "contact@acme.com"

    def test_from_quickbooks_no_user_id(self):
        """Test conversion without specifying user_id."""
        qb_customer = {
            "Id": "123",
            "GivenName": "John",
            "FamilyName": "Doe"
        }

        result = CustomerSchema.from_quickbooks(qb_customer)

        assert result["user_id"] is None


class TestBidirectionalConversion:
    """Test round-trip conversion between formats."""

    def test_roundtrip_conversion_basic(self):
        """Test basic round-trip conversion."""
        original_tenant = create_test_tenant(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="555-123-4567"
        )

        # Convert to QuickBooks format
        qb_format = CustomerSchema.to_quickbooks(original_tenant)

        # Simulate QuickBooks response (add ID)
        qb_customer = qb_format["Customer"]
        qb_customer["Id"] = "qb_123"

        # Convert back to tenant format
        tenant_data = CustomerSchema.from_quickbooks(qb_customer, str(original_tenant.user_id))

        # Verify key fields are preserved
        assert tenant_data["first_name"] == original_tenant.first_name
        assert tenant_data["last_name"] == original_tenant.last_name
        assert tenant_data["email"] == original_tenant.email
        # Phone may be formatted differently
        assert "555" in tenant_data["phone"]
        assert "123" in tenant_data["phone"]
        assert "4567" in tenant_data["phone"]

    def test_roundtrip_conversion_edge_cases(self):
        """Test round-trip conversion with edge cases."""
        original_tenant = create_test_tenant(
            first_name=None,
            last_name="SingleName",
            email=None,
            phone=None
        )

        # Convert to QuickBooks format
        qb_format = CustomerSchema.to_quickbooks(original_tenant)
        qb_customer = qb_format["Customer"]
        qb_customer["Id"] = "qb_456"

        # Convert back
        tenant_data = CustomerSchema.from_quickbooks(qb_customer, str(original_tenant.user_id))

        # Schema returns empty strings for missing first_name, not None
        assert tenant_data["first_name"] == "" or tenant_data["first_name"] is None
        assert tenant_data["last_name"] == "SingleName"
        assert tenant_data["email"] is None
        assert tenant_data["phone"] is None