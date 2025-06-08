"""Payments API router – endpoints and helper utilities for creating, retrieving,
updating and deleting payment records, plus role-based query helpers and receipt parsing."""
import logging
import functools
from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, field_validator
from sqlalchemy import and_, or_, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.accounting.common import PaymentStatus
from Backend.models.accounting.payment import Payment, PaymentMethod
from Backend.models.enums import UserType
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.utils.azure_blob import (delete_blob_by_url,
                                      upload_payment_receipt_to_blob)
from Backend.utils.datetime_utils import (create_audit_datetime,
                                          date_to_utc_range, utc_now,
                                          validate_business_datetime)
from Backend.utils.llm_utils import analyze_payment_receipt_content

from .helpers import (_ensure_id_is_not_none,
                      check_lease_ownership)

logger = logging.getLogger(__name__)
router = APIRouter()

# === Helper Functions for Payments ===
async def get_month_payments(session: AsyncSession, lease_id: int, month_date: date) -> bool:
    """
    Checks if any payment exists for a given lease within the specified month.
    
    Args:
        session: Async database session.
        lease_id: The ID of the lease to check payments for.
        month_date: A date within the month to check.
    
    Returns:
        True if at least one payment exists for the lease in the specified month, otherwise False.
    """
    month_start = month_date.replace(day=1)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
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

def _get_payment_method_enum(payment_method_value: PaymentMethod | str | None) -> PaymentMethod:
    """
    Converts a string or enum value to a PaymentMethod enum, defaulting to OTHER if input is None or invalid.
    
    Raises:
        HTTPException: If the input cannot be converted to a valid PaymentMethod.
    """
    if isinstance(payment_method_value, PaymentMethod):
        return payment_method_value
    if not payment_method_value:
        return PaymentMethod.OTHER
    try:
        # Handle being passed an enum *name* instead of value
        if isinstance(payment_method_value, str):
            try:
                # Trim whitespace and convert to uppercase for consistent matching
                normalized_value = payment_method_value.strip().upper()
                return PaymentMethod[normalized_value]
            except KeyError:
                pass
        return PaymentMethod(payment_method_value)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment_method '{payment_method_value}'."
        ) from e

def _get_tenant_display_name(tenant: Tenant | None) -> str:
    """
    Returns a formatted display name for a tenant, using their full name if available, or a fallback identifier if not.
    
    If the tenant is None, returns "Unknown Tenant". If the tenant has a first name, returns "FirstName LastName". Otherwise, returns "Tenant #<id>".
    """
    if not tenant:
        return "Unknown Tenant"
    if tenant.first_name:
        return f"{tenant.first_name} {tenant.last_name}".strip()
    return f"Tenant #{tenant.id}"

def _check_payment_ownership(payment: Payment, current_user: User) -> bool:
    """
    Determines whether the current user has permission to modify the specified payment.
    
    Admin users are always granted access. For non-admin users, access is allowed only if the user owns the property associated with the payment's lease and all related entities exist.
    
    Returns:
        True if the user can modify the payment; otherwise, False.
    """
    if current_user.is_admin:
        return True
    
    # Check for relationship existence before accessing attributes
    if not (payment.lease and payment.lease.property):
        return False

    # A landlord owns the payment if they own the associated property
    return payment.lease.property.user_id == current_user.id

# === API Models for Payments ===
class PaymentBase(BaseModel): # Not directly used by endpoints, but good for inheritance if needed
    amount: float
    payment_date: datetime
    payment_method: str
    status: PaymentStatus
    transaction_reference: str | None = None
    description: str | None = None
    lease_id: int
    tenant_id: int | None = None

    @field_validator('transaction_reference', 'description', mode='before')
    @staticmethod
    def empty_str_to_none(v: str | None) -> str | None:
        """
        Converts an empty string to None.
        
        Args:
            v: The input string or None.
        
        Returns:
            None if the input is an empty string; otherwise, returns the original value.
        """
        if v == "":
            return None
        return v

class PaymentCreate(BaseModel):
    lease_id: int
    amount: float
    payment_date: datetime | None = None
    payment_method: str | None = PaymentMethod.OTHER.value
    status: PaymentStatus | None = PaymentStatus.PENDING
    transaction_reference: str | None = None
    description: str | None = None
    tenant_name: str | None = None # Used for response, not directly for DB Payment object
    receipt_url: str | None = None

