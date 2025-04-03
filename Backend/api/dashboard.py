import logging
from typing import List, Optional
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func, and_, or_, desc
from pydantic import BaseModel

from backend.database import get_session
from backend.models.user import User, UserType
from backend.models.property import Property, PropertyUnit
from backend.models.accounting import Payment, Invoice, Expense, PaymentStatus
from backend.models.lease import Lease, LeaseStatus
from backend.api.auth import get_current_user

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
    months: List[str]
    revenue: List[float]
    expenses: List[float]
    net_income: List[float]

class PaymentDue(BaseModel):
    id: int
    tenant_name: str
    amount: float
    due_date: date
    days_overdue: Optional[int] = None
    status: PaymentStatus

class Lead(BaseModel):
    id: int
    name: str
    contact_info: str
    property_interest: str
    created_at: datetime
    status: str

class DashboardResponse(BaseModel):
    summary: DashboardSummary
    occupancy: OccupancyData
    revenue: RevenueData
    payments_due: List[PaymentDue]
    leads: List[Lead]

# API endpoints
@router.get("", response_model=DashboardResponse)
async def get_dashboard_data(
    property_id: Optional[int] = None,
    time_period: str = "month",  # Options: week, month, quarter, year
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard data with occupancy rates, revenue trends, and more"""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access dashboard data"
        )
    
    # Calculate date ranges based on selected time period
    today = date.today()
    if time_period == "week":
        start_date = today - timedelta(days=today.weekday())  # Monday of current week
        end_date = start_date + timedelta(days=6)  # Sunday of current week
    elif time_period == "month":
        start_date = date(today.year, today.month, 1)  # First day of current month
        # Last day of current month
        if today.month == 12:
            end_date = date(today.year, 12, 31)
        else:
            end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
    elif time_period == "quarter":
        current_quarter = (today.month - 1) // 3 + 1
        start_date = date(today.year, (current_quarter - 1) * 3 + 1, 1)
        if current_quarter == 4:
            end_date = date(today.year, 12, 31)
        else:
            end_date = date(today.year, current_quarter * 3 + 1, 1) - timedelta(days=1)
    else:  # year
        start_date = date(today.year, 1, 1)
        end_date = date(today.year, 12, 31)
    
    # Generate mock data for dashboard
    # In a real application, this would query the database
    
    # 1. Summary data
    summary_query = """
    WITH property_counts AS (
        SELECT 
            COUNT(DISTINCT p.id) as total_properties,
            COUNT(u.id) as total_units,
            SUM(CASE WHEN u.is_occupied THEN 1 ELSE 0 END) as occupied_units
        FROM 
            properties p
        LEFT JOIN 
            property_units u ON p.id = u.property_id
        WHERE 
            1=1
            {property_filter}
    ),
    financial_summary AS (
        SELECT 
            COALESCE(SUM(CASE WHEN pay.status IN ('paid', 'partial') THEN pay.amount ELSE 0 END), 0) as monthly_revenue,
            COALESCE(SUM(CASE WHEN exp.category = 'maintenance' THEN exp.amount ELSE 0 END), 0) as maintenance_expenses,
            COALESCE(SUM(exp.amount), 0) as monthly_expenses,
            COALESCE(SUM(CASE WHEN inv.status IN ('pending', 'late', 'overdue') THEN inv.amount ELSE 0 END), 0) as outstanding_rent
        FROM 
            properties p
        LEFT JOIN 
            leases l ON p.id = l.property_id
        LEFT JOIN 
            payments pay ON l.id = pay.lease_id AND pay.payment_date BETWEEN :start_date AND :end_date
        LEFT JOIN 
            expenses exp ON p.id = exp.property_id AND exp.expense_date BETWEEN :start_date AND :end_date
        LEFT JOIN 
            invoices inv ON (p.id = inv.property_id OR l.tenant_id = inv.tenant_id) 
                         AND inv.status IN ('pending', 'late', 'overdue')
        WHERE 
            1=1
            {property_filter}
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
        "start_date": start_date,
        "end_date": end_date
    }
    
    if property_id:
        property_filter = "AND p.id = :property_id"
        params["property_id"] = property_id
    
    # Replace the placeholder
    summary_query = summary_query.format(property_filter=property_filter)
    
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
            COALESCE(SUM(CASE WHEN pay.status IN ('paid', 'partial') THEN pay.amount ELSE 0 END), 0) as revenue,
            COALESCE(SUM(exp.amount), 0) as expenses
        FROM 
            months m
        LEFT JOIN 
            properties p ON 1=1 {property_filter}
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
    revenue_query = revenue_query.format(property_filter=property_filter)
    
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
        CONCAT(u.first_name, ' ', u.last_name) as tenant_name,
        i.amount,
        i.due_date,
        CASE 
            WHEN i.due_date < CURRENT_DATE THEN EXTRACT(DAY FROM CURRENT_DATE - i.due_date)::integer
            ELSE NULL
        END as days_overdue,
        i.status
    FROM 
        invoices i
    JOIN 
        users u ON i.tenant_id = u.id
    LEFT JOIN 
        properties p ON i.property_id = p.id
    WHERE 
        i.status IN ('pending', 'late', 'overdue')
        {property_filter}
    ORDER BY 
        i.due_date ASC
    LIMIT 5
    """
    
    # Replace the placeholder
    payments_query = payments_query.format(property_filter=property_filter)
    
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
    
    # 5. Mock leads data (in a real app, we'd have a leads table)
    # For demonstration purposes, we'll create some sample leads
    mock_leads = [
        Lead(
            id=1,
            name="Olivia Riggs",
            contact_info="olivia.riggs@example.com",
            property_interest="2BR Apartment, downtown",
            created_at=datetime.utcnow() - timedelta(hours=4),
            status="new"
        ),
        Lead(
            id=2,
            name="Phoenix Baker",
            contact_info="phoenix.baker@example.com",
            property_interest="Studio in Westside",
            created_at=datetime.utcnow() - timedelta(days=1),
            status="contacted"
        ),
        Lead(
            id=3,
            name="Lana Steiner",
            contact_info="lana.steiner@example.com",
            property_interest="3BR House in suburbs",
            created_at=datetime.utcnow() - timedelta(days=2),
            status="viewing"
        ),
        Lead(
            id=4,
            name="Demi Wilkinson",
            contact_info="demi.wilkinson@example.com",
            property_interest="Commercial space downtown",
            created_at=datetime.utcnow() - timedelta(days=3),
            status="application"
        ),
        Lead(
            id=5,
            name="Orlando Diggs",
            contact_info="orlando.diggs@example.com",
            property_interest="1BR Apartment near university",
            created_at=datetime.utcnow() - timedelta(days=5),
            status="viewing"
        )
    ]
    
    return DashboardResponse(
        summary=summary,
        occupancy=occupancy,
        revenue=revenue_data,
        payments_due=payments_due,
        leads=mock_leads
    )
