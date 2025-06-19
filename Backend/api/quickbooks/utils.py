import asyncio
import logging
from uuid import uuid4
from datetime import datetime, timedelta, UTC
from typing import Callable, Any, Awaitable, Optional
from enum import Enum
from sqlalchemy import desc
from sqlmodel import col

import apideck_unify
from apideck_unify import Apideck
from apideck_unify.models import AccountingCompanyInfoOneResponse
from cachetools import TTLCache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException, status

from Backend.config import settings
from Backend.models.user import User
from Backend.models.accounting.integration import Integration, IntegrationStatus, IntegrationType
from Backend.models.tenant import Tenant
from Backend.models.lease import Lease, LeaseStatus
logger = logging.getLogger(__name__)

# === Configuration ===
APIDECK_SERVICE_ID = getattr(settings, 'APIDECK_SERVICE_ID', 'quickbooks')
RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW_HOURS = 1

# === Startup Validation ===
def validate_apideck_config() -> None:
    """
    Checks that Apideck API credentials are present in the environment at startup.
    
    Raises:
        ValueError: If either APIDECK_API_KEY or APIDECK_APP_ID is missing.
    """
    if not settings.APIDECK_API_KEY or not settings.APIDECK_APP_ID:
        raise ValueError(
            "Apideck configuration is incomplete. Both APIDECK_API_KEY and APIDECK_APP_ID "
            "environment variables must be set for QuickBooks integration to work."
        )
    logger.info("Apideck configuration validated successfully")

# === Operation Handlers ===
class ApideckOperation(Enum):
    """Enum for supported Apideck operations"""
    COMPANY_INFO = "company_info"
    # Add more operations as needed
    # EXPENSES_CREATE = "expenses_create"
    # INVOICES_CREATE = "invoices_create"
    # CUSTOMERS_LIST = "customers_list"

async def _handle_company_info_operation(client: Apideck, service_id: str) -> AccountingCompanyInfoOneResponse:
    """
    Asynchronously retrieves company information from the accounting service via the Apideck client.
    
    Waits up to 30 seconds for the operation to complete before timing out.
    
    Args:
        service_id: Identifier of the accounting service to query.
    
    Returns:
        An AccountingCompanyInfoOneResponse containing the company's information.
    
    Raises:
        asyncio.TimeoutError: If the request does not complete within 30 seconds.
    """
    return await asyncio.wait_for(
        asyncio.to_thread(
            client.accounting.company_info.get,
            service_id=service_id
        ),
        timeout=30.0
    )

# Operation mapping dictionary
OPERATION_HANDLERS: dict[ApideckOperation, Callable[..., Awaitable[Any]]] = {
     ApideckOperation.COMPANY_INFO: _handle_company_info_operation,
 }

# === Rate Limiting ===
# TTL-based rate limiting (prevents memory leaks from inactive users)
# TODO: Implement Redis-based rate limiting for distributed deployments
user_request_cache: TTLCache[str, list[datetime]] = TTLCache(
    maxsize=10000,  # Maximum number of users to track
    ttl=RATE_LIMIT_WINDOW_HOURS * 3600  # TTL in seconds
)
rate_limit_lock = asyncio.Lock()

