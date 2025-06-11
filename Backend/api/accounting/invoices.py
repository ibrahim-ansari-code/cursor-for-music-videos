import logging
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import inspect
from sqlmodel import col, select

# Needed for DEBUG flag in _infer_property_for_invoice
from Backend.config import settings

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.accounting.common import PaymentStatus
from Backend.models.accounting.invoice import Invoice
from Backend.models.enums import UserType
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.models.lease import Lease, LeaseStatus # Needed for tenant property inference
from Backend.utils.datetime_utils import date_to_utc_range, validate_business_datetime, validate_date_range
from .helpers import check_property_ownership

logger = logging.getLogger(__name__)
router = APIRouter()

# === API Models for Invoices ===
class InvoiceBase(BaseModel):
    invoice_number: str
    amount: Decimal
    description: str
    issue_date: datetime
    due_date: datetime
    status: PaymentStatus = PaymentStatus.PENDING
    property_id: int | None = None
    tenant_id: int | None = None # tenant_id in Invoice SQLModel is int

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    amount: Decimal | None = None
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

# === Helper Functions for Invoices ===
async def _infer_property_for_invoice(tenant: Tenant, current_user: User) -> int | None:
    """
    Attempts to determine the property ID associated with a tenant for invoice creation.
    
    Checks the tenant's current property and active leases, ensuring relationships are eagerly loaded to prevent inefficient queries. Returns the property ID if accessible by the current user (admin or property owner). Raises an HTTP 500 error if inference fails due to internal issues.
    """
    try:
        # Check if required relationships are eagerly loaded to prevent N+1 queries
        tenant_state = inspect(tenant)
        if tenant_state is not None:
            # Use 'in tenant_state.unloaded' for the most reliable check
            if "current_property" in tenant_state.unloaded:
                logger.error(
                    "tenant.current_property not eagerly loaded for tenant %s, which may cause N+1 queries.",
                    tenant.id
                )
                # In debug mode, fail fast to enforce the contract
                if settings.DEBUG:
                    raise RuntimeError(
                        f"tenant.current_property not eagerly loaded for tenant {tenant.id}. "
                        "Ensure selectinload(Tenant.current_property) is used in the query."
                    )
            
            if "leases" in tenant_state.unloaded:
                logger.error(
                    "tenant.leases not eagerly loaded for tenant %s, which may cause N+1 queries.",
                    tenant.id
                )
                # In debug mode, fail fast
                if settings.DEBUG:
                    raise RuntimeError(
                        f"tenant.leases not eagerly loaded for tenant {tenant.id}. "
                        "Ensure selectinload(Tenant.leases) is used in the query."
                    )
        
        # 1. Check the tenant's currently assigned property first.
        if tenant.current_property:
            if current_user.user_type == UserType.ADMIN or tenant.current_property.user_id == current_user.id:
                return tenant.current_property.id

        # 2. If no current property, check properties from the tenant's ACTIVE leases only.
        if tenant.leases:
            # Deterministically evaluate the *oldest* active lease first
            active_leases = sorted(
                (lease for lease in tenant.leases if lease.status == LeaseStatus.ACTIVE and lease.property),
                key=lambda lease: (lease.start_date or date.min)
            )
            for lease in active_leases:
                if current_user.user_type == UserType.ADMIN or lease.property.user_id == current_user.id:
                    return lease.property.id

    except Exception:
        logger.exception("Error inferring property for tenant %s", tenant.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to infer property for tenant – internal error."
        )

async def _apply_tenant_invoice_filters(
    filters: list, tenant_id: int | None, property_id: int | None, current_user: User, session: AsyncSession
):
    """
    Applies invoice query filters to restrict results to the current tenant user.
    
    Raises:
        HTTPException: If the user is not a tenant, attempts to access another tenant's invoices, or tries to filter by property.
    """
    tenant_query = select(Tenant).where(col(Tenant.user_id) == current_user.id)
    user_tenant = await session.scalar(tenant_query)
    
    if not user_tenant:
        raise HTTPException(status_code=403, detail="Not authorized to access these invoices.")
    
    if tenant_id and tenant_id != user_tenant.id:
        raise HTTPException(status_code=403, detail="Not authorized to access these invoices.")
    
    filters.append(col(Invoice.tenant_id) == user_tenant.id)
    
    if property_id:
        raise HTTPException(status_code=403, detail="Not authorized to filter invoices by property.")

