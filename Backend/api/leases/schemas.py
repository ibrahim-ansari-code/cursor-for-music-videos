from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID as PythonUUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from Backend.models.lease import LeaseStatus

# Import the actual models instead of using TYPE_CHECKING
from Backend.models.property import Property
from Backend.models.tenant import Tenant


class LeaseBase(BaseModel):
    start_date: date
    end_date: date
    monthly_rent: Decimal
    security_deposit: Decimal
    is_renewable: bool = True
    auto_renew: bool = False
    rent_due_day: int = 1
    late_fee_amount: Decimal | None = None
    late_fee_after_days: int | None = None
    special_terms: str | None = None
    property_id: int
    unit_id: int | None = None
    tenant_id: int

    @field_validator('rent_due_day')
    @classmethod
    def validate_rent_due_day(cls, v: int) -> int:
        if not 1 <= v <= 31:
            raise ValueError('rent_due_day must be between 1 and 31')
        return v

    @model_validator(mode='after')
    def validate_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError('end_date must be after start_date')
        return self


class LeaseCreate(LeaseBase):
    status: LeaseStatus | None = LeaseStatus.DRAFT
    file_url: str | None = None

    # Validation is inherited from LeaseBase - no need to duplicate


class LeaseUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    monthly_rent: Decimal | None = None
    security_deposit: Decimal | None = None
    rent_due_day: int | None = None
    late_fee_amount: Decimal | None = None
    late_fee_after_days: int | None = None
    special_terms: str | None = None


class LeaseResponse(LeaseBase):
    id: int
    status: LeaseStatus
    created_at: datetime
    updated_at: datetime
    tenant: Optional[Tenant] = None
    property: Optional[Property] = None

    model_config = ConfigDict(from_attributes=True)


class LeaseDocumentResponse(BaseModel):
    id: int
    name: str
    file_path: str
    document_type: str
    upload_date: datetime
    uploaded_by_id: PythonUUID | None = None

    model_config = ConfigDict(from_attributes=True)


class LeaseAnalysisResponse(BaseModel):
    monthly_rent: Decimal
    start_date: date | None = None
    end_date: date | None = None
    security_deposit: Decimal
    late_fee_amount: Decimal | None = None
    tenant_name: str | None = None
    unit: str | None = None


class LeaseUploadResponse(BaseModel):
    file_url: str


# Rebuild the LeaseResponse model to resolve forward references
LeaseResponse.model_rebuild()
