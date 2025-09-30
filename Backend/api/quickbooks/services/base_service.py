import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass
from enum import Enum

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException, status

from ....models.user import User
from ....models.accounting.integration import Integration, IntegrationType, IntegrationStatus
from ....utils.datetime_utils import create_audit_datetime
from ..intuit_client import get_intuit_client_for_user, IntuitClient
from ..circuit_breaker import get_circuit_breaker, CircuitBreakerConfig, CircuitBreakerError, CircuitBreaker

logger = logging.getLogger(__name__)


class SyncAction(str, Enum):
    """Types of actions that can be performed during sync."""
    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class SyncItem:
    """Represents an item to be synced with its details."""
    entity_type: str  # "tenant", "invoice", "payment", "expense"
    entity_id: str
    entity_name: str
    action: SyncAction
    details: Dict[str, Any]
    warnings: Optional[List[str]] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class SyncPreview:
    """Preview of what will happen during a sync operation."""
    items: List[SyncItem]
    summary: Dict[str, int]
    warnings: Optional[List[str]] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class BaseQuickBooksService:
    """
    Base service class for QuickBooks entity operations.

    Provides common functionality for all QuickBooks entity services including:
    - Integration validation
    - Client initialization
    - Retry mechanism
    - Error handling
    - Logging
    - Session-level caching
    """

    def __init__(self, user: User, session: AsyncSession, preview_mode: bool = False):
        self.user = user
        self.session = session
        self.preview_mode = preview_mode
        self.integration: Optional[Integration] = None
        self._client: Optional[IntuitClient] = None
        self._session_cache: Dict[str, Any] = {}  # In-memory cache for this sync session
        self._preview_items: List[SyncItem] = []  # Collect items for preview
        self._circuit_breaker: Optional[CircuitBreaker] = None  # Will be initialized lazily

    async def initialize(self) -> None:
        """Initialize service and verify QuickBooks connection."""
        self.integration = await self._get_user_integration()
        if not self.integration or self.integration.status != IntegrationStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QuickBooks integration not found or not connected"
            )
        self._client = await get_intuit_client_for_user(self.user.id, self.session)

        # Initialize circuit breaker for this service
        circuit_breaker_name = f"quickbooks-{self.__class__.__name__.lower()}"
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,      # Open after 5 failures
            recovery_timeout=60,      # Try recovery after 60 seconds
            half_open_max_calls=3,    # Test with max 3 calls
            success_threshold=2,      # Close after 2 successes
            timeout_threshold=30.0,   # 30 second timeout
            failure_rate_threshold=0.5  # 50% failure rate
        )
        self._circuit_breaker = await get_circuit_breaker(circuit_breaker_name, circuit_config)

    async def _get_user_integration(self) -> Optional[Integration]:
        """Get user's QuickBooks integration."""
        return await self.session.scalar(
            select(Integration).where(
                Integration.user_id == self.user.id,
                Integration.integration_type == IntegrationType.QUICKBOOKS
            )
        )

    async def _execute_with_circuit_breaker(self, operation: Callable, operation_name: str) -> Any:
        """
        Execute operation with circuit breaker protection.

        Args:
            operation: Async function to execute
            operation_name: Name of operation for logging

        Returns:
            Result of the operation

        Raises:
            CircuitBreakerError: If circuit breaker is open
            Exception: Original exception if operation fails
        """
        if not self._circuit_breaker:
            # Fallback to direct execution if circuit breaker not initialized
            logger.warning("Circuit breaker not initialized, executing operation directly: %s", operation_name)
            return await operation()

        try:
            return await self._circuit_breaker.call(operation)
        except CircuitBreakerError as e:
            # Circuit breaker is open - log and re-raise
            logger.error("QuickBooks %s blocked by circuit breaker: %s", operation_name, e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"QuickBooks service temporarily unavailable. Please try again later."
            ) from e

    async def _retry_operation(self, operation: Callable, operation_name: str, max_retries: int = 3) -> Any:
        """
        Retry mechanism for QuickBooks operations with circuit breaker protection.

        Args:
            operation: Async function to retry
            operation_name: Name of operation for logging
            max_retries: Maximum number of retry attempts

        Returns:
            Result of the operation

        Raises:
            Exception: The last exception if all retries fail
        """
        last_exception: Optional[Union[HTTPException, aiohttp.ClientError, asyncio.TimeoutError]] = None

        for attempt in range(max_retries + 1):
            try:
                # Execute with circuit breaker protection
                return await self._execute_with_circuit_breaker(operation, operation_name)
            except HTTPException as e:
                # Don't retry HTTP exceptions from circuit breaker or auth errors
                if e.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
                    # Circuit breaker is open
                    raise
                elif e.status_code in [401, 403]:
                    # Auth errors - don't retry
                    logger.error(f"QuickBooks {operation_name} failed with auth error: {e}")
                    raise
                else:
                    # Other HTTP errors - retry
                    last_exception = e
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
            except Exception as e:
                # Don't retry on unexpected errors
                logger.error(f"QuickBooks {operation_name} failed with non-retryable error: {e}")
                raise

            # Retry logic
            if attempt < max_retries:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"QuickBooks {operation_name} failed (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {wait_time}s: {last_exception}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"QuickBooks {operation_name} failed after {max_retries + 1} attempts: {last_exception}")

        if last_exception:
            raise last_exception
        raise RuntimeError(f"QuickBooks {operation_name} failed with unknown error")

    def _log_operation(self, operation: str, level: str = "info", **context) -> None:
        """Log QuickBooks operation with structured context."""
        log_context = {
            "operation": operation,
            "user_id": str(self.user.id),
            "level": level,
            **context
        }

        if level == "error":
            logger.error(f"QuickBooks operation failed: {operation}", extra=log_context)
        elif level == "warning":
            logger.warning(f"QuickBooks operation completed with warnings: {operation}", extra=log_context)
        else:
            logger.info(f"QuickBooks operation completed: {operation}", extra=log_context)

    async def _update_integration_sync_time(self) -> None:
        """Update integration's last sync time."""
        if self.integration:
            self.integration.last_sync_at = create_audit_datetime()
            await self.session.commit()

    async def _get_cached_metadata(self, key: str, default=None) -> Any:
        """Get cached value from integration metadata."""
        if self.integration and self.integration.connection_metadata:
            return self.integration.connection_metadata.get(key, default)
        return default

    async def _cache_metadata(self, key: str, value: Any) -> None:
        """Cache value in integration metadata."""
        if self.integration:
            metadata = self.integration.connection_metadata or {}
            metadata[key] = value
            self.integration.connection_metadata = metadata
            self.session.add(self.integration)
            await self.session.commit()

    @property
    def client(self):
        """Get the QuickBooks client (must call initialize() first)."""
        if self._client is None:
            raise RuntimeError("Service not initialized. Call initialize() first.")
        return self._client

    def _create_sync_result(self, synced_count: int = 0, errors: Optional[list] = None, **kwargs) -> Dict[str, Any]:
        """Create standardized sync result format."""
        errors = errors or []

        return {
            "success": len(errors) == 0,
            "synced_count": synced_count,
            "errors": errors if errors else None,
            **kwargs
        }

    def _get_session_cache(self, key: str, default=None) -> Any:
        """Get value from session cache."""
        return self._session_cache.get(key, default)

    def _set_session_cache(self, key: str, value: Any) -> None:
        """Set value in session cache."""
        self._session_cache[key] = value

    async def _get_or_cache_quickbooks_data(self, cache_key: str, fetch_func: Callable) -> Any:
        """Get data from session cache or fetch and cache it."""
        cached_data = self._get_session_cache(cache_key)
        if cached_data is not None:
            return cached_data

        # Fetch data and cache it
        data = await fetch_func()
        self._set_session_cache(cache_key, data)
        return data

    async def _batch_create_with_errors(self, entities: list, create_func: Callable, entity_name: str) -> Dict[str, Any]:
        """
        Create entities in batches with error aggregation.

        Returns dict with created_count and errors list.
        """
        created_count = 0
        errors = []

        for entity in entities:
            try:
                result = await create_func(entity)
                if result:
                    created_count += 1
                else:
                    errors.append(f"Failed to create {entity_name}")
            except Exception as e:
                errors.append(f"Error creating {entity_name}: {str(e)}")
                logger.error(f"Error creating {entity_name}: {e}", exc_info=True)

        return {"created_count": created_count, "errors": errors}

    def _add_preview_item(self, entity_type: str, entity_id: str, entity_name: str,
                         action: SyncAction, details: Dict[str, Any], warnings: Optional[List[str]] = None) -> None:
        """Add an item to the preview collection."""
        if self.preview_mode:
            item = SyncItem(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                action=action,
                details=details,
                warnings=warnings or []
            )
            self._preview_items.append(item)

    def _generate_preview(self) -> SyncPreview:
        """Generate a sync preview from collected items."""
        summary = {
            "create": sum(1 for item in self._preview_items if item.action == SyncAction.CREATE),
            "update": sum(1 for item in self._preview_items if item.action == SyncAction.UPDATE),
            "skip": sum(1 for item in self._preview_items if item.action == SyncAction.SKIP),
            "error": sum(1 for item in self._preview_items if item.action == SyncAction.ERROR),
            "total": len(self._preview_items)
        }

        global_warnings = []
        warning_count = sum(len(item.warnings or []) for item in self._preview_items)
        if warning_count > 0:
            global_warnings.append(f"{warning_count} items have warnings that require attention")

        return SyncPreview(
            items=self._preview_items,
            summary=summary,
            warnings=global_warnings
        )

    def _should_execute_action(self) -> bool:
        """Check if actions should be executed (not in preview mode)."""
        return not self.preview_mode