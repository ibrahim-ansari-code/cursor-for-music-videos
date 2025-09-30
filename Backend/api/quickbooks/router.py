import asyncio
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from .intuit_client import get_intuit_client_for_user
from .services.sync_service import QuickBooksSyncService
from ...config import settings
from ...models.user import User
from ...models.enums import UserType
from ...models.accounting.common import IntegrationType, IntegrationStatus
from ...database import get_session
from ...utils.datetime_utils import create_audit_datetime
from ...utils.recaptcha import require_recaptcha

from .utils import (
    check_rate_limit, get_user_integration,
    RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_HOURS,
    validate_quickbooks_configuration, check_quickbooks_connection_health
)
from .services import QuickBooksService, QuickBooksAuthService
from .services.expense_service import ExpenseService
from .services.invoice_service import InvoiceService
from .services.payment_service import PaymentService

logger = logging.getLogger(__name__)
router = APIRouter()

# API Models
class QuickBooksConnectionResponse(BaseModel):
    """
    Response model for QuickBooks connection initiation.
    
    Contains the connection status, user message, and optional redirect URL
    to complete the QuickBooks OAuth flow with Intuit.
    """
    status: str
    message: str
    redirect_url: str | None = None

class QuickBooksStatusResponse(BaseModel):
    """
    Response model for QuickBooks integration status.
    
    Provides current connection state, integration type, connection timestamps,
    and the company metadata if available.
    """
    connected: bool
    integration_type: str | None = None
    connected_at: datetime | None = None
    last_sync_at: datetime | None = None
    consumer_id: str | None = None

class QuickBooksSyncResponse(BaseModel):
    """
    Response model for QuickBooks synchronization operations.
    
    Contains sync success status, descriptive message, count of synced items,
    and any errors encountered during the synchronization process.
    """
    success: bool
    message: str
    items_synced: int | None = None
    errors: list[str] | None = None

class QuickBooksDisconnectResponse(BaseModel):
    """
    Response model for QuickBooks disconnection operation.

    Contains success status and message indicating whether the QuickBooks
    integration was successfully disconnected from the user account.
    """
    success: bool
    message: str

class SyncItemResponse(BaseModel):
    """Response model for a single sync item in preview."""
    entity_type: str
    entity_id: str
    entity_name: str
    action: str
    details: dict
    warnings: list[str] = []

class SyncPreviewResponse(BaseModel):
    """Response model for sync preview."""
    items: list[SyncItemResponse]
    summary: dict[str, int]
    warnings: list[str] = []

class QuickBooksAccountResponse(BaseModel):
    """Response model for QuickBooks account."""
    id: str
    name: str
    account_type: str
    account_sub_type: str | None = None
    active: bool

# API Endpoints
@router.get("/connect", response_model=QuickBooksConnectionResponse)
async def connect_to_quickbooks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _recaptcha: None = Depends(require_recaptcha("quickbooks_connect"))
) -> QuickBooksConnectionResponse:
    """Initiate QuickBooks connection for authenticated user."""
    if not await check_rate_limit(str(current_user.id)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_HOURS} hour(s)."
        )

    try:
        auth_service = QuickBooksAuthService(current_user, session)
        authorize_url, _ = await auth_service.build_authorize_url()

        return QuickBooksConnectionResponse(
            status="redirect_required",
            message="Please complete the connection process with Intuit",
            redirect_url=authorize_url,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating QuickBooks connection URL for user %s: %s", current_user.id, e)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to initiate QuickBooks connection")

@router.get("/status", response_model=QuickBooksStatusResponse)
async def get_quickbooks_connection_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksStatusResponse:
    """Get QuickBooks integration status for authenticated user."""
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

        return QuickBooksStatusResponse(
            connected=integration.status == IntegrationStatus.CONNECTED,
            integration_type=integration.integration_type.value,
            connected_at=integration.connected_at,
            last_sync_at=integration.last_sync_at,
            consumer_id=None
        )

    except Exception as e:
        logger.error("Error checking QuickBooks status for user %s: %s", current_user.id, e)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to check QuickBooks status")


