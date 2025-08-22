import logging
import re
import functools
from datetime import date, datetime, UTC
from typing import Any
from enum import Enum
from decimal import Decimal

# Compile regex pattern once at module level for performance
_TABLE_ALIAS_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.enums import UserType
from Backend.models.user import User
# Property model might be needed if check_property_ownership is used, but queries are raw SQL
# from Backend.models.property import Property 
# from .helpers import check_property_ownership # Not used by current raw SQL queries directly

logger = logging.getLogger(__name__)
router = APIRouter()

# === Filter Type Enum for Type Safety ===

class FilterType(str, Enum):
    """Enum for ownership filter types to improve type safety and reduce typos."""
    LANDLORD_OWNED = "landlord_owned"
    LANDLORD_PROPERTY_SPECIFIC = "landlord_property_specific"
    ADMIN_PROPERTY_SPECIFIC = "admin_property_specific"
    EMPTY = "empty"

class Period(str, Enum):
    """Enum for time period types in revenue trend analysis."""
    MONTHLY = "monthly"
    YEARLY = "yearly"

# === SQL Query Constants ===

# Base ownership filter patterns with placeholder for table alias
# Consolidated patterns to eliminate duplication between payment/expense contexts
_OWNERSHIP_FILTER_PATTERNS = {
    FilterType.LANDLORD_OWNED: "AND {table_alias}.user_id = :user_id",
    FilterType.LANDLORD_PROPERTY_SPECIFIC: "AND {table_alias}.user_id = :user_id AND {table_alias}.id = :property_id_filter",
    FilterType.ADMIN_PROPERTY_SPECIFIC: "AND {table_alias}.id = :property_id_filter",
    FilterType.EMPTY: ""
}

def _build_safe_ownership_filter(filter_type: FilterType, table_alias: str = "prop") -> str:
    """
    Constructs a validated SQL ownership filter fragment using a specified filter type and table alias.
    
    Ensures the filter type is a valid FilterType enum member and the table alias matches strict naming rules to prevent SQL injection. Returns a safe SQL fragment with the table alias substituted.
    
    Args:
        filter_type: The ownership filter type to apply.
        table_alias: The SQL table alias to use in the filter (must start with a letter and contain only letters, digits, or underscores).
    
    Returns:
        A SQL filter fragment string with the specified table alias.
    
    Raises:
        ValueError: If the filter type is invalid or the table alias does not meet naming requirements.
    """
    if not isinstance(filter_type, FilterType):
        raise TypeError("filter_type must be a FilterType enum member.")
    
    # Validate table_alias to prevent SQL injection - only allow letters, digits, underscores
    # Must start with letter only (a-z or A-Z), followed by letters, digits, or underscores
    if not _TABLE_ALIAS_PATTERN.match(table_alias):
        raise ValueError(f"Invalid table alias '{table_alias}'. Must contain only letters, digits, and underscores, starting with a letter.")
    
    pattern = _OWNERSHIP_FILTER_PATTERNS[filter_type]
    return pattern.format(table_alias=table_alias)

# Base SQL query templates with bindparam placeholders
_MONTHLY_REVENUE_TRENDS_BASE = """
WITH months AS (SELECT generate_series(1, 12) AS month_num),
payment_data AS (
    SELECT EXTRACT(MONTH FROM p.payment_date) AS month_num, SUM(p.amount) AS revenue
    FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id
    WHERE EXTRACT(YEAR FROM p.payment_date) = :target_year AND p.status IN ('Paid', 'Partial') {payments_filter}
    GROUP BY EXTRACT(MONTH FROM p.payment_date)
),
expense_data AS (
    SELECT EXTRACT(MONTH FROM e.expense_date) AS month_num, SUM(e.subtotal_amount) AS expenses
    FROM expenses e JOIN properties exp_prop ON e.property_id = exp_prop.id
    WHERE EXTRACT(YEAR FROM e.expense_date) = :target_year {expenses_filter}
    GROUP BY EXTRACT(MONTH FROM e.expense_date)
)
SELECT m.month_num, COALESCE(pd.revenue, 0) AS revenue, COALESCE(ed.expenses, 0) AS expenses
FROM months m 
LEFT JOIN payment_data pd ON m.month_num = pd.month_num 
LEFT JOIN expense_data ed ON m.month_num = ed.month_num
ORDER BY m.month_num
"""

