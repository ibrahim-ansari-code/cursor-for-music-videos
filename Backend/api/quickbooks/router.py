import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.models.accounting.common import IntegrationType, IntegrationStatus
from Backend.database import get_session
from Backend.utils.datetime_utils import create_audit_datetime
from Backend.utils.recaptcha import require_recaptcha

from .utils import (
    check_rate_limit, get_or_create_integration, get_user_integration, 
    call_apideck_with_circuit_breaker, APIDECK_SERVICE_ID, RATE_LIMIT_REQUESTS, 
    RATE_LIMIT_WINDOW_HOURS, get_apideck_client
)
from .customers import _pull_and_link_customers, _push_unlinked_tenants
from .payments import _pull_payments_from_quickbooks
from .invoices import _pull_invoices_from_quickbooks
from .expenses import _pull_expenses_from_quickbooks

logger = logging.getLogger(__name__)
router = APIRouter()

# API Models
class QuickBooksConnectionResponse(BaseModel):
    """
    Response model for QuickBooks connection initiation.
    
    Contains the connection status, user message, and optional redirect URL
    to complete the QuickBooks OAuth flow through Apideck Vault.
    """
    status: str
    message: str
    redirect_url: str | None = None

class QuickBooksStatusResponse(BaseModel):
    """
    Response model for QuickBooks integration status.
    
    Provides current connection state, integration type, connection timestamps,
    and the Apideck consumer ID used for API calls.
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

# API Endpoints
@router.get("/connect", response_model=QuickBooksConnectionResponse)
async def connect_to_quickbooks(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _recaptcha: None = Depends(require_recaptcha("quickbooks_connect"))
) -> QuickBooksConnectionResponse:
    """
    Initiates the QuickBooks connection process for the authenticated user.
    
    Checks the user's rate limit, retrieves or creates a QuickBooks integration record, and generates a secure Apideck Vault session URL for completing the connection. Returns a response indicating that user redirection is required to complete the QuickBooks integration.

    Security:
    - Requires reCAPTCHA v3 headers on the request:
      - X-Recaptcha-Token: token from grecaptcha.execute('quickbooks_connect')
      - X-Recaptcha-Action: quickbooks_connect
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
        
        if not integration.apideck_consumer_id:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Integration is missing a consumer ID."
            )

        # The redirect URI should point back to the integrations page on the frontend
        redirect_uri = str(request.url.replace(path="/integrations", query=""))
        
        # Use the Apideck SDK to create a Vault session
        apideck_client = get_apideck_client(integration.apideck_consumer_id)
        
        # This call must be in a thread because the underlying SDK library is synchronous
        session_response = await asyncio.to_thread(
            apideck_client.vault.sessions.create,
            session={"redirect_uri": redirect_uri}
        )

        # The response object contains the session data
        if not session_response or not session_response.create_session_response or not session_response.create_session_response.data or not session_response.create_session_response.data.session_uri:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create Apideck Vault session."
            )
        
        redirect_url = session_response.create_session_response.data.session_uri
        
        logger.info(f"Generated QuickBooks Vault session URL for user {current_user.id}")
        
        return QuickBooksConnectionResponse(
            status="redirect_required",
            message="Please complete the connection process through Apideck Vault",
            redirect_url=redirect_url
        )
        
    except (HTTPException, ConnectionError, TimeoutError) as e:
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
    Retrieves the QuickBooks integration status for the authenticated user.
    
    Checks the user's integration record and verifies the connection by querying Apideck for company information. Updates and returns the current connection status, connection timestamps, and consumer ID. If no integration exists or the connection cannot be verified, returns a disconnected status.
     
    Returns:
        QuickBooksStatusResponse: The current QuickBooks connection status and related metadata.
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
            company_response = await call_apideck_with_circuit_breaker(
                apideck_client, 
                integration.apideck_service_id or APIDECK_SERVICE_ID,
                "company_info"
            )
            
            # Always update last_sync_at on successful ping
            integration.last_sync_at = create_audit_datetime()
            
            # Update integration status to connected if not already
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
            logger.warning("Apideck API call timed out for user %s. Setting integration status to ERROR.", current_user.id)
            integration.status = IntegrationStatus.ERROR
            integration.last_error = "API call timed out"
            integration.updated_at = create_audit_datetime()
            await session.commit()
            
            # Move HTTPException outside the except block to avoid masking commit errors
            timeout_exception = HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Connection to QuickBooks timed out. Please try again later."
            )
            raise timeout_exception
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
    Disconnects the authenticated user's QuickBooks integration.
    
    If a QuickBooks integration exists for the user, marks it as disconnected and clears connection timestamps. Returns a success response. Raises a 404 error if no integration is found, or a 500 error on unexpected failure.
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

