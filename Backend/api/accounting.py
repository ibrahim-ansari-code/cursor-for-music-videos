import logging
from typing import List, Optional
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func, text, exists
from pydantic import BaseModel, validator
from sqlalchemy.orm import selectinload, joinedload
from decimal import Decimal

from Backend.database import get_session
from Backend.models.accounting import Payment, Invoice, Expense, PaymentStatus, PaymentMethod
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property, PropertyUnit
from Backend.models.user import User, UserType
from Backend.models.tenant import Tenant
from Backend.models.vendor import Vendor
from Backend.api.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/accounting",
    tags=["accounting"],
)

# === Helper Functions for Permission Checks ===

async def check_property_ownership(
    property_id: int,
    session: AsyncSession,
    current_user: User
) -> Property:
    """Check if property exists and if the current user owns it (or is admin)."""
    prop_query = select(Property).where(Property.id == property_id)
    prop_result = await session.execute(prop_query)
    prop = prop_result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Property with ID {property_id} not found")
    if not current_user.is_admin and prop.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this property's data")
    return prop

async def check_lease_ownership(
    lease_id: int,
    session: AsyncSession,
    current_user: User
) -> Lease:
    """Check if lease exists and belongs to a property owned by the current user (or is admin)."""
    lease_query = select(Lease).options(joinedload(Lease.property)).where(Lease.id == lease_id)
    lease_result = await session.execute(lease_query)
    lease = lease_result.scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lease with ID {lease_id} not found")
    if not lease.property:
        # This should ideally not happen if FK constraints are set
        logger.error(f"Lease {lease_id} is missing associated property information.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lease data incomplete.")
    if not current_user.is_admin and lease.property.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access data related to this lease")
    return lease

# === API Models (Keep as is) ===

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
    query = select(Payment.id).where(
        and_(
            Payment.lease_id == lease_id,
            func.date_trunc('month', Payment.payment_date) == func.date_trunc('month', month)
        )
    ).limit(1)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# API endpoints - Payments
