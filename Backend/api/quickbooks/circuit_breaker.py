"""
Circuit Breaker Pattern for QuickBooks API calls.

Prevents cascading failures when QuickBooks API is experiencing issues by
temporarily stopping requests when failure thresholds are exceeded.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar
from dataclasses import dataclass, field

import sentry_sdk

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5              # Number of failures before opening
    recovery_timeout: int = 60              # Seconds before trying half-open
    half_open_max_calls: int = 3           # Max calls to test in half-open state
    success_threshold: int = 2              # Successes needed to close from half-open
    timeout_threshold: float = 30.0         # Request timeout considered as failure

    # Failure rate threshold (0.0 to 1.0)
    failure_rate_threshold: float = 0.5     # 50% failure rate triggers opening
    min_requests_for_rate: int = 10         # Minimum requests before checking rate


@dataclass
class CircuitBreakerStats:
    """Statistics for monitoring circuit breaker behavior."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    state_change_count: int = 0
    current_half_open_calls: int = 0
    config: Optional[CircuitBreakerConfig] = None

    # Rolling window stats (last 5 minutes)
    recent_requests: list = field(default_factory=list)
    recent_failures: list = field(default_factory=list)

    def get_failure_rate(self) -> float:
        """Calculate current failure rate in the recent window."""
        now = time.time()
        window = 300  # 5 minutes

        # Clean old entries
        self.recent_requests = [t for t in self.recent_requests if now - t < window]
        self.recent_failures = [t for t in self.recent_failures if now - t < window]

        min_requests = self.config.min_requests_for_rate if self.config else 10
        if len(self.recent_requests) < min_requests:
            return 0.0

        return len(self.recent_failures) / len(self.recent_requests)


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and blocking requests."""

    def __init__(self, message: str, stats: CircuitBreakerStats):
        super().__init__(message)
        self.stats = stats


class CircuitBreaker:
    """
    Circuit breaker implementation for QuickBooks API calls.

    Provides automatic failure detection and recovery with configurable
    thresholds and timeouts.
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self.stats.config = self.config  # Reference for stats methods
        self._lock = asyncio.Lock()

        logger.info(
            "Initialized circuit breaker '%s' with failure_threshold=%d, recovery_timeout=%ds",
            name, self.config.failure_threshold, self.config.recovery_timeout
        )

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Result of function execution

        Raises:
            CircuitBreakerError: If circuit is open and blocking requests
            Original exception: If function fails and circuit allows it
        """
        async with self._lock:
            await self._check_state()

            if self.stats.state == CircuitState.OPEN:
                self._log_blocked_request()
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Last failure: {self.stats.last_failure_time}, "
                    f"Failure count: {self.stats.failure_count}",
                    self.stats
                )

            if (self.stats.state == CircuitState.HALF_OPEN and
                self.stats.current_half_open_calls >= self.config.half_open_max_calls):
                self._log_blocked_request()
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is HALF_OPEN with max calls reached",
                    self.stats
                )

        # Execute the function
        start_time = time.time()
        self.stats.total_requests += 1
        self.stats.recent_requests.append(start_time)

        if self.stats.state == CircuitState.HALF_OPEN:
            self.stats.current_half_open_calls += 1

        try:
            # Add timeout protection
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout_threshold
            )

            # Success - record it
            await self._record_success()
            return result

        except asyncio.TimeoutError as e:
            await self._record_failure(e, "timeout")
            raise
        except Exception as e:
            await self._record_failure(e, "exception")
            raise

    async def _check_state(self) -> None:
        """Check and update circuit breaker state."""
        now = time.time()

        if self.stats.state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if (self.stats.last_failure_time and
                now - self.stats.last_failure_time >= self.config.recovery_timeout):
                await self._transition_to_half_open()

        elif self.stats.state == CircuitState.CLOSED:
            # Check if we should open due to failure rate
            failure_rate = self.stats.get_failure_rate()
            if (failure_rate >= self.config.failure_rate_threshold and
                len(self.stats.recent_requests) >= self.config.min_requests_for_rate):
                await self._transition_to_open("high_failure_rate")

    async def _record_success(self) -> None:
        """Record a successful operation."""
        async with self._lock:
            now = time.time()
            self.stats.success_count += 1
            self.stats.total_successes += 1
            self.stats.last_success_time = now

            if self.stats.state == CircuitState.HALF_OPEN:
                if self.stats.success_count >= self.config.success_threshold:
                    await self._transition_to_closed()
            elif self.stats.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.stats.failure_count = 0

    async def _record_failure(self, exception: Exception, failure_type: str) -> None:
        """Record a failed operation."""
        async with self._lock:
            now = time.time()
            self.stats.failure_count += 1
            self.stats.total_failures += 1
            self.stats.last_failure_time = now
            self.stats.recent_failures.append(now)

            # Log the failure with context
            logger.warning(
                "Circuit breaker '%s' recorded failure (%s): %s [failures: %d/%d]",
                self.name, failure_type, str(exception),
                self.stats.failure_count, self.config.failure_threshold
            )

            # Report to Sentry with circuit breaker context
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("circuit_breaker", self.name)
                scope.set_tag("failure_type", failure_type)
                scope.set_context("circuit_breaker_stats", {
                    "state": self.stats.state.value,
                    "failure_count": self.stats.failure_count,
                    "failure_rate": self.stats.get_failure_rate(),
                    "total_requests": self.stats.total_requests
                })
                sentry_sdk.capture_exception(exception)

            # Check if we should open the circuit
            if self.stats.state == CircuitState.CLOSED:
                if self.stats.failure_count >= self.config.failure_threshold:
                    await self._transition_to_open("failure_threshold")
            elif self.stats.state == CircuitState.HALF_OPEN:
                # Any failure in half-open state opens the circuit
                await self._transition_to_open("half_open_failure")

    async def _transition_to_open(self, reason: str) -> None:
        """Transition circuit to OPEN state."""
        old_state = self.stats.state
        self.stats.state = CircuitState.OPEN
        self.stats.state_change_count += 1
        self.stats.current_half_open_calls = 0

        logger.error(
            "Circuit breaker '%s' transitioned from %s to OPEN (reason: %s) "
            "[failures: %d, failure_rate: %.2f]",
            self.name, old_state.value, reason,
            self.stats.failure_count, self.stats.get_failure_rate()
        )

        # Report state change to Sentry
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("circuit_breaker", self.name)
            scope.set_level("error")
            sentry_sdk.capture_message(
                f"Circuit breaker '{self.name}' opened due to {reason}",
                level="error"
            )

    async def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state."""
        old_state = self.stats.state
        self.stats.state = CircuitState.HALF_OPEN
        self.stats.state_change_count += 1
        self.stats.success_count = 0
        self.stats.failure_count = 0
        self.stats.current_half_open_calls = 0

        logger.info(
            "Circuit breaker '%s' transitioned from %s to HALF_OPEN (testing recovery)",
            self.name, old_state.value
        )

    async def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state."""
        old_state = self.stats.state
        self.stats.state = CircuitState.CLOSED
        self.stats.state_change_count += 1
        self.stats.success_count = 0
        self.stats.failure_count = 0
        self.stats.current_half_open_calls = 0

        logger.info(
            "Circuit breaker '%s' transitioned from %s to CLOSED (recovery confirmed)",
            self.name, old_state.value
        )

        # Report recovery to Sentry
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("circuit_breaker", self.name)
            scope.set_level("info")
            sentry_sdk.capture_message(
                f"Circuit breaker '{self.name}' recovered and closed",
                level="info"
            )

    def _log_blocked_request(self) -> None:
        """Log blocked request for monitoring."""
        logger.warning(
            "Circuit breaker '%s' blocked request [state: %s, failures: %d]",
            self.name, self.stats.state.value, self.stats.failure_count
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get current circuit breaker statistics for monitoring."""
        return {
            "name": self.name,
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_requests": self.stats.total_requests,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "failure_rate": self.stats.get_failure_rate(),
            "state_changes": self.stats.state_change_count,
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
            "half_open_calls": self.stats.current_half_open_calls,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "failure_rate_threshold": self.config.failure_rate_threshold
            }
        }

    async def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        async with self._lock:
            logger.info("Manually resetting circuit breaker '%s' to CLOSED", self.name)
            await self._transition_to_closed()


# Global circuit breaker instances
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_circuit_breaker_lock = asyncio.Lock()


async def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Get or create a circuit breaker instance.

    Args:
        name: Unique name for the circuit breaker
        config: Optional configuration (uses defaults if not provided)

    Returns:
        CircuitBreaker instance
    """
    global _circuit_breakers

    if name not in _circuit_breakers:
        async with _circuit_breaker_lock:
            if name not in _circuit_breakers:
                _circuit_breakers[name] = CircuitBreaker(name, config)

    return _circuit_breakers[name]


async def get_all_circuit_breaker_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all circuit breakers for monitoring."""
    return {name: cb.get_stats() for name, cb in _circuit_breakers.items()}