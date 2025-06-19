import logging
from typing import Any
import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlmodel import select, col

from Backend.models.user import User
from Backend.models.accounting.integration import IntegrationStatus, IntegrationType
from Backend.api.quickbooks.utils import get_user_integration, get_apideck_client, is_already_synced
from Backend.utils.datetime_utils import create_audit_datetime
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.accounting.expense import Expense

logger = logging.getLogger(__name__)

async def _create_qbo_expense_via_apideck(user: User, session: AsyncSession, expense_data: dict[str, Any]) -> None:
    """
    Creates an expense in QuickBooks Online for a user via the Apideck API.
    
    This function is intended to map local expense data to the Apideck accounting API format and submit a creation request for users with an active QuickBooks integration.
    """
    # 1. Ensure user has an active Apideck session/connection for QuickBooks.
    # 2. Map expense_data from your system's format to Apideck's accounting API format for expenses.
    # 3. Call Apideck's API to create the expense.
    # Example: apideck_client.accounting.purchases_add(app_id='quickbooks', consumer_id=user.apideck_consumer_id, body={...mapped_expense_data...})
    pass

async def _sync_expense_to_quickbooks(user: User, session: AsyncSession, expense_data: dict[str, Any]) -> dict[str, Any]:
    """
    Synchronizes a single expense record to QuickBooks Online via Apideck for a connected user.
    
    Validates that the user has an active QuickBooks integration with a valid consumer ID, then attempts to sync the provided expense data to QuickBooks. If the integration is not properly configured or an error occurs during the sync process, raises an HTTPException with an appropriate status code and error message. Currently, the actual sync implementation is pending; the function updates the integration's last sync timestamp and returns a placeholder success response.
    
    Returns:
        A dictionary indicating the success status, a message, and a placeholder for the QuickBooks expense ID.
    """
    try:
        # Get existing integration - don't create a new one during sync attempts
        integration = await get_user_integration(user, session, IntegrationType.QUICKBOOKS)
        
        if not integration or integration.status != IntegrationStatus.CONNECTED or not integration.apideck_consumer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QuickBooks integration is not configured properly."
            )
        
        apideck_client = get_apideck_client(integration.apideck_consumer_id)
        
        # TODO: Implement expense sync once we verify the correct Apideck API format
        # Map our expense data to Apideck's format
        # apideck_expense = {
        #     "number": expense_data.get("id"),
        #     "transaction_date": expense_data.get("expense_date"),
        #     "account_id": expense_data.get("account_id"),  # This would need to be mapped to QB account
        #     "line_items": [{
        #         "description": expense_data.get("description"),
        #         "total_amount": expense_data.get("total_amount"),
        #         "category": expense_data.get("category")
        #     }],
        #     "currency": "USD",  # This could be configurable
        #     "memo": expense_data.get("description")
        # }
        
        # Create expense in QuickBooks via Apideck
        # response = apideck_client.accounting.expenses.create(
        #     service_id="quickbooks",
        #     body=apideck_expense
        # )
        
        # For now, just update the sync time and return success
        integration.last_sync_at = create_audit_datetime()
        integration.updated_at = create_audit_datetime()
        await session.commit()
        
        return {
            "success": True,
            "message": "Expense sync functionality is being implemented",
            "quickbooks_id": None
        }
        
        # if response.status_code in [200, 201]:
        #     # Update last sync time
        #     integration.last_sync_at = create_audit_datetime()
        #     integration.updated_at = create_audit_datetime()
        #     await session.commit()
        #     
        #     return {
        #         "success": True,
        #         "message": "Expense synced to QuickBooks successfully",
        #         "quickbooks_id": response.data.id if response.data else None
        #     }
        # else:
        #     logger.error(f"Failed to sync expense to QuickBooks: {response.status_code}")
        #     return {
        #         "success": False,
        #         "message": f"Failed to sync expense: {response.status_code}"
        #     }
            
    except HTTPException:
        # Re-raise HTTPExceptions as-is to preserve status codes and error details
        raise
    except Exception as e:
        logger.error("Error syncing expense to QuickBooks for user %s: %s", user.id, str(e), exc_info=True)
        
        # Check if this is an Apideck-specific error with response details
        if hasattr(e, 'status') and hasattr(e, 'body'):
            # Extract Apideck error details and convert to appropriate HTTP status
            apideck_status = getattr(e, 'status', 500)
            apideck_body = getattr(e, 'body', {})
            
            # Map common Apideck status codes to HTTP status codes
            status_mapping = {
                400: status.HTTP_400_BAD_REQUEST,
                401: status.HTTP_401_UNAUTHORIZED,
                403: status.HTTP_403_FORBIDDEN,
                404: status.HTTP_404_NOT_FOUND,
                429: status.HTTP_429_TOO_MANY_REQUESTS,
                500: status.HTTP_502_BAD_GATEWAY,  # External service error
                502: status.HTTP_502_BAD_GATEWAY,
                503: status.HTTP_503_SERVICE_UNAVAILABLE,
            }
            
            http_status = status_mapping.get(apideck_status, status.HTTP_502_BAD_GATEWAY)
            
            # Extract error message from Apideck response
            error_message = "QuickBooks sync failed"
            if isinstance(apideck_body, dict):
                error_message = apideck_body.get('message', apideck_body.get('error', error_message))
            elif isinstance(apideck_body, str):
                error_message = apideck_body
            
            raise HTTPException(
                status_code=http_status,
                detail=f"QuickBooks API error: {error_message}"
            )
        else:
            # Generic error without Apideck details
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sync expense to QuickBooks"
            )

