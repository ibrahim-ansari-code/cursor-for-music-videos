import base64
import ssl
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional

import aiohttp
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.config import settings
from Backend.models.accounting.quickbooks_integration import QuickBooksIntegration
from Backend.utils.datetime_utils import create_audit_datetime
from .crypto_utils import encrypt_token, decrypt_token
from .session_manager import get_shared_session

logger = logging.getLogger(__name__)


def _create_ssl_context() -> Optional[ssl.SSLContext]:
    """Create SSL context for API requests with development environment support.

    Handles SSL certificate chain issues commonly seen in development environments
    while maintaining security. For production, uses default secure context.
    """
    try:
        # Create default SSL context with proper certificate validation
        context = ssl.create_default_context()

        # For development environments, handle certificate chain issues
        if settings.ENVIRONMENT == "development":
            logger.info("Configuring SSL context for development environment")

            # Use system certificate store
            try:
                import certifi
                context.load_verify_locations(certifi.where())
                logger.debug("Loaded certificates from certifi")
            except ImportError:
                logger.warning("certifi not available, using system certificates")

            # For macOS development environments, load additional certificates
            import platform
            if platform.system() == "Darwin":  # macOS
                try:
                    # Load macOS system keychain certificates
                    context.load_default_certs(ssl.Purpose.SERVER_AUTH)
                    # Also try to load from common macOS certificate locations
                    macos_cert_paths = [
                        "/System/Library/Keychains/SystemRootCertificates.keychain",
                        "/Library/Keychains/System.keychain"
                    ]
                    for cert_path in macos_cert_paths:
                        try:
                            context.load_verify_locations(cert_path)
                        except:
                            pass  # Silently continue if cert path doesn't exist
                    logger.debug("Loaded macOS system certificates")
                except Exception as e:
                    logger.debug(f"Could not load macOS certificates: {e}")

        return context

    except Exception as e:
        logger.warning(f"Failed to create custom SSL context: {e}")
        logger.info("Falling back to default SSL context")
        return None


def _b64_basic_auth(client_id: str, client_secret: str) -> str:
    """Create basic auth header."""
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


async def refresh_access_token(session: AsyncSession, qbi: QuickBooksIntegration) -> QuickBooksIntegration:
    token_url = settings.INTUIT_TOKEN_URL
    basic = _b64_basic_auth(settings.INTUIT_CLIENT_ID, settings.INTUIT_CLIENT_SECRET)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    from urllib.parse import urlencode

    data = urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": decrypt_token(qbi.refresh_token_encrypted),
        }
    )

    # Use shared session pool to prevent connection pool exhaustion
    client = await get_shared_session()
    async with client.post(token_url, data=data, headers=headers) as resp:
            if resp.status >= 400:
                body = await resp.text()
                logger.error("Intuit token refresh failed: %s %s", resp.status, body)
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Token refresh failed")
            payload = await resp.json()

    access_token = payload.get("access_token")
    expires_in = int(payload.get("expires_in", 3600))
    x_refresh_expires_in = payload.get("x_refresh_token_expires_in")
    refresh_expires_in = int(x_refresh_expires_in) if x_refresh_expires_in is not None else None
    new_refresh = payload.get("refresh_token") or None

    qbi.access_token_encrypted = encrypt_token(access_token)
    qbi.access_token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    if new_refresh:
        qbi.refresh_token_encrypted = encrypt_token(new_refresh)
    if refresh_expires_in:
        qbi.refresh_token_expires_at = datetime.now(UTC) + timedelta(seconds=refresh_expires_in)
    qbi.last_token_refresh_at = create_audit_datetime()
    session.add(qbi)
    await session.commit()
    return qbi
