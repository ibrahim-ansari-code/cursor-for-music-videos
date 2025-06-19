import asyncio
import logging
from typing import Any, Optional
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from apideck_unify import EmailType, PhoneNumberType
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlmodel import col

from Backend.models.user import User
from Backend.models.accounting.integration import IntegrationStatus, IntegrationType    
from .utils import get_user_integration, get_apideck_client
from Backend.models.tenant import Tenant
from Backend.database import async_session

logger = logging.getLogger(__name__)

# Lock to prevent race conditions during sync operations
sync_lock = asyncio.Lock()


async def _search_existing_customer(
    apideck_client: Any, 
    email: str
) -> tuple[Optional[str], bool, Optional[Any]]:
    """
    Search for an existing customer in QuickBooks by email.
    
    Returns:
        Tuple of (customer_id, needs_update, existing_customer_data)
    """
    try:
        search_response = await asyncio.to_thread(
            apideck_client.accounting.customers.list,
            filter_={"email": email},
            limit=1,
            fields="id,display_name,first_name,last_name,email"
        )
        
        if search_response:
            for page in search_response:
                if hasattr(page, 'data'):
                    page_data = getattr(page, 'data', [])
                    if page_data and len(page_data) > 0:
                        existing_customer = page_data[0]
                        customer_id = getattr(existing_customer, 'id', None)
                        if customer_id:
                            logger.info(
                                "Found existing QuickBooks customer %s for email %s", 
                                customer_id, email
                            )
                            return customer_id, False, existing_customer
                break
    except HTTPException as http_exc:
        # Re-raise authentication/authorization errors to preserve error details
        if http_exc.status_code in [401, 403]:
            logger.error("Authentication/authorization error searching for customer: %s", http_exc.detail)
            raise
        # Log other HTTP errors but continue with creation as fallback
        logger.exception("API error searching for existing customer. Will proceed with creation.")
    except asyncio.TimeoutError:
        logger.exception("Timeout error searching for existing customer. Will proceed with creation.")
    except (ConnectionError, OSError):
        logger.exception("Network error searching for existing customer. Will proceed with creation.")
    
    return None, False, None


def _check_customer_needs_update(
    existing_customer: Any, 
    tenant_data: dict[str, Any]
) -> bool:
    """
    Check if the existing customer data needs to be updated.
    """
    display_name = f"{tenant_data.get('first_name', '')} {tenant_data.get('last_name', '')}".strip()
    return (
        getattr(existing_customer, 'display_name', '') != display_name or 
        getattr(existing_customer, 'first_name', '') != tenant_data.get('first_name', '') or
        getattr(existing_customer, 'last_name', '') != tenant_data.get('last_name', '')
    )


def _prepare_customer_data(tenant_data: dict[str, Any]) -> dict[str, Any]:
    """
    Prepare customer data for QuickBooks API calls.
    """
    emails = []
    if tenant_data.get("email"):
        emails.append({"email": str(tenant_data["email"]), "type": EmailType.PRIMARY})

    phone_numbers = []
    if tenant_data.get("phone"):
        phone_numbers.append({"number": str(tenant_data["phone"]), "type": PhoneNumberType.PRIMARY})
    
    return {
        "display_name": f"{tenant_data.get('first_name', '')} {tenant_data.get('last_name', '')}".strip(),
        "first_name": tenant_data.get("first_name"),
        "last_name": tenant_data.get("last_name"),
        "emails": emails,
        "phone_numbers": phone_numbers
    }


async def _update_existing_customer(
    apideck_client: Any,
    customer_id: str,
    tenant_data: dict[str, Any]
) -> bool:
    """
    Update an existing customer in QuickBooks.
    
    Returns:
        True if update was successful, False otherwise
    """
    try:
        customer_data = _prepare_customer_data(tenant_data)
        
        update_response = await asyncio.to_thread(
            apideck_client.accounting.customers.update,
            id=customer_id,
            **customer_data
        )
        
        if not update_response.update_customer_response or not update_response.update_customer_response.data:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update customer in QuickBooks: Invalid response from Apideck."
            )
        
        logger.info("Updated existing QuickBooks customer %s", customer_id)
        return True
        
    except HTTPException as http_exc:
        # Re-raise authentication/authorization errors to preserve error details
        if http_exc.status_code in [401, 403]:
            logger.error("Authentication/authorization error updating customer %s: %s", customer_id, http_exc.detail)
            raise
        # Log other HTTP errors but continue gracefully
        logger.exception("Failed to update existing customer %s", customer_id)
        return False
    except (asyncio.TimeoutError, ConnectionError, OSError):
        logger.exception("Network/timeout error updating customer %s", customer_id)
        return False


