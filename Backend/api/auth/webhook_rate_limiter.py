"""
Rate limiter for webhook endpoints.

Protects webhook endpoints from abuse while allowing legitimate Supabase
webhook traffic. Uses in-memory storage with proper cleanup.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Webhook rate limiting configuration
WEBHOOK_RATE_LIMIT_REQUESTS = 1000  # Max requests per window (generous for webhooks)
WEBHOOK_RATE_LIMIT_WINDOW_SECONDS = 60  # 1 minute window
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes
MAX_IPS_TRACKED = 100  # Maximum number of IPs to track


class WebhookRateLimiter:
    """
    Rate limiter specifically designed for webhook endpoints.
    
    Features:
    - Per-IP rate limiting
    - Generous limits for legitimate webhook traffic
    - Memory-efficient with automatic cleanup
    - Async-safe with proper locking
    """
    
    def __init__(
        self,
        max_requests: int = WEBHOOK_RATE_LIMIT_REQUESTS,
        window_seconds: int = WEBHOOK_RATE_LIMIT_WINDOW_SECONDS,
        max_ips_tracked: int = MAX_IPS_TRACKED,
        cleanup_interval: int = CLEANUP_INTERVAL_SECONDS
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_ips_tracked = max_ips_tracked
        self.cleanup_interval = cleanup_interval
        
        # Track requests per IP with timestamps
        self._ip_requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        
        logger.info(
            "Initialized WebhookRateLimiter: max_requests=%d, window_seconds=%d",
            max_requests, window_seconds
        )
    
    async def check_rate_limit(self, ip_address: str) -> bool:
        """
        Check if IP is within rate limit.
        
        Args:
            ip_address: Client IP address
            
        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            now = time.time()
            
            # Periodic cleanup
            await self._periodic_cleanup(now)
            
            # Get IP's request history
            ip_requests = self._ip_requests[ip_address]
            window_start = now - self.window_seconds
            
            # Remove expired requests
            ip_requests[:] = [req_time for req_time in ip_requests if req_time > window_start]
            
            # Check if over the limit
            if len(ip_requests) >= self.max_requests:
                logger.warning(
                    "Webhook rate limit exceeded for IP %s: %d requests in %d second window",
                    ip_address, len(ip_requests), self.window_seconds
                )
                return False
            
            # Record this request
            ip_requests.append(now)
            
            # Memory pressure management
            await self._manage_memory_pressure()
            
            return True
    
    async def _periodic_cleanup(self, now: float) -> None:
        """Remove expired entries to prevent memory leaks."""
        if now - self._last_cleanup < self.cleanup_interval:
            return
        
        window_start = now - self.window_seconds
        cleaned_ips = []
        
        for ip_address, requests in list(self._ip_requests.items()):
            # Remove expired requests
            requests[:] = [req_time for req_time in requests if req_time > window_start]
            
            # Remove empty entries
            if not requests:
                cleaned_ips.append(ip_address)
        
        for ip_address in cleaned_ips:
            del self._ip_requests[ip_address]
        
        self._last_cleanup = now
        
        if cleaned_ips:
            logger.debug("Cleaned up %d inactive IPs from webhook rate limiter", len(cleaned_ips))
    
    async def _manage_memory_pressure(self) -> None:
        """Enforce maximum tracked IPs to prevent unbounded memory growth."""
        if len(self._ip_requests) <= self.max_ips_tracked:
            return
        
        # Remove oldest IPs (those with oldest last request)
        now = time.time()
        ip_last_request = {
            ip: max(requests) if requests else 0
            for ip, requests in self._ip_requests.items()
        }
        
        # Sort by last request time and remove oldest
        sorted_ips = sorted(ip_last_request.items(), key=lambda x: x[1])
        ips_to_remove = sorted_ips[:len(sorted_ips) - self.max_ips_tracked]
        
        for ip, _ in ips_to_remove:
            del self._ip_requests[ip]
        
        logger.warning(
            "Memory pressure: removed %d IPs from webhook rate limiter",
            len(ips_to_remove)
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Get current rate limiter statistics."""
        return {
            "tracked_ips": len(self._ip_requests),
            "total_requests": sum(len(reqs) for reqs in self._ip_requests.values()),
            "max_requests_per_window": self.max_requests
        }


# Global rate limiter instance
_webhook_rate_limiter: Optional[WebhookRateLimiter] = None
_limiter_lock = asyncio.Lock()


async def get_webhook_rate_limiter() -> WebhookRateLimiter:
    """Get the global webhook rate limiter instance."""
    global _webhook_rate_limiter
    
    if _webhook_rate_limiter is None:
        async with _limiter_lock:
            if _webhook_rate_limiter is None:
                _webhook_rate_limiter = WebhookRateLimiter()
    
    return _webhook_rate_limiter


async def check_webhook_rate_limit(ip_address: str) -> bool:
    """
    Convenience function to check webhook rate limit.
    
    Args:
        ip_address: Client IP address
        
    Returns:
        True if request is allowed, False if rate limited
    """
    limiter = await get_webhook_rate_limiter()
    return await limiter.check_rate_limit(ip_address)