_YEARLY_REVENUE_TRENDS_BASE = """
WITH years AS (SELECT generate_series(:start_year, :end_year) AS year_num),
payment_data AS (
    SELECT EXTRACT(YEAR FROM p.payment_date) AS year_num, SUM(p.amount) AS revenue
    FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id
    WHERE p.status IN ('Paid', 'Partial') {payments_filter}
    GROUP BY EXTRACT(YEAR FROM p.payment_date)
),
expense_data AS (
    SELECT EXTRACT(YEAR FROM e.expense_date) AS year_num, SUM(e.subtotal_amount) AS expenses
    FROM expenses e JOIN properties exp_prop ON e.property_id = exp_prop.id
    WHERE 1=1 {expenses_filter}
    GROUP BY EXTRACT(YEAR FROM e.expense_date)
)
SELECT y.year_num, COALESCE(pd.revenue, 0) AS revenue, COALESCE(ed.expenses, 0) AS expenses
FROM years y 
LEFT JOIN payment_data pd ON y.year_num = pd.year_num 
LEFT JOIN expense_data ed ON y.year_num = ed.year_num
ORDER BY y.year_num
"""

_OVERVIEW_REVENUE_TRENDS_BASE = """
WITH month_series AS (
    SELECT date_trunc('month', generate_series(date_trunc('month', current_date - interval '11 months'), current_date, interval '1 month'))::date as period_start
),
payment_agg AS (
    SELECT date_trunc('month', p.payment_date)::date as period_start, SUM(p.amount) AS revenue
    FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id
    WHERE p.status IN ('Paid', 'Partial') {payments_filter} AND p.payment_date >= date_trunc('month', current_date - interval '11 months')
    GROUP BY 1
),
expense_agg AS (
    SELECT date_trunc('month', e.expense_date)::date as period_start, SUM(e.subtotal_amount) AS expenses
    FROM expenses e JOIN properties exp_prop ON e.property_id = exp_prop.id
    WHERE 1=1 {expenses_filter} AND e.expense_date >= date_trunc('month', current_date - interval '11 months')
    GROUP BY 1
)
SELECT to_char(ms.period_start, 'Mon YY') as period_label, 
       COALESCE(pa.revenue, 0) AS revenue, 
       COALESCE(exa.expenses, 0) AS expenses
FROM month_series ms
LEFT JOIN payment_agg pa ON ms.period_start = pa.period_start
LEFT JOIN expense_agg exa ON ms.period_start = exa.period_start
ORDER BY ms.period_start
"""

@functools.lru_cache(maxsize=64)
def _build_safe_sql_query(base_query: str, payments_filter: str, expenses_filter: str) -> TextClause:
    """
    Constructs a SQLAlchemy TextClause by injecting validated filter fragments into a base SQL query template.
    
    The resulting query is safe for execution, as filter fragments must be pre-validated to prevent SQL injection. This function is cached to optimize performance for frequently used query patterns.
    
    Args:
        base_query: SQL query template containing `{payments_filter}` and `{expenses_filter}` placeholders.
        payments_filter: Pre-validated SQL fragment for filtering payments.
        expenses_filter: Pre-validated SQL fragment for filtering expenses.
    
    Returns:
        A SQLAlchemy TextClause object representing the formatted query.
    """
    return text(base_query.format(
        payments_filter=payments_filter,
        expenses_filter=expenses_filter
    ))

# === API Models for Insights ===
class OccupancyResponse(BaseModel):
    property_id: int | None = None
    property_name: str | None = None
    total_units: int
    occupied_units: int
    vacant_units: int
    occupancy_rate: Decimal

class RevenueTrendResponse(BaseModel):
    period: str  # Month or year
    revenue: Decimal
    expenses: Decimal
    net_income: Decimal

class AccountingOverviewResponse(BaseModel):
    monthly_revenue: Decimal
    monthly_expenses: Decimal
    monthly_net_income: Decimal
    ytd_revenue: Decimal
    ytd_expenses: Decimal
    ytd_net_income: Decimal
    occupancy_rate: Decimal
    outstanding_payments: int
    average_rent: Decimal
    revenue_trends: list[RevenueTrendResponse]

# === API Endpoints for Insights ===

