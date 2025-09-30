import json
import logging
from dataclasses import dataclass
import asyncio
from datetime import datetime, UTC, timedelta
from typing import Any, Dict, Optional, List

import aiohttp
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from Backend.config import settings
from Backend.models.accounting.integration import Integration, IntegrationType, IntegrationStatus
from Backend.models.accounting.quickbooks_integration import QuickBooksIntegration
from .intuit_oauth import refresh_access_token
from .crypto_utils import decrypt_token
from .session_manager import get_shared_session

logger = logging.getLogger(__name__)


@dataclass
class IntuitClient:
    realm_id: str
    access_token: str
    session: AsyncSession
    qbi: QuickBooksIntegration

    @property
    def base_url(self) -> str:
        if settings.INTUIT_ENV == "sandbox":
            return f"https://sandbox-quickbooks.api.intuit.com/v3/company/{self.realm_id}"
        else:
            return f"https://quickbooks.api.intuit.com/v3/company/{self.realm_id}"


    async def _ensure_token_valid(self) -> None:
        # Refresh a minute before expiry
        if self.qbi.access_token_expires_at <= datetime.now(UTC) + timedelta(seconds=60):
            self.qbi = await refresh_access_token(self.session, self.qbi)
            self.access_token = decrypt_token(self.qbi.access_token_encrypted)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        await self._ensure_token_valid()
        url = f"{self.base_url}{path}"
        qparams = {"minorversion": str(settings.QBO_MINOR_VERSION)}
        if params:
            qparams.update(params)

        async def do_http_request(current_token: str) -> tuple[int, str]:
            req_headers = {
                "Authorization": f"Bearer {current_token}",
                "Accept": "application/json",
            }
            if json_body is not None:
                req_headers["Content-Type"] = "application/json"
            if headers:
                req_headers.update(headers)

            # Use shared session pool to prevent connection pool exhaustion
            http = await get_shared_session()
            async with http.request(method.upper(), url, params=qparams, json=json_body, headers=req_headers) as resp:
                text = await resp.text()
                return resp.status, text

        # First attempt
        status_code, text = await do_http_request(self.access_token)

        # If unauthorized/forbidden, try a single transparent refresh + retry
        if status_code in (401, 403):
            try:
                self.qbi = await refresh_access_token(self.session, self.qbi)
                self.access_token = decrypt_token(self.qbi.access_token_encrypted)
                status_code, text = await do_http_request(self.access_token)
            except Exception as e:
                logger.error("Failed to refresh Intuit access token: %s", e, exc_info=True)
                # Re-raise as an HTTPException to stop execution and provide a clear error.
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="QuickBooks token refresh failed. Please reconnect your account.",
                ) from e

        # If throttled, wait briefly and retry once
        if status_code == 429:
            await asyncio.sleep(1.5)
            status_code, text = await do_http_request(self.access_token)

        if status_code >= 400:
            self._log_intuit_error(method, url, status_code, text)
            
            # Provide specific error message for Error 3100
            if status_code == 403:
                try:
                    error_data = json.loads(text) if text else {}
                    fault = error_data.get("Fault") or error_data.get("fault") or error_data.get("error", [])
                    if isinstance(fault, list) and fault and fault[0].get("code") == "3100":
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN, 
                            detail="QuickBooks authorization failed. Please reconnect your QuickBooks account. "
                                   "The OAuth scopes may have changed and require re-authorization."
                        )
                except json.JSONDecodeError:
                    pass
            
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Intuit API request failed")

        # Handle JSON decoding explicitly to avoid silent failures
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to decode JSON response from Intuit API: %s. Response text: %s", e, text[:500])
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid JSON response from Intuit API",
            ) from e

    def _log_intuit_error(self, method: str, url: str, status_code: int, body: str) -> None:
        """Parse and log Intuit error payloads for observability."""
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {"raw": body[:500] if body else ""}
        
        fault = None
        error_code = None
        error_message = None
        
        if isinstance(payload, dict):
            fault = payload.get("Fault") or payload.get("fault") or payload.get("error")
            
            # Extract error details for better diagnostics
            if isinstance(fault, list) and fault:
                error_info = fault[0]
                error_code = error_info.get("code")
                error_message = error_info.get("message")
            elif isinstance(fault, dict):
                error_code = fault.get("code")
                error_message = fault.get("message")
        
        # Special handling for Error 3100 (ApplicationAuthorizationFailed)
        if error_code == "3100":
            logger.error(
                "QuickBooks Error 3100 - ApplicationAuthorizationFailed: "
                "This typically means: "
                "1) Missing 'offline_access' scope in OAuth (most common), "
                "2) App lacks required permissions in QuickBooks, "
                "3) Environment mismatch (sandbox app accessing production or vice versa), "
                "4) OAuth authorization has been revoked. "
                "Error details: %s", error_message
            )
        
        logger.error("Intuit API error %s %s [%s]: %s", method, url, status_code, fault or payload)

    # Convenience helpers
    async def query(self, q: str) -> Dict[str, Any]:
        return await self.request("GET", "/query", params={"query": q})

    async def get_company_info(self) -> Dict[str, Any]:
        return await self.request("GET", f"/companyinfo/{self.realm_id}")

    # === Customer Operations ===
    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer in QuickBooks."""
        return await self.request("POST", "/customer", json_body=customer_data)

    async def update_customer(self, customer_id: str, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing customer in QuickBooks."""
        return await self.request("POST", f"/customer", json_body=customer_data)

    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get a specific customer by ID."""
        return await self.request("GET", f"/customer/{customer_id}")

    async def list_customers(self, start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """List customers with pagination."""
        query = f"SELECT * FROM Customer STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    async def query_customers(self, where_clause: str = "", start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """Query customers with custom WHERE clause."""
        query = f"SELECT * FROM Customer"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    # === Invoice Operations ===
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new invoice in QuickBooks."""
        return await self.request("POST", "/invoice", json_body=invoice_data)

    async def update_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing invoice in QuickBooks."""
        return await self.request("POST", "/invoice", json_body=invoice_data)

    async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Get a specific invoice by ID."""
        return await self.request("GET", f"/invoice/{invoice_id}")

    async def list_invoices(self, start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """List invoices with pagination."""
        query = f"SELECT * FROM Invoice STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    async def query_invoices(self, where_clause: str = "", start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """Query invoices with custom WHERE clause."""
        query = f"SELECT * FROM Invoice"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    async def void_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Void an invoice in QuickBooks."""
        invoice_data["sparse"] = True
        invoice_data["Void"] = True
        return await self.request("POST", "/invoice", json_body=invoice_data)

    async def send_invoice(self, invoice_id: str, send_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send an invoice via email."""
        return await self.request("POST", f"/invoice/{invoice_id}/send", json_body=send_data)

    # === Payment Operations ===
    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new payment in QuickBooks."""
        return await self.request("POST", "/payment", json_body=payment_data)

    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Get a specific payment by ID."""
        return await self.request("GET", f"/payment/{payment_id}")

    async def list_payments(self, start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """List payments with pagination."""
        query = f"SELECT * FROM Payment STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    async def query_payments(self, where_clause: str = "", start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """Query payments with custom WHERE clause."""
        query = f"SELECT * FROM Payment"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    # === Purchase/Expense Operations ===
    async def create_purchase(self, purchase_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new purchase/expense in QuickBooks."""
        return await self.request("POST", "/purchase", json_body=purchase_data)

    async def get_purchase(self, purchase_id: str) -> Dict[str, Any]:
        """Get a specific purchase by ID."""
        return await self.request("GET", f"/purchase/{purchase_id}")

    async def list_purchases(self, start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """List purchases with pagination."""
        query = f"SELECT * FROM Purchase STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    async def query_purchases(self, where_clause: str = "", start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """Query purchases with custom WHERE clause."""
        query = f"SELECT * FROM Purchase"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    # === Item Operations ===
    async def create_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new item (product/service) in QuickBooks."""
        return await self.request("POST", "/item", json_body=item_data)

    async def update_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing item in QuickBooks."""
        return await self.request("POST", "/item", json_body=item_data)

    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """Get a specific item by ID."""
        return await self.request("GET", f"/item/{item_id}")

    async def list_items(self, start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """List items with pagination."""
        query = f"SELECT * FROM Item STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    async def query_items(self, where_clause: str = "", start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """Query items with custom WHERE clause."""
        query = f"SELECT * FROM Item"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    # === Account Operations ===
    async def list_accounts(self, start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """List chart of accounts with pagination."""
        query = f"SELECT * FROM Account STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    async def query_accounts(self, where_clause: str = "", start_position: int = 1, max_results: int = 100) -> Dict[str, Any]:
        """Query accounts with custom WHERE clause."""
        query = f"SELECT * FROM Account"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return await self.query(query)

    async def get_account(self, account_id: str) -> Dict[str, Any]:
        """Get a specific account by ID."""
        return await self.request("GET", f"/account/{account_id}")

    # === Utility Methods ===
    async def batch_request(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute multiple operations in a single batch request."""
        batch_data = {
            "BatchItemRequest": operations
        }
        return await self.request("POST", "/batch", json_body=batch_data)

    def build_qb_object(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to build properly formatted QuickBooks entity objects."""
        return {
            entity_type: data
        }


async def get_intuit_client_for_user(user_id, session: AsyncSession) -> IntuitClient:
    integration = await session.scalar(
        select(Integration).where(
            Integration.user_id == user_id,
            Integration.integration_type == IntegrationType.QUICKBOOKS,
        )
    )
    if not integration or integration.status != IntegrationStatus.CONNECTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="QuickBooks is not connected.")

    qbi = await session.get(QuickBooksIntegration, integration.id)
    if not qbi:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="QuickBooks tokens are missing.")

    access_token = decrypt_token(qbi.access_token_encrypted)
    return IntuitClient(realm_id=qbi.realm_id, access_token=access_token, session=session, qbi=qbi)

