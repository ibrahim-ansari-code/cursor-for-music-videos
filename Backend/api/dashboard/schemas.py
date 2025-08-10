from datetime import date
from decimal import Decimal
from pydantic import BaseModel

from Backend.models.accounting.common import PaymentStatus


class DashboardSummary(BaseModel):
    total_properties: int
    total_units: int
    occupied_units: int
    vacancy_rate: Decimal
    monthly_revenue: Decimal
    monthly_expenses: Decimal
    outstanding_rent: Decimal
    maintenance_expenses: Decimal


class OccupancyData(BaseModel):
    total_units: int
    occupied_units: int
    vacant_units: int
    occupancy_rate: Decimal


class RevenueData(BaseModel):
    months: list[str]
    revenue: list[Decimal]
    expenses: list[Decimal]
    net_income: list[Decimal]


class PaymentDue(BaseModel):
    id: int
    tenant_name: str
    amount: Decimal
    due_date: date
    days_overdue: int | None = None
    status: PaymentStatus


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    occupancy: OccupancyData
    revenue: RevenueData
    payments_due: list[PaymentDue]


