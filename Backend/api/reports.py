import logging
from datetime import UTC, date, datetime, time, timedelta

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.accounting.expense import Expense
from Backend.models.accounting.payment import Payment
from Backend.models.accounting.common import PaymentStatus
from Backend.models.enums import UserType
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.reports import (FinancialTableRow, IncomeByProperty,
                                    MonthlyChartData, ReportResponse,
                                    ReportSummary)
from Backend.models.user import User
from Backend.utils.datetime_utils import date_to_utc_range

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)


def _convert_date_range_to_utc_datetime(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """
    Converts date range to UTC timezone-aware datetime objects for business date queries.

    Args:
        start_date: Start date to convert to beginning of day UTC
        end_date: End date to convert to end of day UTC

    Returns:
        Tuple of (start_datetime_utc, end_datetime_utc) as timezone-aware datetimes
    """
    return date_to_utc_range(start_date, end_date)


def get_date_range(date_range_str: str) -> tuple[date, date]:
    """
    Returns the start and end dates corresponding to a given date range string.

    Supported date range strings include "Current Month", "Last Month", "Last Quarter", "Year to Date", and "Last Year". If the input is invalid, defaults to the current month.

    Args:
        date_range_str: A string specifying the desired date range.

    Returns:
        A tuple containing the start and end dates for the specified range.
    """
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
            end_date = (start_date + relativedelta(months=3)) - \
                timedelta(days=1)
    elif date_range_str == "Year to Date":
        start_date = date(today.year, 1, 1)
        end_date = today
    elif date_range_str == "Last Year":
        start_date = date(today.year - 1, 1, 1)
        end_date = date(today.year - 1, 12, 31)
    else:  # Default to Current Month if invalid string
        logger.warning(
            "Invalid date_range_str: %s. Defaulting to Current Month.", date_range_str)
        start_date = today.replace(day=1)
        end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)

    return start_date, end_date


async def get_user_properties(
    session: AsyncSession,
    user: User,
    property_ids: list[int] | None = None
) -> list[int]:
    """
    Retrieves the list of property IDs accessible to the user, optionally filtered by a provided list.

    If the user is not an admin, only properties owned by the user are included. If `property_ids` are specified, the result is further filtered to those IDs, returning only those the user can access. Raises an HTTP 404 error if no accessible properties are found.

    Args:
        property_ids: Optional list of property IDs to filter the accessible properties.

    Returns:
        List of property IDs the user can access, filtered as specified.
    """
    base_query = select(col(Property.id))

    if user.user_type != UserType.ADMIN:  # Assuming ADMIN can see all, otherwise filter by owner
        base_query = base_query.where(col(Property.user_id) == user.id)

    if property_ids:
        # Ensure requested IDs are valid and owned by the user (if not admin)
        base_query = base_query.where(col(Property.id).in_(property_ids))

    result = await session.execute(base_query)
    valid_property_ids = result.scalars().all()

    if property_ids and len(valid_property_ids) != len(property_ids):
        logger.warning(
            "User %s requested access to properties they don't own or that don't exist.", user.id)
        # Decide if this should be an error or just return the ones they *can* access.
        # Let's return only the valid ones.

    if not valid_property_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No accessible properties found for the given criteria.")

    # Filter out None values
    return [pid for pid in valid_property_ids if pid is not None]