async def check_rate_limit(user_id: str) -> bool:
    """
    Determines if a user is within the allowed number of requests for the current rate limit window.
    
    Tracks recent request timestamps per user in an in-memory cache. Returns True if the user has made fewer than the maximum allowed requests in the configured time window; otherwise, returns False. Not suitable for distributed or multi-process environments.
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

# === Circuit Breaker ===
class SimpleCircuitBreaker:
    """Simple circuit breaker for external API calls - thread-safe for async use"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60) -> None:
        """
        Initializes the circuit breaker with a failure threshold and recovery timeout.
        
        Args:
            failure_threshold: Number of consecutive failures required to open the circuit.
            recovery_timeout: Seconds to wait before allowing operations after the circuit opens.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()  # Protect shared state
    
    async def can_execute(self) -> bool:
        """
        Checks if the circuit breaker currently allows an operation to proceed.
        
        Returns:
            True if execution is permitted based on the circuit state and recovery timeout; otherwise, False.
        """
        async with self._lock:
            if self.state == "CLOSED":
                return True
            if self.state == "OPEN":
                if (self.last_failure_time and 
                    (datetime.now(UTC) - self.last_failure_time).total_seconds() > self.recovery_timeout):
                    self.state = "HALF_OPEN"
                    return True
                return False
            else:  # HALF_OPEN
                return True
    
    async def record_success(self) -> None:
        """
        Resets the circuit breaker state to CLOSED after a successful operation.
        
        Sets the failure count to zero and transitions the circuit breaker to the CLOSED state.
        """
        async with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"
    
    async def record_failure(self) -> None:
        """
        Records a failure and transitions the circuit breaker to OPEN if the threshold is reached.
        
        Increments the failure count and updates the last failure time. If the number of failures meets or exceeds the configured threshold, the circuit breaker state is set to OPEN to prevent further operations until recovery.
        """
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now(UTC)
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"

# Global circuit breaker instance
apideck_circuit_breaker = SimpleCircuitBreaker()

# === Helper Functions ===
def get_apideck_client(consumer_id: str) -> Apideck:
    """
    Returns an Apideck client configured with API key, app ID, and the specified consumer ID.
    
    Raises:
        RuntimeError: If Apideck API credentials are missing from the environment.
    """
    # Guard clause to ensure credentials are configured
    if not settings.APIDECK_API_KEY or not settings.APIDECK_APP_ID:
        raise RuntimeError(
            "Apideck credentials are not configured. Both APIDECK_API_KEY and APIDECK_APP_ID "
            "environment variables must be set. QuickBooks operations are disabled."
        )
    
    return Apideck(
        api_key=settings.APIDECK_API_KEY,
        consumer_id=consumer_id,
        app_id=settings.APIDECK_APP_ID,
    )

async def get_or_create_integration(
    user: User, 
    session: AsyncSession,
    integration_type: IntegrationType = IntegrationType.QUICKBOOKS,
    service_id: str = APIDECK_SERVICE_ID
) -> Integration:
    """
    Retrieves an existing integration for a user and integration type, or creates and returns a new one if none exists.
    
    If no integration is found, creates a new Integration record with a generated Apideck consumer ID, the specified service ID, and a disconnected status. The new integration is committed to the database and returned.
    """
    integration = await session.scalar(
        select(Integration).where(
            Integration.user_id == user.id,
            Integration.integration_type == integration_type
        )
    )
    
    if not integration:
        # Generate a shorter consumer_id using 12 characters for better length management
        consumer_id = f"brikli-{user.id}-{integration_type.value.lower()}-{uuid4().hex}"
        
        integration = Integration(
            user_id=user.id,
            integration_type=integration_type,
            apideck_consumer_id=consumer_id,
            apideck_service_id=service_id,  # Configurable service identifier
            status=IntegrationStatus.DISCONNECTED
        )
        session.add(integration)
        await session.commit()
        await session.refresh(integration)
    
    return integration

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

async def call_apideck_with_circuit_breaker(client: Apideck, service_id: str, operation: str) -> Any:
    """
    Executes an Apideck operation with circuit breaker protection and error handling.
    
    Checks the circuit breaker state before executing the requested operation. Validates the operation name, retrieves the corresponding handler, and executes it asynchronously. On failure or timeout, records the failure and raises an HTTPException with an appropriate status code. On success, records the success and returns the operation result.
    
    Args:
        service_id: The Apideck service identifier.
        operation: The name of the Apideck operation to execute.
    
    Returns:
        The result of the executed Apideck operation.
    
    Raises:
        HTTPException: If the circuit breaker is open, the operation is unsupported or not implemented, or if the Apideck API call fails.
    """
    if not await apideck_circuit_breaker.can_execute():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Apideck service temporarily unavailable (circuit breaker open)"
        )
    
    try:
        # Convert string to enum for safe lookup
        try:
            operation_enum = ApideckOperation(operation)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported operation: '{operation}'. Allowed: {[op.value for op in ApideckOperation]}",
            )

        # Look up operation handler from the mapping
        handler = OPERATION_HANDLERS.get(operation_enum)
        if not handler:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Operation '{operation}' is defined but not implemented.",
            )
        
        # Execute the operation using the appropriate handler
        result = await handler(client, service_id)
        
    except asyncio.TimeoutError:
        # Log with full traceback for better debugging
        logger.exception("Apideck API call timed out for operation: %s", operation)
        # Record failure only once before raising the exception
        await apideck_circuit_breaker.record_failure()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Upstream service timed out during '{operation}' operation."
        )
    except Exception as e:
        await apideck_circuit_breaker.record_failure()
        
        # Enhanced exception handling with structured logging for Apideck errors
        exception_type = type(e).__name__
        
        # Check for Apideck-specific error attributes for better observability
        if hasattr(e, 'status') and hasattr(e, 'body'):
            # This looks like an Apideck API exception
            status_code = getattr(e, 'status', 'Unknown')
            reason = getattr(e, 'reason', 'Unknown reason')
            body = getattr(e, 'body', {})
            headers = getattr(e, 'headers', {})
            
            logger.error(
                "Apideck API error for operation %s: Type=%s, Status=%s, Reason='%s', Body=%s, Headers=%s",
                operation, exception_type, status_code, reason, body, headers,
                exc_info=True
            )
        elif 'apideck' in exception_type.lower() or 'api' in exception_type.lower():
            # Likely an API-related exception even without status/body
            logger.error(
                "API exception for operation %s: Type=%s, Message='%s'",
                operation, exception_type, str(e),
                exc_info=True
            )
        else:
            # Generic exception
            logger.error("Unexpected error for operation %s: Type=%s, Message='%s'", operation, exception_type, str(e))
        
        # Surface a controlled error to the client
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream QuickBooks service failed"
        ) from e
    else:
        await apideck_circuit_breaker.record_success()
        return result

def normalize_qb_datetime(date_str: str | None) -> datetime:
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

async def resolve_tenant_and_lease_from_qb_object(session: AsyncSession, qb_object: Any) -> tuple[Optional[Tenant], Optional[Lease]]:
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

async def is_already_synced(session: AsyncSession, qb_id: str, model: Any) -> bool:
    """Checks if a QuickBooks entity with a given ID has already been synced."""
    query = select(model).where(col(model.quickbooks_id) == qb_id)
    result = await session.scalar(query)
    return result is not None

