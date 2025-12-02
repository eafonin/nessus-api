"""Circuit breaker pattern for scanner failure handling.

Phase 4.12: Prevents cascading failures when scanners become unavailable.

The circuit breaker has three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Scanner failing, requests fail fast without trying
- HALF_OPEN: Testing recovery, allows limited requests

Transitions:
- CLOSED -> OPEN: After N consecutive failures
- OPEN -> HALF_OPEN: After timeout period
- HALF_OPEN -> CLOSED: On successful request
- HALF_OPEN -> OPEN: On failed request
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


# Circuit breaker metrics
circuit_state_gauge = Gauge(
    "nessus_circuit_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["scanner_instance"],
)

circuit_failures_total = Counter(
    "nessus_circuit_failures_total",
    "Total failures recorded by circuit breaker",
    ["scanner_instance"],
)

circuit_opens_total = Counter(
    "nessus_circuit_opens_total",
    "Total times circuit breaker opened",
    ["scanner_instance"],
)


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for scanner connections.

    Usage:
        cb = CircuitBreaker(name="nessus:scanner1")

        if cb.allow_request():
            try:
                result = await scanner.some_operation()
                cb.record_success()
            except Exception as e:
                cb.record_failure()
                raise
        else:
            raise CircuitOpenError(f"Circuit open for {cb.name}")

    Configuration:
        - failure_threshold: Number of failures before opening (default: 5)
        - recovery_timeout: Seconds to wait before testing recovery (default: 30)
        - half_open_max_requests: Requests allowed in half-open state (default: 1)
    """

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_requests: int = 1

    # Internal state
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float | None = field(default=None, init=False)
    _half_open_requests: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self):
        """Initialize metrics."""
        self._update_state_metric()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            self._check_recovery()
            return self._state

    def _check_recovery(self) -> None:
        """Check if circuit should transition from OPEN to HALF_OPEN."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                logger.info(
                    f"[{self.name}] Circuit transitioning OPEN -> HALF_OPEN "
                    f"(elapsed={elapsed:.1f}s)"
                )
                self._state = CircuitState.HALF_OPEN
                self._half_open_requests = 0
                self._update_state_metric()

    def allow_request(self) -> bool:
        """
        Check if a request should be allowed.

        Returns:
            True if request can proceed, False if circuit is open
        """
        with self._lock:
            self._check_recovery()

            if self._state == CircuitState.CLOSED:
                return True
            elif self._state == CircuitState.HALF_OPEN:
                if self._half_open_requests < self.half_open_max_requests:
                    self._half_open_requests += 1
                    return True
                return False
            else:  # OPEN
                return False

    def record_success(self) -> None:
        """
        Record a successful request.

        Resets failure count and closes circuit if in half-open state.
        """
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(f"[{self.name}] Circuit transitioning HALF_OPEN -> CLOSED")
                self._state = CircuitState.CLOSED
                self._update_state_metric()

            self._failure_count = 0
            self._last_failure_time = None

    def record_failure(self) -> None:
        """
        Record a failed request.

        Increments failure count and opens circuit if threshold exceeded.
        """
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            circuit_failures_total.labels(scanner_instance=self.name).inc()

            if self._state == CircuitState.HALF_OPEN:
                # Failed during recovery test, reopen
                logger.warning(
                    f"[{self.name}] Circuit transitioning HALF_OPEN -> OPEN "
                    "(recovery test failed)"
                )
                self._state = CircuitState.OPEN
                circuit_opens_total.labels(scanner_instance=self.name).inc()
                self._update_state_metric()

            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    logger.warning(
                        f"[{self.name}] Circuit transitioning CLOSED -> OPEN "
                        f"(failures={self._failure_count})"
                    )
                    self._state = CircuitState.OPEN
                    circuit_opens_total.labels(scanner_instance=self.name).inc()
                    self._update_state_metric()

    def reset(self) -> None:
        """Manually reset circuit to closed state."""
        with self._lock:
            logger.info(f"[{self.name}] Circuit manually reset to CLOSED")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._half_open_requests = 0
            self._update_state_metric()

    def _update_state_metric(self) -> None:
        """Update Prometheus state metric."""
        state_value = {
            CircuitState.CLOSED: 0,
            CircuitState.OPEN: 1,
            CircuitState.HALF_OPEN: 2,
        }[self._state]
        circuit_state_gauge.labels(scanner_instance=self.name).set(state_value)

    def get_status(self) -> dict[str, Any]:
        """
        Get current circuit breaker status.

        Returns:
            Dict with state, failure count, last failure time
        """
        with self._lock:
            self._check_recovery()
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "last_failure_time": self._last_failure_time,
                "recovery_timeout": self.recovery_timeout,
                "time_until_recovery": max(
                    0, self.recovery_timeout - (time.time() - self._last_failure_time)
                )
                if self._last_failure_time and self._state == CircuitState.OPEN
                else None,
            }


class CircuitOpenError(Exception):
    """Raised when circuit is open and request cannot proceed."""

    def __init__(self, message: str, circuit_name: str | None = None) -> None:
        super().__init__(message)
        self.circuit_name = circuit_name


class CircuitBreakerRegistry:
    """
    Manages circuit breakers for all scanner instances.

    Provides a central point for:
    - Creating circuit breakers per scanner
    - Getting status of all circuits
    - Manually resetting circuits
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        """
        Initialize circuit breaker registry.

        Args:
            failure_threshold: Default failures before opening
            recovery_timeout: Default seconds before recovery test
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get(self, scanner_name: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for scanner.

        Args:
            scanner_name: Scanner instance identifier

        Returns:
            CircuitBreaker for the scanner
        """
        with self._lock:
            if scanner_name not in self._breakers:
                self._breakers[scanner_name] = CircuitBreaker(
                    name=scanner_name,
                    failure_threshold=self.failure_threshold,
                    recovery_timeout=self.recovery_timeout,
                )
            return self._breakers[scanner_name]

    def get_all_status(self) -> dict[str, dict[str, Any]]:
        """
        Get status of all circuit breakers.

        Returns:
            Dict mapping scanner names to status dicts
        """
        with self._lock:
            return {name: cb.get_status() for name, cb in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        with self._lock:
            for cb in self._breakers.values():
                cb.reset()

    def reset(self, scanner_name: str) -> bool:
        """
        Reset specific circuit breaker.

        Args:
            scanner_name: Scanner instance identifier

        Returns:
            True if breaker found and reset, False otherwise
        """
        with self._lock:
            if scanner_name in self._breakers:
                self._breakers[scanner_name].reset()
                return True
            return False


# Global registry instance (can be overridden in tests)
_registry: CircuitBreakerRegistry | None = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get global circuit breaker registry."""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


def get_circuit_breaker(scanner_name: str) -> CircuitBreaker:
    """
    Convenience function to get circuit breaker for scanner.

    Args:
        scanner_name: Scanner instance identifier

    Returns:
        CircuitBreaker for the scanner
    """
    return get_circuit_breaker_registry().get(scanner_name)
