import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col, desc

from ....models.user import User
from ....models.tenant import Tenant
from ....models.property import Property
from ....models.lease import Lease, LeaseStatus
from ....models.accounting.invoice import Invoice
from ..schemas.invoice import InvoiceSchema
from .base_service import BaseQuickBooksService, SyncAction, SyncPreview

logger = logging.getLogger(__name__)


class InvoiceService(BaseQuickBooksService):
    """Service for QuickBooks Invoice operations."""

    async def sync_invoices(self) -> Dict[str, Any]:
        """Perform bidirectional invoice synchronization."""
        return await self.sync_invoices_internal()

    async def preview_invoices(self) -> SyncPreview:
        """Preview what would happen during invoice synchronization."""
        # Create a preview-mode service
        preview_service = InvoiceService(self.user, self.session, preview_mode=True)
        await preview_service.initialize()
        await preview_service.sync_invoices_internal()
        return preview_service._generate_preview()

    async def sync_invoices_internal(self) -> Dict[str, Any]:
        """Perform bidirectional invoice synchronization."""
        await self.initialize()

        all_errors = []
        pulled_count = 0
        pushed_count = 0

        try:
            # Pull invoices from QuickBooks
            pull_result = await self._pull_invoices_from_quickbooks()
            pulled_count = pull_result.get("synced_count", 0)
            all_errors.extend(pull_result.get("errors", []))

            # Push invoices to QuickBooks
            push_result = await self._push_invoices_to_quickbooks()
            pushed_count = push_result.get("pushed_count", 0)
            all_errors.extend(push_result.get("errors", []))

            total_synced = pulled_count + pushed_count

            # Update integration sync time on success
            if total_synced > 0 and len(all_errors) == 0:
                await self._update_integration_sync_time()

            self._log_operation(
                operation="sync_invoices",
                level="info" if len(all_errors) == 0 else "warning",
                synced_count=total_synced,
                pulled_count=pulled_count,
                pushed_count=pushed_count,
                error_count=len(all_errors)
            )

            return self._create_sync_result(
                synced_count=total_synced,
                pulled_count=pulled_count,
                pushed_count=pushed_count,
                errors=all_errors
            )

        except Exception as e:
            logger.error(f"Error in invoice sync for user {self.user.id}: {e}", exc_info=True)
            return self._create_sync_result(errors=[f"Invoice sync failed: {str(e)}"])

    async def _pull_invoices_from_quickbooks(self) -> Dict[str, Any]:
        """Pull invoices from QuickBooks and sync to local database."""
        new_invoices_count = 0
        errors = []

        try:
            # Get invoices from QuickBooks
            invoices_response = await self.client.list_invoices(max_results=100)

            if not invoices_response or "QueryResponse" not in invoices_response:
                return {"synced_count": 0, "errors": ["No invoices found in QuickBooks"]}

            qb_invoices = invoices_response["QueryResponse"].get("Invoice", [])
            if not qb_invoices:
                return {"synced_count": 0, "errors": []}

            # Get existing invoice IDs to avoid duplicates
            qb_invoice_ids = [invoice.get("Id") for invoice in qb_invoices if invoice.get("Id")]
            existing_ids_result = await self.session.execute(
                select(Invoice.quickbooks_id).where(col(Invoice.quickbooks_id).in_(qb_invoice_ids))
            )
            existing_ids = {row[0] for row in existing_ids_result}

            # Prefetch all tenants and their active leases for this user to avoid N+1 queries
            tenants_with_leases = await self._prefetch_tenants_and_leases()

            for qb_invoice in qb_invoices:
                qb_invoice_id = qb_invoice.get("Id")
                if not qb_invoice_id or qb_invoice_id in existing_ids:
                    continue

                try:
                    # Resolve tenant and lease using prefetched data
                    tenant, lease = self._resolve_tenant_and_lease_from_cache(qb_invoice, tenants_with_leases)

                    if not tenant or not lease:
                        logger.warning(f"Skipping invoice {qb_invoice_id} - could not resolve tenant/lease")
                        continue

                    # Create Brikli invoice from QuickBooks data
                    new_invoice, tax_details = InvoiceSchema.from_quickbooks(qb_invoice, lease, tenant)

                    # In preview mode, collect item for preview
                    if self.preview_mode:
                        warnings = []
                        if len(tax_details) == 0:
                            warnings.append("No tax details found")

                        self._add_preview_item(
                            entity_type="invoice",
                            entity_id=qb_invoice_id,
                            entity_name=f"Invoice for {tenant.first_name} {tenant.last_name}" if tenant else f"QB Invoice {qb_invoice_id}",
                            action=SyncAction.CREATE,
                            details={
                                "amount": float(new_invoice.total_amount) if new_invoice.total_amount else 0,
                                "due_date": new_invoice.due_date.isoformat() if new_invoice.due_date else None,
                                "tenant": f"{tenant.first_name} {tenant.last_name}" if tenant else "Unknown",
                                "tax_details_count": len(tax_details)
                            },
                            warnings=warnings
                        )
                    else:
                        # Execute the actual creation
                        self.session.add(new_invoice)

                        # Flush to get the invoice ID assigned for tax details
                        await self.session.flush()

                        # Add tax details if any
                        for tax_detail in tax_details:
                            if new_invoice.id is None:
                                raise ValueError(f"Failed to get invoice ID after flush for QB invoice {qb_invoice_id}")
                            tax_detail.invoice_id = new_invoice.id
                            self.session.add(tax_detail)

                        logger.info(f"Synced invoice {qb_invoice_id} from QuickBooks")

                    new_invoices_count += 1

                except Exception as e:
                    error_msg = f"Error processing invoice {qb_invoice_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)

            if new_invoices_count > 0 and self._should_execute_action():
                await self.session.commit()

        except Exception as e:
            logger.error(f"Error pulling invoices from QuickBooks: {e}", exc_info=True)
            errors.append(f"Pull invoices failed: {str(e)}")

        return {"synced_count": new_invoices_count, "errors": errors}

    async def _push_invoices_to_quickbooks(self) -> Dict[str, Any]:
        """Push unsynced Brikli invoices to QuickBooks."""
        pushed_count = 0
        errors = []

        try:
            # Get user's properties to filter invoices
            property_ids_result = await self.session.execute(
                select(Property.id).where(col(Property.user_id) == self.user.id)
            )
            property_ids = [row[0] for row in property_ids_result]

            if not property_ids:
                return {"pushed_count": 0, "errors": ["No properties found for user"]}

            # Find invoices that haven't been synced to QuickBooks
            unsynced_invoices = await self.session.scalars(
                select(Invoice)
                .join(Tenant)
                .where(
                    col(Invoice.property_id).in_(property_ids),  # Use Invoice.property_id directly
                    col(Invoice.quickbooks_id).is_(None),
                    col(Tenant.quickbooks_id).is_not(None)  # Tenant must be synced first
                ).limit(50)  # Limit to avoid timeout
            )
            unsynced_invoices_list = list(unsynced_invoices)

            if not unsynced_invoices_list:
                return {"pushed_count": 0, "errors": []}

            # Prefetch all tenants to avoid N+1 queries
            tenant_ids = [invoice.tenant_id for invoice in unsynced_invoices_list]
            tenants = await self.session.scalars(
                select(Tenant).where(col(Tenant.id).in_(tenant_ids))
            )
            tenants_by_id = {tenant.id: tenant for tenant in tenants}

            # Cache service item to avoid multiple API calls
            service_item_id = await self._get_or_cache_service_item()

            for invoice in unsynced_invoices_list:
                try:
                    # Get tenant from prefetched data
                    tenant = tenants_by_id.get(invoice.tenant_id)
                    if not tenant or not tenant.quickbooks_id:
                        errors.append(f"Invoice {invoice.id}: Tenant not synced to QuickBooks")
                        continue

                    # Build QuickBooks invoice data
                    invoice_data = InvoiceSchema.to_quickbooks(invoice, tenant, service_item_id)

                    # In preview mode, collect item for preview
                    if self.preview_mode:
                        warnings = []
                        if not tenant.quickbooks_id:
                            warnings.append("Tenant not synced to QuickBooks")

                        self._add_preview_item(
                            entity_type="invoice",
                            entity_id=str(invoice.id),
                            entity_name=f"Invoice for {tenant.first_name} {tenant.last_name}" if tenant else f"Invoice {invoice.id}",
                            action=SyncAction.CREATE,
                            details={
                                "amount": float(invoice.total_amount) if invoice.total_amount else 0,
                                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                                "tenant": f"{tenant.first_name} {tenant.last_name}" if tenant else "Unknown",
                                "destination": "QuickBooks"
                            },
                            warnings=warnings
                        )
                        pushed_count += 1
                    else:
                        # Create invoice in QuickBooks with retry
                        async def create_operation():
                            return await self.client.create_invoice(invoice_data)

                        response = await self._retry_operation(
                            create_operation,
                            f"create_invoice_{invoice.id}",
                            max_retries=2
                        )

                        if response and "Invoice" in response:
                            qb_invoice = response["Invoice"]
                            qb_invoice_id = qb_invoice.get("Id")

                            if qb_invoice_id:
                                invoice.quickbooks_id = qb_invoice_id
                                invoice.last_synced_at = datetime.now(UTC)
                                self.session.add(invoice)
                                pushed_count += 1
                                logger.info(f"Successfully pushed invoice {invoice.id} to QuickBooks with ID {qb_invoice_id}")
                            else:
                                errors.append(f"Invoice {invoice.id}: QuickBooks response missing ID")
                        else:
                            errors.append(f"Invoice {invoice.id}: Invalid QuickBooks response")

                except Exception as e:
                    error_msg = f"Error pushing invoice {invoice.id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)

            # Commit all successful updates (only in non-preview mode)
            if pushed_count > 0 and self._should_execute_action():
                await self.session.commit()

        except Exception as e:
            logger.error(f"Error pushing invoices to QuickBooks: {e}", exc_info=True)
            errors.append(f"Push invoices failed: {str(e)}")

        return {"pushed_count": pushed_count, "errors": errors}

    async def _resolve_tenant_and_lease_from_qb_invoice(self, qb_invoice: Dict[str, Any]) -> Tuple[Optional[Tenant], Optional[Lease]]:
        """Resolve tenant and lease from QuickBooks invoice customer reference."""
        qb_customer_id = InvoiceSchema.get_customer_id(qb_invoice)
        if not qb_customer_id:
            return None, None

        # Find tenant by QuickBooks customer ID
        tenant = await self.session.scalar(
            select(Tenant).where(
                col(Tenant.quickbooks_id) == qb_customer_id,
                col(Tenant.user_id) == self.user.id
            )
        )

        if not tenant:
            return None, None

        # Find active lease for the tenant
        active_lease = await self.session.scalar(
            select(Lease).where(
                col(Lease.tenant_id) == tenant.id,
                col(Lease.status) == LeaseStatus.ACTIVE
            ).order_by(desc(Lease.start_date))
        )

        return tenant, active_lease

    async def _prefetch_tenants_and_leases(self) -> Dict[str, Tuple[Tenant, Optional[Lease]]]:
        """Prefetch all tenants with their active leases to avoid N+1 queries."""
        # Get all user's tenants with QuickBooks IDs
        tenants = await self.session.scalars(
            select(Tenant).where(
                col(Tenant.user_id) == self.user.id,
                col(Tenant.quickbooks_id).is_not(None)
            )
        )
        tenants_list = list(tenants)

        if not tenants_list:
            return {}

        # Get tenant IDs
        tenant_ids = [tenant.id for tenant in tenants_list]

        # Prefetch active leases for all tenants
        active_leases = await self.session.scalars(
            select(Lease).where(
                col(Lease.tenant_id).in_(tenant_ids),
                col(Lease.status) == LeaseStatus.ACTIVE
            ).order_by(desc(Lease.start_date))
        )

        # Create tenant to lease mapping
        lease_by_tenant = {}
        for lease in active_leases:
            if lease.tenant_id not in lease_by_tenant:
                lease_by_tenant[lease.tenant_id] = lease

        # Create customer ID to tenant+lease mapping
        result = {}
        for tenant in tenants_list:
            if tenant.quickbooks_id and tenant.id is not None:
                active_lease = lease_by_tenant.get(tenant.id)
                result[tenant.quickbooks_id] = (tenant, active_lease)

        return result

    def _resolve_tenant_and_lease_from_cache(self, qb_invoice: Dict[str, Any], tenant_cache: Dict[str, Tuple[Tenant, Optional[Lease]]]) -> Tuple[Optional[Tenant], Optional[Lease]]:
        """Resolve tenant and lease from cached data."""
        qb_customer_id = InvoiceSchema.get_customer_id(qb_invoice)
        if not qb_customer_id:
            return None, None

        tenant_lease_tuple = tenant_cache.get(qb_customer_id)
        if tenant_lease_tuple:
            return tenant_lease_tuple

        return None, None

    async def _get_or_cache_service_item(self) -> str:
        """Get or cache service item ID to avoid multiple API calls."""
        async def fetch_service_item():
            return await self._get_or_create_default_service_item()

        return await self._get_or_cache_quickbooks_data("default_service_item_id", fetch_service_item)

    async def _get_or_create_default_service_item(self) -> str:
        """Get or create a default service item for invoices."""
        # Check integration metadata for cached service item
        cached_item_id = await self._get_cached_metadata("default_service_item_id")
        if cached_item_id:
            return cached_item_id

        try:
            # Search for existing service items
            items_response = await self.client.query_items(
                where_clause="Active=true AND Type='Service'",
                max_results=50
            )

            if items_response and "QueryResponse" in items_response:
                items = items_response["QueryResponse"].get("Item", [])

                # Look for a service item suitable for rent/property management
                for item in items:
                    item_name = item.get("Name", "").lower()
                    if any(keyword in item_name for keyword in ["rent", "service", "property", "income"]):
                        item_id = item.get("Id")
                        if item_id:
                            await self._cache_metadata("default_service_item_id", item_id)
                            return item_id

                # Use the first service item if no specific one found
                if items and items[0].get("Id"):
                    item_id = items[0]["Id"]
                    await self._cache_metadata("default_service_item_id", item_id)
                    return item_id

            # Create a new service item if none found
            service_item_data = {
                "Item": {
                    "Name": "Property Management Service",
                    "Type": "Service",
                    "IncomeAccountRef": {
                        "value": await self._get_default_income_account_id()
                    },
                    "Active": True,
                    "Description": "Property management and rental services"
                }
            }

            create_response = await self.client.create_item(service_item_data)

            if create_response and "Item" in create_response:
                new_item_id = create_response["Item"].get("Id")
                if new_item_id:
                    await self._cache_metadata("default_service_item_id", new_item_id)
                    logger.info(f"Created new service item {new_item_id} for user {self.user.id}")
                    return new_item_id

            # Fallback: return "1" (common default in sandbox)
            logger.warning(f"Unable to find or create service item for user {self.user.id}, using fallback ID '1'")
            return "1"

        except Exception as e:
            logger.error(f"Error getting/creating service item: {e}", exc_info=True)
            return "1"

    async def _get_default_income_account_id(self) -> str:
        """Get a default income account ID for the service item."""
        try:
            accounts_response = await self.client.query_accounts(
                where_clause="Active=true AND Classification='Revenue'",
                max_results=20
            )

            if accounts_response and "QueryResponse" in accounts_response:
                accounts = accounts_response["QueryResponse"].get("Account", [])

                for account in accounts:
                    account_type = account.get("AccountType", "").upper()
                    if account_type in ["INCOME", "OTHER_INCOME"]:
                        account_id = account.get("Id")
                        if account_id:
                            return account_id

                # Use first account if no specific income account found
                if accounts and accounts[0].get("Id"):
                    return accounts[0]["Id"]
        except Exception as e:
            logger.error(f"Error finding income account: {e}")

        # Fallback to commonly used income account ID in QuickBooks
        return "1"