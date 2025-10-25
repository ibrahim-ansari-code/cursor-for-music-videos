"""
Service layer for expense operations.

This module contains the core business logic for expense management,
separated from the FastAPI-specific endpoint handlers.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Dict, Optional

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import and_, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from Backend.models.accounting.expense import (
    Expense, ExpenseCreate, ExpenseUpdate, ExpenseResponse, PaymentMethod
)
from Backend.models.enums import UserType
from Backend.models.property import Property
from Backend.models.user import User
from Backend.utils.azure_blob import upload_expense_receipt_to_blob, generate_secure_document_url
from Backend.utils.datetime_utils import (
    create_audit_datetime, date_to_utc_range, validate_business_datetime
)
from Backend.llm import analyze_expense_receipt_content
from Backend.config import Settings
from Backend.utils.tax_utils import (
    quantize_2dp, finalize_parsed_receipt_data
)
from Backend.utils.file_validation import validate_file_from_upload
from Backend.utils.db_transaction import db_transaction
from Backend.api.accounting.helpers import check_property_ownership

from .schemas import ExpenseReceiptParseDetails, ExpenseReceiptParseResponse, CSVExpenseImportRequest, CSVExpenseImportResult, CSVImportError
from .helpers import (
    calculate_expense_taxes,
    create_expense_tax_orm_list,
    update_expense_basic_fields,
    update_expense_taxes,
    delete_blob_with_error_handling
)
from .service_batch import bulk_create_expenses, prepare_expense_batch, check_duplicate_expenses

logger = logging.getLogger(__name__)
settings = Settings()


async def get_smart_tax_for_expense_creation(
    session: AsyncSession,
    user_id: str,
    property_id: int,
    expense_data: ExpenseCreate
) -> ExpenseCreate:
    """
    Auto-populate tax data for expense creation if none provided.
    
    Uses smart tax selection if expense has no tax details specified.
    Returns the expense_data with tax details populated if applicable.
    """
    from Backend.api.accounting.tax_preferences.service import get_smart_tax_for_expense
    
    # If tax details are already provided, don't override
    if expense_data.taxes:
        return expense_data
    
    # Get smart tax recommendation
    smart_tax = await get_smart_tax_for_expense(session, user_id, property_id)
    if not smart_tax:
        return expense_data  # No smart recommendation available
    
    tax_name, tax_rate = smart_tax
    
    # Create tax detail from smart recommendation
    from Backend.models.accounting.expense import ExpenseTaxDetailCreate
    smart_tax_detail = ExpenseTaxDetailCreate(
        tax_name=tax_name,
        tax_rate=tax_rate,
        # tax_amount will be calculated by the existing tax calculation logic
    )
    
    # Create new expense data with smart tax applied
    expense_with_tax = expense_data.model_copy()
    expense_with_tax.taxes = [smart_tax_detail]
    
    logger.info(f"Auto-populated smart tax for expense: {tax_name} {tax_rate}%")
    return expense_with_tax


async def parse_expense_receipt(
    file: UploadFile,
    current_user: User
) -> ExpenseReceiptParseResponse:
    """
    Parses an uploaded expense receipt file and extracts structured expense details.

    Validates the user's authorization and the file type, uploads the receipt to blob storage,
    and analyzes its content to extract expense information such as date, tax, and total amounts.
    Returns the receipt URL and parsed details.

    Args:
        file: The uploaded receipt file.
        current_user: The user making the request.

    Returns:
        ExpenseReceiptParseResponse with receipt URL and parsed details.

    Raises:
        HTTPException: For authorization, validation, or processing errors.
    """
    if current_user.user_type not in [UserType.LANDLORD, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    try:
        # Use secure file validation with magic number checking
        file_content, validated_mime_type = await validate_file_from_upload(file, file.content_type)
        logger.info("File validated: declared=%s, detected=%s",
                    file.content_type, validated_mime_type)

        receipt_url = await upload_expense_receipt_to_blob(file, current_user.id)

        parsed_data_dict: dict[str, Any] = await analyze_expense_receipt_content(
            file_content=file_content,
            filename=file.filename if file.filename is not None else "uploaded_expense_receipt"
        )

        # Ensure required fields for ExpenseReceiptParseDetails are present.
        # The LLM can sometimes fail to find all fields, so we provide safe defaults.
        subtotal = quantize_2dp(
            Decimal(str(parsed_data_dict.get('subtotal_amount', '0.0'))))
        total = quantize_2dp(
            Decimal(str(parsed_data_dict.get('total_amount', '0.0'))))

        # Process and validate tax details using helper function
        parsed_data_dict = finalize_parsed_receipt_data(
            parsed_data_dict, subtotal, total)

        parsed_details = ExpenseReceiptParseDetails(**parsed_data_dict)
        return ExpenseReceiptParseResponse(
            receipt_url=receipt_url,
            parsed_details=parsed_details,
            message="Expense receipt processed. Review extracted details."
        )
    except ValueError as ve:
        logger.exception(
            "File validation or data parsing error during expense receipt parsing")
        # Check if it's a file validation error (more specific error message)
        if "file" in str(ve).lower() or "mime" in str(ve).lower() or "size" in str(ve).lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"File validation failed: {str(ve)}") from ve
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid receipt data provided.") from ve
    except ConnectionError as ce:
        logger.exception(
            "Azure connection error during expense receipt parsing")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="External service is unavailable.") from ce
    except Exception as e:
        logger.exception(
            "Unhandled error parsing expense receipt: %s", file.filename)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to parse receipt due to an internal error.") from e


async def create_expense(
    expense_data: ExpenseCreate,
    session: AsyncSession,
    current_user: User
) -> ExpenseResponse:
    """
    Creates a new expense record with associated tax details.

    Auto-populates smart tax data if none provided, validates user authorization 
    and property ownership, calculates taxes and totals, and persists the expense 
    and its tax details in the database.

    Args:
        expense_data: The expense creation data.
        session: The database session.
        current_user: The user creating the expense.

    Returns:
        The created expense as a response model.

    Raises:
        HTTPException: If the user is not authorized, does not own the property,
                       or if an error occurs during creation.
    """
    if current_user.user_type not in [UserType.LANDLORD, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    await check_property_ownership(expense_data.property_id, session, current_user)

    # Auto-populate smart tax if no tax details provided and property_id is present
    if expense_data.property_id:
        expense_data = await get_smart_tax_for_expense_creation(
            session=session,
            user_id=str(current_user.id),
            property_id=expense_data.property_id,
            expense_data=expense_data
        )

    subtotal = quantize_2dp(Decimal(str(expense_data.subtotal_amount)))

    try:
        tax_details_dto, total_tax_amount = calculate_expense_taxes(
            expense_data, subtotal)
    except (ValueError, HTTPException) as e:
        # Re-raise HTTPException as-is to preserve status code and detail
        if isinstance(e, HTTPException):
            raise
        # Convert ValueError to HTTPException with 400 status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    tax_orm_objects = create_expense_tax_orm_list(tax_details_dto, subtotal)

    db_expense = Expense(
        property_id=expense_data.property_id,
        category=expense_data.category,
        description=expense_data.description,
        expense_date=validate_business_datetime(expense_data.expense_date),
        receipt_url=expense_data.receipt_url,
        subtotal_amount=subtotal,
        total_tax_amount=total_tax_amount,
        taxes=tax_orm_objects
    )

    try:
        async with db_transaction(session) as tx:
            tx.add(db_expense)

        await session.refresh(db_expense, attribute_names=['taxes'])

        logger.info("Expense %s created for property %s by user %s",
                    db_expense.id, db_expense.property_id, current_user.id)

        return ExpenseResponse.model_validate(db_expense)
    except Exception as e:
        logger.exception("Error creating expense")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to create expense") from e


async def get_expenses(
    session: AsyncSession,
    current_user: User,
    property_id: int | None = None,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> dict[str, Any]:
    """
    Retrieves a paginated list of expenses filtered by property, category, date range, and search.

    Only landlords and admins are authorized to access this endpoint. Landlords can view
    expenses for their own properties, while admins can view all expenses or filter by property.
    Results are ordered by expense date in descending order.

    Args:
        session: The database session.
        current_user: The user making the request.
        property_id: Optional property ID to filter expenses.
        category: Optional category substring to filter expenses.
        start_date: Optional start date to filter expenses from.
        end_date: Optional end date to filter expenses to.
        search: Optional search term to filter expenses.
        limit: Maximum number of expenses to return.
        offset: Number of expenses to skip for pagination.

    Returns:
        A paginated response with expense items and pagination info.

    Raises:
        HTTPException: If the user is not authorized.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    query = select(Expense).options(selectinload(
        getattr(Expense, "property")), selectinload(getattr(Expense, "taxes")))
    filters: list[Any] = []
    if category:
        filters.append(col(Expense.category).ilike(f"%{category}%"))
    if start_date:
        filters.append(col(Expense.expense_date) >= date_to_utc_range(start_date, start_date)[0])
    if end_date:
        filters.append(col(Expense.expense_date) <= date_to_utc_range(end_date, end_date)[1])

    # Add search filtering
    if search:
        # Escape special SQL LIKE pattern characters to prevent injection
        # Note: SQLAlchemy's .ilike() method uses parameterized queries internally,
        # so this is safe from SQL injection. The escaping here is for LIKE patterns,
        # not SQL injection prevention.
        escaped_search = search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        search_term = f"%{escaped_search}%"
        filters.append(
            (col(Expense.description).ilike(search_term) |
             col(Expense.category).ilike(search_term))
        )

    if current_user.user_type == UserType.LANDLORD:
        query = query.join(Property, col(Expense.property_id)
                           == col(Property.id))  # Ensure join
        filters.append(col(Property.user_id) == current_user.id)
        if property_id:
            filters.append(col(Expense.property_id) == property_id)
    elif current_user.user_type == UserType.ADMIN and property_id:
        filters.append(col(Expense.property_id) == property_id)

    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(col(Expense.expense_date).desc())

    # Add pagination
    query = query.offset(offset).limit(
        limit + 1)  # +1 to check if there's more
    expenses_orm = (await session.execute(query)).scalars().unique().all()

    # Check if there are more items
    has_more = len(expenses_orm) > limit
    if has_more:
        expenses_orm = expenses_orm[:limit]  # Remove the extra item

    expense_responses = [ExpenseResponse.model_validate(
        exp) for exp in expenses_orm]

    return {
        "items": expense_responses,
        "has_more": has_more
    }


