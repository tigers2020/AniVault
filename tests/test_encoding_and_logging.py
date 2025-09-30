"""
Integration tests for UTF-8 encoding and logging functionality.

These tests verify that the AniVault application properly handles UTF-8 encoding
and logging configuration across different scenarios.
"""

import io
import logging
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the modules we're testing
from src.anivault.utils.encoding import (
    setup_utf8_environment,
    open_utf8,
    read_text_file,
    write_text_file,
    ensure_utf8_string,
    safe_filename,
    get_file_encoding,
    UTF8_ENCODING,
)

from src.anivault.utils.logging_config import (
    setup_logging,
    get_logger,
    log_startup,
    log_shutdown,
    cleanup_logging,
    LoggingContext,
    AniVaultFormatter,
)


class TestUTF8Encoding:
    """Test UTF-8 encoding functionality."""

    def test_utf8_environment_setup(self):
        """Test that UTF-8 environment is properly configured."""
        # Clear any existing PYTHONUTF8 setting
        if "PYTHONUTF8" in os.environ:
            del os.environ["PYTHONUTF8"]

        # Setup UTF-8 environment
        setup_utf8_environment()

        # Verify PYTHONUTF8 is set
        assert os.environ.get("PYTHONUTF8") == "1"

    def test_open_utf8_text_file(self):
        """Test opening text files with UTF-8 encoding."""
        test_content = "안녕하세요 こんにちは Hello 你好"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            # Read with open_utf8
            with open_utf8(temp_path, "r") as f:
                content = f.read()
                assert content == test_content
        finally:
            os.unlink(temp_path)

    def test_open_utf8_binary_file(self):
        """Test opening binary files with UTF-8 encoding."""
        test_content = b"Binary content"

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        try:
            # Read binary file
            with open_utf8(temp_path, "rb") as f:
                content = f.read()
                assert content == test_content
        finally:
            os.unlink(temp_path)

    def test_read_text_file(self):
        """Test reading text files with UTF-8 encoding."""
        test_content = "애니메이션 アニメ 动画 Anime"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            content = read_text_file(temp_path)
            assert content == test_content
        finally:
            os.unlink(temp_path)

    def test_write_text_file(self):
        """Test writing text files with UTF-8 encoding."""
        test_content = "작은 공주 세라 小さなプリンセス セーラ Little Princess Sara"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            write_text_file(temp_path, test_content)

            # Verify content was written correctly
            with open(temp_path, encoding="utf-8") as f:
                content = f.read()
                assert content == test_content
        finally:
            os.unlink(temp_path)

    def test_write_text_file_with_bom(self):
        """Test writing text files with UTF-8 BOM."""
        test_content = "BOM test content"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            write_text_file(temp_path, test_content, ensure_utf8_bom=True)

            # Verify BOM was added
            with open(temp_path, "rb") as f:
                content = f.read()
                assert content.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM

            # Verify content can be read correctly (BOM should be automatically handled)
            with open(temp_path, encoding="utf-8") as f:
                content = f.read()
                # The BOM should be automatically stripped by Python's UTF-8 decoder
                # But if it's not, we need to handle it manually
                if content.startswith("\ufeff"):
                    content = content[1:]  # Remove BOM
                assert content == test_content
        finally:
            os.unlink(temp_path)

    def test_ensure_utf8_string_from_string(self):
        """Test ensuring UTF-8 string from already encoded string."""
        test_string = "스트링 테스트"
        result = ensure_utf8_string(test_string)
        assert result == test_string
        assert isinstance(result, str)

    def test_ensure_utf8_string_from_bytes(self):
        """Test ensuring UTF-8 string from bytes."""
        test_bytes = "바이트 테스트".encode()
        result = ensure_utf8_string(test_bytes)
        assert result == "바이트 테스트"
        assert isinstance(result, str)

    def test_safe_filename(self):
        """Test creating safe filenames."""
        # Test with invalid characters
        unsafe_name = "test<file>:name?.txt"
        safe_name = safe_filename(unsafe_name)
        assert (
            safe_name == "test_file__name_.txt"
        )  # Each invalid char becomes underscore

        # Test with Korean characters (should be preserved)
        korean_name = "애니메이션 파일.txt"
        safe_korean = safe_filename(korean_name)
        assert safe_korean == "애니메이션 파일.txt"

        # Test with very long filename
        long_name = "a" * 300 + ".txt"
        safe_long = safe_filename(long_name, max_length=10)
        assert len(safe_long) <= 10
        assert safe_long.endswith(".txt")

    def test_safe_filename_edge_cases(self):
        """Test safe filename edge cases."""
        # Empty filename
        assert safe_filename("") == "unnamed"

        # Only dots and spaces
        assert safe_filename("   ...   ") == "unnamed"

        # Only invalid characters
        assert safe_filename('<>:"/\\|?*') == "unnamed"


