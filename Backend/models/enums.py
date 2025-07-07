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
    """
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
