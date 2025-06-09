import logging
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.accounting.expense import Expense, ExpenseTaxDetail
from Backend.models.enums import UserType
from Backend.models.property import Property
from Backend.models.user import User
from Backend.utils.azure_blob import upload_expense_receipt_to_blob
from Backend.utils.datetime_utils import (create_audit_datetime,
                                          date_to_utc_range, validate_business_datetime)
from Backend.utils.llm_utils import analyze_expense_receipt_content
from Backend.utils.blob_tasks import delete_blob_in_background as _delete_blob_in_background

from .helpers import check_property_ownership

def quantize_2dp(value: Decimal) -> Decimal:
    """
    Quantize a Decimal value to two decimal places using ROUND_HALF_UP.
    """
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

logger = logging.getLogger(__name__)
router = APIRouter()

# === API Models for Expenses ===

class ExpenseTaxDetailBase(BaseModel):
    tax_name: str
    tax_rate: Decimal

class ExpenseTaxDetailCreate(ExpenseTaxDetailBase):
    pass

class ExpenseTaxDetailResponse(ExpenseTaxDetailBase):
    id: int
    tax_amount: Decimal
    expense_id: int

    class Config:
        from_attributes = True

class ExpenseBase(BaseModel):
    category: str
    description: str | None = None
    expense_date: datetime
    receipt_url: str | None = None
    property_id: int
    subtotal_amount: Decimal

class ExpenseCreate(BaseModel):
    property_id: int
    category: str
    subtotal_amount: Decimal
    expense_date: datetime
    description: str | None = None
    receipt_url: str | None = None
    taxes: list[ExpenseTaxDetailCreate] | None = None

class ExpenseUpdate(BaseModel):
    property_id: int | None = None
    category: str | None = None
    subtotal_amount: Decimal | None = None
    expense_date: datetime | None = None
    description: str | None = None
    receipt_url: str | None = None
    taxes: list[ExpenseTaxDetailCreate] | None = None

class ExpenseResponse(ExpenseBase):
    id: int
    total_tax_amount: Decimal
    total_amount: Decimal
    taxes: list[ExpenseTaxDetailResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Models for Expense Receipt Parsing (similar to PaymentReceiptParse, but can diverge)
class ExpenseReceiptParseDetails(BaseModel):
    expense_date: str | None = None  # LLM might return it as expense_date
    total_tax_amount: Decimal
    total_amount: Decimal
    currency: str | None = None
    # payment_method: str | None = None # Less relevant for generic expenses, could be a vendor or category
    description_notes: str | None = None
    raw_text_preview: str | None = None

class ExpenseReceiptParseResponse(BaseModel):
    receipt_url: str
    parsed_details: ExpenseReceiptParseDetails
    message: str | None = None

# === Helper Functions for Expenses ===

async def _handle_receipt_url_update(
    db_expense: Expense, new_receipt_url: str | None, old_receipt_url: str | None
) -> str | None:
    """
    Updates the receipt URL of an expense if it has changed.
    
    If the receipt URL is updated, returns the previous URL for potential deletion; otherwise, returns None.
    """
    if new_receipt_url != old_receipt_url:
        db_expense.receipt_url = new_receipt_url
        return old_receipt_url if old_receipt_url else None
    return None

def _calculate_expense_taxes(
    expense_data: ExpenseCreate | ExpenseUpdate, # Can be used for both create and update
    current_subtotal: Decimal,
) -> tuple[list[ExpenseTaxDetailCreate], Decimal]:
    """
    Validates and calculates tax details and total tax amount for an expense.
    
    Args:
    	expense_data: The expense creation or update data containing tax information.
    	current_subtotal: The subtotal amount to use for tax calculations.
    
    Returns:
    	A tuple containing a list of tax detail DTOs and the total tax amount, rounded to two decimal places.
    
    Raises:
    	HTTPException: If any tax rate is not a positive value.
    """
    new_tax_details_dto: list[ExpenseTaxDetailCreate] = []
    calculated_total_tax_amount = Decimal("0.00")

    if expense_data.taxes is not None:
        for tax_item_data in expense_data.taxes:
            if not (0 <= tax_item_data.tax_rate <= 100):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tax rate must be between 0 and 100."
                )
            item_tax_amount = (current_subtotal * tax_item_data.tax_rate) / Decimal("100")
            calculated_total_tax_amount += item_tax_amount
            new_tax_details_dto.append(ExpenseTaxDetailCreate(tax_name=tax_item_data.tax_name, tax_rate=tax_item_data.tax_rate))
    return new_tax_details_dto, calculated_total_tax_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def _create_expense_tax_orm_list(tax_details_dto: list[ExpenseTaxDetailCreate], subtotal: Decimal) -> list[ExpenseTaxDetail]:
    """
    Converts a list of tax detail DTOs into ORM ExpenseTaxDetail objects with calculated tax amounts.
    
    Each tax amount is computed as a percentage of the provided subtotal and rounded to two decimal places.
    
    Args:
        tax_details_dto: List of tax detail data transfer objects containing tax name and rate.
        subtotal: The subtotal amount to use for tax calculations.
    
    Returns:
        A list of ExpenseTaxDetail ORM objects with calculated tax amounts.
    """
    result = []
    for tax_item in tax_details_dto:
        # Do not manually set expense_id - let SQLAlchemy relationship handle it
        tax_detail = ExpenseTaxDetail(
            tax_name=tax_item.tax_name,
            tax_rate=tax_item.tax_rate,
            tax_amount=quantize_2dp((subtotal * tax_item.tax_rate) / Decimal("100"))
        )
        result.append(tax_detail)
    return result

