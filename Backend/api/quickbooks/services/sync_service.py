import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime
from .quickbooks_service import QuickBooksService

logger = logging.getLogger(__name__)


class QuickBooksSyncService:
    """
    Simplified service for managing QuickBooks synchronization operations.

    This service acts as a thin wrapper around the main QuickBooksService,
    providing high-level sync operations with simplified error handling.
    """

    def __init__(self, user: User, session: AsyncSession):
        self.user = user
        self.session = session
        self.qb_service = QuickBooksService(user, session)

    async def sync_customers(self) -> Dict[str, Any]:
        """Synchronize customers between QuickBooks and Brikli."""
        return await self.qb_service.sync_customers()

    async def sync_payments(self) -> Dict[str, Any]:
        """Perform bidirectional payment synchronization."""
        return await self.qb_service.sync_payments()

    async def sync_invoices(self) -> Dict[str, Any]:
        """Perform bidirectional invoice synchronization."""
        return await self.qb_service.sync_invoices()

    async def sync_expenses(self) -> Dict[str, Any]:
        """Perform bidirectional expense synchronization."""
        return await self.qb_service.sync_expenses()

    async def perform_initial_sync(self) -> Dict[str, Any]:
        """Perform comprehensive initial synchronization of all data types."""
        return await self.qb_service.perform_sync_all()

    async def perform_sync_all(self) -> Dict[str, Any]:
        """Perform comprehensive synchronization of all data types."""
        return await self.qb_service.perform_sync_all()