"""Unit tests for RateLimitStateMachine."""

import time
from unittest.mock import patch

import pytest

from anivault.services.state_machine import RateLimitStateMachine, RateLimitState


class TestRateLimitStateMachine:
    """Test cases for RateLimitStateMachine."""

    def test_initialization(self):
        """Test state machine initialization."""
        sm = RateLimitStateMachine(
            error_threshold=70.0, time_window=300, max_retry_after=600
        )

        assert sm.error_threshold == 70.0
        assert sm.time_window == 300
        assert sm.max_retry_after == 600
        assert sm.state == RateLimitState.NORMAL

    def test_initialization_defaults(self):
        """Test state machine initialization with default values."""
        sm = RateLimitStateMachine()

        assert sm.error_threshold == 60.0
        assert sm.time_window == 300
        assert sm.max_retry_after == 300
        assert sm.state == RateLimitState.NORMAL

    def test_handle_429_with_retry_after(self):
        """Test handling 429 error with Retry-After header."""
        sm = RateLimitStateMachine()

        # Handle 429 with Retry-After
        sm.handle_429(retry_after=5.0)

        assert sm.state == RateLimitState.THROTTLE
        assert sm.get_retry_delay() > 0

    def test_handle_429_without_retry_after(self):
        """Test handling 429 error without Retry-After header."""
        sm = RateLimitStateMachine()

        # Handle 429 without Retry-After
        sm.handle_429()

        assert sm.state == RateLimitState.THROTTLE
        assert sm.get_retry_delay() > 0

    def test_handle_429_max_retry_after(self):
        """Test handling 429 with Retry-After exceeding max."""
        sm = RateLimitStateMachine(max_retry_after=10)

        # Handle 429 with Retry-After exceeding max
        sm.handle_429(retry_after=20.0)

        assert sm.state == RateLimitState.THROTTLE
        assert sm.get_retry_delay() <= 10.0

    def test_handle_success_from_throttle(self):
        """Test handling success from THROTTLE state."""
        sm = RateLimitStateMachine()

        # First handle 429
        sm.handle_429(retry_after=1.0)
        assert sm.state == RateLimitState.THROTTLE

        # Wait for retry delay to pass
        time.sleep(1.1)

        # Handle success
        sm.handle_success()
        assert sm.state == RateLimitState.NORMAL

    def test_handle_success_from_sleep_then_resume(self):
        """Test handling success from SLEEP_THEN_RESUME state."""
        sm = RateLimitStateMachine()

        # First handle 429
        sm.handle_429(retry_after=1.0)
        assert sm.state == RateLimitState.THROTTLE

        # Handle success (should transition to NORMAL)
        sm.handle_success()
        assert sm.state == RateLimitState.NORMAL

    def test_handle_error_5xx(self):
        """Test handling 5xx server errors."""
        sm = RateLimitStateMachine()

        # Handle 500 error
        sm.handle_error(500)

        # Should still be in NORMAL state (not enough errors for circuit breaker)
        assert sm.state == RateLimitState.NORMAL

    def test_handle_error_4xx(self):
        """Test handling 4xx client errors."""
        sm = RateLimitStateMachine()

        # Handle 400 error
        sm.handle_error(400)

        # Should still be in NORMAL state
        assert sm.state == RateLimitState.NORMAL

    def test_circuit_breaker_activation(self):
        """Test circuit breaker activation under high error rate."""
        sm = RateLimitStateMachine(error_threshold=50.0, time_window=60)

        # Generate many errors to trigger circuit breaker
        for _ in range(10):
            sm.handle_error(500)

        # Add some successes
        for _ in range(5):
            sm.handle_success()

        # Should trigger circuit breaker
        assert sm.state == RateLimitState.CACHE_ONLY

    def test_should_make_request_normal(self):
        """Test should_make_request in NORMAL state."""
        sm = RateLimitStateMachine()

        assert sm.should_make_request() is True

    def test_should_make_request_throttle(self):
        """Test should_make_request in THROTTLE state."""
        sm = RateLimitStateMachine()

        # Handle 429
        sm.handle_429(retry_after=1.0)
        assert sm.state == RateLimitState.THROTTLE

        # Should not make request immediately
        assert sm.should_make_request() is False

        # Wait for retry delay
        time.sleep(1.1)

        # Should now make request
        assert sm.should_make_request() is True

    def test_should_make_request_cache_only(self):
        """Test should_make_request in CACHE_ONLY state."""
        sm = RateLimitStateMachine()

        # Trigger circuit breaker
        for _ in range(10):
            sm.handle_error(500)

        assert sm.state == RateLimitState.CACHE_ONLY
        assert sm.should_make_request() is False

    def test_get_retry_delay(self):
        """Test get_retry_delay method."""
        sm = RateLimitStateMachine()

        # In NORMAL state, should be 0
        assert sm.get_retry_delay() == 0.0

        # Handle 429
        sm.handle_429(retry_after=2.0)
        assert sm.get_retry_delay() > 0.0

        # Wait for delay to pass
        time.sleep(2.1)
        assert sm.get_retry_delay() == 0.0

    def test_reset(self):
        """Test state machine reset."""
        sm = RateLimitStateMachine()

        # Generate some state
        sm.handle_429(retry_after=5.0)
        sm.handle_error(500)

        # Reset
        sm.reset()

        assert sm.state == RateLimitState.NORMAL
        assert sm.get_retry_delay() == 0.0

    def test_get_stats(self):
        """Test get_stats method."""
        sm = RateLimitStateMachine()

        # Get initial stats
        stats = sm.get_stats()

        assert "state" in stats
        assert "recent_errors" in stats
        assert "recent_successes" in stats
        assert "error_rate_percent" in stats
        assert "retry_delay" in stats
        assert "last_429_time" in stats

        assert stats["state"] == "normal"
        assert stats["recent_errors"] == 0
        assert stats["recent_successes"] == 0
        assert stats["error_rate_percent"] == 0.0
        assert stats["retry_delay"] == 0.0

    def test_get_stats_with_activity(self):
        """Test get_stats with some activity."""
        sm = RateLimitStateMachine()

        # Generate some activity
        sm.handle_success()
        sm.handle_error(500)
        sm.handle_429(retry_after=1.0)

        stats = sm.get_stats()

        assert stats["recent_errors"] >= 1
        assert stats["recent_successes"] >= 1
        assert stats["error_rate_percent"] > 0.0
        assert stats["retry_delay"] > 0.0

    def test_clean_old_timestamps(self):
        """Test cleaning of old timestamps."""
        sm = RateLimitStateMachine(time_window=1)  # 1 second window

        # Generate some activity
        sm.handle_success()
        sm.handle_error(500)

        # Wait for timestamps to become old
        time.sleep(1.1)

        # Generate new activity
        sm.handle_success()

        stats = sm.get_stats()

        # Should only have recent activity
        assert stats["recent_errors"] == 0  # Old error should be cleaned
        assert stats["recent_successes"] == 1  # Only recent success

    def test_thread_safety(self):
        """Test thread safety of state machine."""
        import threading

        sm = RateLimitStateMachine()
        results = []

        def worker():
            for _ in range(10):
                sm.handle_success()
                sm.handle_error(500)
                results.append(sm.state.value)

        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(3)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have some results
        assert len(results) > 0

        # All results should be valid states
        valid_states = {state.value for state in RateLimitState}
        assert all(result in valid_states for result in results)

    def test_error_threshold_edge_cases(self):
        """Test error threshold edge cases."""
        sm = RateLimitStateMachine(error_threshold=100.0)  # 100% threshold

        # Generate only errors
        for _ in range(10):
            sm.handle_error(500)

        # Should trigger circuit breaker
        assert sm.state == RateLimitState.CACHE_ONLY

        # Reset and test 0% threshold
        sm.reset()
        sm.error_threshold = 0.0

        # Generate one error
        sm.handle_error(500)

        # Should trigger circuit breaker immediately
        assert sm.state == RateLimitState.CACHE_ONLY