def _recalculate_orm_taxes(existing_taxes: list[ExpenseTaxDetail], new_subtotal: Decimal) -> Decimal:
    """
    Recalculates and updates tax amounts for existing tax details based on a new subtotal.
    
    Args:
    	existing_taxes: List of ExpenseTaxDetail ORM objects to update.
    	new_subtotal: The updated subtotal amount to use for tax calculations.
    
    Returns:
    	The total recalculated tax amount as a Decimal, rounded to two decimal places.
    """
    calculated_total_tax_amount = Decimal("0.00")
    for existing_tax_detail in existing_taxes:
        tax_amount = ((new_subtotal * existing_tax_detail.tax_rate) / Decimal("100")).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        existing_tax_detail.tax_amount = tax_amount
        calculated_total_tax_amount += tax_amount
    return calculated_total_tax_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

async def _update_expense_basic_fields(
    db_expense: Expense, 
    update_payload: dict, 
    session: AsyncSession, 
    current_user: User
) -> tuple[bool, str | None]:
    """
    Updates the basic fields of an expense ORM object from the provided payload.
    
    Validates property ownership if the property ID is changed, updates fields such as category, description, expense date, receipt URL, and subtotal. Returns a tuple indicating whether the subtotal was updated and the URL of any old receipt blob to be deleted.
     
    Returns:
        A tuple (subtotal_updated, blob_to_delete), where subtotal_updated is True if the subtotal was changed, and blob_to_delete is the URL of the old receipt blob if it should be deleted.
    """
    old_receipt_url = db_expense.receipt_url
    blob_to_delete = None
    subtotal_updated = False

    if "property_id" in update_payload and update_payload["property_id"] != db_expense.property_id:
        await check_property_ownership(update_payload["property_id"], session, current_user)
        db_expense.property_id = update_payload["property_id"]
    
    if "category" in update_payload and update_payload["category"] is not None:
        db_expense.category = update_payload["category"]
    
    if "description" in update_payload:
        db_expense.description = update_payload["description"]
    
    if "expense_date" in update_payload and update_payload["expense_date"] is not None:
        db_expense.expense_date = validate_business_datetime(update_payload["expense_date"])
    
    if "receipt_url" in update_payload:
        blob_to_delete = await _handle_receipt_url_update(db_expense, update_payload["receipt_url"], old_receipt_url)
    
    if "subtotal_amount" in update_payload and update_payload["subtotal_amount"] is not None:
        new_subtotal = quantize_2dp(update_payload["subtotal_amount"])
        current_subtotal = quantize_2dp(Decimal(str(db_expense.subtotal_amount)))  
        
        # Use direct inequality comparison after quantizing both Decimals
        if current_subtotal != new_subtotal:
            db_expense.subtotal_amount = new_subtotal
            subtotal_updated = True

    return subtotal_updated, blob_to_delete

