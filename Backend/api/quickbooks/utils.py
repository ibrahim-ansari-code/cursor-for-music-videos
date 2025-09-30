import asyncio
import logging
import random
from datetime import datetime, timedelta, UTC
from typing import Callable, Any, Awaitable, Optional, Dict, List, Union, Tuple
from uuid import uuid4
from sqlalchemy import desc
from sqlmodel import col

from cachetools import TTLCache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, SQLModel
from fastapi import HTTPException, status

from Backend.config import settings
from Backend.models.user import User
from Backend.models.accounting.integration import Integration, IntegrationStatus, IntegrationType
from Backend.models.accounting.quickbooks_integration import QuickBooksIntegration
from Backend.models.tenant import Tenant
from Backend.models.lease import Lease, LeaseStatus
from Backend.utils.datetime_utils import create_audit_datetime
from .intuit_client import get_intuit_client_for_user
from .crypto_utils import encrypt_token, decrypt_token
logger = logging.getLogger(__name__)

# === Configuration ===
RATE_LIMIT_REQUESTS = settings.QB_RATE_LIMIT_REQUESTS
RATE_LIMIT_WINDOW_HOURS = settings.QB_RATE_LIMIT_WINDOW_HOURS


# === Error Message Sanitization ===
def sanitize_error_message(error_message: str) -> str:
    """Sanitize error messages for safe user display."""
    # Import from auth service to avoid duplication
    from .services.auth_service import QuickBooksAuthService
    return QuickBooksAuthService.sanitize_error(error_message)

# === Structured Logging ===
def log_quickbooks_operation(
    operation: str,
    user_id: str,
    level: str = "info",
    **context
) -> None:
    """
    Logs QuickBooks operations with structured business context for Sentry.

    Args:
        operation: The operation being performed (e.g., "sync_payments", "create_expense")
        user_id: The user ID performing the operation
        level: Log level (info, warning, error, critical)
        **context: Additional context to include in the log
    """
    try:
        # Import here to avoid circular imports
        import sentry_sdk

        # Base context for all QuickBooks operations
        base_context = {
            "feature": "quickbooks_integration",
            "service": "intuit",
            "operation": operation,
            "user_id": user_id,
        }

        # Merge with additional context
        log_context = {**base_context, **context}

        # Create structured log message
        message = f"QuickBooks {operation.replace('_', ' ').title()}"
        if context.get("status"):
            message += f" - {context['status']}"

        # Log with appropriate level
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(message, extra={"context": log_context})

        # Also send to Sentry with structured context
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("feature", "quickbooks_integration")
            scope.set_tag("operation", operation)
            scope.set_context("quickbooks", log_context)

            if level.lower() == "error":
                sentry_sdk.capture_message(message, level="error")
            elif level.lower() == "warning":
                sentry_sdk.capture_message(message, level="warning")
            else:
                # For info level, just add breadcrumb
                sentry_sdk.add_breadcrumb(
                    message=message,
                    category="quickbooks",
                    level="info",
                    data=log_context
                )

    except Exception as e:
        # Fallback to regular logging if Sentry logging fails
        logger.error(f"Failed to log QuickBooks operation {operation}: {e}")
        logger.info(f"QuickBooks {operation}: user_id={user_id}, context={context}")

# === Rate Limiting ===
# Memory-based rate limiting with TTL cache
from cachetools import TTLCache
from datetime import datetime, UTC

user_request_cache: TTLCache[str, List[datetime]] = TTLCache(
    maxsize=1000,  # Maximum number of users to track
    ttl=RATE_LIMIT_WINDOW_HOURS * 3600  # TTL in seconds
)
rate_limit_lock = asyncio.Lock()

async def check_rate_limit(user_id: str) -> bool:
    """
    Determines if a user is within the allowed number of requests for the current rate limit window.

    Tracks recent request timestamps per user in an in-memory cache with TTL. Returns True if the user
    has made fewer than the maximum allowed requests in the configured time window.

    Args:
        user_id: Unique user identifier

    Returns:
        True if request is allowed, False if rate limited
    """
    async with rate_limit_lock:
        now = datetime.now(UTC)
        
        # Get or initialize request list for this user
        if user_id not in user_request_cache:
            user_request_cache[user_id] = []
        
        request_list = user_request_cache[user_id]
        window_start = now - timedelta(hours=RATE_LIMIT_WINDOW_HOURS)
        
        # Clean old requests (belt-and-suspenders with TTL cache)
        request_list[:] = [req_time for req_time in request_list if req_time > window_start]
        
        # Check if under limit
        if len(request_list) >= RATE_LIMIT_REQUESTS:
            return False
        
        # Record this request
        request_list.append(now)
        user_request_cache[user_id] = request_list
        
        return True


