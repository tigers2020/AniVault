"""Semaphore Manager for concurrency control.

This module provides a semaphore manager to limit the number of concurrent
requests sent to external APIs, preventing overwhelming the API and helping
manage application resources.
"""

from __future__ import annotations

import logging
import threading
import types

from typing_extensions import Self

from anivault.shared.constants import NetworkConfig
from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext
from anivault.shared.logging import log_operation_error, log_operation_success

logger = logging.getLogger(__name__)


class SemaphoreManager:
    """Semaphore manager for controlling concurrent API requests.

    This class provides a thread-safe way to limit the number of concurrent
    requests to external APIs. It uses a semaphore to control access and
    can be used as a context manager for automatic resource management.

    Args:
        concurrency_limit: Maximum number of concurrent requests allowed (default: 4)
    """

    def __init__(
        self,
        concurrency_limit: int = NetworkConfig.DEFAULT_CONCURRENT_REQUESTS,
    ):
        """Initialize the semaphore manager.

        Args:
            concurrency_limit: Maximum number of concurrent requests allowed

        Raises:
            ApplicationError: If concurrency_limit is invalid
        """
        context = ErrorContext(
            operation="semaphore_manager_init",
            additional_data={"concurrency_limit": concurrency_limit},
        )

        try:
            if concurrency_limit <= 0:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Concurrency limit must be positive, got: {concurrency_limit}",
                    context=context,
                )

            self.concurrency_limit = concurrency_limit
            self._semaphore = threading.Semaphore(concurrency_limit)
            self._lock = threading.Lock()
            self._active_count = 0

            log_operation_success(
                logger=logger,
                operation="semaphore_manager_init",
                duration_ms=0,
                context=context.additional_data,
            )

        except ApplicationError:
            # Re-raise ApplicationError as-is
            raise
        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Failed to initialize semaphore manager: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="semaphore_manager_init",
                error=error,
                additional_context=context.additional_data,
            )
            raise error from e

    def acquire(self, timeout: float | None = 30.0) -> bool:
        """Acquire the semaphore with optional timeout.

        This method attempts to acquire the semaphore, blocking until
        it becomes available or the timeout expires.

        Args:
            timeout: Maximum time to wait for semaphore acquisition in seconds.
                    If None, blocks indefinitely. Default: 30.0 seconds.

        Returns:
            True if semaphore was acquired successfully, False if timeout occurred

        Raises:
            ApplicationError: If semaphore acquisition fails
        """
        context = ErrorContext(
            operation="semaphore_acquire",
            additional_data={
                "concurrency_limit": self.concurrency_limit,
                "timeout": timeout,
                "active_count": self._active_count,
            },
        )

        try:
            if timeout is not None and timeout < 0:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Timeout must be non-negative, got: {timeout}",
                    context=context,
                )

            acquired = self._semaphore.acquire(timeout=timeout)

            if acquired:
                with self._lock:
                    self._active_count += 1

            log_operation_success(
                logger=logger,
                operation="semaphore_acquire",
                duration_ms=0,
                context={**(context.additional_data or {}), "acquired": acquired},
            )

            return acquired

        except ApplicationError:
            # Re-raise ApplicationError as-is
            raise
        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.CONCURRENCY_ERROR,
                message=f"Failed to acquire semaphore: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="semaphore_acquire",
                error=error,
                additional_context=context.additional_data,
            )
            raise error from e

    def release(self) -> None:
        """Release the semaphore.

        This method releases a previously acquired semaphore, making it
        available for other threads to acquire.

        Raises:
            ApplicationError: If semaphore release fails
        """
        context = ErrorContext(
            operation="semaphore_release",
            additional_data={
                "concurrency_limit": self.concurrency_limit,
                "active_count": self._active_count,
            },
        )

        try:
            with self._lock:
                if self._active_count > 0:
                    self._active_count -= 1

            self._semaphore.release()

            log_operation_success(
                logger=logger,
                operation="semaphore_release",
                duration_ms=0,
                context=context.additional_data,
            )

        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.CONCURRENCY_ERROR,
                message=f"Failed to release semaphore: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="semaphore_release",
                error=error,
                additional_context=context.additional_data,
            )
            raise error from e

    def __enter__(self) -> Self:
        """Enter the context manager.

        Returns:
            Self for use in context manager

        Raises:
            ApplicationError: If semaphore acquisition fails within timeout
        """
        context = ErrorContext(
            operation="semaphore_acquire",
            additional_data={"concurrency_limit": self.concurrency_limit},
        )

        if not self.acquire():
            error = ApplicationError(
                code=ErrorCode.RESOURCE_UNAVAILABLE,
                message="Failed to acquire semaphore within timeout",
                context=context,
            )
            log_operation_error(
                logger=logger,
                operation="semaphore_acquire",
                error=error,
                additional_context=context.additional_data,
            )
            raise error

        log_operation_success(
            logger=logger,
            operation="semaphore_acquire",
            duration_ms=0,
            context=context.additional_data,
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit the context manager.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        context = ErrorContext(
            operation="semaphore_release",
            additional_data={"concurrency_limit": self.concurrency_limit},
        )

        try:
            self.release()
            log_operation_success(
                logger=logger,
                operation="semaphore_release",
                duration_ms=0,
                context=context.additional_data,
            )
        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.RESOURCE_CLEANUP_ERROR,
                message="Failed to release semaphore",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="semaphore_release",
                error=error,
                additional_context=context.additional_data,
            )
            # Don't re-raise here as it's in __exit__

    async def __aenter__(self) -> Self:
        """Enter the async context manager.

        Returns:
            Self for use in async context manager

        Raises:
            ApplicationError: If semaphore acquisition fails within timeout
        """
        context = ErrorContext(
            operation="semaphore_acquire",
            additional_data={"concurrency_limit": self.concurrency_limit},
        )

        if not self.acquire():
            error = ApplicationError(
                code=ErrorCode.RESOURCE_UNAVAILABLE,
                message="Failed to acquire semaphore within timeout",
                context=context,
            )
            log_operation_error(
                logger=logger,
                operation="semaphore_acquire",
                error=error,
                additional_context=context.additional_data,
            )
            raise error

        log_operation_success(
            logger=logger,
            operation="semaphore_acquire",
            duration_ms=0,
            context=context.additional_data,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit the async context manager.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        context = ErrorContext(
            operation="semaphore_release",
            additional_data={"concurrency_limit": self.concurrency_limit},
        )

        try:
            self.release()
            log_operation_success(
                logger=logger,
                operation="semaphore_release",
                duration_ms=0,
                context=context.additional_data,
            )
        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.RESOURCE_CLEANUP_ERROR,
                message="Failed to release semaphore",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="semaphore_release",
                error=error,
                additional_context=context.additional_data,
            )
            # Don't re-raise here as it's in __aexit__

    def get_active_count(self) -> int:
        """Get the current number of active requests.

        Returns:
            Number of currently active requests

        Raises:
            ApplicationError: If active count retrieval fails
        """
        context = ErrorContext(
            operation="semaphore_get_active_count",
            additional_data={"concurrency_limit": self.concurrency_limit},
        )

        try:
            with self._lock:
                return self._active_count

        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.CONCURRENCY_ERROR,
                message=f"Failed to get active count: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="semaphore_get_active_count",
                error=error,
                additional_context=context.additional_data,
            )
            raise error from e

    def get_available_count(self) -> int:
        """Get the number of available semaphore slots.

        Returns:
            Number of available semaphore slots

        Raises:
            ApplicationError: If available count retrieval fails
        """
        context = ErrorContext(
            operation="semaphore_get_available_count",
            additional_data={"concurrency_limit": self.concurrency_limit},
        )

        try:
            return self._semaphore._value

        except Exception as e:
            error = ApplicationError(
                code=ErrorCode.CONCURRENCY_ERROR,
                message=f"Failed to get available count: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="semaphore_get_available_count",
                error=error,
                additional_context=context.additional_data,
            )
            raise error from e