class PaymentUpdate(BaseModel):
    amount: float | None = None
    payment_date: datetime | None = None
    payment_method: str | None = None
    status: PaymentStatus | None = None
    transaction_reference: str | None = None
    description: str | None = None
    receipt_url: str | None = None

class PaymentResponse(BaseModel):
    id: int
    lease_id: int
    tenant_id: int | None = None
    amount: float
    payment_date: datetime | None = None
    payment_method: PaymentMethod | None = None
    status: PaymentStatus | None = None
    transaction_reference: str | None = None
    description: str | None = None
    receipt_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tenant_name: str | None = None
    property_name: str | None = None

    class Config:
        from_attributes = True

class PaginatedPaymentsResponse(BaseModel):
    items: list[PaymentResponse]
    has_more: bool

class PaymentReceiptParseDetails(BaseModel):
    payment_date: str | None = None
    subtotal_amount: float | None = None
    total_amount: float | None = None
    currency: str | None = None
    payment_method: str | None = None
    description_notes: str | None = None
    raw_text_preview: str | None = None

class PaymentReceiptParseResponse(BaseModel):
    receipt_url: str
    parsed_details: PaymentReceiptParseDetails
    message: str | None = None

# === Payment Query Helper Functions ===

def _build_payment_base_query() -> Select:
    """
    Constructs a SQLAlchemy select query for payments with eager loading of related lease, property, and tenant entities.
    """
    return select(Payment).options(
        selectinload(getattr(Payment, "lease")).options(
            selectinload(getattr(Lease, "property")),
            selectinload(getattr(Lease, "tenant"))
        )
    )

def _apply_common_payment_filters(query: Select, lease_id: int | None, payment_status: PaymentStatus | None, 
                                start_date: date | None, end_date: date | None) -> Select:
    """
                                Applies lease, status, and date range filters to a payment query.
                                
                                All date filters are converted to UTC using `date_to_utc_range` to ensure consistent timezone handling when filtering by payment date.
                                """
    filters = []
    
    if lease_id:
        filters.append(col(Payment.lease_id) == lease_id)
    if payment_status:
        filters.append(col(Payment.status) == payment_status)
    if start_date:
        # Convert date to UTC range for consistent timezone handling
        start_datetime, _ = date_to_utc_range(start_date, start_date)
        filters.append(col(Payment.payment_date) >= start_datetime)
    if end_date:
        # Convert date to UTC range for consistent timezone handling
        _, end_datetime = date_to_utc_range(end_date, end_date)
        filters.append(col(Payment.payment_date) <= end_datetime)
    
    if filters:
        query = query.where(and_(*filters))
    
    return query

async def _apply_tenant_payment_filters(query: Select, tenant_id: int | None, property_id: int | None, 
                                       current_user: User, session: AsyncSession) -> Select:
    """
                                       Applies tenant-specific filters to a payment query, restricting results to payments belonging to the current user's tenant profile.
                                       
                                       Raises:
                                           HTTPException: If the user lacks a tenant profile, attempts to access another tenant's payments, or tries to filter by property.
                                       """
    tenant_query = select(Tenant).where(col(Tenant.user_id) == current_user.id)
    user_tenant = await session.scalar(tenant_query)
    
    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No tenant profile found for user. Access denied."
        )
    
    if tenant_id and tenant_id != user_tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to access payments for other tenants."
        )
    
    if property_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Tenants cannot filter payments by property."
        )
    
    query = query.where(col(Payment.tenant_id) == user_tenant.id)
    return query