@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    payment: PaymentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new payment record, ensuring user has access to the lease/property."""
    # Landlords/Admins can create payments. Tenants cannot use this endpoint directly.
    if current_user.user_type == UserType.TENANT:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenants cannot directly create payment records via this endpoint.")

    # Validate lease existence and landlord ownership
    lease = await check_lease_ownership(payment.lease_id, session, current_user)

    # Determine tenant_id from the lease
    tenant_id = lease.tenant_id
    
    # Create payment record
    payment_obj = Payment(
        lease_id=payment.lease_id,
        tenant_id=tenant_id, # Use tenant_id from the validated lease
        amount=payment.amount,
        payment_date=payment.payment_date or datetime.utcnow(), # Default payment date to now if not provided
        payment_method=payment.payment_method or PaymentMethod.OTHER.value,
        status=payment.status or PaymentStatus.PENDING,
        transaction_reference=payment.transaction_reference,
        notes=payment.notes,
        tenant_name=payment.tenant_name # Store provided name, could also fetch from Tenant record
        # created_at/updated_at handled by model defaults
    )
    
    try:
        session.add(payment_obj)
        await session.commit()
        await session.refresh(payment_obj)
        
        # Create response manually to include property name
        response = PaymentResponse(
            id=payment_obj.id,
            lease_id=payment_obj.lease_id,
            tenant_id=payment_obj.tenant_id,
            amount=payment_obj.amount,
            payment_date=payment_obj.payment_date,
            payment_method=payment_obj.payment_method,
            status=payment_obj.status,
            transaction_reference=payment_obj.transaction_reference,
            notes=payment_obj.notes,
            created_at=payment_obj.created_at,
            updated_at=payment_obj.updated_at,
            tenant_name=payment_obj.tenant_name,
            property_name=lease.property.name if lease.property else "Unknown Property"
        )
        logger.info(f"Payment {payment_obj.id} created for lease {lease.id} by user {current_user.id}")
        return response
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating payment for lease {payment.lease_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment: {str(e)}"
        )

@router.get("/payments", response_model=List[PaymentResponse])
async def get_payments(
    lease_id: Optional[int] = None,
    property_id: Optional[int] = None, # New filter
    tenant_id: Optional[int] = None,
    status: Optional[PaymentStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get payments, filtered by user role and ownership."""
    try:
        # Use ORM query for better relationship handling and filtering
        query = select(Payment).options(
            selectinload(Payment.lease).options(
                selectinload(Lease.property),
                selectinload(Lease.tenant) # Load tenant directly associated with lease
            )
        )

        # Base filters
        filters = []
        if lease_id:
            filters.append(Payment.lease_id == lease_id)
        if status:
            filters.append(Payment.status == status)
        if start_date:
            filters.append(Payment.payment_date >= start_date) # Assuming payment_date is DateTime
        if end_date:
             # Adjust end_date to include the whole day if it's just a date
            if isinstance(end_date, date) and not isinstance(end_date, datetime):
                end_datetime = datetime.combine(end_date, datetime.max.time())
            else:
                end_datetime = end_date
            filters.append(Payment.payment_date <= end_datetime)

        # Role-based access control and filtering
        if current_user.user_type == UserType.TENANT:
            # Tenants see their payments (check Payment.tenant_id)
            # Also allow filtering by lease_id if it's theirs
            if tenant_id and tenant_id != current_user.id: return [] # Tenant trying to filter for someone else
            filters.append(Payment.tenant_id == current_user.id)
            if property_id: # Tenants cannot filter by arbitrary property_id
                logger.warning(f"Tenant {current_user.id} attempted to filter payments by property_id {property_id}")
                return []

        elif current_user.user_type == UserType.LANDLORD:
            # Landlords see payments for leases on their properties
            query = query.join(Payment.lease).join(Lease.property)
            filters.append(Property.user_id == current_user.id)
            if property_id: # Landlord can filter by specific owned property
                filters.append(Property.id == property_id)
            if tenant_id: # Landlord can filter by tenant_id
                filters.append(Payment.tenant_id == tenant_id)

        elif current_user.is_admin:
             # Admin can filter by property_id or tenant_id
             if property_id:
                  query = query.join(Payment.lease, isouter=True).join(Lease.property, isouter=True)
                  filters.append(Property.id == property_id)
             if tenant_id:
                  filters.append(Payment.tenant_id == tenant_id)
        else:
             logger.error(f"Unhandled user type for payment filtering: {current_user.user_type}")
             return [] # Should not happen

        # Apply all filters
        if filters:
            query = query.where(and_(*filters))

        # Add ordering
        query = query.order_by(Payment.payment_date.desc())
        
        # Execute query
        result = await session.execute(query)
        payments_orm = result.unique().scalars().all()
        
        # Convert ORM objects to response models
        payment_responses = []
        for p in payments_orm:
            tenant_name = p.tenant_name # Use stored name first
            if not tenant_name and p.lease and p.lease.tenant:
                 # Fallback to tenant record name
                 t = p.lease.tenant
                 tenant_name = f"{t.first_name} {t.last_name}".strip() if t.first_name else f"Tenant #{t.id}"

            response = PaymentResponse(
                id=p.id,
                lease_id=p.lease_id,
                tenant_id=p.tenant_id,
                amount=p.amount,
                payment_date=p.payment_date,
                payment_method=p.payment_method,
                status=p.status,
                transaction_reference=p.transaction_reference,
                notes=p.notes,
                created_at=p.created_at,
                updated_at=p.updated_at,
                tenant_name=tenant_name,
                property_name=p.lease.property.name if p.lease and p.lease.property else "Unknown Property"
            )
            payment_responses.append(response)
            
        return payment_responses
        
    except Exception as e:
        logger.error(f"Error fetching payments for user {current_user.id}: {str(e)}", exc_info=True)
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
    """Get a specific payment by ID, checking permissions."""
    query = select(Payment).options(
        selectinload(Payment.lease).options(
            selectinload(Lease.property),
            selectinload(Lease.tenant)
        )
    ).where(Payment.id == payment_id)
    result = await session.execute(query)
    payment = result.unique().scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment {payment_id} not found")

    # Permission check
    if current_user.user_type == UserType.TENANT:
        if payment.tenant_id != current_user.id:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    elif current_user.user_type == UserType.LANDLORD:
        if not payment.lease or not payment.lease.property or payment.lease.property.user_id != current_user.id:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    elif not current_user.is_admin: # Fallback deny if not admin
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Format response
    tenant_name = payment.tenant_name
    if not tenant_name and payment.lease and payment.lease.tenant:
        t = payment.lease.tenant
        tenant_name = f"{t.first_name} {t.last_name}".strip() if t.first_name else f"Tenant #{t.id}"

    response = PaymentResponse(
        id=payment.id,
        lease_id=payment.lease_id,
        tenant_id=payment.tenant_id,
        amount=payment.amount,
        payment_date=payment.payment_date,
        payment_method=payment.payment_method,
        status=payment.status,
        transaction_reference=payment.transaction_reference,
        notes=payment.notes,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
        tenant_name=tenant_name,
        property_name=payment.lease.property.name if payment.lease and payment.lease.property else "Unknown Property"
    )
    return response

