import logging
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlunparse
from typing import Any, Awaitable
from collections.abc import Callable
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import apideck_unify
from apideck_unify import Apideck
from apideck_unify.models import AccountingCompanyInfoOneResponse
from cachetools import TTLCache

# Note: Apideck exceptions will be caught by the general Exception handler
# with enhanced attribute checking for structured error details

from Backend.api.auth import get_current_user
from Backend.config import settings
from Backend.database import get_session
from Backend.models.user import User
from Backend.models.accounting.integration import Integration
from Backend.models.accounting.common import IntegrationStatus, IntegrationType
from Backend.utils.datetime_utils import create_audit_datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# === Configuration ===
APIDECK_SERVICE_ID = getattr(settings, 'APIDECK_SERVICE_ID', 'quickbooks')
RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW_HOURS = 1

# === Operation Handlers ===
class ApideckOperation(Enum):
    """Enum for supported Apideck operations"""
    COMPANY_INFO = "company_info"
    # Add more operations as needed
    # EXPENSES_CREATE = "expenses_create"
    # INVOICES_CREATE = "invoices_create"
    # CUSTOMERS_LIST = "customers_list"

async def _handle_company_info_operation(client: Apideck, service_id: str) -> AccountingCompanyInfoOneResponse:
    """Handler for company info operation"""
    return await asyncio.wait_for(
        asyncio.to_thread(
            client.accounting.company_info.get,
            service_id=service_id
        ),
        timeout=30.0
    )

# Operation mapping dictionary
OPERATION_HANDLERS: dict[str, Callable[..., Awaitable[Any]]] = {
    ApideckOperation.COMPANY_INFO.value: _handle_company_info_operation,
    # Add more handlers as needed
}

# === Rate Limiting ===
# TTL-based rate limiting (prevents memory leaks from inactive users)
# TODO: Implement Redis-based rate limiting for distributed deployments (see Post-Launch Epic)
user_request_cache: TTLCache[str, list[datetime]] = TTLCache(
    maxsize=10000,  # Maximum number of users to track
    ttl=RATE_LIMIT_WINDOW_HOURS * 3600  # TTL in seconds
)
rate_limit_lock = asyncio.Lock()

async def check_rate_limit(user_id: str) -> bool:
    """
    Check if user has exceeded rate limit for connection requests
    Uses TTL cache to automatically remove stale entries and prevent memory leaks.
    Note: This implementation is only suitable for single-process deployments.
    For distributed systems, implement Redis-based rate limiting.
    """
    async with rate_limit_lock:
        now = datetime.now(timezone.utc)
        
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
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()  # Protect shared state
    
    async def can_execute(self) -> bool:
        """Check if circuit allows execution"""
        async with self._lock:
            if self.state == "CLOSED":
                return True
            elif self.state == "OPEN":
                if (self.last_failure_time and 
                    (datetime.now(timezone.utc) - self.last_failure_time).total_seconds() > self.recovery_timeout):
                    self.state = "HALF_OPEN"
                    return True
                return False
            else:  # HALF_OPEN
                return True
    
    async def record_success(self) -> None:
        """Record successful call"""
        async with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"
    
    async def record_failure(self) -> None:
        """Record failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now(timezone.utc)
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"

# Global circuit breaker instance
apideck_circuit_breaker = SimpleCircuitBreaker()

# === Startup Validation ===
def validate_apideck_config() -> None:
    """Validate Apideck configuration at startup - fail fast if incomplete"""
    if not settings.APIDECK_API_KEY or not settings.APIDECK_APP_ID:
        raise ValueError(
            "Apideck configuration is incomplete. Both APIDECK_API_KEY and APIDECK_APP_ID "
            "environment variables must be set for QuickBooks integration to work."
        )
    logger.info("Apideck configuration validated successfully")

# Call validation at module import time - fail fast if incomplete
validate_apideck_config()

# === API Models for QuickBooks Integration ===

class QuickBooksConnectionResponse(BaseModel):
    status: str
    message: str
    redirect_url: str | None = None

class QuickBooksStatusResponse(BaseModel):
    connected: bool
    integration_type: str | None = None
    connected_at: datetime | None = None
    last_sync_at: datetime | None = None
    consumer_id: str | None = None

class QuickBooksSyncResponse(BaseModel):
    success: bool
    message: str
    items_synced: int | None = None
    errors: list[str] | None = None

class QuickBooksDisconnectResponse(BaseModel):
    success: bool
    message: str

# === Helper Functions ===

def get_apideck_client(consumer_id: str) -> Apideck:
    """Create an Apideck client instance for the given consumer"""
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
    """Get existing integration or create a new one"""
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
    """Get user's integration using clean ORM pattern"""
    return await session.scalar(
        select(Integration).where(
            Integration.user_id == user.id,
            Integration.integration_type == integration_type
        )
    )