async def _apply_landlord_invoice_filters(
    filters: list, property_id: int | None, tenant_id: int | None, current_user: User, session: AsyncSession
) -> bool:
    """
    Applies invoice filters to restrict results to those associated with properties owned by the landlord.
    
    Returns:
        True if the landlord owns properties and filters are applied; False if the landlord owns no properties.
        
    Raises:
        HTTPException: If a property_id is provided but the landlord does not own the specified property.
    """
    # Check if landlord has any properties at all (lightweight check)
    has_properties_query = select(Property.id).where(col(Property.user_id) == current_user.id).limit(1)
    has_properties = await session.scalar(has_properties_query)
    
    if not has_properties:
        return False

    if property_id:
        # Verify specific property ownership using subquery
        property_owned = await session.scalar(
            select(Property.id).where(
                and_(
                    col(Property.id) == property_id,
                    col(Property.user_id) == current_user.id
                )
            )
        )
        if not property_owned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this property.")
        filters.append(col(Invoice.property_id) == property_id)
        if tenant_id:
            filters.append(col(Invoice.tenant_id) == tenant_id)
    elif tenant_id:
        filters.append(col(Invoice.tenant_id) == tenant_id)
        # Use EXISTS correlated subquery for better performance and scalability
        filters.append(exists().where(
            and_(
                col(Property.id) == col(Invoice.property_id),
                col(Property.user_id) == current_user.id
            )
        ))
    else:
        # Use EXISTS correlated subquery for better performance and scalability
        filters.append(exists().where(
            and_(
                col(Property.id) == col(Invoice.property_id),
                col(Property.user_id) == current_user.id
            )
        ))
    
    return True

def _apply_admin_invoice_filters(filters: list, property_id: int | None, tenant_id: int | None):
    """
    Appends tenant and property filters to the invoice query for admin users.
    
    If tenant_id or property_id are provided, corresponding filters are added to the filters list.
    """
    if tenant_id:
        filters.append(col(Invoice.tenant_id) == tenant_id)
    if property_id:
        filters.append(col(Invoice.property_id) == property_id)


# === API Endpoints for Invoices ===

