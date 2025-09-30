from typing import Dict, Any, Optional
from datetime import datetime, UTC
import re

from Backend.models.tenant import Tenant
from Backend.models.enums import TenantType


class CustomerSchema:
    """Schema for transforming between Brikli Tenant and QuickBooks Customer."""

    @staticmethod
    def format_canadian_phone(phone: str) -> str:
        """Format phone number for Canadian context."""
        if not phone:
            return ""

        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)

        # Handle Canadian phone number formatting
        if len(digits_only) == 10:
            # Assume it's a Canadian number without country code
            return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
        elif len(digits_only) == 11 and digits_only.startswith('1'):
            # North American number with country code
            area_code = digits_only[1:4]
            exchange = digits_only[4:7]
            number = digits_only[7:]
            return f"+1 ({area_code}) {exchange}-{number}"
        else:
            # Return as-is if it doesn't match expected patterns
            return phone.strip()

    @staticmethod
    def validate_for_quickbooks(tenant: Tenant) -> Dict[str, str]:
        """
        Validate tenant data for QuickBooks sync and return any issues.

        Returns:
            Dict with validation errors, empty if valid
        """
        errors = {}

        # Check required fields based on tenant type
        if tenant.tenant_type == TenantType.COMPANY:
            if not tenant.company_name or not tenant.company_name.strip():
                errors["company_name"] = "Company name is required for business customers"
            if not tenant.contact_person and not (tenant.first_name or tenant.last_name):
                errors["contact_person"] = "Contact person or individual name is required for business customers"
        else:
            if not tenant.first_name and not tenant.last_name:
                errors["name"] = "First name or last name is required for individual customers"

        # Email is highly recommended for matching
        if not tenant.email:
            errors["email"] = "Email address is recommended for proper customer matching"

        # Validate phone format if provided
        if tenant.phone:
            phone_digits = re.sub(r'\D', '', str(tenant.phone))
            if len(phone_digits) not in [10, 11] or (len(phone_digits) == 11 and not phone_digits.startswith('1')):
                errors["phone"] = "Phone number should be a valid North American format"

        return errors

    @staticmethod
    def to_quickbooks(tenant: Tenant) -> Dict[str, Any]:
        """Transform Brikli Tenant to QuickBooks Customer format."""
        customer_data = {
            "Customer": {
                "GivenName": tenant.first_name or "",
                "FamilyName": tenant.last_name or "",
                "DisplayName": f"{tenant.first_name or ''} {tenant.last_name or ''}".strip(),
                "Active": True
            }
        }

        # Add email if provided
        if tenant.email:
            customer_data["Customer"]["PrimaryEmailAddr"] = {
                "Address": str(tenant.email)
            }

        # Add phone if provided (format for Canadian numbers)
        if tenant.phone:
            formatted_phone = CustomerSchema.format_canadian_phone(str(tenant.phone))
            if formatted_phone:
                customer_data["Customer"]["PrimaryPhone"] = {
                    "FreeFormNumber": formatted_phone
                }

        return customer_data

    @staticmethod
    def from_quickbooks(qb_customer: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Transform QuickBooks Customer to Brikli Tenant format."""
        email_obj = qb_customer.get("PrimaryEmailAddr", {})
        phone_obj = qb_customer.get("PrimaryPhone", {})

        return {
            "first_name": qb_customer.get("GivenName", ""),
            "last_name": qb_customer.get("FamilyName", ""),
            "display_name": qb_customer.get("DisplayName", ""),
            "email": email_obj.get("Address") if email_obj else None,
            "phone": phone_obj.get("FreeFormNumber") if phone_obj else None,
            "quickbooks_id": qb_customer.get("Id"),
            "last_synced_at": datetime.now(UTC),
            "user_id": user_id
        }

    @staticmethod
    def create_search_query(email: str) -> str:
        """Create QuickBooks query for finding customers by email."""
        return f"Active=true AND PrimaryEmailAddr='{email}'"

    @staticmethod
    def needs_update(qb_customer: Dict[str, Any], tenant: Tenant) -> bool:
        """Check if QuickBooks customer needs to be updated with tenant data."""
        current_display_name = qb_customer.get("DisplayName", "")
        current_company_name = qb_customer.get("CompanyName", "")
        current_given_name = qb_customer.get("GivenName", "")
        current_family_name = qb_customer.get("FamilyName", "")

        # Check email
        current_email = ""
        email_obj = qb_customer.get("PrimaryEmailAddr")
        if email_obj:
            current_email = email_obj.get("Address", "")

        # Check phone
        current_phone = ""
        phone_obj = qb_customer.get("PrimaryPhone")
        if phone_obj:
            current_phone = phone_obj.get("FreeFormNumber", "")

        # Determine expected values based on tenant type
        if tenant.tenant_type == TenantType.COMPANY and tenant.company_name:
            expected_display_name = tenant.company_name.strip()
            expected_company_name = tenant.company_name.strip()

            # Contact person handling
            expected_given_name = ""
            expected_family_name = ""
            if tenant.contact_person:
                contact_parts = tenant.contact_person.strip().split(' ', 1)
                expected_given_name = contact_parts[0]
                expected_family_name = contact_parts[1] if len(contact_parts) > 1 else ""
            elif tenant.first_name or tenant.last_name:
                expected_given_name = tenant.first_name or ""
                expected_family_name = tenant.last_name or ""
        else:
            expected_display_name = f"{tenant.first_name or ''} {tenant.last_name or ''}".strip()
            if not expected_display_name:
                expected_display_name = "Unknown Customer"
            expected_company_name = ""
            expected_given_name = tenant.first_name or ""
            expected_family_name = tenant.last_name or ""

        # Compare all relevant fields
        return (
            current_display_name != expected_display_name or
            current_company_name != expected_company_name or
            current_given_name != expected_given_name or
            current_family_name != expected_family_name or
            current_email != (tenant.email or "") or
            current_phone != (str(tenant.phone) if tenant.phone else "")
        )

    @staticmethod
    def to_quickbooks_update(tenant: Tenant, qb_customer_id: str, sync_token: str) -> Dict[str, Any]:
        """Transform Brikli Tenant to QuickBooks Customer update format."""
        # Generate the full customer data using existing method
        customer_data = CustomerSchema.to_quickbooks(tenant)

        # Add required fields for update
        customer_data["Customer"]["Id"] = qb_customer_id
        customer_data["Customer"]["SyncToken"] = sync_token

        return customer_data