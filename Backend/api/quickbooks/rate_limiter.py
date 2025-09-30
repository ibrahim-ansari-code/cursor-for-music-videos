"""
Improved rate limiter for QuickBooks API requests.

Provides memory-efficient rate limiting without requiring external dependencies
like Redis, while maintaining better cleanup and distributed-environment awareness.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 100  # Max requests per window
RATE_LIMIT_WINDOW_HOURS = 24  # Window duration in hours
CLEANUP_INTERVAL_MINUTES = 5  # How often to run cleanup
MAX_USERS_TRACKED = 1000  # Maximum number of users to track simultaneously


class MemoryEfficientRateLimiter:
    """
    Memory-efficient rate limiter that addresses the TTL cache memory leak issues.
    
    This implementation provides proper cleanup and memory management without 
    requiring external dependencies like Redis.
    """
    
    def __init__(
        self,
        max_requests: int = RATE_LIMIT_REQUESTS,
        window_hours: int = RATE_LIMIT_WINDOW_HOURS,
        max_users_tracked: int = MAX_USERS_TRACKED,
        cleanup_interval_minutes: int = CLEANUP_INTERVAL_MINUTES
    ):
        self.max_requests = max_requests
        self.window_hours = window_hours
        self.max_users_tracked = max_users_tracked
        self.cleanup_interval_minutes = cleanup_interval_minutes
        
        # Track requests per user with timestamps
        self._user_requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        
        logger.info(
            "Initialized MemoryEfficientRateLimiter: max_requests=%d, window_hours=%d, max_users=%d",
            max_requests, window_hours, max_users_tracked
        )
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user is within rate limit and record the request.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            now = time.time()
            
            # Perform periodic cleanup to prevent memory leaks
            await self._periodic_cleanup(now)
            
            # Get user's request history
            user_requests = self._user_requests[user_id]
            window_start = now - (self.window_hours * 3600)
            
            # Remove expired requests
            user_requests[:] = [req_time for req_time in user_requests if req_time > window_start]
            
            # Check if user is over the limit
            if len(user_requests) >= self.max_requests:
                logger.warning(
                    "Rate limit exceeded for user %s: %d requests in %d hour window",
                    user_id, len(user_requests), self.window_hours
                )
                return False
            
            # Record this request
            user_requests.append(now)
            
            # Apply memory pressure management
            await self._manage_memory_pressure()
            
            return True
    
    async def _periodic_cleanup(self, now: float) -> None:
        """Perform periodic cleanup to prevent memory accumulation."""
        if now - self._last_cleanup < (self.cleanup_interval_minutes * 60):
            return
            
        logger.debug("Performing rate limiter cleanup")
        
        window_start = now - (self.window_hours * 3600)
        users_removed = 0
        
        # Remove users with no recent requests
        user_ids_to_remove = []
        for user_id, requests in self._user_requests.items():
            # Clean expired requests
            requests[:] = [req_time for req_time in requests if req_time > window_start]
            
            # Remove users with no remaining requests
            if not requests:
                user_ids_to_remove.append(user_id)
        
        for user_id in user_ids_to_remove:
            del self._user_requests[user_id]
            users_removed += 1
        
        self._last_cleanup = now
        
        if users_removed > 0:
            logger.info(
                "Rate limiter cleanup completed: removed %d inactive users, tracking %d users",
                users_removed, len(self._user_requests)
            )
    
    async def _manage_memory_pressure(self) -> None:
        """Manage memory pressure when tracking too many users."""
        if len(self._user_requests) <= self.max_users_tracked:
            return
            
        logger.warning(
            "Rate limiter memory pressure: tracking %d users (max: %d), removing oldest",
            len(self._user_requests), self.max_users_tracked
        )
        
        # Find users with oldest last activity
        now = time.time()
        user_last_activity = {
            user_id: max(requests) if requests else 0
            for user_id, requests in self._user_requests.items()
        }
        
        # Sort by last activity (oldest first)
        sorted_users = sorted(user_last_activity.items(), key=lambda x: x[1])
        
        # Remove oldest users to get back under the limit
        users_to_remove = len(self._user_requests) - self.max_users_tracked + 10  # Remove a few extra
        for user_id, _ in sorted_users[:users_to_remove]:
            del self._user_requests[user_id]
        
        logger.info(
            "Removed %d oldest users due to memory pressure, now tracking %d users",
            users_to_remove, len(self._user_requests)
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Get current rate limiter statistics."""
        return {
            "users_tracked": len(self._user_requests),
            "max_users_tracked": self.max_users_tracked,
            "total_requests_tracked": sum(len(requests) for requests in self._user_requests.values()),
            "window_hours": self.window_hours,
            "max_requests_per_window": self.max_requests
        }


# Global rate limiter instance
_rate_limiter: Optional[MemoryEfficientRateLimiter] = None
_rate_limiter_lock = asyncio.Lock()


async def get_rate_limiter() -> MemoryEfficientRateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        async with _rate_limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = MemoryEfficientRateLimiter()
    
    return _rate_limiter


async def check_rate_limit(user_id: str) -> bool:
    """
    Check if a user is within the allowed number of requests for the current rate limit window.
    
    This is an improved version that addresses memory leak issues from the previous TTL cache
    implementation while maintaining compatibility.
    
    Args:
        user_id: Unique user identifier
        
    Returns:
        True if request is allowed, False if rate limited
    """
    rate_limiter = await get_rate_limiter()
    return await rate_limiter.check_rate_limit(user_id)


async def get_rate_limiter_stats() -> Dict[str, int]:
    """Get current rate limiter statistics for monitoring."""
    rate_limiter = await get_rate_limiter()
    return rate_limiter.get_stats()
