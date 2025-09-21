"""Logging utilities for consistent logging across all levels (debug, info, warning, error)."""

import logging
from typing import Any, Optional, Union, Iterable
from functools import wraps

logger = logging.getLogger(__name__)


def log_operation_error(operation_name: str, error: Exception, additional_context: Optional[str] = None) -> None:
    """Log operation errors with consistent formatting.
    
    Args:
        operation_name: Name of the operation that failed
        error: The exception that occurred
        additional_context: Additional context information
    """
    context_msg = f" - {additional_context}" if additional_context else ""
    logger.error(f"Failed to {operation_name}: {error}{context_msg}")


def log_database_error(operation_name: str, error: Exception, table_name: Optional[str] = None) -> None:
    """Log database operation errors with consistent formatting.
    
    Args:
        operation_name: Name of the database operation that failed
        error: The exception that occurred
        table_name: Optional table name for additional context
    """
    table_msg = f" on table '{table_name}'" if table_name else ""
    logger.error(f"Failed to {operation_name}{table_msg}: {error}")


def log_bulk_operation_error(operation_name: str, error: Exception, record_type: str, count: Optional[int] = None) -> None:
    """Log bulk operation errors with consistent formatting.
    
    Args:
        operation_name: Name of the bulk operation that failed
        error: The exception that occurred
        record_type: Type of records being operated on
        count: Optional count of records for additional context
    """
    count_msg = f" ({count} records)" if count else ""
    logger.error(f"Failed to {operation_name} {record_type}{count_msg}: {error}")


def log_schema_error(error_type: str, error_details: Any) -> None:
    """Log schema-related errors with consistent formatting.
    
    Args:
        error_type: Type of schema error
        error_details: Details about the error
    """
    logger.error(f"Schema {error_type}: {error_details}")


def handle_database_operation_error(
    operation_name: str, 
    error: Exception, 
    return_value: Any = None,
    table_name: Optional[str] = None
) -> Any:
    """Handle database operation errors with consistent logging and return value.
    
    Args:
        operation_name: Name of the operation that failed
        error: The exception that occurred
        return_value: Value to return after logging the error
        table_name: Optional table name for additional context
        
    Returns:
        The provided return_value
    """
    log_database_error(operation_name, error, table_name)
    return return_value


