"""Service layer for payments - contains all business logic for payment operations."""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from Backend.models.accounting.common import PaymentStatus
from Backend.models.accounting.payment import Payment, PaymentMethod
from Backend.models.enums import UserType
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.utils.azure_blob import upload_payment_receipt_to_blob, generate_secure_document_url
from Backend.utils.datetime_utils import (create_audit_datetime,
                                          date_to_utc_range, utc_now,
                                          validate_business_datetime)
from Backend.llm.receipt_parser import analyze_payment_receipt_content

from Backend.utils.file_validation import validate_file_from_upload

from Backend.api.accounting.helpers import (
    _ensure_id_is_not_none,
    check_lease_ownership,
)
from Backend.utils.tax_utils import quantize_2dp

from .helpers import (
    get_payment_method_enum,
    get_tenant_display_name,
    check_payment_ownership,
    build_payment_response_from_orm,
)
from .queries import (
    get_month_payments,
    build_payments_query,
    check_for_orphaned_payments,
)
from .schemas import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaginatedPaymentsResponse,
    PaymentReceiptParseDetails,
    PaymentReceiptParseResponse,
    CSVPaymentImportResult,
    CSVImportError,
)
from .service_batch import prepare_payment_batch, bulk_create_payments, check_duplicate_payments
from Backend.config import settings

# Constants for commonly used payment status combinations
OUTSTANDING_PAYMENT_STATUSES = (PaymentStatus.PENDING, PaymentStatus.OVERDUE)

logger = logging.getLogger(__name__)