async def call_apideck_with_circuit_breaker(client: Apideck, service_id: str, operation: str) -> Any:
    """Call Apideck API with circuit breaker protection"""
    if not await apideck_circuit_breaker.can_execute():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Apideck service temporarily unavailable (circuit breaker open)"
        )
    
    try:
        # Look up operation handler from the mapping
        handler = OPERATION_HANDLERS.get(operation)
        if not handler:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported operation '{operation}'. Allowed: {list(OPERATION_HANDLERS.keys())}",
            )
        
        # Execute the operation using the appropriate handler
        result = await handler(client, service_id)
        
    except asyncio.TimeoutError:
        await apideck_circuit_breaker.record_failure()
        logger.error("Apideck API call timed out for operation: %s", operation)
        raise
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

# === API Endpoints ===

@router.get("/connect", response_model=QuickBooksConnectionResponse)
async def connect_to_quickbooks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksConnectionResponse:
    """
    Initiates QuickBooks connection by generating Apideck Vault URL
    Rate limited to 5 requests per hour per user
    """
    # Check rate limit
    if not await check_rate_limit(str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} connection requests per {RATE_LIMIT_WINDOW_HOURS} hour(s)."
        )
    
    try:
        # Get or create integration record
        integration = await get_or_create_integration(current_user, session)
        
        # Build Apideck Vault URL safely with proper encoding
        vault_params = {
            'consumer_id': integration.apideck_consumer_id,
            'application_id': settings.APIDECK_APP_ID
        }
        vault_url = urlunparse((
            'https',  # scheme
            'vault.apideck.com',  # netloc
            '/vault/sessions',  # path
            '',  # params
            urlencode(vault_params),  # query
            ''  # fragment
        ))
        
        logger.info(f"Generated QuickBooks connection URL for user {current_user.id}")
        
        return QuickBooksConnectionResponse(
            status="redirect_required",
            message="Please complete the connection process through Apideck Vault",
            redirect_url=vault_url
        )
        
    except Exception as e:
        logger.error("Error generating QuickBooks connection URL for user %s: %s", current_user.id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to initiate QuickBooks connection"
        )

@router.get("/status", response_model=QuickBooksStatusResponse)
async def get_quickbooks_connection_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksStatusResponse:
    """
    Checks the current QuickBooks connection status via Apideck
    """
    try:
        integration = await get_user_integration(current_user, session, IntegrationType.QUICKBOOKS)
        
        if not integration:
            return QuickBooksStatusResponse(
                connected=False,
                integration_type=None,
                connected_at=None,
                last_sync_at=None,
                consumer_id=None
            )
        
        # Check connection status via Apideck
        try:
            if not integration.apideck_consumer_id:
                logger.warning(f"No consumer_id found for user {current_user.id}")
                integration.status = IntegrationStatus.ERROR
                integration.last_error = "No consumer ID found"
                integration.updated_at = create_audit_datetime()
                await session.commit()
                
                return QuickBooksStatusResponse(
                    connected=False,
                    integration_type=integration.integration_type.value,
                    connected_at=integration.connected_at,
                    last_sync_at=integration.last_sync_at,
                    consumer_id=integration.apideck_consumer_id
                )
            
            apideck_client = get_apideck_client(integration.apideck_consumer_id)
            
            # Try to get company info to verify connection with circuit breaker
            try:
                company_response = await call_apideck_with_circuit_breaker(
                    apideck_client, 
                    integration.apideck_service_id or APIDECK_SERVICE_ID,
                    "company_info"
                )
                
                # Update integration status to connected
                if integration.status != IntegrationStatus.CONNECTED:
                    integration.status = IntegrationStatus.CONNECTED
                    integration.connected_at = create_audit_datetime()
                    integration.updated_at = create_audit_datetime()
                    await session.commit()
                
                return QuickBooksStatusResponse(
                    connected=True,
                    integration_type=integration.integration_type.value,
                    connected_at=integration.connected_at,
                    last_sync_at=integration.last_sync_at,
                    consumer_id=integration.apideck_consumer_id
                )
            except asyncio.TimeoutError:
                logger.warning("Apideck API call timed out after 30 seconds for user %s", current_user.id)
                integration.status = IntegrationStatus.ERROR
                integration.last_error = "API call timed out after 30 seconds"
                integration.updated_at = create_audit_datetime()
                await session.commit()
            except HTTPException as http_e:
                # Circuit breaker or other HTTP errors
                integration.status = IntegrationStatus.ERROR
                integration.last_error = http_e.detail
                integration.updated_at = create_audit_datetime()
                await session.commit()
            except Exception as api_error:
                logger.warning("Apideck API call failed for user %s: %s", current_user.id, str(api_error))
                integration.status = IntegrationStatus.ERROR
                integration.last_error = f"API call failed: {str(api_error)}"
                integration.updated_at = create_audit_datetime()
                await session.commit()
                
        except Exception as apideck_error:
            logger.warning("Apideck connection check failed for user %s: %s", current_user.id, str(apideck_error))
            integration.status = IntegrationStatus.DISCONNECTED
            integration.last_error = str(apideck_error)
            integration.updated_at = create_audit_datetime()
            await session.commit()
        
        return QuickBooksStatusResponse(
            connected=False,
            integration_type=integration.integration_type.value if integration else None,
            connected_at=integration.connected_at if integration else None,
            last_sync_at=integration.last_sync_at if integration else None,
            consumer_id=integration.apideck_consumer_id if integration else None
        )
        
    except Exception as e:
        logger.error("Error checking QuickBooks connection status for user %s: %s", current_user.id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to check QuickBooks connection status"
        )