@router.get("/diagnostics")
async def get_quickbooks_diagnostics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get detailed QuickBooks diagnostics for troubleshooting Error 3100 and other issues."""
    try:
        # Get basic status first
        integration = await get_user_integration(current_user, session, IntegrationType.QUICKBOOKS)
        
        
        diagnostics: dict[str, Any] = {
            "connected": integration and integration.status == IntegrationStatus.CONNECTED,
            "environment": settings.INTUIT_ENV,
            "scopes_configured": settings.INTUIT_SCOPES,
            "has_offline_access": "offline_access" in settings.INTUIT_SCOPES,
            "redirect_uri": settings.INTUIT_REDIRECT_URI,
            "integration_exists": integration is not None
        }
        
        # If connected, try a simple API call to verify authorization
        if integration and integration.status == IntegrationStatus.CONNECTED:
            try:
                from .intuit_client import get_intuit_client_for_user
                client = await get_intuit_client_for_user(current_user.id, session)
                # Try to get company info as a test
                company_info = await client.get_company_info()
                diagnostics["api_test"] = {
                    "success": True,
                    "company_name": company_info.get("CompanyInfo", {}).get("CompanyName"),
                    "company_id": company_info.get("CompanyInfo", {}).get("Id")
                }
            except HTTPException as e:
                diagnostics["api_test"] = {
                    "success": False,
                    "error": str(e.detail),
                    "status_code": e.status_code,
                    "is_3100_error": "3100" in str(e.detail) or "authorization failed" in str(e.detail).lower()
                }
            except Exception as e:
                diagnostics["api_test"] = {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
        
        return diagnostics
        
    except Exception as e:
        logger.error(f"Error getting QuickBooks diagnostics for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get diagnostics: {str(e)}"
        )


@router.post("/disconnect", response_model=QuickBooksDisconnectResponse)
async def disconnect_from_quickbooks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksDisconnectResponse:
    """Disconnect QuickBooks integration for authenticated user."""
    try:
        auth_service = QuickBooksAuthService(current_user, session)
        result = await auth_service.disconnect_quickbooks()

        return QuickBooksDisconnectResponse(
            success=result["success"],
            message=result["message"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error disconnecting QuickBooks for user %s: %s", current_user.id, e)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to disconnect QuickBooks")

@router.get("/callback", response_model=dict)
async def quickbooks_oauth_callback(
    code: str,
    realmId: str,
    state: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> dict:
    """Handle OAuth callback from QuickBooks after user authorization."""
    try:
        auth_service = QuickBooksAuthService(current_user, session)
        result = await auth_service.exchange_code_for_tokens(code, realmId, state)

        return {
            "success": True,
            "message": "Successfully connected to QuickBooks",
            **result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in QuickBooks OAuth callback for user %s: %s", current_user.id, e)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to complete QuickBooks connection")


@router.post("/initial-sync", response_model=QuickBooksSyncResponse)
async def initial_quickbooks_sync(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksSyncResponse:
    """
    Performs an initial synchronization between the user's account and QuickBooks.

    This operation pulls and links customers, pushes any unlinked tenants, and imports all
    payments, invoices, and expenses from QuickBooks. Only available to landlords and admins.

    Returns:
        QuickBooksSyncResponse: Summary of the sync operation, including success status,
                               total items synced, and any errors encountered.
    """
    if current_user.user_type != UserType.LANDLORD and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only landlords can perform initial sync."
        )

    # Verify QuickBooks connection exists
    integration = await get_user_integration(current_user, session, IntegrationType.QUICKBOOKS)
    if not integration or integration.status != IntegrationStatus.CONNECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QuickBooks must be connected before performing initial sync"
        )

    try:
        # Use the new sync service for clean, organized sync operations
        sync_service = QuickBooksSyncService(current_user, session)
        result = await sync_service.perform_initial_sync()

        return QuickBooksSyncResponse(
            success=result["success"],
            message=result["message"],
            items_synced=result["items_synced"],
            errors=result.get("errors")
        )

    except Exception as e:
        logger.error("Error during initial sync for user %s: %s", current_user.id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete initial synchronization"
        )

@router.post("/sync/payments", response_model=QuickBooksSyncResponse)
async def sync_payments_bidirectional(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksSyncResponse:
    """
    Performs bidirectional payment synchronization between Brikli and QuickBooks.

    This operation:
    1. Pulls new/updated payments from QuickBooks into Brikli
    2. Pushes unsynced Brikli payments to QuickBooks

    Returns a summary with counts for both operations and any errors encountered.
    """

    if current_user.user_type != UserType.LANDLORD and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only landlords and admins can sync payments.")

    try:
        # Use the new sync service
        sync_service = QuickBooksSyncService(current_user, session)
        result = await sync_service.sync_payments()

        message = f"Bidirectional payment sync completed. Pulled {result.get('pulled_count', 0)}, pushed {result.get('pushed_count', 0)} payments."

        return QuickBooksSyncResponse(
            success=result["success"],
            message=message,
            items_synced=result["synced_count"],
            errors=result.get("errors")
        )

    except Exception as e:
        logger.error(f"Error during bidirectional payment sync for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete bidirectional payment sync"
        )

@router.post("/sync/invoices", response_model=QuickBooksSyncResponse)
async def sync_invoices_bidirectional(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksSyncResponse:
    """
    Performs bidirectional invoice synchronization between Brikli and QuickBooks.

    This operation:
    1. Pulls new/updated invoices from QuickBooks into Brikli
    2. Pushes unsynced Brikli invoices to QuickBooks

    Returns a summary with counts for both operations and any errors encountered.
    """

    if current_user.user_type != UserType.LANDLORD and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only landlords and admins can sync invoices.")

    try:
        # Use the new sync service
        sync_service = QuickBooksSyncService(current_user, session)
        result = await sync_service.sync_invoices()

        message = f"Bidirectional invoice sync completed. Pulled {result.get('pulled_count', 0)}, pushed {result.get('pushed_count', 0)} invoices."

        return QuickBooksSyncResponse(
            success=result["success"],
            message=message,
            items_synced=result["synced_count"],
            errors=result.get("errors")
        )

    except Exception as e:
        logger.error(f"Error during bidirectional invoice sync for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete bidirectional invoice sync"
        )

@router.post("/sync/expenses", response_model=QuickBooksSyncResponse)
async def sync_expenses_bidirectional(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksSyncResponse:
    """
    Performs bidirectional expense synchronization between Brikli and QuickBooks.

    This operation:
    1. Pulls new/updated expenses from QuickBooks into Brikli
    2. Pushes unsynced Brikli expenses to QuickBooks

    Returns a summary with counts for both operations and any errors encountered.
    """

    if current_user.user_type != UserType.LANDLORD and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only landlords and admins can sync expenses.")

    try:
        # Use the new sync service
        sync_service = QuickBooksSyncService(current_user, session)
        result = await sync_service.sync_expenses()

        message = f"Bidirectional expense sync completed. Pulled {result.get('pulled_count', 0)}, pushed {result.get('pushed_count', 0)} expenses."

        return QuickBooksSyncResponse(
            success=result["success"],
            message=message,
            items_synced=result["synced_count"],
            errors=result.get("errors")
        )

    except Exception as e:
        logger.error(f"Error during bidirectional expense sync for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete bidirectional expense sync"
        )


@router.post("/sync/all", response_model=QuickBooksSyncResponse)
async def sync_all_quickbooks_data(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksSyncResponse:
    """
    Performs a comprehensive sync of all QuickBooks data.

    This endpoint synchronizes all supported data types (customers, payments,
    invoices, expenses) between QuickBooks and Brikli in both directions.

    Returns:
        QuickBooksSyncResponse: Summary of the unified sync operation with total items synced and any errors.
    """

    if current_user.user_type != UserType.LANDLORD and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only landlords and admins can perform sync operations.")

    try:
        # Use the new sync service for comprehensive sync
        sync_service = QuickBooksSyncService(current_user, session)
        result = await sync_service.perform_sync_all()

        return QuickBooksSyncResponse(
            success=result["success"],
            message=result["message"],
            items_synced=result["items_synced"],
            errors=result.get("errors")
        )

    except Exception as e:
        logger.error(f"Error during unified sync for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete unified sync"
        )


@router.get("/sync/preview", response_model=SyncPreviewResponse)
async def preview_quickbooks_sync(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> SyncPreviewResponse:
    """
    Preview what would happen during a QuickBooks sync operation.

    This endpoint performs a dry-run of the sync process and returns
    a detailed preview of what items would be created, updated, or skipped.
    No actual changes are made to the database.

    Returns:
        SyncPreviewResponse: Detailed preview of sync actions
    """
    if current_user.user_type != UserType.LANDLORD and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only landlords and admins can preview sync operations."
        )

    try:
        # Get previews from all services
        expense_service = ExpenseService(current_user, session)
        invoice_service = InvoiceService(current_user, session)
        payment_service = PaymentService(current_user, session)

        # Run all previews
        expense_preview = await expense_service.preview_expenses()
        invoice_preview = await invoice_service.preview_invoices()
        payment_preview = await payment_service.preview_payments()

        # Combine all items
        all_items = (
            expense_preview.items +
            invoice_preview.items +
            payment_preview.items
        )

        # Combine summaries
        combined_summary = {
            "create": sum([
                expense_preview.summary.get("create", 0),
                invoice_preview.summary.get("create", 0),
                payment_preview.summary.get("create", 0)
            ]),
            "update": sum([
                expense_preview.summary.get("update", 0),
                invoice_preview.summary.get("update", 0),
                payment_preview.summary.get("update", 0)
            ]),
            "skip": sum([
                expense_preview.summary.get("skip", 0),
                invoice_preview.summary.get("skip", 0),
                payment_preview.summary.get("skip", 0)
            ]),
            "error": sum([
                expense_preview.summary.get("error", 0),
                invoice_preview.summary.get("error", 0),
                payment_preview.summary.get("error", 0)
            ]),
            "total": len(all_items)
        }

        # Combine warnings
        combined_warnings = (
            expense_preview.warnings +
            invoice_preview.warnings +
            payment_preview.warnings
        )

        # Convert preview to response model
        items = [
            SyncItemResponse(
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                entity_name=item.entity_name,
                action=item.action.value,
                details=item.details,
                warnings=item.warnings or []
            )
            for item in all_items
        ]

        return SyncPreviewResponse(
            items=items,
            summary=combined_summary,
            warnings=combined_warnings
        )

    except Exception as e:
        logger.error(f"Error during sync preview for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate sync preview"
        )


@router.get("/accounts", response_model=list[QuickBooksAccountResponse])
async def list_quickbooks_accounts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> list[QuickBooksAccountResponse]:
    """
    List all accounts from the connected QuickBooks company.

    Returns all chart of accounts entries that can be used for mapping
    categories and configuring default accounts.

    Returns:
        list[QuickBooksAccountResponse]: List of QuickBooks accounts
    """
    if current_user.user_type != UserType.LANDLORD and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only landlords and admins can access QuickBooks accounts."
        )

    try:
        # Verify QuickBooks connection
        integration = await get_user_integration(current_user, session, IntegrationType.QUICKBOOKS)
        if not integration or integration.status != IntegrationStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QuickBooks must be connected to list accounts"
            )

        # Get QuickBooks client
        client = await get_intuit_client_for_user(current_user.id, session)

        # Fetch accounts from QuickBooks
        accounts_response = await client.list_accounts(max_results=200)

        if not accounts_response or "QueryResponse" not in accounts_response:
            return []

        accounts = accounts_response["QueryResponse"].get("Account", [])

        # Convert to response models
        result = []
        for account in accounts:
            result.append(QuickBooksAccountResponse(
                id=account.get("Id", ""),
                name=account.get("Name", ""),
                account_type=account.get("AccountType", ""),
                account_sub_type=account.get("AccountSubType"),
                active=account.get("Active", True)
            ))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing QuickBooks accounts for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list QuickBooks accounts"
        )


class QuickBooksValidationResponse(BaseModel):
    """Response model for QuickBooks configuration validation."""
    is_valid: bool
    missing_config: list[str]
    warnings: list[str]
    account_info: dict
    item_info: dict
    company_info: dict | None = None


class QuickBooksHealthResponse(BaseModel):
    """Response model for QuickBooks connection health check."""
    is_healthy: bool
    status: str
    last_checked: str
    issues: list[str]
    metrics: dict
    recommendations: list[str]


@router.get("/validate", response_model=QuickBooksValidationResponse)
async def validate_quickbooks_configuration_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksValidationResponse:
    """
    Validates the QuickBooks integration configuration for the current user.

    Checks if all required components are properly configured:
    - Active QuickBooks connection
    - Default bank/credit card account for expenses
    - Default expense category account
    - Default service item for invoices

    Returns detailed validation results with suggestions for missing configuration.
    """
    if current_user.user_type != UserType.LANDLORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only landlords can validate QuickBooks configuration"
        )

    try:
        validation_result = await validate_quickbooks_configuration(current_user, session)

        return QuickBooksValidationResponse(
            is_valid=validation_result["is_valid"],
            missing_config=validation_result["missing_config"],
            warnings=validation_result["warnings"],
            account_info=validation_result["account_info"],
            item_info=validation_result["item_info"],
            company_info=validation_result.get("company_info")
        )

    except Exception as e:
        logger.error(f"Error validating QuickBooks configuration for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate QuickBooks configuration"
        )


@router.get("/health", response_model=QuickBooksHealthResponse)
async def check_quickbooks_health(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    deep_check: bool = False
) -> QuickBooksHealthResponse:
    """
    Check the health of the QuickBooks integration connection.

    Performs various health checks including configuration validation,
    error count monitoring, and optional API connectivity testing.

    Args:
        deep_check: Whether to perform API calls to verify connectivity (slower but more thorough)

    Returns:
        QuickBooksHealthResponse with health status, issues, and recommendations
    """
    if current_user.user_type != UserType.LANDLORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only landlords can check QuickBooks health"
        )

    try:
        health_status = await check_quickbooks_connection_health(
            current_user, session, perform_deep_check=deep_check
        )

        return QuickBooksHealthResponse(**health_status)

    except Exception as e:
        logger.error(f"Error checking QuickBooks health for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check QuickBooks health"
        )


# === Monitoring and Circuit Breaker Endpoints ===

class CircuitBreakerStatsResponse(BaseModel):
    """Response model for circuit breaker statistics."""
    circuit_breakers: dict[str, Any]
    global_stats: dict[str, Any]


class TransactionStatsResponse(BaseModel):
    """Response model for transaction coordinator statistics."""
    message: str
    note: str


@router.get("/monitoring/circuit-breakers", response_model=CircuitBreakerStatsResponse)
async def get_circuit_breaker_stats(
    current_user: User = Depends(get_current_user)
) -> CircuitBreakerStatsResponse:
    """
    Get circuit breaker statistics for monitoring.

    Returns current state and statistics for all QuickBooks circuit breakers.
    Useful for monitoring system health and failure patterns.
    """
    if current_user.user_type != UserType.LANDLORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only landlords can access monitoring endpoints"
        )

    try:
        from .circuit_breaker import get_all_circuit_breaker_stats

        stats = await get_all_circuit_breaker_stats()

        # Calculate global statistics
        global_stats = {
            "total_circuit_breakers": len(stats),
            "open_circuits": sum(1 for cb_stats in stats.values() if cb_stats["state"] == "open"),
            "half_open_circuits": sum(1 for cb_stats in stats.values() if cb_stats["state"] == "half_open"),
            "closed_circuits": sum(1 for cb_stats in stats.values() if cb_stats["state"] == "closed"),
            "total_requests": sum(cb_stats["total_requests"] for cb_stats in stats.values()),
            "total_failures": sum(cb_stats["total_failures"] for cb_stats in stats.values()),
            "average_failure_rate": sum(cb_stats["failure_rate"] for cb_stats in stats.values()) / len(stats) if stats else 0
        }

        return CircuitBreakerStatsResponse(
            circuit_breakers=stats,
            global_stats=global_stats
        )

    except Exception as e:
        logger.error(f"Error getting circuit breaker stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve circuit breaker statistics"
        )




@router.post("/monitoring/reset-circuit-breaker/{circuit_name}")
async def reset_circuit_breaker(
    circuit_name: str,
    current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    """
    Manually reset a specific circuit breaker to closed state.

    This is an admin function to recover from circuit breaker failures
    when the underlying issue has been resolved.
    """
    if current_user.user_type != UserType.LANDLORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only landlords can reset circuit breakers"
        )

    try:
        from .circuit_breaker import get_circuit_breaker

        circuit_breaker = await get_circuit_breaker(circuit_name)
        await circuit_breaker.reset()

        logger.info(f"Circuit breaker '{circuit_name}' manually reset by user {current_user.id}")

        return {
            "status": "success",
            "message": f"Circuit breaker '{circuit_name}' has been reset to closed state"
        }

    except Exception as e:
        logger.error(f"Error resetting circuit breaker '{circuit_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset circuit breaker '{circuit_name}'"
        )




@router.get("/monitoring/transactions", response_model=TransactionStatsResponse)
async def get_transaction_stats(
    current_user: User = Depends(get_current_user)
) -> TransactionStatsResponse:
    """
    Get transaction coordinator statistics.

    Note: Individual transaction statistics are logged but not persisted
    for performance reasons. This endpoint provides general information
    about the transaction coordinator system.
    """
    if current_user.user_type != UserType.LANDLORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only landlords can access monitoring endpoints"
        )

    return TransactionStatsResponse(
        message="Transaction coordinator monitoring is event-based",
        note="Check application logs and Sentry for detailed transaction statistics and failure analysis"
    )