async def _create_new_customer(
    apideck_client: Any,
    tenant_data: dict[str, Any]
) -> str:
    """
    Create a new customer in QuickBooks.
    
    Returns:
        The created customer ID
    
    Raises:
        HTTPException if creation fails
    """
    customer_data = _prepare_customer_data(tenant_data)
    
    response = await asyncio.to_thread(
        apideck_client.accounting.customers.create,
        **customer_data
    )

    if not response.create_customer_response or not response.create_customer_response.data:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create customer in QuickBooks: Invalid response from Apideck."
        )

    created_customer_id = response.create_customer_response.data.id
    logger.info("Created new QuickBooks customer %s", created_customer_id)
    
    return created_customer_id


async def link_or_create_qb_customer(user: User, tenant_data: dict[str, Any]) -> dict[str, Any]:
    """
    Synchronizes a tenant record with QuickBooks as a Customer via the Apideck API.
    
    Searches for an existing QuickBooks customer by the tenant's email. If found, updates the customer data if necessary and returns the QuickBooks customer ID. If not found, creates a new customer in QuickBooks using the tenant's information and returns the new customer ID. Raises HTTP exceptions for integration or API errors.
    
    Args:
        tenant_data: Dictionary containing tenant information such as email, first name, last name, and phone.
    
    Returns:
        A dictionary with the synchronization result, including success status, message, QuickBooks customer ID, and action performed ("linked", "updated", or "created").
    """
    try:
        # Create a fresh database session for this operation
        async with async_session() as session:
            integration = await get_user_integration(user, session, IntegrationType.QUICKBOOKS)
            
            if not integration or integration.status != IntegrationStatus.CONNECTED or not integration.apideck_consumer_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="QuickBooks is not connected or configured properly."
                )

            apideck_client = get_apideck_client(integration.apideck_consumer_id)

            # Step 1: Search for existing customer by email
            existing_customer_id = None
            customer_needs_update = False
            
            if tenant_data.get("email"):
                existing_customer_id, _, existing_customer = await _search_existing_customer(
                    apideck_client, tenant_data["email"]
                )
                
                if existing_customer_id and existing_customer:
                    customer_needs_update = _check_customer_needs_update(existing_customer, tenant_data)

            # Step 2: Update existing customer or create new one
            if existing_customer_id:
                update_success = False
                if customer_needs_update:
                    update_success = await _update_existing_customer(
                        apideck_client, existing_customer_id, tenant_data
                    )
                
                return {
                    "success": True,
                    "message": f"Tenant linked to existing QuickBooks customer{' (updated)' if customer_needs_update and update_success else ''}.",
                    "quickbooks_id": existing_customer_id,
                    "action": "updated" if customer_needs_update and update_success else "linked"
                }
            
            # Create new customer
            created_customer_id = await _create_new_customer(apideck_client, tenant_data)
            
            return {
                "success": True,
                "message": "Tenant synced to QuickBooks successfully as a new Customer.",
                "quickbooks_id": created_customer_id,
                "action": "created"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error syncing tenant to QuickBooks for user %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync tenant to QuickBooks due to an internal error."
        ) from e

async def _link_or_create_qb_customer(user: User, session: AsyncSession, tenant_data: dict[str, Any]) -> dict[str, Any]:
    """
    DEPRECATED: Wrapper for backward compatibility with link_or_create_qb_customer.
    
    Calls link_or_create_qb_customer to synchronize a tenant with QuickBooks. This function will be removed in a future version.
    """
    logger.warning("_link_or_create_qb_customer is deprecated. Use link_or_create_qb_customer instead.")
    return await link_or_create_qb_customer(user, tenant_data)

