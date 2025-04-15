from enum import Enum

class UserType(str, Enum):
    ADMIN = "ADMIN"
    LANDLORD = "LANDLORD"
    TENANT = "TENANT"
    VENDOR = "VENDOR" 