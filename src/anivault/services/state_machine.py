"""Rate Limiting State Machine implementation.

This module provides a state machine to manage the operational state of the
TMDB client based on API feedback, particularly for handling rate limits and errors.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from enum import Enum
from typing import Any


class RateLimitState(Enum):
    """Rate limiting states for the TMDB client."""

    NORMAL = "normal"
    THROTTLE = "throttle"
    SLEEP_THEN_RESUME = "sleep_then_resume"
    CACHE_ONLY = "cache_only"


class RateLimitStateMachine:
    """State machine for managing TMDB client rate limiting and error handling.

    This class manages the operational state of the TMDB client based on API
    responses, implementing circuit breaker patterns and automatic recovery
    mechanisms for rate limiting scenarios.

    Args:
        error_threshold: Percentage of errors (429/5xx) to trigger circuit breaker (default: 60)
        time_window: Time window in seconds for error rate calculation (default: 300)
        max_retry_after: Maximum retry-after delay in seconds (default: 300)
    """

    def __init__(
        self,
        error_threshold: float = 60.0,
        time_window: int = 300,
        max_retry_after: int = 300,
    ):
        """Initialize the rate limiting state machine.

        Args:
            error_threshold: Percentage of errors to trigger circuit breaker
            time_window: Time window in seconds for error rate calculation
            max_retry_after: Maximum retry-after delay in seconds
        """
        self.error_threshold = error_threshold
        self.time_window = time_window
        self.max_retry_after = max_retry_after

        self._state = RateLimitState.NORMAL
        self._lock = threading.Lock()
        self._error_timestamps = deque()
        self._success_timestamps = deque()
        self._last_429_time = 0.0
        self._retry_after_delay = 0.0

    @property
    def state(self) -> RateLimitState:
        """Get the current state of the state machine.

        Returns:
            Current rate limiting state
        """
        with self._lock:
            return self._state

    def handle_429(self, retry_after: float | None = None) -> None:
        """Handle a 429 (Too Many Requests) response.

        This method transitions the state machine to handle rate limiting
        scenarios, respecting the Retry-After header if provided.

        Args:
            retry_after: Retry-After header value in seconds
        """
        with self._lock:
            current_time = time.time()
            self._last_429_time = current_time
            self._error_timestamps.append(current_time)

            # Respect Retry-After header, but cap at max_retry_after
            if retry_after is not None:
                self._retry_after_delay = min(retry_after, self.max_retry_after)
            else:
                # Default exponential backoff for 429 without Retry-After
                self._retry_after_delay = min(60.0, self._retry_after_delay * 2)

            # Transition to THROTTLE state
            self._state = RateLimitState.THROTTLE

            # Clean old error timestamps
            self._clean_old_timestamps()

    def handle_success(self) -> None:
        """Handle a successful API response.

        This method records the success and may transition the state machine
        back to NORMAL if conditions are met.
        """
        with self._lock:
            current_time = time.time()
            self._success_timestamps.append(current_time)

            # Clean old timestamps
            self._clean_old_timestamps()

            # Check if we should transition back to NORMAL
            if self._state == RateLimitState.THROTTLE:
                # Check if enough time has passed since last 429
                if current_time - self._last_429_time >= self._retry_after_delay:
                    self._state = RateLimitState.NORMAL
                    self._retry_after_delay = 0.0
            elif self._state == RateLimitState.SLEEP_THEN_RESUME:
                # Transition from SLEEP_THEN_RESUME to NORMAL
                self._state = RateLimitState.NORMAL

    def handle_error(self, status_code: int) -> None:
        """Handle an error response.

        This method processes error responses and may trigger circuit breaker
        logic if the error rate exceeds the threshold.

        Args:
            status_code: HTTP status code of the error response
        """
        with self._lock:
            current_time = time.time()
            self._error_timestamps.append(current_time)

            # Clean old timestamps
            self._clean_old_timestamps()

            # Check circuit breaker condition
            if self._should_trigger_circuit_breaker():
                self._state = RateLimitState.CACHE_ONLY
            elif status_code == 429:
                self.handle_429()

    def should_make_request(self) -> bool:
        """Check if a request should be made based on current state.

        Returns:
            True if a request should be made, False otherwise
        """
        with self._lock:
            if self._state == RateLimitState.CACHE_ONLY:
                return False

            if self._state == RateLimitState.THROTTLE:
                # Check if enough time has passed since last 429
                current_time = time.time()
                return current_time - self._last_429_time >= self._retry_after_delay

            return True

    def get_retry_delay(self) -> float:
        """Get the recommended retry delay based on current state.

        Returns:
            Recommended retry delay in seconds
        """
        with self._lock:
            if self._state == RateLimitState.THROTTLE:
                current_time = time.time()
                remaining_delay = self._retry_after_delay - (
                    current_time - self._last_429_time
                )
                return max(0.0, remaining_delay)

            return 0.0

    def reset(self) -> None:
        """Reset the state machine to NORMAL state.

        This method clears all error tracking and resets the state to NORMAL.
        """
        with self._lock:
            self._state = RateLimitState.NORMAL
            self._error_timestamps.clear()
            self._success_timestamps.clear()
            self._last_429_time = 0.0
            self._retry_after_delay = 0.0

    def _clean_old_timestamps(self) -> None:
        """Clean timestamps older than the time window."""
        current_time = time.time()
        cutoff_time = current_time - self.time_window

        # Clean error timestamps
        while self._error_timestamps and self._error_timestamps[0] < cutoff_time:
            self._error_timestamps.popleft()

        # Clean success timestamps
        while self._success_timestamps and self._success_timestamps[0] < cutoff_time:
            self._success_timestamps.popleft()

    def _should_trigger_circuit_breaker(self) -> bool:
        """Check if the circuit breaker should be triggered.

        Returns:
            True if circuit breaker should be triggered
        """
        if not self._error_timestamps:
            return False

        # Count errors in the time window
        error_count = len(self._error_timestamps)
        success_count = len(self._success_timestamps)
        total_requests = error_count + success_count

        if total_requests < 10:  # Need minimum requests for reliable calculation
            return False

        error_rate = (error_count / total_requests) * 100
        return error_rate >= self.error_threshold

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics about the state machine.

        Returns:
            Dictionary containing state machine statistics
        """
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - self.time_window

            recent_errors = sum(1 for ts in self._error_timestamps if ts >= cutoff_time)
            recent_successes = sum(
                1 for ts in self._success_timestamps if ts >= cutoff_time
            )
            total_recent = recent_errors + recent_successes

            error_rate = (
                (recent_errors / total_recent * 100) if total_recent > 0 else 0.0
            )

            return {
                "state": self._state.value,
                "recent_errors": recent_errors,
                "recent_successes": recent_successes,
                "error_rate_percent": error_rate,
                "retry_delay": self.get_retry_delay(),
                "last_429_time": self._last_429_time,
            }