@router.post("/disconnect", response_model=QuickBooksDisconnectResponse)
async def disconnect_from_quickbooks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksDisconnectResponse:
    """
    Disconnects QuickBooks integration
    """
    try:
        # Clean ORM query
        integration = await get_user_integration(current_user, session, IntegrationType.QUICKBOOKS)
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No QuickBooks integration found"
            )
        
        # Update integration status
        integration.status = IntegrationStatus.DISCONNECTED
        integration.connected_at = None
        integration.last_sync_at = None
        integration.updated_at = create_audit_datetime()
        
        await session.commit()
        
        logger.info(f"QuickBooks disconnected for user {current_user.id}")
        
        return QuickBooksDisconnectResponse(
            success=True,
            message="QuickBooks integration disconnected successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error disconnecting QuickBooks for user %s: %s", current_user.id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect QuickBooks integration"
        )

# === Data Sync Functions ===

async def _sync_expense_to_quickbooks(user: User, session: AsyncSession, expense_data: dict[str, Any]) -> dict[str, Any]:
    """
    Internal function to sync an expense from our system to QuickBooks via Apideck
    """
    try:
        # Get existing integration - don't create a new one during sync attempts
        integration = await get_user_integration(user, session, IntegrationType.QUICKBOOKS)
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QuickBooks integration not found. Please connect to QuickBooks first."
            )
        
        if integration.status != IntegrationStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QuickBooks not connected"
            )
        
        if not integration.apideck_consumer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No consumer ID found for integration"
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

# Additional sync functions for invoices, payments, customers, etc. will be implemented similarly

# Placeholder for QBO API interaction functions via Apideck
async def _get_qbo_company_info_via_apideck(user: User, session: AsyncSession) -> None:
    """
    Internal function to fetch company info from QBO via Apideck.
    """
    # 1. Ensure user has an active Apideck session/connection for QuickBooks.
    # 2. Call Apideck's API to get company info (or equivalent).
    # Example: apideck_client.accounting.companies_one(app_id='quickbooks', consumer_id=user.apideck_consumer_id)
    #
    # try:
    #     # company_info = ... call to Apideck ...
    #     return {
    #         "company_name": company_info.name,
    #         # ... other relevant fields mapped from Apideck's response
    #     }
    # except Exception as e:
    #     logger.error(f"Failed to fetch QBO company info via Apideck for user {user.id}: {str(e)}", exc_info=True)
    #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch data from QuickBooks via Apideck.")
    raise NotImplementedError("QBO company-info sync not yet implemented")

async def _create_qbo_expense_via_apideck(user: User, session: AsyncSession, expense_data: dict[str, Any]) -> None:
    """
    Internal function to create an expense in QBO via Apideck.
    """
    # 1. Ensure user has an active Apideck session/connection for QuickBooks.
    # 2. Map expense_data from your system's format to Apideck's accounting API format for expenses.
    # 3. Call Apideck's API to create the expense.
    # Example: apideck_client.accounting.purchases_add(app_id='quickbooks', consumer_id=user.apideck_consumer_id, body={...mapped_expense_data...})
    pass

# More functions will be needed for syncing via Apideck:
# - Syncing Invoices
# - Syncing Payments (and applying them to Invoices or creating SalesReceipts)
# - Managing Chart of Accounts mapping
# - Managing Customer (Tenant) mapping
# - Managing Item (Product/Service) mapping
# - Handling Bank Deposits and reconciliation
# - etc. 