@router.post("/initial-sync", response_model=QuickBooksSyncResponse)
async def initial_quickbooks_sync(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksSyncResponse:
    """
    Performs an initial synchronization between the user's account and QuickBooks.
    
    This operation pulls and links customers, pushes any unlinked tenants, and imports all payments, invoices, and expenses from QuickBooks. Only available to landlords and admins.
    
    Returns:
        QuickBooksSyncResponse: Summary of the sync operation, including success status, total items synced, and any errors encountered.
    """

    if current_user.user_type != UserType.LANDLORD and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only landlords can perform initial sync.")

    all_errors = []
    total_synced = 0

    # Step 1: Pull and link customers
    customer_pull_result = await _pull_and_link_customers(current_user, session)
    total_synced += customer_pull_result.get("linked", 0) + customer_pull_result.get("created", 0)
    all_errors.extend(customer_pull_result.get("errors", []))

    # Step 2: Push any remaining unlinked tenants
    tenant_push_result = await _push_unlinked_tenants(current_user, session)
    total_synced += tenant_push_result.get("created", 0)
    all_errors.extend(tenant_push_result.get("errors", []))
    
    # Step 3: Pull financial records
    payments_result = await _pull_payments_from_quickbooks(current_user, session)
    total_synced += payments_result.get("synced_count", 0)
    all_errors.extend(payments_result.get("errors", []))
    
    invoices_result = await _pull_invoices_from_quickbooks(current_user, session)
    total_synced += invoices_result.get("synced_count", 0)
    all_errors.extend(invoices_result.get("errors", []))
    
    expenses_result = await _pull_expenses_from_quickbooks(current_user, session)
    total_synced += expenses_result.get("synced_count", 0)
    all_errors.extend(expenses_result.get("errors", []))

    return QuickBooksSyncResponse(
        success=len(all_errors) == 0,
        message=f"Initial sync completed. Synced {total_synced} items with {len(all_errors)} errors.",
        items_synced=total_synced,
        errors=all_errors if all_errors else None
    )

@router.post("/sync/payments", response_model=QuickBooksSyncResponse)
async def sync_payments_from_quickbooks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksSyncResponse:
    """
    Synchronizes recent payments from QuickBooks to Brikli.
    
    Returns:
        QuickBooksSyncResponse: Contains the success status, number of payments synced, and any errors encountered during synchronization.
    """
    
    if current_user.user_type != UserType.LANDLORD and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only landlords and admins can sync payments.")

    result = await _pull_payments_from_quickbooks(current_user, session)
    return QuickBooksSyncResponse(
        success=len(result['errors']) == 0,
        message=f"Successfully synced {result['synced_count']} new payments from QuickBooks.",
        items_synced=result['synced_count'],
        errors=result['errors'] if result['errors'] else None
    )

@router.post("/sync/invoices", response_model=QuickBooksSyncResponse)
async def sync_invoices_from_quickbooks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksSyncResponse:
    """
    Synchronizes recent invoices from QuickBooks to Brikli.
    
    Returns:
        QuickBooksSyncResponse: Contains the success status, number of invoices synced, and any errors encountered during synchronization.
    """
    
    if current_user.user_type != UserType.LANDLORD and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only landlords and admins can sync invoices.")

    result = await _pull_invoices_from_quickbooks(current_user, session)
    return QuickBooksSyncResponse(
        success=len(result['errors']) == 0,
        message=f"Successfully synced {result['synced_count']} new invoices from QuickBooks.",
        items_synced=result['synced_count'],
        errors=result['errors'] if result['errors'] else None
    )

@router.post("/sync/expenses", response_model=QuickBooksSyncResponse)
async def sync_expenses_from_quickbooks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> QuickBooksSyncResponse:
    """
    Synchronizes recent expenses from QuickBooks to the application.
    
    Retrieves recent expense records from QuickBooks for the authenticated user and syncs them to the application's database. Returns a summary of the synchronization result, including the number of expenses synced and any errors encountered.
    """
    
    if current_user.user_type != UserType.LANDLORD and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only landlords and admins can sync expenses.")

    result = await _pull_expenses_from_quickbooks(current_user, session)
    return QuickBooksSyncResponse(
        success=len(result['errors']) == 0,
        message=f"Successfully synced {result['synced_count']} new expenses from QuickBooks.",
        items_synced=result['synced_count'],
        errors=result['errors'] if result['errors'] else None
    )
