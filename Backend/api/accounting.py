import logging
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func, text
from pydantic import BaseModel

from backend.database import get_session
from backend.models.accounting import Payment, Invoice, Expense, PaymentStatus
from backend.models.lease import Lease
from backend.models.property import Property, PropertyUnit
from backend.models.user import User, UserType
from backend.api.auth import get_current_user

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
    tenant_id: int

class PaymentCreate(PaymentBase):
    pass

class PaymentUpdate(BaseModel):
    amount: Optional[float] = None
    payment_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    status: Optional[PaymentStatus] = None
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None

class PaymentResponse(PaymentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
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

# API endpoints - Payments
@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: PaymentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new payment record"""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create payment records"
        )
    
    # Validate lease and tenant exist and are related
    query = select(Lease).where(Lease.id == payment_data.lease_id)
    result = await session.execute(query)
    lease = result.scalar_one_or_none()
    
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with ID {payment_data.lease_id} not found"
        )
    
    if lease.tenant_id != payment_data.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant ID {payment_data.tenant_id} does not match lease tenant ID {lease.tenant_id}"
        )
    
    # Create new payment
    new_payment = Payment(**payment_data.dict())
    session.add(new_payment)
    await session.commit()
    await session.refresh(new_payment)
    
    logger.info(f"Payment created: {new_payment.id} for lease {payment_data.lease_id}")
    return new_payment

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
    query = select(Payment)
    
    # Apply filters
    conditions = []
    if lease_id:
        conditions.append(Payment.lease_id == lease_id)
    if tenant_id:
        conditions.append(Payment.tenant_id == tenant_id)
    if status:
        conditions.append(Payment.status == status)
    if start_date:
        conditions.append(Payment.payment_date >= start_date)
    if end_date:
        conditions.append(Payment.payment_date <= end_date)
    
    # Apply conditions if any
    if conditions:
        query = query.where(and_(*conditions))
    
    # Apply access control
    if current_user.user_type == UserType.TENANT:
        # Tenants can only see their own payments
        query = query.where(Payment.tenant_id == current_user.id)
    
    result = await session.execute(query)
    payments = result.scalars().all()
    return payments

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
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
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
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
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
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
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
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
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
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
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
        SUM(CASE WHEN u.is_occupied THEN 1 ELSE 0 END) as occupied_units,
        SUM(CASE WHEN NOT u.is_occupied THEN 1 ELSE 0 END) as vacant_units,
        CASE 
            WHEN COUNT(u.id) > 0 THEN 
                CAST(SUM(CASE WHEN u.is_occupied THEN 1 ELSE 0 END) AS FLOAT) / COUNT(u.id) * 100
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
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
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
