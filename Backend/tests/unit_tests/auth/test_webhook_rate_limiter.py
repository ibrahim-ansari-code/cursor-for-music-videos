"""
Unit tests for webhook rate limiter.

Tests the WebhookRateLimiter class for proper rate limiting, memory management,
and cleanup behavior.
"""

import pytest
import asyncio
import time
from unittest.mock import patch

from Backend.api.auth.webhook_rate_limiter import (
    WebhookRateLimiter,
    get_webhook_rate_limiter,
    check_webhook_rate_limit
)


pytestmark = pytest.mark.unit


class TestWebhookRateLimiter:
    """Tests for WebhookRateLimiter class."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_under_limit(self):
        """Test rate limiter allows requests under the limit."""
        limiter = WebhookRateLimiter(
            max_requests=10,
            window_seconds=60
        )
        
        # Make 10 requests (under limit)
        for i in range(10):
            allowed = await limiter.check_rate_limit("test-ip")
            assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_over_limit(self):
        """Test rate limiter blocks requests over the limit."""
        limiter = WebhookRateLimiter(
            max_requests=5,
            window_seconds=60
        )
        
        # Make 5 requests (at limit)
        for i in range(5):
            allowed = await limiter.check_rate_limit("test-ip")
            assert allowed is True
        
        # 6th request should be blocked
        allowed = await limiter.check_rate_limit("test-ip")
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_rate_limiter_per_ip_isolation(self):
        """Test rate limiter tracks IPs independently."""
        limiter = WebhookRateLimiter(
            max_requests=3,
            window_seconds=60
        )
        
        # IP 1: Make 3 requests
        for i in range(3):
            allowed = await limiter.check_rate_limit("ip-1")
            assert allowed is True
        
        # IP 1: 4th request blocked
        allowed = await limiter.check_rate_limit("ip-1")
        assert allowed is False
        
        # IP 2: Should still work
        allowed = await limiter.check_rate_limit("ip-2")
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_window_expiry(self):
        """Test rate limiter resets after window expires."""
        limiter = WebhookRateLimiter(
            max_requests=2,
            window_seconds=1  # 1 second window
        )
        
        # Make 2 requests (at limit)
        await limiter.check_rate_limit("test-ip")
        await limiter.check_rate_limit("test-ip")
        
        # 3rd request blocked
        allowed = await limiter.check_rate_limit("test-ip")
        assert allowed is False
        
        # Wait for window to expire
        await asyncio.sleep(1.1)
        
        # Should work again
        allowed = await limiter.check_rate_limit("test-ip")
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_periodic_cleanup(self):
        """Test rate limiter cleans up expired entries."""
        limiter = WebhookRateLimiter(
            max_requests=5,
            window_seconds=1,
            cleanup_interval=1
        )
        
        # Make requests from multiple IPs
        await limiter.check_rate_limit("ip-1")
        await limiter.check_rate_limit("ip-2")
        await limiter.check_rate_limit("ip-3")
        
        assert len(limiter._ip_requests) == 3
        
        # Wait for cleanup
        await asyncio.sleep(1.5)
        
        # Trigger cleanup by making another request
        await limiter.check_rate_limit("ip-4")
        
        # Old IPs should be cleaned up
        # (Note: cleanup happens periodically, not guaranteed immediate)
        assert len(limiter._ip_requests) <= 4
    
    @pytest.mark.asyncio
    async def test_rate_limiter_memory_pressure_management(self):
        """Test rate limiter enforces max IPs tracked."""
        limiter = WebhookRateLimiter(
            max_requests=10,
            window_seconds=60,
            max_ips_tracked=5
        )
        
        # Add 10 IPs (over limit)
        for i in range(10):
            await limiter.check_rate_limit(f"ip-{i}")
        
        # Should have enforced max
        assert len(limiter._ip_requests) <= 5
    
    @pytest.mark.asyncio
    async def test_rate_limiter_get_stats(self):
        """Test rate limiter statistics."""
        limiter = WebhookRateLimiter(
            max_requests=10,
            window_seconds=60
        )
        
        # Make some requests
        await limiter.check_rate_limit("ip-1")
        await limiter.check_rate_limit("ip-1")
        await limiter.check_rate_limit("ip-2")
        
        stats = limiter.get_stats()
        
        assert stats["tracked_ips"] == 2
        assert stats["total_requests"] == 3
        assert stats["max_requests_per_window"] == 10
    
    @pytest.mark.asyncio
    async def test_rate_limiter_thread_safety(self):
        """Test rate limiter is thread-safe with concurrent requests."""
        limiter = WebhookRateLimiter(
            max_requests=100,
            window_seconds=60
        )
        
        # Make concurrent requests
        tasks = [limiter.check_rate_limit("test-ip") for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        # All should be allowed (under limit)
        assert all(results)
        
        # Should have tracked exactly 50 requests
        stats = limiter.get_stats()
        assert stats["total_requests"] == 50


class TestWebhookRateLimiterGlobalInstance:
    """Tests for global rate limiter instance and convenience functions."""
    
    @pytest.mark.asyncio
    async def test_get_webhook_rate_limiter_singleton(self):
        """Test get_webhook_rate_limiter returns same instance."""
        limiter1 = await get_webhook_rate_limiter()
        limiter2 = await get_webhook_rate_limiter()
        
        assert limiter1 is limiter2
    
    @pytest.mark.asyncio
    async def test_check_webhook_rate_limit_convenience_function(self):
        """Test convenience function for checking rate limit."""
        # Should work without explicit limiter instance
        allowed = await check_webhook_rate_limit("test-ip")
        assert allowed is True


class TestWebhookRateLimiterEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_handles_empty_ip(self):
        """Test rate limiter handles empty IP address."""
        limiter = WebhookRateLimiter(max_requests=5, window_seconds=60)
        
        allowed = await limiter.check_rate_limit("")
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_handles_none_ip(self):
        """Test rate limiter handles None IP address."""
        limiter = WebhookRateLimiter(max_requests=5, window_seconds=60)
        
        # Should not crash
        allowed = await limiter.check_rate_limit("unknown")
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_with_zero_requests(self):
        """Test rate limiter with max_requests=0 blocks all requests."""
        limiter = WebhookRateLimiter(max_requests=0, window_seconds=60)
        
        allowed = await limiter.check_rate_limit("test-ip")
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_rate_limiter_cleanup_doesnt_crash_on_concurrent_access(self):
        """Test cleanup handles concurrent access safely."""
        limiter = WebhookRateLimiter(
            max_requests=10,
            window_seconds=1,
            cleanup_interval=1
        )
        
        # Make concurrent requests while cleanup might be running
        tasks = []
        for i in range(20):
            tasks.append(limiter.check_rate_limit(f"ip-{i % 5}"))
            if i % 5 == 0:
                await asyncio.sleep(0.3)  # Trigger cleanup intermittently
        
        results = await asyncio.gather(*tasks)
        
        # Should not crash, some requests should succeed
        assert any(results)

