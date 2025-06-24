"""
Helper functions for expense operations.

These functions provide utility operations for expense management, including
receipt URL handling, tax calculations, and field updates.
"""

import logging
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.models.accounting.expense import (
    Expense, ExpenseTaxDetail, ExpenseTaxDetailCreate, ExpenseCreate, ExpenseUpdate
)
from Backend.models.user import User
from Backend.api.accounting.helpers import check_property_ownership
from Backend.utils.datetime_utils import validate_business_datetime
from Backend.utils.tax_utils import (
    quantize_2dp,
    validate_tax_rate,
    calculate_tax_amount
)
from Backend.utils.blob_tasks import delete_blob_in_background

logger = logging.getLogger(__name__)


async def handle_receipt_url_update(
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


def calculate_expense_taxes(
    # Can be used for both create and update
    expense_data: ExpenseCreate | ExpenseUpdate,
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
            # Use centralized tax rate validation
            try:
                tax_rate_decimal = validate_tax_rate(tax_item_data.tax_rate)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                ) from e
            
            # Calculate tax amount using centralized function
            item_tax_amount = calculate_tax_amount(current_subtotal, tax_rate_decimal)
            calculated_total_tax_amount += item_tax_amount
            
            new_tax_details_dto.append(ExpenseTaxDetailCreate(
                tax_name=tax_item_data.tax_name,
                tax_rate=tax_rate_decimal,
                tax_amount=item_tax_amount
            ))
    
    return new_tax_details_dto, quantize_2dp(calculated_total_tax_amount)


def create_expense_tax_orm_list(tax_details_dto: list[ExpenseTaxDetailCreate], subtotal: Decimal) -> list[ExpenseTaxDetail]:
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
        # Use pre-calculated tax amount if available, otherwise calculate it
        if tax_item.tax_amount is not None:
            tax_amount = quantize_2dp(tax_item.tax_amount)
        else:
            tax_amount = quantize_2dp(
                (subtotal * tax_item.tax_rate) / Decimal("100"))

        # Do not manually set expense_id - let SQLAlchemy relationship handle it
        tax_detail = ExpenseTaxDetail(
            tax_name=tax_item.tax_name,
            tax_rate=tax_item.tax_rate,
            tax_amount=tax_amount
        )
        result.append(tax_detail)
    return result


def recalculate_orm_taxes(existing_taxes: list[ExpenseTaxDetail], new_subtotal: Decimal) -> Decimal:
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
        tax_amount = calculate_tax_amount(new_subtotal, existing_tax_detail.tax_rate)
        existing_tax_detail.tax_amount = tax_amount
        calculated_total_tax_amount += tax_amount
    return quantize_2dp(calculated_total_tax_amount)


async def update_expense_basic_fields(
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
        db_expense.expense_date = validate_business_datetime(
            update_payload["expense_date"])

    if "receipt_url" in update_payload:
        blob_to_delete = await handle_receipt_url_update(db_expense, update_payload["receipt_url"], old_receipt_url)

    if "subtotal_amount" in update_payload and update_payload["subtotal_amount"] is not None:
        new_subtotal = quantize_2dp(update_payload["subtotal_amount"])
        current_subtotal = quantize_2dp(
            Decimal(str(db_expense.subtotal_amount)))

        # Use direct inequality comparison after quantizing both Decimals
        if current_subtotal != new_subtotal:
            db_expense.subtotal_amount = new_subtotal
            subtotal_updated = True

    return subtotal_updated, blob_to_delete


async def update_expense_taxes(
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
        tax_details_dto, calculated_total_tax_amount = calculate_expense_taxes(
            expense_data, current_subtotal)
        new_tax_details_orm = create_expense_tax_orm_list(
            tax_details_dto, current_subtotal)
        db_expense.taxes = new_tax_details_orm
        db_expense.total_tax_amount = calculated_total_tax_amount
        # Update total amount (subtotal + tax)
        db_expense.total_amount = quantize_2dp(current_subtotal + calculated_total_tax_amount)
    elif subtotal_updated:
        db_expense.total_tax_amount = recalculate_orm_taxes(
            db_expense.taxes, current_subtotal)
        # Update total amount when subtotal changes
        db_expense.total_amount = quantize_2dp(current_subtotal + db_expense.total_tax_amount)


async def delete_blob_with_error_handling(blob_url: str) -> None:
    """
    Wrapper for delete_blob_in_background that catches and logs exceptions.
    This ensures that background task failures are monitored.
    """
    try:
        await delete_blob_in_background(blob_url)
    except Exception:
        logger.exception(
            "Background task to delete blob %s failed.", blob_url
        )
        # In a real application, you might emit a metric here, e.g.:
        # metrics.increment("background_blob_deletion_failures")