async def _check_for_orphaned_payments(session: AsyncSession, current_user: User, run_for_all_users: bool = False) -> dict:
    """
    Checks for payments that reference a lease but have missing or broken lease or property relationships.
    
    This function identifies "orphaned" payments—those with a lease_id but lacking a valid lease or property association. Payments without a lease_id are not considered orphaned. Returns a report indicating whether orphaned payments exist, the total count, the number of affected users, and up to 10 orphaned payment IDs. Handles both single-user and global scans based on the `run_for_all_users` flag. Logs warnings or errors if orphaned payments are found.
    """
    try:
        # Define base conditions for orphaned payments
        conditions = [
            col(Payment.lease_id).is_not(None),
            or_(
                col(Lease.id).is_(None),
                and_(
                    col(Lease.id).is_not(None),
                    col(Lease.property_id).is_not(None),
                    col(Property.id).is_(None)
                )
            )
        ]

        # Conditionally add the ownership filter
        if not run_for_all_users:
            conditions.append(
                or_(
                    col(Property.user_id) == current_user.id,
                    col(Property.user_id).is_(None)
                )
            )

        # Build the final query
        orphaned_query = select(Payment).outerjoin(
            getattr(Payment, "lease")
        ).outerjoin(
            getattr(Lease, "property")
        ).where(and_(*conditions))
        
        payments = (await session.execute(orphaned_query)).scalars().all()
        unique_payment_ids = {p.id for p in payments if p.id is not None}
        orphaned_count = len(unique_payment_ids)
        
        if orphaned_count > 0:
            orphaned_ids_list = [str(pid) for pid in unique_payment_ids]
            
            # Calculate actual number of affected users for global scans
            affected_user_ids = set()
            if run_for_all_users:
                # Count distinct users affected by orphaned payments using multiple strategies
                # to handle broken relationships gracefully
                for payment in payments:
                    user_id = None
                    
                    # Strategy 1: Use direct relationship if available
                    if payment.lease and payment.lease.property and payment.lease.property.user_id:
                        user_id = payment.lease.property.user_id
                    
                    # Strategy 2: If lease exists but property relationship is broken,
                    # try to find the property via a separate query
                    elif payment.lease_id and not user_id:
                        try:
                            # Query the lease and property directly using the lease_id
                            lease_query = select(Lease).options(
                                selectinload(getattr(Lease, "property"))
                            ).where(col(Lease.id) == payment.lease_id)
                            lease_result = await session.execute(lease_query)
                            lease_obj = lease_result.scalar_one_or_none()
                            if lease_obj and lease_obj.property:
                                user_id = lease_obj.property.user_id
                        except Exception:
                            # Don't let individual lookup failures break the overall count
                            pass
                    
                    # Strategy 3: If we have a tenant_id, try to find the user through tenant relationships
                    if not user_id and payment.tenant_id:
                        try:
                            # Find properties associated with this tenant
                            tenant_property_query = select(Property.user_id).join(
                                Lease, col(Lease.property_id) == col(Property.id)
                            ).where(col(Lease.tenant_id) == payment.tenant_id).distinct()
                            tenant_property_result = await session.execute(tenant_property_query)
                            property_user_ids = tenant_property_result.scalars().all()
                            # If there's exactly one user associated with this tenant, use it
                            if len(property_user_ids) == 1:
                                user_id = property_user_ids[0]
                        except Exception:
                            # Don't let individual lookup failures break the overall count
                            pass
                    
                    if user_id:
                        affected_user_ids.add(user_id)
                
                users_with_orphans_count = len(affected_user_ids)
                
                # Use appropriate logging for global scans
                logger.warning(
                    "Data integrity alert: Found %d unique orphaned lease-related payment(s) across %d user(s). "
                    "Payment IDs: %s. These payments reference lease_id but have broken lease/property relationships "
                    "and will not appear in landlord queries. Consider data cleanup.",
                    orphaned_count, users_with_orphans_count, ", ".join(orphaned_ids_list[:10])
                )
                if orphaned_count > 10:
                    logger.error(
                        "Critical data integrity issue: Found %d unique orphaned lease-related payments across %d user(s), "
                        "which suggests a systemic data quality problem. Immediate attention required.",
                        orphaned_count, users_with_orphans_count
                    )
            else:
                # Single-user scan logging
                users_with_orphans_count = 1
                logger.warning(
                    "Data integrity alert: Found %d unique orphaned lease-related payment(s) for user %s. "
                    "Payment IDs: %s. These payments reference lease_id but have broken lease/property relationships "
                    "and will not appear in landlord queries. Consider data cleanup.",
                    orphaned_count, current_user.id, ", ".join(orphaned_ids_list[:10])
                )
                if orphaned_count > 10:
                    logger.error(
                        "Critical data integrity issue: User %s has %d unique orphaned lease-related payments, "
                        "which suggests a systemic data quality problem. Immediate attention required.",
                        current_user.id, orphaned_count
                    )
            
            return {
                "orphaned_payments": True,
                "total_orphaned_count": orphaned_count,
                "users_with_orphans": users_with_orphans_count,
                "orphaned_payment_ids": orphaned_ids_list[:10]
            }

    except Exception as e:
        # Don't let monitoring failures break the main query
        logger.exception("Error during orphaned payment monitoring for user %s: %s", current_user.id, e)

    # Default return if no orphans or an error occurred
    return {
        "orphaned_payments": False,
        "total_orphaned_count": 0,
        "users_with_orphans": 0,
        "orphaned_payment_ids": []
    }