async def _update_expense_taxes(
    db_expense: Expense, 
    expense_data: ExpenseUpdate, 
    subtotal_updated: bool
) -> None:
    """
    Updates the tax details and total amounts for an expense based on new tax data or a changed subtotal.
    
    If new tax data is provided, replaces existing tax details and recalculates total tax and total amount. If only the subtotal has changed, recalculates tax amounts for existing taxes. Updates the total tax and total amount fields on the expense.
    """
    current_subtotal = Decimal(str(db_expense.subtotal_amount))
    if expense_data.taxes is not None:
        tax_details_dto, calculated_total_tax_amount = _calculate_expense_taxes(expense_data, current_subtotal)
        new_tax_details_orm = _create_expense_tax_orm_list(tax_details_dto, current_subtotal)
        db_expense.taxes = new_tax_details_orm
        db_expense.total_tax_amount = calculated_total_tax_amount
    elif subtotal_updated:
        db_expense.total_tax_amount = _recalculate_orm_taxes(db_expense.taxes, current_subtotal)

# === API Endpoints for Expenses ===

@router.post("/parse-receipt", response_model=ExpenseReceiptParseResponse)
async def parse_expense_receipt(
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)]
) -> ExpenseReceiptParseResponse:
    """
    Parses an uploaded expense receipt file and extracts structured expense details.
    
    Validates the user's authorization and the file type, uploads the receipt to blob storage, and analyzes its content to extract expense information such as date, tax, and total amounts. Returns the receipt URL and parsed details. Raises HTTP errors for unauthorized access, unsupported file types, validation failures, external service issues, or unexpected errors.
    """
    if current_user.user_type not in [UserType.LANDLORD, UserType.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    
    # File size validation (e.g., 10 MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the limit of {MAX_FILE_SIZE / 1024 / 1024} MB."
        )

    allowed_content_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_content_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported file type: {file.content_type}.")
    try:
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File content size exceeds the {MAX_FILE_SIZE / 1024 / 1024} MB limit."
            )
        await file.seek(0)
        # Ensure current_user.id is UUID for blob path consistency if _convert_to_uuid was used in original
        # user_id_for_blob = _convert_to_uuid(current_user.id, "blob path user ID") # current_user.id is already UUID
        receipt_url = await upload_expense_receipt_to_blob(file, current_user.id) 

        parsed_data_dict: dict[str, Any] = await analyze_expense_receipt_content(
            file_content=file_content,
            filename=file.filename if file.filename is not None else "uploaded_expense_receipt"
        )
        
        # Ensure required fields for ExpenseReceiptParseDetails are present.
        # The LLM can sometimes fail to find all fields, so we provide safe defaults.
        subtotal = parsed_data_dict.get('subtotal_amount', 0.0)
        total = parsed_data_dict.get('total_amount', 0.0)
        
        # Calculate total_tax_amount if it's missing, ensuring it's not negative.
        parsed_data_dict.setdefault('total_tax_amount', max(0, float(total) - float(subtotal)))
        # Ensure total_amount has a default if missing.
        parsed_data_dict.setdefault('total_amount', total)

        parsed_details = ExpenseReceiptParseDetails(**parsed_data_dict)
        return ExpenseReceiptParseResponse(
            receipt_url=receipt_url,
            parsed_details=parsed_details,
            message="Expense receipt processed. Review extracted details."
        )
    except ValueError as ve:
        logger.exception("Validation error during expense receipt parsing")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid receipt data provided.") from ve
    except ConnectionError as ce:
        logger.exception("Azure connection error during expense receipt parsing")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="External service is unavailable.") from ce
    except Exception as e:
        logger.exception("Unhandled error parsing expense receipt: %s", file.filename)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to parse receipt due to an internal error.") from e

