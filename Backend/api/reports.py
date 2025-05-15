import logging
from typing import List, Optional, Dict, Tuple
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from Backend.database import get_session
from Backend.api.auth import get_current_user
from Backend.models.user import User, UserType
from Backend.models.property import Property, PropertyUnit
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.accounting import Payment, PaymentStatus, Expense
from Backend.models.reports import (
    MonthlyChartData,
    ReportSummary,
    FinancialTableRow,
    IncomeByProperty,
    ReportResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)

def get_date_range(date_range_str: str) -> Tuple[date, date]:
    """Calculate start and end dates based on the string identifier."""
    today = date.today()
    
    if date_range_str == "Current Month":
        start_date = today.replace(day=1)
        end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
    elif date_range_str == "Last Month":
        end_date = today.replace(day=1) - timedelta(days=1)
        start_date = end_date.replace(day=1)
    elif date_range_str == "Last Quarter":
        current_quarter = (today.month - 1) // 3 + 1
        if current_quarter == 1:
            start_date = date(today.year - 1, 10, 1)
            end_date = date(today.year - 1, 12, 31)
        else:
            start_month_of_quarter = (current_quarter - 2) * 3 + 1
            start_date = date(today.year, start_month_of_quarter, 1)
            end_date = (start_date + relativedelta(months=3)) - timedelta(days=1)
    elif date_range_str == "Year to Date":
        start_date = date(today.year, 1, 1)
        end_date = today
    elif date_range_str == "Last Year":
        start_date = date(today.year - 1, 1, 1)
        end_date = date(today.year - 1, 12, 31)
    else: # Default to Current Month if invalid string
        logger.warning(f"Invalid date_range_str: {date_range_str}. Defaulting to Current Month.")
        start_date = today.replace(day=1)
        end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        
    return start_date, end_date

async def get_user_properties(session: AsyncSession, user: User, property_ids: Optional[List[int]] = None) -> List[int]:
    """Get list of property IDs the user has access to, optionally filtered."""
    base_query = select(Property.id)
    
    if user.user_type != UserType.ADMIN: # Assuming ADMIN can see all, otherwise filter by owner
        base_query = base_query.where(Property.user_id == user.id)
        
    if property_ids:
        # Ensure requested IDs are valid and owned by the user (if not admin)
        base_query = base_query.where(Property.id.in_(property_ids))
        
    result = await session.execute(base_query)
    valid_property_ids = result.scalars().all()
    
    if property_ids and len(valid_property_ids) != len(property_ids):
        logger.warning(f"User {user.id} requested access to properties they don't own or that don't exist.")
        # Decide if this should be an error or just return the ones they *can* access.
        # Let's return only the valid ones.
        
    if not valid_property_ids:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No accessible properties found for the given criteria.")
         
    return valid_property_ids

