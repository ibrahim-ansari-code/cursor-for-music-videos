import re
from datetime import datetime
from uuid import UUID as PythonUUID

from pydantic import BaseModel, ConfigDict, computed_field, field_validator, model_validator

from Backend.models.tenant import TenantStatus


# === Models ===
class PropertyResponseSimple(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UnitResponseSimple(BaseModel):
    id: int
    name: str  # Assuming unit has a 'name' or 'unit_number' field
    property: PropertyResponseSimple | None = None  # Nested property info

    model_config = ConfigDict(from_attributes=True)


class TenantBase(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: str
    status: TenantStatus = TenantStatus.ACTIVE
    user_id: PythonUUID | None = None
    current_property_id: int | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """
        Validates and normalizes an email address.
        
        Trims whitespace, converts the email to lowercase, and checks that it matches a standard email format. Raises a ValueError if the email is empty or invalid.
        """
        email = v.strip().lower()
        if not email:
            raise ValueError("Email cannot be empty")
        # Basic email validation
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            raise ValueError("Invalid email format")
        return email

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validates that a name string is not empty or only whitespace.
        
        Returns the trimmed name if valid; raises ValueError if the input is empty or contains only whitespace.
        """
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """
        Validates that a phone number contains 10 to 15 digits and only allowed formatting characters.
        
        The phone number may include digits, spaces, hyphens, parentheses, and a plus sign. Raises a ValueError if the digit count is outside the allowed range or if disallowed characters are present.
        """
        # Single regex validation for both allowed characters and digit count
        # Pattern ensures 10-20 characters total with at least 10-15 digits
        if not re.fullmatch(r"^[\d\s\-\(\)\+]{10,20}$", v):
            raise ValueError("Phone number must be 10-20 characters long and contain only digits, spaces, hyphens, parentheses, and plus signs")
        
        # Verify digit count is within range
        digit_count = len(re.sub(r"[^0-9]", "", v))
        if not (10 <= digit_count <= 15):
            raise ValueError("Phone number must contain 10-15 digits")
        
        return v.strip()


class TenantCreate(TenantBase):
    # Allow receiving full_name from frontend for backward compatibility
    full_name: str | None = None
    # Make all fields required except these optional ones
    current_property_id: int | None = None
    user_id: PythonUUID | None = None

    @model_validator(mode="before")
    @classmethod
    def split_full_name(cls, data: dict) -> dict:
        """
        Extracts first and last names from a 'full_name' field in input data if separate fields are missing.
        
        If 'full_name' is present and both 'first_name' and 'last_name' are absent, splits 'full_name' into first and last names, assigns them to the corresponding fields, and removes 'full_name' from the data.
        """
        if isinstance(data, dict):
            full_name = data.get("full_name")
            first_name = data.get("first_name")
            last_name = data.get("last_name")

            if full_name and not first_name and not last_name:
                names = full_name.split(" ", 1)
                data["first_name"] = names[0]
                if len(names) > 1:
                    data["last_name"] = names[1]
                else:
                    # Use the first name as last name if no space is found
                    # This prevents empty last_name validation errors
                    data["last_name"] = names[0]
        return data


class TenantBaseOptional(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: TenantStatus | None = None
    current_property_id: int | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """
        Validates and normalizes an email address.
        
        Trims whitespace, converts to lowercase, and checks that the email is non-empty and matches a standard email pattern. Returns the normalized email or None if input is None.
        
        Raises:
            ValueError: If the email is empty or does not match the required format.
        """
        if v is None:
            return v
        if not v:
            raise ValueError("Email cannot be empty")
        email = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            raise ValueError("Invalid email format")
        return email

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """
        Validates that a name is not empty or whitespace.
        
        Returns the trimmed name if valid, or None if the input is None. Raises a ValueError if the name is empty or contains only whitespace.
        """
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """
        Validates that a phone number contains 10 to 15 digits and only allowed characters.
        
        Returns the trimmed phone number if valid, or None if input is None.
        
        Raises:
            ValueError: If the phone number does not contain 10-15 digits or contains invalid characters.
        """
        if v is None:
            return v
        # Single regex validation for both allowed characters and digit count
        # Pattern ensures 10-20 characters total with at least 10-15 digits
        if not re.fullmatch(r"^[\d\s\-\(\)\+]{10,20}$", v):
            raise ValueError("Phone number must be 10-20 characters long and contain only digits, spaces, hyphens, parentheses, and plus signs")
        
        # Verify digit count is within range
        digit_count = len(re.sub(r"[^0-9]", "", v))
        if not (10 <= digit_count <= 15):
            raise ValueError("Phone number must contain 10-15 digits")
        
        return v.strip()


class TenantUpdate(TenantBaseOptional):
    full_name: str | None = None

    @model_validator(mode="before")
    @classmethod
    def split_full_name_update(cls, data: dict) -> dict:
        """
        Splits a 'full_name' field into 'first_name' and 'last_name' if they are not already provided.
        
        If 'full_name' exists in the input dictionary and neither 'first_name' nor 'last_name' are present,
        the function splits 'full_name' at the first space and assigns the resulting parts to 'first_name'
        and 'last_name' respectively. The 'full_name' key is removed from the dictionary.
        """
        if (
            not isinstance(data, dict)
            or "full_name" not in data
            or not data["full_name"]
        ):
            return data

        full_name = data.pop("full_name")

        if data.get("first_name") is not None or data.get("last_name") is not None:
            return data

        names = full_name.split(" ", 1)
        data["first_name"] = names[0]
        data["last_name"] = names[1] if len(names) > 1 else data.get("last_name")

        return data


class TenantResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: str | None = None
    email: str | None = None
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
    current_property_id: int | None = None
    # Add fields for unit and property
    unit: UnitResponseSimple | None = None
    property: PropertyResponseSimple | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def full_name(self) -> str:
        """
        Returns the tenant's full name as a single string.
        
        Concatenates the first and last names with a space and trims any leading or trailing whitespace.
        """
        return f"{self.first_name} {self.last_name}".strip()
