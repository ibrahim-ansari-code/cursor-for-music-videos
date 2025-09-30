"""
Session Pool Manager for QuickBooks API requests.

Provides a singleton session pool to prevent connection pool exhaustion 
and memory leaks from creating new HTTP sessions for each request.
"""

import asyncio
import logging
from typing import Optional, Any
import aiohttp

logger = logging.getLogger(__name__)


class SessionPoolManager:
    """
    Singleton session pool manager for HTTP requests.
    
    Maintains a single aiohttp.ClientSession instance with proper connection pooling
    to prevent the anti-pattern of creating new sessions for each request.
    """
    
    _instance: Optional['SessionPoolManager'] = None
    _lock = asyncio.Lock()
    
    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._closed = False
    
    @classmethod
    async def get_instance(cls) -> 'SessionPoolManager':
        """Get singleton instance of SessionPoolManager."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    async def get_session(self) -> aiohttp.ClientSession:
        """
        Get the shared HTTP session with optimized connection pooling.
        
        Returns:
            Configured aiohttp.ClientSession instance
        """
        if self._session is None or self._session.closed:
            await self._create_session()
        
        # At this point _session should never be None due to _create_session
        if self._session is None:
            raise RuntimeError("Failed to create HTTP session")
        
        return self._session
    
    async def _create_session(self) -> None:
        """Create new HTTP session with optimized connection pool settings."""
        if self._connector and not self._connector.closed:
            await self._connector.close()
            
        # Import SSL context function
        from .intuit_oauth import _create_ssl_context

        # Optimized connection pool settings with SSL context for development
        ssl_context = _create_ssl_context()

        connector_kwargs = {
            'limit': 100,                    # Total connection pool size
            'limit_per_host': 30,            # Max connections per host (QuickBooks API)
            'ttl_dns_cache': 300,           # DNS cache TTL (5 minutes)
            'use_dns_cache': True,          # Enable DNS caching
            'enable_cleanup_closed': True,   # Clean up closed connections
            'keepalive_timeout': 30         # Keep-alive timeout
        }

        # Add SSL context if available (for development certificate handling)
        if ssl_context:
            connector_kwargs['ssl'] = ssl_context

        self._connector = aiohttp.TCPConnector(**connector_kwargs)
        
        # Create session with proper timeout and connector
        timeout = aiohttp.ClientTimeout(
            total=30,      # Total request timeout
            connect=10,    # Connection timeout
            sock_read=20   # Socket read timeout
        )
        
        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Brikli-QuickBooks-Integration/1.0',
                'Accept': 'application/json',
            }
        )
        
        self._closed = False
        logger.info("Created new HTTP session with optimized connection pool")
    
    async def close(self) -> None:
        """Close the session and connector to prevent resource leaks."""
        if not self._closed:
            if self._session and not self._session.closed:
                await self._session.close()
                logger.info("Closed HTTP session")
                
            if self._connector and not self._connector.closed:
                await self._connector.close()
                logger.info("Closed HTTP connector")
                
            self._closed = True
    
    async def __aenter__(self) -> aiohttp.ClientSession:
        """Async context manager entry."""
        return await self.get_session()
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - do not close session here as it's shared."""
        pass


# Global session pool manager instance
_session_manager: Optional[SessionPoolManager] = None


async def get_shared_session() -> aiohttp.ClientSession:
    """
    Get the shared HTTP session for QuickBooks API requests.
    
    This is a convenience function that manages the singleton SessionPoolManager
    and returns the shared HTTP session instance.
    
    Returns:
        Configured aiohttp.ClientSession instance
    """
    global _session_manager
    
    if _session_manager is None:
        _session_manager = await SessionPoolManager.get_instance()
    
    return await _session_manager.get_session()


async def close_shared_session() -> None:
    """Close the shared HTTP session. Should be called on application shutdown."""
    global _session_manager
    
    if _session_manager is not None:
        await _session_manager.close()
        _session_manager = None
        logger.info("Shared session manager closed")
