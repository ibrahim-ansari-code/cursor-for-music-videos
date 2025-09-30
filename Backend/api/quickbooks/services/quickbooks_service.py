import logging
import asyncio
from typing import Dict, Any, Optional, cast

from sqlalchemy.ext.asyncio import AsyncSession

from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime
from .base_service import BaseQuickBooksService
from .customer_service import CustomerService
from .invoice_service import InvoiceService
from .payment_service import PaymentService
from .expense_service import ExpenseService
from ..transaction_coordinator import TransactionCoordinator, execute_sync_transaction

logger = logging.getLogger(__name__)


class QuickBooksService(BaseQuickBooksService):
    """
    Main QuickBooks service that coordinates all entity-specific services.

    This service acts as the main entry point for all QuickBooks operations,
    delegating to specialized entity services while maintaining a unified interface.
    """

    def __init__(self, user: User, session: AsyncSession):
        super().__init__(user, session)
        self.customer_service = CustomerService(user, session)
        self.invoice_service = InvoiceService(user, session)
        self.payment_service = PaymentService(user, session)
        self.expense_service = ExpenseService(user, session)

    async def get_connection_status(self) -> Dict[str, Any]:
        """Get QuickBooks connection status."""
        integration = await self._get_user_integration()
        if not integration:
            return {
                "connected": False,
                "status": "not_configured",
                "message": "QuickBooks integration not configured"
            }

        return {
            "connected": integration.status.value == "connected",
            "status": integration.status.value,
            "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
            "connected_at": integration.connected_at.isoformat() if integration.connected_at else None,
            "company_name": integration.connection_metadata.get("company_name") if integration.connection_metadata else None
        }

    # === Customer Operations ===

    async def sync_customers(self) -> Dict[str, Any]:
        """Synchronize customers between QuickBooks and Brikli."""
        return await self.customer_service.sync_customers()

    async def link_or_create_customer(self, tenant_data: Dict[str, Any]) -> Optional[str]:
        """Link or create a QuickBooks customer for a tenant."""
        return await self.customer_service.link_or_create_qb_customer(tenant_data)

    # === Invoice Operations ===

    async def sync_invoices(self) -> Dict[str, Any]:
        """Perform bidirectional invoice synchronization."""
        return await self.invoice_service.sync_invoices()

    # === Payment Operations ===

    async def sync_payments(self) -> Dict[str, Any]:
        """Perform bidirectional payment synchronization."""
        return await self.payment_service.sync_payments()

    # === Expense Operations ===

    async def sync_expenses(self) -> Dict[str, Any]:
        """Perform bidirectional expense synchronization."""
        return await self.expense_service.sync_expenses()

    async def create_expense(self, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single expense in QuickBooks."""
        return await self.expense_service.create_expense_in_quickbooks(expense_data)

    # === High-level Sync Operations ===

    async def perform_sync_all(self) -> Dict[str, Any]:
        """Perform comprehensive synchronization of all data types with transaction support."""
        await self.initialize()

        logger.info(f"Starting comprehensive sync for user {self.user.id}")

        try:
            # Check if we're already in a transaction to avoid nested transaction error
            if self.session.in_transaction():
                logger.info("Already in transaction, proceeding without explicit begin")
                # Proceed without starting a new transaction
                in_existing_transaction = True
            else:
                # Use database transaction for consistency
                in_existing_transaction = False

            if not in_existing_transaction:
                async with self.session.begin():
                    return await self._perform_sync_operations()
            else:
                return await self._perform_sync_operations()

        except Exception as e:
            logger.error(f"Error during comprehensive sync for user {self.user.id}: {e}", exc_info=True)
            # Transaction will auto-rollback on exception
            return {
                "success": False,
                "message": "Comprehensive sync failed",
                "items_synced": 0,
                "sync_details": {},
                "errors": [f"Sync failed: {str(e)}"]
            }

    async def _perform_sync_operations(self) -> Dict[str, Any]:
        """Perform the actual sync operations."""
        all_errors = []
        total_synced = 0
        sync_results = {}

        try:
            # Step 1: Sync customers first (required for other data types)
            customer_result = await self.sync_customers()
            sync_results["customers"] = customer_result
            total_synced += customer_result.get("synced_count", 0)
            if customer_result.get("errors"):
                all_errors.extend(customer_result["errors"])

            # If customer sync completely failed, don't continue
            if not customer_result.get("success", True) and customer_result.get("synced_count", 0) == 0:
                logger.warning("Customer sync failed completely, skipping other syncs")
                return {
                    "success": False,
                    "message": "Sync failed: Customer sync required for other operations",
                    "items_synced": 0,
                    "sync_details": sync_results,
                    "errors": all_errors
                }

            # Step 2: Sync financial records in parallel groups
            # Payments and invoices can sync in parallel
            payment_task = asyncio.create_task(self.sync_payments())
            invoice_task = asyncio.create_task(self.sync_invoices())

            results = await asyncio.gather(
                payment_task, invoice_task, return_exceptions=True
            )
            payment_result, invoice_result = results[0], results[1]

            # Handle payment results
            if isinstance(payment_result, Exception):
                all_errors.append(f"Payment sync failed: {str(payment_result)}")
                sync_results["payments"] = {"success": False, "synced_count": 0}
            else:
                payment_result = cast(Dict[str, Any], payment_result)
                sync_results["payments"] = payment_result
                total_synced += payment_result.get("synced_count", 0)
                if payment_result.get("errors"):
                    all_errors.extend(payment_result["errors"])

            # Handle invoice results
            if isinstance(invoice_result, Exception):
                all_errors.append(f"Invoice sync failed: {str(invoice_result)}")
                sync_results["invoices"] = {"success": False, "synced_count": 0}
            else:
                invoice_result = cast(Dict[str, Any], invoice_result)
                sync_results["invoices"] = invoice_result
                total_synced += invoice_result.get("synced_count", 0)
                if invoice_result.get("errors"):
                    all_errors.extend(invoice_result["errors"])

            # Sync expenses separately (can be heavy)
            expense_result = await self.sync_expenses()
            sync_results["expenses"] = expense_result
            total_synced += expense_result.get("synced_count", 0)
            if expense_result.get("errors"):
                all_errors.extend(expense_result["errors"])

            # Update integration with final sync timestamp
            if self.integration:
                self.integration.last_sync_at = create_audit_datetime()
                # Will be committed by the transaction manager or manually if not in transaction

            success = len(all_errors) == 0
            message = f"Comprehensive sync completed. Synced {total_synced} items"
            if len(all_errors) > 0:
                message += f" with {len(all_errors)} errors"

            self._log_operation(
                operation="sync_all",
                level="info" if success else "warning",
                total_synced=total_synced,
                error_count=len(all_errors),
                **{f"{k}_count": v.get("synced_count", 0) for k, v in sync_results.items()}
            )

            return {
                "success": success,
                "message": message,
                "items_synced": total_synced,
                "sync_details": sync_results,
                "errors": all_errors if all_errors else None
            }

        except Exception as e:
            logger.error(f"Error during sync operations for user {self.user.id}: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Comprehensive sync failed",
                "items_synced": total_synced,
                "sync_details": sync_results,
                "errors": all_errors + [f"Sync failed: {str(e)}"]
            }