@router.put("/payments/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update a payment record, checking ownership."""
    if current_user.user_type == UserType.TENANT:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenants cannot update payment records.")

    # Fetch payment with lease and property for ownership check
    query = select(Payment).options(
        joinedload(Payment.lease).joinedload(Lease.property)
    ).where(Payment.id == payment_id)
    result = await session.execute(query)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment {payment_id} not found")

    # Check ownership (Landlord owns property or Admin)
    if not current_user.is_admin:
        if not payment.lease or not payment.lease.property or payment.lease.property.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this payment")
    
    # Update payment fields
    payment_data_dict = payment_data.model_dump(exclude_unset=True)
    for key, value in payment_data_dict.items():
        setattr(payment, key, value)
    
    payment.updated_at = datetime.utcnow() # Manually update timestamp
    
    try:
        session.add(payment)
        await session.commit()
        await session.refresh(payment) # Refresh to get updated data
        # Re-fetch related data if needed for response formatting
        await session.refresh(payment.lease)
        if payment.lease: await session.refresh(payment.lease.property)
        if payment.lease: await session.refresh(payment.lease.tenant)

        logger.info(f"Payment {payment.id} updated by user {current_user.id}")

        # Format response
        tenant_name = payment.tenant_name
        if not tenant_name and payment.lease and payment.lease.tenant:
            t = payment.lease.tenant
            tenant_name = f"{t.first_name} {t.last_name}".strip() if t.first_name else f"Tenant #{t.id}"

        response = PaymentResponse(
            id=payment.id,
            lease_id=payment.lease_id,
            tenant_id=payment.tenant_id,
            amount=payment.amount,
            payment_date=payment.payment_date,
            payment_method=payment.payment_method,
            status=payment.status,
            transaction_reference=payment.transaction_reference,
            notes=payment.notes,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            tenant_name=tenant_name,
            property_name=payment.lease.property.name if payment.lease and payment.lease.property else "Unknown Property"
        )
        return response
    except Exception as e:
         await session.rollback()
         logger.error(f"Error updating payment {payment_id}: {str(e)}", exc_info=True)
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update payment: {str(e)}"
         )