@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_data: ExpenseCreate, 
    session: AsyncSession = Depends(get_session), 
    current_user: User = Depends(get_current_user)
) -> ExpenseResponse:
    """
    Creates a new expense record with associated tax details.
    
    Validates user authorization and property ownership, calculates taxes and totals, and persists the expense and its tax details in the database. Returns the created expense as a response model.
    
    Raises:
        HTTPException: If the user is not authorized, does not own the property, or if an error occurs during creation.
    """
    if current_user.user_type not in [UserType.LANDLORD, UserType.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    await check_property_ownership(expense_data.property_id, session, current_user)

    subtotal = quantize_2dp(Decimal(str(expense_data.subtotal_amount)))
    # Use the helper for tax calculation
    tax_details_dto, calculated_total_tax_amount = _calculate_expense_taxes(expense_data, subtotal)
    tax_details_to_create_orm = _create_expense_tax_orm_list(tax_details_dto, subtotal)
    calculated_total_amount = quantize_2dp(subtotal + calculated_total_tax_amount)

    db_expense = Expense(
        property_id=expense_data.property_id, category=expense_data.category,
        description=expense_data.description, expense_date=validate_business_datetime(expense_data.expense_date),
        receipt_url=expense_data.receipt_url, subtotal_amount=subtotal,
        total_tax_amount=calculated_total_tax_amount,
        taxes=tax_details_to_create_orm
    )
    try:
        session.add(db_expense)
        await session.commit()
        await session.refresh(db_expense)
        await session.refresh(db_expense, attribute_names=['taxes'])
        logger.info("Expense %s created for property %s by user %s", db_expense.id, db_expense.property_id, current_user.id)
        return ExpenseResponse.model_validate(db_expense)
    except Exception as e:
        await session.rollback()
        logger.exception("Error creating expense")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create expense") from e

@router.get("", response_model=list[ExpenseResponse])
async def get_expenses(
    property_id: int | None = None, category: str | None = None, 
    start_date: date | None = None, end_date: date | None = None,
    session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)
) -> list[ExpenseResponse]:
    """
    Retrieves a list of expenses filtered by property, category, and date range.
    
    Only landlords and admins are authorized to access this endpoint. Landlords can view expenses for their own properties, while admins can view all expenses or filter by property. Results are ordered by expense date in descending order.
    
    Args:
        property_id: Optional property ID to filter expenses.
        category: Optional category substring to filter expenses.
        start_date: Optional start date to filter expenses from.
        end_date: Optional end date to filter expenses to.
    
    Returns:
        A list of expense responses matching the provided filters.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    query = select(Expense).options(selectinload(getattr(Expense, "property")), selectinload(getattr(Expense, "taxes")))
    filters = []
    if category:
        filters.append(col(Expense.category).ilike(f"%{category}%"))
    if start_date:
        filters.append(col(Expense.expense_date) >= date_to_utc_range(start_date, start_date)[0])
    if end_date:
        filters.append(col(Expense.expense_date) <= date_to_utc_range(end_date, end_date)[1])

    if current_user.user_type == UserType.LANDLORD:
        query = query.join(Property, col(Expense.property_id) == col(Property.id)) # Ensure join
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

@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense_by_id(
    expense_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)
) -> ExpenseResponse:
    """
    Retrieves a single expense by its ID with related property and tax details.
    
    Raises a 404 error if the expense does not exist, or a 403 error if the user is not authorized to access the expense.
    
    Returns:
        The expense data including associated property and tax information.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    query = select(Expense).options(selectinload(getattr(Expense, "property")), selectinload(getattr(Expense, "taxes"))).where(Expense.id == expense_id)
    db_expense = await session.scalar(query)

    if not db_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense {expense_id} not found")
    if not current_user.is_admin and (not db_expense.property or db_expense.property.user_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return ExpenseResponse.model_validate(db_expense)

@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int, expense_data: ExpenseUpdate, 
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)
) -> ExpenseResponse:
    """
    Updates an existing expense by ID with new data, including taxes and receipt information.
    
    Performs authorization and property ownership checks, updates basic fields and tax details, recalculates totals as needed, and updates the modification timestamp. If the receipt file is changed, schedules background deletion of the old receipt blob after a successful commit.
    
    Args:
        expense_id: The ID of the expense to update.
        expense_data: The fields to update for the expense.
    
    Returns:
        The updated expense as a response model.
    
    Raises:
        HTTPException: If the expense is not found, the user is unauthorized, or the update fails.
    """
    if current_user.user_type not in [UserType.LANDLORD, UserType.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    db_expense = await session.get(Expense, expense_id, options=[selectinload(getattr(Expense, "taxes")), selectinload(getattr(Expense, "property"))])
    if not db_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense {expense_id} not found")
    if not current_user.is_admin and (not db_expense.property or db_expense.property.user_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    update_payload = expense_data.model_dump(exclude_unset=True)
    
    # Update basic fields
    subtotal_updated, blob_to_delete = await _update_expense_basic_fields(db_expense, update_payload, session, current_user)
    
    # Update taxes
    await _update_expense_taxes(db_expense, expense_data, subtotal_updated)
    
    # Update timestamp
    db_expense.updated_at = create_audit_datetime()

    commit_succeeded = False
    try:
        session.add(db_expense)
        await session.commit()
        commit_succeeded = True  # Mark success only after successful commit
        await session.refresh(db_expense)
        await session.refresh(db_expense, attribute_names=['taxes', 'property'])
        logger.info("Expense %s updated by user %s", db_expense.id, current_user.id)
        
        return ExpenseResponse.model_validate(db_expense)
    except Exception as e:
        await session.rollback()
        logger.exception("Error updating expense %d", expense_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update expense") from e
    finally:
        # Only delete blob if commit definitively succeeded
        if commit_succeeded and blob_to_delete:
            background_tasks.add_task(_delete_blob_with_error_handling, blob_to_delete)

@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int, background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)
) -> None:
    """
    Deletes an expense by ID after verifying user authorization and property ownership.
    
    Raises a 404 error if the expense does not exist or a 403 error if the user is not authorized. Upon successful deletion, schedules background removal of the associated receipt file from blob storage.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    expense_to_delete = await session.get(Expense, expense_id, options=[selectinload(getattr(Expense, "property"))])
    if not expense_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense {expense_id} not found")
    if not current_user.is_admin and (not expense_to_delete.property or expense_to_delete.property.user_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    receipt_url_to_delete = expense_to_delete.receipt_url
    commit_succeeded = False
    try:
        await session.delete(expense_to_delete) # Cascading delete for taxes should be handled by relationship
        await session.commit()
        commit_succeeded = True  # Mark success only after successful commit
        logger.info("Expense %s deleted by user %s", expense_id, current_user.id)
    except Exception as e:
        await session.rollback()
        logger.exception("Error deleting expense %d", expense_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete expense") from e
    finally:
        # Only delete blob if commit definitively succeeded
        if commit_succeeded and receipt_url_to_delete:
            background_tasks.add_task(_delete_blob_with_error_handling, receipt_url_to_delete)

async def _delete_blob_with_error_handling(blob_url: str) -> None:
    """
    Wrapper for delete_blob_in_background that catches and logs exceptions.
    This ensures that background task failures are monitored.
    """
    try:
        await _delete_blob_in_background(blob_url)
    except Exception:
        logger.exception(
            "Background task to delete blob %s failed.", blob_url
        )
        # In a real application, you might emit a metric here, e.g.:
        # metrics.increment("background_blob_deletion_failures") 