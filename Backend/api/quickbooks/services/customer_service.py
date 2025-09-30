import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from Backend.models.user import User
from Backend.models.tenant import Tenant
from Backend.database import async_session
from ..schemas.customer import CustomerSchema
from .base_service import BaseQuickBooksService

logger = logging.getLogger(__name__)


class CustomerService(BaseQuickBooksService):
    """Service for QuickBooks Customer operations."""

    async def sync_customers(self) -> Dict[str, Any]:
        """Synchronize customers between QuickBooks and Brikli."""
        await self.initialize()

        all_errors = []
        total_synced = 0

        try:
            # Pull and link existing customers from QuickBooks
            pull_result = await self._pull_and_link_customers()
            total_synced += pull_result.get("linked_count", 0)
            all_errors.extend(pull_result.get("errors", []))

            # Push unlinked tenants to QuickBooks (creates new customers)
            push_result = await self._push_unlinked_tenants()
            total_synced += push_result.get("pushed_count", 0)
            all_errors.extend(push_result.get("errors", []))

            # Update existing linked customers that need updates
            update_result = await self._push_customer_updates()
            total_synced += update_result.get("updated_count", 0)
            all_errors.extend(update_result.get("errors", []))

            # Update integration sync time on success
            if total_synced > 0 and len(all_errors) == 0:
                await self._update_integration_sync_time()

            self._log_operation(
                operation="sync_customers",
                level="info" if len(all_errors) == 0 else "warning",
                synced_count=total_synced,
                error_count=len(all_errors)
            )

            return self._create_sync_result(synced_count=total_synced, errors=all_errors)

        except Exception as e:
            logger.error(f"Error in customer sync for user {self.user.id}: {e}", exc_info=True)
            return self._create_sync_result(errors=[f"Customer sync failed: {str(e)}"])

    async def _pull_and_link_customers(self) -> Dict[str, Any]:
        """Pull customers from QuickBooks and link them to existing tenants."""
        linked_count = 0
        errors = []

        try:
            # Get customers from QuickBooks (cache for session)
            async def fetch_customers():
                customers_response = await self.client.list_customers(max_results=100)
                if customers_response and "QueryResponse" in customers_response:
                    return customers_response["QueryResponse"].get("Customer", [])
                return []

            qb_customers = await self._get_or_cache_quickbooks_data("qb_customers", fetch_customers)

            if not qb_customers:
                return {"linked_count": 0, "errors": ["No customers found in QuickBooks"]}

            # Get all user's tenants that don't have QuickBooks IDs in one query
            unlinked_tenants = await self.session.scalars(
                select(Tenant).where(
                    col(Tenant.user_id) == self.user.id,
                    col(Tenant.quickbooks_id).is_(None)
                )
            )
            unlinked_tenants_list = list(unlinked_tenants)

            if not unlinked_tenants_list:
                return {"linked_count": 0, "errors": []}

            # Create email lookup for QuickBooks customers
            qb_customers_by_email = {}
            for qb_customer in qb_customers:
                qb_email_obj = qb_customer.get("PrimaryEmailAddr", {})
                qb_email = qb_email_obj.get("Address", "") if qb_email_obj else ""
                if qb_email:
                    qb_customers_by_email[qb_email.lower()] = qb_customer

            # Match tenants to customers by email
            for tenant in unlinked_tenants_list:
                if not tenant.email:
                    continue

                qb_customer = qb_customers_by_email.get(tenant.email.lower())
                if qb_customer:
                    tenant.quickbooks_id = qb_customer.get("Id")
                    tenant.last_synced_at = datetime.now(UTC)
                    self.session.add(tenant)
                    linked_count += 1
                    logger.info(f"Linked tenant {tenant.id} to QuickBooks customer {tenant.quickbooks_id}")

            if linked_count > 0:
                await self.session.commit()

        except Exception as e:
            logger.error(f"Error pulling customers from QuickBooks: {e}", exc_info=True)
            errors.append(f"Pull customers failed: {str(e)}")

        return {"linked_count": linked_count, "errors": errors}

    async def _push_unlinked_tenants(self) -> Dict[str, Any]:
        """Push unlinked tenants to QuickBooks as customers."""
        pushed_count = 0
        errors = []

        try:
            # Get tenants that haven't been synced to QuickBooks
            unlinked_tenants = await self.session.scalars(
                select(Tenant).where(
                    col(Tenant.user_id) == self.user.id,
                    col(Tenant.quickbooks_id).is_(None),
                    col(Tenant.email).is_not(None)
                )
            )

            for tenant in unlinked_tenants:
                try:
                    # Check for existing customer by email first
                    if not tenant.email:
                        continue
                    existing_customer_id = await self._find_existing_customer_by_email(tenant.email)

                    if existing_customer_id:
                        # Link to existing customer
                        tenant.quickbooks_id = existing_customer_id
                        tenant.last_synced_at = datetime.now(UTC)
                        self.session.add(tenant)
                        pushed_count += 1
                        logger.info(f"Linked tenant {tenant.id} to existing QuickBooks customer {existing_customer_id}")
                    else:
                        # Create new customer
                        customer_id = await self._create_customer_in_quickbooks(tenant)
                        if customer_id:
                            tenant.quickbooks_id = customer_id
                            tenant.last_synced_at = datetime.now(UTC)
                            self.session.add(tenant)
                            pushed_count += 1
                            logger.info(f"Created QuickBooks customer {customer_id} for tenant {tenant.id}")
                        else:
                            errors.append(f"Failed to create QuickBooks customer for tenant {tenant.id}")

                except Exception as e:
                    error_msg = f"Error processing tenant {tenant.id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)

            # Commit all successful updates
            if pushed_count > 0:
                await self.session.commit()

        except Exception as e:
            logger.error(f"Error pushing tenants to QuickBooks: {e}", exc_info=True)
            errors.append(f"Push tenants failed: {str(e)}")

        return {"pushed_count": pushed_count, "errors": errors}

    async def _push_customer_updates(self) -> Dict[str, Any]:
        """Update existing QuickBooks customers that need updates."""
        updated_count = 0
        errors = []

        try:
            # Get tenants that have QuickBooks IDs (already linked)
            linked_tenants = await self.session.scalars(
                select(Tenant).where(
                    col(Tenant.user_id) == self.user.id,
                    col(Tenant.quickbooks_id).is_not(None)
                )
            )
            linked_tenants_list = list(linked_tenants)

            if not linked_tenants_list:
                return {"updated_count": 0, "errors": []}

            # Process tenants in batches to avoid timeout
            batch_size = 10
            for i in range(0, len(linked_tenants_list), batch_size):
                batch_tenants = linked_tenants_list[i:i + batch_size]

                for tenant in batch_tenants:
                    try:
                        # Skip if updated recently (within last hour)
                        if (tenant.last_synced_at and
                            tenant.last_synced_at > datetime.now(UTC) - timedelta(hours=1)):
                            continue

                        # Get current customer data from QuickBooks
                        current_customer = await self.client.get_customer(tenant.quickbooks_id)
                        if not current_customer or "Customer" not in current_customer:
                            logger.warning(f"Could not retrieve QuickBooks customer {tenant.quickbooks_id} for tenant {tenant.id}")
                            continue

                        qb_customer = current_customer["Customer"]

                        # Check if update is needed
                        if CustomerSchema.needs_update(qb_customer, tenant):
                            success = await self.update_customer_in_quickbooks(tenant)
                            if success:
                                updated_count += 1
                                logger.info(f"Updated QuickBooks customer {tenant.quickbooks_id} for tenant {tenant.id}")
                            else:
                                errors.append(f"Failed to update QuickBooks customer for tenant {tenant.id}")
                        else:
                            # No update needed, but refresh sync timestamp
                            tenant.last_synced_at = datetime.now(UTC)
                            self.session.add(tenant)

                    except Exception as e:
                        error_msg = f"Error processing tenant {tenant.id} for update: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg, exc_info=True)

                # Commit after each batch
                await self.session.commit()

        except Exception as e:
            logger.error(f"Error pushing customer updates to QuickBooks: {e}", exc_info=True)
            errors.append(f"Push customer updates failed: {str(e)}")

        return {"updated_count": updated_count, "errors": errors}

    async def _find_existing_customer_by_email(self, email: str) -> Optional[str]:
        """Find existing QuickBooks customer by email."""
        try:
            search_query = CustomerSchema.create_search_query(email)
            search_response = await self.client.query_customers(
                where_clause=search_query,
                max_results=1
            )

            if search_response and "QueryResponse" in search_response:
                customers = search_response["QueryResponse"].get("Customer", [])
                if customers:
                    return customers[0].get("Id")
        except Exception as e:
            logger.warning(f"Error searching for existing customer with email {email}: {e}")

        return None

    async def _create_customer_in_quickbooks(self, tenant: Tenant) -> Optional[str]:
        """Create a customer in QuickBooks."""
        try:
            # Validate tenant data before creating customer
            validation_errors = CustomerSchema.validate_for_quickbooks(tenant)
            if validation_errors:
                error_msg = f"Validation failed for tenant {tenant.id}: {validation_errors}"
                logger.warning(error_msg)
                # Continue with creation but log warnings

            customer_data = CustomerSchema.to_quickbooks(tenant)

            async def create_operation():
                return await self.client.create_customer(customer_data)

            response = await self._retry_operation(
                create_operation,
                f"create_customer_{tenant.id}",
                max_retries=2
            )

            if response and "Customer" in response:
                customer_id = response["Customer"].get("Id")
                if customer_id:
                    logger.info(f"Successfully created QuickBooks customer with ID: {customer_id}")
                    return customer_id
                else:
                    logger.error("Customer creation response missing ID field")
            else:
                logger.error("Invalid customer creation response from QuickBooks")

        except Exception as e:
            logger.error(f"Failed to create customer in QuickBooks: {e}", exc_info=True)

        return None

    async def update_customer_in_quickbooks(self, tenant: Tenant) -> bool:
        """
        Update an existing QuickBooks customer with current tenant data.

        Args:
            tenant: Tenant object with QuickBooks ID to update

        Returns:
            True if update successful, False otherwise
        """
        if not tenant.quickbooks_id:
            logger.warning(f"Cannot update customer: tenant {tenant.id} has no QuickBooks ID")
            return False

        try:
            await self.initialize()

            # First, get the current customer data from QuickBooks to get the SyncToken
            current_customer = await self.client.get_customer(tenant.quickbooks_id)
            if not current_customer or "Customer" not in current_customer:
                logger.error(f"Could not retrieve QuickBooks customer {tenant.quickbooks_id} for update")
                return False

            qb_customer = current_customer["Customer"]
            sync_token = qb_customer.get("SyncToken")
            if not sync_token:
                logger.error(f"Missing SyncToken for QuickBooks customer {tenant.quickbooks_id}")
                return False

            # Check if update is actually needed
            if not CustomerSchema.needs_update(qb_customer, tenant):
                logger.info(f"No update needed for QuickBooks customer {tenant.quickbooks_id}")
                tenant.last_synced_at = datetime.now(UTC)
                self.session.add(tenant)
                await self.session.commit()
                return True

            # Prepare update data
            update_data = CustomerSchema.to_quickbooks_update(tenant, tenant.quickbooks_id, sync_token)

            # Perform the update with retry
            async def update_operation():
                return await self.client.update_customer(tenant.quickbooks_id, update_data)

            response = await self._retry_operation(
                update_operation,
                f"update_customer_{tenant.id}",
                max_retries=2
            )

            if response and "Customer" in response:
                # Update successful, update sync timestamp
                tenant.last_synced_at = datetime.now(UTC)
                self.session.add(tenant)
                await self.session.commit()

                logger.info(f"Successfully updated QuickBooks customer {tenant.quickbooks_id} for tenant {tenant.id}")

                self._log_operation(
                    operation="update_customer",
                    level="info",
                    status="success",
                    tenant_id=tenant.id,
                    customer_id=tenant.quickbooks_id
                )
                return True
            else:
                logger.error(f"Invalid response from QuickBooks customer update for tenant {tenant.id}")
                return False

        except Exception as e:
            logger.error(f"Failed to update QuickBooks customer for tenant {tenant.id}: {e}", exc_info=True)
            self._log_operation(
                operation="update_customer",
                level="error",
                status="failed",
                tenant_id=tenant.id,
                customer_id=tenant.quickbooks_id,
                error=str(e)
            )
            return False

    async def link_or_create_qb_customer(self, tenant_data: Dict[str, Any]) -> Optional[str]:
        """
        Links a tenant to an existing QuickBooks customer or creates a new one.

        This function is used by the tenants service to sync individual tenants
        with QuickBooks customers during tenant creation.

        Args:
            tenant_data: Dictionary containing tenant information including:
                - email: Required for linking/creating
                - first_name: Optional
                - last_name: Optional
                - phone: Optional
                - id: Tenant ID for logging

        Returns:
            QuickBooks customer ID if successful, None otherwise

        Raises:
            HTTPException: If QuickBooks integration is not configured
        """
        async with async_session() as session:
            service = CustomerService(self.user, session)
            await service.initialize()

            email = tenant_data.get("email")
            if not email:
                logger.warning("Cannot link/create QuickBooks customer: email is required")
                return None

            try:
                # First, search for existing customer by email
                existing_customer_id = await service._find_existing_customer_by_email(email)

                if existing_customer_id:
                    # Log successful linking to existing customer
                    service._log_operation(
                        operation="link_customer",
                        level="info",
                        status="linked_existing",
                        tenant_id=tenant_data.get("id"),
                        customer_id=existing_customer_id
                    )
                    return existing_customer_id

                # No existing customer found, create a new one
                # Create a temporary tenant object for schema transformation
                temp_tenant = Tenant(
                    first_name=tenant_data.get("first_name"),
                    last_name=tenant_data.get("last_name"),
                    email=tenant_data.get("email"),
                    phone=tenant_data.get("phone"),
                    user_id=self.user.id
                )

                customer_id = await service._create_customer_in_quickbooks(temp_tenant)

                if customer_id:
                    # Log successful customer creation
                    service._log_operation(
                        operation="create_customer",
                        level="info",
                        status="created",
                        tenant_id=tenant_data.get("id"),
                        customer_id=customer_id
                    )
                    return customer_id
                else:
                    # Log failure to create customer
                    service._log_operation(
                        operation="create_customer",
                        level="error",
                        status="failed",
                        tenant_id=tenant_data.get("id"),
                        error="Failed to create customer in QuickBooks"
                    )
                    return None

            except Exception as e:
                # Log operation failure
                service._log_operation(
                    operation="link_or_create_customer",
                    level="error",
                    status="failed",
                    tenant_id=tenant_data.get("id"),
                    error=str(e)
                )
                logger.error(f"Error linking/creating QuickBooks customer for tenant {tenant_data.get('id')}: {e}", exc_info=True)
                raise