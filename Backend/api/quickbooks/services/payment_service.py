import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col, desc

from ....models.user import User
from ....models.tenant import Tenant
from ....models.property import Property
from ....models.lease import Lease, LeaseStatus
from ....models.accounting.payment import Payment, PaymentStatus
from ....models.accounting.invoice import Invoice
from ....models.accounting.common import PaymentStatus as CommonPaymentStatus
from ..schemas.payment import PaymentSchema
from .base_service import BaseQuickBooksService, SyncAction, SyncPreview

logger = logging.getLogger(__name__)


class PaymentService(BaseQuickBooksService):
    """Service for QuickBooks Payment operations."""

    async def sync_payments(self) -> Dict[str, Any]:
        """Perform bidirectional payment synchronization."""
        return await self.sync_payments_internal()

    async def preview_payments(self) -> SyncPreview:
        """Preview what would happen during payment synchronization."""
        # Create a preview-mode service
        preview_service = PaymentService(self.user, self.session, preview_mode=True)
        await preview_service.initialize()
        await preview_service.sync_payments_internal()
        return preview_service._generate_preview()

    async def sync_payments_internal(self) -> Dict[str, Any]:
        """Perform bidirectional payment synchronization."""
        await self.initialize()

        all_errors = []
        pulled_count = 0
        pushed_count = 0

        try:
            # Pull payments from QuickBooks
            pull_result = await self._pull_payments_from_quickbooks()
            pulled_count = pull_result.get("synced_count", 0)
            all_errors.extend(pull_result.get("errors", []))

            # Push payments to QuickBooks
            push_result = await self._push_payments_to_quickbooks()
            pushed_count = push_result.get("pushed_count", 0)
            all_errors.extend(push_result.get("errors", []))

            total_synced = pulled_count + pushed_count

            # Update integration sync time on success
            if total_synced > 0 and len(all_errors) == 0:
                await self._update_integration_sync_time()

            self._log_operation(
                operation="sync_payments",
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
            logger.error(f"Error in payment sync for user {self.user.id}: {e}", exc_info=True)
            return self._create_sync_result(errors=[f"Payment sync failed: {str(e)}"])

    async def _pull_payments_from_quickbooks(self) -> Dict[str, Any]:
        """Pull payments from QuickBooks and sync to local database."""
        new_payments_count = 0
        errors = []

        try:
            # Get payments from QuickBooks
            payments_response = await self.client.list_payments(max_results=100)

            if not payments_response or "QueryResponse" not in payments_response:
                return {"synced_count": 0, "errors": ["No payments found in QuickBooks"]}

            qb_payments = payments_response["QueryResponse"].get("Payment", [])
            if not qb_payments:
                return {"synced_count": 0, "errors": []}

            # Get existing payment IDs to avoid duplicates
            qb_payment_ids = [payment.get("Id") for payment in qb_payments if payment.get("Id")]
            existing_ids_result = await self.session.execute(
                select(Payment.quickbooks_id).where(col(Payment.quickbooks_id).in_(qb_payment_ids))
            )
            existing_ids = {row[0] for row in existing_ids_result}

            # Prefetch all tenants and their active leases for this user to avoid N+1 queries
            tenants_with_leases = await self._prefetch_tenants_and_leases()

            for qb_payment in qb_payments:
                qb_payment_id = qb_payment.get("Id")
                if not qb_payment_id or qb_payment_id in existing_ids:
                    continue

                try:
                    # Resolve tenant and lease using prefetched data
                    tenant, lease = self._resolve_tenant_and_lease_from_cache(qb_payment, tenants_with_leases)

                    if not tenant or not lease:
                        logger.warning(f"Skipping payment {qb_payment_id} - could not resolve tenant/lease")
                        continue

                    # Create Brikli payment from QuickBooks data
                    new_payment = PaymentSchema.from_quickbooks(qb_payment, lease, tenant)

                    # In preview mode, collect item for preview
                    if self.preview_mode:
                        warnings: list[str] = []

                        self._add_preview_item(
                            entity_type="payment",
                            entity_id=qb_payment_id,
                            entity_name=f"Payment from {tenant.first_name} {tenant.last_name}" if tenant else f"QB Payment {qb_payment_id}",
                            action=SyncAction.CREATE,
                            details={
                                "amount": float(new_payment.amount) if new_payment.amount else 0,
                                "payment_date": new_payment.payment_date.isoformat() if new_payment.payment_date else None,
                                "tenant": f"{tenant.first_name} {tenant.last_name}" if tenant else "Unknown",
                                "payment_method": new_payment.payment_method.value if new_payment.payment_method else None
                            },
                            warnings=warnings
                        )
                    else:
                        # Execute the actual creation
                        self.session.add(new_payment)
                        logger.info(f"Synced payment {qb_payment_id} from QuickBooks")

                    new_payments_count += 1

                except Exception as e:
                    error_msg = f"Error processing payment {qb_payment_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)

            if new_payments_count > 0 and self._should_execute_action():
                await self.session.commit()

        except Exception as e:
            logger.error(f"Error pulling payments from QuickBooks: {e}", exc_info=True)
            errors.append(f"Pull payments failed: {str(e)}")

        return {"synced_count": new_payments_count, "errors": errors}

    async def _push_payments_to_quickbooks(self) -> Dict[str, Any]:
        """Push unsynced Brikli payments to QuickBooks."""
        pushed_count = 0
        errors = []

        try:
            # Get user's properties to filter payments
            property_ids_result = await self.session.execute(
                select(Property.id).where(col(Property.user_id) == self.user.id)
            )
            property_ids = [row[0] for row in property_ids_result]

            if not property_ids:
                return {"pushed_count": 0, "errors": ["No properties found for user"]}

            # Find payments that haven't been synced to QuickBooks
            unsynced_payments = await self.session.scalars(
                select(Payment).join(Lease).join(Tenant).where(
                    col(Tenant.current_property_id).in_(property_ids),
                    col(Payment.quickbooks_id).is_(None),
                    col(Tenant.quickbooks_customer_id).is_not(None),  # Tenant must be synced first
                    col(Payment.status) == PaymentStatus.PAID  # Only push confirmed payments
                ).limit(50)  # Limit to avoid timeout
            )
            unsynced_payments_list = list(unsynced_payments)

            if not unsynced_payments_list:
                return {"pushed_count": 0, "errors": []}

            # Prefetch all tenants to avoid N+1 queries
            tenant_ids = [payment.tenant_id for payment in unsynced_payments_list]
            tenants = await self.session.scalars(
                select(Tenant).where(col(Tenant.id).in_(tenant_ids))
            )
            tenants_by_id = {tenant.id: tenant for tenant in tenants}

            # Prefetch latest unpaid invoice per tenant using DISTINCT ON for Postgres
            # Ensures we always link to the most recent unpaid invoice if any
            unpaid_invoices = await self.session.scalars(
                select(Invoice)
                .where(
                    col(Invoice.tenant_id).in_(tenant_ids),
                    col(Invoice.quickbooks_id).is_not(None),
                    col(Invoice.status).in_([CommonPaymentStatus.PENDING, CommonPaymentStatus.DRAFT])
                )
                .distinct(col(Invoice.tenant_id))
                .order_by(col(Invoice.tenant_id), desc(col(Invoice.issue_date)))
            )
            unpaid_invoices_by_tenant = {}
            for invoice in unpaid_invoices:
                unpaid_invoices_by_tenant[invoice.tenant_id] = invoice

            for payment in unsynced_payments_list:
                try:
                    # Get tenant from prefetched data
                    tenant = tenants_by_id.get(payment.tenant_id)
                    if not tenant or not tenant.quickbooks_customer_id:
                        errors.append(f"Payment {payment.id}: Tenant not synced to QuickBooks")
                        continue

                    # Build QuickBooks payment data
                    payment_data = PaymentSchema.to_quickbooks(payment, tenant)

                    # Try to link to unpaid invoice if available
                    unpaid_invoice = unpaid_invoices_by_tenant.get(tenant.id)
                    if unpaid_invoice and unpaid_invoice.quickbooks_id:
                        payment_data = PaymentSchema.add_invoice_link(payment_data, unpaid_invoice.quickbooks_id)

                    # In preview mode, collect item for preview
                    if self.preview_mode:
                        warnings = []
                        if not tenant.quickbooks_customer_id:
                            warnings.append("Tenant not synced to QuickBooks")

                        self._add_preview_item(
                            entity_type="payment",
                            entity_id=str(payment.id),
                            entity_name=f"Payment from {tenant.first_name} {tenant.last_name}" if tenant else f"Payment {payment.id}",
                            action=SyncAction.CREATE,
                            details={
                                "amount": float(payment.amount) if payment.amount else 0,
                                "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
                                "tenant": f"{tenant.first_name} {tenant.last_name}" if tenant else "Unknown",
                                "payment_method": payment.payment_method.value if payment.payment_method else None,
                                "linked_invoice": f"Invoice {unpaid_invoice.id}" if unpaid_invoice else None,
                                "destination": "QuickBooks"
                            },
                            warnings=warnings
                        )
                        pushed_count += 1
                    else:
                        # Create payment in QuickBooks with retry
                        async def create_operation():
                            return await self.client.create_payment(payment_data)

                        response = await self._retry_operation(
                            create_operation,
                            f"create_payment_{payment.id}",
                            max_retries=2
                        )

                        if response and "Payment" in response:
                            qb_payment = response["Payment"]
                            qb_payment_id = qb_payment.get("Id")

                            if qb_payment_id:
                                payment.quickbooks_id = qb_payment_id
                                payment.last_synced_at = datetime.now(UTC)
                                self.session.add(payment)
                                pushed_count += 1
                                logger.info(f"Successfully pushed payment {payment.id} to QuickBooks with ID {qb_payment_id}")
                            else:
                                errors.append(f"Payment {payment.id}: QuickBooks response missing ID")
                        else:
                            errors.append(f"Payment {payment.id}: Invalid QuickBooks response")

                except Exception as e:
                    error_msg = f"Error pushing payment {payment.id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)

            # Commit all successful updates (only in non-preview mode)
            if pushed_count > 0 and self._should_execute_action():
                await self.session.commit()

        except Exception as e:
            logger.error(f"Error pushing payments to QuickBooks: {e}", exc_info=True)
            errors.append(f"Push payments failed: {str(e)}")

        return {"pushed_count": pushed_count, "errors": errors}

    async def _resolve_tenant_and_lease_from_qb_payment(self, qb_payment: Dict[str, Any]) -> Tuple[Optional[Tenant], Optional[Lease]]:
        """Resolve tenant and lease from QuickBooks payment customer reference."""
        qb_customer_id = PaymentSchema.get_customer_id(qb_payment)
        if not qb_customer_id:
            return None, None

        # Find tenant by QuickBooks customer ID
        tenant = await self.session.scalar(
            select(Tenant).where(
                col(Tenant.quickbooks_customer_id) == qb_customer_id,
                col(Tenant.landlord_id) == self.user.id
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
                col(Tenant.landlord_id) == self.user.id,
                col(Tenant.quickbooks_customer_id).is_not(None)
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
            if tenant.quickbooks_customer_id and tenant.id is not None:
                active_lease = lease_by_tenant.get(tenant.id)
                result[tenant.quickbooks_customer_id] = (tenant, active_lease)

        return result

    def _resolve_tenant_and_lease_from_cache(self, qb_payment: Dict[str, Any], tenant_cache: Dict[str, Tuple[Tenant, Optional[Lease]]]) -> Tuple[Optional[Tenant], Optional[Lease]]:
        """Resolve tenant and lease from cached data."""
        qb_customer_id = PaymentSchema.get_customer_id(qb_payment)
        if not qb_customer_id:
            return None, None

        tenant_lease_tuple = tenant_cache.get(qb_customer_id)
        if tenant_lease_tuple:
            return tenant_lease_tuple

        return None, None

    async def _find_unpaid_invoice_for_tenant(self, tenant_id: int | None) -> Optional[Invoice]:
        """Find an unpaid invoice for this tenant to apply the payment to."""
        return await self.session.scalar(
            select(Invoice).where(
                col(Invoice.tenant_id) == tenant_id,
                col(Invoice.quickbooks_id).is_not(None),
                col(Invoice.status).in_([CommonPaymentStatus.PENDING, CommonPaymentStatus.DRAFT])
            ).order_by(desc(col(Invoice.issue_date))).limit(1)
        )