"""
TMDB Controller Implementation

This module contains the TMDBController class that manages TMDB API operations
and coordinates between the UI layer and TMDB services.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from anivault.core.models import ScannedFile
from anivault.gui.workers import TMDBMatchingWorker

logger = logging.getLogger(__name__)


class TMDBController(QObject):
    """
    Controller for TMDB API operations and file matching.

    This class manages TMDB API interactions, coordinates matching operations,
    and provides signals for UI communication.
    """

    # Signals for UI communication
    matching_started = Signal()
    file_matched = Signal(dict)  # match result
    matching_progress = Signal(int)  # progress percentage
    matching_finished = Signal(list)  # results
    matching_error = Signal(str)  # error message
    matching_cancelled = Signal()
    cache_stats_updated = Signal(dict)  # cache statistics

    def __init__(self, api_key: str | None = None, parent: QObject | None = None):
        """Initialize the TMDB controller.

        Args:
            api_key: TMDB API key for authentication
            parent: Parent QObject for Qt parent-child relationship
        """
        super().__init__(parent)

        # API configuration
        self.api_key = api_key

        # Thread management
        self.tmdb_thread: QThread | None = None
        self.tmdb_worker: TMDBMatchingWorker | None = None

        # State
        self.is_matching = False
        self.match_results: list[dict[str, Any]] = []

        # Cache statistics timer
        self.cache_stats_timer = QTimer()
        self.cache_stats_timer.timeout.connect(self._fetch_and_emit_stats)
        self.cache_stats_timer.start(10000)  # 10 seconds interval

        logger.debug("TMDBController initialized")

    def set_api_key(self, api_key: str) -> None:
        """Set the TMDB API key.

        Args:
            api_key: The TMDB API key
        """
        self.api_key = api_key
        logger.debug("API key set")

    def match_files(self, files: list[ScannedFile]) -> None:
        """Start matching files against TMDB.

        Args:
            files: List of ScannedFile objects to match

        Raises:
            ValueError: If API key is not set or files list is empty
            RuntimeError: If matching is already in progress
        """
        if not self.api_key:
            raise ValueError("TMDB API key is required")

        if not files:
            raise ValueError("Files list cannot be empty")

        if self.is_matching:
            raise RuntimeError("Matching is already in progress")

        self._start_matching_thread(files)

    def cancel_matching(self) -> None:
        """Cancel the current matching operation."""
        if self.tmdb_worker:
            self.tmdb_worker.cancel_matching()
        logger.debug("Matching cancelled")

    def get_match_result(self, file_path: str) -> dict[str, Any] | None:
        """Get match result for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            Match result dictionary or None if not found
        """
        for result in self.match_results:
            if result.get("file_path") == file_path:
                return result
        return None

    def get_matched_files_count(self) -> int:
        """Get the number of successfully matched files.

        Returns:
            Number of matched files
        """
        return sum(1 for result in self.match_results
                  if result.get("status") == "matched")

    def get_total_files_count(self) -> int:
        """Get the total number of files processed.

        Returns:
            Total number of files
        """
        return len(self.match_results)

    def _start_matching_thread(self, files: list[ScannedFile]) -> None:
        """Start the TMDB matching thread.

        Args:
            files: List of files to match
        """
        # Create and setup thread
        self.tmdb_thread = QThread()
        self.tmdb_worker = TMDBMatchingWorker(self.api_key)

        # Move worker to thread
        self.tmdb_worker.moveToThread(self.tmdb_thread)

        # Connect signals
        self.tmdb_thread.started.connect(
            lambda: self.tmdb_worker.match_files(files),
        )
        self.tmdb_worker.matching_started.connect(self._on_matching_started)
        self.tmdb_worker.file_matched.connect(self._on_file_matched)
        self.tmdb_worker.matching_progress.connect(self._on_matching_progress)
        self.tmdb_worker.matching_finished.connect(self._on_matching_finished)
        self.tmdb_worker.matching_error.connect(self._on_matching_error)
        self.tmdb_worker.matching_cancelled.connect(self._on_matching_cancelled)

        # Cleanup when thread finishes
        self.tmdb_thread.finished.connect(self.tmdb_thread.deleteLater)
        self.tmdb_thread.finished.connect(self.tmdb_worker.deleteLater)

        # Start thread
        self.tmdb_thread.start()
        logger.debug("TMDB matching thread started")

    def _on_matching_started(self) -> None:
        """Handle matching started signal."""
        self.is_matching = True
        self.match_results.clear()
        self.matching_started.emit()
        # Update cache stats immediately when matching starts
        self._fetch_and_emit_stats()

    def _on_file_matched(self, result: dict[str, Any]) -> None:
        """Handle file matched signal.

        Args:
            result: Match result dictionary
        """
        self.match_results.append(result)
        self.file_matched.emit(result)

    def _on_matching_progress(self, progress: int) -> None:
        """Handle matching progress signal.

        Args:
            progress: Progress percentage
        """
        self.matching_progress.emit(progress)

    def _on_matching_finished(self, results: list[dict[str, Any]]) -> None:
        """Handle matching finished signal.

        Args:
            results: List of match results
        """
        self.is_matching = False
        self.match_results = results
        self.matching_finished.emit(results)
        # Update cache stats immediately when matching finishes
        self._fetch_and_emit_stats()

        # Cleanup thread
        if self.tmdb_thread:
            self.tmdb_thread.quit()
            self.tmdb_thread.wait()
            self.tmdb_thread = None
            self.tmdb_worker = None

    def _on_matching_error(self, error_msg: str) -> None:
        """Handle matching error signal.

        Args:
            error_msg: Error message
        """
        self.is_matching = False
        self.matching_error.emit(error_msg)

    def _on_matching_cancelled(self) -> None:
        """Handle matching cancelled signal."""
        self.is_matching = False
        self.matching_cancelled.emit()

    def has_api_key(self) -> bool:
        """Check if API key is set.

        Returns:
            True if API key is set, False otherwise
        """
        return bool(self.api_key)

    def is_operation_in_progress(self) -> bool:
        """Check if an operation is currently in progress.

        Returns:
            True if operation is in progress, False otherwise
        """
        return self.is_matching

    def _fetch_and_emit_stats(self) -> None:
        """Fetch cache statistics and emit cache_stats_updated signal.

        This method retrieves cache statistics from the matching engine
        and emits the cache_stats_updated signal for GUI updates.
        """
        try:
            if self.tmdb_worker and hasattr(self.tmdb_worker, "matching_engine"):
                stats = self.tmdb_worker.matching_engine.get_cache_stats()
                self.cache_stats_updated.emit(stats)
                logger.debug("Cache stats emitted: %s", stats)
            else:
                # Default stats when no worker is available
                default_stats = {
                    "hit_ratio": 0.0,
                    "total_requests": 0,
                    "cache_items": 0,
                    "cache_type": "Unknown",
                }
                self.cache_stats_updated.emit(default_stats)
                logger.debug("Default cache stats emitted")
        except (OSError, sqlite3.Error):
            logger.exception("Failed to fetch cache stats")
            # Emit error stats to prevent UI blocking
            error_stats = {
                "hit_ratio": 0.0,
                "total_requests": 0,
                "cache_items": 0,
                "cache_type": "Error",
            }
            self.cache_stats_updated.emit(error_stats)
