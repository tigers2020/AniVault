"""Token Bucket Rate Limiter implementation.

This module provides a thread-safe token bucket rate limiter for controlling
request rates to external APIs, particularly the TMDB API.
"""

import logging
import threading
import time

from anivault.shared.constants import NetworkConfig
from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext
from anivault.shared.logging import log_operation_error, log_operation_success

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """Thread-safe token bucket rate limiter.

    This class implements a token bucket algorithm to control the rate of
    requests to external APIs. It maintains a bucket of tokens that are
    consumed with each request and refilled at a constant rate.

    Args:
        capacity: Maximum number of tokens the bucket can hold (default: 35)
        refill_rate: Number of tokens to add per second (default: 35)
    """

    def __init__(
        self,
        capacity: int = NetworkConfig.DEFAULT_TOKEN_BUCKET_CAPACITY,
        refill_rate: float = NetworkConfig.DEFAULT_TOKEN_REFILL_RATE,
    ):
        """Initialize the token bucket rate limiter.

        Args:
            capacity: Maximum number of tokens the bucket can hold
            refill_rate: Number of tokens to add per second

        Raises:
            ApplicationError: If capacity or refill_rate are invalid
        """
        context = ErrorContext(
            operation="rate_limiter_init",
            additional_data={"capacity": capacity, "refill_rate": refill_rate},
        )

        try:
            if capacity <= 0:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Capacity must be positive, got: {capacity}",
                    context=context,
                )

            if refill_rate <= 0:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Refill rate must be positive, got: {refill_rate}",
                    context=context,
                )

            self.capacity = capacity
            self.refill_rate = refill_rate
            self.tokens = float(capacity)
            self.last_refill = time.time()
            self._lock = threading.Lock()

            log_operation_success(
                logger=logger,
                operation="rate_limiter_init",
                duration_ms=0,
                context=context.additional_data,
            )

        except ApplicationError:
            # Re-raise ApplicationError as-is
            raise
        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Failed to initialize rate limiter: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="rate_limiter_init",
                error=error,
                additional_context=context.additional_data,
            )
            raise error from e

    def _refill(self) -> None:
        """Refill tokens based on elapsed time since last refill.

        This method calculates the number of tokens to add based on the
        elapsed time and refill rate, ensuring the token count doesn't
        exceed the bucket's capacity.

        Raises:
            ApplicationError: If refill calculation fails
        """
        context = ErrorContext(
            operation="rate_limiter_refill",
            additional_data={
                "current_tokens": self.tokens,
                "capacity": self.capacity,
                "refill_rate": self.refill_rate,
            },
        )

        try:
            now = time.time()
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * self.refill_rate

            if tokens_to_add > 0:
                self.tokens = min(self.capacity, self.tokens + tokens_to_add)
                self.last_refill = now

        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.RATE_LIMIT_ERROR,
                message=f"Failed to refill tokens: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="rate_limiter_refill",
                error=error,
                additional_context=context.additional_data,
            )
            raise error from e

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens from the bucket.

        This method attempts to acquire the specified number of tokens
        from the bucket. If sufficient tokens are available, they are
        consumed and True is returned. Otherwise, False is returned.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            True if tokens were successfully acquired, False otherwise

        Raises:
            ApplicationError: If token acquisition fails
        """
        context = ErrorContext(
            operation="rate_limiter_acquire",
            additional_data={
                "requested_tokens": tokens,
                "current_tokens": self.tokens,
                "capacity": self.capacity,
            },
        )

        try:
            if tokens <= 0:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Tokens to acquire must be positive, got: {tokens}",
                    context=context,
                )

            if tokens > self.capacity:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Tokens to acquire ({tokens}) exceeds capacity ({self.capacity})",
                    context=context,
                )

            with self._lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    log_operation_success(
                        logger=logger,
                        operation="rate_limiter_acquire",
                        duration_ms=0,
                        context=context.additional_data,
                    )
                    return True

                log_operation_success(
                    logger=logger,
                    operation="rate_limiter_acquire",
                    duration_ms=0,
                    context={
                        **(context.additional_data or {}),
                        "result": "insufficient_tokens",
                    },
                )
                return False

        except ApplicationError:
            # Re-raise ApplicationError as-is
            raise
        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.RATE_LIMIT_ERROR,
                message=f"Failed to acquire tokens: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="rate_limiter_acquire",
                error=error,
                additional_context=context.additional_data,
            )
            raise error from e

    def get_tokens_available(self) -> int:
        """Get the current number of tokens available in the bucket.

        Returns:
            Number of tokens currently available

        Raises:
            ApplicationError: If token count retrieval fails
        """
        context = ErrorContext(
            operation="rate_limiter_get_tokens",
            additional_data={
                "capacity": self.capacity,
                "refill_rate": self.refill_rate,
            },
        )

        try:
            with self._lock:
                self._refill()
                return int(self.tokens)

        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.RATE_LIMIT_ERROR,
                message=f"Failed to get available tokens: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="rate_limiter_get_tokens",
                error=error,
                additional_context=context.additional_data,
            )
            raise error from e

    def reset(self) -> None:
        """Reset the bucket to its full capacity.

        This method resets the token count to the bucket's capacity
        and updates the last refill time to the current time.

        Raises:
            ApplicationError: If reset operation fails
        """
        context = ErrorContext(
            operation="rate_limiter_reset",
            additional_data={
                "capacity": self.capacity,
                "refill_rate": self.refill_rate,
            },
        )

        try:
            with self._lock:
                self.tokens = self.capacity
                self.last_refill = time.time()

            log_operation_success(
                logger=logger,
                operation="rate_limiter_reset",
                duration_ms=0,
                context=context.additional_data,
            )

        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.RATE_LIMIT_ERROR,
                message=f"Failed to reset rate limiter: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="rate_limiter_reset",
                error=error,
                additional_context=context.additional_data,
            )
            raise error from e
