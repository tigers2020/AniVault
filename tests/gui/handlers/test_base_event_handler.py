"""Tests for BaseEventHandler.

This module tests the base functionality for all event handlers,
ensuring consistent status message and error handling patterns.
"""

from unittest.mock import MagicMock, Mock, call, patch

import pytest

from anivault.gui.handlers.base_event_handler import BaseEventHandler


class TestBaseEventHandler:
    """Test cases for BaseEventHandler."""

    @pytest.fixture
    def mock_status_manager(self):
        """Create a mock StatusManager."""
        mock_mgr = Mock()
        mock_mgr.show_message = Mock()
        return mock_mgr

    @pytest.fixture
    def handler(self, mock_status_manager):
        """Create a BaseEventHandler instance for testing."""
        return BaseEventHandler(status_manager=mock_status_manager)

    def test_initialization(self, handler, mock_status_manager):
        """Test BaseEventHandler initialization."""
        assert handler is not None
        assert handler._status_manager is mock_status_manager
        assert handler._logger is not None
        assert handler._logger.name == "BaseEventHandler"

    def test_show_status_displays_message(self, handler, mock_status_manager):
        """Test _show_status displays message in status bar."""
        # Arrange
        test_message = "Processing files..."

        # Act
        handler._show_status(test_message)

        # Assert
        mock_status_manager.show_message.assert_called_once_with(test_message, 0)

    def test_show_status_with_timeout(self, handler, mock_status_manager):
        """Test _show_status displays message with timeout."""
        # Arrange
        test_message = "Complete!"
        timeout = 3000

        # Act
        handler._show_status(test_message, timeout=timeout)

        # Assert
        mock_status_manager.show_message.assert_called_once_with(test_message, timeout)

    def test_show_status_logs_message(self, handler):
        """Test _show_status logs message at INFO level."""
        # Arrange
        test_message = "Scanning files..."

        # Act
        with patch.object(handler._logger, "info") as mock_log:
            handler._show_status(test_message)

        # Assert
        mock_log.assert_called_once_with(test_message)

    @patch("anivault.gui.handlers.base_event_handler.QMessageBox")
    def test_show_error_displays_dialog(self, mock_qmessagebox, handler):
        """Test _show_error displays error dialog."""
        # Arrange
        test_message = "Failed to process file"
        test_title = "Processing Error"

        # Act
        handler._show_error(test_message, test_title)

        # Assert
        mock_qmessagebox.warning.assert_called_once_with(None, test_title, test_message)

    @patch("anivault.gui.handlers.base_event_handler.QMessageBox")
    def test_show_error_displays_status_message(
        self, mock_qmessagebox, handler, mock_status_manager
    ):
        """Test _show_error displays message in status bar."""
        # Arrange
        test_message = "Failed to scan directory"

        # Act
        handler._show_error(test_message)

        # Assert
        mock_status_manager.show_message.assert_called_once_with(
            f"Error: {test_message}"
        )

    @patch("anivault.gui.handlers.base_event_handler.QMessageBox")
    def test_show_error_logs_message(self, mock_qmessagebox, handler):
        """Test _show_error logs message at ERROR level."""
        # Arrange
        test_message = "Critical failure"

        # Act
        with patch.object(handler._logger, "error") as mock_log:
            handler._show_error(test_message)

        # Assert
        mock_log.assert_called_once_with(test_message)

    @patch("anivault.gui.handlers.base_event_handler.QMessageBox")
    def test_show_error_default_title(self, mock_qmessagebox, handler):
        """Test _show_error uses default title when not specified."""
        # Arrange
        test_message = "Something went wrong"

        # Act
        handler._show_error(test_message)

        # Assert
        mock_qmessagebox.warning.assert_called_once()
        args = mock_qmessagebox.warning.call_args[0]
        assert args[1] == "Error"  # Default title

    def test_show_status_empty_message(self, handler, mock_status_manager):
        """Test _show_status handles empty message."""
        # Arrange
        empty_message = ""

        # Act
        handler._show_status(empty_message)

        # Assert
        mock_status_manager.show_message.assert_called_once_with(empty_message, 0)

    @patch("anivault.gui.handlers.base_event_handler.QMessageBox")
    def test_show_error_special_characters(self, mock_qmessagebox, handler):
        """Test _show_error handles special characters in message."""
        # Arrange
        special_chars_message = "Failed: <>&\"'\\n\\t"

        # Act
        handler._show_error(special_chars_message)

        # Assert - Should not raise exception
        mock_qmessagebox.warning.assert_called_once()
