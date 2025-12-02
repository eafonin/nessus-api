"""Unit tests for circuit breaker."""

import time

from core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitOpenError,
    CircuitState,
)


class TestCircuitBreakerBasic:
    """Test basic circuit breaker functionality."""

    def test_initial_state_closed(self):
        """Test circuit starts in closed state."""
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED

    def test_allow_request_when_closed(self):
        """Test requests allowed when closed."""
        cb = CircuitBreaker(name="test")
        assert cb.allow_request() is True

    def test_record_success_keeps_closed(self):
        """Test success keeps circuit closed."""
        cb = CircuitBreaker(name="test")
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_single_failure_stays_closed(self):
        """Test single failure doesn't open circuit."""
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 1

    def test_opens_after_threshold(self):
        """Test circuit opens after threshold failures."""
        cb = CircuitBreaker(name="test", failure_threshold=3)

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_blocks_requests_when_open(self):
        """Test requests blocked when open."""
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_reset_closes_circuit(self):
        """Test manual reset closes circuit."""
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0


class TestCircuitBreakerRecovery:
    """Test circuit breaker recovery behavior."""

    def test_transitions_to_half_open(self):
        """Test circuit transitions to half-open after timeout."""
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_allows_limited_requests(self):
        """Test half-open allows limited requests."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=1,
            recovery_timeout=0.1,
            half_open_max_requests=2,
        )
        cb.record_failure()
        time.sleep(0.15)

        # Should allow 2 requests
        assert cb.allow_request() is True
        assert cb.allow_request() is True
        # Third should be blocked
        assert cb.allow_request() is False

    def test_success_in_half_open_closes(self):
        """Test success during half-open closes circuit."""
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        time.sleep(0.15)

        assert cb.state == CircuitState.HALF_OPEN
        cb.allow_request()
        cb.record_success()

        assert cb.state == CircuitState.CLOSED

    def test_failure_in_half_open_reopens(self):
        """Test failure during half-open reopens circuit."""
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        time.sleep(0.15)

        assert cb.state == CircuitState.HALF_OPEN
        cb.allow_request()
        cb.record_failure()

        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerStatus:
    """Test circuit breaker status reporting."""

    def test_get_status_closed(self):
        """Test status when closed."""
        cb = CircuitBreaker(name="test", failure_threshold=5)
        status = cb.get_status()

        assert status["name"] == "test"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["failure_threshold"] == 5

    def test_get_status_open(self):
        """Test status when open."""
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=30)
        cb.record_failure()

        status = cb.get_status()

        assert status["state"] == "open"
        assert status["failure_count"] == 1
        assert status["time_until_recovery"] is not None
        assert status["time_until_recovery"] > 0

    def test_success_resets_failure_count(self):
        """Test success resets failure count."""
        cb = CircuitBreaker(name="test", failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2

        cb.record_success()
        assert cb._failure_count == 0


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry."""

    def test_get_creates_breaker(self):
        """Test registry creates new breakers."""
        registry = CircuitBreakerRegistry()
        cb = registry.get("scanner1")

        assert cb is not None
        assert cb.name == "scanner1"

    def test_get_returns_same_breaker(self):
        """Test registry returns same breaker for same name."""
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("scanner1")
        cb2 = registry.get("scanner1")

        assert cb1 is cb2

    def test_get_different_breakers(self):
        """Test registry creates different breakers for different names."""
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("scanner1")
        cb2 = registry.get("scanner2")

        assert cb1 is not cb2

    def test_get_all_status(self):
        """Test getting status of all breakers."""
        registry = CircuitBreakerRegistry()
        registry.get("scanner1")
        registry.get("scanner2")

        status = registry.get_all_status()

        assert "scanner1" in status
        assert "scanner2" in status

    def test_reset_specific(self):
        """Test resetting specific breaker."""
        registry = CircuitBreakerRegistry(failure_threshold=1)
        cb = registry.get("scanner1")
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        result = registry.reset("scanner1")

        assert result is True
        assert cb.state == CircuitState.CLOSED

    def test_reset_nonexistent(self):
        """Test resetting nonexistent breaker."""
        registry = CircuitBreakerRegistry()
        result = registry.reset("nonexistent")
        assert result is False

    def test_reset_all(self):
        """Test resetting all breakers."""
        registry = CircuitBreakerRegistry(failure_threshold=1)
        cb1 = registry.get("scanner1")
        cb2 = registry.get("scanner2")

        cb1.record_failure()
        cb2.record_failure()

        assert cb1.state == CircuitState.OPEN
        assert cb2.state == CircuitState.OPEN

        registry.reset_all()

        assert cb1.state == CircuitState.CLOSED
        assert cb2.state == CircuitState.CLOSED

    def test_custom_defaults(self):
        """Test registry with custom defaults."""
        registry = CircuitBreakerRegistry(failure_threshold=10, recovery_timeout=60.0)
        cb = registry.get("scanner1")

        assert cb.failure_threshold == 10
        assert cb.recovery_timeout == 60.0


class TestCircuitOpenError:
    """Test circuit open error."""

    def test_error_message(self):
        """Test error includes message."""
        error = CircuitOpenError("Circuit open for scanner1", circuit_name="scanner1")
        assert "Circuit open" in str(error)
        assert error.circuit_name == "scanner1"


class TestMetricsIntegration:
    """Test Prometheus metrics integration."""

    def test_state_metric_updated(self):
        """Test state metric is updated on transitions."""
        from core.circuit_breaker import circuit_state_gauge

        cb = CircuitBreaker(
            name="metrics_test", failure_threshold=1, recovery_timeout=0.1
        )

        # Initial closed state
        assert (
            circuit_state_gauge.labels(scanner_instance="metrics_test")._value.get()
            == 0
        )

        # Open
        cb.record_failure()
        assert (
            circuit_state_gauge.labels(scanner_instance="metrics_test")._value.get()
            == 1
        )

        # Half-open
        time.sleep(0.15)
        _ = cb.state  # Trigger check
        assert (
            circuit_state_gauge.labels(scanner_instance="metrics_test")._value.get()
            == 2
        )

    def test_failure_counter_incremented(self):
        """Test failure counter incremented."""
        from core.circuit_breaker import circuit_failures_total

        cb = CircuitBreaker(name="counter_test", failure_threshold=5)
        initial = circuit_failures_total.labels(
            scanner_instance="counter_test"
        )._value.get()

        cb.record_failure()

        final = circuit_failures_total.labels(
            scanner_instance="counter_test"
        )._value.get()
        assert final == initial + 1

    def test_opens_counter_incremented(self):
        """Test opens counter incremented when circuit opens."""
        from core.circuit_breaker import circuit_opens_total

        cb = CircuitBreaker(name="opens_test", failure_threshold=1)
        initial = circuit_opens_total.labels(scanner_instance="opens_test")._value.get()

        cb.record_failure()  # This opens the circuit

        final = circuit_opens_total.labels(scanner_instance="opens_test")._value.get()
        assert final == initial + 1


class TestConcurrency:
    """Test thread safety."""

    def test_concurrent_access(self):
        """Test circuit breaker handles concurrent access."""
        import threading

        cb = CircuitBreaker(name="concurrent_test", failure_threshold=100)
        errors = []

        def record_failures():
            try:
                for _ in range(50):
                    cb.record_failure()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_failures) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cb._failure_count == 200
