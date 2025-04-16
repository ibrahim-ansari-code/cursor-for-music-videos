import logging
from typing import List, Optional
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func, text
from pydantic import BaseModel, validator
from sqlalchemy.orm import selectinload
from decimal import Decimal

from Backend.database import get_session
from Backend.models.accounting import Payment, Invoice, Expense, PaymentStatus, PaymentMethod
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property, PropertyUnit
from Backend.models.user import User, UserType
from Backend.api.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/accounting",
    tags=["accounting"],
)

# API models
class PaymentBase(BaseModel):
    amount: float
    payment_date: datetime
    payment_method: str
    status: PaymentStatus
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None
    lease_id: int
    tenant_id: Optional[int] = None

    @validator('transaction_reference', 'notes', pre=True)
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

class PaymentCreate(BaseModel):
    """Schema for creating a new payment"""
    lease_id: int
    amount: float
    payment_date: Optional[datetime] = None
    payment_method: Optional[str] = PaymentMethod.OTHER.value
    status: Optional[PaymentStatus] = PaymentStatus.PENDING
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None
    tenant_name: Optional[str] = None  # Add tenant_name field

class PaymentUpdate(BaseModel):
    amount: Optional[float] = None
    payment_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    status: Optional[PaymentStatus] = None
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None

class PaymentResponse(BaseModel):
    """Schema for payment response"""
    id: int
    lease_id: int
    tenant_id: int
    amount: float
    payment_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    status: Optional[PaymentStatus] = None
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tenant_name: Optional[str] = None  # Add tenant_name field in response
    property_name: Optional[str] = None
    
    class Config:
        orm_mode = True

class InvoiceBase(BaseModel):
    invoice_number: str
    amount: float
    description: str
    issue_date: date
    due_date: date
    status: PaymentStatus = PaymentStatus.PENDING
    property_id: Optional[int] = None
    tenant_id: int

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[PaymentStatus] = None

