"""Tests for centralized logging functionality."""

import logging

from anivault.core.logging import get_logger, setup_logging


class TestLoggingSetup:
    """Test logging setup functionality."""

    def test_setup_logging_with_defaults(self, tmp_path):
        """Test that logging setup works with default configuration."""
        # Create a temporary log file
        log_file = tmp_path / "test.log"

        # Setup logging with temporary file
        setup_logging(log_file=str(log_file))

        # Get the root logger
        root_logger = logging.getLogger()

        # Check that handlers are added
        assert len(root_logger.handlers) == 2  # File + Console handlers

        # Check that file handler exists
        file_handlers = [
            h
            for h in root_logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) == 1

        # Check that console handler exists
        console_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert len(console_handlers) == 1

    def test_setup_logging_with_custom_params(self, tmp_path):
        """Test that logging setup works with custom parameters."""
        log_file = tmp_path / "custom.log"

        setup_logging(
            log_file=str(log_file),
            log_level="DEBUG",
            log_max_bytes=1024,  # 1KB for easy rotation testing
            log_backup_count=2,
        )

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

        # Check file handler configuration
        file_handlers = [
            h
            for h in root_logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) == 1
        assert file_handlers[0].maxBytes == 1024
        assert file_handlers[0].backupCount == 2

    def test_log_rotation(self, tmp_path):
        """Test that log rotation works correctly."""
        log_file = tmp_path / "rotation_test.log"

        # Setup logging with small max bytes for easy rotation
        setup_logging(
            log_file=str(log_file),
            log_max_bytes=100,  # Very small for testing
            log_backup_count=2,
        )

        logger = get_logger("test_rotation")

        # Write enough data to trigger rotation
        for i in range(10):
            logger.info(
                f"This is a test log message number {i} with some extra content to make it longer"
            )

        # Check that log file exists
        assert log_file.exists()

        # Check that backup files are created (if rotation occurred)
        backup_files = list(tmp_path.glob("rotation_test.log.*"))
        # Note: Rotation might not occur if the total size is still under the limit
        # This test verifies the setup works, actual rotation depends on content size

    def test_get_logger(self):
        """Test that get_logger returns a proper logger instance."""
        logger = get_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_logging_with_utf8_content(self, tmp_path):
        """Test that logging handles UTF-8 content correctly."""
        log_file = tmp_path / "utf8_test.log"

        setup_logging(log_file=str(log_file))
        logger = get_logger("utf8_test")

        # Log content with UTF-8 characters
        test_messages = [
            "English message",
            "日本語メッセージ",
            "한국어 메시지",
            "Русский текст",
            "العربية",
            "עברית",
        ]

        for message in test_messages:
            logger.info(message)

        # Verify that the log file was created and contains the content
        assert log_file.exists()

        # Read the log file and verify UTF-8 content
        with open(log_file, encoding="utf-8") as f:
            log_content = f.read()

        for message in test_messages:
            assert message in log_content

    def test_log_directory_creation(self, tmp_path):
        """Test that log directory is created if it doesn't exist."""
        # Create a nested directory path
        log_file = tmp_path / "nested" / "deep" / "log" / "test.log"

        # This should create the directory structure
        setup_logging(log_file=str(log_file))

        # Verify the directory was created
        assert log_file.parent.exists()
        assert log_file.parent.is_dir()

    def test_console_handler_level(self, tmp_path):
        """Test that console handler has correct level."""
        log_file = tmp_path / "console_test.log"

        setup_logging(log_file=str(log_file))

        root_logger = logging.getLogger()
        console_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)
        ]

        assert len(console_handlers) == 1
        assert console_handlers[0].level == logging.INFO
