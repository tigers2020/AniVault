"""Conditional JSON formatter for optimized logging performance.

This module provides a custom logging formatter that only serializes
complex data to JSON for higher log levels (WARNING, ERROR, CRITICAL),
reducing CPU overhead for DEBUG and INFO messages.
"""

import json
import logging
from collections.abc import Callable
from typing import Any, Literal

try:
    import orjson  # type: ignore[import-untyped]

    ORJSON_AVAILABLE = True
except ImportError:
    orjson = None  # type: ignore[assignment]
    ORJSON_AVAILABLE = False


class ConditionalJsonFormatter(logging.Formatter):
    """Custom formatter that conditionally serializes data to JSON based on log level.

    This formatter only performs expensive JSON serialization for WARNING, ERROR,
    and CRITICAL log levels. For DEBUG and INFO levels, it uses simple string
    formatting to reduce CPU overhead.

    Attributes:
        json_levels: List of log levels that should be serialized to JSON
        json_serializer: Function to use for JSON serialization (orjson.dumps or json.dumps)
        include_extra: Whether to include extra attributes in JSON output
    """

    json_serializer: Callable[[Any], str]

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "%",
        json_levels: list[int] | None = None,
        include_extra: bool = True,
        use_orjson: bool = True,
    ) -> None:
        """Initialize the conditional JSON formatter.

        Args:
            fmt: Log record format string
            datefmt: Date format string
            style: Format style ('%', '{', or '$')
            json_levels: List of log levels that should be serialized to JSON
            include_extra: Whether to include extra attributes in JSON output
            use_orjson: Whether to use orjson for serialization (if available)
        """
        super().__init__(fmt, datefmt, style)

        # Default JSON levels: WARNING, ERROR, CRITICAL
        self.json_levels = json_levels or [
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]

        self.include_extra = include_extra

        # Choose JSON serializer
        if use_orjson and ORJSON_AVAILABLE and orjson is not None:
            self.json_serializer = self._orjson_dumps_wrapper
            self._is_orjson = True
        else:
            self.json_serializer = json.dumps
            self._is_orjson = False

    def _orjson_dumps_wrapper(self, obj: Any) -> str:
        """Wrapper for orjson.dumps that returns str instead of bytes.

        Args:
            obj: Object to serialize

        Returns:
            JSON string
        """
        if orjson is not None:
            result = orjson.dumps(obj)
            if isinstance(result, bytes):
                return result.decode("utf-8")
            return str(result)
        else:
            return json.dumps(obj)

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record.

        Args:
            record: Log record to format

        Returns:
            Formatted log message
        """
        # Check if this level should be serialized to JSON
        if record.levelno in self.json_levels:
            return self._format_as_json(record)
        else:
            # Use standard string formatting for DEBUG/INFO
            return super().format(record)

    def _format_as_json(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log message
        """
        # Build base log entry
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add thread information if available
        if hasattr(record, "thread") and record.thread:
            log_entry["thread"] = record.thread
        if hasattr(record, "threadName") and record.threadName:
            log_entry["thread_name"] = record.threadName

        # Add process information if available
        if hasattr(record, "process") and record.process:
            log_entry["process"] = record.process
        if hasattr(record, "processName") and record.processName:
            log_entry["process_name"] = record.processName

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_entry["stack_info"] = self.formatStack(record.stack_info)

        # Add extra attributes if requested
        if self.include_extra:
            self._add_extra_attributes(log_entry, record)

        # Serialize to JSON
        try:
            return self.json_serializer(log_entry)
        except (TypeError, ValueError) as e:
            # Fallback to string representation for non-serializable objects
            log_entry["serialization_error"] = f"Failed to serialize: {e}"
            return self.json_serializer(log_entry)

    def _add_extra_attributes(self, log_entry: dict[str, Any], record: logging.LogRecord) -> None:
        """Add extra attributes from the log record.

        Args:
            log_entry: Dictionary to add attributes to
            record: Log record containing extra attributes
        """
        # Standard LogRecord attributes to exclude
        excluded_attrs = {
            "name",
            "msg",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "args",
            "asctime",
            "getMessage",
        }

        # Add all non-standard attributes
        for key, value in record.__dict__.items():
            if key not in excluded_attrs:
                try:
                    # Test if the value is JSON serializable
                    if self._is_orjson and orjson is not None:
                        orjson.dumps(value)
                    else:
                        json.dumps(value)
                    log_entry[key] = value
                except (TypeError, ValueError):
                    # Convert non-serializable objects to strings
                    log_entry[key] = str(value)

    def set_json_levels(self, levels: list[int]) -> None:
        """Set the log levels that should be serialized to JSON.

        Args:
            levels: List of log level constants
        """
        self.json_levels = levels

    def add_json_level(self, level: int) -> None:
        """Add a log level to JSON serialization.

        Args:
            level: Log level constant to add
        """
        if level not in self.json_levels:
            self.json_levels.append(level)

    def remove_json_level(self, level: int) -> None:
        """Remove a log level from JSON serialization.

        Args:
            level: Log level constant to remove
        """
        if level in self.json_levels:
            self.json_levels.remove(level)


def create_optimized_formatter(
    json_levels: list[int] | None = None,
    use_orjson: bool = True,
    include_extra: bool = True,
) -> ConditionalJsonFormatter:
    """Create an optimized conditional JSON formatter.

    Args:
        json_levels: Log levels to serialize as JSON (default: WARNING+)
        use_orjson: Whether to use orjson for serialization
        include_extra: Whether to include extra attributes

    Returns:
        Configured ConditionalJsonFormatter instance
    """
    return ConditionalJsonFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        json_levels=json_levels,
        include_extra=include_extra,
        use_orjson=use_orjson,
    )


def create_simple_formatter() -> logging.Formatter:
    """Create a simple formatter for non-JSON levels.

    Returns:
        Simple logging.Formatter instance
    """
    return logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