# API endpoints - Invoices
@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new invoice, checking property ownership if property_id is set."""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create invoices")

    # If property_id is provided, check ownership
    if invoice_data.property_id:
        await check_property_ownership(invoice_data.property_id, session, current_user)
        # We could also infer property_id from tenant_id via lease, but explicit is clearer
    else:
         # If no property_id, we need to infer from tenant and check ownership via their lease/property
         tenant_query = select(Tenant).options(selectinload(Tenant.leases).selectinload(Lease.property)).where(Tenant.id == invoice_data.tenant_id)
         tenant_result = await session.execute(tenant_query)
         tenant = tenant_result.scalar_one_or_none()
         if not tenant:
              raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {invoice_data.tenant_id} not found")

         # Find a property owned by the current user that this tenant is associated with
         owned_property_found = False
         if tenant.current_property_id:
              prop_query = select(Property.id).where(Property.id == tenant.current_property_id, Property.user_id == current_user.id)
              if await session.scalar(prop_query):
                   owned_property_found = True
                   invoice_data.property_id = tenant.current_property_id # Assign inferred property
         if not owned_property_found and tenant.leases:
             for lease in tenant.leases:
                 if lease.property and lease.property.user_id == current_user.id:
                      owned_property_found = True
                      invoice_data.property_id = lease.property_id # Assign inferred property
                      break # Found one, no need to check further

         if not current_user.is_admin and not owned_property_found:
              raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create invoice for a tenant not associated with your properties")

    
    # Create new invoice
    try:
        new_invoice = Invoice(**invoice_data.model_dump())
        session.add(new_invoice)
        await session.commit()
        await session.refresh(new_invoice)
    
        logger.info(f"Invoice {new_invoice.id} created for tenant {invoice_data.tenant_id} by user {current_user.id}")
        return new_invoice
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating invoice for tenant {invoice_data.tenant_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create invoice: {str(e)}"
        )

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
    """Get invoices, filtered by user role and ownership."""
    query = select(Invoice)
    filters = []

    # Basic filters
    if status: filters.append(Invoice.status == status)
    if start_date: filters.append(Invoice.issue_date >= start_date)
    if end_date: filters.append(Invoice.issue_date <= end_date)

    # Role-based access control
    if current_user.user_type == UserType.TENANT:
        if tenant_id and tenant_id != current_user.id: return [] # Tenant filtering for someone else
        filters.append(Invoice.tenant_id == current_user.id)
        if property_id: return [] # Tenant cannot filter by property

    elif current_user.user_type == UserType.LANDLORD:
        # Landlords see invoices for their properties OR for tenants linked to their properties
        query = query.outerjoin(Property, Invoice.property_id == Property.id) # Join needed for filtering
        owned_prop_ids_subquery = select(Property.id).where(Property.user_id == current_user.id).scalar_subquery()

        landlord_filters = [Property.user_id == current_user.id] # Direct link via property_id

        # If filtering by a specific tenant, ensure they are linked to landlord's property
    if tenant_id:
             # Subquery to check if tenant is linked via lease or current_prop to landlord's properties
             tenant_link_check = exists().where(
                 or_(
                    and_(Lease.tenant_id == tenant_id, Lease.property_id.in_(owned_prop_ids_subquery)),
                    and_(Tenant.id == tenant_id, Tenant.current_property_id.in_(owned_prop_ids_subquery))
                 )
             ).select()
             # This subquery needs adjustment to work correctly within the main filter context
             # Simplified: Filter invoices where tenant_id matches AND property_id is owned OR property_id is null
             # This isn't perfect, might need refinement based on exact requirements for null property_id invoices
             landlord_filters.append(
                  or_(
                     Invoice.property_id.in_(owned_prop_ids_subquery),
                     and_(Invoice.property_id == None, Invoice.tenant_id == tenant_id) # Allow landlord to see tenant-only invoices? Needs business logic clarification
                  )
             )
             filters.append(Invoice.tenant_id == tenant_id) # Add the tenant filter itself
    else:
        # If not filtering by tenant, just show invoices linked to owned properties
        filters.append(Invoice.property_id.in_(owned_prop_ids_subquery))


        # Apply specific property filter if provided by landlord
    if property_id:
             filters.append(Invoice.property_id == property_id)
             # Ensure landlord owns this specific property (redundant if already filtered above, but safe)
             filters.append(Property.user_id == current_user.id)


    elif current_user.is_admin:
        # Admin can filter by any tenant or property
        if tenant_id: filters.append(Invoice.tenant_id == tenant_id)
        if property_id: filters.append(Invoice.property_id == property_id)

    else:
         logger.error(f"Unhandled user type for invoice filtering: {current_user.user_type}")
         return []

    # Apply combined filters
    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(Invoice.issue_date.desc())
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
    """Create a new expense record, checking property ownership."""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Check property ownership
    await check_property_ownership(expense_data.property_id, session, current_user)

    # Optional: Check vendor existence if vendor_id is provided
    if expense_data.vendor_id:
         vendor_exists = await session.scalar(select(Vendor.id).where(Vendor.id == expense_data.vendor_id))
         if not vendor_exists:
              raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vendor {expense_data.vendor_id} not found")

    try:
        new_expense = Expense(**expense_data.model_dump())
        session.add(new_expense)
        await session.commit()
        await session.refresh(new_expense)
        logger.info(f"Expense {new_expense.id} created for property {expense_data.property_id} by user {current_user.id}")
        return new_expense
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating expense for property {expense_data.property_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create expense: {str(e)}"
        )


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
    """Get expenses, filtered by user role and ownership."""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    query = select(Expense).options(selectinload(Expense.property)) # Load property for filtering
    filters = []

    # Basic filters
    if vendor_id: filters.append(Expense.vendor_id == vendor_id)
    if category: filters.append(Expense.category.ilike(f"%{category}%")) # Case-insensitive search
    if start_date: filters.append(Expense.expense_date >= start_date)
    if end_date: filters.append(Expense.expense_date <= end_date)

    # Ownership filtering
    if current_user.user_type == UserType.LANDLORD:
        query = query.join(Property, Expense.property_id == Property.id)
        filters.append(Property.user_id == current_user.id)
        if property_id: # Landlord filtering by specific owned property
             filters.append(Expense.property_id == property_id)

    elif current_user.is_admin:
        # Admin can filter by any property_id
        if property_id:
             filters.append(Expense.property_id == property_id)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(Expense.expense_date.desc())
    result = await session.execute(query)
    expenses = result.scalars().all()
    return expenses

# Analytics endpoints - Applying Ownership Checks

@router.get("/occupancy", response_model=List[OccupancyResponse])
async def get_occupancy_rates(
    property_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get occupancy rates, filtered by ownership."""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Base query
    query = text("""
    SELECT 
        p.id as property_id, p.name as property_name, p.user_id as owner_user_id,
        COUNT(u.id) as total_units,
        SUM(CASE WHEN u.is_rented THEN 1 ELSE 0 END) as occupied_units
    FROM properties p
    LEFT JOIN property_units u ON p.id = u.property_id
    WHERE 1=1
    {property_ownership_filter}
    GROUP BY p.id, p.name, p.user_id
    ORDER BY p.name
    """)
    params = {}
    prop_filter_sql = ""

    # Apply ownership filter
    if current_user.user_type == UserType.LANDLORD:
        prop_filter_sql += " AND p.user_id = :user_id"
        params["user_id"] = current_user.id
        if property_id: # Landlord requests specific owned property
            prop_filter_sql += " AND p.id = :property_id"
        params["property_id"] = property_id
    
    elif current_user.is_admin:
        if property_id: # Admin requests specific property
            prop_filter_sql += " AND p.id = :property_id"
            params["property_id"] = property_id
    
    # Format query with filter
    final_query = query.format(property_ownership_filter=prop_filter_sql)

    result = await session.execute(text(final_query), params)
    occupancy_data = result.mappings().all()
    
    # Calculate remaining fields in Python
    response_list = []
    for row in occupancy_data:
        total = row['total_units'] or 0
        occupied = row['occupied_units'] or 0
        vacant = total - occupied
        rate = (occupied / total * 100) if total > 0 else 0.0
        response_list.append(
        OccupancyResponse(
            property_id=row['property_id'],
            property_name=row['property_name'],
                total_units=total,
                occupied_units=occupied,
                vacant_units=vacant,
                occupancy_rate=rate
            )
        )
    return response_list