@router.get("/occupancy", response_model=list[OccupancyResponse])
async def get_occupancy_rates(
    property_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[OccupancyResponse]:
    """
    Retrieves occupancy rates for properties accessible to the current user.
    
    Returns a list of occupancy statistics per property, including total, occupied, and vacant units, as well as occupancy rate. Results are filtered based on user role (admin or landlord) and, if provided, a specific property ID.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Base query using text() for safe construction
    base_query_text = """
    SELECT 
        p.id as property_id, p.name as property_name, p.user_id as owner_user_id,
        COUNT(u.id) as total_units,
        SUM(CASE WHEN u.is_rented THEN 1 ELSE 0 END) as occupied_units
    FROM properties p
    LEFT JOIN property_units u ON p.id = u.property_id
    WHERE 1=1 {property_filter}
    GROUP BY p.id, p.name, p.user_id
    ORDER BY p.name
    """
    
    params: dict[str, Any] = {}
    
    # Determine safe property filter type using enum
    property_filter_type = FilterType.EMPTY
    
    if current_user.user_type == UserType.LANDLORD:
        params["user_id"] = current_user.id
        if property_id: # Landlord requests specific owned property
            property_filter_type = FilterType.LANDLORD_PROPERTY_SPECIFIC
            params["property_id_filter"] = property_id
        else:
            property_filter_type = FilterType.LANDLORD_OWNED
    elif current_user.user_type == UserType.ADMIN:
        if property_id: # Admin requests specific property
            property_filter_type = FilterType.ADMIN_PROPERTY_SPECIFIC
            params["property_id_filter"] = property_id
    
    # Use unified filter building with "p" alias for properties table
    prop_filter_sql = _build_safe_ownership_filter(property_filter_type, table_alias="p")
    
    # Build safe query using text()
    query = text(base_query_text.format(property_filter=prop_filter_sql))
    result = await session.execute(query, params)
    occupancy_data = result.mappings().all()

    response_list = []
    for row in occupancy_data:
        total = row['total_units'] or 0
        occupied = row['occupied_units'] or 0
        vacant = total - occupied
        rate = (Decimal(occupied) / Decimal(total) * 100) if total > 0 else Decimal('0.0')
        response_list.append(
            OccupancyResponse(
                property_id=row['property_id'], property_name=row['property_name'],
                total_units=total, occupied_units=occupied, vacant_units=vacant, occupancy_rate=rate
            )
        )
    return response_list

@router.get("/revenue-trends", response_model=list[RevenueTrendResponse])
async def get_revenue_trends(
    period_type: Period = Period.MONTHLY, year: int | None = None,
    property_id: int | None = None, session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[RevenueTrendResponse]:
    """
    Retrieves revenue, expenses, and net income trends for properties, grouped by month or year.
    
    Only users with ADMIN or LANDLORD roles can access this endpoint. The trends can be filtered by a specific property and year. Results are grouped by month for monthly trends or by year for yearly trends, and include revenue, expenses, and calculated net income for each period.
    
    Args:
        period_type: The aggregation period for trends (monthly or yearly).
        year: The target year for monthly trends or the end year for yearly trends. Defaults to the current year if not provided.
        property_id: Optional property ID to filter results to a specific property.
    
    Returns:
        A list of RevenueTrendResponse objects, each representing revenue, expenses, and net income for a period.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    current_year = datetime.now(UTC).year
    target_year = year or current_year

    # Determine safe ownership filter types using enum
    payment_filter_type = FilterType.EMPTY
    expense_filter_type = FilterType.EMPTY
    params: dict[str, Any] = {"target_year": target_year} if period_type == Period.MONTHLY else {"start_year": target_year - 4, "end_year": target_year}

    if current_user.user_type == UserType.LANDLORD:
        params["user_id"] = current_user.id
        if property_id:
            payment_filter_type = FilterType.LANDLORD_PROPERTY_SPECIFIC
            expense_filter_type = FilterType.LANDLORD_PROPERTY_SPECIFIC
            params["property_id_filter"] = property_id
        else:
            payment_filter_type = FilterType.LANDLORD_OWNED
            expense_filter_type = FilterType.LANDLORD_OWNED
    elif current_user.user_type == UserType.ADMIN:
        if property_id:
            payment_filter_type = FilterType.ADMIN_PROPERTY_SPECIFIC
            expense_filter_type = FilterType.ADMIN_PROPERTY_SPECIFIC
            params["property_id_filter"] = property_id

    if period_type == Period.MONTHLY:
        # Build safe filters with appropriate table aliases
        payments_filter = _build_safe_ownership_filter(payment_filter_type, table_alias="prop")
        expenses_filter = _build_safe_ownership_filter(expense_filter_type, table_alias="exp_prop")
        
        # Build safe query using text()
        query = _build_safe_sql_query(_MONTHLY_REVENUE_TRENDS_BASE, payments_filter, expenses_filter)
        result = await session.execute(query, params)
        trends_data = result.mappings().all()
        
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return [
            RevenueTrendResponse(
                period=month_names[int(row['month_num'])-1] + f" {target_year % 100}", # e.g. Jan 23
                revenue=Decimal(row['revenue']), expenses=Decimal(row['expenses']),
                net_income=Decimal(row['revenue']) - Decimal(row['expenses'])
            ) for row in trends_data
        ]
        
    if period_type == Period.YEARLY:
        # Build safe filters with appropriate table aliases
        payments_filter = _build_safe_ownership_filter(payment_filter_type, table_alias="prop")
        expenses_filter = _build_safe_ownership_filter(expense_filter_type, table_alias="exp_prop")
        
        # Build safe query using text()
        query = _build_safe_sql_query(_YEARLY_REVENUE_TRENDS_BASE, payments_filter, expenses_filter)
        result = await session.execute(query, params)
        trends_data = result.mappings().all()
        
        return [
            RevenueTrendResponse(
                period=str(int(row['year_num'])), revenue=Decimal(row['revenue']), expenses=Decimal(row['expenses']),
                net_income=Decimal(row['revenue']) - Decimal(row['expenses'])
            ) for row in trends_data
        ]
    # Defensive: should never reach here due to earlier check
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unhandled period_type logic.")

@router.get("/overview", response_model=AccountingOverviewResponse)
async def get_accounting_overview(
    property_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> AccountingOverviewResponse:
    """
    Retrieves a comprehensive accounting overview for the current user.
    
    Returns aggregated financial and occupancy metrics for the current month and year-to-date, including revenue, expenses, net income, occupancy rate, outstanding payments, average rent, and revenue trends for the last 12 months. Only accessible to admin and landlord users.
    
    Args:
        property_id: Optional property ID to filter results to a specific property. Landlords can only filter their owned properties, while admins can filter any property.
    
    Returns:
        An AccountingOverviewResponse containing all aggregated metrics and revenue trends.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    today = datetime.now(UTC).date()
    year_start = date(today.year, 1, 1)
    month_start = date(today.year, today.month, 1)
    
    base_params: dict[str, Any] = {"month_start": month_start, "year_start": year_start, "today": today}
    
    # Determine the correct filter type based on user role and property_id parameter
    filter_type = FilterType.EMPTY
    
    if current_user.user_type == UserType.LANDLORD:
        base_params["user_id"] = current_user.id
        if property_id:  # Landlord requests specific owned property
            filter_type = FilterType.LANDLORD_PROPERTY_SPECIFIC
            base_params["property_id_filter"] = property_id
        else:
            filter_type = FilterType.LANDLORD_OWNED
    elif current_user.user_type == UserType.ADMIN:
        if property_id:  # Admin requests specific property
            filter_type = FilterType.ADMIN_PROPERTY_SPECIFIC
            base_params["property_id_filter"] = property_id

    # Build safe, reusable filter strings for different table aliases
    payments_filter = _build_safe_ownership_filter(filter_type, table_alias="prop")
    expenses_filter = _build_safe_ownership_filter(filter_type, table_alias="exp_prop")
    leases_filter = _build_safe_ownership_filter(filter_type, table_alias="prop")
    units_filter = _build_safe_ownership_filter(filter_type, table_alias="prop")
    
    # Static JOIN clauses with dynamic WHERE clauses via the validated filter strings
    # Monthly Revenue
    mr_q_str = f"SELECT COALESCE(SUM(p.amount), 0.0)::numeric FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id WHERE p.payment_date >= :month_start AND p.payment_date <= :today AND p.status IN ('Paid', 'Partial') {payments_filter}"
    mr_q = text(mr_q_str)
    monthly_revenue = await session.scalar(mr_q, base_params) or Decimal("0.0")
    # YTD Revenue
    yr_q_str = f"SELECT COALESCE(SUM(p.amount), 0.0)::numeric FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id WHERE p.payment_date >= :year_start AND p.payment_date <= :today AND p.status IN ('Paid', 'Partial') {payments_filter}"
    yr_q = text(yr_q_str)
    ytd_revenue = await session.scalar(yr_q, base_params) or Decimal("0.0")
    # Monthly Expenses
    me_q_str = f"SELECT COALESCE(SUM(e.subtotal_amount), 0.0)::numeric FROM expenses e JOIN properties exp_prop ON e.property_id = exp_prop.id WHERE e.expense_date >= :month_start AND e.expense_date <= :today {expenses_filter}"
    me_q = text(me_q_str)
    monthly_expenses = await session.scalar(me_q, base_params) or Decimal("0.0")
    # YTD Expenses
    ye_q_str = f"SELECT COALESCE(SUM(e.subtotal_amount), 0.0)::numeric FROM expenses e JOIN properties exp_prop ON e.property_id = exp_prop.id WHERE e.expense_date >= :year_start AND e.expense_date <= :today {expenses_filter}"
    ye_q = text(ye_q_str)
    ytd_expenses = await session.scalar(ye_q, base_params) or Decimal("0.0")
    # Outstanding Payments (count for current month)
    op_q_str = f"SELECT COUNT(p.id) FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id WHERE p.payment_date >= :month_start AND p.payment_date <= :today AND p.status IN ('Pending', 'Overdue') {payments_filter}"
    op_q = text(op_q_str)
    outstanding_payments = await session.scalar(op_q, base_params) or 0
    # Average Rent (active leases)
    ar_q_str = f"SELECT COALESCE(AVG(l.monthly_rent), 0.0)::numeric FROM leases l JOIN properties prop ON l.property_id = prop.id WHERE l.status = 'ACTIVE' {leases_filter}"
    ar_q = text(ar_q_str)
    average_rent = await session.scalar(ar_q, base_params) or Decimal("0.0")
    # Occupancy Rate
    ocr_q_str = f"SELECT CASE WHEN COUNT(u.id) > 0 THEN CAST(SUM(CASE WHEN u.is_rented THEN 1 ELSE 0 END) AS NUMERIC) / COUNT(u.id) * 100 ELSE 0 END FROM property_units u JOIN properties prop ON u.property_id = prop.id WHERE 1=1 {units_filter}"
    ocr_q = text(ocr_q_str)
    occupancy_rate = await session.scalar(ocr_q, base_params) or Decimal('0.0')

    # Revenue Trends (last 12 months including current) - using same filter logic as main overview
    trend_params_rt: dict[str, Any] = {}
    
    # Use the same filter type as the main overview calculations
    trend_payment_filter_type = filter_type
    trend_expense_filter_type = filter_type
    
    # Copy the same parameters used for main queries
    if current_user.user_type == UserType.LANDLORD:
        trend_params_rt["user_id"] = current_user.id
        if property_id:
            trend_params_rt["property_id_filter"] = property_id
    elif current_user.user_type == UserType.ADMIN:
        if property_id:
            trend_params_rt["property_id_filter"] = property_id
    
    # Build safe filters with appropriate table aliases
    payments_filter_rt = _build_safe_ownership_filter(trend_payment_filter_type, table_alias="prop")
    expenses_filter_rt = _build_safe_ownership_filter(trend_expense_filter_type, table_alias="exp_prop")

    # Build safe query using text()
    trends_query = _build_safe_sql_query(_OVERVIEW_REVENUE_TRENDS_BASE, payments_filter_rt, expenses_filter_rt)
    trends_result = await session.execute(trends_query, trend_params_rt)
    revenue_trends_list = [
        RevenueTrendResponse(period=row.period_label, revenue=Decimal(row.revenue), expenses=Decimal(row.expenses),
                           net_income=Decimal(row.revenue) - Decimal(row.expenses))
        for row in trends_result.mappings().all()
    ]

    return AccountingOverviewResponse(
        monthly_revenue=Decimal(monthly_revenue), monthly_expenses=Decimal(monthly_expenses),
        monthly_net_income=Decimal(monthly_revenue) - Decimal(monthly_expenses),
        ytd_revenue=Decimal(ytd_revenue), ytd_expenses=Decimal(ytd_expenses),
        ytd_net_income=Decimal(ytd_revenue) - Decimal(ytd_expenses),
        occupancy_rate=occupancy_rate, outstanding_payments=int(outstanding_payments),
        average_rent=Decimal(average_rent), revenue_trends=revenue_trends_list
    )
