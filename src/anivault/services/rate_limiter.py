"""Token Bucket Rate Limiter implementation.

This module provides a thread-safe token bucket rate limiter for controlling
request rates to external APIs, particularly the TMDB API.
"""

import threading
import time


class TokenBucketRateLimiter:
    """Thread-safe token bucket rate limiter.

    This class implements a token bucket algorithm to control the rate of
    requests to external APIs. It maintains a bucket of tokens that are
    consumed with each request and refilled at a constant rate.

    Args:
        capacity: Maximum number of tokens the bucket can hold (default: 35)
        refill_rate: Number of tokens to add per second (default: 35)
    """

    def __init__(self, capacity: int = 35, refill_rate: float = 35.0):
        """Initialize the token bucket rate limiter.

        Args:
            capacity: Maximum number of tokens the bucket can hold
            refill_rate: Number of tokens to add per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time since last refill.

        This method calculates the number of tokens to add based on the
        elapsed time and refill rate, ensuring the token count doesn't
        exceed the bucket's capacity.
        """
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate

        if tokens_to_add > 0:
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens from the bucket.

        This method attempts to acquire the specified number of tokens
        from the bucket. If sufficient tokens are available, they are
        consumed and True is returned. Otherwise, False is returned.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            True if tokens were successfully acquired, False otherwise
        """
        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def get_tokens_available(self) -> int:
        """Get the current number of tokens available in the bucket.

        Returns:
            Number of tokens currently available
        """
        with self._lock:
            self._refill()
            return int(self.tokens)

    def reset(self) -> None:
        """Reset the bucket to its full capacity.

        This method resets the token count to the bucket's capacity
        and updates the last refill time to the current time.
        """
        with self._lock:
            self.tokens = self.capacity
            self.last_refill = time.time()
