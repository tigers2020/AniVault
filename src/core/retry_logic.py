"""
Retry logic module for database operations with exponential backoff.

This module provides robust retry mechanisms for transient database failures,
including automatic retry logic with exponential backoff, jitter, and
comprehensive error detection for SQLAlchemy operations.

Author: AniVault Development Team
Created: 2025-01-19
"""

import logging
import random
from typing import Any, Callable, Optional, Set, Type, Union
from functools import wraps

from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
    retry_if_exception,
    RetryError,
    RetryCallState,
)
from sqlalchemy.exc import (
    OperationalError,
    DisconnectionError,
    InterfaceError,
    TimeoutError,
    SQLAlchemyError,
    IntegrityError,
    ProgrammingError,
    DataError,
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Constants for retry configuration
DEFAULT_MAX_ATTEMPTS = 7
DEFAULT_MIN_WAIT = 0.5
DEFAULT_MAX_WAIT = 30.0
DEFAULT_MULTIPLIER = 1.0
DEFAULT_JITTER = True

# Retriable database exceptions
RETRIABLE_DB_EXCEPTIONS = (
    OperationalError,
    DisconnectionError,
    InterfaceError,
    TimeoutError,
)

# Non-retriable database exceptions (fail fast)
NON_RETRIABLE_DB_EXCEPTIONS = (
    IntegrityError,
    ProgrammingError,
    DataError,
)


class RetryConfiguration:
    """Configuration class for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        min_wait: float = DEFAULT_MIN_WAIT,
        max_wait: float = DEFAULT_MAX_WAIT,
        multiplier: float = DEFAULT_MULTIPLIER,
        jitter: bool = DEFAULT_JITTER,
        retriable_exceptions: Optional[Set[Type[Exception]]] = None,
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            min_wait: Minimum wait time between retries in seconds
            max_wait: Maximum wait time between retries in seconds
            multiplier: Exponential backoff multiplier
            jitter: Whether to add jitter to wait times
            retriable_exceptions: Set of exception types that should trigger retries
        """
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.multiplier = multiplier
        self.jitter = jitter
        self.retriable_exceptions = retriable_exceptions or set(RETRIABLE_DB_EXCEPTIONS)


def is_transient_db_error(exception: Exception) -> bool:
    """
    Check if an exception is a transient database error that should trigger a retry.
    
    Args:
        exception: The exception to check
        
    Returns:
        True if the exception is transient and should trigger a retry
    """
    # Check if it's one of the common retriable exception types
    if isinstance(exception, RETRIABLE_DB_EXCEPTIONS):
        return True
    
    # Check for specific error messages or codes within a broader SQLAlchemyError
    if isinstance(exception, SQLAlchemyError) and hasattr(exception, 'orig') and exception.orig is not None:
        error_message = str(exception.orig).lower()
        
        # Check for specific transient error patterns
        transient_patterns = [
            "deadlock detected",
            "could not serialize access due to concurrent update",
            "connection reset by peer",
            "connection timed out",
            "temporary failure",
            "resource temporarily unavailable",
            "too many connections",
            "connection pool exhausted",
        ]
        
        for pattern in transient_patterns:
            if pattern in error_message:
                return True
    
    return False


def is_non_retriable_error(exception: Exception) -> bool:
    """
    Check if an exception is a non-retriable error that should fail fast.
    
    Args:
        exception: The exception to check
        
    Returns:
        True if the exception is non-retriable and should fail immediately
    """
    return isinstance(exception, NON_RETRIABLE_DB_EXCEPTIONS)


def create_retry_decorator(config: Optional[RetryConfiguration] = None) -> Callable:
    """
    Create a retry decorator with the specified configuration.
    
    Args:
        config: Retry configuration, uses defaults if None
        
    Returns:
        Decorator function for retry logic
    """
    if config is None:
        config = RetryConfiguration()
    
    def retry_predicate(exception: Exception) -> bool:
        """Predicate function to determine if an exception should trigger a retry."""
        # Don't retry non-retriable errors
        if is_non_retriable_error(exception):
            return False
        
        # Retry if it's a known retriable exception type
        if isinstance(exception, tuple(config.retriable_exceptions)):
            return True
        
        # Retry if it matches transient error patterns
        return is_transient_db_error(exception)
    
    return retry(
        wait=wait_exponential(
            multiplier=config.multiplier,
            min=config.min_wait,
            max=config.max_wait,
        ),
        stop=stop_after_attempt(config.max_attempts),
        retry=retry_if_exception(retry_predicate),
        before_sleep=before_sleep_log(logger, logging.WARNING, exc_info=True),
        after=after_log(logger, logging.INFO),
        reraise=True,
    )


# Default retry decorator for database operations
db_retry = create_retry_decorator()


def retry_database_operation(
    config: Optional[RetryConfiguration] = None,
    operation_name: Optional[str] = None,
):
    """
    Decorator for database operations with retry logic.
    
    This decorator should be used to wrap database operations that might
    fail due to transient errors. It automatically retries the operation
    with exponential backoff.
    
    Args:
        config: Retry configuration, uses defaults if None
        operation_name: Name of the operation for logging purposes
        
    Example:
        @retry_database_operation(operation_name="save_metadata")
        def save_metadata(session: Session, data: dict) -> bool:
            # Database operation here
            pass
    """
    def decorator(func: Callable) -> Callable:
        retry_decorator = create_retry_decorator(config)
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or func.__name__
            logger.debug(f"Starting database operation: {op_name}")
            
            try:
                result = retry_decorator(func)(*args, **kwargs)
                logger.debug(f"Successfully completed database operation: {op_name}")
                return result
            except RetryError as e:
                logger.error(
                    f"Database operation failed after all retries: {op_name}. "
                    f"Last exception: {e.last_attempt.exception()}"
                )
                raise e.last_attempt.exception()
            except Exception as e:
                logger.error(f"Database operation failed with non-retriable error: {op_name}. Error: {e}")
                raise
        
        return wrapper
    return decorator


def retry_with_fresh_session(
    session_factory: Callable[[], Session],
    config: Optional[RetryConfiguration] = None,
    operation_name: Optional[str] = None,
):
    """
    Decorator that ensures each retry attempt uses a fresh database session.
    
    This is particularly important for SQLAlchemy operations where a failed
    session might be in an invalid state and should not be reused.
    
    Args:
        session_factory: Function that creates a new database session
        config: Retry configuration, uses defaults if None
        operation_name: Name of the operation for logging purposes
        
    Example:
        @retry_with_fresh_session(
            session_factory=lambda: SessionLocal(),
            operation_name="bulk_insert_metadata"
        )
        def bulk_insert_metadata(data_list: list) -> int:
            with session_factory() as session:
                # Database operations here
                pass
    """
    def decorator(func: Callable) -> Callable:
        retry_decorator = create_retry_decorator(config)
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or func.__name__
            logger.debug(f"Starting database operation with fresh sessions: {op_name}")
            
            def operation_with_fresh_session():
                """Execute the operation with a fresh session."""
                with session_factory() as session:
                    # Pass the session as the first argument if the function expects it
                    if 'session' in func.__code__.co_varnames:
                        return func(session, *args, **kwargs)
                    else:
                        return func(*args, **kwargs)
            
            try:
                result = retry_decorator(operation_with_fresh_session)()
                logger.debug(f"Successfully completed database operation: {op_name}")
                return result
            except RetryError as e:
                logger.error(
                    f"Database operation failed after all retries: {op_name}. "
                    f"Last exception: {e.last_attempt.exception()}"
                )
                raise e.last_attempt.exception()
            except Exception as e:
                logger.error(f"Database operation failed with non-retriable error: {op_name}. Error: {e}")
                raise
        
        return wrapper
    return decorator


class RetryStatistics:
    """Statistics tracking for retry operations."""
    
    def __init__(self):
        self.total_attempts = 0
        self.successful_retries = 0
        self.failed_after_retries = 0
        self.non_retriable_failures = 0
    
    def record_attempt(self):
        """Record a retry attempt."""
        self.total_attempts += 1
    
    def record_successful_retry(self):
        """Record a successful retry."""
        self.successful_retries += 1
    
    def record_failed_after_retries(self):
        """Record a failure after all retries were exhausted."""
        self.failed_after_retries += 1
    
    def record_non_retriable_failure(self):
        """Record a non-retriable failure."""
        self.non_retriable_failures += 1
    
    def get_stats(self) -> dict:
        """Get current statistics."""
        return {
            'total_attempts': self.total_attempts,
            'successful_retries': self.successful_retries,
            'failed_after_retries': self.failed_after_retries,
            'non_retriable_failures': self.non_retriable_failures,
            'success_rate': (
                (self.total_attempts - self.failed_after_retries - self.non_retriable_failures) 
                / max(self.total_attempts, 1) * 100
            ),
        }


# Global statistics instance
retry_stats = RetryStatistics()


def get_retry_statistics() -> dict:
    """
    Get current retry statistics.
    
    Returns:
        Dictionary containing retry statistics
    """
    return retry_stats.get_stats()


def reset_retry_statistics():
    """Reset retry statistics."""
    global retry_stats
    retry_stats = RetryStatistics()
