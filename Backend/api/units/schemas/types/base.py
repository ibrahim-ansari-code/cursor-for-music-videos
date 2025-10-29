"""
Base schema for unit type-specific details.
Provides common structure for all unit type detail schemas.
"""
from pydantic import BaseModel, ConfigDict


class UnitTypeDetailsBase(BaseModel):
    """
    Base class for all unit type-specific detail schemas.

    This provides the foundation for type-specific unit details
    that are stored in the unit_type_details JSONB column.
    """

    model_config = ConfigDict(
        # Allow reading from ORM models
        from_attributes=True,
        # Use enum values in JSON
        use_enum_values=True,
        # Validate on assignment
        validate_assignment=True,
        # Be strict about extra fields
        extra="forbid"
    )
