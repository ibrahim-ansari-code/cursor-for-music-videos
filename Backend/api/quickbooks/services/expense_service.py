import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from ....models.user import User
from ....models.property import Property
from ....models.accounting.expense import Expense
from ..schemas.expense import ExpenseSchema
from .base_service import BaseQuickBooksService, SyncAction, SyncPreview

logger = logging.getLogger(__name__)


class ExpenseService(BaseQuickBooksService):
    """Service for QuickBooks Expense/Purchase operations."""

    async def sync_expenses(self) -> Dict[str, Any]:
        """Perform bidirectional expense synchronization."""
        return await self.sync_expenses_internal()

    async def preview_expenses(self) -> SyncPreview:
        """Preview what would happen during expense synchronization."""
        # Create a preview-mode service
        preview_service = ExpenseService(self.user, self.session, preview_mode=True)
        await preview_service.initialize()
        await preview_service.sync_expenses_internal()
        return preview_service._generate_preview()

    async def sync_expenses_internal(self) -> Dict[str, Any]:
        """Perform bidirectional expense synchronization."""
        await self.initialize()

        all_errors = []
        pulled_count = 0
        pushed_count = 0

        try:
            # Pull expenses from QuickBooks
            pull_result = await self._pull_expenses_from_quickbooks()
            pulled_count = pull_result.get("synced_count", 0)
            all_errors.extend(pull_result.get("errors", []))

            # Push expenses to QuickBooks
            push_result = await self._push_expenses_to_quickbooks()
            pushed_count = push_result.get("pushed_count", 0)
            all_errors.extend(push_result.get("errors", []))

            total_synced = pulled_count + pushed_count

            # Update integration sync time on success
            if total_synced > 0 and len(all_errors) == 0:
                await self._update_integration_sync_time()

            self._log_operation(
                operation="sync_expenses",
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
            logger.error(f"Error in expense sync for user {self.user.id}: {e}", exc_info=True)
            return self._create_sync_result(errors=[f"Expense sync failed: {str(e)}"])

    async def _pull_expenses_from_quickbooks(self) -> Dict[str, Any]:
        """Pull expenses from QuickBooks and sync to local database."""
        new_expenses_count = 0
        errors = []

        try:
            # Get purchases from QuickBooks (expenses are typically recorded as Purchase entities)
            purchases_response = await self.client.list_purchases(max_results=100)

            if not purchases_response or "QueryResponse" not in purchases_response:
                return {"synced_count": 0, "errors": ["No purchases found in QuickBooks"]}

            qb_purchases = purchases_response["QueryResponse"].get("Purchase", [])
            if not qb_purchases:
                return {"synced_count": 0, "errors": []}

            # Get existing expense IDs to avoid duplicates
            qb_purchase_ids = [purchase.get("Id") for purchase in qb_purchases if purchase.get("Id")]
            existing_ids_result = await self.session.execute(
                select(Expense.quickbooks_id).where(col(Expense.quickbooks_id).in_(qb_purchase_ids))
            )
            existing_ids = {row[0] for row in existing_ids_result}

            # Use user's first property for all expenses (cache this)
            user_property = await self._get_or_cache_user_property()

            if not user_property:
                return {"synced_count": 0, "errors": ["User has no properties available"]}

            # Cache tax account mapping to identify tax lines
            tax_account_mapping = ExpenseSchema.get_canadian_tax_accounts()

            for qb_purchase in qb_purchases:
                qb_purchase_id = qb_purchase.get("Id")
                if not qb_purchase_id or qb_purchase_id in existing_ids:
                    continue

                try:
                    # Create Brikli expense from QuickBooks data with tax details
                    new_expense, tax_details = ExpenseSchema.from_quickbooks(qb_purchase, user_property, tax_account_mapping)

                    # In preview mode, collect item for preview
                    if self.preview_mode:
                        warnings = []
                        if len(tax_details) == 0:
                            warnings.append("No tax details found")

                        self._add_preview_item(
                            entity_type="expense",
                            entity_id=qb_purchase_id,
                            entity_name=new_expense.description or f"QB Purchase {qb_purchase_id}",
                            action=SyncAction.CREATE,
                            details={
                                "amount": float(new_expense.subtotal_amount + new_expense.total_tax_amount),
                                "category": new_expense.category,
                                "date": new_expense.expense_date.isoformat() if new_expense.expense_date else None,
                                "tax_details_count": len(tax_details),
                                "payment_method": new_expense.payment_method.value if new_expense.payment_method else None
                            },
                            warnings=warnings
                        )
                    else:
                        # Execute the actual creation
                        self.session.add(new_expense)

                        # Add tax details if any
                        for tax_detail in tax_details:
                            tax_detail.expense_id = new_expense.id
                            self.session.add(tax_detail)

                        logger.info(f"Synced expense {qb_purchase_id} from QuickBooks with {len(tax_details)} tax details")

                    new_expenses_count += 1

                except Exception as e:
                    error_msg = f"Error processing purchase {qb_purchase_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)

            if new_expenses_count > 0 and self._should_execute_action():
                await self.session.commit()

        except Exception as e:
            logger.error(f"Error pulling expenses from QuickBooks: {e}", exc_info=True)
            errors.append(f"Pull expenses failed: {str(e)}")

        return {"synced_count": new_expenses_count, "errors": errors}

    async def _push_expenses_to_quickbooks(self) -> Dict[str, Any]:
        """Push unsynced Brikli expenses to QuickBooks."""
        pushed_count = 0
        errors = []

        try:
            # Get user's properties to filter expenses
            property_ids_result = await self.session.execute(
                select(Property.id).where(col(Property.user_id) == self.user.id)
            )
            property_ids = [row[0] for row in property_ids_result]

            if not property_ids:
                return {"pushed_count": 0, "errors": ["No properties found for user"]}

            # Find expenses that haven't been synced to QuickBooks
            unsynced_expenses = await self.session.scalars(
                select(Expense).where(
                    col(Expense.property_id).in_(property_ids),
                    col(Expense.quickbooks_id).is_(None)
                ).limit(50)  # Limit to avoid timeout
            )
            unsynced_expenses_list = list(unsynced_expenses)

            if not unsynced_expenses_list:
                return {"pushed_count": 0, "errors": []}

            # Cache default accounts to avoid multiple API calls
            paid_from_account_id, expense_account_id = await self._get_or_cache_default_accounts()

            # Cache tax account mapping for tax line creation
            tax_account_mapping = await self._get_or_cache_tax_accounts()

            for expense in unsynced_expenses_list:
                try:
                    # Build QuickBooks expense data with tax support
                    expense_data = ExpenseSchema.to_quickbooks(
                        expense,
                        paid_from_account_id,
                        expense_account_id,
                        tax_account_mapping
                    )

                    # In preview mode, collect item for preview
                    if self.preview_mode:
                        warnings: list[str] = []
                        validation_errors = ExpenseSchema.validate_for_quickbooks(expense)
                        if validation_errors:
                            warnings.extend([str(msg) for msg in validation_errors.values()])

                        self._add_preview_item(
                            entity_type="expense",
                            entity_id=str(expense.id),
                            entity_name=expense.description or f"Expense {expense.id}",
                            action=SyncAction.CREATE,
                            details={
                                "amount": float(expense.subtotal_amount + expense.total_tax_amount),
                                "category": expense.category,
                                "date": expense.expense_date.isoformat() if expense.expense_date else None,
                                "payment_method": expense.payment_method.value if expense.payment_method else None,
                                "destination": "QuickBooks"
                            },
                            warnings=warnings
                        )
                        pushed_count += 1
                    else:
                        # Create expense in QuickBooks with retry
                        async def create_operation():
                            return await self.client.create_purchase(expense_data)

                        response = await self._retry_operation(
                            create_operation,
                            f"create_expense_{expense.id}",
                            max_retries=2
                        )

                        if response and "Purchase" in response:
                            qb_expense = response["Purchase"]
                            qb_expense_id = qb_expense.get("Id")

                            if qb_expense_id:
                                expense.quickbooks_id = qb_expense_id
                                expense.last_synced_at = datetime.now(UTC)
                                self.session.add(expense)
                                pushed_count += 1
                                logger.info(f"Successfully pushed expense {expense.id} to QuickBooks with ID {qb_expense_id}")
                            else:
                                errors.append(f"Expense {expense.id}: QuickBooks response missing ID")
                        else:
                            errors.append(f"Expense {expense.id}: Invalid QuickBooks response")

                except Exception as e:
                    error_msg = f"Error pushing expense {expense.id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)

            # Commit all successful updates (only in non-preview mode)
            if pushed_count > 0 and self._should_execute_action():
                await self.session.commit()

        except Exception as e:
            logger.error(f"Error pushing expenses to QuickBooks: {e}", exc_info=True)
            errors.append(f"Push expenses failed: {str(e)}")

        return {"pushed_count": pushed_count, "errors": errors}

    async def _get_default_accounts(self) -> Tuple[str, str]:
        """Get default accounts for expenses."""
        # Check integration metadata for cached accounts
        paid_from = await self._get_cached_metadata("default_paid_from_account_id")
        expense_account = await self._get_cached_metadata("default_expense_account_id")

        if paid_from and expense_account:
            return paid_from, expense_account

        try:
            # Get accounts from QuickBooks
            accounts_response = await self.client.list_accounts(max_results=100)

            if accounts_response and "QueryResponse" in accounts_response:
                accounts = accounts_response["QueryResponse"].get("Account", [])

                paid_from_account_id = "1"  # Default fallback
                expense_account_id = "1"   # Default fallback

                for account in accounts:
                    account_type = account.get("AccountType", "").upper()
                    account_subtype = account.get("AccountSubType", "").upper()

                    # Look for bank/checking account for "paid from"
                    if account_type == "BANK" or account_subtype == "CHECKING":
                        paid_from_account_id = account.get("Id", "1")

                    # Look for expense account
                    elif account_type == "EXPENSE":
                        expense_account_id = account.get("Id", "1")

                # Cache the accounts
                await self._cache_metadata("default_paid_from_account_id", paid_from_account_id)
                await self._cache_metadata("default_expense_account_id", expense_account_id)

                return paid_from_account_id, expense_account_id

        except Exception as e:
            logger.error(f"Error getting default accounts: {e}")

        return "1", "1"

    async def _get_or_cache_user_property(self) -> Optional[Property]:
        """Get or cache user's first property."""
        async def fetch_property():
            return await self.session.scalar(
                select(Property).where(col(Property.user_id) == self.user.id).limit(1)
            )

        return await self._get_or_cache_quickbooks_data("user_property", fetch_property)

    async def _get_or_cache_default_accounts(self) -> Tuple[str, str]:
        """Get or cache default accounts to avoid multiple API calls."""
        cached_accounts = self._get_session_cache("default_accounts")
        if cached_accounts:
            return cached_accounts

        accounts = await self._get_default_accounts()
        self._set_session_cache("default_accounts", accounts)
        return accounts

    async def _get_or_cache_tax_accounts(self) -> Dict[str, str]:
        """Get or cache tax account mapping."""
        cached_tax_accounts = self._get_session_cache("tax_account_mapping")
        if cached_tax_accounts:
            return cached_tax_accounts

        # TEMPORARILY DISABLED: Tax account mapping returns account names instead of IDs
        # This causes QuickBooks validation errors. Return empty mapping to skip tax lines.
        # TODO: Implement proper account ID lookup from QuickBooks Chart of Accounts
        tax_accounts: Dict[str, str] = {}  # Empty mapping disables tax line creation
        self._set_session_cache("tax_account_mapping", tax_accounts)
        return tax_accounts

    async def create_expense_in_quickbooks(self, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a single expense in QuickBooks.

        Args:
            expense_data: Dictionary containing expense details from Brikli

        Returns:
            Dictionary with success status, message, and QuickBooks ID if successful
        """
        await self.initialize()

        try:
            # Get default accounts
            paid_from_account_id, expense_account_id = await self._get_default_accounts()

            # Validate expense data (basic validation)
            if not expense_data.get("total_amount") or float(expense_data["total_amount"]) <= 0:
                return {
                    "success": False,
                    "message": "Invalid expense amount",
                    "quickbooks_id": None
                }

            # Build QuickBooks expense data
            total_amount = float(expense_data.get("total_amount", 0))
            tx_date = expense_data.get("expense_date", datetime.now().strftime('%Y-%m-%d'))
            description = expense_data.get("description", "Expense from Brikli")

            purchase_data = {
                "Purchase": {
                    "AccountRef": {
                        "value": str(paid_from_account_id)
                    },
                    "PaymentType": "Cash",  # Default payment type
                    "TxnDate": tx_date,
                    "Line": [
                        {
                            "Id": "1",
                            "Amount": total_amount,
                            "DetailType": "AccountBasedExpenseLineDetail",
                            "AccountBasedExpenseLineDetail": {
                                "AccountRef": {
                                    "value": str(expense_account_id)
                                }
                            },
                            "Description": description
                        }
                    ],
                    "PrivateNote": description
                }
            }

            # Create expense in QuickBooks with retry
            async def create_operation():
                return await self.client.create_purchase(purchase_data)

            response = await self._retry_operation(
                create_operation,
                f"create_single_expense_{expense_data.get('id', 'unknown')}",
                max_retries=2
            )

            if response and "Purchase" in response:
                purchase = response["Purchase"]
                quickbooks_id = purchase.get("Id")

                if quickbooks_id:
                    self._log_operation(
                        operation="create_expense",
                        level="info",
                        status="success",
                        quickbooks_id=quickbooks_id,
                        expense_amount=expense_data.get("total_amount"),
                        expense_category=expense_data.get("category")
                    )
                    return {
                        "success": True,
                        "message": "Expense created in QuickBooks successfully",
                        "quickbooks_id": quickbooks_id
                    }

            # Failed to get valid response
            self._log_operation(
                operation="create_expense",
                level="warning",
                status="failed",
                error="Invalid response from QuickBooks",
                expense_amount=expense_data.get("total_amount")
            )
            return {
                "success": False,
                "message": "Failed to create expense: Invalid response from QuickBooks",
                "quickbooks_id": None
            }

        except Exception as e:
            logger.error(f"Error creating expense in QuickBooks: {e}", exc_info=True)

            self._log_operation(
                operation="create_expense",
                level="error",
                status="failed",
                error=str(e),
                expense_amount=expense_data.get("total_amount")
            )

            return {
                "success": False,
                "message": f"QuickBooks service error: {str(e)}",
                "quickbooks_id": None
            }