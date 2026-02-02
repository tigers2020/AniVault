"""Match event handler for MainWindow."""

from __future__ import annotations

import logging

from anivault.gui_v2.handlers.base_event_handler import BaseEventHandler
from anivault.gui_v2.models import OperationError, OperationProgress

logger = logging.getLogger(__name__)


class MatchEventHandler(BaseEventHandler):
    """Handles match-related events for MainWindow."""

    def on_match_clicked(self) -> None:
        """Handle match button click."""
        if not self._window.match_controller:
            self._window.status_bar.set_status("매칭 컨트롤러가 초기화되지 않았습니다.", "error")
            return

        files = self._window._subtitle_scan_results if self._window._current_view == "subtitles" else self._window._scan_results
        if not files:
            self._window.status_bar.set_status("먼저 디렉터리를 스캔하세요.", "warn")
            return

        self._window._active_match_target = "subtitles" if self._window._current_view == "subtitles" else "videos"
        self._window.match_controller.match_files(files)

    def on_match_started(self) -> None:
        """Handle match start."""
        self._window.status_bar.set_status("TMDB 매칭 시작...", "ok")
        self._window.loading_overlay.show_loading("TMDB 매칭 중...")

    def on_match_progress(self, progress: OperationProgress) -> None:
        """Handle match progress updates."""
        message = progress.message or f"{progress.current}/{progress.total}"
        self._window.status_bar.set_status(message, "ok")

    def on_match_finished(self, results: list) -> None:
        """Handle match completion."""
        logger.debug("Match finished: received %d results", len(results))
        self._window.loading_overlay.hide_loading()
        self._window.status_bar.set_status("매칭 완료", "ok")

        if self._window._active_match_target == "subtitles":
            self._window._subtitle_scan_results = results
            if self._window._current_view == "subtitles":
                self._window.groups_view.set_file_metadata(results)
                self._window._refresh_statistics()
            self._window._refresh_status_bar()
            return

        self._window._scan_results = results
        self._window._update_all_views_with_metadata(results)
        self._window._refresh_statistics()
        self._window._refresh_status_bar()

    def on_match_error(self, error: OperationError) -> None:
        """Handle match errors."""
        self._window.loading_overlay.hide_loading()
        self._window.status_bar.set_status(error.message, "error")