async def get_expense_by_id(
    expense_id: int,
    session: AsyncSession,
    current_user: User
) -> ExpenseResponse:
    """
    Retrieves a single expense by its ID with related property and tax details.

    Args:
        expense_id: The ID of the expense to retrieve.
        session: The database session.
        current_user: The user making the request.

    Returns:
        The expense data including associated property and tax information.

    Raises:
        HTTPException: If the expense does not exist or the user is not authorized.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    query = select(Expense).options(selectinload(getattr(Expense, "property")), selectinload(
        getattr(Expense, "taxes"))).where(Expense.id == expense_id)
    db_expense = await session.scalar(query)

    if not db_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Expense {expense_id} not found")
    if not current_user.is_admin and (not db_expense.property or db_expense.property.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return ExpenseResponse.model_validate(db_expense)


async def update_expense(
    expense_id: int,
    expense_data: ExpenseUpdate,
    session: AsyncSession,
    current_user: User
) -> tuple[ExpenseResponse, str | None]:
    """
    Updates an existing expense by ID with new data, including taxes and receipt information.

    Performs authorization and property ownership checks, updates basic fields and tax details,
    recalculates totals as needed, and updates the modification timestamp.

    Args:
        expense_id: The ID of the expense to update.
        expense_data: The fields to update for the expense.
        session: The database session.
        current_user: The user making the update.

    Returns:
        A tuple of (updated expense response, blob URL to delete if any).

    Raises:
        HTTPException: If the expense is not found, the user is unauthorized, or the update fails.
    """
    if current_user.user_type not in [UserType.LANDLORD, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    db_expense = await session.get(Expense, expense_id, options=[selectinload(getattr(Expense, "taxes")), selectinload(getattr(Expense, "property"))])
    if not db_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Expense {expense_id} not found")
    if not current_user.is_admin and (not db_expense.property or db_expense.property.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    update_payload = expense_data.model_dump(exclude_unset=True)

    # Update basic fields
    subtotal_updated, blob_to_delete = await update_expense_basic_fields(db_expense, update_payload, session, current_user)

    # Update taxes
    await update_expense_taxes(db_expense, expense_data, subtotal_updated, session)

    # Update timestamp
    db_expense.updated_at = create_audit_datetime()

    try:
        session.add(db_expense)
        await session.commit()
        await session.refresh(db_expense, attribute_names=['taxes'])
        logger.info("Expense %s updated by user %s",
                    db_expense.id, current_user.id)

        return ExpenseResponse.model_validate(db_expense), blob_to_delete
    except Exception as e:
        await session.rollback()
        logger.exception("Error updating expense %d", expense_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to update expense") from e


async def delete_expense(
    expense_id: int,
    session: AsyncSession,
    current_user: User
) -> str | None:
    """
    Deletes an expense by ID after verifying user authorization and property ownership.

    Args:
        expense_id: The ID of the expense to delete.
        session: The database session.
        current_user: The user making the deletion.

    Returns:
        The receipt URL to delete from blob storage, if any.

    Raises:
        HTTPException: If the expense does not exist, the user is not authorized, or deletion fails.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    expense_to_delete = await session.get(Expense, expense_id, options=[selectinload(getattr(Expense, "property"))])
    if not expense_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Expense {expense_id} not found")
    if not current_user.is_admin and (not expense_to_delete.property or expense_to_delete.property.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    receipt_url_to_delete = expense_to_delete.receipt_url
    try:
        # Cascading delete for taxes should be handled by relationship
        await session.delete(expense_to_delete)
        await session.commit()
        logger.info("Expense %s deleted by user %s",
                    expense_id, current_user.id)
        return receipt_url_to_delete
    except Exception as e:
        await session.rollback()
        logger.exception("Error deleting expense %d", expense_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to delete expense") from e


async def generate_receipt_secure_url(
    receipt_url: str,
    current_user: User
) -> dict:
    """
    Generate a time-limited SAS token URL for expense receipt access.
    
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
            detail="Not authorized to access expense receipts."
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
        logger.error(f"Error generating secure URL for expense receipt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate secure URL: {str(e)}"
        )


async def import_expenses_from_csv(
    import_request,  # CSVExpenseImportRequest
    session: AsyncSession,
    current_user: User
) -> Any:  # CSVExpenseImportResult
    """
    Import expenses from CSV data with batch processing and atomic transactions.
    
    Args:
        import_request: The CSV import request containing expense data.
        session: Database session.
        current_user: The current user making the request.
    
    Returns:
        Import results with success/failure counts and error details.
    """
    # Validate user permissions
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to import expenses"
        )
    
    # Check row limit
    total_rows = len(import_request.expenses)
    if total_rows > settings.MAX_CSV_IMPORT_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV exceeds maximum {settings.MAX_CSV_IMPORT_ROWS} rows. Found {total_rows} rows."
        )
    
    if total_rows == 0:
        return CSVExpenseImportResult(
            total_rows=0,
            successful_imports=0,
            failed_imports=0,
            errors=[],
            created_expense_ids=[]
        )
    
    # Get all properties for matching
    properties_query = select(Property)
    if current_user.user_type == UserType.LANDLORD:
        properties_query = properties_query.where(col(Property.user_id) == current_user.id)
    
    properties_result = await session.execute(properties_query)
    properties = {prop.name.lower(): prop for prop in properties_result.scalars().all()}
    
    # Prepare expenses in batch
    valid_expenses, preparation_errors = prepare_expense_batch(
        import_request.expenses,
        properties,
        str(current_user.id),
        current_user.user_type
    )
    
    # Check for duplicates
    duplicate_indices = await check_duplicate_expenses(valid_expenses, session)
    
    # Remove duplicates from valid expenses and add to errors
    if duplicate_indices:
        for idx in sorted(duplicate_indices, reverse=True):
            expense = valid_expenses.pop(idx)
            preparation_errors.append({
                "row_number": idx + 1,
                "error_message": f"Duplicate expense found for property {expense['property_id']}, category {expense['category']}, amount {expense['subtotal_amount']}, date {expense['expense_date']}"
            })
    
    # Process expenses in batches with atomic transaction
    created_expense_ids = []
    
    try:
        # Start nested transaction for atomicity
        async with session.begin_nested():
            # Process in batches
            for i in range(0, len(valid_expenses), settings.CSV_IMPORT_BATCH_SIZE):
                batch = valid_expenses[i:i + settings.CSV_IMPORT_BATCH_SIZE]
                batch_ids = await bulk_create_expenses(batch, session)
                created_expense_ids.extend(batch_ids)
            
            # Commit the nested transaction
            await session.commit()
            
    except Exception as e:
        # Rollback will happen automatically
        logger.error(f"Failed to import expenses batch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import expenses: {str(e)}"
        )
    
    return CSVExpenseImportResult(
        total_rows=total_rows,
        successful_imports=len(created_expense_ids),
        failed_imports=len(preparation_errors),
        errors=[CSVImportError(**error) for error in preparation_errors],
        created_expense_ids=created_expense_ids
    )
