"""Helper functions for invoice operations."""
import logging
from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, inspect, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from Backend.config import settings
from Backend.models.accounting.invoice import Invoice
from Backend.models.enums import UserType
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.user import User


logger = logging.getLogger(__name__)


async def check_invoice_ownership(
    invoice: Invoice,
    current_user: User,
    session: AsyncSession
) -> None:
    """
    Checks if the current user has permission to access/modify an invoice.
    
    Args:
        invoice: The invoice to check ownership for
        current_user: The user making the request
        session: Database session
        
    Raises:
        HTTPException: If user doesn't have permission
    """
    if current_user.user_type == UserType.ADMIN:
        return  # Admins can access all invoices
    
    if current_user.user_type == UserType.TENANT:
        # Tenants can only access their own invoices
        tenant_query = select(Tenant).where(col(Tenant.user_id) == current_user.id)
        user_tenant = await session.scalar(tenant_query)
        if not user_tenant or invoice.tenant_id != user_tenant.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this invoice"
            )
    
    elif current_user.user_type == UserType.LANDLORD:
        # Landlords can only access invoices for their properties
        if invoice.property_id:
            property_query = select(Property).where(
                and_(
                    col(Property.id) == invoice.property_id,
                    col(Property.user_id) == current_user.id
                )
            )
            property_owned = await session.scalar(property_query)
            if not property_owned:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this invoice"
                )
        # Allow access to invoices with NULL property_id (unassigned invoices)


def build_invoice_response(invoice: Invoice) -> dict:
    """
    Builds a standardized invoice response dictionary.
    
    Args:
        invoice: The invoice ORM object
        
    Returns:
        Dictionary with invoice data formatted for API response
    """
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "amount": invoice.amount,  # Keep as Decimal to preserve precision
        "description": invoice.description,
        "issue_date": invoice.issue_date.isoformat(),
        "due_date": invoice.due_date.isoformat(),
        "status": invoice.status.value if hasattr(invoice.status, 'value') else invoice.status,
        "property_id": invoice.property_id,
        "tenant_id": invoice.tenant_id,
        "quickbooks_id": invoice.quickbooks_id,
        "last_synced_at": invoice.last_synced_at.isoformat() if invoice.last_synced_at else None,
        "created_at": invoice.created_at.isoformat(),
        "updated_at": invoice.updated_at.isoformat(),
        # Include related data if loaded
        "property": {
            "id": invoice.property.id,
            "name": invoice.property.name
        } if invoice.property else None,
        "tenant": {
            "id": invoice.tenant.id,
            "full_name": f"{invoice.tenant.first_name} {invoice.tenant.last_name}".strip()
        } if invoice.tenant else None
    }


async def infer_property_for_invoice(tenant: Tenant, current_user: User) -> int | None:
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

    except RuntimeError:
        # Re-raise RuntimeError in debug mode to preserve debugging info
        if settings.DEBUG:
            raise
        # Convert to HTTP error in production
        logger.exception("Error inferring property for tenant %s", tenant.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to infer property for tenant – internal error."
        )
    except Exception:
        logger.exception("Error inferring property for tenant %s", tenant.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to infer property for tenant – internal error."
        )
    
    # Explicit return None if no property is found
    return None


async def apply_tenant_invoice_filters(
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access these invoices.")
    
    if tenant_id and tenant_id != user_tenant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access these invoices.")
    
    filters.append(col(Invoice.tenant_id) == user_tenant.id)
    
    if property_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to filter invoices by property.")


async def apply_landlord_invoice_filters(
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
        # When no specific filters, include both:
        # 1. Invoices with NULL property_id (unassigned invoices)
        # 2. Invoices with property_id matching landlord's properties
        filters.append(or_(
            col(Invoice.property_id).is_(None),
            exists().where(
                and_(
                    col(Property.id) == col(Invoice.property_id),
                    col(Property.user_id) == current_user.id
                )
            )
        ))
    
    return True


def apply_admin_invoice_filters(filters: list, property_id: int | None, tenant_id: int | None):
    """
    Appends tenant and property filters to the invoice query for admin users.
    
    If tenant_id or property_id are provided, corresponding filters are added to the filters list.
    """
    if tenant_id:
        filters.append(col(Invoice.tenant_id) == tenant_id)
    if property_id:
        filters.append(col(Invoice.property_id) == property_id)
