"""
Service layer for expense operations.

This module contains the core business logic for expense management,
separated from the FastAPI-specific endpoint handlers.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from Backend.models.accounting.expense import (
    Expense, ExpenseCreate, ExpenseUpdate, ExpenseResponse
)
from Backend.models.enums import UserType
from Backend.models.property import Property
from Backend.models.user import User
from Backend.utils.azure_blob import upload_expense_receipt_to_blob
from Backend.utils.datetime_utils import (
    create_audit_datetime, date_to_utc_range, validate_business_datetime
)
from Backend.llm.receipt_parser import analyze_expense_receipt_content
from Backend.utils.tax_utils import (
    quantize_2dp, finalize_parsed_receipt_data
)
from Backend.utils.file_validation import validate_file_from_upload
from Backend.utils.db_transaction import db_transaction
from Backend.api.accounting.helpers import check_property_ownership

from .schemas import ExpenseReceiptParseDetails, ExpenseReceiptParseResponse
from .helpers import (
    calculate_expense_taxes,
    create_expense_tax_orm_list,
    update_expense_basic_fields,
    update_expense_taxes
)

logger = logging.getLogger(__name__)


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
        logger.info("File validated: declared=%s, detected=%s", file.content_type, validated_mime_type)
        
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
        logger.exception("File validation or data parsing error during expense receipt parsing")
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

    Validates user authorization and property ownership, calculates taxes and totals,
    and persists the expense and its tax details in the database.

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

    subtotal = quantize_2dp(Decimal(str(expense_data.subtotal_amount)))
    
    try:
        tax_details_dto, total_tax_amount = calculate_expense_taxes(expense_data, subtotal)
    except (ValueError, HTTPException) as e:
        # Re-raise HTTPException as-is to preserve status code and detail
        if isinstance(e, HTTPException):
            raise
        # Convert ValueError to HTTPException with 400 status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

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
    end_date: date | None = None
) -> list[ExpenseResponse]:
    """
    Retrieves a list of expenses filtered by property, category, and date range.

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

    Returns:
        A list of expense responses matching the provided filters.

    Raises:
        HTTPException: If the user is not authorized.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    query = select(Expense).options(selectinload(
        getattr(Expense, "property")), selectinload(getattr(Expense, "taxes")))
    filters = []
    if category:
        filters.append(col(Expense.category).ilike(f"%{category}%"))
    if start_date:
        filters.append(col(Expense.expense_date) >=
                       date_to_utc_range(start_date, start_date)[0])
    if end_date:
        filters.append(col(Expense.expense_date) <=
                       date_to_utc_range(end_date, end_date)[1])

    if current_user.user_type == UserType.LANDLORD:
        query = query.join(Property, col(Expense.property_id)
                           == col(Property.id))  # Ensure join
        filters.append(Property.user_id == current_user.id)
        if property_id:
            filters.append(Expense.property_id == property_id)
    elif current_user.user_type == UserType.ADMIN and property_id:
        filters.append(Expense.property_id == property_id)

    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(col(Expense.expense_date).desc())
    expenses_orm = (await session.execute(query)).scalars().unique().all()
    return [ExpenseResponse.model_validate(exp) for exp in expenses_orm]


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
    await update_expense_taxes(db_expense, expense_data, subtotal_updated)

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