class TestLoggingConfiguration:
    """Test logging configuration functionality."""

    def test_setup_logging_console_only(self):
        """Test setting up logging with console output only."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        root_logger.handlers.clear()

        try:
            # Setup console-only logging
            logger = setup_logging(console_output=True, file_output=False)

            # Verify logger is configured
            assert logger.level == logging.INFO
            assert len(logger.handlers) == 1

            # Verify handler is console handler
            handler = logger.handlers[0]
            assert isinstance(handler, logging.StreamHandler)
            assert handler.stream == sys.stdout

        finally:
            # Restore original handlers
            root_logger.handlers = original_handlers

    def test_setup_logging_file_only(self):
        """Test setting up logging with file output only."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)

            # Clear existing handlers
            root_logger = logging.getLogger()
            original_handlers = root_logger.handlers[:]
            root_logger.handlers.clear()

            try:
                # Setup file-only logging
                logger = setup_logging(
                    console_output=False,
                    file_output=True,
                    log_dir=log_dir,
                    log_file="test.log",
                )

                # Verify logger is configured
                assert logger.level == logging.INFO
                assert len(logger.handlers) == 1

                # Verify handler is file handler
                handler = logger.handlers[0]
                assert isinstance(handler, logging.handlers.RotatingFileHandler)

                # Test logging to file
                test_message = "Test log message with Unicode: 안녕하세요"
                logger.info(test_message)

                # Verify log was written to file
                log_file = log_dir / "test.log"
                assert log_file.exists()

                with open(log_file, encoding="utf-8") as f:
                    log_content = f.read()
                    assert test_message in log_content
                    assert "안녕하세요" in log_content

                # Clean up handlers to close file handles
                cleanup_logging(logger)

            finally:
                # Restore original handlers
                root_logger.handlers = original_handlers

    def test_setup_logging_both_outputs(self):
        """Test setting up logging with both console and file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)

            # Clear existing handlers
            root_logger = logging.getLogger()
            original_handlers = root_logger.handlers[:]
            root_logger.handlers.clear()

            try:
                # Setup both console and file logging
                logger = setup_logging(
                    console_output=True,
                    file_output=True,
                    log_dir=log_dir,
                    log_file="test.log",
                )

                # Verify logger has both handlers
                assert len(logger.handlers) == 2

                # Verify one is console, one is file
                handler_types = [type(h) for h in logger.handlers]
                assert logging.StreamHandler in handler_types
                assert logging.handlers.RotatingFileHandler in handler_types

                # Clean up handlers to close file handles
                cleanup_logging(logger)

            finally:
                # Restore original handlers
                root_logger.handlers = original_handlers

    def test_get_logger(self):
        """Test getting logger for specific module."""
        logger = get_logger("test.module")
        assert logger.name == "test.module"
        assert isinstance(logger, logging.Logger)

    def test_logging_context_manager(self):
        """Test LoggingContext for temporary log level changes."""
        logger = logging.getLogger("test.context")
        original_level = logger.level

        try:
            # Test context manager
            with LoggingContext(logging.DEBUG, "test.context") as ctx_logger:
                assert ctx_logger.level == logging.DEBUG

            # Verify level was restored
            assert logger.level == original_level

        finally:
            logger.setLevel(original_level)

    def test_log_startup_and_shutdown(self):
        """Test startup and shutdown logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)

            # Setup logging
            logger = setup_logging(
                console_output=False,
                file_output=True,
                log_dir=log_dir,
                log_file="startup_test.log",
            )

            # Test startup logging
            log_startup(logger, "1.0.0")

            # Test shutdown logging
            log_shutdown(logger)

            # Clean up handlers to close file handles
            cleanup_logging(logger)

            # Verify logs were written
            log_file = log_dir / "startup_test.log"
            assert log_file.exists()

            with open(log_file, encoding="utf-8") as f:
                log_content = f.read()
                assert "AniVault Startup" in log_content
                assert "Version: 1.0.0" in log_content
                assert "AniVault Shutdown" in log_content


