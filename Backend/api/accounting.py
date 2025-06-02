import logging
from datetime import UTC, date, datetime
from typing import Any, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import col

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.accounting import (Expense, Invoice, Payment,
                                       PaymentMethod, PaymentStatus)
from Backend.models.enums import UserType
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.utils.datetime_utils import (create_audit_datetime,
                                          date_to_utc_range, utc_now,
                                          validate_business_datetime)

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/accounting",
    tags=["accounting"],
)

# Define a TypeVar for the ID types
IDType = TypeVar('IDType', int, str, UUID)

# === Helper Functions for Permission Checks ===


def _convert_to_uuid(user_id: UUID | str | None, context: str = "user ID") -> UUID:
    """
    Converts a user ID to UUID format, handling both UUID and string inputs.

    Args:
        user_id: The user ID to convert (must be either UUID or string).
        context: Description of what this user ID represents for error messages.

    Returns:
        UUID: The converted UUID object.

    Raises:
        HTTPException: If the user ID cannot be converted to a valid UUID.
    """
    # Handle None values explicitly
    if user_id is None:
        logger.error("Cannot convert None to UUID for %s", context)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User ID cannot be None for {context}"
        )

    try:
        if isinstance(user_id, UUID):
            return user_id
        return UUID(str(user_id))
    except (ValueError, TypeError) as e:
        logger.exception(
            "Invalid user_id format for UUID conversion: %s (type: %s)", user_id, type(user_id).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid User ID format for {context}: {user_id}"
        ) from e


def _ensure_id_is_not_none(
    entity_id: IDType | None,
    entity_name: str,
    context: str,
) -> IDType:
    """
    Raises an HTTP 500 error if the provided entity ID is None.

    Logs a critical error and aborts the request if a required entity ID is missing in the given context.
    Returns the entity_id if it's not None.
    """
    if entity_id is None:
        logger.error("Critical error: %s ID is None %s.", entity_name, context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Critical error: {entity_name} ID missing {context}."
        )
    return entity_id


async def check_property_ownership(
    property_id: int,
    session: AsyncSession,
    current_user: User
) -> Property:
    """
    Verifies that a property exists and that the current user is authorized to access it.

    Raises a 404 error if the property does not exist, or a 403 error if the user is not the owner and not an admin.

    Returns:
        The Property object if access is permitted.
    """
    prop_query = select(Property).where(col(Property.id) == property_id)
    prop_result = await session.execute(prop_query)
    prop = prop_result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Property with ID {property_id} not found")
    if not current_user.is_admin and prop.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to access this property's data")
    return prop