async def _pull_and_link_customers(user: User, session: AsyncSession) -> dict[str, Any]:
    """
    Synchronizes QuickBooks customers with local tenants by linking or creating records.
    
    Fetches all customers from QuickBooks, matches them to local tenants by email, and links them if not already linked. If a matching tenant does not exist, creates a new tenant record with the customer's information. Returns counts of linked and created tenants, along with any errors encountered.
    """
    async with sync_lock:
        integration = await get_user_integration(user, session, IntegrationType.QUICKBOOKS)
        if not integration or not integration.apideck_consumer_id:
            return {"linked": 0, "created": 0, "errors": ["QuickBooks not connected."]}

        apideck_client = get_apideck_client(integration.apideck_consumer_id)
        linked_count, created_count, errors = 0, 0, []

        try:
            # Step 1: Collect all customer emails from QuickBooks
            all_customers = []
            customers_response = await asyncio.to_thread(apideck_client.accounting.customers.list)
            if customers_response:
                for page in customers_response:
                    all_customers.extend(getattr(page, 'data', []))
            
            customer_emails = [
                email.email for customer in all_customers 
                if customer.emails and len(customer.emails) > 0 and (email := customer.emails[0]) and email.email
            ]

            # Step 2: Fetch all matching tenants from the database in one query
            if customer_emails:
                tenants_query = select(Tenant).where(
                    col(Tenant.landlord_id) == user.id,
                    col(Tenant.email).in_(customer_emails)
                )
                tenants_result = await session.execute(tenants_query)
                existing_tenants = {t.email: t for t in tenants_result.scalars().all()}
            else:
                existing_tenants = {}

            # Step 3: Process customers, linking or creating tenants
            objects_to_add = []
            for qb_customer in all_customers:
                customer_email = getattr(qb_customer.emails[0], 'email', None) if qb_customer.emails and len(qb_customer.emails) > 0 else None
                if not customer_email or not getattr(qb_customer, 'id', None):
                    continue

                tenant = existing_tenants.get(customer_email)
                
                if tenant:
                    # Tenant exists, link if not already linked
                    if not tenant.quickbooks_id:
                        tenant.quickbooks_id = qb_customer.id
                        tenant.last_synced_at = datetime.now(UTC)
                        objects_to_add.append(tenant)
                        linked_count += 1
                else:
                    # Tenant does not exist, create a new one
                    new_tenant = Tenant(
                        first_name=getattr(qb_customer, 'first_name', ''),
                        last_name=getattr(qb_customer, 'last_name', ''),
                        email=customer_email,
                        phone=getattr(qb_customer.phone_numbers[0], 'number', None) if qb_customer.phone_numbers and len(qb_customer.phone_numbers) > 0 else None,
                        landlord_id=user.id,
                        quickbooks_id=qb_customer.id,
                        last_synced_at=datetime.now(UTC)
                    )
                    objects_to_add.append(new_tenant)
                    created_count += 1

            # Batch add all modified and new objects at once
            if objects_to_add:
                session.add_all(objects_to_add)
                await session.commit()
        except Exception:
            logger.exception("Error pulling/linking customers for user %s", user.id)
            errors.append("An unexpected error occurred during customer sync.")

        return {"linked": linked_count, "created": created_count, "errors": errors}

async def _push_unlinked_tenants(user: User, session: AsyncSession) -> dict[str, Any]:
    """
    Creates QuickBooks customers for all local tenants of a user that are not yet linked.
    
    Finds tenants without a QuickBooks ID, creates corresponding customers in QuickBooks, updates local records with the new linkage, and commits changes. Returns the number of tenants created and any errors encountered.
    """
    async with sync_lock:
        unlinked_tenants_query = select(Tenant).where(
            col(Tenant.landlord_id) == user.id,
            col(Tenant.quickbooks_id).is_(None)
        )
        unlinked_tenants = (await session.execute(unlinked_tenants_query)).scalars().all()
        
        created_count = 0
        errors = []

        for tenant in unlinked_tenants:
            try:
                tenant_dict = tenant.model_dump()
                # This function will find-or-create, but since we're filtering for unlinked,
                # it will effectively only create.
                sync_result = await link_or_create_qb_customer(user=user, tenant_data=tenant_dict)
                if sync_result.get("success") and sync_result.get("quickbooks_id"):
                    tenant.quickbooks_id = sync_result["quickbooks_id"]
                    tenant.last_synced_at = datetime.now(UTC)
                    session.add(tenant)
                    created_count += 1
            except HTTPException as http_exc:
                logger.warning(
                    "HTTP error when pushing tenant %s to QuickBooks: %s", tenant.id, http_exc.detail
                )
                errors.append(f"Tenant {tenant.first_name} {tenant.last_name}: {http_exc.detail}")
            except Exception:
                logger.exception("Failed to push unlinked tenant %s to QuickBooks", tenant.id)
                errors.append(f"Tenant {tenant.first_name} {tenant.last_name}: An unexpected error occurred.")

        if created_count > 0:
            await session.commit()
            
        return {"created": created_count, "errors": errors}
