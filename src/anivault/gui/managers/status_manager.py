"""Status Bar Manager.

This module provides StatusManager, which handles all status bar functionality
for MainWindow including cache status display and temporary messages.

Design Pattern:
    - Follows the manager pattern for centralized status bar management
    - Does NOT inherit from QObject as it only manages status display
    - Encapsulates status formatting logic

Usage:
    StatusManager manages two types of status information:
    - Temporary messages (via showMessage)
    - Permanent cache status display

Example:
    >>> status_manager = StatusManager(status_bar)
    >>> status_manager.setup_status_bar()
    >>> status_manager.show_message("Processing files...")
    >>> status_manager.update_cache_status(cache_stats)
"""

from __future__ import annotations

from typing import TypedDict

from PySide6.QtWidgets import QLabel, QStatusBar


class CacheStats(TypedDict, total=False):
    """Cache statistics dictionary type (NO Any!).

    Attributes:
        hit_ratio: Cache hit ratio percentage (0.0-100.0)
        total_requests: Total cache requests (hits + misses)
        cache_items: Total items in cache
        cache_type: Primary cache type (SQLite/JSON/Hybrid)
    """

    hit_ratio: float
    total_requests: int
    cache_items: int
    cache_type: str


class StatusManager:
    """Manages status bar display for MainWindow.

    This class extracts status bar management logic from MainWindow to improve
    separation of concerns. It handles both temporary messages and permanent
    cache status display.

    Attributes:
        _status_bar: Reference to the QStatusBar widget
        _cache_status_label: QLabel for permanent cache status display

    Status Display:
        - Temporary messages: Displayed via showMessage()
        - Cache status: Permanent widget showing hit ratio, item count, type
    """

    def __init__(self, status_bar: QStatusBar) -> None:
        """Initialize StatusManager.

        Args:
            status_bar: QStatusBar widget to manage
        """
        self._status_bar = status_bar
        self._cache_status_label: QLabel | None = None

    def setup_status_bar(self) -> None:
        """Set up status bar with initial message and permanent widgets.

        This should be called once during MainWindow initialization to
        configure the status bar with:
        - Initial "Ready" message
        - Permanent cache status label
        """
        # Show initial ready message
        self._status_bar.showMessage("Ready")

        # Add cache status label as permanent widget
        self._cache_status_label = QLabel("캐시: 초기화 중...")
        self._cache_status_label.setToolTip("캐시 히트율 및 항목 수 정보")
        self._status_bar.addPermanentWidget(self._cache_status_label)

    def show_message(self, message: str, timeout: int = 0) -> None:
        """Display a temporary message in the status bar.

        Args:
            message: Message text to display
            timeout: Time in milliseconds to display message (0 = until next message)

        Example:
            >>> status_manager.show_message("Scanning files...", 3000)
        """
        self._status_bar.showMessage(message, timeout)

    def update_cache_status(self, stats: CacheStats) -> None:
        """Update cache status display in status bar (NO Any!).

        Args:
            stats: Cache statistics with typed fields:
                - hit_ratio: Cache hit ratio percentage (0.0-100.0)
                - total_requests: Total cache requests (hits + misses)
                - cache_items: Total items in cache
                - cache_type: Primary cache type (SQLite/JSON/Hybrid)

        Example:
            >>> stats = {"hit_ratio": 87.3, "cache_items": 1247, "cache_type": "SQLite"}
            >>> status_manager.update_cache_status(stats)
        """
        # CacheStats TypedDict validation - NO LONGER NEEDED
        # TypedDict provides compile-time type safety

        if self._cache_status_label is None:
            # Status bar not initialized yet
            return

        # Format and update cache status text
        status_text = self._format_cache_status(stats)
        self._cache_status_label.setText(status_text)

    def _format_cache_status(self, stats: CacheStats) -> str:
        """Format cache statistics into display text (NO Any!).

        Args:
            stats: Cache statistics with typed fields

        Returns:
            Formatted status text string

        Format:
            "캐시: 87.3% 히트율 (1,247 항목) [SQLite]"
        """
        hit_ratio = stats.get("hit_ratio", 0.0)
        cache_items = stats.get("cache_items", 0)
        cache_type = stats.get("cache_type", "Unknown")

        # Format with thousands separator for cache items
        return f"캐시: {hit_ratio:.1f}% 히트율 ({cache_items:,} 항목) [{cache_type}]"
