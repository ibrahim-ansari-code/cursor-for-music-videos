import base64
import secrets
import re
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, Tuple, Dict, Any

import aiohttp
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import cast

from Backend.config import settings
from Backend.models.user import User
from Backend.models.accounting.integration import Integration, IntegrationStatus, IntegrationType
from Backend.models.accounting.quickbooks_integration import QuickBooksIntegration
from Backend.utils.datetime_utils import create_audit_datetime
from ..crypto_utils import encrypt_token, decrypt_token
from ..session_manager import get_shared_session

logger = logging.getLogger(__name__)


class QuickBooksAuthService:
    """Consolidated service for QuickBooks OAuth and authentication operations."""

    def __init__(self, user: User, session: AsyncSession):
        self.user = user
        self.session = session


    @staticmethod
    def _b64_basic_auth(client_id: str, client_secret: str) -> str:
        """Create basic auth header."""
        raw = f"{client_id}:{client_secret}".encode("utf-8")
        return base64.b64encode(raw).decode("utf-8")

    @staticmethod
    def sanitize_error(error_msg: str) -> str:
        """Sanitize error messages for safe user display."""
        if not error_msg:
            return "QuickBooks operation failed"

        # Single regex for all sensitive patterns
        error_msg = re.sub(r'(token|key|secret|password)[\s:=]*\S+', '[REDACTED]', error_msg, flags=re.I)
        error_msg = re.sub(r'\S+@\S+', '[EMAIL]', error_msg)
        error_msg = re.sub(r'/Users/\S+|C:\\Users\\\S+', '[PATH]', error_msg)

        return error_msg[:300].strip() or "QuickBooks operation failed"

    async def get_or_create_integration(self) -> Integration:
        """Get or create QuickBooks integration for user."""
        integration = await self.session.scalar(
            select(Integration).where(
                Integration.user_id == self.user.id,
                Integration.integration_type == IntegrationType.QUICKBOOKS,
            )
        )
        if not integration:
            integration = Integration(
                user_id=self.user.id,
                integration_type=IntegrationType.QUICKBOOKS,
                status=IntegrationStatus.DISCONNECTED,
            )
            self.session.add(integration)
            await self.session.commit()
        return integration

    async def build_authorize_url(self) -> Tuple[str, str]:
        """Generate OAuth authorization URL with state."""
        integration = await self.get_or_create_integration()

        # Generate and save OAuth state
        state = secrets.token_urlsafe(32)
        state_expires = datetime.now(UTC) + timedelta(minutes=settings.INTUIT_STATE_TTL_MINUTES)

        metadata = integration.connection_metadata or {}
        if integration.status == IntegrationStatus.DISCONNECTED:
            # Clear old QB data
            for key in ["realm_id", "company_id", "company_name"]:
                metadata.pop(key, None)

        # Use the same keys as the original implementation
        metadata.update({
            "intuit_oauth_state": state,
            "intuit_oauth_state_set_at": state_expires.isoformat()
        })

        integration.connection_metadata = metadata
        integration.updated_at = create_audit_datetime()

        # Force SQLAlchemy to detect the change
        from sqlalchemy.orm import attributes
        attributes.flag_modified(integration, 'connection_metadata')

        await self.session.commit()

        # Verify state was saved
        await self.session.refresh(integration)
        saved_metadata = integration.connection_metadata or {}
        saved_state = saved_metadata.get("intuit_oauth_state")

        logger.info("OAuth state saved for user %s: state=%s, saved_state=%s",
                   self.user.id, state[:10] + "...", saved_state[:10] + "..." if saved_state else None)

        # Build authorization URL
        from urllib.parse import urlencode, quote

        # Log scope configuration for debugging
        logger.info("QuickBooks OAuth URL generation - Scope: '%s', Environment: %s",
                   settings.INTUIT_SCOPES, settings.INTUIT_ENV)

        query = urlencode({
            "client_id": settings.INTUIT_CLIENT_ID,
            "redirect_uri": settings.INTUIT_REDIRECT_URI,
            "response_type": "code",
            "scope": settings.INTUIT_SCOPES,  # urlencode will properly encode spaces as %20
            "state": state,
        }, quote_via=quote)

        auth_url = f"{settings.INTUIT_AUTH_URL}?{query}"
        logger.info("Generated QuickBooks OAuth URL (scope portion): ...scope=%s...",
                   query.split("scope=")[1].split("&")[0] if "scope=" in query else "NOT_FOUND")

        return auth_url, state

    async def exchange_code_for_tokens(self, code: str, realm_id: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for access/refresh tokens."""
        integration = await self.get_or_create_integration()

        # Refresh to get latest metadata from database
        await self.session.refresh(integration)

        # Validate OAuth state
        metadata = integration.connection_metadata or {}
        stored_state = metadata.get("intuit_oauth_state")
        state_expires_str = metadata.get("intuit_oauth_state_set_at")

        logger.info("OAuth state validation for user %s: provided=%s, stored=%s, metadata_keys=%s",
                   self.user.id,
                   state[:10] + "..." if state else None,
                   stored_state[:10] + "..." if stored_state else None,
                   list(metadata.keys()))

        if not stored_state:
            logger.error("No stored OAuth state found for user %s", self.user.id)
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No OAuth state found in session")

        if stored_state != state:
            logger.error("OAuth state mismatch for user %s: provided=%s, stored=%s",
                        self.user.id, state[:10] + "...", stored_state[:10] + "...")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OAuth state")

        if state_expires_str:
            try:
                state_expires = datetime.fromisoformat(state_expires_str)
                if datetime.now(UTC) > state_expires:
                    logger.error("OAuth state expired for user %s", self.user.id)
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Expired OAuth state")
            except ValueError:
                logger.error("Invalid OAuth state timestamp for user %s: %s", self.user.id, state_expires_str)
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OAuth state timestamp")

        # Exchange code for tokens
        token_response = await self._request_tokens(code)

        # Create/update QuickBooks integration record
        if integration.id is None:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Integration ID missing after commit")
        qbi = await self._upsert_quickbooks_details(
            integration.id,
            realm_id,
            token_response
        )

        # Update integration status
        integration.status = IntegrationStatus.CONNECTED
        integration.connected_at = create_audit_datetime()

        # Clear OAuth state and store company info
        metadata.pop("intuit_oauth_state", None)
        metadata.pop("intuit_oauth_state_set_at", None)
        metadata["realm_id"] = realm_id

        # Try to fetch company info
        try:
            company_info = await self._fetch_company_info(qbi, realm_id)
            if company_info:
                metadata.update(company_info)
        except Exception as e:
            logger.warning(f"Failed to fetch company info: {e}")

        integration.connection_metadata = metadata
        await self.session.commit()

        return {
            "realm_id": realm_id,
            "company_name": metadata.get("company_name"),
            "connected_at": integration.connected_at.isoformat() if integration.connected_at else None
        }

    async def disconnect_quickbooks(self) -> Dict[str, Any]:
        """Disconnect QuickBooks integration."""
        integration = await self.session.scalar(
            select(Integration).where(
                Integration.user_id == self.user.id,
                Integration.integration_type == IntegrationType.QUICKBOOKS,
            )
        )

        if not integration:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No QuickBooks integration found")

        # Revoke token (best effort)
        qbi = await self.session.get(QuickBooksIntegration, integration.id)
        if qbi and qbi.refresh_token_encrypted:
            await self._revoke_token_safe(qbi.refresh_token_encrypted)
            await self.session.delete(qbi)

        # Update integration
        integration.status = IntegrationStatus.DISCONNECTED
        integration.connected_at = None
        integration.last_sync_at = None
        integration.updated_at = create_audit_datetime()

        await self.session.commit()

        return {
            "success": True,
            "message": "QuickBooks integration disconnected successfully"
        }

    async def _request_tokens(self, code: str) -> Dict[str, Any]:
        """Make token exchange request to Intuit."""
        basic_auth = self._b64_basic_auth(settings.INTUIT_CLIENT_ID, settings.INTUIT_CLIENT_SECRET)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        from urllib.parse import urlencode
        data = urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.INTUIT_REDIRECT_URI,
        })

        from ..intuit_client import IntuitClient
        
        logger.info("Making token exchange request to %s", settings.INTUIT_TOKEN_URL)

        try:
            # Use shared session pool with SSL context for development
            client = await get_shared_session()
            async with client.post(
                    settings.INTUIT_TOKEN_URL,
                    data=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status >= 400:
                        body = await resp.text()
                        logger.error("Token exchange failed with status %d: %s", resp.status, body)
                        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Token exchange failed: {resp.status}")

                    return await resp.json()

        except aiohttp.ClientSSLError as e:
            logger.error("SSL certificate error during token exchange: %s", e)
            if "certificate verify failed" in str(e).lower():
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    "SSL certificate verification failed when connecting to QuickBooks. "
                    "This may be a temporary issue. Please try again in a few moments."
                )
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"SSL connection error: {e}")

        except aiohttp.ClientConnectorError as e:
            logger.error("Connection error during token exchange: %s", e)
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Could not connect to QuickBooks OAuth service. Please try again later."
            )

        except aiohttp.ClientError as e:
            logger.error("HTTP client error during token exchange: %s", e)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Connection error: {e}")

        except Exception as e:
            logger.error("Unexpected error during token exchange: %s", e, exc_info=True)
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "An unexpected error occurred during QuickBooks authentication"
            )

    async def _upsert_quickbooks_details(self, integration_id: int, realm_id: str, token_response: Dict[str, Any]) -> QuickBooksIntegration:
        """Create or update QuickBooks integration details."""
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = int(token_response.get("expires_in", 3600))
        refresh_expires_in = token_response.get("x_refresh_token_expires_in")

        if not access_token or not refresh_token:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Invalid token response")

        access_expiry = datetime.now(UTC) + timedelta(seconds=expires_in)
        refresh_expiry = (
            datetime.now(UTC) + timedelta(seconds=int(refresh_expires_in))
            if refresh_expires_in else None
        )

        qbi = await self.session.get(QuickBooksIntegration, integration_id)
        if not qbi:
            qbi = QuickBooksIntegration(
                integration_id=integration_id,
                realm_id=realm_id,
                access_token_encrypted=encrypt_token(access_token),
                refresh_token_encrypted=encrypt_token(refresh_token),
                access_token_expires_at=access_expiry,
                refresh_token_expires_at=refresh_expiry,
                scope=token_response.get("scope"),
                last_token_refresh_at=create_audit_datetime(),
            )
            self.session.add(qbi)
        else:
            qbi.realm_id = realm_id
            qbi.access_token_encrypted = encrypt_token(access_token)
            qbi.refresh_token_encrypted = encrypt_token(refresh_token)
            qbi.access_token_expires_at = access_expiry
            qbi.refresh_token_expires_at = refresh_expiry
            qbi.scope = token_response.get("scope")
            qbi.last_token_refresh_at = create_audit_datetime()

        await self.session.flush()
        return qbi

    async def _fetch_company_info(self, qbi: QuickBooksIntegration, realm_id: str) -> Optional[Dict[str, str]]:
        """Fetch company information from QuickBooks."""
        from ..intuit_client import IntuitClient

        client = IntuitClient(
            realm_id=realm_id,
            access_token=decrypt_token(qbi.access_token_encrypted),
            session=self.session,
            qbi=qbi
        )

        try:
            company_response = await client.get_company_info()
            if company_response and "CompanyInfo" in company_response:
                company = company_response["CompanyInfo"]
                return {
                    "company_id": company.get("Id"),
                    "company_name": company.get("CompanyName")
                }
        except Exception as e:
            logger.warning(f"Failed to fetch company info: {e}")

        return None

    async def _revoke_token_safe(self, encrypted_refresh_token: str) -> None:
        """Safely revoke refresh token (best effort)."""
        try:
            refresh_token = decrypt_token(encrypted_refresh_token)
            basic_auth = self._b64_basic_auth(settings.INTUIT_CLIENT_ID, settings.INTUIT_CLIENT_SECRET)

            headers = {
                "Accept": "application/json",
                "Authorization": f"Basic {basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            from urllib.parse import urlencode
            data = urlencode({"token": refresh_token})

            from ..intuit_client import IntuitClient
            
            # Use shared session pool to prevent connection pool exhaustion
            client = await get_shared_session()
            async with client.post(
                    "https://developer.api.intuit.com/v2/oauth2/tokens/revoke",
                    data=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as resp:
                    if resp.status >= 400:
                        logger.warning(f"Token revocation failed: {resp.status}")
        except Exception as e:
            logger.warning(f"Token revocation error: {e}")