class InvoiceResponse(InvoiceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class ExpenseBase(BaseModel):
    amount: float
    category: str
    description: str
    expense_date: date
    receipt_url: Optional[str] = None
    property_id: int
    vendor_id: Optional[int] = None

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    expense_date: Optional[date] = None
    receipt_url: Optional[str] = None
    vendor_id: Optional[int] = None

class ExpenseResponse(ExpenseBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class OccupancyResponse(BaseModel):
    property_id: Optional[int] = None
    property_name: Optional[str] = None
    total_units: int
    occupied_units: int
    vacant_units: int
    occupancy_rate: float  # Percentage (0-100)

class RevenueTrendResponse(BaseModel):
    period: str  # Month or year
    revenue: float
    expenses: float
    net_income: float

class AccountingOverviewResponse(BaseModel):
    monthly_revenue: float
    monthly_expenses: float
    monthly_net_income: float
    ytd_revenue: float
    ytd_expenses: float
    ytd_net_income: float
    occupancy_rate: float
    outstanding_payments: int
    average_rent: float
    revenue_trends: list[RevenueTrendResponse]

class GeneratePaymentsResponse(BaseModel):
    created: int
    skipped: int

async def get_month_payments(session: AsyncSession, lease_id: int, month: date) -> bool:
    """Check if payments exist for a lease in a given month"""
    query = select(Payment).where(
        and_(
            Payment.lease_id == lease_id,
            func.date_trunc('month', Payment.payment_date) == func.date_trunc('month', month)
        )
    )
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# API endpoints - Payments
@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    payment: PaymentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new payment record"""
    
    # Validate that the lease exists
    lease_query = select(Lease).filter(Lease.id == payment.lease_id)
    lease_result = await session.execute(lease_query)
    lease = lease_result.scalars().first()
    
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with ID {payment.lease_id} not found"
        )
    
    # Create payment record
    payment_obj = Payment(
        lease_id=payment.lease_id,
        tenant_id=current_user.id,  # Use current user ID for foreign key
        amount=payment.amount,
        payment_date=payment.payment_date,
        payment_method=payment.payment_method,
        status=payment.status,
        transaction_reference=payment.transaction_reference,
        notes=payment.notes,
        tenant_name=payment.tenant_name  # Store the tenant's name from the request
    )
    
    try:
        session.add(payment_obj)
        await session.commit()
        await session.refresh(payment_obj)
        
        # Get property name
        property_query = select(Property).join(Lease, Lease.property_id == Property.id).filter(Lease.id == payment.lease_id)
        property_result = await session.execute(property_query)
        property_obj = property_result.scalars().first()
        
        # Create response with additional information
        response = {
            **payment_obj.__dict__,
            "property_name": property_obj.name if property_obj else None,
        }
        
        return response
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating payment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment: {str(e)}"
        )

@router.get("/payments", response_model=List[PaymentResponse])
async def get_payments(
    lease_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    status: Optional[PaymentStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all payments with optional filtering"""
    try:
        # Build query with joins to get tenant and property information
        query = """
        SELECT 
            p.id, p.amount, p.payment_date, p.payment_method, p.status, 
            p.transaction_reference, p.notes, p.lease_id, p.tenant_id,
            p.created_at, p.updated_at,
            t.first_name || ' ' || t.last_name as tenant_name,
            prop.name as property_name
        FROM payments p
        LEFT JOIN leases l ON p.lease_id = l.id
        LEFT JOIN tenants t ON l.tenant_id = t.id
        LEFT JOIN properties prop ON l.property_id = prop.id
        WHERE 1=1
        """
        params = {}
        
        # Apply filters
        if lease_id:
            query += " AND p.lease_id = :lease_id"
            params["lease_id"] = lease_id
            
        if status:
            query += " AND p.status = :status"
            params["status"] = status
            
        if start_date:
            query += " AND DATE(p.payment_date) >= :start_date"
            params["start_date"] = start_date
            
        if end_date:
            query += " AND DATE(p.payment_date) <= :end_date"
            params["end_date"] = end_date
            
        # Apply access control based on user type
        user_type = current_user.user_type.upper() if current_user.user_type else None
        
        if user_type == "TENANT":
            # Tenants can only see their own payments
            query += " AND l.tenant_id = :tenant_id"
            params["tenant_id"] = current_user.id
        elif user_type == "LANDLORD":
            # Landlords can only see payments for their properties
            query += " AND prop.owner_id = :landlord_id"
            params["landlord_id"] = current_user.id
            
        # Add order by
        query += " ORDER BY p.payment_date DESC"
        
        # Execute query
        result = await session.execute(text(query), params)
        payments = result.mappings().all()
        
        # Convert DB rows to PaymentResponse objects
        payment_responses = []
        for payment in payments:
            payment_dict = dict(payment)
            # Convert decimal to float if needed
            if isinstance(payment_dict.get("amount"), Decimal):
                payment_dict["amount"] = float(payment_dict["amount"])
            payment_responses.append(payment_dict)
            
        return payment_responses
        
    except Exception as e:
        logger.error(f"Error fetching payments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch payments: {str(e)}"
        )

@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific payment by ID"""
    query = select(Payment).where(Payment.id == payment_id)
    result = await session.execute(query)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found"
        )
    
    # Apply access control
    if current_user.user_type == UserType.TENANT and payment.tenant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this payment"
        )
    
    return payment

@router.put("/payments/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update a payment record"""
    # Convert user_type to uppercase string for case-insensitive comparison
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    
    if user_type not in ["ADMIN", "LANDLORD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update payment records"
        )
    
    query = select(Payment).where(Payment.id == payment_id)
    result = await session.execute(query)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found"
        )
    
    # Update payment fields
    payment_data_dict = payment_data.dict(exclude_unset=True)
    for key, value in payment_data_dict.items():
        setattr(payment, key, value)
    
    # Update timestamp
    payment.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(payment)
    
    logger.info(f"Payment updated: {payment.id} by user {current_user.id}")
    return payment

# API endpoints - Invoices
@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new invoice"""
    # Convert user_type to uppercase string for case-insensitive comparison
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    
    if user_type not in ["ADMIN", "LANDLORD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create invoices"
        )
    
    # Create new invoice
    new_invoice = Invoice(**invoice_data.dict())
    session.add(new_invoice)
    await session.commit()
    await session.refresh(new_invoice)
    
    logger.info(f"Invoice created: {new_invoice.id} for tenant {invoice_data.tenant_id}")
    return new_invoice

@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    tenant_id: Optional[int] = None,
    property_id: Optional[int] = None,
    status: Optional[PaymentStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all invoices with optional filtering"""
    query = select(Invoice)
    
    # Apply filters
    conditions = []
    if tenant_id:
        conditions.append(Invoice.tenant_id == tenant_id)
    if property_id:
        conditions.append(Invoice.property_id == property_id)
    if status:
        conditions.append(Invoice.status == status)
    if start_date:
        conditions.append(Invoice.issue_date >= start_date)
    if end_date:
        conditions.append(Invoice.issue_date <= end_date)
    
    # Apply conditions if any
    if conditions:
        query = query.where(and_(*conditions))
    
    # Apply access control
    if current_user.user_type == UserType.TENANT:
        # Tenants can only see their own invoices
        query = query.where(Invoice.tenant_id == current_user.id)
    
    result = await session.execute(query)
    invoices = result.scalars().all()
    return invoices

# API endpoints - Expenses
@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_data: ExpenseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new expense record"""
    # Convert user_type to uppercase string for case-insensitive comparison
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    
    if user_type not in ["ADMIN", "LANDLORD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create expense records"
        )
    
    # Create new expense
    new_expense = Expense(**expense_data.dict())
    session.add(new_expense)
    await session.commit()
    await session.refresh(new_expense)
    
    logger.info(f"Expense created: {new_expense.id} for property {expense_data.property_id}")
    return new_expense

@router.get("/expenses", response_model=List[ExpenseResponse])
async def get_expenses(
    property_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all expenses with optional filtering"""
    # Convert user_type to uppercase string for case-insensitive comparison
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    
    if user_type not in ["ADMIN", "LANDLORD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view expense records"
        )
    
    query = select(Expense)
    
    # Apply filters
    conditions = []
    if property_id:
        conditions.append(Expense.property_id == property_id)
    if vendor_id:
        conditions.append(Expense.vendor_id == vendor_id)
    if category:
        conditions.append(Expense.category == category)
    if start_date:
        conditions.append(Expense.expense_date >= start_date)
    if end_date:
        conditions.append(Expense.expense_date <= end_date)
    
    # Apply conditions if any
    if conditions:
        query = query.where(and_(*conditions))
    
    result = await session.execute(query)
    expenses = result.scalars().all()
    return expenses

# Analytics endpoints
@router.get("/occupancy", response_model=List[OccupancyResponse])
async def get_occupancy_rates(
    property_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get occupancy rates for properties"""
    # Convert user_type to uppercase string for case-insensitive comparison
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    
    if user_type not in ["ADMIN", "LANDLORD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view occupancy data"
        )
    
    # Build query
    query = """
    SELECT 
        p.id as property_id,
        p.name as property_name,
        COUNT(u.id) as total_units,
        SUM(CASE WHEN u.is_rented THEN 1 ELSE 0 END) as occupied_units,
        SUM(CASE WHEN NOT u.is_rented THEN 1 ELSE 0 END) as vacant_units,
        CASE 
            WHEN COUNT(u.id) > 0 THEN 
                CAST(SUM(CASE WHEN u.is_rented THEN 1 ELSE 0 END) AS FLOAT) / COUNT(u.id) * 100
            ELSE 0
        END as occupancy_rate
    FROM 
        properties p
    LEFT JOIN 
        property_units u ON p.id = u.property_id
    """
    
    params = {}
    if property_id:
        query += " WHERE p.id = :property_id"
        params["property_id"] = property_id
    
    query += " GROUP BY p.id, p.name"
    
    result = await session.execute(text(query), params)
    occupancy_data = result.mappings().all()
    
    return [
        OccupancyResponse(
            property_id=row['property_id'],
            property_name=row['property_name'],
            total_units=row['total_units'] or 0,
            occupied_units=row['occupied_units'] or 0,
            vacant_units=row['vacant_units'] or 0,
            occupancy_rate=row['occupancy_rate'] or 0.0
        )
        for row in occupancy_data
    ]

@router.get("/revenue-trends", response_model=List[RevenueTrendResponse])
async def get_revenue_trends(
    period_type: str = "monthly",  # 'monthly' or 'yearly'
    year: Optional[int] = None,
    property_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get revenue trends by month or year"""
    # Convert user_type to uppercase string for case-insensitive comparison
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    
    if user_type not in ["ADMIN", "LANDLORD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view revenue data"
        )
    
    # Get current year if not specified
    if not year:
        year = datetime.utcnow().year
    
    # SQL query for revenue trends
    if period_type == "monthly":
        # Monthly trends for a specific year
        query = """
        WITH months AS (
            SELECT generate_series(1, 12) AS month
        ),
        payment_data AS (
            SELECT 
                EXTRACT(MONTH FROM p.payment_date) AS month,
                SUM(p.amount) AS revenue
            FROM 
                payments p
            JOIN 
                leases l ON p.lease_id = l.id
            JOIN 
                properties prop ON l.property_id = prop.id
            WHERE 
                EXTRACT(YEAR FROM p.payment_date) = :year
                AND p.status IN ('paid', 'partial')
                {property_filter}
            GROUP BY 
                EXTRACT(MONTH FROM p.payment_date)
        ),
        expense_data AS (
            SELECT 
                EXTRACT(MONTH FROM e.expense_date) AS month,
                SUM(e.amount) AS expenses
            FROM 
                expenses e
            WHERE 
                EXTRACT(YEAR FROM e.expense_date) = :year
                {property_filter_expenses}
            GROUP BY 
                EXTRACT(MONTH FROM e.expense_date)
        )
        SELECT 
            m.month,
            COALESCE(p.revenue, 0) AS revenue,
            COALESCE(e.expenses, 0) AS expenses,
            COALESCE(p.revenue, 0) - COALESCE(e.expenses, 0) AS net_income
        FROM 
            months m
        LEFT JOIN 
            payment_data p ON m.month = p.month
        LEFT JOIN 
            expense_data e ON m.month = e.month
        ORDER BY 
            m.month
        """
        
        # Add property filter if specified
        property_filter = ""
        property_filter_expenses = ""
        params = {"year": year}
        
        if property_id:
            property_filter = "AND prop.id = :property_id"
            property_filter_expenses = "AND e.property_id = :property_id"
            params["property_id"] = property_id
        
        # Replace the placeholders
        query = query.format(
            property_filter=property_filter,
            property_filter_expenses=property_filter_expenses
        )
        
        result = await session.execute(text(query), params)
        trends_data = result.mappings().all()
        
        # Map month numbers to names
        month_names = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]
        
        return [
            RevenueTrendResponse(
                period=month_names[int(row['month'])-1],
                revenue=float(row['revenue']),
                expenses=float(row['expenses']),
                net_income=float(row['net_income'])
            )
            for row in trends_data
        ]
    
    else:
        # Yearly trends
        query = """
        WITH years AS (
            SELECT generate_series(:start_year, :end_year) AS year
        ),
        payment_data AS (
            SELECT 
                EXTRACT(YEAR FROM p.payment_date) AS year,
                SUM(p.amount) AS revenue
            FROM 
                payments p
            JOIN 
                leases l ON p.lease_id = l.id
            JOIN 
                properties prop ON l.property_id = prop.id
            WHERE 
                p.status IN ('paid', 'partial')
                {property_filter}
            GROUP BY 
                EXTRACT(YEAR FROM p.payment_date)
        ),
        expense_data AS (
            SELECT 
                EXTRACT(YEAR FROM e.expense_date) AS year,
                SUM(e.amount) AS expenses
            FROM 
                expenses e
            WHERE 
                1=1
                {property_filter_expenses}
            GROUP BY 
                EXTRACT(YEAR FROM e.expense_date)
        )
        SELECT 
            y.year,
            COALESCE(p.revenue, 0) AS revenue,
            COALESCE(e.expenses, 0) AS expenses,
            COALESCE(p.revenue, 0) - COALESCE(e.expenses, 0) AS net_income
        FROM 
            years y
        LEFT JOIN 
            payment_data p ON y.year = p.year
        LEFT JOIN 
            expense_data e ON y.year = e.year
        ORDER BY 
            y.year
        """
        
        # Add property filter if specified
        property_filter = ""
        property_filter_expenses = ""
        params = {"start_year": year - 4, "end_year": year}
        
        if property_id:
            property_filter = "AND prop.id = :property_id"
            property_filter_expenses = "AND e.property_id = :property_id"
            params["property_id"] = property_id
        
        # Replace the placeholders
        query = query.format(
            property_filter=property_filter,
            property_filter_expenses=property_filter_expenses
        )
        
        result = await session.execute(text(query), params)
        trends_data = result.mappings().all()
        
        return [
            RevenueTrendResponse(
                period=str(int(row['year'])),
                revenue=float(row['revenue']),
                expenses=float(row['expenses']),
                net_income=float(row['net_income'])
            )
            for row in trends_data
        ]

@router.get("/overview", response_model=AccountingOverviewResponse)
async def get_accounting_overview(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get accounting overview metrics"""
    # Convert user_type to uppercase string for case-insensitive comparison
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    
    if user_type not in ["ADMIN", "LANDLORD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view accounting overview"
        )

    # Calculate date ranges
    today = date.today()
    year_start = date(today.year, 1, 1)
    month_start = date(today.year, today.month, 1)
    
    # Get monthly revenue from paid payments
    monthly_revenue_query = select(func.coalesce(func.sum(Payment.amount), 0.0)).where(
        and_(
            Payment.payment_date >= month_start,
            Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL])
        )
    )
    result = await session.execute(monthly_revenue_query)
    monthly_revenue = result.scalar()

    # Get YTD revenue from paid payments
    ytd_revenue_query = select(func.coalesce(func.sum(Payment.amount), 0.0)).where(
        and_(
            Payment.payment_date >= year_start,
            Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL])
        )
    )
    result = await session.execute(ytd_revenue_query)
    ytd_revenue = result.scalar()

    # Get monthly expenses
    monthly_expenses_query = select(func.coalesce(func.sum(Expense.amount), 0.0)).where(
        Expense.expense_date >= month_start
    )
    result = await session.execute(monthly_expenses_query)
    monthly_expenses = result.scalar()

    # Get YTD expenses
    ytd_expenses_query = select(func.coalesce(func.sum(Expense.amount), 0.0)).where(
        Expense.expense_date >= year_start
    )
    result = await session.execute(ytd_expenses_query)
    ytd_expenses = result.scalar()

    # Calculate net income
    monthly_net_income = monthly_revenue - monthly_expenses
    ytd_net_income = ytd_revenue - ytd_expenses

    # Get occupancy rate
    occupancy_query = """
        SELECT 
            CASE 
                WHEN COUNT(u.id) > 0 
                THEN CAST(SUM(CASE WHEN u.is_rented THEN 1 ELSE 0 END) AS FLOAT) / COUNT(u.id) * 100
                ELSE 0
            END as occupancy_rate
        FROM property_units u
    """
    result = await session.execute(text(occupancy_query))
    occupancy_rate = result.scalar() or 0.0

    # Get count of outstanding payments
    outstanding_query = select(func.count(Invoice.id)).where(
        Invoice.status.in_([PaymentStatus.PENDING, PaymentStatus.LATE, PaymentStatus.OVERDUE])
    )
    result = await session.execute(outstanding_query)
    outstanding_payments = result.scalar()

    # Calculate average rent from active leases
    average_rent_query = select(func.coalesce(func.avg(Lease.monthly_rent), 0.0)).where(
        Lease.status == LeaseStatus.ACTIVE
    )
    result = await session.execute(average_rent_query)
    average_rent = result.scalar() or 0.0

    # Get revenue trends for past 12 months
    trends_query = """
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
                COALESCE(SUM(CASE WHEN pay.status IN ('PAID', 'PARTIAL') THEN pay.amount ELSE 0 END), 0) as revenue,
                COALESCE(SUM(exp.amount), 0) as expenses
            FROM
                months m
            LEFT JOIN
                properties p ON 1=1
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
            to_char(month, 'Mon YYYY') as period,
            revenue,
            expenses,
            revenue - expenses as net_income
        FROM
            monthly_data
    """
    result = await session.execute(text(trends_query))
    revenue_trends = [
        RevenueTrendResponse(
            period=row.period,
            revenue=float(row.revenue),
            expenses=float(row.expenses),
            net_income=float(row.net_income)
        )
        for row in result.all()
    ]

    return AccountingOverviewResponse(
        monthly_revenue=monthly_revenue,
        monthly_expenses=monthly_expenses,
        monthly_net_income=monthly_net_income,
        ytd_revenue=ytd_revenue,
        ytd_expenses=ytd_expenses,
        ytd_net_income=ytd_net_income,
        occupancy_rate=occupancy_rate,
        outstanding_payments=outstanding_payments,
        average_rent=average_rent,
        revenue_trends=revenue_trends
    )

@router.post("/generate-due-payments", response_model=GeneratePaymentsResponse)
async def generate_due_payments(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Generate due payments for all active leases"""
    # Convert user_type to uppercase string for case-insensitive comparison
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    
    if user_type not in ["ADMIN", "LANDLORD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to generate payments"
        )

    # Get current month
    today = date.today()
    current_month = date(today.year, today.month, 1)
    
    # Get all active leases
    query = select(Lease).where(
        and_(
            Lease.start_date <= today,
            or_(Lease.end_date >= today, Lease.end_date.is_(None))
        )
    )
    result = await session.execute(query)
    active_leases = result.scalars().all()
    
    created_count = 0
    skipped_count = 0
    
    for lease in active_leases:
        # Check if payment already exists for this month
        has_payment = await get_month_payments(session, lease.id, current_month)
        
        if not has_payment:
            # Create payment due date based on lease's rent_due_day
            payment_date = date(today.year, today.month, lease.rent_due_day)
            if payment_date < today:  # If due day has passed, set to next month
                if today.month == 12:
                    payment_date = date(today.year + 1, 1, lease.rent_due_day)
                else:
                    payment_date = date(today.year, today.month + 1, lease.rent_due_day)
            
            # Create new payment
            new_payment = Payment(
                lease_id=lease.id,
                tenant_id=lease.tenant_id,
                amount=lease.monthly_rent,
                payment_date=payment_date,
                status=PaymentStatus.DUE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(new_payment)
            created_count += 1
            logger.info(f"Created payment for lease {lease.id}, tenant {lease.tenant_id}, due on {payment_date}")
        else:
            skipped_count += 1
    
    await session.commit()
    logger.info(f"Generated {created_count} payments, skipped {skipped_count} existing payments")
    
    return GeneratePaymentsResponse(
        created=created_count,
        skipped=skipped_count
    )
