from pydantic import BaseModel
from decimal import Decimal


class MonthlyChartData(BaseModel):
    months: list[str]
    rental_income: list[Decimal]
    other_income: list[Decimal]
    expenses: list[Decimal]


class ReportSummary(BaseModel):
    total_monthly_revenue: Decimal  # Revenue for the last month of the period
    avg_rent: Decimal
    # Skipping portfolio_value and change_pct for now as calculation is ambiguous
    # portfolio_value: float
    # change_pct: float


class FinancialTableRow(BaseModel):
    property: str
    property_id: int  # Added for potential linking
    units: int
    occupied_units: int
    occupancy_rate: Decimal  # e.g., "85%"
    monthly_revenue: Decimal
    avg_rent: Decimal
    expenses: Decimal
    net_income: Decimal


class IncomeByProperty(BaseModel):
    property: str
    property_id: int  # Added for potential linking
    monthly_income: Decimal  # Income for the last month of the period
    occupancy_rate: Decimal  # Percentage 0-100


class ReportResponse(BaseModel):
    monthly_chart: MonthlyChartData
    summary: ReportSummary
    financial_table: list[FinancialTableRow]
    income_by_property: list[IncomeByProperty]

