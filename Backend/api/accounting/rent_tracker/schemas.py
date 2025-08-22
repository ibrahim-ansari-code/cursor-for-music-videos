"""
Pydantic schemas for rent tracker functionality.
"""
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RentStatus(str, Enum):
    """Enumeration of possible rent payment statuses."""
    PAID = "PAID"
    PARTIAL = "PARTIAL"
    DUE = "DUE"
    OVERDUE = "OVERDUE"


class RentTrackingEntry(BaseModel):
    """
    Represents a single rent tracking entry for a lease.
    
    Contains payment information for a specific lease during a given month,
    including amounts paid, amounts due, and payment status.
    """
    lease_id: int = Field(..., description="Unique identifier of the lease")
    tenant_id: Optional[int] = Field(None, description="Unique identifier of the tenant")
    tenant_name: str = Field(..., description="Full name of the tenant")
    property_name: str = Field(..., description="Name of the property")
    unit_name: Optional[str] = Field(None, description="Name/number of the unit if applicable")
    monthly_rent: Decimal = Field(..., description="Monthly rent amount for the lease")
    amount_paid: Decimal = Field(..., description="Total amount paid for the period")
    remaining_due: Decimal = Field(..., description="Remaining amount due for the period")
    status: RentStatus = Field(..., description="Current payment status")
    due_date: Optional[date] = Field(None, description="Rent due date for the period")
    last_payment_date: Optional[date] = Field(None, description="Date of the most recent payment")
    days_overdue: Optional[int] = Field(None, description="Number of days overdue if applicable")

    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('monthly_rent', 'amount_paid', 'remaining_due')
    @classmethod
    def validate_monetary_amounts(cls, v: Decimal) -> Decimal:
        """Ensure monetary amounts are non-negative and within reasonable precision."""
        if v < 0:
            raise ValueError('Monetary amounts must be non-negative')
        
        # Check for reasonable upper limit (prevent unrealistic values)
        if v > Decimal('99999999.99'):  # 8 digits + 2 decimal places
            raise ValueError('Monetary amount exceeds maximum allowed value')
        
        # Validate decimal precision (max 2 decimal places)
        exponent = v.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -2:
            raise ValueError('Monetary amounts cannot have more than 2 decimal places')
        
        return v
    
    @field_validator('days_overdue')
    @classmethod
    def validate_days_overdue(cls, v: Optional[int]) -> Optional[int]:
        """Ensure days overdue is non-negative when provided."""
        if v is not None and v < 0:
            raise ValueError('Days overdue must be non-negative')
        return v


class RentTrackerSummary(BaseModel):
    """
    Summary statistics for rent tracking across all properties or a specific property.
    """
    total_units: int = Field(..., description="Total number of units being tracked")
    total_expected: Decimal = Field(..., description="Total expected rent for the period")
    total_collected: Decimal = Field(..., description="Total amount collected for the period")
    total_outstanding: Decimal = Field(..., description="Total amount outstanding for the period")
    
    # Status breakdown
    units_paid: int = Field(..., description="Number of units with rent fully paid")
    units_partial: int = Field(..., description="Number of units with partial payment")
    units_due: int = Field(..., description="Number of units with rent due")
    units_overdue: int = Field(..., description="Number of units with overdue rent")
    
    # Collection rate
    collection_rate: Decimal = Field(..., description="Percentage of rent collected")
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('total_expected', 'total_collected', 'total_outstanding')
    @classmethod
    def validate_positive_amounts(cls, v: Decimal) -> Decimal:
        """Ensure monetary amounts are non-negative."""
        if v < 0:
            raise ValueError('Monetary amounts must be non-negative')
        return v
    
    @field_validator('units_paid', 'units_partial', 'units_due', 'units_overdue', 'total_units')
    @classmethod
    def validate_positive_counts(cls, v: int) -> int:
        """Ensure unit counts are non-negative."""
        if v < 0:
            raise ValueError('Unit counts must be non-negative')
        return v
    
    @field_validator('collection_rate')
    @classmethod
    def validate_collection_rate(cls, v: Decimal) -> Decimal:
        """Ensure collection rate is between 0 and 100."""
        if v < 0 or v > 100:
            raise ValueError('Collection rate must be between 0 and 100')
        return v


class RentTrackerFilter(BaseModel):
    """
    Filter parameters for rent tracker queries.
    """
    month: Optional[int] = Field(None, ge=1, le=12, description="Month (1-12)")
    year: Optional[int] = Field(None, ge=2000, le=2100, description="Year")
    property_id: Optional[int] = Field(None, description="Filter by specific property")
    status: Optional[RentStatus] = Field(None, description="Filter by payment status")
    include_vacant: bool = Field(False, description="Include vacant units in the results")
    
    model_config = ConfigDict(from_attributes=True)