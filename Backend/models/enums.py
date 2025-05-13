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