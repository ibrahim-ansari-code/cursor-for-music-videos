import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.accounting.common import PaymentStatus
from Backend.models.enums import UserType
from Backend.models.user import User
from Backend.utils.datetime_utils import date_to_utc_range

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)

# API models


class DashboardSummary(BaseModel):
    total_properties: int
    total_units: int
    occupied_units: int
    vacancy_rate: float  # percentage
    monthly_revenue: float
    monthly_expenses: float
    outstanding_rent: float
    maintenance_expenses: float


class OccupancyData(BaseModel):
    total_units: int
    occupied_units: int
    vacant_units: int
    occupancy_rate: float  # percentage


class RevenueData(BaseModel):
    months: list[str]
    revenue: list[float]
    expenses: list[float]
    net_income: list[float]


class PaymentDue(BaseModel):
    id: int
    tenant_name: str
    amount: float
    due_date: date
    days_overdue: int | None = None
    status: PaymentStatus


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    occupancy: OccupancyData
    revenue: RevenueData
    payments_due: list[PaymentDue]

# API endpoints


@router.get("", response_model=DashboardResponse)
async def get_dashboard_data(
    property_id: int | None = None,
    time_period: str = "month",  # Options: week, month, quarter, year
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> DashboardResponse:
    """
    Retrieves aggregated dashboard data for real estate management, including property statistics, occupancy rates, financial summaries, revenue trends, and outstanding payments.
    
    Only users with ADMIN or LANDLORD roles can access this endpoint. The response includes summary metrics, occupancy details, revenue and expense trends for the past 12 months, and up to five pending or overdue payments. Data can be filtered by property and time period ("week", "month", "quarter", or "year").
    
    Args:
        property_id: Optional; filters dashboard data to a specific property.
        time_period: Time range for summary calculations; accepts "week", "month", "quarter", or "year".
    
    Returns:
        DashboardResponse containing summary metrics, occupancy data, revenue trends, and a list of payments due.
    
    Raises:
        HTTPException: If the user does not have ADMIN or LANDLORD privileges.
    """
    # Convert user_type to uppercase for comparison
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access dashboard data"
        )

    # Define a filter for landlord's properties
    landlord_property_filter_sql = ""
    landlord_params = {}
    if current_user.user_type == UserType.LANDLORD:
        landlord_property_filter_sql = "AND p.user_id = :current_user_id"
        landlord_params["current_user_id"] = current_user.id

    # Calculate date range for filtering
    today = date.today()
    if time_period == "week":
        start_date = today - timedelta(days=7)
    elif time_period == "month":
        start_date = today - timedelta(days=30)
    elif time_period == "quarter":
        start_date = today - timedelta(days=90)
    elif time_period == "year":
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)  # Default to month

    # Convert to timezone-aware datetime range for business date filtering
    start_datetime, end_datetime = date_to_utc_range(start_date, today)

    # Generate mock data for dashboard
    # In a real application, this would query the database

    # 1. Summary data
    summary_query = """
    WITH property_counts AS (
        SELECT 
            COUNT(DISTINCT p.id) as total_properties,
            COUNT(u.id) as total_units,
            SUM(CASE WHEN u.is_rented THEN 1 ELSE 0 END) as occupied_units
        FROM 
            properties p
        LEFT JOIN 
            property_units u ON p.id = u.property_id
        WHERE 
            1=1
            {property_filter} {landlord_property_filter_sql}
    ),
    financial_summary AS (
        SELECT 
            COALESCE(SUM(CASE WHEN pay.status IN ('Paid', 'Partial') THEN pay.amount ELSE 0 END), 0) as monthly_revenue,
            COALESCE(SUM(CASE WHEN exp.category = 'maintenance' THEN exp.total_amount ELSE 0 END), 0) as maintenance_expenses,
            COALESCE(SUM(exp.total_amount), 0) as monthly_expenses,
            COALESCE(SUM(CASE WHEN inv.status IN ('Pending', 'Overdue') THEN inv.amount ELSE 0 END), 0) as outstanding_rent
        FROM 
            properties p
        LEFT JOIN 
            leases l ON p.id = l.property_id
        LEFT JOIN       
            tenants t ON l.tenant_id = t.id
        LEFT JOIN 
            payments pay ON l.id = pay.lease_id AND pay.payment_date BETWEEN :start_date AND :end_date
        LEFT JOIN 
            expenses exp ON p.id = exp.property_id AND exp.expense_date BETWEEN :start_date AND :end_date
        LEFT JOIN 
            invoices inv ON (p.id = inv.property_id OR t.id = inv.tenant_id)
                         AND inv.status IN ('Pending', 'Overdue')
        WHERE 
            1=1
            {property_filter} {landlord_property_filter_sql}
    )
    SELECT 
        pc.total_properties,
        pc.total_units,
        pc.occupied_units,
        CASE WHEN pc.total_units > 0 THEN 
            CAST((pc.total_units - pc.occupied_units) AS FLOAT) / pc.total_units * 100 
        ELSE 0 END as vacancy_rate,
        fs.monthly_revenue,
        fs.monthly_expenses,
        fs.outstanding_rent,
        fs.maintenance_expenses
    FROM 
        property_counts pc,
        financial_summary fs
    """

    property_filter = ""
    params = {
        "start_date": start_datetime,
        "end_date": end_datetime,
        **landlord_params
    }

    if property_id:
        property_filter = "AND p.id = :property_id"
        params["property_id"] = property_id
    else:
        property_filter = ""

    # Replace the placeholder
    summary_query = summary_query.format(
        property_filter=property_filter,
        landlord_property_filter_sql=landlord_property_filter_sql
    )

    summary_result = await session.execute(text(summary_query), params)
    summary_row = summary_result.mappings().one_or_none()

    if summary_row:
        summary = DashboardSummary(
            total_properties=summary_row['total_properties'] or 0,
            total_units=summary_row['total_units'] or 0,
            occupied_units=summary_row['occupied_units'] or 0,
            vacancy_rate=summary_row['vacancy_rate'] or 0.0,
            monthly_revenue=summary_row['monthly_revenue'] or 0.0,
            monthly_expenses=summary_row['monthly_expenses'] or 0.0,
            outstanding_rent=summary_row['outstanding_rent'] or 0.0,
            maintenance_expenses=summary_row['maintenance_expenses'] or 0.0
        )
    else:
        # Default values if no data
        summary = DashboardSummary(
            total_properties=0,
            total_units=0,
            occupied_units=0,
            vacancy_rate=0.0,
            monthly_revenue=0.0,
            monthly_expenses=0.0,
            outstanding_rent=0.0,
            maintenance_expenses=0.0
        )

    # 2. Occupancy data
    occupancy = OccupancyData(
        total_units=summary.total_units,
        occupied_units=summary.occupied_units,
        vacant_units=summary.total_units - summary.occupied_units,
        occupancy_rate=100.0 - summary.vacancy_rate
    )

    # 3. Revenue trends (last 12 months)
    revenue_query = """
    WITH months AS (
        SELECT generate_series(
            date_trunc('month', current_date - interval '11 months'),
            date_trunc('month', current_date),
            interval '1 month'
        )::date as month_start
    ),
    monthly_data AS (
        SELECT 
            date_trunc('month', m.month_start)::date as month,
            COALESCE(SUM(CASE WHEN pay.status IN ('Paid', 'Partial') THEN pay.amount ELSE 0 END), 0) as revenue,
            COALESCE(SUM(exp.total_amount), 0) as expenses
        FROM 
            months m
        LEFT JOIN 
            properties p ON 1=1 {property_filter} {landlord_property_filter_sql}
        LEFT JOIN 
            leases l ON p.id = l.property_id
        LEFT JOIN 
            payments pay ON l.id = pay.lease_id 
                        AND date_trunc('month', pay.payment_date) = m.month_start
        LEFT JOIN 
            expenses exp ON p.id = exp.property_id 
                        AND date_trunc('month', exp.expense_date) = m.month_start
        GROUP BY 
            m.month_start
        ORDER BY 
            m.month_start
    )
    SELECT 
        to_char(month, 'Mon') as month_name,
        revenue,
        expenses,
        revenue - expenses as net_income
    FROM 
        monthly_data
    """

    # Replace the placeholder
    revenue_query = revenue_query.format(
        property_filter=property_filter,
        landlord_property_filter_sql=landlord_property_filter_sql
    )

    revenue_result = await session.execute(text(revenue_query), params)
    revenue_rows = revenue_result.mappings().all()

    months = []
    revenue_values = []
    expense_values = []
    net_income_values = []

    for row in revenue_rows:
        months.append(row['month_name'])
        revenue_values.append(float(row['revenue']))
        expense_values.append(float(row['expenses']))
        net_income_values.append(float(row['net_income']))

    revenue_data = RevenueData(
        months=months,
        revenue=revenue_values,
        expenses=expense_values,
        net_income=net_income_values
    )

    # 4. Payments due
    payments_query = """
    SELECT 
        i.id,
        CONCAT(t.first_name, ' ', t.last_name) as tenant_name,
        i.amount,
        i.due_date,
        CASE 
            WHEN i.due_date < CURRENT_DATE THEN EXTRACT(DAY FROM (CURRENT_DATE - i.due_date))
            ELSE NULL
        END as days_overdue,
        i.status
    FROM 
        invoices i
    JOIN 
        tenants t ON i.tenant_id = t.id
    LEFT JOIN 
        properties p ON i.property_id = p.id
    WHERE 
        i.status IN ('Pending', 'Overdue')
        {property_filter} {landlord_property_filter_sql}
    ORDER BY 
        i.due_date ASC
    LIMIT 5
    """

    # Replace the placeholder
    payments_query = payments_query.format(
        property_filter=property_filter,
        landlord_property_filter_sql=landlord_property_filter_sql
    )

    payments_result = await session.execute(text(payments_query), params)
    payments_rows = payments_result.mappings().all()

    payments_due = []
    for row in payments_rows:
        payments_due.append(PaymentDue(
            id=row['id'],
            tenant_name=row['tenant_name'],
            amount=float(row['amount']),
            due_date=row['due_date'],
            days_overdue=row['days_overdue'],
            status=row['status']
        ))

    return DashboardResponse(
        summary=summary,
        occupancy=occupancy,
        revenue=revenue_data,
        payments_due=payments_due,
    )