async def _pull_expenses_from_quickbooks(user: User, session: AsyncSession) -> dict[str, Any]:
    """
    Fetches recent expenses from QuickBooks and synchronizes them into the local database.
    
    For each expense retrieved from QuickBooks, attempts to link it to a Brikli tenant by matching the customer reference. Only expenses associated with a valid tenant and property are imported. Returns the number of new expenses synced and any errors encountered during the process.
    
    Returns:
        A dictionary containing the count of newly synced expenses and a list of error messages, if any.
    """
    integration = await get_user_integration(user, session, IntegrationType.QUICKBOOKS)
    if not integration or integration.status != IntegrationStatus.CONNECTED or not integration.apideck_consumer_id:
        return {"synced_count": 0, "errors": ["QuickBooks connection not found or inactive."]}

    apideck_client = get_apideck_client(integration.apideck_consumer_id)
    new_expenses_count = 0
    errors = []

    try:
        expenses_response = await asyncio.to_thread(
            apideck_client.accounting.expenses.list,
            service_id="quickbooks"
        )
        if expenses_response and hasattr(expenses_response, '__iter__'):
            for page in expenses_response:
                if hasattr(page, 'data'):
                    qb_expenses = getattr(page, 'data', [])
                    if not qb_expenses:
                        continue
                    
                    # --- N+1 Query Fix ---
                    # 1. Get all QB IDs from the current page
                    qb_expense_ids = [
                        getattr(exp, 'id', None) for exp in qb_expenses if getattr(exp, 'id', None)
                    ]
                    
                    # 2. Pre-fetch all existing expense IDs from the database in a single query
                    existing_expenses_query = select(Expense.quickbooks_id).where(
                        col(Expense.quickbooks_id).in_(qb_expense_ids)
                    )
                    existing_ids_result = await session.execute(existing_expenses_query)
                    existing_ids = {row[0] for row in existing_ids_result}
                    # --- End N+1 Query Fix ---

                    for qb_expense in qb_expenses:
                        qb_expense_id = getattr(qb_expense, 'id', None)
                        if not qb_expense_id: continue

                        # 3. Check against the pre-fetched set instead of a DB call per item
                        if qb_expense_id in existing_ids:
                            continue
                        
                        # Get customer from expense to link to a tenant
                        customer_ref = getattr(qb_expense, 'customer', None)
                        if not customer_ref or not getattr(customer_ref, 'id', None):
                            logger.warning(f"Expense {qb_expense_id} from QuickBooks has no associated customer. Skipping.")
                            continue
                        
                        qb_customer_id = customer_ref.id
                        tenant = await session.scalar(select(Tenant).where(col(Tenant.quickbooks_id) == qb_customer_id))
                        
                        if not tenant or not tenant.current_property_id:
                            logger.warning(f"Could not find Brikli tenant or tenant's property for QB Customer ID {qb_customer_id}. Skipping expense {qb_expense_id}.")
                            continue
                        
                        new_brikli_expense = Expense(
                            category=getattr(qb_expense.line_items[0].category, 'name', 'Uncategorized') if qb_expense.line_items and len(qb_expense.line_items) > 0 else 'Uncategorized',
                            description=f"Expense synced from QuickBooks. QB ID: {qb_expense_id}",
                            expense_date=qb_expense.transaction_date or datetime.now(timezone.utc),
                            subtotal_amount=Decimal(str(getattr(qb_expense, 'sub_total', 0))),
                            total_tax_amount=Decimal(str(getattr(qb_expense, 'total_tax', 0))),
                            property_id=tenant.current_property_id,
                            quickbooks_id=qb_expense_id,
                            last_synced_at=datetime.now(timezone.utc)
                        )
                        session.add(new_brikli_expense)
                        new_expenses_count += 1
    except Exception as e:
        logger.error(f"Error pulling expenses from QuickBooks for user {user.id}: {e}", exc_info=True)
        errors.append(f"An unexpected error occurred: {str(e)}")

    if new_expenses_count > 0:
        await session.commit()
    
    return {"synced_count": new_expenses_count, "errors": errors}
