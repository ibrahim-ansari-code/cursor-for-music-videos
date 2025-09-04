"""
Pydantic models for Tax Preferences API.

Defines request/response schemas for tax preference management endpoints.
"""

from decimal import Decimal
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator


class TaxPreferenceBase(BaseModel):
    """Base model for tax preference data."""
    tax_name: str = Field(description="Name of the tax (e.g., 'HST', 'GST', 'GST+PST')")
    tax_rate: Decimal = Field(
        description="Tax rate as percentage (0-100)",
        ge=Decimal('0'),
        le=Decimal('100')
    )
    
    @field_validator('tax_name')
    @classmethod
    def validate_tax_name_format(cls, v: str) -> str:
        """Validate Canadian tax name format."""
        from Backend.utils.tax_utils import validate_canadian_tax_name
        return validate_canadian_tax_name(v)

class TaxPreferenceCreate(TaxPreferenceBase):
    """Request model for creating/updating tax preferences."""
    pass


class TaxPreferenceResponse(TaxPreferenceBase):
    """Response model for tax preference data."""
    source: Literal["user_default", "property_default", "provincial_default", "historical_usage", "none"]
    
    model_config = {"from_attributes": True}


class SmartTaxRequest(BaseModel):
    """Request model for smart tax selection."""
    property_id: Optional[int] = Field(None, description="Property ID for context-aware tax selection")


class SmartTaxResponse(BaseModel):
    """Response model for smart tax selection."""
    tax_name: Optional[str] = Field(None, description="Recommended tax name")
    tax_rate: Optional[Decimal] = Field(None, description="Recommended tax rate")
    source: Literal["property_default", "provincial_default", "user_default", "historical_usage", "none"]
    confidence: float = Field(description="Confidence score (0.0-1.0)", ge=0.0, le=1.0)
    reasoning: str = Field(description="Human-readable explanation of the selection")


class HistoricalTaxUsage(BaseModel):
    """Response model for historical tax usage analysis."""
    tax_name: str
    tax_rate: Decimal
    usage_count: int
    last_used: Optional[str] = Field(None, description="ISO datetime of last usage")
    percentage: float = Field(description="Percentage of total usage", ge=0.0, le=100.0)