import logging
import ssl

import aiohttp
from fastapi import Depends, Header, HTTPException, Request, status

from Backend.config import settings

logger = logging.getLogger(__name__)


async def _verify_recaptcha(token: str, remote_ip: str | None) -> dict:
    """
    Verify a reCAPTCHA v3 token against Google's verification endpoint.
    Returns the parsed JSON response.
    """
    payload = {
        "secret": settings.RECAPTCHA_SECRET_KEY,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        # Create SSL context for connecting to Google
        timeout = aiohttp.ClientTimeout(total=10.0)
        
        # For local development environments that may have SSL certificate issues
        # This is safe because we're only connecting to Google's official reCAPTCHA endpoint
        if settings.ENVIRONMENT == "development":
            # In development, disable SSL verification for Google's endpoint
            # This avoids certificate issues on local machines
            logger.info("Using no SSL verification for reCAPTCHA in development mode")
            connector = aiohttp.TCPConnector(ssl=False)
        else:
            # In production, use default SSL context
            connector = aiohttp.TCPConnector(ssl=ssl.create_default_context())

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.post(settings.RECAPTCHA_VERIFY_URL, data=payload) as resp:
                data = await resp.json()
                return data
    except Exception as e:
        logger.error("reCAPTCHA verify failed: %s", str(e))
        logger.error("reCAPTCHA debug info - Environment: %s, Secret key configured: %s, URL: %s", 
                    settings.ENVIRONMENT, 
                    bool(settings.RECAPTCHA_SECRET_KEY.strip()) if settings.RECAPTCHA_SECRET_KEY else False,
                    settings.RECAPTCHA_VERIFY_URL)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify reCAPTCHA"
        )


def require_recaptcha(expected_action: str):
    """
    Returns a FastAPI dependency that enforces reCAPTCHA v3 verification.

    - Reads token from `X-Recaptcha-Token` header
    - Reads action from `X-Recaptcha-Action` header (optional; validated if present)
    - Allows bypass if no secret key is configured or when running tests
    """

    async def _dependency(
        request: Request,
        token: str | None = Header(default=None, alias="X-Recaptcha-Token"),
        action: str | None = Header(default=None, alias="X-Recaptcha-Action"),
    ) -> None:
        # Bypass in testing, development/preview environments, or when no secret key is configured
        is_development_like = (
            settings.ENVIRONMENT in ("development", "preview", "staging") or 
            settings.ENVIRONMENT.startswith("preview-") or
            "preview" in settings.ENVIRONMENT.lower()
        )
        
        if (settings.TESTING or 
            not settings.RECAPTCHA_SECRET_KEY or 
            settings.RECAPTCHA_SECRET_KEY.strip() == ""):
            logger.info("reCAPTCHA bypassed - testing=%s, no_secret=%s, environment=%s", 
                       settings.TESTING, 
                       not bool(settings.RECAPTCHA_SECRET_KEY.strip()) if settings.RECAPTCHA_SECRET_KEY else True,
                       settings.ENVIRONMENT)
            return None

        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing reCAPTCHA token"
            )

        remote_ip = request.client.host if request.client else None
        verification = await _verify_recaptcha(token, remote_ip)

        success = bool(verification.get("success"))
        score = float(verification.get("score", 0.0))
        action_resp = verification.get("action")

        if not success:
            # Log sanitized info only
            logger.warning(
                "reCAPTCHA failed: success=%s, score=%s, action=%s, error_codes=%s",
                success,
                verification.get("score"),
                action_resp,
                verification.get("error-codes")
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="reCAPTCHA verification failed"
            )

        # Validate expected action and score
        if action_resp and expected_action and action_resp != expected_action:
            logger.warning("reCAPTCHA action mismatch: expected=%s got=%s", expected_action, action_resp)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="reCAPTCHA action mismatch"
            )

        # For development environments, use a lower threshold to account for testing behavior
        min_score_threshold = settings.RECAPTCHA_MIN_SCORE
        is_dev_environment = (
            settings.ENVIRONMENT in ("development", "staging") or
            (request.url and "ngrok" in str(request.url.hostname))
        )
        if is_dev_environment:
            min_score_threshold = max(0.1, settings.RECAPTCHA_MIN_SCORE - 0.3)
            logger.info("Using relaxed reCAPTCHA score threshold for development: %.2f", min_score_threshold)

        if score < min_score_threshold:
            logger.warning("reCAPTCHA low score: %.2f < %.2f (threshold: %.2f)",
                          score, settings.RECAPTCHA_MIN_SCORE, min_score_threshold)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="reCAPTCHA score too low"
            )

        return None

    return _dependency