@router.get("/summary", response_model=ReportResponse)
async def get_report_summary(
    report_type: str | None = None,
    date_range: str | None = None,
    property_ids: list[int] | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> ReportResponse:
    """
    Generates a comprehensive financial summary report for properties accessible to the current user over a specified date range.

    The report includes monthly income and expense charts, summary statistics (such as total monthly revenue and average rent), a financial table with property-level details, and income by property for the last month in the range. Only properties the user has access to are included. Raises HTTP errors for invalid date ranges or inaccessible properties.

    Args:
        report_type: The type of report to generate (default is "Financial Summary").
        date_range: The date range for the report (e.g., "Current Month", "Last Month", "YTD").
        property_ids: Optional list of property IDs to filter the report.

    Returns:
        A structured report response containing chart data, summary statistics, financial table rows, and income by property.
    """
    actual_report_type = report_type if report_type is not None else "Financial Summary"
    actual_date_range = date_range if date_range is not None else "Current Month"

    logger.info("Generating report: type=%s, range=%s, properties=%s for user %s",
                actual_report_type, actual_date_range, property_ids, current_user.id)

    # --- 1. Determine Date Range & Properties ---
    try:
        start_date, end_date = get_date_range(actual_date_range)
        logger.info("Calculated date range: %s to %s", start_date, end_date)

        # Convert date range to UTC datetime objects for timezone-aware comparisons
        start_datetime_utc, end_datetime_utc = _convert_date_range_to_utc_datetime(
            start_date, end_date)
        logger.info("Converted to UTC datetime range: %s to %s",
                    start_datetime_utc, end_datetime_utc)

        accessible_property_ids = await get_user_properties(session, current_user, property_ids)
        logger.info("User has access to properties: %s",
                    accessible_property_ids)

    except HTTPException as e:
        raise e  # Re-raise validation/permission errors
    except Exception as e:
        logger.error(
            "Error determining date range or properties: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid date range or property IDs.")

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
    ).join(Lease, col(Lease.id) == col(Payment.lease_id))\
        .where(
            col(Payment.payment_date) >= start_datetime_utc,
            col(Payment.payment_date) <= end_datetime_utc,
            col(Payment.status).in_(
                [PaymentStatus.PAID, PaymentStatus.PARTIAL]),
            col(Lease.property_id).in_(accessible_property_ids)
    ).group_by(text('month'))

    # Query expenses grouped by month
    expenses_query = select(
        func.date_trunc('month', Expense.expense_date).label('month'),
        func.sum(Expense.total_amount).label('total_expenses')
    ).where(
        col(Expense.expense_date) >= start_datetime_utc,
        col(Expense.expense_date) <= end_datetime_utc,
        col(Expense.property_id).in_(accessible_property_ids)
    ).group_by(text('month'))

    payments_result = await session.execute(payments_query)
    monthly_income_data = {row.month.date(): float(row.total_income)
                           for row in payments_result.all()}

    expenses_result = await session.execute(expenses_query)
    monthly_expense_data = {row.month.date(): float(
        row.total_expenses) for row in expenses_result.all()}

    # Assemble chart data
    monthly_chart_data = MonthlyChartData(
        months=month_strs,
        # Assuming all income is rental for now
        rental_income=[monthly_income_data.get(
            m, 0.0) for m in months_in_range],
        # Placeholder for other income
        other_income=[0.0] * len(months_in_range),
        expenses=[monthly_expense_data.get(m, 0.0) for m in months_in_range]
    )

    # --- 3. Calculate Summary Data ---
    # Total Monthly Revenue (for the *last* month of the range)
    last_month_start = end_date.replace(day=1)
    last_month_revenue = monthly_income_data.get(last_month_start, 0.0)

    # Average Rent (across active leases in selected properties)
    avg_rent_query = select(func.avg(Lease.monthly_rent))\
        .where(
            col(Lease.status) == LeaseStatus.ACTIVE,
            col(Lease.property_id).in_(accessible_property_ids)
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
    props_query = select(Property).options(selectinload(getattr(
        Property, "units"))).where(col(Property.id).in_(accessible_property_ids))
    props_result = await session.execute(props_query)
    properties = props_result.scalars().unique().all()

    # Fetch payments and expenses for the *entire* date range for *all* selected properties
    all_payments_query = select(col(Lease.property_id), func.sum(Payment.amount).label('total_revenue'))\
        .join(Lease, col(Lease.id) == col(Payment.lease_id))\
        .where(
            col(Payment.payment_date) >= start_datetime_utc,
            col(Payment.payment_date) <= end_datetime_utc,
            col(Payment.status).in_(
                [PaymentStatus.PAID, PaymentStatus.PARTIAL]),
            col(Lease.property_id).in_(accessible_property_ids)
    ).group_by(col(Lease.property_id))

    all_expenses_query = select(col(Expense.property_id), func.sum(Expense.total_amount).label('total_expenses'))\
        .where(
            col(Expense.expense_date) >= start_datetime_utc,
            col(Expense.expense_date) <= end_datetime_utc,
            col(Expense.property_id).in_(accessible_property_ids)
    ).group_by(col(Expense.property_id))

    all_payments_res = await session.execute(all_payments_query)
    all_expenses_res = await session.execute(all_expenses_query)

    prop_revenue_map = {p.property_id: float(
        p.total_revenue) for p in all_payments_res.all()}
    prop_expense_map = {p.property_id: float(
        p.total_expenses) for p in all_expenses_res.all()}

    # Fetch average rent per property for active leases
    prop_avg_rent_query = select(col(Lease.property_id), func.avg(Lease.monthly_rent).label('avg_rent'))\
        .where(
            col(Lease.status) == LeaseStatus.ACTIVE,
            col(Lease.property_id).in_(accessible_property_ids)
    ).group_by(col(Lease.property_id))
    prop_avg_rent_res = await session.execute(prop_avg_rent_query)
    prop_avg_rent_map = {p.property_id: float(
        p.avg_rent or 0.0) for p in prop_avg_rent_res.all()}

    for prop in properties:
        if prop.id is None:
            logger.warning(
                "Skipping financial table row for property with no ID: %s", prop.name)
            continue
        total_units = len(prop.units)
        occupied_units = sum(1 for unit in prop.units if unit.is_rented)
        occupancy_rate_num = (
            occupied_units / total_units * 100) if total_units > 0 else 0
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
                # Note: This is total revenue for the period, not monthly
                monthly_revenue=prop_revenue,
                avg_rent=prop_avg_rent,
                expenses=prop_expenses,
                net_income=prop_revenue - prop_expenses
            )
        )

    # --- 5. Calculate Income By Property Data ---
    income_by_property = []

    # Fetch income for the *last month* only, grouped by property
    # Convert last_month_start to UTC datetime for timezone-aware comparison
    last_month_start_utc = datetime.combine(
        last_month_start, time.min, UTC)  # Keep UTC

    last_month_payments_query = select(
        col(Property.id).label('property_id'),
        col(Property.name).label('property_name'),  # Select property name
        func.sum(Payment.amount).label('last_month_income')
    )\
        .join(Lease, col(Lease.id) == col(Payment.lease_id))\
        .join(Property, col(Property.id) == col(Lease.property_id))\
        .where(
            col(Payment.payment_date) >= last_month_start_utc,
            # Use end_datetime_utc instead of end_date
            col(Payment.payment_date) <= end_datetime_utc,
            col(Payment.status).in_(
                [PaymentStatus.PAID, PaymentStatus.PARTIAL]),
            col(Lease.property_id).in_(accessible_property_ids)
    ).group_by(col(Property.id), col(Property.name))  # Group by Property ID and Name

    last_month_payments_res = await session.execute(last_month_payments_query)
    # Map needs property_id now
    last_month_income_map = {p.property_id: float(
        p.last_month_income) for p in last_month_payments_res.all()}

    for prop in properties:
        if prop.id is None:
            logger.warning(
                "Skipping income by property row for property with no ID: %s", prop.name)
            continue
        total_units = len(prop.units)
        occupied_units = sum(1 for unit in prop.units if unit.is_rented)
        occupancy_rate_num = (
            occupied_units / total_units * 100) if total_units > 0 else 0

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