@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED) # Corresponds to POST /accounting/invoices
async def create_invoice(
    invoice_data: InvoiceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> InvoiceResponse:
    """
    Creates a new invoice for a property or tenant.
    
    Allows admin and landlord users to create an invoice, requiring either a property ID or tenant ID. If only a tenant ID is provided, attempts to infer the associated property. Validates property ownership, ensures due date is not before issue date, and persists the invoice to the database. Returns the created invoice details.
    
    Raises:
        HTTPException: If the user is unauthorized, required fields are missing, property ownership is invalid, date validation fails, or invoice creation encounters an error.
        
    Returns:
        The created invoice as an InvoiceResponse.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create invoices")

    # Consolidated validation for property_id and tenant_id
    if not invoice_data.property_id and not invoice_data.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'property_id' or 'tenant_id' must be provided to create an invoice."
        )

    final_property_id = invoice_data.property_id

    # If tenant_id is provided without a property_id, attempt to infer it
    if invoice_data.tenant_id and not final_property_id:
        tenant_query = select(Tenant).options(
            selectinload(getattr(Tenant, "leases")).selectinload(getattr(Lease, "property")),
            selectinload(getattr(Tenant, "current_property"))
        ).where(col(Tenant.id) == invoice_data.tenant_id)
        tenant = (await session.execute(tenant_query)).scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant with ID {invoice_data.tenant_id} not found")

        inferred_property_id = await _infer_property_for_invoice(tenant, current_user)
        
        if not inferred_property_id and current_user.user_type != UserType.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create invoice for tenant with no valid property link. Please assign the tenant to a property."
            )
        
        final_property_id = inferred_property_id

    # Enforce that a valid property_id is present before proceeding.
    if not final_property_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid 'property_id' is required to create an invoice and could not be inferred from the tenant."
        )

    # Now check ownership of the final property_id
    await check_property_ownership(final_property_id, session, current_user)
    
    # Update invoice_data with final property_id if it was inferred
    if final_property_id != invoice_data.property_id:
        invoice_data = invoice_data.model_copy(update={"property_id": final_property_id})

    try:
        invoice_data_dict = invoice_data.model_dump()
        if invoice_data_dict.get('issue_date') and isinstance(invoice_data_dict['issue_date'], datetime):
            invoice_data_dict['issue_date'] = validate_business_datetime(invoice_data_dict['issue_date'])
        if invoice_data_dict.get('due_date') and isinstance(invoice_data_dict['due_date'], datetime):
            invoice_data_dict['due_date'] = validate_business_datetime(invoice_data_dict['due_date'])
        
        issue = invoice_data_dict.get('issue_date')
        due   = invoice_data_dict.get('due_date')
        if issue and due and due < issue:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Due date cannot be earlier than issue date."
            )
        
        new_invoice = Invoice(**invoice_data_dict)
        session.add(new_invoice)
        await session.commit()
        await session.refresh(new_invoice)
        logger.info("Invoice %s created for tenant %s, property %s by user %s", 
                    new_invoice.id, new_invoice.tenant_id, new_invoice.property_id, current_user.id)
        return InvoiceResponse.model_validate(new_invoice)
    except Exception as e:
        await session.rollback()
        logger.exception("Error creating invoice")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to create invoice."
        ) from e

@router.get("", response_model=list[InvoiceResponse])
async def get_invoices(
    tenant_id: int | None = None,
    property_id: int | None = None,
    payment_status_filter: PaymentStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[InvoiceResponse]:
    """
    Retrieves a list of invoices filtered by user role, tenant, property, payment status, and date range.
    
    Validates and applies filters based on the current user's role:
    - Tenants can only view their own invoices.
    - Landlords can view invoices for properties or tenants they own.
    - Admins can view all invoices with optional tenant and property filters.
    
    Args:
        tenant_id: Optional tenant ID to filter invoices.
        property_id: Optional property ID to filter invoices.
        payment_status_filter: Optional payment status to filter invoices.
        start_date: Optional start date to filter invoices by issue date.
        end_date: Optional end date to filter invoices by issue date.
    
    Returns:
        A list of invoices matching the applied filters.
    """
    validate_date_range(start_date, end_date)

    query = (
        select(Invoice)
    .options(
        selectinload(getattr(Invoice, "property")),
        selectinload(getattr(Invoice, "tenant"))
    )
)
    filters = []

    if payment_status_filter:
        filters.append(col(Invoice.status) == payment_status_filter)
    if start_date:
        start_datetime, _ = date_to_utc_range(start_date, start_date)
        filters.append(col(Invoice.issue_date) >= start_datetime)
    if end_date:
        _, end_datetime = date_to_utc_range(end_date, end_date)
        filters.append(col(Invoice.issue_date) <= end_datetime)

    if current_user.user_type == UserType.TENANT:
        await _apply_tenant_invoice_filters(filters, tenant_id, property_id, current_user, session)
    elif current_user.user_type == UserType.LANDLORD:
        can_proceed = await _apply_landlord_invoice_filters(filters, property_id, tenant_id, current_user, session)
        if not can_proceed:
            return []
    elif current_user.user_type == UserType.ADMIN:
        _apply_admin_invoice_filters(filters, property_id, tenant_id)
    else:
        raise HTTPException(status_code=403, detail="Not authorized to access these invoices.")

    if filters:
        query = query.where(and_(*filters))
    
    query = query.order_by(col(Invoice.issue_date).desc())
    invoices_orm = (await session.execute(query)).scalars().all()
    return [InvoiceResponse.model_validate(inv) for inv in invoices_orm] 