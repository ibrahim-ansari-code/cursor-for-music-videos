from pydantic import BaseModel


class MonthlyChartData(BaseModel):
    months: list[str]
    rental_income: list[float]
    other_income: list[float]
    expenses: list[float]


class ReportSummary(BaseModel):
    total_monthly_revenue: float  # Revenue for the last month of the period
    avg_rent: float
    # Skipping portfolio_value and change_pct for now as calculation is ambiguous
    # portfolio_value: float
    # change_pct: float


class FinancialTableRow(BaseModel):
    property: str
    property_id: int  # Added for potential linking
    units: int
    occupied_units: int
    occupancy_rate: str  # e.g., "85%"
    monthly_revenue: float
    avg_rent: float
    expenses: float
    net_income: float


class IncomeByProperty(BaseModel):
    property: str
    property_id: int  # Added for potential linking
    monthly_income: float  # Income for the last month of the period
    occupancy_rate: float  # Percentage 0-100


class ReportResponse(BaseModel):
    monthly_chart: MonthlyChartData
    summary: ReportSummary
    financial_table: list[FinancialTableRow]
    income_by_property: list[IncomeByProperty]
