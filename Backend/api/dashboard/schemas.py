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


# Tenant Dashboard Schemas
class TenantMyUnitSection(BaseModel):
    unit_id: int
    unit_name: str
    property_id: int
    property_name: str
    full_address: str
    lease_start: date
    lease_end: date


class TenantMonthlyRentSection(BaseModel):
    amount: str
    rent_due_day: int
    has_active_lease: bool
    last_payment_date: str


class TenantNextPaymentSection(BaseModel):
    # Balance info (actual outstanding balance, not just monthly rent)
    current_balance: str
    current_balance_cents: int

    # Due date info
    due_date: str
    days_remaining: int

    # Status flags
    is_overdue: bool
    is_paid: bool

    # Autopay info
    has_autopay: bool
    autopay_status: str  # "not_enrolled", "active", "paused", "canceled"
    next_autopay_date: str | None = None


class TenantMaintenanceSection(BaseModel):
    open_requests: int
    last_updated: str


class TenantDashboardResponse(BaseModel):
    my_unit: TenantMyUnitSection
    monthly_rent: TenantMonthlyRentSection
    next_payment: TenantNextPaymentSection
    maintenance: TenantMaintenanceSection