class TestIntegrationScenarios:
    """Test integration scenarios combining UTF-8 and logging."""

    def test_utf8_logging_integration(self):
        """Test that logging works correctly with UTF-8 content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)

            # Setup logging
            logger = setup_logging(
                console_output=False,
                file_output=True,
                log_dir=log_dir,
                log_file="utf8_test.log",
            )

            # Log messages with various Unicode content
            unicode_messages = [
                "Korean: 안녕하세요",
                "Japanese: こんにちは",
                "Chinese: 你好",
                "Arabic: مرحبا",
                "Emoji: 🎌 🎬 📺",
                "Mixed: Hello こんにちは 안녕하세요 你好",
            ]

            for message in unicode_messages:
                logger.info(message)

            # Clean up handlers to close file handles
            cleanup_logging(logger)

            # Verify all messages were logged correctly
            log_file = log_dir / "utf8_test.log"
            assert log_file.exists()

            with open(log_file, encoding="utf-8") as f:
                log_content = f.read()

            for message in unicode_messages:
                assert message in log_content

    def test_file_operations_with_logging(self):
        """Test file operations while logging is active."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            log_dir = temp_path / "logs"

            # Setup logging
            logger = setup_logging(
                console_output=False,
                file_output=True,
                log_dir=log_dir,
                log_file="file_ops_test.log",
            )

            # Perform file operations
            test_file = temp_path / "test_utf8.txt"
            test_content = "애니메이션 파일 테스트 アニメファイルテスト"

            logger.info(f"Writing file: {test_file}")
            write_text_file(test_file, test_content)

            logger.info(f"Reading file: {test_file}")
            read_content = read_text_file(test_file)

            assert read_content == test_content
            logger.info("File operations completed successfully")

            # Clean up handlers to close file handles
            cleanup_logging(logger)

            # Verify operations were logged
            log_file = log_dir / "file_ops_test.log"
            with open(log_file, encoding="utf-8") as f:
                log_content = f.read()

            assert "Writing file:" in log_content
            assert "Reading file:" in log_content
            assert "File operations completed successfully" in log_content

    def test_error_handling_with_utf8(self):
        """Test error handling scenarios with UTF-8 content."""
        logger = get_logger("test.errors")

        # Test logging errors with Unicode content
        try:
            raise ValueError("에러 메시지: エラーメッセージ")
        except ValueError as e:
            logger.error(f"Caught error: {e}")

        # Test logging with malformed UTF-8
        try:
            # This should not crash the logging system
            malformed_bytes = b"\xff\xfe\x00\x00"  # Invalid UTF-8
            logger.warning(f"Malformed bytes detected: {malformed_bytes}")
        except Exception:
            pytest.fail("Logging should handle malformed UTF-8 gracefully")


if __name__ == "__main__":
    pytest.main([__file__])
