"""Organize event handler for MainWindow."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import QDialog

from anivault.config.settings_provider import get_settings_provider
from anivault.core.organizer.organize_service import (
    execute_organization_plan,
    generate_enhanced_organization_plan,
    generate_organization_plan,
)
from anivault.gui_v2.dialogs.organize_dry_run_dialog import OrganizeDryRunDialog
from anivault.gui_v2.handlers.base_event_handler import BaseEventHandler
from anivault.gui_v2.models import OperationError, OperationProgress

logger = logging.getLogger(__name__)


class OrganizeEventHandler(BaseEventHandler):
    """Handles organize-related events for MainWindow."""

    def on_organize_preflight_clicked(self) -> None:
        """Handle organize preflight (dry run)."""
        if not self._window.organize_controller:
            self._window.status_bar.set_status("정리 컨트롤러가 초기화되지 않았습니다.", "error")
            return

        files = self._window._subtitle_scan_results if self._window._current_view == "subtitles" else self._window._scan_results
        if not files:
            self._window.status_bar.set_status("먼저 매칭을 완료하세요.", "warn")
            return

        self._window.organize_controller.organize_files(files, dry_run=True)

    def on_organize_execute_clicked(self) -> None:
        """Handle organize execution."""
        if not self._window.organize_controller:
            self._window.status_bar.set_status("정리 컨트롤러가 초기화되지 않았습니다.", "error")
            return

        files = self._window._subtitle_scan_results if self._window._current_view == "subtitles" else self._window._scan_results
        if not files:
            self._window.status_bar.set_status("먼저 매칭을 완료하세요.", "warn")
            return

        from anivault.gui_v2.builders.organize_builder import OrganizeBuilder

        scanned_files = OrganizeBuilder.build_scanned_files(files)
        if not scanned_files:
            self._window.status_bar.set_status("정리할 파일이 없습니다.", "warn")
            return

        config_file = self._window.app_context.config_path
        logger.info("Loading settings from: %s", config_file)
        self._window.app_context.settings = get_settings_provider().get_settings(config_file)

        if self._window.app_context.settings.folders:
            logger.info(
                "Organize settings loaded: template=%s, target_folder=%s",
                self._window.app_context.settings.folders.organize_path_template,
                self._window.app_context.settings.folders.target_folder,
            )
        else:
            logger.error("Folder settings not found in configuration - organizing will use defaults!")

        directory = self._resolve_organize_directory()
        if directory is None:
            self._window.status_bar.set_status("정리 경로를 확인할 수 없습니다.", "error")
            return

        destination = ""
        if self._window.app_context.settings.folders:
            destination = self._window.app_context.settings.folders.target_folder or ""

        options = OrganizeBuilder.build_organize_options(
            directory,
            destination=destination or "Anime",
            dry_run=True,
            use_subtitles=self._window._current_view == "subtitles",
        )

        plan = (
            generate_enhanced_organization_plan(scanned_files, options.destination)
            if options.enhanced
            else generate_organization_plan(scanned_files, settings=self._window.app_context.settings)
        )

        if not plan:
            self._window.status_bar.set_status("정리 계획이 비어 있습니다.", "warn")
            return

        preview = OrganizeDryRunDialog(plan, self._window)
        if preview.exec() != QDialog.DialogCode.Accepted or not preview.is_confirmed():
            self._window.status_bar.set_status("파일 정리가 취소되었습니다.", "ok")
            return

        self._window.status_bar.set_status("파일 정리 실행 중...", "ok")
        source_directory = options.directory.path if hasattr(options.directory, "path") else Path(str(options.directory))
        try:
            execute_organization_plan(
                plan,
                source_directory,
                settings=self._window.app_context.settings,
            )
            self._window.status_bar.set_status("정리 완료", "ok")
            self._window._refresh_statistics(pending_override=0)
            self._window._refresh_status_bar()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("Organize execution failed")
            self._window.status_bar.set_status(str(exc) or "정리 실행 실패", "error")

    def on_organize_started(self) -> None:
        """Handle organize start."""
        self._window.status_bar.set_status("파일 정리 시작...", "ok")
        self._window.loading_overlay.show_loading("파일 정리 중...")

    def on_organize_progress(self, progress: OperationProgress) -> None:
        """Handle organize progress updates."""
        message = progress.message or f"{progress.current}/{progress.total}"
        self._window.status_bar.set_status(message, "ok")

    def on_organize_finished(self, _results: list) -> None:
        """Handle organize completion."""
        self._window.loading_overlay.hide_loading()
        self._window.status_bar.set_status("정리 완료", "ok")
        self._window._refresh_statistics(pending_override=0)
        self._window._refresh_status_bar()

    def on_organize_error(self, error: OperationError) -> None:
        """Handle organize errors."""
        self._window.loading_overlay.hide_loading()
        self._window.status_bar.set_status(error.message, "error")

    def _resolve_organize_directory(self) -> Path | None:
        """Resolve the organize directory from settings or scan results."""
        if self._window.app_context.settings.folders and self._window.app_context.settings.folders.source_folder:
            source_path = Path(self._window.app_context.settings.folders.source_folder)
            if source_path.exists() and source_path.is_dir():
                return source_path

        results = self._window._subtitle_scan_results if self._window._current_view == "subtitles" else self._window._scan_results
        if results:
            candidate = Path(results[0].file_path).parent
            if candidate.exists() and candidate.is_dir():
                return candidate
        return None