@router.get("/summary", response_model=ReportResponse)
async def get_report_summary(
    report_type: str = Query("Financial Summary", description="Type of report"),
    date_range: str = Query("Current Month", description="Date range (e.g., 'Current Month', 'Last Month', 'YTD')"),
    property_ids: Optional[List[int]] = Query(None, description="List of property IDs to include"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Generate a summary report based on the specified parameters."""
    logger.info(f"Generating report: type={report_type}, range={date_range}, properties={property_ids} for user {current_user.id}")

    # --- 1. Determine Date Range & Properties ---
    try:
        start_date, end_date = get_date_range(date_range)
        logger.info(f"Calculated date range: {start_date} to {end_date}")
        
        accessible_property_ids = await get_user_properties(session, current_user, property_ids)
        logger.info(f"User has access to properties: {accessible_property_ids}")
        
    except HTTPException as e:
        raise e # Re-raise validation/permission errors
    except Exception as e:
        logger.error(f"Error determining date range or properties: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date range or property IDs.")

    # --- 2. Calculate Monthly Chart Data ---
    # Generate all months in the range
    months_in_range = []
    current_month_dt = start_date.replace(day=1)
    while current_month_dt <= end_date:
        months_in_range.append(current_month_dt)
        current_month_dt += relativedelta(months=1)
        
    month_strs = [m.strftime("%b %Y") for m in months_in_range]
    
    # Query payments (income) grouped by month
    payments_query = select(
            func.date_trunc('month', Payment.payment_date).label('month'),
            func.sum(Payment.amount).label('total_income')
        ).join(Lease, Lease.id == Payment.lease_id)\
        .where(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date,
            Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
            Lease.property_id.in_(accessible_property_ids)
        ).group_by(text('month'))
        
    # Query expenses grouped by month
    expenses_query = select(
            func.date_trunc('month', Expense.expense_date).label('month'),
            func.sum(Expense.amount).label('total_expenses')
        ).where(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
            Expense.property_id.in_(accessible_property_ids)
        ).group_by(text('month'))
        
    payments_result = await session.execute(payments_query)
    monthly_income_data = {row.month.date(): float(row.total_income) for row in payments_result.all()}
    
    expenses_result = await session.execute(expenses_query)
    monthly_expense_data = {row.month.date(): float(row.total_expenses) for row in expenses_result.all()}
    
    # Assemble chart data
    monthly_chart_data = MonthlyChartData(
        months=month_strs,
        rental_income=[monthly_income_data.get(m, 0.0) for m in months_in_range], # Assuming all income is rental for now
        other_income=[0.0] * len(months_in_range), # Placeholder for other income
        expenses=[monthly_expense_data.get(m, 0.0) for m in months_in_range]
    )

    # --- 3. Calculate Summary Data ---
    # Total Monthly Revenue (for the *last* month of the range)
    last_month_start = end_date.replace(day=1)
    last_month_revenue = monthly_income_data.get(last_month_start, 0.0)
    
    # Average Rent (across active leases in selected properties)
    avg_rent_query = select(func.avg(Lease.monthly_rent))\
        .where(
            Lease.status == LeaseStatus.ACTIVE,
            Lease.property_id.in_(accessible_property_ids)
        )
    avg_rent_result = await session.execute(avg_rent_query)
    avg_rent = float(avg_rent_result.scalar_one_or_none() or 0.0)
    
    summary_data = ReportSummary(
        total_monthly_revenue=last_month_revenue,
        avg_rent=avg_rent
    )

    # --- 4. Calculate Financial Table Data ---
    financial_table = []
    
    # Get all properties with their units
    props_query = select(Property).options(selectinload(Property.units)).where(Property.id.in_(accessible_property_ids))
    props_result = await session.execute(props_query)
    properties = props_result.scalars().unique().all()
    
    # Fetch payments and expenses for the *entire* date range for *all* selected properties
    all_payments_query = select(Lease.property_id, func.sum(Payment.amount).label('total_revenue'))\
        .join(Lease, Lease.id == Payment.lease_id)\
        .where(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date,
            Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
            Lease.property_id.in_(accessible_property_ids)
        ).group_by(Lease.property_id)
        
    all_expenses_query = select(Expense.property_id, func.sum(Expense.amount).label('total_expenses'))\
        .where(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
            Expense.property_id.in_(accessible_property_ids)
        ).group_by(Expense.property_id)

    all_payments_res = await session.execute(all_payments_query)
    all_expenses_res = await session.execute(all_expenses_query)
    
    prop_revenue_map = {p.property_id: float(p.total_revenue) for p in all_payments_res.all()}
    prop_expense_map = {p.property_id: float(p.total_expenses) for p in all_expenses_res.all()}
    
    # Fetch average rent per property for active leases
    prop_avg_rent_query = select(Lease.property_id, func.avg(Lease.monthly_rent).label('avg_rent'))\
        .where(
            Lease.status == LeaseStatus.ACTIVE,
            Lease.property_id.in_(accessible_property_ids)
        ).group_by(Lease.property_id)
    prop_avg_rent_res = await session.execute(prop_avg_rent_query)
    prop_avg_rent_map = {p.property_id: float(p.avg_rent or 0.0) for p in prop_avg_rent_res.all()}

    for prop in properties:
        total_units = len(prop.units)
        occupied_units = sum(1 for unit in prop.units if unit.is_rented)
        occupancy_rate_num = (occupied_units / total_units * 100) if total_units > 0 else 0
        occupancy_rate_str = f"{occupancy_rate_num:.0f}%"
        
        prop_revenue = prop_revenue_map.get(prop.id, 0.0)
        prop_expenses = prop_expense_map.get(prop.id, 0.0)
        prop_avg_rent = prop_avg_rent_map.get(prop.id, 0.0)
        
        financial_table.append(
            FinancialTableRow(
                property=prop.name,
                property_id=prop.id,
                units=total_units,
                occupied_units=occupied_units,
                occupancy_rate=occupancy_rate_str,
                monthly_revenue=prop_revenue, # Note: This is total revenue for the period, not monthly
                avg_rent=prop_avg_rent,
                expenses=prop_expenses,
                net_income=prop_revenue - prop_expenses
            )
        )

    # --- 5. Calculate Income By Property Data ---
    income_by_property = []
    
    # Fetch income for the *last month* only, grouped by property
    last_month_payments_query = select(
            Property.id.label('property_id'),
            Property.name.label('property_name'), # Select property name
            func.sum(Payment.amount).label('last_month_income')
        )\
        .join(Lease, Lease.id == Payment.lease_id)\
        .join(Property, Property.id == Lease.property_id)\
        .where(
            Payment.payment_date >= last_month_start,
            Payment.payment_date <= end_date, # Use end_date of overall range
            Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
            Lease.property_id.in_(accessible_property_ids)
        ).group_by(Property.id, Property.name) # Group by Property ID and Name
        
    last_month_payments_res = await session.execute(last_month_payments_query)
    # Map needs property_id now
    last_month_income_map = {p.property_id: float(p.last_month_income) for p in last_month_payments_res.all()}
    
    for prop in properties:
        total_units = len(prop.units)
        occupied_units = sum(1 for unit in prop.units if unit.is_rented)
        occupancy_rate_num = (occupied_units / total_units * 100) if total_units > 0 else 0
        
        prop_last_month_income = last_month_income_map.get(prop.id, 0.0)
        
        income_by_property.append(
            IncomeByProperty(
                property=prop.name,
                property_id=prop.id,
                monthly_income=prop_last_month_income,
                occupancy_rate=occupancy_rate_num
            )
        )

    # --- 6. Assemble Final Response ---
    response = ReportResponse(
        monthly_chart=monthly_chart_data,
        summary=summary_data,
        financial_table=financial_table,
        income_by_property=income_by_property
    )

    logger.info("Report generated successfully")
    return response 