"""Unit tests for TokenBucketRateLimiter."""

import time
import threading
from unittest.mock import patch

import pytest

from anivault.services.rate_limiter import TokenBucketRateLimiter


class TestTokenBucketRateLimiter:
    """Test cases for TokenBucketRateLimiter."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=5.0)

        assert limiter.capacity == 10
        assert limiter.refill_rate == 5.0
        assert limiter.tokens == 10
        assert limiter.get_tokens_available() == 10

    def test_initialization_defaults(self):
        """Test rate limiter initialization with default values."""
        limiter = TokenBucketRateLimiter()

        assert limiter.capacity == 35
        assert limiter.refill_rate == 35.0
        assert limiter.tokens == 35

    def test_try_acquire_success(self):
        """Test successful token acquisition."""
        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=10.0)

        # Should succeed when tokens are available
        assert limiter.try_acquire() is True
        assert limiter.get_tokens_available() == 4

        # Should succeed multiple times
        assert limiter.try_acquire(2) is True
        assert limiter.get_tokens_available() == 2

    def test_try_acquire_failure(self):
        """Test failed token acquisition when no tokens available."""
        limiter = TokenBucketRateLimiter(capacity=2, refill_rate=1.0)

        # Acquire all tokens
        assert limiter.try_acquire(2) is True
        assert limiter.get_tokens_available() == 0

        # Should fail when no tokens available
        assert limiter.try_acquire() is False
        assert limiter.get_tokens_available() == 0

    def test_token_refill(self):
        """Test token refill over time."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=10.0)

        # Acquire all tokens
        assert limiter.try_acquire(10) is True
        assert limiter.get_tokens_available() == 0

        # Wait for refill
        time.sleep(0.2)  # Should refill 2 tokens

        # Should now have tokens available
        assert limiter.try_acquire() is True
        assert limiter.get_tokens_available() >= 1

    def test_token_refill_capacity_limit(self):
        """Test that token refill doesn't exceed capacity."""
        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=100.0)

        # Wait for refill
        time.sleep(0.1)  # Should refill 10 tokens, but capped at 5

        # Should not exceed capacity
        assert limiter.get_tokens_available() == 5

    def test_reset(self):
        """Test rate limiter reset."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=5.0)

        # Acquire some tokens
        limiter.try_acquire(3)
        assert limiter.get_tokens_available() == 7

        # Reset
        limiter.reset()
        assert limiter.get_tokens_available() == 10

    def test_thread_safety(self):
        """Test thread safety of rate limiter."""
        limiter = TokenBucketRateLimiter(capacity=100, refill_rate=100.0)
        results = []

        def worker():
            for _ in range(10):
                if limiter.try_acquire():
                    results.append(1)
                time.sleep(0.001)

        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(10)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have acquired exactly 100 tokens
        assert sum(results) == 100

    def test_concurrent_refill_and_acquire(self):
        """Test concurrent token refill and acquisition."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=100.0)

        # Acquire all tokens initially
        assert limiter.try_acquire(10) is True

        results = []

        def worker():
            for _ in range(5):
                if limiter.try_acquire():
                    results.append(1)
                time.sleep(0.01)

        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(2)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have acquired some tokens due to refill
        assert len(results) > 0
        assert len(results) <= 10  # Should not exceed capacity

    def test_negative_tokens_requested(self):
        """Test behavior when negative tokens are requested."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=5.0)

        # Should handle negative tokens gracefully
        assert limiter.try_acquire(-1) is True
        assert limiter.get_tokens_available() == 10  # Should not change

    def test_zero_tokens_requested(self):
        """Test behavior when zero tokens are requested."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=5.0)

        # Should succeed when zero tokens are requested
        assert limiter.try_acquire(0) is True
        assert limiter.get_tokens_available() == 10  # Should not change
