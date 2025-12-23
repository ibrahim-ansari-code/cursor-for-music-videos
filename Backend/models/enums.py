from enum import Enum
from typing import Self, Any, Optional


class UserType(str, Enum):
    """
    Defines user roles within the system.
    """
    ADMIN = "ADMIN"
    LANDLORD = "LANDLORD"
    TENANT = "TENANT"
    STAFF = "STAFF"  # For maintenance personnel or other staff

    @classmethod
    def _missing_(cls, value: Any) -> Self | None:
        if isinstance(value, str):
            try:
                return cls(value.upper())
            except ValueError:
                pass
        return super()._missing_(value)


class TenantType(str, Enum):
    """
    Defines the type of tenant - individual person or company/organization.
    """
    INDIVIDUAL = "Individual"
    COMPANY = "Company"

    @classmethod
    def _missing_(cls, value: Any) -> Self | None:
        if isinstance(value, str):
            # Handle case-insensitive matching
            # Normalize input value before loop to improve performance
            value_lower = value.lower()
            for member in cls:
                if member.value.lower() == value_lower:
                    return member
        return super()._missing_(value)


class ExpenseCategory(str, Enum):
    """
    Defines valid expense categories for property management.
    """
    MAINTENANCE = "maintenance"
    UTILITIES = "utilities"
    TAXES = "taxes"
    INSURANCE = "insurance"
    ADMINISTRATIVE = "administrative"
    OTHER = "other"

    @classmethod
    def _missing_(cls, value: Any) -> Optional["ExpenseCategory"]:
        if isinstance(value, str):
            # Case-insensitive matching for value
            lower_value = value.lower()
            for member in cls:
                if member.value.lower() == lower_value:
                    return member
            # Case-insensitive matching for member name
            try:
                return cls[value.upper()]
            except KeyError:
                pass
        return super()._missing_(value)


class PropertyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DRAFT = "DRAFT"
    ARCHIVED = "ARCHIVED"
    RENTED = "RENTED"
    VACANT = "VACANT"
    PARTIALLY_RENTED = "PARTIALLY_RENTED"

    @classmethod
    def _missing_(cls, value: Any) -> Self | None:
        if isinstance(value, str):
            try:
                return cls(value.upper())
            except ValueError:
                pass
        return super()._missing_(value)


class MaintenancePriority(str, Enum):
    """
    Defines priority levels for maintenance requests.

    Levels:
    - LOW: Non-urgent issues that can be addressed during routine maintenance
    - MEDIUM: Important issues requiring attention but not immediate action
    - HIGH: Critical issues requiring immediate attention to prevent damage or safety concerns
    """
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

    @classmethod
    def _missing_(cls, value: Any) -> Optional["MaintenancePriority"]:
        if isinstance(value, str):
            # Case-insensitive matching for value
            lower_value = value.lower()
            for member in cls:
                if member.value.lower() == lower_value:
                    return member
            # Case-insensitive matching for member name (e.g., "HIGH" maps to MaintenancePriority.HIGH)
            try:
                return cls[value.upper()]
            except KeyError:
                pass
        return super()._missing_(value)


class MaintenanceStatus(str, Enum):
    """
    Defines status states for maintenance requests throughout their lifecycle.
    
    Status Flow:
    - NEW: Tenant submitted, landlord hasn't reviewed yet
    - PENDING: Landlord reviewed, work not started
    - IN_PROGRESS: Work actively being done
    - SCHEDULED: Work scheduled for future date
    - COMPLETED: Work finished
    - CANCELLED: Request cancelled
    """
    NEW = "New"
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    SCHEDULED = "Scheduled"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

    @classmethod
    def _missing_(cls, value: Any) -> Optional["MaintenanceStatus"]:
        if isinstance(value, str):
            # Case-insensitive matching for value
            lower_value = value.lower()
            for member in cls:
                # Special handling for "In Progress" due to space
                member_val_lower = member.value.lower().replace(" ", "")
                input_val_lower = lower_value.replace(" ", "").replace(
                    "_", "")  # Also handle snake_case input like "in_progress"
                if member_val_lower == input_val_lower:
                    return member
            # Case-insensitive matching for member name
            try:
                # For names like IN_PROGRESS, client might send "IN_PROGRESS" or "in_progress"
                return cls[value.upper().replace(" ", "_")]
            except KeyError:
                pass
        return super()._missing_(value)


class DocumentCategory(str, Enum):
    """
    Document category enum - matches database document_category_enum.
    
    Defines 14 main categories for tenant document organization:
    - Lease & Core Agreements
    - Lease Addendums
    - Condition & Inspections
    - Province/Territory Forms
    - Commercial Tenant Files
    - Applications & Screening/KYC
    - Insurance & Risk
    - Financial & Payments
    - Maintenance/Unit-Level Work
    - Legal Notices & Tribunal
    - Communications & Records
    - Move-In/Move-Out & Assets
    - Privacy & Data Security
    - Health/Safety/Accessibility
    """
    LEASE_AGREEMENTS = "lease_agreements"
    LEASE_ADDENDUMS = "lease_addendums"
    CONDITION_INSPECTIONS = "condition_inspections"
    PROVINCE_FORMS = "province_forms"
    COMMERCIAL_FILES = "commercial_files"
    APPLICATIONS_KYC = "applications_kyc"
    INSURANCE_RISK = "insurance_risk"
    FINANCIAL_PAYMENTS = "financial_payments"
    MAINTENANCE_WORK = "maintenance_work"
    LEGAL_NOTICES = "legal_notices"
    COMMUNICATIONS = "communications"
    MOVE_IN_OUT = "move_in_out"
    PRIVACY_SECURITY = "privacy_security"
    HEALTH_SAFETY = "health_safety"

    @classmethod
    def _missing_(cls, value: Any) -> Optional["DocumentCategory"]:
        if isinstance(value, str):
            # Case-insensitive matching for value
            lower_value = value.lower()
            for member in cls:
                if member.value.lower() == lower_value:
                    return member
            # Case-insensitive matching for member name
            try:
                return cls[value.upper()]
            except KeyError:
                pass
        return super()._missing_(value)


class DocumentStatus(str, Enum):
    """
    Document status enum - matches database document_status_enum.

    Defines document workflow states:
    - PENDING: Awaiting review or verification
    - VERIFIED: Approved and verified by admin
    - REJECTED: Rejected or invalid document
    - EXPIRED: Document has passed its expiry date
    """
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"

    @classmethod
    def _missing_(cls, value):
        """Enable case-insensitive lookup"""
        if isinstance(value, str):
            value_lower = value.lower()
            for member in cls:
                if member.value == value_lower:
                    return member
        return None


class PortalStatus(str, Enum):
    """
    Defines tenant portal access status.

    This enum tracks the lifecycle of a tenant's portal access:
    - NONE: Tenant has never been invited to the portal
    - INVITED: Invitation sent but not yet accepted
    - ACTIVE: Tenant has portal access and is using a seat
    - REVOKED: Portal access was explicitly revoked by landlord

    Seat counting: seats_used = COUNT(tenants WHERE portal_status = 'active')
    """
    NONE = "none"
    INVITED = "invited"
    ACTIVE = "active"
    REVOKED = "revoked"

    @classmethod
    def _missing_(cls, value: Any) -> Self | None:
        if isinstance(value, str):
            try:
                return cls(value.lower())
            except ValueError:
                pass
        return super()._missing_(value)

