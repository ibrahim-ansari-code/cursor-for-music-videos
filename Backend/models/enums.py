from enum import Enum


class UserType(str, Enum):
    TENANT = "TENANT"
    LANDLORD = "LANDLORD"
    ADMIN = "ADMIN"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            try:
                return cls(value.upper())
            except ValueError:
                pass
        return super()._missing_(value)


class PropertyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DRAFT = "DRAFT"
    ARCHIVED = "ARCHIVED"


class MaintenancePriority(str, Enum):
    """
    Defines priority levels for maintenance requests.

    Levels:
    - LOW: Non-urgent issues that can be addressed during routine maintenance
    - MEDIUM: Important issues requiring attention but not immediate action
    - HIGH: Critical issues requiring immediate attention to prevent damage or safety concerns
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            try:
                return cls(value.upper())
            except ValueError:
                pass
        return super()._missing_(value)


class MaintenanceStatus(str, Enum):
    """
    Defines status states for maintenance requests throughout their lifecycle.
    """
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            try:
                return cls(value.upper())
            except ValueError:
                pass
        return super()._missing_(value)
