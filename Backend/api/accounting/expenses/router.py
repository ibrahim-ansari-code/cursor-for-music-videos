"""
FastAPI router for expense endpoints.

This module contains the API endpoint definitions for expense operations,
delegating all business logic to the service layer.
"""

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.accounting.expense import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse
)
from Backend.models.user import User

from . import service
from .schemas import (
    ExpenseReceiptParseResponse, PaginatedExpensesResponse,
    CSVExpenseImportRequest, CSVExpenseImportResult, SecureReceiptUrlResponse
)
from .helpers import delete_blob_with_error_handling
from Backend.utils.recaptcha import require_recaptcha

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/parse-receipt", response_model=ExpenseReceiptParseResponse)
async def parse_expense_receipt(
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    _recaptcha: None = Depends(require_recaptcha("expense_parse_receipt"))
) -> ExpenseReceiptParseResponse:
    """
    Parses an uploaded expense receipt file and extracts structured expense details.

    Validates the user's authorization and the file type, uploads the receipt to blob storage,
    and analyzes its content to extract expense information such as date, tax, and total amounts.
    Returns the receipt URL and parsed details. Raises HTTP errors for unauthorized access,
    unsupported file types, validation failures, external service issues, or unexpected errors.
    """
    return await service.parse_expense_receipt(file, current_user)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_data: ExpenseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _recaptcha: None = Depends(require_recaptcha("expense_create"))
) -> ExpenseResponse:
    """
    Creates a new expense record with associated tax details.

    Validates user authorization and property ownership, calculates taxes and totals,
    and persists the expense and its tax details in the database. Returns the
    created expense as a response model.

    Raises:
        HTTPException: If the user is not authorized, does not own the property,
                       or if an error occurs during creation.
    """
    return await service.create_expense(expense_data, session, current_user)


@router.get("", response_model=PaginatedExpensesResponse)
async def get_expenses(
    property_id: int | None = None,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> PaginatedExpensesResponse:
    """
    Retrieves a paginated list of expenses filtered by property, category, date range, and search.

    Only landlords and admins are authorized to access this endpoint. Landlords can view
    expenses for their own properties, while admins can view all expenses or filter by property.
    Results are ordered by expense date in descending order.

    Args:
        property_id: Optional property ID to filter expenses.
        category: Optional category substring to filter expenses.
        start_date: Optional start date to filter expenses from.
        end_date: Optional end date to filter expenses to.
        search: Optional search term to filter expenses.
        limit: Maximum number of expenses to return (default 100, max 500).
        offset: Number of expenses to skip for pagination.

    Returns:
        A paginated response with expense items and pagination info.
    """
    result = await service.get_expenses(
        session, current_user, property_id, category, start_date, end_date, search, limit, offset
    )
    return PaginatedExpensesResponse(**result)


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense_by_id(
    expense_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> ExpenseResponse:
    """
    Retrieves a single expense by its ID with related property and tax details.

    Raises a 404 error if the expense does not exist, or a 403 error if the user
    is not authorized to access the expense.

    Returns:
        The expense data including associated property and tax information.
    """
    return await service.get_expense_by_id(expense_id, session, current_user)


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    expense_data: ExpenseUpdate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> ExpenseResponse:
    """
    Updates an existing expense by ID with new data, including taxes and receipt information.

    Performs authorization and property ownership checks, updates basic fields and tax details,
    recalculates totals as needed, and updates the modification timestamp. If the receipt file
    is changed, schedules background deletion of the old receipt blob after a successful commit.

    Args:
        expense_id: The ID of the expense to update.
        expense_data: The fields to update for the expense.

    Returns:
        The updated expense as a response model.

    Raises:
        HTTPException: If the expense is not found, the user is unauthorized, or the update fails.
    """
    expense_response, blob_to_delete = await service.update_expense(
        expense_id, expense_data, session, current_user
    )

    # Schedule blob deletion if needed
    if blob_to_delete:
        background_tasks.add_task(
            delete_blob_with_error_handling, blob_to_delete)

    return expense_response


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Deletes an expense by ID after verifying user authorization and property ownership.

    Raises a 404 error if the expense does not exist or a 403 error if the user is not authorized.
    Upon successful deletion, schedules background removal of the associated receipt file from blob storage.
    """
    receipt_url_to_delete = await service.delete_expense(expense_id, session, current_user)

    # Schedule blob deletion if needed
    if receipt_url_to_delete:
        background_tasks.add_task(
            delete_blob_with_error_handling, receipt_url_to_delete)


@router.post("/receipts/secure-url", response_model=SecureReceiptUrlResponse)
async def get_receipt_secure_url(
    request: Request,
    current_user: User = Depends(get_current_user),
    receipt_url: str = Query(..., description="The original Azure Blob URL of the receipt")
):
    """
    Generate a time-limited, authenticated URL for secure expense receipt access.
    
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
        logger.exception("Error generating secure URL for expense receipt")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate secure preview URL."
        )


@router.post("/import-csv", response_model=CSVExpenseImportResult)
async def import_expenses_from_csv(
    import_request: CSVExpenseImportRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _recaptcha: None = Depends(require_recaptcha("expense_import_csv"))
) -> CSVExpenseImportResult:
    """
    Import expenses from CSV data.
    
    Validates user permissions, processes CSV data, and creates expense records.
    Returns import results with success/failure counts and error details.
    """
    return await service.import_expenses_from_csv(import_request, session, current_user)
