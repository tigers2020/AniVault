"""Tests for structured logging system."""

from __future__ import annotations

import json
import logging

from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext
from anivault.shared.logging import (
    StructuredFormatter,
    log_operation_error,
    log_operation_start,
    log_operation_success,
    setup_structured_logger,
)


class TestStructuredFormatter:
    """Test StructuredFormatter JSON output."""

    def test_format_basic_log(self):
        """Test basic log record formatting to JSON."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        # Should be valid JSON
        log_data = json.loads(result)

        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert "timestamp" in log_data

    def test_format_log_with_context(self):
        """Test log record with extra context fields."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=20,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )

        # Add custom fields
        record.error_code = "TEST_ERROR"
        record.context = {"file_path": "/test/path"}
        record.operation = "test_operation"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["error_code"] == "TEST_ERROR"
        assert log_data["context"] == {"file_path": "/test/path"}
        assert log_data["operation"] == "test_operation"


class TestSetupStructuredLogger:
    """Test structured logger setup."""

    def test_setup_creates_logger_with_handler(self):
        """Test that setup creates logger with handler."""
        logger = setup_structured_logger(name="test_structured")

        assert isinstance(logger, logging.Logger)
        assert len(logger.handlers) > 0
        assert isinstance(logger.handlers[0].formatter, StructuredFormatter)

    def test_logger_does_not_propagate(self):
        """Test that structured logger doesn't propagate to parent."""
        logger = setup_structured_logger(name="test_no_propagate")

        assert logger.propagate is False


class TestLoggingHelpers:
    """Test logging helper functions."""

    def test_log_operation_error(self, caplog):
        """Test logging operation errors."""
        logger = logging.getLogger("test_error_log")
        error = ApplicationError(
            code=ErrorCode.FILE_NOT_FOUND,
            message="Test file error",
            context=ErrorContext(file_path="/test/file.txt", operation="test_op"),
        )

        with caplog.at_level(logging.ERROR):
            log_operation_error(logger, error, operation="test_operation")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
        assert "Test file error" in caplog.records[0].message

    def test_log_operation_success(self, caplog):
        """Test logging successful operations."""
        logger = logging.getLogger("test_success_log")

        with caplog.at_level(logging.INFO):
            log_operation_success(
                logger,
                operation="test_op",
                duration_ms=150.5,
                result_info={"files_processed": 10},
            )

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "test_op" in caplog.records[0].message

    def test_log_operation_start(self, caplog):
        """Test logging operation start."""
        logger = logging.getLogger("test_start_log")

        with caplog.at_level(logging.INFO):
            log_operation_start(
                logger, operation="test_op", context={"param": "value"},
            )

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "test_op" in caplog.records[0].message


class TestJSONLoggingIntegration:
    """Test JSON logging integration."""

    def test_structured_logger_outputs_json(self):
        """Test that structured logger actually outputs JSON."""
        import io

        # Create logger with string buffer
        logger = logging.getLogger("test_json_output")
        logger.handlers.clear()
        logger.setLevel(logging.INFO)

        # Add handler with StructuredFormatter
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)

        # Log a message
        logger.info("Test JSON message", extra={"test_field": "test_value"})

        # Get output
        output = stream.getvalue().strip()

        # Should be valid JSON
        log_data = json.loads(output)

        assert log_data["message"] == "Test JSON message"
        assert log_data["level"] == "INFO"
        assert "timestamp" in log_data