@router.get("/revenue-trends", response_model=List[RevenueTrendResponse])
async def get_revenue_trends(
    period_type: str = "monthly",
    year: Optional[int] = None,
    property_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get revenue trends, filtered by ownership."""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    current_year = datetime.utcnow().year
    target_year = year or current_year

    # Base ownership filter SQL clause
    ownership_filter_payments = ""
    ownership_filter_expenses = ""
    params = {"year": target_year} if period_type == "monthly" else {"start_year": target_year - 4, "end_year": target_year}

    if current_user.user_type == UserType.LANDLORD:
        ownership_filter_payments = "AND prop.user_id = :user_id"
        ownership_filter_expenses = "AND exp_prop.user_id = :user_id"
        params["user_id"] = current_user.id
        if property_id:
             ownership_filter_payments += " AND prop.id = :property_id"
             ownership_filter_expenses += "AND exp_prop.id = :property_id"
             params["property_id"] = property_id
    elif current_user.is_admin:
        if property_id:
             ownership_filter_payments = "AND prop.id = :property_id"
             ownership_filter_expenses = "AND exp_prop.id = :property_id"
             params["property_id"] = property_id

    # Construct the query based on period type
    if period_type == "monthly":
        query = text(f"""
        WITH months AS (SELECT generate_series(1, 12) AS month),
        payment_data AS (
            SELECT EXTRACT(MONTH FROM p.payment_date) AS month, SUM(p.amount) AS revenue
            FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id
            WHERE EXTRACT(YEAR FROM p.payment_date) = :year AND p.status IN ('PAID', 'PARTIAL') {ownership_filter_payments}
            GROUP BY EXTRACT(MONTH FROM p.payment_date)
        ),
        expense_data AS (
            SELECT EXTRACT(MONTH FROM e.expense_date) AS month, SUM(e.amount) AS expenses
            FROM expenses e JOIN properties exp_prop ON e.property_id = exp_prop.id
            WHERE EXTRACT(YEAR FROM e.expense_date) = :year {ownership_filter_expenses}
            GROUP BY EXTRACT(MONTH FROM e.expense_date)
        )
        SELECT m.month, COALESCE(p.revenue, 0) AS revenue, COALESCE(e.expenses, 0) AS expenses
        FROM months m LEFT JOIN payment_data p ON m.month = p.month LEFT JOIN expense_data e ON m.month = e.month
        ORDER BY m.month
        """)
        result = await session.execute(query, params)
        trends_data = result.mappings().all()
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return [
            RevenueTrendResponse(
                period=month_names[int(row['month'])-1],
                revenue=float(row['revenue']), expenses=float(row['expenses']),
                net_income=float(row['revenue']) - float(row['expenses'])
            ) for row in trends_data
        ]
    else: # Yearly
        query = text(f"""
        WITH years AS (SELECT generate_series(:start_year, :end_year) AS year),
        payment_data AS (
            SELECT EXTRACT(YEAR FROM p.payment_date) AS year, SUM(p.amount) AS revenue
            FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id
            WHERE p.status IN ('PAID', 'PARTIAL') {ownership_filter_payments}
            GROUP BY EXTRACT(YEAR FROM p.payment_date)
        ),
        expense_data AS (
            SELECT EXTRACT(YEAR FROM e.expense_date) AS year, SUM(e.amount) AS expenses
            FROM expenses e JOIN properties exp_prop ON e.property_id = exp_prop.id
            WHERE 1=1 {ownership_filter_expenses}
            GROUP BY EXTRACT(YEAR FROM e.expense_date)
        )
        SELECT y.year, COALESCE(p.revenue, 0) AS revenue, COALESCE(e.expenses, 0) AS expenses
        FROM years y LEFT JOIN payment_data p ON y.year = p.year LEFT JOIN expense_data e ON y.year = e.year
        ORDER BY y.year
        """)
        result = await session.execute(query, params)
        trends_data = result.mappings().all()
        return [
            RevenueTrendResponse(
                period=str(int(row['year'])), revenue=float(row['revenue']), expenses=float(row['expenses']),
                net_income=float(row['revenue']) - float(row['expenses'])
            ) for row in trends_data
        ]


@router.get("/overview", response_model=AccountingOverviewResponse)
async def get_accounting_overview(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get accounting overview metrics, filtered by ownership."""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    today = date.today()
    year_start = date(today.year, 1, 1)
    month_start = date(today.year, today.month, 1)
    params = {"month_start": month_start, "year_start": year_start}
    ownership_filter = ""
    prop_join_needed = False

    if current_user.user_type == UserType.LANDLORD:
        ownership_filter = "AND prop.user_id = :user_id"
        params["user_id"] = current_user.id
        prop_join_needed = True # Need to join Property table

    # -- Helper to construct queries with optional ownership filter --
    def build_filtered_query(base_select, date_field, date_start, extra_joins="", status_filter_sql=""):
        sql = f"{base_select} WHERE {date_field} >= :date_start {status_filter_sql} {ownership_filter if prop_join_needed else ''}"
        # Add JOIN only if filtering by ownership
        if prop_join_needed:
            sql = sql.replace("FROM payments p", "FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id")
            sql = sql.replace("FROM expenses e", "FROM expenses e JOIN properties prop ON e.property_id = prop.id")
            sql = sql.replace("FROM leases l", "FROM leases l JOIN properties prop ON l.property_id = prop.id")
            sql = sql.replace("FROM property_units u", "FROM property_units u JOIN properties prop ON u.property_id = prop.id")
        return text(sql)

    # -- Calculations --
    paid_status_filter = "AND p.status IN ('PAID', 'PARTIAL')"
    outstanding_status_filter = "AND p.status IN ('PENDING', 'LATE', 'OVERDUE')"

    monthly_revenue_q = build_filtered_query("SELECT COALESCE(SUM(p.amount), 0.0) FROM payments p", "p.payment_date", ":month_start", status_filter_sql=paid_status_filter)
    ytd_revenue_q = build_filtered_query("SELECT COALESCE(SUM(p.amount), 0.0) FROM payments p", "p.payment_date", ":year_start", status_filter_sql=paid_status_filter)
    monthly_expenses_q = build_filtered_query("SELECT COALESCE(SUM(e.amount), 0.0) FROM expenses e", "e.expense_date", ":month_start")
    ytd_expenses_q = build_filtered_query("SELECT COALESCE(SUM(e.amount), 0.0) FROM expenses e", "e.expense_date", ":year_start")
    outstanding_payments_q = build_filtered_query("SELECT COUNT(p.id) FROM payments p", "p.payment_date", ":month_start", status_filter_sql=outstanding_status_filter)
    average_rent_q = build_filtered_query("SELECT COALESCE(AVG(l.monthly_rent), 0.0) FROM leases l", "l.start_date", "'1900-01-01'", status_filter_sql="AND l.status = 'ACTIVE'") # Filter by active status

    occupancy_rate_q = text(f"""
        SELECT CASE WHEN COUNT(u.id) > 0 THEN CAST(SUM(CASE WHEN u.is_rented THEN 1 ELSE 0 END) AS FLOAT) / COUNT(u.id) * 100 ELSE 0 END
        FROM property_units u JOIN properties prop ON u.property_id = prop.id
        WHERE 1=1 {ownership_filter if prop_join_needed else ''}
    """)

    # Execute queries
    monthly_revenue = await session.scalar(monthly_revenue_q, params)
    ytd_revenue = await session.scalar(ytd_revenue_q, params)
    monthly_expenses = await session.scalar(monthly_expenses_q, params)
    ytd_expenses = await session.scalar(ytd_expenses_q, params)
    outstanding_payments = await session.scalar(outstanding_payments_q, params)
    average_rent = await session.scalar(average_rent_q, params)
    occupancy_rate = await session.scalar(occupancy_rate_q, params)

    # Revenue Trends (re-using logic from get_revenue_trends with ownership)
    # Simpler approach: Call the trends function internally (ensure it handles params correctly)
    # This requires passing the ownership params down. For simplicity, we duplicate the trend query logic here.
    trend_params = {"user_id": current_user.id} if current_user.user_type == UserType.LANDLORD else {}
    ownership_filter_payments = "AND prop.user_id = :user_id" if current_user.user_type == UserType.LANDLORD else ""
    ownership_filter_expenses = "AND exp_prop.user_id = :user_id" if current_user.user_type == UserType.LANDLORD else ""

    trends_query_text = f"""
        WITH months AS (
            SELECT generate_series(date_trunc('month', current_date - interval '11 months'), date_trunc('month', current_date), interval '1 month')::date as month_start
        ),
        payment_data AS (
            SELECT date_trunc('month', p.payment_date)::date as month, SUM(p.amount) AS revenue
            FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id
            WHERE p.status IN ('PAID', 'PARTIAL') {ownership_filter_payments} AND p.payment_date >= date_trunc('month', current_date - interval '11 months')
            GROUP BY 1
        ),
        expense_data AS (
            SELECT date_trunc('month', e.expense_date)::date as month, SUM(e.amount) AS expenses
            FROM expenses e JOIN properties exp_prop ON e.property_id = exp_prop.id
            WHERE 1=1 {ownership_filter_expenses} AND e.expense_date >= date_trunc('month', current_date - interval '11 months')
            GROUP BY 1
        )
        SELECT to_char(m.month_start, 'Mon YYYY') as period, COALESCE(p.revenue, 0) AS revenue, COALESCE(e.expenses, 0) AS expenses
        FROM months m LEFT JOIN payment_data p ON m.month_start = p.month LEFT JOIN expense_data e ON m.month_start = e.month
        ORDER BY m.month_start
    """
    trends_result = await session.execute(text(trends_query_text), trend_params)
    revenue_trends = [
        RevenueTrendResponse(period=row.period, revenue=float(row.revenue), expenses=float(row.expenses), net_income=float(row.revenue) - float(row.expenses))
        for row in trends_result.mappings().all()
    ]

    return AccountingOverviewResponse(
        monthly_revenue=float(monthly_revenue),
        monthly_expenses=float(monthly_expenses),
        monthly_net_income=float(monthly_revenue) - float(monthly_expenses),
        ytd_revenue=float(ytd_revenue),
        ytd_expenses=float(ytd_expenses),
        ytd_net_income=float(ytd_revenue) - float(ytd_expenses),
        occupancy_rate=float(occupancy_rate),
        outstanding_payments=outstanding_payments,
        average_rent=float(average_rent),
        revenue_trends=revenue_trends
    )

@router.post("/generate-due-payments", response_model=List[PaymentResponse])
async def generate_due_payments(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Generate due payments for active leases owned by the current user."""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    today = date.today()
    current_month = date(today.year, today.month, 1)
    logger.info(f"Generating payments for {current_month} by user {current_user.id}")

    # Query active leases, filtering by ownership for landlords
    lease_query = select(Lease).options(
        selectinload(Lease.property),
        selectinload(Lease.tenant)
    ).where(
            and_(
                Lease.start_date <= today,
                or_(Lease.end_date >= today, Lease.end_date.is_(None)),
                Lease.status == LeaseStatus.ACTIVE
            )
        )
    if current_user.user_type == UserType.LANDLORD:
        lease_query = lease_query.join(Lease.property).where(Property.user_id == current_user.id)

    try:
        active_leases_result = await session.execute(lease_query)
        active_leases = active_leases_result.scalars().unique().all()
        logger.info(f"Found {len(active_leases)} active leases for user {current_user.id}")

        created_payments_responses = []
        processed_lease_ids = set() # To handle potential duplicates if join logic is complex

        for lease in active_leases:
            if lease.id in processed_lease_ids: continue
            processed_lease_ids.add(lease.id)

            # Check if payment already exists using helper
            if await get_month_payments(session, lease.id, current_month):
                logger.info(f"Payment exists for lease {lease.id}, skipping.")
                continue

            tenant_name = "Unknown Tenant"
            if lease.tenant:
                t = lease.tenant
                tenant_name = f"{t.first_name} {t.last_name}".strip() if t.first_name else f"Tenant #{t.id}"

            # Create new payment - ensure we use the correct tenant_id from the lease
            new_payment = Payment(
                lease_id=lease.id,
                tenant_id=lease.tenant_id, # Crucial: Use Lease's tenant_id
                amount=lease.monthly_rent,
                payment_date=datetime.combine(today, datetime.min.time()), # Use today's date with time
                payment_method=PaymentMethod.OTHER.value,
                status=PaymentStatus.PENDING,
                tenant_name=tenant_name
                # created/updated handled by default
            )

            session.add(new_payment)
            # Commit per payment or batch commit? Batch might be faster but harder to track errors.
            # Committing individually for now.
            try:
                 await session.commit()
                 await session.refresh(new_payment)

                 property_name = lease.property.name if lease.property else "Unknown Property"
                 response = PaymentResponse(
                    id=new_payment.id, lease_id=new_payment.lease_id, tenant_id=new_payment.tenant_id,
                    amount=new_payment.amount, payment_date=new_payment.payment_date,
                    payment_method=new_payment.payment_method, status=new_payment.status,
                    transaction_reference=new_payment.transaction_reference, notes=new_payment.notes,
                    created_at=new_payment.created_at, updated_at=new_payment.updated_at,
                    tenant_name=new_payment.tenant_name, property_name=property_name
                 )
                 created_payments_responses.append(response)
                 logger.info(f"Created payment {new_payment.id} for lease {lease.id}")
            except Exception as commit_err:
                 logger.error(f"Error committing payment for lease {lease.id}: {commit_err}", exc_info=True)
                 await session.rollback() # Rollback this specific payment attempt

        logger.info(f"Generated {len(created_payments_responses)} payments for user {current_user.id}")
        return created_payments_responses

    except Exception as lease_proc_err: # Catch errors during lease processing loop
        logger.error(f"Error processing leases for payment generation: {lease_proc_err}", exc_info=True)
        # Rollback might be needed if the session is in a bad state, but individual errors are handled above
        # await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during payment generation: {lease_proc_err}"
        )


@router.get("/outstanding-payments", response_model=List[PaymentResponse])
async def get_outstanding_payments(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get outstanding payments for the current month, filtered by ownership."""
    today = date.today()
    month_start = date(today.year, today.month, 1)
    
    try:
        query = select(Payment).options(
            selectinload(Payment.lease).options(
                selectinload(Lease.property),
                selectinload(Lease.tenant)
            )
        ).where(
            and_(
                Payment.payment_date >= month_start, # Check payments generated *this* month
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.LATE, PaymentStatus.OVERDUE])
            )
        )

        # Apply ownership filter
        if current_user.user_type == UserType.TENANT:
            query = query.where(Payment.tenant_id == current_user.id)
        elif current_user.user_type == UserType.LANDLORD:
            query = query.join(Payment.lease).join(Lease.property).where(Property.user_id == current_user.id)
        elif not current_user.is_admin: # Deny other types if any exist
            return []

        query = query.order_by(Payment.payment_date)
        result = await session.execute(query)
        payments = result.unique().scalars().all()
        
        # Format response
        payment_responses = []
        for p in payments:
            tenant_name = p.tenant_name
            if not tenant_name and p.lease and p.lease.tenant:
                t = p.lease.tenant
                tenant_name = f"{t.first_name} {t.last_name}".strip() if t.first_name else f"Tenant #{t.id}"
            property_name = p.lease.property.name if p.lease and p.lease.property else "Unknown Property"

            response = PaymentResponse(
                id=p.id, lease_id=p.lease_id, tenant_id=p.tenant_id, amount=p.amount,
                payment_date=p.payment_date, payment_method=p.payment_method, status=p.status,
                transaction_reference=p.transaction_reference, notes=p.notes, created_at=p.created_at,
                updated_at=p.updated_at, tenant_name=tenant_name, property_name=property_name
            )
            payment_responses.append(response)
            
        return payment_responses
        
    except Exception as e:
        logger.error(f"Error fetching outstanding payments for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch outstanding payments: {str(e)}"
        )