async def create_payment(
    payment: PaymentCreate,
    session: AsyncSession,
    current_user: User
) -> PaymentResponse:
    """
    Creates a new payment record for a specified lease.

    Only landlords and admins are permitted to create payments. Validates lease ownership,
    assigns the tenant from the lease, and sets the payment date to the provided value or the current UTC time.
    """
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Tenants cannot directly create payment records.")

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
        payment_method=get_payment_method_enum(payment.payment_method),
        transaction_reference=payment.transaction_reference,
        receipt_url=payment.receipt_url,
        reduction_amount=payment.reduction_amount,
        reduction_reason=payment.reduction_reason
    )

    try:
        session.add(payment_obj)
        await session.commit()
        await session.refresh(payment_obj)
        _ensure_id_is_not_none(payment_obj.id, "Payment",
                               "after database commit")
        await session.refresh(payment_obj, attribute_names=["lease"])
        if payment_obj.lease:
            await session.refresh(payment_obj.lease, attribute_names=["property", "tenant"])

        payment_response = build_payment_response_from_orm(payment_obj)
        if not payment_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Payment data integrity error")

        logger.info("Payment %s created for lease %s by user %s",
                    payment_obj.id, lease.id, current_user.id)
        return payment_response
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.exception(
            "Error creating payment for lease %s", payment.lease_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to create payment.") from e


async def get_payments(
    session: AsyncSession,
    current_user: User,
    lease_id: int | None = None,
    property_id: int | None = None,
    tenant_id: int | None = None,
    payment_status: PaymentStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    offset: int = 0
) -> PaginatedPaymentsResponse:
    """
    Retrieves a paginated list of payments filtered by user role and query parameters.

    Applies role-based access control and filters by lease, property, tenant, payment status, and date range.
    Returns payments ordered by payment date in descending order, with pagination support.
    """
    try:
        # Use the new unified query builder
        query = await build_payments_query(
            session=session,
            current_user=current_user,
            lease_id=lease_id,
            property_id=property_id,
            tenant_id=tenant_id,
            payment_status=payment_status,
            start_date=start_date,
            end_date=end_date
        )

        # Apply ordering and pagination
        query = query.order_by(col(Payment.payment_date).desc()).offset(
            offset).limit(limit + 1)
        payments_orm = (await session.execute(query)).unique().scalars().all()

        has_more = len(payments_orm) > limit
        items_to_return = payments_orm[:limit]

        payment_responses = []
        for payment_orm in items_to_return:
            response = build_payment_response_from_orm(payment_orm)
            if response:
                payment_responses.append(response)

        return PaginatedPaymentsResponse(items=payment_responses, has_more=has_more)
    except HTTPException:
        # Re-raise HTTP exceptions (from tenant access checks, etc.)
        raise
    except Exception as e:
        logger.exception(
            "Error fetching payments for user %s", current_user.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to fetch payments.") from e


async def get_payment_by_id(
    payment_id: int,
    session: AsyncSession,
    current_user: User
) -> PaymentResponse:
    """
    Retrieves a payment by ID with related lease, property, and tenant information.

    Enforces role-based access control: tenants can access only their own payments,
    landlords only payments for their properties, and admins have unrestricted access.
    """
    query = select(Payment).options(
        selectinload(getattr(Payment, "lease")).options(
            selectinload(getattr(Lease, "property")),
            selectinload(getattr(Lease, "tenant"))
        )
    ).where(col(Payment.id) == payment_id)
    payment = (await session.execute(query)).unique().scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Payment {payment_id} not found")

    if current_user.user_type == UserType.TENANT:
        tenant_query = select(Tenant).where(
            col(Tenant.user_id) == current_user.id)
        user_tenant = await session.scalar(tenant_query)
        if not user_tenant or payment.tenant_id != user_tenant.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    elif current_user.user_type == UserType.LANDLORD:
        if not payment.lease or not payment.lease.property or payment.lease.property.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    elif not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    payment_response = build_payment_response_from_orm(payment)
    if not payment_response:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Payment data integrity error")

    return payment_response


async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    session: AsyncSession,
    current_user: User
) -> PaymentResponse:
    """
    Updates an existing payment record with new data.

    Only landlords and admins can update payments. Validates user authorization and payment ownership,
    applies provided updates, and refreshes related entities before returning the updated payment response.
    """
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Tenants cannot update payment records.")

    query = select(Payment).options(
        selectinload(getattr(Payment, "lease")).options(
            selectinload(getattr(Lease, "property")),
            selectinload(getattr(Lease, "tenant"))
        )
    ).where(col(Payment.id) == payment_id)
    payment = (await session.execute(query)).scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Payment {payment_id} not found")

    if not check_payment_ownership(payment, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to update this payment")

    payment_data_dict = payment_data.model_dump(exclude_unset=True)
    for key, value in payment_data_dict.items():
        if key == "payment_method" and value is not None:
            setattr(payment, key, get_payment_method_enum(value))
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

        logger.info("Payment %s updated by user %s",
                    payment.id, current_user.id)

        payment_response = build_payment_response_from_orm(payment)
        if not payment_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Payment data integrity error")

        return payment_response
    except Exception as e:
        await session.rollback()
        logger.exception("Error updating payment %s", payment_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to update payment.") from e


async def delete_payment(
    payment_id: int,
    session: AsyncSession,
    current_user: User
) -> str | None:
    """
    Deletes a payment by its ID after verifying user authorization.

    Returns the receipt_url if one exists (for background deletion), or None.
    Raises appropriate HTTPExceptions for not found or unauthorized cases.
    """
    query = select(Payment).options(
        selectinload(getattr(Payment, "lease")).options(
            selectinload(getattr(Lease, "property"))
        )
    ).where(col(Payment.id) == payment_id)
    payment_to_delete = (await session.execute(query)).unique().scalar_one_or_none()

    if not payment_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Payment {payment_id} not found")

    if not check_payment_ownership(payment_to_delete, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to delete this payment")

    receipt_url_to_delete = payment_to_delete.receipt_url

    try:
        await session.delete(payment_to_delete)
        await session.commit()
        logger.info("Payment %s deleted successfully by user %s",
                    payment_id, current_user.id)
        return receipt_url_to_delete
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.exception("Error deleting payment %s", payment_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to delete payment.") from e


async def get_outstanding_payments_for_month(
    session: AsyncSession,
    current_user: User,
    limit: int = 100,
    property_id: int | None = None
) -> list[PaymentResponse]:
    """
    Retrieves outstanding payments for the current month based on user role.

    Returns payments with status PENDING or OVERDUE for the current month,
    optionally filtered by property_id. The provided limit will be capped between 1 and 500.

    Args:
        session: Database session
        current_user: Current authenticated user
        limit: Maximum number of records to return (will be capped between 1 and 500)
        property_id: Optional property ID to filter payments to a specific property

    Returns:
        List of outstanding PaymentResponse objects for the current month
    """
    # Enforce limit boundaries: minimum 1, maximum 500
    limit = max(1, min(limit, 500))

    today = utc_now().date()
    month_start = date(today.year, today.month, 1)

    try:
        # Use the unified query builder with specific filters for outstanding payments
        query = await build_payments_query(
            session=session,
            current_user=current_user,
            property_id=property_id,  # Filter by property if specified
            # Don't set payment_status here since we'll use IN clause below
            start_date=month_start
        )

        # Apply the status filter to include both PENDING and OVERDUE
        query = query.where(
            col(Payment.status).in_(OUTSTANDING_PAYMENT_STATUSES)
        )

        # Apply ordering and limit
        query = query.order_by(col(Payment.payment_date).desc()).limit(limit)

        payments = (await session.execute(query)).unique().scalars().all()

        payment_responses = []
        for p in payments:
            payment_response = build_payment_response_from_orm(p)
            if payment_response:
                payment_responses.append(payment_response)

        return payment_responses
    except HTTPException:
        # Re-raise HTTP exceptions (from tenant access checks, etc.)
        raise
    except Exception as e:
        logger.exception(
            "Error fetching outstanding payments for user %s", current_user.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to fetch outstanding payments.") from e


async def generate_due_payments_for_month(
    session: AsyncSession,
    current_user: User
) -> list[PaymentResponse]:
    """
    Generates pending payments for the current month's rent for all active leases without existing payments.

    Accessible only to landlords and admins. For each active lease owned by the user (or all leases for admins),
    creates a pending payment for the current month if one does not already exist.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    today = utc_now().date()
    current_month = date(today.year, today.month, 1)
    logger.info("Generating payments for %s by user %s",
                current_month, current_user.id)

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
        lease_query = lease_query.join(Property, col(Lease.property_id) == col(
            Property.id)).where(col(Property.user_id) == current_user.id)

    try:
        active_leases = (await session.execute(lease_query)).scalars().unique().all()
        logger.info("Found %s active leases for user %s",
                    len(active_leases), current_user.id)

        payments_to_add = []
        for lease in active_leases:
            if lease.id is None:
                continue
            if await get_month_payments(session, lease.id, current_month):
                logger.info("Payment exists for lease %s, skipping.", lease.id)
                continue

            actual_tenant_id_for_payment = lease.tenant.id if lease.tenant and lease.tenant.id else None
            if not actual_tenant_id_for_payment:
                logger.warning(
                    "Tenant or tenant ID missing for lease %s. Skipping.", lease.id)
                continue

            tenant_name = get_tenant_display_name(lease.tenant)

            new_payment = Payment(
                lease_id=lease.id,
                tenant_id=actual_tenant_id_for_payment,
                amount=quantize_2dp(Decimal(str(lease.monthly_rent))),
                payment_date=utc_now(),
                status=PaymentStatus.PENDING,
                description=f"Monthly rent payment for {tenant_name}",
                payment_method=PaymentMethod.OTHER,
            )
            session.add(new_payment)
            payments_to_add.append(new_payment)

        if not payments_to_add:
            return []

        created_payments_responses = []
        try:
            await session.commit()
            for payment in payments_to_add:
                await session.refresh(payment)
                _ensure_id_is_not_none(payment.id, "Payment", "after commit")

                await session.refresh(payment, attribute_names=["lease"])
                if payment.lease:
                    await session.refresh(payment.lease, attribute_names=["property", "tenant"])

                payment_response = build_payment_response_from_orm(payment)
                if payment_response:
                    created_payments_responses.append(payment_response)
                logger.info("Created payment %s for lease %s",
                            payment.id, payment.lease_id)
        except Exception:
            logger.exception(
                "Error during batch commit of generated payments for user %s", current_user.id)
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create one or more due payments during database commit.",
            )

        logger.info("Generated %d payments for user %s", len(
            created_payments_responses), current_user.id)
        return created_payments_responses
    except Exception as lease_proc_err:
        logger.exception(
            "Error processing leases for payment generation for user %s", current_user.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to generate due payments.") from lease_proc_err


async def parse_payment_receipt(
    file: UploadFile,
    current_user: User
) -> PaymentReceiptParseResponse:
    """
    Parses an uploaded payment receipt file and extracts structured payment details.

    Only landlords and admins are authorized to use this function. Accepts PDF, JPG, or PNG files up to 10 MB,
    uploads the receipt to cloud storage, and analyzes its content to extract payment information.
    """
    if current_user.user_type not in [UserType.LANDLORD, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to parse payment receipts."
        )

    try:
        # Use secure file validation with magic number checking
        file_content, validated_mime_type = await validate_file_from_upload(file, file.content_type)
        logger.info("File validated: declared=%s, detected=%s",
                    file.content_type, validated_mime_type)

        receipt_url = await upload_payment_receipt_to_blob(file, current_user.id)

        parsed_data_dict: dict[str, Any] = await analyze_payment_receipt_content(
            file_content=file_content,
            filename=file.filename if file.filename is not None else "uploaded_receipt"
        )

        parsed_details = PaymentReceiptParseDetails(**parsed_data_dict)
        return PaymentReceiptParseResponse(
            receipt_url=receipt_url,
            parsed_details=parsed_details,
            message="Receipt processed. Review extracted details."
        )
    except ValueError as ve:
        logger.exception(
            "File validation or data parsing error during payment receipt parsing")
        # Check if it's a file validation error (more specific error message)
        if "file" in str(ve).lower() or "mime" in str(ve).lower() or "size" in str(ve).lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"File validation failed: {str(ve)}") from ve
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid receipt data provided.") from ve
    except ConnectionError as ce:
        logger.exception(
            "Azure Blob Storage connection error for user %s: %s", current_user.id, ce)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="External service is unavailable.") from ce
    except Exception as e:
        logger.exception(
            "Error parsing payment receipt for user %s", current_user.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to parse payment receipt due to an internal error.") from e


async def generate_receipt_secure_url(
    receipt_url: str,
    current_user: User
) -> dict:
    """
    Generate a time-limited SAS token URL for payment receipt access.
    
    Args:
        receipt_url: The Azure Blob URL of the receipt
        current_user: Current authenticated user
        
    Returns:
        Dict with secure_url, expires_at, expires_in_seconds
    """
    # Authorization check
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access payment receipts."
        )
    
    try:
        # Generate secure URL with SAS token
        url_data = await generate_secure_document_url(
            blob_url=receipt_url,
            user_id=current_user.id,
            document_id=receipt_url,  # Use URL as identifier for logging
            expires_in_hours=1,
            client_ip=None,  # No IP restriction for browser-loaded images
        )
        
        return url_data
        
    except Exception as e:
        logger.error(f"Error generating secure URL for payment receipt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate secure URL: {str(e)}"
        )


async def run_orphaned_payments_check(
    session: AsyncSession,
    current_user: User
) -> dict[str, Any]:
    """
    (Admin-Only) Runs an integrity check to find 'orphaned' payments.

    Orphaned payments are those that have a `lease_id` but the corresponding
    lease or property record is missing, indicating a data integrity issue.
    """
    logger.info(
        "Admin user %s initiated orphaned payments integrity check", current_user.id)

    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized for this operation.")

    try:
        report = await check_for_orphaned_payments(session, current_user, run_for_all_users=True)

        if not report.get("orphaned_payments"):
            return {"status": "ok", "message": "No orphaned payments found."}

        return {
            "status": "warning",
            "message": f"Found {report['total_orphaned_count']} orphaned payment(s) across {report['users_with_orphans']} user(s).",
            "details": report
        }
    except Exception as e:
        logger.exception("Error during integrity check")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Integrity check failed due to internal error"
        ) from e


async def import_payments_from_csv(
    import_request,  # CSVPaymentImportRequest
    session: AsyncSession,
    current_user: User
):  # -> CSVPaymentImportResult
    """
    Import payments from CSV data with batch processing.
    
    Args:
        import_request: The CSV import request containing payment data.
        session: Database session.
        current_user: The current user making the request.
    
    Returns:
        Import results with success/failure counts and error details.
    """
    
    # Validate user permissions
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to import payments"
        )
    
    total_rows = len(import_request.payments)
    
    # Validate row limit
    if total_rows > settings.MAX_CSV_IMPORT_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV contains {total_rows} rows, exceeding maximum of {settings.MAX_CSV_IMPORT_ROWS}"
        )
    
    # Get all properties and active leases for matching
    properties_query = select(Property)
    if current_user.user_type == UserType.LANDLORD:
        properties_query = properties_query.where(col(Property.user_id) == current_user.id)
    
    properties_result = await session.execute(properties_query)
    properties = {prop.name.lower(): prop for prop in properties_result.scalars().all()}
    
    # Get active leases with tenant info
    leases_query = select(Lease).options(
        selectinload(getattr(Lease, "tenant")),
        selectinload(getattr(Lease, "property"))
    ).where(col(Lease.status) == LeaseStatus.ACTIVE)
    
    if current_user.user_type == UserType.LANDLORD:
        property_ids = [prop.id for prop in properties.values()]
        leases_query = leases_query.where(col(Lease.property_id).in_(property_ids))
    
    leases_result = await session.execute(leases_query)
    leases = leases_result.scalars().all()
    
    # Create mappings for quick lookup
    tenants: Dict[str, Tenant] = {}  # tenant_name -> tenant
    active_leases: Dict[str, Any] = {}  # tenant_id -> lease_id for active leases
    
    for current_lease in leases:
        if current_lease.tenant and current_lease.tenant.id is not None and current_lease.id is not None:
            tenant_name = get_tenant_display_name(current_lease.tenant).lower()
            tenants[tenant_name] = current_lease.tenant
            if current_lease.status == LeaseStatus.ACTIVE:
                active_leases[str(current_lease.tenant.id)] = current_lease.id
    
    # Prepare payments in batch
    valid_payments, preparation_errors = prepare_payment_batch(
        import_request.payments,
        properties,
        tenants,
        active_leases,
        str(current_user.id),
        current_user.user_type
    )
    
    # Check for duplicates
    duplicate_indices = await check_duplicate_payments(valid_payments, session)
    
    # Remove duplicates from valid payments and add to errors
    if duplicate_indices:
        for idx in sorted(duplicate_indices, reverse=True):
            payment = valid_payments.pop(idx)
            preparation_errors.append({
                "row_number": idx + 1,
                "error_message": f"Duplicate payment found for lease {payment['lease_id']}, amount {payment['amount']}, date {payment['payment_date']}"
            })
    
    # Process payments in batches with atomic transaction
    created_payment_ids = []
    
    try:
        # Start nested transaction for atomicity
        async with session.begin_nested():
            # Process in batches
            for i in range(0, len(valid_payments), settings.CSV_IMPORT_BATCH_SIZE):
                batch = valid_payments[i:i + settings.CSV_IMPORT_BATCH_SIZE]
                batch_ids = await bulk_create_payments(batch, session)
                created_payment_ids.extend(batch_ids)
            
            # Commit the nested transaction
            await session.commit()
            
    except Exception as e:
        # Rollback will happen automatically
        logger.error(f"Failed to import payments batch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import payments: {str(e)}"
        )
    
    return CSVPaymentImportResult(
        total_rows=total_rows,
        successful_imports=len(created_payment_ids),
        failed_imports=len(preparation_errors),
        errors=[CSVImportError(**error) for error in preparation_errors],
        created_payment_ids=created_payment_ids
    )
