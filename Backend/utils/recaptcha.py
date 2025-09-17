import logging

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
        timeout = aiohttp.ClientTimeout(total=10.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(settings.RECAPTCHA_VERIFY_URL, data=payload) as resp:
                data = await resp.json()
                return data
    except Exception as e:
        logger.error("reCAPTCHA verify failed: %s", str(e))
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
        # Bypass in testing or when no secret key is configured
        if settings.TESTING or not settings.RECAPTCHA_SECRET_KEY:
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

        if score < settings.RECAPTCHA_MIN_SCORE:
            logger.warning("reCAPTCHA low score: %.2f < %.2f", score, settings.RECAPTCHA_MIN_SCORE)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="reCAPTCHA score too low"
            )

        return None

    return _dependency