# === Helper Functions ===
async def get_quickbooks_client(user: User, session: AsyncSession):
    """
    Returns an Intuit QuickBooks client for the given user.

    Raises:
        HTTPException: If QuickBooks integration is not configured or credentials are missing.
    """
    try:
        return await get_intuit_client_for_user(user.id, session)
    except Exception as e:
        logger.error(f"Failed to get QuickBooks client for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QuickBooks integration is not configured properly."
        )

# Removed get_or_create_integration - use QuickBooksAuthService instead

async def get_user_integration(
    user: User,
    session: AsyncSession, 
    integration_type: IntegrationType = IntegrationType.QUICKBOOKS
) -> Integration | None:
    """
    Retrieves an existing integration record for a user and integration type.
    
    Returns:
        The Integration instance if found, otherwise None.
    """
    return await session.scalar(
        select(Integration).where(
            Integration.user_id == user.id,
            Integration.integration_type == integration_type
        )
    )

# Apideck functions removed - replaced with direct Intuit integration

def normalize_qb_datetime(date_str: Optional[str]) -> datetime:
    """
    Parses a date or datetime string from QuickBooks into a timezone-aware datetime object.
    Defaults to the current UTC time if the input is None or invalid.
    """
    if not date_str:
        return datetime.now(UTC)
    try:
        # Handles both 'YYYY-MM-DD' and 'YYYY-MM-DDTHH:MM:SSZ' formats
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            # Parse date-only string and explicitly set to UTC at start of day
            dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=UTC)
        
        # Ensure the datetime is timezone-aware (convert if necessary)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        logger.warning("Could not parse date string '%s'. Defaulting to now().", date_str)
        return datetime.now(UTC)

async def resolve_tenant_and_lease_from_qb_object(session: AsyncSession, qb_object: object) -> Tuple[Optional[Tenant], Optional[Lease]]:
    """
    Finds the Brikli tenant and their active lease from a QuickBooks object (e.g., invoice, payment).
    """
    customer_ref = getattr(qb_object, 'customer', None)
    customer_id = getattr(customer_ref, 'id', None) if customer_ref else None

    if not customer_id:
        return None, None

    tenant = await session.scalar(select(Tenant).where(col(Tenant.quickbooks_id) == customer_id))
    if not tenant:
        logger.warning("Could not find Brikli tenant for QB Customer ID %s", customer_id)
        return None, None

    lease = await session.scalar(
        select(Lease)
        .where(Lease.tenant_id == tenant.id, Lease.status == LeaseStatus.ACTIVE)
        .order_by(desc(col(Lease.start_date)))
        .limit(1)
    )
    if not lease:
        logger.warning(
            "Could not find active lease for tenant %s to associate with QB object %s",
            tenant.id,
            getattr(qb_object, 'id', 'Unknown')
        )
    
    return tenant, lease

async def is_already_synced(session: AsyncSession, qb_id: str, model_class: type[SQLModel]) -> bool:
    """Checks if a QuickBooks entity with a given ID has already been synced."""
    # Use string-based column access to avoid static type issues
    query = select(model_class).where(col(getattr(model_class, 'quickbooks_id')) == qb_id)
    result = await session.scalar(query)
    return result is not None

async def check_quickbooks_connection_health(
    user: User,
    session: AsyncSession,
    perform_deep_check: bool = False
) -> Dict[str, Any]:
    """Simple QuickBooks connection health check."""
    integration = await get_user_integration(user, session, IntegrationType.QUICKBOOKS)

    if not integration:
        return {
            "is_healthy": False,
            "status": "not_configured",
            "issues": ["QuickBooks integration not found"]
        }

    is_connected = integration.status == IntegrationStatus.CONNECTED
    issues = []

    if not is_connected:
        issues.append("Not connected to QuickBooks")

    if perform_deep_check and is_connected:
        try:
            intuit_client = await get_intuit_client_for_user(user.id, session)
            await asyncio.wait_for(intuit_client.get_company_info(), timeout=10.0)
        except Exception:
            issues.append("API connectivity test failed")

    return {
        "is_healthy": is_connected and not issues,
        "status": "healthy" if is_connected and not issues else "unhealthy",
        "issues": issues
    }


