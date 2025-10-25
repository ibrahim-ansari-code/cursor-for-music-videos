"""Payments API router - RESTful endpoints for payment operations."""
import logging
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Request, Response, UploadFile, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.accounting.common import PaymentStatus
from Backend.models.user import User
from Backend.utils.blob_tasks import delete_blob_in_background

from . import service
from .schemas import (
    PaymentCreate,
    PaymentResponse,
    PaymentUpdate,
    PaginatedPaymentsResponse,
    PaymentReceiptParseResponse,
    SecureReceiptUrlResponse,
    CSVPaymentImportRequest,
    CSVPaymentImportResult,
)
from Backend.utils.recaptcha import require_recaptcha


logger = logging.getLogger(__name__)
router = APIRouter()


# === CRUD Operations (following RESTful conventions) ===

# CREATE
@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment: PaymentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _recaptcha: None = Depends(require_recaptcha("payment_create"))
) -> PaymentResponse:
    """
    Create a new payment record.
    
    - **lease_id**: ID of the lease this payment is for
    - **amount**: Payment amount
    - **payment_date**: Date of payment (optional, defaults to current UTC time)
    - **payment_method**: Method of payment (optional, defaults to OTHER)
    - **status**: Payment status (optional, defaults to PENDING)
    - **transaction_reference**: External transaction reference (optional)
    - **description**: Payment description (optional)
    - **receipt_url**: URL to payment receipt (optional)
    
    Only landlords and admins can create payments.
    """
    return await service.create_payment(payment, session, current_user)


# READ (List)
@router.get("", response_model=PaginatedPaymentsResponse)
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
    Retrieve a paginated list of payments.
    
    - **lease_id**: Filter by lease ID
    - **property_id**: Filter by property ID
    - **tenant_id**: Filter by tenant ID
    - **payment_status**: Filter by payment status
    - **start_date**: Filter payments on or after this date
    - **end_date**: Filter payments on or before this date
    - **limit**: Maximum number of payments to return (default 100, max 500)
    - **offset**: Number of payments to skip for pagination
    
    Results are filtered based on user role:
    - Tenants see only their own payments
    - Landlords see payments for their properties
    - Admins see all payments
    """
    return await service.get_payments(
        session=session,
        current_user=current_user,
        lease_id=lease_id,
        property_id=property_id,
        tenant_id=tenant_id,
        payment_status=payment_status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )


# READ (Single)
@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> PaymentResponse:
    """
    Retrieve a single payment by ID.
    
    Access control:
    - Tenants can only access their own payments
    - Landlords can only access payments for their properties
    - Admins can access all payments
    """
    return await service.get_payment_by_id(payment_id, session, current_user)


# UPDATE
@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> PaymentResponse:
    """
    Update an existing payment.
    
    All fields are optional - only provided fields will be updated:
    - **amount**: New payment amount
    - **payment_date**: New payment date
    - **payment_method**: New payment method
    - **status**: New payment status
    - **transaction_reference**: New transaction reference
    - **description**: New description
    - **receipt_url**: New receipt URL
    
    Only landlords and admins can update payments.
    """
    return await service.update_payment(payment_id, payment_data, session, current_user)


# DELETE
@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Delete a payment by ID.
    
    If the payment has an associated receipt file, it will be deleted in the background.
    Only landlords and admins can delete payments.
    """
    receipt_url = await service.delete_payment(payment_id, session, current_user)
    
    # Schedule blob deletion in background if receipt exists
    if receipt_url:
        background_tasks.add_task(delete_blob_in_background, receipt_url)


# === Additional Operations (Business-specific endpoints) ===