def _apply_landlord_payment_filters(query: Select, property_id: int | None, tenant_id: int | None, current_user: User) -> Select:
    """
    Filters a payment query to include only payments for leases owned by the landlord.
    
    Payments are restricted to those associated with properties owned by the current user. Optionally filters by property and tenant if specified. Orphaned payments lacking valid lease or property relationships are excluded.
    """
    # NOTE: Using inner joins here to enforce data integrity - this excludes payments
    # with missing lease or property relationships, which helps identify data inconsistencies.
    # Trade-off: orphaned payments (without proper lease/property links) won't appear in results,
    # but this is intentional to prevent displaying potentially corrupted data to landlords.
    
    # Define the subquery for owned leases separately before using it
    owned_leases_query = (
        select(Lease.id)
        .join(Property)
        .where(Property.user_id == current_user.id)
    )
    
    # Apply property-specific filter to the subquery if needed
    if property_id:
        owned_leases_query = owned_leases_query.where(Property.id == property_id)
    
    # Filter payments to only include those for owned leases
    owned = owned_leases_query.subquery()
    query = query.join(owned, owned.c.id == Payment.lease_id)
    
    # Apply tenant filter if specified (can be applied directly to Payment table)
    if tenant_id:
        query = query.where(col(Payment.tenant_id) == tenant_id)
    
    return query

def _apply_admin_payment_filters(query: Select, property_id: int | None, tenant_id: int | None) -> tuple[Select, bool]:
    """
    Applies property and tenant filters to a payment query for admin users.
    
    Returns:
        A tuple containing the modified query and a boolean flag indicating whether to continue processing.
    """
    filters = []
    
    if property_id:
        query = query.join(getattr(Payment, "lease"), isouter=True).join(getattr(Lease, "property"), isouter=True)
        filters.append(col(Property.id) == property_id)
    
    if tenant_id:
        filters.append(col(Payment.tenant_id) == tenant_id)
    
    if filters:
        query = query.where(and_(*filters))
    
    return query, True

def _build_payment_response_from_orm(payment_orm: Payment) -> PaymentResponse | None:
    """
    Constructs a PaymentResponse object from a Payment ORM instance, including tenant and property display names.
    
    Returns:
        A PaymentResponse with populated fields, or None if the payment has no ID.
    """
    if payment_orm.id is None:
        return None
    
    tenant_name = _get_tenant_display_name(payment_orm.lease.tenant if payment_orm.lease else None)
    property_name = payment_orm.lease.property.name if payment_orm.lease and payment_orm.lease.property else "Unknown Property"
    
    return PaymentResponse(
        id=payment_orm.id,
        lease_id=payment_orm.lease_id,
        tenant_id=payment_orm.tenant_id,
        amount=payment_orm.amount,
        payment_date=payment_orm.payment_date,
        payment_method=_get_payment_method_enum(payment_orm.payment_method),
        status=payment_orm.status,
        transaction_reference=payment_orm.transaction_reference,
        description=payment_orm.description,
        receipt_url=payment_orm.receipt_url,
        created_at=payment_orm.created_at,
        updated_at=payment_orm.updated_at,
        tenant_name=tenant_name,
        property_name=property_name
    )

# === API Endpoints for Payments ===

