"""Main Window for GUI v2."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from anivault.gui_v2.app_context import AppContext
from anivault.gui_v2.components.layout.main_content import MainContentComponent
from anivault.gui_v2.components.layout.overlay_layer import OverlayLayerComponent
from anivault.gui_v2.controllers import MatchController, OrganizeController, ScanController
from anivault.gui_v2.dialogs.settings_dialog import SettingsDialog
from anivault.gui_v2.dialogs.tmdb_manual_search_dialog import TmdbManualSearchDialog
from anivault.gui_v2.flows.organize_execution import run_organize_execute_flow
from anivault.gui_v2.models import OperationError, OperationProgress, ViewKind, format_progress_message
from anivault.gui_v2.views.base_view import BaseView
from anivault.gui_v2.views.groups_view import GroupsView
from anivault.gui_v2.widgets.header_widget import HeaderWidget
from anivault.gui_v2.widgets.status_bar import StatusBar
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent, QShowEvent


class MainWindow(QMainWindow):
    """Main window for AniVault GUI v2."""

    def __init__(
        self,
        parent: QWidget | None = None,
        app_context: AppContext | None = None,
    ) -> None:
        """Initialize main window."""
        super().__init__(parent)
        self.setWindowTitle("AniVault - 애니메이션 컬렉션 관리")
        self.setGeometry(100, 100, 1600, 900)

        self.app_context = app_context

        # Controllers
        self.scan_controller: ScanController | None = None
        self.match_controller: MatchController | None = None
        self.organize_controller: OrganizeController | None = None
        self._scan_results: list[FileMetadata] = []
        self._subtitle_scan_results: list[FileMetadata] = []
        self._current_view = "work"
        self._active_scan_target = ViewKind.VIDEOS.value
        self._active_match_target = ViewKind.VIDEOS.value
        self._current_detail_group: dict | None = None
        self._progress_ui_last_update: float | None = None  # throttle progress UI updates
        self._pending_progress: OperationProgress | None = None
        self._progress_flush_timer: QTimer | None = None  # coalesce progress UI updates

        # Components
        self.settings_dialog: SettingsDialog | None = None

        # Setup UI
        self._setup_controllers()
        self._setup_ui()
        self._setup_connections()
        self._initialize_defaults()

        logger.info("MainWindow initialized")

    def _setup_ui(self) -> None:
        """Set up the main window UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        self.header = HeaderWidget()
        main_layout.addWidget(self.header)

        # Main content (sidebar + workspace)
        self.main_content = MainContentComponent()
        self.sidebar = self.main_content.sidebar
        self.workspace = self.main_content.workspace
        self._create_views()

        # Overlay layer (detail panel + loading overlay)
        self.overlay_layer = OverlayLayerComponent(central_widget)
        self.detail_panel = self.overlay_layer.detail_panel
        self.loading_overlay = self.overlay_layer.loading_overlay

        main_layout.addWidget(self.main_content)

        # Status bar
        self.status_bar = StatusBar()
        main_layout.addWidget(self.status_bar)

    def _create_views(self) -> None:
        """Create all view widgets.

        All tabs share the same GroupsView instance for consistent layout and data.
        Only the toolbar changes based on the selected tab.
        """
        self.groups_view = GroupsView(
            build_groups_use_case_factory=lambda: self.app_context.container.build_groups_use_case(),
        )
        self.workspace.add_view(self.groups_view)
        self._view_name_to_index = {
            "work": 0,
            "groups": 0,
            "tmdb": 0,
            "organize": 0,
            "subtitles": 0,
        }
        self.workspace.view_stack.setCurrentWidget(self.groups_view)

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        # Header signals
        self.header.settings_clicked.connect(self._on_settings_clicked)
        self.header.scan_clicked.connect(self._on_scan_clicked)

        # Sidebar signals
        self.sidebar.view_changed.connect(self._on_view_changed)

        # Groups view signals
        self.groups_view.group_clicked.connect(self._on_group_clicked)
        self.groups_view.groups_build_progress.connect(self._on_groups_build_progress)
        self.groups_view.groups_build_finished.connect(self._on_groups_build_finished)

        # Detail panel signals
        self.detail_panel.match_clicked.connect(self._on_detail_match_clicked)

        if self.scan_controller:
            self.scan_controller.operation_started.connect(self._on_scan_started)
            self.scan_controller.operation_progress.connect(self._on_scan_progress)
            self.scan_controller.operation_finished.connect(self._on_scan_finished)
            self.scan_controller.operation_error.connect(self._on_scan_error)

        if self.match_controller:
            self.match_controller.operation_started.connect(self._on_match_started)
            self.match_controller.operation_progress.connect(self._on_match_progress)
            self.match_controller.operation_finished.connect(self._on_match_finished)
            self.match_controller.operation_error.connect(self._on_match_error)

        if self.organize_controller:
            self.organize_controller.operation_started.connect(self._on_organize_started)
            self.organize_controller.operation_progress.connect(self._on_organize_progress)
            self.organize_controller.operation_finished.connect(self._on_organize_finished)
            self.organize_controller.operation_error.connect(self._on_organize_error)

        self.workspace.match_clicked.connect(self._on_match_clicked)
        self.workspace.organize_preflight_clicked.connect(self._on_organize_preflight_clicked)
        self.workspace.organize_execute_clicked.connect(self._on_organize_execute_clicked)

    def _on_settings_clicked(self) -> None:
        """Handle settings button click."""
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self.app_context, self)
        self.settings_dialog.show()

    def _on_scan_clicked(self) -> None:
        """Handle scan button click."""
        if not self.scan_controller:
            self.status_bar.set_status("스캔 컨트롤러가 초기화되지 않았습니다.", "error")
            return

        source_folder = ""
        if self.app_context.settings.folders and self.app_context.settings.folders.source_folder:
            source_folder = self.app_context.settings.folders.source_folder

        if not source_folder:
            directory = QFileDialog.getExistingDirectory(self, "스캔할 디렉터리 선택")
            if not directory:
                return
            source_folder = directory

        directory_path = Path(source_folder)
        if not directory_path.exists() or not directory_path.is_dir():
            self.status_bar.set_status(f"설정된 소스 폴더가 유효하지 않습니다: {source_folder}", "error")
            directory = QFileDialog.getExistingDirectory(self, "스캔할 디렉터리 선택")
            if not directory:
                return
            directory_path = Path(directory)

        self.status_bar.set_current_path(str(directory_path))
        if self.is_subtitles_view():
            self._active_scan_target = ViewKind.SUBTITLES.value
            self.scan_controller.scan_subtitle_directory(directory_path)
        else:
            self._active_scan_target = ViewKind.VIDEOS.value
            self.scan_controller.scan_directory(directory_path)

    def _on_scan_started(self) -> None:
        """Handle scan start."""
        self._reset_progress_ui_throttle()
        self.status_bar.set_status("디렉터리 스캔 시작...", "ok")
        self.loading_overlay.show_loading("디렉터리 스캔 중...")

    def _on_scan_progress(self, progress: OperationProgress) -> None:
        """Handle scan progress updates (throttled)."""
        self._maybe_update_progress_ui(progress)

    def _on_scan_finished(self, results: list) -> None:
        """Handle scan completion."""
        logger.info("Scan finished: received %d results (type: %s)", len(results), type(results).__name__)
        if results:
            logger.info(
                "First result type: %s, keys: %s",
                type(results[0]).__name__,
                list(results[0].__dict__.keys()) if hasattr(results[0], "__dict__") else "N/A",
            )
        self.loading_overlay.hide_loading()
        self.status_bar.set_status("스캔 완료", "ok")

        if self._active_scan_target == ViewKind.SUBTITLES.value:
            self._subtitle_scan_results = results
            if self.is_subtitles_view():
                self.groups_view.set_file_metadata(results)
                self._refresh_statistics()
            self._refresh_status_bar()
            if results and self.match_controller:
                logger.info("Auto-matching started after subtitle scan completion")
                self._active_match_target = ViewKind.SUBTITLES.value
                self.match_controller.match_files(results)
            return

        self._scan_results = results
        self._update_all_views_with_metadata(results)
        self._refresh_statistics()
        self._refresh_status_bar()

        if results and self.match_controller:
            logger.info("Auto-matching started after scan completion")
            self._active_match_target = ViewKind.VIDEOS.value
            self.match_controller.match_files(results)

    def _on_scan_error(self, error: OperationError) -> None:
        """Handle scan errors."""
        self.loading_overlay.hide_loading()
        self.status_bar.set_status(error.message, "error")

    def _on_match_clicked(self) -> None:
        """Handle match button click."""
        if not self.match_controller:
            self.status_bar.set_status("매칭 컨트롤러가 초기화되지 않았습니다.", "error")
            return

        files = self.get_current_scan_results()
        if not files:
            self.status_bar.set_status("먼저 디렉터리를 스캔하세요.", "warn")
            return

        self.set_active_match_target_from_view()
        self.match_controller.match_files(files)

    def _on_match_started(self) -> None:
        """Handle match start."""
        self._reset_progress_ui_throttle()
        self.status_bar.set_status("TMDB 매칭 시작...", "ok")
        self.loading_overlay.show_loading("TMDB 매칭 중...")

    def _on_match_progress(self, progress: OperationProgress) -> None:
        """Handle match progress updates (throttled)."""
        self._maybe_update_progress_ui(progress)

    def _on_match_finished(self, results: list) -> None:
        """Handle match completion."""
        logger.debug("Match finished: received %d results", len(results))
        self.loading_overlay.hide_loading()
        self.status_bar.set_status("매칭 완료", "ok")

        if self._active_match_target == ViewKind.SUBTITLES.value:
            self._subtitle_scan_results = results
            if self.is_subtitles_view():
                self.groups_view.set_file_metadata(results)
                self._refresh_statistics()
            self._refresh_status_bar()
            return

        self._scan_results = results
        self._update_all_views_with_metadata(results)
        self._refresh_statistics()
        self._refresh_status_bar()

    def _on_match_error(self, error: OperationError) -> None:
        """Handle match errors."""
        self.loading_overlay.hide_loading()
        self.status_bar.set_status(error.message, "error")

    def _on_organize_preflight_clicked(self) -> None:
        """Handle organize preflight (dry run)."""
        if not self.organize_controller:
            self.status_bar.set_status("정리 컨트롤러가 초기화되지 않았습니다.", "error")
            return

        files = self.get_current_scan_results()
        if not files:
            self.status_bar.set_status("먼저 매칭을 완료하세요.", "warn")
            return

        self.organize_controller.organize_files(files, dry_run=True)

    def _on_organize_execute_clicked(self) -> None:
        """Handle organize execution: delegate to flow module."""
        run_organize_execute_flow(self, self._refresh_list_after_organize)

    def _on_organize_started(self) -> None:
        """Handle organize start."""
        self._reset_progress_ui_throttle()
        self.status_bar.set_status("파일 정리 시작...", "ok")
        self.loading_overlay.show_loading("파일 정리 중...")

    def _on_organize_progress(self, progress: OperationProgress) -> None:
        """Handle organize progress updates (throttled)."""
        self._maybe_update_progress_ui(progress)

    def _on_organize_finished(self, _results: list) -> None:
        """Handle organize completion."""
        self.loading_overlay.hide_loading()
        self.status_bar.set_status("정리 완료", "ok")
        self._refresh_list_after_organize()

    def _on_organize_error(self, error: OperationError) -> None:
        """Handle organize errors."""
        self.loading_overlay.hide_loading()
        self.status_bar.set_status(error.message, "error")

    def _refresh_list_after_organize(self) -> None:
        """Clear scan results and refresh groups list after files were moved."""
        self._scan_results = []
        self._subtitle_scan_results = []
        self.groups_view.set_file_metadata([])
        self.detail_panel.hide_panel()
        self._refresh_statistics(pending_override=0)
        self._refresh_status_bar()

    def _on_view_changed(self, view_name: str) -> None:
        """Handle view change - all tabs share the same GroupsView.

        Args:
            view_name: Name of the tab to switch to (groups, tmdb, organize, etc.)
        """
        self._current_view = view_name
        self.workspace.set_view(view_name)
        self.status_bar.set_status(f"탭 전환: {view_name}", "ok")

        # Ensure the shared view has the latest metadata when switching
        if view_name == ViewKind.SUBTITLES.value:
            if self._subtitle_scan_results:
                self.groups_view.set_file_metadata(self._subtitle_scan_results)
                self._refresh_statistics()
        elif self._scan_results:
            self.groups_view.set_file_metadata(self._scan_results)
            self._refresh_statistics()

    def _update_all_views_with_metadata(self, metadata: list) -> None:
        """Update all views with the shared file metadata list.

        This ensures all tabs have access to the same file metadata,
        synchronized with the groups view.

        Args:
            metadata: List of FileMetadata instances to share across all views.
        """
        stack = self.workspace.view_stack
        for i in range(stack.count()):
            widget = stack.widget(i)
            if isinstance(widget, BaseView):
                widget.set_file_metadata(metadata)

    def _on_group_clicked(self, group_id: int) -> None:
        """Handle group card click: pass group dict to DetailPanel."""
        group = next((g for g in self.groups_view._groups if g["id"] == group_id), None)
        self._current_detail_group = group
        self.detail_panel.set_group_data(group)

    def _reset_progress_ui_throttle(self) -> None:
        """Reset progress UI throttle and cancel any pending flush."""
        self._progress_ui_last_update = None
        self._pending_progress = None
        if self._progress_flush_timer is not None:
            self._progress_flush_timer.stop()
            self._progress_flush_timer = None

    def _maybe_update_progress_ui(self, progress: OperationProgress) -> None:
        """Coalesce progress updates: store and flush at most every 150ms to avoid UI freeze."""
        is_final = progress.total > 0 and progress.current >= progress.total
        if is_final:
            self._pending_progress = None
            if self._progress_flush_timer is not None:
                self._progress_flush_timer.stop()
                self._progress_flush_timer = None
            self._do_update_progress_ui(progress)
            return
        self._pending_progress = progress
        if self._progress_flush_timer is None or not self._progress_flush_timer.isActive():
            self._progress_flush_timer = QTimer(self)
            self._progress_flush_timer.setSingleShot(True)
            self._progress_flush_timer.timeout.connect(self._flush_pending_progress)
            self._progress_flush_timer.start(150)

    def _flush_pending_progress(self) -> None:
        """Flush one coalesced progress update to the UI."""
        if self._progress_flush_timer is not None:
            self._progress_flush_timer = None
        p = self._pending_progress
        self._pending_progress = None
        if p is not None:
            self._do_update_progress_ui(p)

    def _do_update_progress_ui(self, progress: OperationProgress) -> None:
        """Actually update status bar and loading overlay."""
        self._progress_ui_last_update = time.monotonic()
        message = format_progress_message(progress)
        self.status_bar.set_status(message, "ok")
        self.loading_overlay.show_loading(
            progress.message or f"{progress.current}/{progress.total}",
            current=progress.current,
            total=progress.total,
        )
        self.status_bar.update()
        self.loading_overlay.update()
        app = QApplication.instance()
        if app is not None:
            app.processEvents()

    def _on_groups_build_progress(self, progress: OperationProgress) -> None:
        """Handle groups build progress: update status bar and loading overlay."""
        if progress.current == 0:
            self._reset_progress_ui_throttle()
        self._maybe_update_progress_ui(progress)

    def _on_groups_build_finished(self) -> None:
        """Handle groups build finished: hide loading overlay."""
        self.loading_overlay.hide_loading()

    def _get_detail_match_context(
        self,
    ) -> tuple[object, str, list] | None:
        """Validate preconditions and return (tmdb_client, group_title, file_metadata_list), or None on failure."""
        if not self._current_detail_group:
            self.status_bar.set_status("그룹 정보를 찾을 수 없습니다.", "warn")
            return None
        file_metadata_list = self._current_detail_group.get("file_metadata_list", [])
        if not file_metadata_list:
            self.status_bar.set_status("매칭할 파일이 없습니다.", "warn")
            return None
        if not self.app_context or not self.app_context.container:
            self.status_bar.set_status("앱 컨텍스트를 사용할 수 없습니다.", "error")
            return None
        tmdb_settings = getattr(
            getattr(self.app_context.settings, "api", None),
            "tmdb",
            None,
        )
        if not tmdb_settings or not getattr(tmdb_settings, "api_key", None):
            self.status_bar.set_status("TMDB API 키를 먼저 설정해주세요.", "warn")
            return None
        tmdb_client = self.app_context.container.tmdb_client()
        group_title = self._current_detail_group.get("title", "")
        return (tmdb_client, group_title, file_metadata_list)

    def _merge_updated_metadata_into_results(
        self,
        updated_list: list[FileMetadata],
        scan_results: list[FileMetadata],
    ) -> list[FileMetadata]:
        """Merge dialog-updated metadata back into scan results by resolved path."""

        def path_resolved(p: Path) -> Path:
            try:
                return p.resolve()
            except OSError:
                return p

        updated_resolved = {path_resolved(fm.file_path) for fm in updated_list}
        updated_by_path: dict[Path, FileMetadata] = {path_resolved(fm.file_path): fm for fm in updated_list}
        merged: list[FileMetadata] = []
        for fm in scan_results:
            pr = path_resolved(fm.file_path)
            merged.append(updated_by_path[pr] if pr in updated_resolved else fm)
        return merged

    def _set_scan_results_for_current_view(self, merged: list[FileMetadata]) -> None:
        """Assign merged list to the correct scan results for current view."""
        if self.is_subtitles_view():
            self._subtitle_scan_results = merged
        else:
            self._scan_results = merged

    def is_subtitles_view(self) -> bool:
        """Return True if the current tab is subtitles (subtitle scan results)."""
        return self._current_view == ViewKind.SUBTITLES.value

    def get_current_scan_results(self) -> list[FileMetadata]:
        """Return the scan results list for the current view (single source of truth)."""
        return (
            self._subtitle_scan_results
            if self.is_subtitles_view()
            else self._scan_results
        )

    def set_current_scan_results(self, merged: list[FileMetadata]) -> None:
        """Set the scan results for the current view (single entry point)."""
        self._set_scan_results_for_current_view(merged)

    def get_active_match_target_value(self) -> str:
        """Return the active match target: ViewKind.SUBTITLES.value or ViewKind.VIDEOS.value."""
        return (
            ViewKind.SUBTITLES.value
            if self.is_subtitles_view()
            else ViewKind.VIDEOS.value
        )

    def set_active_match_target_from_view(self) -> None:
        """Set _active_match_target from current view (subtitles vs videos)."""
        self._active_match_target = self.get_active_match_target_value()

    def _on_detail_match_clicked(self) -> None:
        """Handle TMDB match button in detail panel - open manual search dialog."""
        context = self._get_detail_match_context()
        if context is None:
            return
        tmdb_client, group_title, file_metadata_list = context

        dialog = TmdbManualSearchDialog(
            group_title=group_title,
            file_metadata_list=file_metadata_list,
            tmdb_client=tmdb_client,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.status_bar.set_status("TMDB 매칭이 취소되었습니다.", "ok")
            return
        updated_list = dialog.get_updated_metadata()
        if not updated_list:
            logger.warning("get_updated_metadata returned empty")
            return

        scan_results = self.get_current_scan_results()
        merged = self._merge_updated_metadata_into_results(updated_list, scan_results)
        self.set_current_scan_results(merged)
        self.groups_view.set_file_metadata(merged)
        self._refresh_statistics()
        self.detail_panel.hide_panel()
        self.status_bar.set_status("TMDB 매칭이 적용되었습니다.", "ok")

    def _initialize_defaults(self) -> None:
        """Initialize GUI with default values."""
        # Initialize with empty groups
        self.groups_view.set_groups([])

        self.workspace.set_view("work")

        self.sidebar.update_statistics_from_data([], 0)
        self.status_bar.set_status("unknown", "ok")
        self.status_bar.refresh_from_context("unknown", has_scan_results=False)

    def _refresh_statistics(self, *, pending_override: int | None = None) -> None:
        """Recalculate and update sidebar statistics (data only; SidebarWidget computes)."""
        groups = self.groups_view._groups
        scan_results = self.get_current_scan_results()
        total_files = len(scan_results) if scan_results else sum(int(g.get("files", 0) or 0) for g in groups)
        self.sidebar.update_statistics_from_data(groups, total_files, pending_override)

    def _refresh_status_bar(self) -> None:
        """Refresh status bar path and cache status (data only; StatusBar updates display)."""
        source_folder = ""
        if self.app_context and self.app_context.settings.folders:
            source_folder = self.app_context.settings.folders.source_folder or ""
        has_results = bool(self._scan_results or self._subtitle_scan_results)
        self.status_bar.refresh_from_context(source_folder, has_results)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        """Handle window show event."""
        super().showEvent(event)
        # Check for auto scan on startup
        self._check_auto_scan_startup()

    def _check_auto_scan_startup(self) -> None:
        """Check if auto scan on startup is enabled and trigger scan if needed."""
        if not self.app_context or not self.scan_controller:
            return

        settings = self.app_context.settings
        if not settings.folders:
            return

        # Check if auto scan on startup is enabled
        if not settings.folders.auto_scan_on_startup:
            return

        # Check if source folder is configured
        source_folder = settings.folders.source_folder
        if not source_folder:
            logger.warning("Auto scan on startup enabled but source folder not configured")
            return

        # Validate source folder exists
        source_path = Path(source_folder)
        if not source_path.exists() or not source_path.is_dir():
            logger.warning(
                "Auto scan on startup: source folder does not exist: %s",
                source_folder,
            )
            return

        # Trigger auto scan after a short delay to ensure UI is fully rendered
        QTimer.singleShot(500, lambda: self._trigger_auto_scan(source_path))

    def _trigger_auto_scan(self, directory_path: Path) -> None:
        """Trigger automatic scan of configured directory.

        Args:
            directory_path: Path to directory to scan.
        """
        logger.info("Auto scan on startup: scanning %s", directory_path)
        self.status_bar.set_current_path(str(directory_path))
        self.scan_controller.scan_directory(directory_path)

    def _setup_controllers(self) -> None:
        """Initialize controllers."""
        if not self.app_context:
            logger.warning("AppContext not available; controllers not initialized")
            return
        self.scan_controller = ScanController(self.app_context)
        self.match_controller = MatchController(self.app_context)
        self.organize_controller = OrganizeController(self.app_context)

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Handle window resize event."""
        super().resizeEvent(event)
        if self.overlay_layer:
            self.overlay_layer.update_geometry()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Stop scan process on window close so the child process does not outlive the app."""
        if self.scan_controller is not None:
            self.scan_controller.cleanup()
        super().closeEvent(event)