@router.get("/outstanding/current-month", response_model=list[PaymentResponse])
async def get_outstanding_payments(
    response: Response,
    property_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[PaymentResponse]:
    """
    Retrieve outstanding payments for the current month.
    
    Returns payments with status PENDING or OVERDUE for the current month.
    - **property_id**: Optional property ID to filter payments to a specific property
    - **limit**: Maximum number of records to return (capped at 500)
    
    Response headers indicate if the limit was adjusted:
    - X-Applied-Limit: The actual limit used
    - X-Original-Limit: The requested limit
    - X-Limit-Adjusted: "true" if limit was adjusted
    """
    original_limit = limit
    limit = max(1, min(limit, 500))
    
    # Set response headers if limit was adjusted
    if limit != original_limit:
        response.headers["X-Applied-Limit"] = str(limit)
        response.headers["X-Original-Limit"] = str(original_limit)
        response.headers["X-Limit-Adjusted"] = "true"
    
    return await service.get_outstanding_payments_for_month(
        session=session,
        current_user=current_user,
        limit=limit,
        property_id=property_id
    )


@router.post("/generate/monthly-rent", response_model=list[PaymentResponse])
async def generate_monthly_rent_payments(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[PaymentResponse]:
    """
    Generate pending rent payments for the current month.
    
    Creates a pending payment for each active lease that doesn't already have
    a payment for the current month.
    
    Only landlords and admins can generate payments.
    """
    return await service.generate_due_payments_for_month(session, current_user)


@router.post("/receipts/parse", response_model=PaymentReceiptParseResponse)
async def parse_payment_receipt(
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    _recaptcha: None = Depends(require_recaptcha("payment_parse_receipt"))
) -> PaymentReceiptParseResponse:
    """
    Parse a payment receipt file and extract payment details.
    
    Accepts PDF, JPG, or PNG files up to 10 MB.
    The file is uploaded to cloud storage and analyzed to extract:
    - Payment date
    - Amount (subtotal and total)
    - Payment method
    - Currency
    - Description/notes
    
    Only landlords and admins can parse receipts.
    """
    return await service.parse_payment_receipt(file, current_user)


@router.post("/receipts/secure-url", response_model=SecureReceiptUrlResponse)
async def get_receipt_secure_url(
    request: Request,
    current_user: User = Depends(get_current_user),
    receipt_url: str = Query(..., description="The original Azure Blob URL of the receipt")
):
    """
    Generate a time-limited, authenticated URL for secure payment receipt access.
    
    For private Azure containers, receipts require SAS tokens to be accessed.
    This endpoint generates a 1-hour expiring SAS token for secure receipt viewing.
    """
    try:
        return await service.generate_receipt_secure_url(
            receipt_url=receipt_url,
            current_user=current_user
        )
    except HTTPException:
        raise
    except ValueError as ve:
        error_msg = str(ve)
        if "not found in storage" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The receipt file no longer exists in storage."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid receipt URL: {error_msg}"
        )
    except Exception as e:
        logger.exception("Error generating secure URL for payment receipt")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate secure preview URL."
        )


# === Administrative Operations ===

@router.get("/diagnostics/orphaned-payments", 
           response_model=dict[str, Any],
           tags=["diagnostics"])
async def check_orphaned_payments(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Run integrity check for orphaned payments (Admin only).
    
    Identifies payments that have a lease_id but the corresponding
    lease or property record is missing, indicating a data integrity issue.
    
    Returns:
    - status: "ok" or "warning"
    - message: Summary of findings
    - details: Detailed report if orphaned payments found
    
    **Note**: This is an expensive operation that may time out under heavy load.
    """
    # Explicit admin-only authorization check
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for diagnostic operations"
        )
    
    return await service.run_orphaned_payments_check(session, current_user)


@router.post("/import-csv", response_model=CSVPaymentImportResult)
async def import_payments_from_csv(
    import_request: CSVPaymentImportRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _recaptcha: None = Depends(require_recaptcha("payment_import_csv"))
) -> CSVPaymentImportResult:
    """
    Import payments from CSV data.
    
    Validates user permissions, processes CSV data, and creates payment records.
    Returns import results with success/failure counts and error details.
    """
    return await service.import_payments_from_csv(import_request, session, current_user)