@router.post("/parse-receipt", response_model=PaymentReceiptParseResponse) # Renamed from /parse-payment-receipt
async def parse_payment_receipt(
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)]
) -> PaymentReceiptParseResponse:
    """
    Parses an uploaded payment receipt file and extracts structured payment details.
    
    Only landlords and admins are authorized to use this endpoint. Accepts PDF, JPG, or PNG files, uploads the receipt to cloud storage, and uses an external utility to extract payment information such as date, amount, and method. Returns the receipt URL and parsed details. Raises HTTP errors for unauthorized access, unsupported file types, invalid data, or external service failures.
    """
    if current_user.user_type not in [UserType.LANDLORD, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to parse payment receipts."
        )
    allowed_content_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed types are PDF, JPG, PNG."
        )
    try:
        file_content = await file.read()
        await file.seek(0)
        receipt_url = await upload_payment_receipt_to_blob(file, current_user.id)
        func_to_run = functools.partial(
            analyze_payment_receipt_content,
            file_content=file_content,
            filename=file.filename if file.filename is not None else "uploaded_receipt"
        )
        parsed_data_dict = await run_in_threadpool(func_to_run)
        parsed_details = PaymentReceiptParseDetails(**parsed_data_dict)
        return PaymentReceiptParseResponse(
            receipt_url=receipt_url,
            parsed_details=parsed_details,
            message="Receipt processed. Review extracted details."
        )
    except ValueError as ve:
        logger.exception("Validation error during receipt parsing for user %s: %s", current_user.id, ve)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid receipt data provided.") from ve
    except ConnectionError as ce:
        logger.exception("Azure Blob Storage connection error for user %s: %s", current_user.id, ce)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="External service is unavailable.") from ce
    except Exception as e:
        logger.exception("Error parsing payment receipt for user %s: %s", current_user.id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to parse payment receipt due to an internal error.") from e

@router.post("", response_model=PaymentResponse) # Corresponds to POST /accounting/payments
async def create_payment(
    payment: PaymentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> PaymentResponse:
    """
    Creates a new payment record for a specified lease.
    
    Only landlords and admins can create payments. Validates lease ownership, sets the payment date to the provided value or the current UTC time, and assigns the tenant from the lease. Commits the new payment to the database and returns the created payment details.
    
    Raises:
        HTTPException: If the user is a tenant, lease ownership is invalid, or a database error occurs.
        
    Returns:
        The created payment as a PaymentResponse.
    """
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenants cannot directly create payment records.")
    lease = await check_lease_ownership(payment.lease_id, session, current_user)
    actual_tenant_id_for_payment = lease.tenant.id if lease.tenant else None
    final_payment_date: datetime
    if payment.payment_date:
        final_payment_date = validate_business_datetime(payment.payment_date)
    else:
        final_payment_date = utc_now()

    payment_obj = Payment(
        lease_id=payment.lease_id,
        tenant_id=actual_tenant_id_for_payment,
        amount=payment.amount,
        payment_date=final_payment_date,
        status=payment.status or PaymentStatus.PENDING,
        description=payment.description,
        payment_method=_get_payment_method_enum(payment.payment_method),
        transaction_reference=payment.transaction_reference,
        receipt_url=payment.receipt_url
    )
    try:
        session.add(payment_obj)
        await session.commit()
        await session.refresh(payment_obj)
        _ensure_id_is_not_none(payment_obj.id, "Payment", "after database commit")
        
        # Eagerly load relationships on the new payment object for the response
        await session.refresh(payment_obj, attribute_names=["lease"])
        if payment_obj.lease:
            await session.refresh(payment_obj.lease, attribute_names=["property", "tenant"])

        payment_response = _build_payment_response_from_orm(payment_obj)
        if not payment_response:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Payment data integrity error")
        
        logger.info("Payment %s created for lease %s by user %s", payment_obj.id, lease.id, current_user.id)
        return payment_response
    except Exception as e:
        await session.rollback()
        logger.exception("Error creating payment for lease %s", payment.lease_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create payment.") from e

@router.get("", response_model=PaginatedPaymentsResponse) # Corresponds to GET /accounting/payments
async def get_payments(
    lease_id: int | None = None,
    property_id: int | None = None,
    tenant_id: int | None = None,
    payment_status: PaymentStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> PaginatedPaymentsResponse:
    """
    Retrieves a paginated list of payments filtered by user role and query parameters.
    
    Applies role-based access control and filters by lease, property, tenant, payment status, and date range. Returns payments ordered by payment date in descending order, with pagination support. Only authorized users can access relevant payments; unauthorized users receive an empty result.
     
    Args:
        lease_id: Filter payments by lease ID.
        property_id: Filter payments by property ID.
        tenant_id: Filter payments by tenant ID.
        payment_status: Filter payments by payment status.
        start_date: Filter payments with payment dates on or after this date.
        end_date: Filter payments with payment dates on or before this date.
        limit: Maximum number of payments to return (default 100, max 500).
        offset: Number of payments to skip for pagination.
    
    Returns:
        PaginatedPaymentsResponse: Contains a list of payment responses and a flag indicating if more results are available.
    """
    try:
        query = _build_payment_base_query()
        query = _apply_common_payment_filters(query, lease_id, payment_status, start_date, end_date)

        if current_user.user_type == UserType.TENANT:
            query = await _apply_tenant_payment_filters(query, tenant_id, property_id, current_user, session)
        elif current_user.user_type == UserType.LANDLORD:
            query = _apply_landlord_payment_filters(query, property_id, tenant_id, current_user)
        elif current_user.is_admin:
            query, should_continue = _apply_admin_payment_filters(query, property_id, tenant_id)
            if not should_continue:
                return PaginatedPaymentsResponse(items=[], has_more=False)
        else:
            return PaginatedPaymentsResponse(items=[], has_more=False)

        # Fetch one more item than the limit to determine if there's a next page
        query = query.order_by(col(Payment.payment_date).desc()).offset(offset).limit(limit + 1)
        payments_orm = (await session.execute(query)).unique().scalars().all()

        has_more = len(payments_orm) > limit
        # Trim the extra item if it exists
        items_to_return = payments_orm[:limit]

        payment_responses = []
        for payment_orm in items_to_return:
            response = _build_payment_response_from_orm(payment_orm)
            if response:
                payment_responses.append(response)
        
        return PaginatedPaymentsResponse(items=payment_responses, has_more=has_more)
    except Exception as e:
        logger.error("Error fetching payments for user %s: %s", current_user.id, str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch payments.") from e

@router.get("/diagnostics/run-integrity-check", status_code=status.HTTP_200_OK, summary="Run Orphaned Payments Integrity Check")
async def run_orphaned_payments_check(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Runs an integrity check to identify orphaned payments with missing lease or property records.
    
    Only accessible to admin users. Returns a summary report indicating whether orphaned payments exist and details about affected records. Raises HTTP 403 if the user is not an admin and HTTP 500 on internal errors.
    """
    logger.info("Admin user %s initiated orphaned payments integrity check", current_user.id)
    """
    (Admin-Only)
    This endpoint runs an integrity check to find 'orphaned' payments.
    Orphaned payments are those that have a `lease_id` but the corresponding
    lease or property record is missing, indicating a data integrity issue.
    
    Note: This is an expensive operation that may time out under heavy load.
    Consider implementing background task processing for production use.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this operation.")
    
    try:
        # We pass the full user object to the check function now
        report = await _check_for_orphaned_payments(session, current_user, run_for_all_users=True)
        
        if not report.get("orphaned_payments"):
            return {"status": "ok", "message": "No orphaned payments found."}
            
        return {
            "status": "warning",
            "message": f"Found {report['total_orphaned_count']} orphaned payment(s) across {report['users_with_orphans']} user(s).",
            "details": report
        }
    except Exception as e:
        logger.error("Error during integrity check: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Integrity check failed due to internal error"
        ) from e

@router.get("/outstanding", response_model=list[PaymentResponse]) # Renamed from /outstanding-payments
async def get_outstanding_payments_for_month( # Renamed function
    response: Response,
    limit: int = 100,  # Default limit of 100 records to prevent excessive data retrieval
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[PaymentResponse]:
    # Validate and cap the limit parameter to prevent excessive data retrieval
    """
    Retrieves outstanding payments for the current month, filtered by user role.
    
    Returns a list of payments with status PENDING or OVERDUE for the current month, limited to a maximum of 500 records. Tenants receive only their payments, landlords receive payments for their properties, and other users receive an empty list. Response headers indicate if the requested limit was adjusted.
    """
    original_limit = limit
    limit = max(1, min(limit, 500))
    
    # Inform user if limit was adjusted
    if limit != original_limit:
        response.headers["X-Applied-Limit"] = str(limit)
        response.headers["X-Original-Limit"] = str(original_limit)
        response.headers["X-Limit-Adjusted"] = "true"
        
    today = utc_now().date()
    month_start = date(today.year, today.month, 1)
    start_datetime, _ = date_to_utc_range(month_start, month_start)  # Only need start of month

    try:
        query = select(Payment).options(
            selectinload(getattr(Payment, "lease")).options(
                selectinload(getattr(Lease, "property")),
                selectinload(getattr(Lease, "tenant"))
            )
        ).where(
            and_(
                col(Payment.payment_date) >= start_datetime,
                col(Payment.status).in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE])
            )
        )
        if current_user.user_type == UserType.TENANT:
            tenant_query = select(Tenant).where(col(Tenant.user_id) == current_user.id)
            user_tenant = await session.scalar(tenant_query)
            if not user_tenant:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="No tenant profile found for user.")
            query = query.where(col(Payment.tenant_id) == user_tenant.id)
        elif current_user.user_type == UserType.LANDLORD:
            query = query.join(getattr(Payment, "lease")).join(getattr(Lease, "property")).where(col(Property.user_id) == current_user.id)
        elif not current_user.is_admin:
            return []

        query = query.order_by(col(Payment.payment_date).desc()).limit(limit)
        payments = (await session.execute(query)).unique().scalars().all()
        payment_responses = []
        for p in payments:
            payment_response = _build_payment_response_from_orm(p)
            if payment_response:
                payment_responses.append(payment_response)
        return payment_responses
    except Exception as e:
        logger.error("Error fetching outstanding payments for user %s: %s", current_user.id, str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch outstanding payments.") from e 

@router.get("/{payment_id}", response_model=PaymentResponse) # Corresponds to GET /accounting/payments/{payment_id}
async def get_payment(
    payment_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> PaymentResponse:
    """
    Retrieves a payment by its ID with related lease, property, and tenant details.
    
    Enforces role-based access control: tenants can access only their own payments, landlords only payments for their properties, and admins have unrestricted access. Raises HTTP 404 if the payment does not exist, HTTP 403 if access is unauthorized, and HTTP 500 if payment data integrity is compromised.
    
    Returns:
        PaymentResponse: The payment details including related lease, property, and tenant information.
    """
    query = select(Payment).options(
        selectinload(getattr(Payment, "lease")).options(
            selectinload(getattr(Lease, "property")),
            selectinload(getattr(Lease, "tenant"))
        )
    ).where(col(Payment.id) == payment_id)
    payment = (await session.execute(query)).unique().scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment {payment_id} not found")

    if current_user.user_type == UserType.TENANT:
        tenant_query = select(Tenant).where(col(Tenant.user_id) == current_user.id)
        user_tenant = await session.scalar(tenant_query)
        if not user_tenant or payment.tenant_id != user_tenant.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    elif current_user.user_type == UserType.LANDLORD:
        if not payment.lease or not payment.lease.property or payment.lease.property.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    elif not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    payment_response = _build_payment_response_from_orm(payment)
    if not payment_response:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Payment data integrity error")
    
    return payment_response

@router.put("/{payment_id}", response_model=PaymentResponse) # Corresponds to PUT /accounting/payments/{payment_id}
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> PaymentResponse:
    """
    Updates an existing payment record with new data.
    
    Only landlords and admins can update payments. Validates user authorization and payment ownership, applies provided updates, and refreshes related entities before returning the updated payment response.
    
    Args:
        payment_id: The ID of the payment to update.
        payment_data: The fields to update in the payment record.
    
    Returns:
        The updated payment as a PaymentResponse.
    
    Raises:
        HTTPException: If the payment is not found, the user is unauthorized, or an error occurs during the update.
    """
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenants cannot update payment records.")

    query = select(Payment).options(
        selectinload(getattr(Payment, "lease")).options(
            selectinload(getattr(Lease, "property")),
            selectinload(getattr(Lease, "tenant"))
        )
    ).where(col(Payment.id) == payment_id)
    payment = (await session.execute(query)).scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment {payment_id} not found")

    if not _check_payment_ownership(payment, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this payment")

    payment_data_dict = payment_data.model_dump(exclude_unset=True)
    for key, value in payment_data_dict.items():
        if key == "payment_method" and value is not None:
            setattr(payment, key, _get_payment_method_enum(value))
        elif key == "payment_date" and value is not None:
            setattr(payment, key, validate_business_datetime(value))
        elif value is not None:
            setattr(payment, key, value)
    payment.updated_at = create_audit_datetime()

    try:
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        # Refresh related objects for response
        if payment.lease:
            await session.refresh(payment.lease)
            if payment.lease.property:
                await session.refresh(payment.lease.property)
            if payment.lease.tenant:
                await session.refresh(payment.lease.tenant)
        
        logger.info("Payment %s updated by user %s", payment.id, current_user.id)
        
        payment_response = _build_payment_response_from_orm(payment)
        if not payment_response:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Payment data integrity error")

        return payment_response
    except Exception as e:
        await session.rollback()
        logger.error("Error updating payment %s: %s", payment_id, str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update payment.") from e

@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT) # Corresponds to DELETE /accounting/payments/{payment_id}
async def delete_payment(
    payment_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Deletes a payment record by its ID after verifying user authorization.
    
    Raises:
        HTTPException: If the payment does not exist, the user is not authorized, or a deletion error occurs.
    """
    query = select(Payment).options(
        selectinload(getattr(Payment, "lease")).options(
            selectinload(getattr(Lease, "property"))
        )
    ).where(col(Payment.id) == payment_id)
    payment_to_delete = (await session.execute(query)).unique().scalar_one_or_none()

    if not payment_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment {payment_id} not found")

    if not _check_payment_ownership(payment_to_delete, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this payment")

    receipt_url_to_delete = payment_to_delete.receipt_url
    try:
        await session.delete(payment_to_delete)
        await session.commit()
        logger.info(f"Payment {payment_id} deleted successfully by user {current_user.id}")
        if receipt_url_to_delete:
            logger.info(f"Attempting to delete receipt blob: {receipt_url_to_delete}")
            try:
                await delete_blob_by_url(receipt_url_to_delete)
                logger.info(f"Successfully deleted blob {receipt_url_to_delete} from Azure Storage.")
            except Exception as blob_del_exc:
                 logger.warning(f"Could not delete blob {receipt_url_to_delete} from Azure Storage: {blob_del_exc}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("Error deleting payment %s: %s", payment_id, str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete payment.") from e

@router.post("/generate-due", response_model=list[PaymentResponse]) # Renamed from /generate-due-payments
async def generate_due_payments_for_month( # Renamed function
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[PaymentResponse]:
    """
    Generates due payments for the current month for all active leases without existing payments.
    
    Only accessible to landlords and admins. For each active lease owned by the user (or all leases for admins), creates a pending payment for the current month's rent if one does not already exist. Returns a list of created payment responses. Raises HTTP 403 if unauthorized and HTTP 500 on processing errors.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    today = datetime.now(utc_now().tzinfo).date() # Ensure today is timezone aware like utc_now()
    current_month = date(today.year, today.month, 1)
    logger.info("Generating payments for %s by user %s", current_month, current_user.id)

    lease_query = select(Lease).options(
        selectinload(getattr(Lease, "property")),
        selectinload(getattr(Lease, "tenant"))
    ).where(
        and_(
            col(Lease.start_date) <= today,
            or_(col(Lease.end_date) >= today, col(Lease.end_date).is_(None)),
            col(Lease.status) == LeaseStatus.ACTIVE
        )
    )
    if current_user.user_type == UserType.LANDLORD:
        lease_query = lease_query.join(Property, col(Lease.property_id) == col(Property.id)).where(col(Property.user_id) == current_user.id)

    try:
        active_leases = (await session.execute(lease_query)).scalars().unique().all()
        logger.info("Found %s active leases for user %s", len(active_leases), current_user.id)
        created_payments_responses = []

        for lease in active_leases:
            if lease.id is None: continue
            if await get_month_payments(session, lease.id, current_month):
                logger.info("Payment exists for lease %s, skipping.", lease.id)
                continue

            tenant_name = "Unknown Tenant"
            actual_tenant_id_for_payment: int | None = None
            if lease.tenant and lease.tenant.id:
                actual_tenant_id_for_payment = lease.tenant.id
                tenant_name = _get_tenant_display_name(lease.tenant)
            else:
                logger.warning("Tenant or tenant ID missing for lease %s. Skipping.", lease.id)
                continue
            
            new_payment = Payment(
                lease_id=lease.id, tenant_id=actual_tenant_id_for_payment, amount=lease.monthly_rent,
                payment_date=utc_now(), status=PaymentStatus.PENDING,
                description=f"Monthly rent payment for {tenant_name}",
                payment_method=PaymentMethod.OTHER
            )
            session.add(new_payment)
            try:
                await session.commit()
                await session.refresh(new_payment)
                _ensure_id_is_not_none(new_payment.id, "Payment", "after commit")
                
                # Eagerly load relationships for the response
                await session.refresh(new_payment, attribute_names=["lease"])
                if new_payment.lease:
                    await session.refresh(new_payment.lease, attribute_names=["property", "tenant"])

                payment_response = _build_payment_response_from_orm(new_payment)
                if payment_response:
                    created_payments_responses.append(payment_response)
                logger.info("Created payment %s for lease %s", new_payment.id, lease.id)
            except Exception as commit_err:
                logger.error("Error committing payment for lease %s: %s", lease.id, commit_err, exc_info=True)
                await session.rollback()
        
        logger.info("Generated %s payments for user %s", len(created_payments_responses), current_user.id)
        return created_payments_responses
    except Exception as lease_proc_err:
        logger.error("Error processing leases for payment generation: %s", lease_proc_err, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate due payments.") from lease_proc_err
