"""Unit tests for StatusManager.

This module tests StatusManager functionality including:
- Status bar setup
- Message display
- Cache status formatting and display
"""

from typing import Any

import pytest
from PySide6.QtWidgets import QStatusBar
from pytestqt.qtbot import QtBot

from anivault.gui.managers.status_manager import StatusManager


@pytest.fixture
def status_bar(qtbot: QtBot) -> QStatusBar:
    """Create a QStatusBar instance for testing.

    Args:
        qtbot: PyTest-Qt fixture for Qt testing

    Returns:
        QStatusBar instance
    """
    bar = QStatusBar()
    qtbot.addWidget(bar)
    return bar


@pytest.fixture
def status_manager(status_bar: QStatusBar) -> StatusManager:
    """Create a StatusManager instance for testing.

    Args:
        status_bar: Status bar fixture

    Returns:
        StatusManager instance
    """
    return StatusManager(status_bar)


class TestStatusManager:
    """Unit tests for StatusManager class."""

    def test_init(
        self,
        status_bar: QStatusBar,
        status_manager: StatusManager,
    ) -> None:
        """Test StatusManager initialization."""
        assert status_manager._status_bar == status_bar
        assert status_manager._cache_status_label is None

    def test_setup_status_bar(
        self,
        status_bar: QStatusBar,
        status_manager: StatusManager,
    ) -> None:
        """Test that setup_status_bar() initializes status bar correctly."""
        # When: setup_status_bar is called
        status_manager.setup_status_bar()

        # Then: Status bar should show ready message
        assert status_bar.currentMessage() == "Ready"

        # And: Cache status label should be created and added
        assert status_manager._cache_status_label is not None
        assert status_manager._cache_status_label.text() == "캐시: 초기화 중..."
        assert (
            status_manager._cache_status_label.toolTip()
            == "캐시 히트율 및 항목 수 정보"
        )

    def test_show_message(
        self,
        status_bar: QStatusBar,
        status_manager: StatusManager,
    ) -> None:
        """Test that show_message() displays message in status bar."""
        # Given: Status bar is set up
        status_manager.setup_status_bar()

        # When: Showing a message
        test_message = "Processing files..."
        status_manager.show_message(test_message)

        # Then: Message should be displayed
        assert status_bar.currentMessage() == test_message

    def test_show_message_with_timeout(
        self,
        status_bar: QStatusBar,
        status_manager: StatusManager,
    ) -> None:
        """Test that show_message() accepts timeout parameter."""
        # Given: Status bar is set up
        status_manager.setup_status_bar()

        # When: Showing a message with timeout
        test_message = "Temporary message"
        status_manager.show_message(test_message, timeout=3000)

        # Then: Message should be displayed (timeout behavior tested by Qt)
        assert status_bar.currentMessage() == test_message

    def test_update_cache_status_formatting(
        self,
        status_manager: StatusManager,
    ) -> None:
        """Test that update_cache_status() formats cache stats correctly."""
        # Given: Status bar is set up
        status_manager.setup_status_bar()

        # When: Updating cache status with valid stats
        stats: dict[str, Any] = {
            "hit_ratio": 87.3,
            "cache_items": 1247,
            "cache_type": "SQLite",
        }
        status_manager.update_cache_status(stats)

        # Then: Cache status label should show formatted text
        assert status_manager._cache_status_label is not None
        expected_text = "캐시: 87.3% 히트율 (1,247 항목) [SQLite]"
        assert status_manager._cache_status_label.text() == expected_text

    def test_update_cache_status_with_defaults(
        self,
        status_manager: StatusManager,
    ) -> None:
        """Test that update_cache_status() handles missing fields with defaults."""
        # Given: Status bar is set up
        status_manager.setup_status_bar()

        # When: Updating with partial stats
        stats: dict[str, Any] = {"hit_ratio": 50.0}
        status_manager.update_cache_status(stats)

        # Then: Missing fields should use defaults
        assert status_manager._cache_status_label is not None
        expected_text = "캐시: 50.0% 히트율 (0 항목) [Unknown]"
        assert status_manager._cache_status_label.text() == expected_text

    def test_update_cache_status_before_setup(
        self,
        status_manager: StatusManager,
    ) -> None:
        """Test that update_cache_status() handles being called before setup."""
        # When: Updating cache status before setup_status_bar
        stats: dict[str, Any] = {"hit_ratio": 90.0, "cache_items": 100}
        status_manager.update_cache_status(stats)

        # Then: No error should occur (defensive programming)
        # Cache label is None, so update is silently skipped
        assert status_manager._cache_status_label is None

    def test_update_cache_status_invalid_input(
        self,
        status_manager: StatusManager,
    ) -> None:
        """Test that update_cache_status() handles invalid input gracefully."""
        # Given: Status bar is set up
        status_manager.setup_status_bar()
        original_text = status_manager._cache_status_label.text()

        # When: Calling with invalid input
        status_manager.update_cache_status("not a dict")  # type: ignore

        # Then: Status should remain unchanged (defensive programming)
        assert status_manager._cache_status_label is not None
        assert status_manager._cache_status_label.text() == original_text

    def test_format_cache_status_with_large_numbers(
        self,
        status_manager: StatusManager,
    ) -> None:
        """Test that _format_cache_status() formats large numbers with separators."""
        # When: Formatting with large cache item count
        stats: dict[str, Any] = {
            "hit_ratio": 99.9,
            "cache_items": 1234567,
            "cache_type": "Hybrid",
        }

        # Then: Should use thousands separator
        formatted = status_manager._format_cache_status(stats)
        expected = "캐시: 99.9% 히트율 (1,234,567 항목) [Hybrid]"
        assert formatted == expected

    def test_format_cache_status_decimal_precision(
        self,
        status_manager: StatusManager,
    ) -> None:
        """Test that _format_cache_status() formats hit ratio with 1 decimal place."""
        # When: Formatting with various hit ratios
        test_cases = [
            (0.0, "캐시: 0.0% 히트율 (0 항목) [Unknown]"),
            (50.123, "캐시: 50.1% 히트율 (0 항목) [Unknown]"),
            (100.0, "캐시: 100.0% 히트율 (0 항목) [Unknown]"),
        ]

        for hit_ratio, expected in test_cases:
            stats: dict[str, Any] = {"hit_ratio": hit_ratio}
            formatted = status_manager._format_cache_status(stats)
            assert formatted == expected