async def validate_quickbooks_configuration(
    user: User,
    session: AsyncSession
) -> Dict[str, Any]:
    """Simple QuickBooks configuration validation."""
    integration = await get_user_integration(user, session, IntegrationType.QUICKBOOKS)

    if not integration or integration.status != IntegrationStatus.CONNECTED:
        return {
            "is_valid": False,
            "missing_config": ["QuickBooks integration not connected"],
            "warnings": [],
            "account_info": {},
            "item_info": {}
        }

    try:
        await get_intuit_client_for_user(user.id, session)
        return {
            "is_valid": True,
            "missing_config": [],
            "warnings": [],
            "account_info": {},
            "item_info": {}
        }
    except Exception:
        return {
            "is_valid": False,
            "missing_config": ["QuickBooks client connection failed"],
            "warnings": [],
            "account_info": {},
            "item_info": {}
        }


async def resolve_default_accounts_intuit(
    intuit_client,
    integration: Integration,
    session: AsyncSession
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve and cache default QuickBooks account IDs for expenses.

    Strategy:
      1) Try cached values in integration.connection_metadata
      2) Fallback: list accounts via Intuit API and pick first matching types
      3) Cache results back into integration.connection_metadata

    Returns:
        Tuple (paid_from_account_id, default_expense_account_id)
    """
    try:
        metadata = integration.connection_metadata or {}
        paid_from_account_id = metadata.get("paid_from_account_id")
        default_expense_account_id = metadata.get("default_expense_account_id")

        if paid_from_account_id and default_expense_account_id:
            return paid_from_account_id, default_expense_account_id

        # Get accounts from QuickBooks
        accounts_response = await intuit_client.list_accounts(max_results=200)

        if not accounts_response or "QueryResponse" not in accounts_response:
            return paid_from_account_id, default_expense_account_id

        accounts = accounts_response["QueryResponse"].get("Account", [])

        candidate_paid_from = None
        candidate_expense = None

        for account in accounts:
            account_type = account.get("AccountType", "").upper()
            account_subtype = account.get("AccountSubType", "").upper()
            account_name = account.get("Name", "").lower()
            account_id = account.get("Id")

            # Look for bank/credit card accounts (for paying expenses)
            if not candidate_paid_from and (
                account_type in {"BANK", "CREDIT_CARD", "CASH"} or
                account_subtype in {"CHECKING", "SAVINGS", "CASH_ON_HAND", "CREDIT_CARD"} or
                any(word in account_name for word in ["bank", "checking", "cash", "credit"])
            ):
                candidate_paid_from = account_id

            # Look for expense accounts (for categorizing expenses)
            if not candidate_expense and (
                account_type in {"EXPENSE", "COST_OF_GOODS_SOLD"} or
                account_subtype in {"OPERATING_EXPENSES", "EXPENSE"} or
                "expense" in account_name
            ):
                candidate_expense = account_id

            if candidate_paid_from and candidate_expense:
                break

        # Cache the results if found
        updated = False
        if candidate_paid_from and not paid_from_account_id:
            metadata["paid_from_account_id"] = candidate_paid_from
            updated = True
        if candidate_expense and not default_expense_account_id:
            metadata["default_expense_account_id"] = candidate_expense
            updated = True

        if updated:
            integration.connection_metadata = metadata
            session.add(integration)
            await session.commit()

        return (
            candidate_paid_from or paid_from_account_id,
            candidate_expense or default_expense_account_id,
        )

    except Exception as e:
        logger.exception("Failed to resolve default QuickBooks accounts via Intuit API")
        return None, None


# === Batch Processing Utilities ===
async def process_in_batches(
    items: List[object],
    batch_processor: Callable[[List[object]], Awaitable[Dict[str, Union[int, float, str, List[str]]]]],
    batch_size: int = 100,
    delay_between_batches: float = 0.5
) -> Dict[str, Union[int, float, str, List[str]]]:
    """
    Process a list of items in batches with configurable batch size and delays.

    Args:
        items: List of items to process
        batch_processor: Async function that processes a batch and returns results
        batch_size: Number of items to process in each batch
        delay_between_batches: Delay in seconds between batches to respect rate limits

    Returns:
        Dictionary with aggregated results from all batches
    """
    total_processed = 0
    total_errors: List[str] = []
    total_results: Dict[str, Union[int, float, str, List[str]]] = {}

    # Process items in chunks
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_number = (i // batch_size) + 1
        total_batches = (len(items) + batch_size - 1) // batch_size

        logger.info(f"Processing batch {batch_number}/{total_batches} ({len(batch)} items)")

        try:
            batch_result = await batch_processor(batch)

            # Aggregate results
            if isinstance(batch_result, dict):
                for key, value in batch_result.items():
                    if key == "errors" and isinstance(value, list):
                        total_errors.extend(value)
                    elif isinstance(value, (int, float)):
                        existing_value = total_results.get(key, 0)
                        if isinstance(existing_value, (int, float)) and isinstance(value, (int, float)):
                            total_results[key] = existing_value + value  # type: ignore[operator]
                        else:
                            total_results[key] = value
                    elif key not in total_results:
                        total_results[key] = value

            total_processed += len(batch)

            # Add delay between batches to respect rate limits
            if i + batch_size < len(items) and delay_between_batches > 0:
                await asyncio.sleep(delay_between_batches)

        except Exception as e:
            logger.error(f"Error processing batch {batch_number}: {e}", exc_info=True)
            total_errors.append(f"Batch {batch_number} failed: {str(e)[:100]}")

    # Add error list to results if there were any errors
    if total_errors:
        total_results["errors"] = total_errors

    total_results["total_processed"] = total_processed
    return total_results


async def batch_database_operations(
    session: AsyncSession,
    operations: List[Callable[[], Awaitable[object]]],
    batch_size: int = 50,
    commit_each_batch: bool = True
) -> List[object]:
    """
    Execute database operations in batches for better performance.

    Args:
        session: Database session
        operations: List of async functions that perform database operations
        batch_size: Number of operations to execute before committing
        commit_each_batch: Whether to commit after each batch

    Returns:
        List of results from all operations
    """
    results: List[object] = []

    for i in range(0, len(operations), batch_size):
        batch_ops = operations[i:i + batch_size]
        batch_results = []

        try:
            # Execute all operations in the batch
            for operation in batch_ops:
                result = await operation()
                batch_results.append(result)

            # Commit the batch if requested
            if commit_each_batch:
                await session.commit()

            results.extend(batch_results)
            logger.debug(f"Completed database batch {(i // batch_size) + 1} with {len(batch_ops)} operations")

        except Exception as e:
            # Rollback on error
            await session.rollback()
            logger.error(f"Database batch failed, rolled back: {e}", exc_info=True)
            raise

    return results


# === Retry Logic ===
async def retry_with_exponential_backoff(
    func: Callable[[], Awaitable[object]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    ),
    operation_name: str = "operation"
) -> object:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exceptions that should trigger a retry
        operation_name: Name of the operation for logging

    Returns:
        Result of the function call

    Raises:
        The last exception if all retries are exhausted
    """
    last_exception = None

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            result = await func()

            if attempt > 0:
                logger.info(f"QuickBooks {operation_name} succeeded after {attempt} retries")

            return result

        except Exception as e:
        # Check if the exception is one of the retryable types
            if not isinstance(e, retryable_exceptions):
                # Non-retryable exception, fail immediately
                logger.error(f"QuickBooks {operation_name} failed with non-retryable error: {e}")
                raise
            
            last_exception = e

            if attempt == max_retries:
                logger.error(f"QuickBooks {operation_name} failed after {max_retries} retries: {e}")
                break

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** attempt), max_delay)

            # Add jitter to prevent thundering herd
            if jitter:
                delay += random.uniform(0, delay * 0.1)

            logger.warning(
                f"QuickBooks {operation_name} attempt {attempt + 1} failed: {e}. "
                f"Retrying in {delay:.2f} seconds..."
            )

            await asyncio.sleep(delay)

    # All retries exhausted
    if last_exception:
        raise last_exception
    else:
        raise RuntimeError(f"QuickBooks {operation_name} failed: maximum retries exceeded")

