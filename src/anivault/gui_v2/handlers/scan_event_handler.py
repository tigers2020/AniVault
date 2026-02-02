"""Scan event handler for MainWindow."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from anivault.gui_v2.handlers.base_event_handler import BaseEventHandler
from anivault.gui_v2.models import OperationError, OperationProgress

logger = logging.getLogger(__name__)


class ScanEventHandler(BaseEventHandler):
    """Handles scan-related events for MainWindow."""

    def on_scan_clicked(self) -> None:
        """Handle scan button click."""
        if not self._window.scan_controller:
            self._window.status_bar.set_status("스캔 컨트롤러가 초기화되지 않았습니다.", "error")
            return

        source_folder = ""
        if self._window.app_context.settings.folders and self._window.app_context.settings.folders.source_folder:
            source_folder = self._window.app_context.settings.folders.source_folder

        if not source_folder:
            directory = QFileDialog.getExistingDirectory(self._window, "스캔할 디렉터리 선택")
            if not directory:
                return
            source_folder = directory

        directory_path = Path(source_folder)
        if not directory_path.exists() or not directory_path.is_dir():
            self._window.status_bar.set_status(f"설정된 소스 폴더가 유효하지 않습니다: {source_folder}", "error")
            directory = QFileDialog.getExistingDirectory(self._window, "스캔할 디렉터리 선택")
            if not directory:
                return
            directory_path = Path(directory)

        self._window.status_bar.set_current_path(str(directory_path))
        if self._window._current_view == "subtitles":
            self._window._active_scan_target = "subtitles"
            self._window.scan_controller.scan_subtitle_directory(directory_path)
        else:
            self._window._active_scan_target = "videos"
            self._window.scan_controller.scan_directory(directory_path)

    def on_scan_started(self) -> None:
        """Handle scan start."""
        self._window.status_bar.set_status("디렉터리 스캔 시작...", "ok")
        self._window.loading_overlay.show_loading("디렉터리 스캔 중...")

    def on_scan_progress(self, progress: OperationProgress) -> None:
        """Handle scan progress updates."""
        message = progress.message or f"{progress.current}/{progress.total}"
        self._window.status_bar.set_status(message, "ok")

    def on_scan_finished(self, results: list) -> None:
        """Handle scan completion."""
        logger.info("Scan finished: received %d results (type: %s)", len(results), type(results).__name__)
        if results:
            logger.info(
                "First result type: %s, keys: %s",
                type(results[0]).__name__,
                list(results[0].__dict__.keys()) if hasattr(results[0], "__dict__") else "N/A",
            )
        self._window.loading_overlay.hide_loading()
        self._window.status_bar.set_status("스캔 완료", "ok")

        if self._window._active_scan_target == "subtitles":
            self._window._subtitle_scan_results = results
            if self._window._current_view == "subtitles":
                self._window.groups_view.set_file_metadata(results)
                self._window._refresh_statistics()
            self._window._refresh_status_bar()
            if results and self._window.match_controller:
                logger.info("Auto-matching started after subtitle scan completion")
                self._window._active_match_target = "subtitles"
                self._window.match_controller.match_files(results)
            return

        self._window._scan_results = results
        self._window._update_all_views_with_metadata(results)
        self._window._refresh_statistics()
        self._window._refresh_status_bar()

        if results and self._window.match_controller:
            logger.info("Auto-matching started after scan completion")
            self._window._active_match_target = "videos"
            self._window.match_controller.match_files(results)

    def on_scan_error(self, error: OperationError) -> None:
        """Handle scan errors."""
        self._window.loading_overlay.hide_loading()
        self._window.status_bar.set_status(error.message, "error")