def error_handler_decorator(operation_name: str, return_value: Any = None):
    """Decorator for consistent error handling in database operations.
    
    Args:
        operation_name: Name of the operation for logging
        return_value: Value to return on error
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_operation_error(operation_name, e)
                return return_value
        return wrapper
    return decorator


# Specific error handlers for common patterns
def handle_get_operation_error(operation_name: str, error: Exception) -> None:
    """Handle get operation errors."""
    log_operation_error(f"get {operation_name}", error)


def handle_search_operation_error(operation_name: str, error: Exception) -> list:
    """Handle search operation errors."""
    log_operation_error(f"search {operation_name}", error)
    return []


def handle_bulk_insert_error(record_type: str, error: Exception) -> None:
    """Handle bulk insert errors."""
    log_bulk_operation_error("bulk insert", error, record_type)


def handle_bulk_update_error(record_type: str, error: Exception) -> None:
    """Handle bulk update errors."""
    log_bulk_operation_error("bulk update", error, record_type)


def handle_bulk_upsert_error(record_type: str, error: Exception) -> None:
    """Handle bulk upsert errors."""
    log_bulk_operation_error("bulk upsert", error, record_type)


def handle_schema_validation_error(error: Exception) -> None:
    """Handle schema validation errors."""
    log_schema_error("validation failed", error)


def handle_table_validation_error(table_name: str, error: Exception) -> None:
    """Handle table validation errors."""
    log_schema_error(f"validation failed for table '{table_name}'", error)


# Generic logging utilities for all levels
def log_operation(level: int, operation_name: str, message: str, *args, **kwargs) -> None:
    """Generic operation logging with consistent formatting.
    
    Args:
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        operation_name: Name of the operation
        message: Message to log
        *args: Additional format arguments
        **kwargs: Additional logging keyword arguments
    """
    formatted_msg = f"{operation_name}: {message}".format(*args) if args else f"{operation_name}: {message}"
    logger.log(level, formatted_msg, **kwargs)


def log_operation_debug(operation_name: str, message: str, *args, **kwargs) -> None:
    """Log debug messages with consistent formatting."""
    log_operation(logging.DEBUG, operation_name, message, *args, **kwargs)


def log_operation_info(operation_name: str, message: str, *args, **kwargs) -> None:
    """Log info messages with consistent formatting."""
    log_operation(logging.INFO, operation_name, message, *args, **kwargs)


def log_operation_warning(operation_name: str, message: str, *args, **kwargs) -> None:
    """Log warning messages with consistent formatting."""
    log_operation(logging.WARNING, operation_name, message, *args, **kwargs)


def log_operation_error(operation_name: str, error: Exception, level: int = logging.ERROR, exc_info: bool = False) -> None:
    """Logs an error for a given operation."""
    logger.log(level, f"Operation '{operation_name}' failed: {error}", exc_info=exc_info)


# Specific logging patterns for common use cases
def log_cache_operation(level: int, operation: str, key: str, *args, **kwargs) -> None:
    """Log cache operations with consistent formatting."""
    message = f"{operation} for key: {key}"
    if args:
        message += " " + " ".join(map(str, args))
    logger.log(level, message, **kwargs)


def log_database_operation(level: int, operation: str, entity: str, *args, **kwargs) -> None:
    """Log database operations with consistent formatting."""
    message = f"{operation} {entity}"
    if args:
        message += " " + " ".join(map(str, args))
    logger.log(level, message, **kwargs)


def log_circuit_breaker_operation(level: int, operation: str, op_name: str, *args, **kwargs) -> None:
    """Log circuit breaker operations with consistent formatting."""
    message = f"{operation} for operation: {op_name}"
    if args:
        message += " " + " ".join(map(str, args))
    logger.log(level, message, **kwargs)


def log_validation_operation(level: int, operation: str, entity_id: str, *args, **kwargs) -> None:
    """Log validation operations with consistent formatting."""
    message = f"{operation} for {entity_id}"
    if args:
        message += " " + " ".join(map(str, args))
    logger.log(level, message, **kwargs)


# Convenience functions for common logging patterns
def log_cache_debug(operation: str, key: str, *args, **kwargs) -> None:
    """Log cache debug operations."""
    log_cache_operation(logging.DEBUG, operation, key, *args, **kwargs)


def log_cache_info(operation: str, key: str, *args, **kwargs) -> None:
    """Log cache info operations."""
    log_cache_operation(logging.INFO, operation, key, *args, **kwargs)


def log_cache_warning(operation: str, key: str, *args, **kwargs) -> None:
    """Log cache warning operations."""
    log_cache_operation(logging.WARNING, operation, key, *args, **kwargs)


def log_database_debug(operation: str, entity: str, *args, **kwargs) -> None:
    """Log database debug operations."""
    log_database_operation(logging.DEBUG, operation, entity, *args, **kwargs)


def log_database_info(operation: str, entity: str, *args, **kwargs) -> None:
    """Log database info operations."""
    log_database_operation(logging.INFO, operation, entity, *args, **kwargs)


def log_circuit_breaker_debug(operation: str, op_name: str, *args, **kwargs) -> None:
    """Log circuit breaker debug operations."""
    log_circuit_breaker_operation(logging.DEBUG, operation, op_name, *args, **kwargs)


def log_circuit_breaker_info(operation: str, op_name: str, *args, **kwargs) -> None:
    """Log circuit breaker info operations."""
    log_circuit_breaker_operation(logging.INFO, operation, op_name, *args, **kwargs)


def log_circuit_breaker_warning(operation: str, op_name: str, *args, **kwargs) -> None:
    """Log circuit breaker warning operations."""
    log_circuit_breaker_operation(logging.WARNING, operation, op_name, *args, **kwargs)


def log_validation_debug(operation: str, entity_id: str, *args, **kwargs) -> None:
    """Log validation debug operations."""
    log_validation_operation(logging.DEBUG, operation, entity_id, *args, **kwargs)


def log_validation_info(operation: str, entity_id: str, *args, **kwargs) -> None:
    """Log validation info operations."""
    log_validation_operation(logging.INFO, operation, entity_id, *args, **kwargs)


def log_validation_warning(operation: str, entity_id: str, *args, **kwargs) -> None:
    """Log validation warning operations."""
    log_validation_operation(logging.WARNING, operation, entity_id, *args, **kwargs)
