"""
Base schemas and utilities for property type-specific data.
Provides shared base classes and validators for all property types.
Aligned with hierarchical database tables.
"""
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PropertyTypeDetailsBase(BaseModel):
    """Base schema for all property type details"""
    model_config = ConfigDict(
        from_attributes=True, 
        use_enum_values=True,
        json_encoders={
            Decimal: lambda v: float(v)
        }
    )


class PropertyTypeValidators:
    """Shared validators for property type fields"""
    
    @staticmethod
    def validate_percentage(value: Optional[Decimal], field_name: str) -> Optional[Decimal]:
        """Validate percentage fields are between 0 and 100"""
        if value is not None and (value < 0 or value > 100):
            raise ValueError(f"{field_name} must be between 0 and 100")
        return value
    
    @staticmethod
    def validate_positive_number(value: Optional[int], field_name: str) -> Optional[int]:
        """Validate that numeric fields are positive"""
        if value is not None and value < 0:
            raise ValueError(f"{field_name} must be a positive number")
        return value
    
    @staticmethod
    def validate_email(value: Optional[str]) -> Optional[str]:
        """Basic email validation"""
        if value and '@' not in value:
            raise ValueError("Invalid email format")
        return value
    
    @staticmethod
    def validate_phone(value: Optional[str]) -> Optional[str]:
        """Basic phone validation - accepts various formats"""
        if value:
            # Remove common formatting characters
            cleaned = value.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').replace('+', '')
            if not cleaned.isdigit() or len(cleaned) < 10:
                raise ValueError("Invalid phone number format")
        return value