async def check_lease_ownership(
    lease_id: int,
    session: AsyncSession,
    current_user: User
) -> Lease:
    """
    Checks that a lease exists and is owned by the current user or the user is an admin.

    Raises a 404 error if the lease does not exist, a 500 error if the lease lacks property data, or a 403 error if the user is not authorized to access the lease.

    Returns:
        The Lease object if ownership or admin rights are confirmed.
    """
    lease_query = select(Lease).options(joinedload(
        getattr(Lease, "property"))).where(col(Lease.id) == lease_id)
    lease_result = await session.execute(lease_query)
    lease = lease_result.scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Lease with ID {lease_id} not found")
    if not lease.property:
        # This should ideally not happen if FK constraints are set
        logger.error(
            "Lease %s is missing associated property information.", lease_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lease data incomplete.")
    if not current_user.is_admin and lease.property.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to access data related to this lease")
    return lease

# === API Models (Keep as is) ===

# API models


class PaymentBase(BaseModel):
    amount: float
    payment_date: datetime
    payment_method: str
    status: PaymentStatus
    transaction_reference: str | None = None
    description: str | None = None
    lease_id: int
    tenant_id: str | None = None

    @field_validator('transaction_reference', 'description', mode='before')
    @staticmethod
    def empty_str_to_none(v: str | None) -> str | None:
        """
        Converts empty string values to None.

        Used as a Pydantic validator to normalize empty string inputs to None for optional fields.

        Args:
            v: The input value, either a string or None.

        Returns:
            None if the input is an empty string, otherwise returns the original value.
        """
        if v == "":
            return None
        return v


class PaymentCreate(BaseModel):
    """Schema for creating a new payment"""
    lease_id: int
    amount: float
    payment_date: datetime | None = None
    payment_method: str | None = PaymentMethod.OTHER.value
    status: PaymentStatus | None = PaymentStatus.PENDING
    transaction_reference: str | None = None
    description: str | None = None
    tenant_name: str | None = None


class PaymentUpdate(BaseModel):
    """Schema for updating an existing payment record."""
    amount: float | None = None
    payment_date: datetime | None = None
    payment_method: str | None = None
    status: PaymentStatus | None = None
    transaction_reference: str | None = None
    description: str | None = None


class PaymentResponse(BaseModel):
    """Schema for payment response"""
    id: int
    lease_id: int
    tenant_id: str | None = None
    amount: float
    payment_date: datetime | None = None
    payment_method: str | None = None
    status: PaymentStatus | None = None
    transaction_reference: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tenant_name: str | None = None
    property_name: str | None = None

    class Config:
        from_attributes = True


class InvoiceBase(BaseModel):
    invoice_number: str
    amount: float
    description: str
    issue_date: datetime
    due_date: datetime
    status: PaymentStatus = PaymentStatus.PENDING
    property_id: int | None = None
    tenant_id: str


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    """Schema for updating an existing invoice."""
    amount: float | None = None
    description: str | None = None
    issue_date: datetime | None = None
    due_date: datetime | None = None
    status: PaymentStatus | None = None


class InvoiceResponse(InvoiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExpenseBase(BaseModel):
    amount: float
    category: str
    description: str
    expense_date: datetime
    receipt_url: str | None = None
    property_id: int


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    """Schema for updating an existing expense record."""
    amount: float | None = None
    category: str | None = None
    description: str | None = None
    expense_date: datetime | None = None
    receipt_url: str | None = None


class ExpenseResponse(ExpenseBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OccupancyResponse(BaseModel):
    property_id: int | None = None
    property_name: str | None = None
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


async def get_month_payments(session: AsyncSession, lease_id: int, month_date: date) -> bool:
    """Check if payments exist for a lease in a given month"""
    month_start = month_date.replace(day=1)
    # Calculate the first day of the next month, then subtract one day to get the end of the current month
    if month_start.month == 12:
        month_end = month_start.replace(
            year=month_start.year + 1, month=1, day=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1, day=1)

    query = select(col(Payment.id)).where(
        and_(
            col(Payment.lease_id) == lease_id,
            col(Payment.payment_date) >= month_start,
            col(Payment.payment_date) < month_end
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
    """
    Creates a new payment record for a lease if the user is a landlord or admin.

    Validates lease ownership and tenant association, constructs a payment entry, and commits it to the database. Returns a detailed payment response including property and tenant information. Raises a 403 error if a tenant attempts to create a payment, a 400 error if the tenant ID is invalid, and a 500 error if the payment cannot be created.
    """
    # Landlords/Admins can create payments. Tenants cannot use this endpoint directly.
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Tenants cannot directly create payment records via this endpoint.")

    # Validate lease existence and landlord ownership
    lease = await check_lease_ownership(payment.lease_id, session, current_user)

    # Create payment record
    # Convert tenant_id to UUID if it's not None, else pass None
    tenant_uuid: UUID | None = None
    actual_tenant_id_for_payment = lease.tenant.user_id if lease.tenant else None

    if actual_tenant_id_for_payment is not None:
        tenant_uuid = _convert_to_uuid(
            actual_tenant_id_for_payment,
            "Tenant associated with lease"
        )

    # Ensure payment_date is properly timezone-aware for business date storage
    final_payment_date: datetime
    if payment.payment_date:
        final_payment_date = validate_business_datetime(payment.payment_date)
    else:
        final_payment_date = utc_now()

    payment_obj = Payment(
        lease_id=payment.lease_id,
        tenant_id=tenant_uuid,
        amount=payment.amount,
        payment_date=final_payment_date,
        status=payment.status or PaymentStatus.PENDING,
        description=payment.description,
        payment_method=PaymentMethod(
            payment.payment_method) if payment.payment_method else PaymentMethod.OTHER,
        transaction_reference=payment.transaction_reference
    )

    try:
        session.add(payment_obj)
        await session.commit()
        await session.refresh(payment_obj)

        validated_payment_id = _ensure_id_is_not_none(
            payment_obj.id, "Payment", "after database commit")

        response = PaymentResponse(
            id=validated_payment_id,
            lease_id=payment_obj.lease_id,
            tenant_id=str(
                payment_obj.tenant_id) if payment_obj.tenant_id is not None else None,
            amount=payment_obj.amount,
            payment_date=payment_obj.payment_date,
            payment_method=payment_obj.payment_method,
            status=payment_obj.status,
            transaction_reference=payment_obj.transaction_reference,
            description=payment_obj.description,  # Changed from notes
            created_at=payment_obj.created_at,
            updated_at=payment_obj.updated_at,
            tenant_name=payment.tenant_name,
            property_name=lease.property.name if lease.property else "Unknown Property"
        )
        logger.info("Payment %s created for lease %s by user %s",
                    payment_obj.id, lease.id, current_user.id)
        return response
    except Exception as e:
        await session.rollback()
        logger.error("Error creating payment for lease %s: %s",
                     payment.lease_id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment: {str(e)}"
        ) from e


@router.get("/payments", response_model=list[PaymentResponse])
async def get_payments(
    lease_id: int | None = None,
    property_id: int | None = None,
    tenant_id: str | None = None,
    payment_status: PaymentStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[PaymentResponse]:
    """
    Retrieves payments filtered by lease, property, tenant, status, and date range, with results limited by the current user's role and ownership.

    Tenants can view only their own payments. Landlords can view payments for leases on their properties, with optional filtering by property or tenant. Admins can view all payments and filter by property or tenant. Returns a list of payment details including related tenant and property names.
    """
    try:
        # Use ORM query for better relationship handling and filtering
        query = select(Payment).options(
            selectinload(getattr(Payment, "lease")).options(
                selectinload(getattr(Lease, "property")),
                selectinload(getattr(Lease, "tenant"))
            )
        )

        # Base filters
        filters = []
        if lease_id:
            filters.append(Payment.lease_id == lease_id)
        if payment_status:  # Updated to use new parameter name
            filters.append(Payment.status == payment_status)
        if start_date:
            start_datetime, _ = date_to_utc_range(start_date, start_date)
            filters.append(Payment.payment_date >= start_datetime)
        if end_date:
            _, end_datetime = date_to_utc_range(end_date, end_date)
            filters.append(Payment.payment_date <= end_datetime)

        # Role-based access control and filtering
        if current_user.user_type == UserType.TENANT:
            # Tenants see their payments (check Payment.tenant_id)
            # Also allow filtering by lease_id if it's theirs
            if tenant_id and tenant_id != current_user.id:
                return []  # Tenant trying to filter for someone else
            filters.append(Payment.tenant_id == current_user.id)
            if property_id:  # Tenants cannot filter by arbitrary property_id
                logger.warning(
                    "Tenant %s attempted to filter payments by property_id %s", current_user.id, property_id)
                return []

        elif current_user.user_type == UserType.LANDLORD:
            # Landlords see payments for leases on their properties
            query = query.join(getattr(Payment, "lease")).join(
                getattr(Lease, "property"))
            filters.append(Property.user_id == current_user.id)
            if property_id:  # Landlord can filter by specific owned property
                filters.append(Property.id == property_id)
            if tenant_id:  # Landlord can filter by tenant_id
                filters.append(Payment.tenant_id == tenant_id)

        elif current_user.is_admin:
            # Admin can filter by property_id or tenant_id
            if property_id:
                query = query.join(getattr(Payment, "lease"), isouter=True).join(
                    getattr(Lease, "property"), isouter=True)
                filters.append(Property.id == property_id)
            if tenant_id:
                filters.append(Payment.tenant_id == tenant_id)
        else:
            logger.error(
                "Unhandled user type for payment filtering: %s", current_user.user_type)
            return []  # Should not happen

        # Apply all filters
        if filters:
            query = query.where(and_(*filters))

        # Add ordering
        query = query.order_by(col(Payment.payment_date).desc())

        # Execute query
        result = await session.execute(query)
        payments_orm = result.unique().scalars().all()

        # Convert ORM objects to response models
        payment_responses = []
        for p in payments_orm:
            if p.id is None:
                logger.error(
                    "Payment ID is None from database query - data integrity issue")
                continue  # Skip this payment rather than failing the entire request
            tenant_name = f"{p.lease.tenant.first_name} {p.lease.tenant.last_name}".strip() if p.lease and p.lease.tenant and p.lease.tenant.first_name else (
                f"Tenant #{p.lease.tenant.id}" if p.lease and p.lease.tenant else "Unknown Tenant")

            response = PaymentResponse(
                id=p.id,
                lease_id=p.lease_id,
                tenant_id=str(
                    p.tenant_id) if p.tenant_id is not None else None,
                amount=p.amount,
                payment_date=p.payment_date,
                payment_method=p.payment_method,  # Use from model
                status=p.status,
                transaction_reference=p.transaction_reference,  # Use from model
                description=p.description,
                created_at=p.created_at,
                updated_at=p.updated_at,
                tenant_name=tenant_name,
                property_name=p.lease.property.name if p.lease and p.lease.property else "Unknown Property"
            )
            payment_responses.append(response)

        return payment_responses

    except Exception as e:
        logger.error(
            f"Error fetching payments for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch payments: {str(e)}"
        ) from e


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a payment by its ID with role-based access control.

    Only the associated tenant, the landlord who owns the related property, or an admin can access the payment. Returns detailed payment information, including tenant and property names. Raises 404 if the payment does not exist or 403 if the user is not authorized.
    """
    query = select(Payment).options(
        selectinload(getattr(Payment, "lease")).options(
            selectinload(getattr(Lease, "property")),
            selectinload(getattr(Lease, "tenant"))
        )
    ).where(col(Payment.id) == payment_id)
    result = await session.execute(query)
    payment = result.unique().scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Payment {payment_id} not found")

    # Permission check
    if current_user.user_type == UserType.TENANT:
        if payment.tenant_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    elif current_user.user_type == UserType.LANDLORD:
        if not payment.lease or not payment.lease.property or payment.lease.property.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    elif not current_user.is_admin:  # Fallback deny if not admin
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Format response
    if payment.id is None:
        logger.error("Fetched payment ID is None - database integrity issue")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment data integrity error"
        )
    tenant_name = f"{payment.lease.tenant.first_name} {payment.lease.tenant.last_name}".strip() if payment.lease and payment.lease.tenant and payment.lease.tenant.first_name else (
        f"Tenant #{payment.lease.tenant.id}" if payment.lease and payment.lease.tenant else "Unknown Tenant")

    response = PaymentResponse(
        id=payment.id,
        lease_id=payment.lease_id,
        tenant_id=str(
            payment.tenant_id) if payment.tenant_id is not None else None,
        amount=payment.amount,
        payment_date=payment.payment_date,
        payment_method=payment.payment_method,  # Use from model
        status=payment.status,
        transaction_reference=payment.transaction_reference,  # Use from model
        description=payment.description,
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
    """
    Updates an existing payment record if the user is authorized.

    Only landlords and admins can update payments. Verifies payment existence and ownership before applying updates. Returns the updated payment details. Raises 403 if the user is a tenant or not authorized, 404 if the payment does not exist, and 500 on database errors.
    """
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Tenants cannot update payment records.")

    # Fetch payment with lease and property for ownership check
    query = select(Payment).options(
        joinedload(getattr(Payment, "lease")).joinedload(
            getattr(Lease, "property"))
    ).where(col(Payment.id) == payment_id)
    result = await session.execute(query)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Payment {payment_id} not found")

    # Check ownership (Landlord owns property or Admin)
    if not current_user.is_admin:
        if not payment.lease or not payment.lease.property or payment.lease.property.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Not authorized to update this payment")

    # Update payment fields
    payment_data_dict = payment_data.model_dump(exclude_unset=True)
    for key, value in payment_data_dict.items():
        if key == "payment_method" and value is not None:
            setattr(payment, key, PaymentMethod(value))
        elif key == "payment_date" and value is not None:
            # Ensure payment_date is properly timezone-aware for business date storage
            validated_payment_date = validate_business_datetime(value)
            setattr(payment, key, validated_payment_date)
        elif value is not None:  # Ensure other None values are not set if not intended
            setattr(payment, key, value)

    payment.updated_at = create_audit_datetime()

    try:
        session.add(payment)
        await session.commit()
        await session.refresh(payment)  # Refresh to get updated data
        await session.refresh(payment.lease)
        if payment.lease:
            await session.refresh(payment.lease.property)
        if payment.lease:
            await session.refresh(payment.lease.tenant)

        logger.info("Payment %s updated by user %s",
                    payment.id, current_user.id)

        # Format response
        if payment.id is None:
            logger.error(
                "Updated payment ID is None - database integrity issue")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Payment data integrity error"
            )
        tenant_name = f"{payment.lease.tenant.first_name} {payment.lease.tenant.last_name}".strip() if payment.lease and payment.lease.tenant and payment.lease.tenant.first_name else (
            f"Tenant #{payment.lease.tenant.id}" if payment.lease and payment.lease.tenant else "Unknown Tenant")

        response = PaymentResponse(
            id=payment.id,
            lease_id=payment.lease_id,
            tenant_id=str(
                payment.tenant_id) if payment.tenant_id is not None else None,
            amount=payment.amount,
            payment_date=payment.payment_date,
            payment_method=payment.payment_method,  # Use from model
            status=payment.status,
            transaction_reference=payment.transaction_reference,  # Use from model
            description=payment.description,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            tenant_name=tenant_name,
            property_name=payment.lease.property.name if payment.lease and payment.lease.property else "Unknown Property"
        )
        return response
    except Exception as e:
        await session.rollback()
        logger.error("Error updating payment %s: %s",
                     payment_id, str(e), exc_info=True)
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
    """
    Creates a new invoice, enforcing property ownership and role-based access control.

    Only landlords and admins can create invoices. If a property ID is provided, verifies that the current user owns the property. If not, attempts to infer the property from the tenant's current property or leases and checks ownership. Raises 403 if the user is not authorized or the tenant is not associated with the user's properties, and 404 if the tenant does not exist.

    Returns:
        The created Invoice object.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to create invoices")

    # If property_id is provided, check ownership
    if invoice_data.property_id:
        await check_property_ownership(invoice_data.property_id, session, current_user)
        # We could also infer property_id from tenant_id via lease, but explicit is clearer
    else:
        # If no property_id, we need to infer from tenant and check ownership via their lease/property
        tenant_query = select(Tenant).options(selectinload(getattr(Tenant, "leases")).selectinload(
            getattr(Lease, "property"))).where(col(Tenant.user_id) == invoice_data.tenant_id)
        tenant_result = await session.execute(tenant_query)
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Tenant with user ID {invoice_data.tenant_id} not found")

        # Find a property owned by the current user that this tenant is associated with
        owned_property_found = False
        if tenant.current_property_id:
            prop_query = select(col(Property.id)).where(col(
                Property.id) == tenant.current_property_id, col(Property.user_id) == current_user.id)
            if await session.scalar(prop_query):
                owned_property_found = True
                invoice_data.property_id = tenant.current_property_id  # Assign inferred property
        if not owned_property_found and tenant.leases:
            for lease in tenant.leases:
                if lease.property and lease.property.user_id == current_user.id:
                    owned_property_found = True
                    invoice_data.property_id = lease.property_id  # Assign inferred property
                    break  # Found one, no need to check further

        if not current_user.is_admin and not owned_property_found:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Cannot create invoice for a tenant not associated with your properties")

    # Create new invoice
    try:
        invoice_data_dict = invoice_data.model_dump()

        # Ensure issue_date is properly timezone-aware for business date storage
        if invoice_data_dict.get('issue_date') and isinstance(invoice_data_dict['issue_date'], datetime):
            invoice_data_dict['issue_date'] = validate_business_datetime(
                invoice_data_dict['issue_date'])

        # Ensure due_date is properly timezone-aware for business date storage
        if invoice_data_dict.get('due_date') and isinstance(invoice_data_dict['due_date'], datetime):
            invoice_data_dict['due_date'] = validate_business_datetime(
                invoice_data_dict['due_date'])

        new_invoice = Invoice(**invoice_data_dict)
        session.add(new_invoice)
        await session.commit()
        await session.refresh(new_invoice)

        logger.info("Invoice %s created for tenant %s by user %s",
                    new_invoice.id, invoice_data.tenant_id, current_user.id)
        return new_invoice
    except Exception as e:
        await session.rollback()
        logger.error("Error creating invoice for tenant %s: %s",
                     invoice_data.tenant_id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create invoice: {str(e)}"
        ) from e


@router.get("/invoices", response_model=list[Invoice])
async def get_invoices(
    tenant_id: str | None = None,
    property_id: int | None = None,
    status: PaymentStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[Invoice]:
    """
    Retrieves invoices filtered by tenant, property, status, and date range, applying role-based access control.

    Tenants can only view their own invoices and cannot filter by property. Landlords can view invoices for their owned properties or tenants linked to those properties, with optional filtering by tenant or property. Admins can view all invoices with any filters applied. Returns an empty list if access is not permitted or filters are invalid.
    """
    query = select(Invoice)
    filters = []

    # Basic filters
    if status:
        filters.append(Invoice.status == status)
    if start_date:
        start_datetime, _ = date_to_utc_range(start_date, start_date)
        filters.append(Invoice.issue_date >= start_datetime)
    if end_date:
        _, end_datetime = date_to_utc_range(end_date, end_date)
        filters.append(Invoice.issue_date <= end_datetime)

    # Role-based access control
    if current_user.user_type == UserType.TENANT:
        if tenant_id and tenant_id != current_user.id:
            return []  # Tenant filtering for someone else
        filters.append(Invoice.tenant_id == current_user.id)
        if property_id:
            return []  # Tenant cannot filter by property

    elif current_user.user_type == UserType.LANDLORD:
        # Landlords see invoices for their properties OR for tenants linked to their properties
        query = query.outerjoin(Property, col(
            Invoice.property_id) == col(Property.id))
        owned_prop_ids_subquery = select(col(Property.id)).where(
            col(Property.user_id) == current_user.id).scalar_subquery()

        landlord_filters = [col(Property.user_id) == current_user.id]

        if tenant_id:
            if 'owned_prop_ids_subquery' not in locals() and current_user.user_type == UserType.LANDLORD:
                owned_prop_ids_subquery = select(col(Property.id)).where(
                    col(Property.user_id) == current_user.id).scalar_subquery()

            if current_user.user_type == UserType.LANDLORD and 'owned_prop_ids_subquery' in locals():
                if 'landlord_filters' not in locals():
                    landlord_filters = []
                landlord_filters.append(
                    or_(
                        col(Invoice.property_id).in_(owned_prop_ids_subquery),
                        and_(col(Invoice.property_id).is_(None),
                             col(Invoice.tenant_id) == tenant_id)
                    )
                )
            filters.append(col(Invoice.tenant_id) == tenant_id)
        elif current_user.user_type == UserType.LANDLORD and 'owned_prop_ids_subquery' in locals():
            filters.append(col(Invoice.property_id).in_(
                owned_prop_ids_subquery))

    elif current_user.is_admin:
        # Admin can filter by any tenant or property
        if tenant_id:
            filters.append(Invoice.tenant_id == tenant_id)
        if property_id:
            filters.append(Invoice.property_id == property_id)

    else:
        logger.error("Unhandled user type for invoice filtering: %s",
                     current_user.user_type)
        return []

    # Apply combined filters
    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(col(Invoice.issue_date).desc())
    result = await session.execute(query)
    invoices = result.scalars().all()
    return list(invoices)

# API endpoints - Expenses


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_data: ExpenseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new expense record after verifying that the current user owns the specified property.

    Only users with landlord or admin roles are permitted to create expenses. Raises a 403 error if unauthorized, or a 500 error if the expense creation fails.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Check property ownership
    await check_property_ownership(expense_data.property_id, session, current_user)

    try:
        expense_data_dict = expense_data.model_dump()

        # Ensure expense_date is properly timezone-aware for business date storage
        if expense_data_dict.get('expense_date') and isinstance(expense_data_dict['expense_date'], datetime):
            expense_data_dict['expense_date'] = validate_business_datetime(
                expense_data_dict['expense_date'])

        new_expense = Expense(**expense_data_dict)
        session.add(new_expense)
        await session.commit()
        await session.refresh(new_expense)
        logger.info("Expense %s created for property %s by user %s",
                    new_expense.id, expense_data.property_id, current_user.id)
        return new_expense
    except Exception as e:
        await session.rollback()
        logger.error("Error creating expense for property %s: %s",
                     expense_data.property_id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create expense: {str(e)}"
        ) from e


@router.get("/expenses", response_model=list[Expense])
async def get_expenses(
    property_id: int | None = None,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[Expense]:
    """
    Retrieves expenses filtered by property, category, and date range, with results limited to properties owned by the current landlord or all properties for admins.

    Only landlords and admins can access this endpoint. Landlords see expenses for their own properties, while admins may filter by any property.
    Returns a list of matching expense records.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    query = select(Expense).options(selectinload(
        getattr(Expense, "property")))  # Load property for filtering
    filters = []

    # Basic filters
    if category:
        # pass `category` as a SQLAlchemy bound parameter instead of f-string
        filters.append(col(Expense.category).ilike(f"%{category}%"))
    if start_date:
        start_datetime, _ = date_to_utc_range(start_date, start_date)
        filters.append(col(Expense.expense_date) >= start_datetime)
    if end_date:
        _, end_datetime = date_to_utc_range(end_date, end_date)
        filters.append(col(Expense.expense_date) <= end_datetime)

    # Ownership filtering
    if current_user.user_type == UserType.LANDLORD:
        query = query.join(Property, col(
            Expense.property_id) == col(Property.id))
        filters.append(col(Property.user_id) == current_user.id)
        if property_id:  # Landlord filtering by specific owned property
            filters.append(col(Expense.property_id) == property_id)

    elif current_user.is_admin:
        # Admin can filter by any property_id
        if property_id:
            filters.append(col(Expense.property_id) == property_id)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(col(Expense.expense_date).desc())
    result = await session.execute(query)
    expenses = result.scalars().all()
    return list(expenses)

# Analytics endpoints - Applying Ownership Checks


@router.get("/occupancy", response_model=list[OccupancyResponse])
async def get_occupancy_rates(
    property_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[OccupancyResponse]:
    """
    Retrieves occupancy rates for properties owned by the current user or all properties if the user is an admin.

    Only landlords and admins are authorized to access this endpoint. Optionally filters by a specific property ID. Returns a list of occupancy statistics, including total, occupied, and vacant units, as well as the occupancy rate for each property.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

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
    params: dict[str, Any] = {}
    prop_filter_sql = ""

    # Apply ownership filter
    if current_user.user_type == UserType.LANDLORD:
        prop_filter_sql += " AND p.user_id = :user_id"
        params["user_id"] = current_user.id
        if property_id:  # Landlord requests specific owned property
            prop_filter_sql += " AND p.id = :property_id"
        params["property_id"] = property_id

    elif current_user.is_admin:
        if property_id:  # Admin requests specific property
            prop_filter_sql += " AND p.id = :property_id"
            params["property_id"] = property_id

    # Format query with filter
    final_query_string = query.text.format(
        property_ownership_filter=prop_filter_sql)

    result = await session.execute(text(final_query_string), params)
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


@router.get("/revenue-trends", response_model=list[RevenueTrendResponse])
async def get_revenue_trends(
    period_type: str = "monthly",
    year: int | None = None,
    property_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[RevenueTrendResponse]:
    """
    Returns revenue trends aggregated by month or year, filtered by user role and property ownership.

    Only landlords and admins can access this endpoint. Revenue and expense data are aggregated for each month of a given year or for each year in a five-year window, depending on the `period_type`. Results are filtered to include only properties owned by the current user (if landlord) or, optionally, a specific property.

    Args:
        period_type: "monthly" for monthly trends in a single year, "yearly" for annual trends over five years.
        year: The year to aggregate by (defaults to current year for monthly, or current year and previous four for yearly).
        property_id: If provided, restricts results to a specific property.

    Returns:
        A list of RevenueTrendResponse objects, each containing the period label, revenue, expenses, and net income.

    Raises:
        HTTPException: If the user is not authorized to access revenue trends.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    current_year = datetime.now(UTC).year
    target_year = year or current_year

    # Base ownership filter SQL clause
    ownership_filter_payments = ""
    ownership_filter_expenses = ""
    params: dict[str, Any] = {"year": target_year} if period_type == "monthly" else {
        "start_year": target_year - 4, "end_year": target_year}

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
        month_names = ["Jan", "Feb", "Mar", "Apr", "May",
                       "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return [
            RevenueTrendResponse(
                period=month_names[int(row['month'])-1],
                revenue=float(row['revenue']), expenses=float(row['expenses']),
                net_income=float(row['revenue']) - float(row['expenses'])
            ) for row in trends_data
        ]
    else:  # Yearly
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
    """
    Returns an accounting overview with key financial and occupancy metrics for the current user.

    Provides monthly and year-to-date revenue, expenses, net income, occupancy rate, outstanding payments count, average rent, and revenue trends for the past 12 months. Results are filtered by property ownership for landlords; admins receive data for all properties. Only accessible to landlords and admins; tenants are forbidden.

    Returns:
        An AccountingOverviewResponse containing aggregated financial and occupancy data.

    Raises:
        HTTPException: If the user is not an admin or landlord (403 Forbidden).
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    today = datetime.now(UTC).date()
    year_start = date(today.year, 1, 1)
    month_start = date(today.year, today.month, 1)
    params = {"month_start": month_start, "year_start": year_start}
    ownership_filter = ""
    prop_join_needed = False

    if current_user.user_type == UserType.LANDLORD:
        ownership_filter = "AND prop.user_id = :user_id"
        prop_join_needed = True

    # -- Helper to construct queries with optional ownership filter --
    def build_filtered_query(base_select, date_field, date_param_name_in_sql, status_filter_sql=""):
        # date_param_name_in_sql is the placeholder used in SQL, e.g., "filter_date"
        # The actual params dict will map this name to a value.
        sql = f"{base_select} WHERE {date_field} >= :{date_param_name_in_sql} {status_filter_sql} {ownership_filter if prop_join_needed else ''}"
        if prop_join_needed:
            if "FROM payments p" in base_select and "JOIN leases l" not in sql:
                sql = sql.replace(
                    "FROM payments p", "FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id")
            elif "FROM expenses e" in base_select and "JOIN properties prop" not in sql:
                sql = sql.replace(
                    "FROM expenses e", "FROM expenses e JOIN properties prop ON e.property_id = prop.id")
            elif "FROM leases l" in base_select and "JOIN properties prop" not in sql:
                sql = sql.replace(
                    "FROM leases l", "FROM leases l JOIN properties prop ON l.property_id = prop.id")
            elif "FROM property_units u" in base_select and "JOIN properties prop" not in sql:
                sql = sql.replace(
                    "FROM property_units u", "FROM property_units u JOIN properties prop ON u.property_id = prop.id")
        return text(sql)

    # -- Calculations --
    paid_status_filter = "AND p.status IN ('Paid', 'Partial')"
    outstanding_status_filter = "AND p.status IN ('Pending', 'Overdue')"

    # Prepare base params (user_id if landlord)
    base_query_params = {}
    if current_user.user_type == UserType.LANDLORD:
        base_query_params["user_id"] = current_user.id

    # Monthly Revenue
    monthly_revenue_params = {**base_query_params, "filter_date": month_start}
    monthly_revenue_q = build_filtered_query(
        "SELECT COALESCE(SUM(p.amount), 0.0) FROM payments p", "p.payment_date", "filter_date", status_filter_sql=paid_status_filter)
    monthly_revenue = await session.scalar(monthly_revenue_q, monthly_revenue_params)

    # YTD Revenue
    ytd_revenue_params = {**base_query_params, "filter_date": year_start}
    ytd_revenue_q = build_filtered_query("SELECT COALESCE(SUM(p.amount), 0.0) FROM payments p",
                                         "p.payment_date", "filter_date", status_filter_sql=paid_status_filter)
    ytd_revenue = await session.scalar(ytd_revenue_q, ytd_revenue_params)

    # Monthly Expenses
    monthly_expenses_params = {**base_query_params, "filter_date": month_start}
    monthly_expenses_q = build_filtered_query(
        "SELECT COALESCE(SUM(e.amount), 0.0) FROM expenses e", "e.expense_date", "filter_date")
    monthly_expenses = await session.scalar(monthly_expenses_q, monthly_expenses_params)

    # YTD Expenses
    ytd_expenses_params = {**base_query_params, "filter_date": year_start}
    ytd_expenses_q = build_filtered_query(
        "SELECT COALESCE(SUM(e.amount), 0.0) FROM expenses e", "e.expense_date", "filter_date")
    ytd_expenses = await session.scalar(ytd_expenses_q, ytd_expenses_params)

    # Outstanding Payments
    outstanding_params = {**base_query_params, "filter_date": month_start}
    outstanding_payments_q = build_filtered_query(
        "SELECT COUNT(p.id) FROM payments p", "p.payment_date", "filter_date", status_filter_sql=outstanding_status_filter)
    outstanding_payments = await session.scalar(outstanding_payments_q, outstanding_params)

    # Average Rent
    avg_rent_sql_str = f"SELECT COALESCE(AVG(l.monthly_rent), 0.0) FROM leases l WHERE l.status = 'ACTIVE' {ownership_filter if prop_join_needed else ''}"
    # Ensure join is added if ownership_filter is active
    if prop_join_needed and "JOIN properties prop" not in avg_rent_sql_str:
        avg_rent_sql_str = avg_rent_sql_str.replace(
            "FROM leases l", "FROM leases l JOIN properties prop ON l.property_id = prop.id")
    average_rent_q = text(avg_rent_sql_str)
    # Only user_id needed if landlord
    average_rent = await session.scalar(average_rent_q, base_query_params)

    # Occupancy Rate
    occupancy_rate_sql_str = f"""
        SELECT CASE WHEN COUNT(u.id) > 0 THEN CAST(SUM(CASE WHEN u.is_rented THEN 1 ELSE 0 END) AS FLOAT) / COUNT(u.id) * 100 ELSE 0 END
        FROM property_units u JOIN properties prop ON u.property_id = prop.id
        WHERE 1=1 {ownership_filter if prop_join_needed else ''}
    """
    occupancy_rate_q = text(occupancy_rate_sql_str)
    # Only user_id needed if landlord
    occupancy_rate = await session.scalar(occupancy_rate_q, base_query_params)

    # Revenue Trends
    trend_params = {}
    if current_user.user_type == UserType.LANDLORD:
        trend_params["user_id"] = current_user.id

    trend_ownership_filter_payments = "AND prop.user_id = :user_id" if current_user.user_type == UserType.LANDLORD else ""
    trend_ownership_filter_expenses = "AND exp_prop.user_id = :user_id" if current_user.user_type == UserType.LANDLORD else ""

    trends_query_text = f"""
        WITH months AS (
            SELECT generate_series(date_trunc('month', current_date - interval '11 months'), date_trunc('month', current_date), interval '1 month')::date as month_start
        ),
        payment_data AS (
            SELECT date_trunc('month', p.payment_date)::date as month, SUM(p.amount) AS revenue
            FROM payments p JOIN leases l ON p.lease_id = l.id JOIN properties prop ON l.property_id = prop.id
            WHERE p.status IN ('Paid', 'Partial') {trend_ownership_filter_payments} AND p.payment_date >= date_trunc('month', current_date - interval '11 months')
            GROUP BY 1
        ),
        expense_data AS (
            SELECT date_trunc('month', e.expense_date)::date as month, SUM(e.amount) AS expenses
            FROM expenses e JOIN properties exp_prop ON e.property_id = exp_prop.id
            WHERE 1=1 {trend_ownership_filter_expenses} AND e.expense_date >= date_trunc('month', current_date - interval '11 months')
            GROUP BY 1
        )
        SELECT to_char(m.month_start, 'Mon YYYY') as period, COALESCE(p.revenue, 0) AS revenue, COALESCE(e.expenses, 0) AS expenses
        FROM months m LEFT JOIN payment_data p ON m.month_start = p.month LEFT JOIN expense_data e ON m.month_start = e.month
        ORDER BY m.month_start
    """
    trends_result = await session.execute(text(trends_query_text), trend_params)
    revenue_trends = [
        RevenueTrendResponse(period=row.period, revenue=float(row.revenue), expenses=float(
            row.expenses), net_income=float(row.revenue) - float(row.expenses))
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


@router.post("/generate-due-payments", response_model=list[PaymentResponse])
async def generate_due_payments(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[PaymentResponse]:
    """
    Generates pending monthly rent payments for all active leases owned by the current user.

    For each active lease without an existing payment for the current month, creates a new pending payment with the lease's monthly rent and a description referencing the tenant. Only users with admin or landlord roles can invoke this operation; others receive a 403 error. Leases with missing tenant information or existing payments for the current month are skipped. Returns a list of created payment records.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    today = datetime.now(UTC).date()
    current_month = date(today.year, today.month, 1)
    logger.info("Generating payments for %s by user %s",
                current_month, current_user.id)

    # Query active leases, filtering by ownership for landlords
    lease_query = select(Lease).options(
        selectinload(getattr(Lease, "property")),
        selectinload(getattr(Lease, "tenant"))
    ).where(
        and_(
            col(Lease.start_date) <= today,
            or_(col(Lease.end_date) >= today,
                col(Lease.end_date).is_(None)),
            col(Lease.status) == LeaseStatus.ACTIVE
        )
    )
    if current_user.user_type == UserType.LANDLORD:
        lease_query = lease_query.join(Property, col(Lease.property_id) == col(
            Property.id)).where(col(Property.user_id) == current_user.id)

    try:
        active_leases_result = await session.execute(lease_query)
        active_leases = active_leases_result.scalars().unique().all()
        logger.info("Found %s active leases for user %s",
                    len(active_leases), current_user.id)

        created_payments_responses = []
        processed_lease_ids = set()  # To handle potential duplicates if join logic is complex

        for lease in active_leases:
            if lease.id in processed_lease_ids:
                continue
            processed_lease_ids.add(lease.id)

            if lease.id is None:
                logger.warning(
                    "Lease ID is None - skipping payment generation for this lease")
                continue
            # Check if payment already exists using helper
            if await get_month_payments(session, lease.id, current_month):
                logger.info("Payment exists for lease %s, skipping.", lease.id)
                continue

            tenant_name = "Unknown Tenant"
            if lease.tenant:
                t = lease.tenant
                tenant_name = f"{t.first_name} {t.last_name}".strip(
                ) if t.first_name else f"Tenant #{t.id}"

            # Create new payment - ensure we use the correct tenant_id from the lease
            tenant_user_id_for_payment: UUID | None = None
            if lease.tenant and lease.tenant.user_id:
                tenant_user_id_for_payment = _convert_to_uuid(
                    lease.tenant.user_id,
                    f"Tenant associated with lease {lease.id}"
                )
            else:
                logger.warning(
                    "Tenant or tenant user_id missing for lease %s. Skipping payment generation.", lease.id)
                continue  # Skip this lease

            if lease.id is None:
                logger.warning(
                    "Lease ID is None when creating payment - skipping")
                continue
            new_payment = Payment(
                lease_id=lease.id,
                tenant_id=tenant_user_id_for_payment,  # Use the validated/converted UUID
                amount=lease.monthly_rent,
                payment_date=utc_now(),  # Store as timezone-aware UTC for business date
                status=PaymentStatus.PENDING,
                # Use description instead
                description=f"Monthly rent payment for {tenant_name}",
                # Default to OTHER, or determine from lease/tenant if applicable
                payment_method=PaymentMethod.OTHER,
                transaction_reference=None,  # Added
                # created/updated handled by default
            )

            session.add(new_payment)
            # Commit per payment or batch commit? Batch might be faster but harder to track errors.
            # Committing individually for now.
            try:
                await session.commit()
                await session.refresh(new_payment)

                # Ensure payment has a valid ID after commit
                _ensure_id_is_not_none(
                    new_payment.id, "Payment", "after database commit")
                if new_payment.id is None:
                    logger.error(
                        "Payment ID is None after commit - database operation failed")
                    continue  # Skip this payment response creation

                property_name = lease.property.name if lease.property else "Unknown Property"
                response = PaymentResponse(
                    id=new_payment.id, lease_id=new_payment.lease_id, tenant_id=str(
                        new_payment.tenant_id) if new_payment.tenant_id is not None else None,
                    amount=new_payment.amount, payment_date=new_payment.payment_date,
                    payment_method=new_payment.payment_method, status=new_payment.status,  # Use from model
                    transaction_reference=new_payment.transaction_reference, description=new_payment.description,  # Use from model
                    created_at=new_payment.created_at, updated_at=new_payment.updated_at,
                    tenant_name=tenant_name, property_name=property_name
                )
                created_payments_responses.append(response)
                logger.info("Created payment %s for lease %s",
                            new_payment.id, lease.id)
            except Exception as commit_err:
                logger.error("Error committing payment for lease %s: %s",
                             lease.id, commit_err, exc_info=True)
                await session.rollback()  # Rollback this specific payment attempt

        logger.info("Generated %s payments for user %s", len(
            created_payments_responses), current_user.id)
        return created_payments_responses

    except Exception as lease_proc_err:  # Catch errors during lease processing loop
        logger.error("Error processing leases for payment generation: %s",
                     lease_proc_err, exc_info=True)
        # Rollback might be needed if the session is in a bad state, but individual errors are handled above
        # await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during payment generation: {lease_proc_err}"
        )


@router.get("/outstanding-payments", response_model=list[PaymentResponse])
async def get_outstanding_payments(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[PaymentResponse]:
    """
    Retrieves outstanding payments for the current month, filtered by user role.

    Outstanding payments include those with status PENDING or OVERDUE and a payment date within the current month. Tenants receive only their own outstanding payments, landlords receive payments for their properties, and admins receive all outstanding payments. Returns a list of payment responses with associated tenant and property details.
    """
    today = datetime.now(UTC).date()
    month_start = date(today.year, today.month, 1)

    try:
        # Convert date to timezone-aware datetime for business date filtering
        start_datetime, end_datetime = date_to_utc_range(month_start, today)

        query = select(Payment).options(
            selectinload(getattr(Payment, "lease")).options(
                selectinload(getattr(Lease, "property")),
                selectinload(getattr(Lease, "tenant"))
            )
        ).where(
            and_(
                # Compare with timezone-aware datetime
                col(Payment.payment_date) >= start_datetime,
                # Added end range for current month
                col(Payment.payment_date) <= end_datetime,
                col(Payment.status).in_(
                    [PaymentStatus.PENDING, PaymentStatus.OVERDUE])  # Applied col()
            )
        )

        # Apply ownership filter
        if current_user.user_type == UserType.TENANT:
            query = query.where(col(Payment.tenant_id) ==
                                current_user.id)  # Applied col()
        elif current_user.user_type == UserType.LANDLORD:
            query = query.join(getattr(Payment, "lease")).join(getattr(Lease, "property")).where(
                col(Property.user_id) == current_user.id)  # Applied getattr & col()
        elif not current_user.is_admin:  # Deny other types if any exist
            return []

        query = query.order_by(col(Payment.payment_date).desc())
        result = await session.execute(query)
        payments = result.unique().scalars().all()

        # Format response
        payment_responses = []
        for p in payments:
            if p.id is None:
                logger.error(
                    "Outstanding payment ID is None from database query - data integrity issue")
                continue  # Skip this payment rather than failing the entire request
            tenant_name = f"{p.lease.tenant.first_name} {p.lease.tenant.last_name}".strip() if p.lease and p.lease.tenant and p.lease.tenant.first_name else (
                f"Tenant #{p.lease.tenant.id}" if p.lease and p.lease.tenant else "Unknown Tenant")
            property_name = p.lease.property.name if p.lease and p.lease.property else "Unknown Property"

            response = PaymentResponse(
                id=p.id, lease_id=p.lease_id, tenant_id=str(p.tenant_id) if p.tenant_id is not None else None, amount=p.amount,
                payment_date=p.payment_date,
                payment_method=p.payment_method, status=p.status,  # Use from model
                transaction_reference=p.transaction_reference, description=p.description, created_at=p.created_at,  # Use from model
                updated_at=p.updated_at, tenant_name=tenant_name, property_name=property_name
            )
            payment_responses.append(response)

        return payment_responses

    except Exception as e:
        logger.error("Error fetching outstanding payments for user %s: %s",
                     current_user.id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch outstanding payments: {str(e)}"
        )
