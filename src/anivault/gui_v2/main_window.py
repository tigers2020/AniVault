"""Main Window for GUI v2."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from anivault.gui_v2.app_context import AppContext
from anivault.gui_v2.controllers import MatchController, OrganizeController, ScanController
from anivault.gui_v2.dialogs.settings_dialog import SettingsDialog
from anivault.gui_v2.models import OperationError, OperationProgress
from anivault.gui_v2.views.base_view import BaseView
from anivault.gui_v2.views.groups_view import GroupsView
from anivault.gui_v2.widgets.detail_panel import DetailPanel
from anivault.gui_v2.widgets.header_widget import HeaderWidget
from anivault.gui_v2.widgets.loading_overlay import LoadingOverlay
from anivault.gui_v2.widgets.sidebar_widget import SidebarWidget
from anivault.gui_v2.widgets.status_bar import StatusBar
from anivault.gui_v2.widgets.toolbar_widget import ToolbarWidget

logger = logging.getLogger(__name__)


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
        self._scan_results: list = []

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

        # Main content area
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        self.sidebar = SidebarWidget()
        content_layout.addWidget(self.sidebar)

        # Workspace (toolbar + views)
        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        # Toolbar
        self.toolbar = ToolbarWidget()
        workspace_layout.addWidget(self.toolbar)

        # View stack
        self.view_stack = QStackedWidget()
        workspace_layout.addWidget(self.view_stack)

        # Create views
        self._create_views()

        content_layout.addWidget(workspace)

        # Detail panel (overlay)
        self.detail_panel = DetailPanel(central_widget)
        # Initialize position off-screen
        if self.detail_panel.parent():
            parent_width = self.detail_panel.parent().width()
            self.detail_panel.setGeometry(parent_width, 0, 500, self.detail_panel.parent().height())
        self.detail_panel.hide()

        # Loading overlay
        self.loading_overlay = LoadingOverlay(central_widget)
        if self.loading_overlay.parent():
            self.loading_overlay.setGeometry(0, 0, self.loading_overlay.parent().width(), self.loading_overlay.parent().height())
        self.loading_overlay.hide()

        main_layout.addWidget(content_widget)

        # Status bar
        self.status_bar = StatusBar()
        main_layout.addWidget(self.status_bar)

    def _create_views(self) -> None:
        """Create all view widgets.

        All tabs share the same GroupsView instance for consistent layout and data.
        Only the toolbar changes based on the selected tab.
        """
        # Create a single GroupsView instance shared by all tabs
        self.groups_view = GroupsView()
        self.view_stack.addWidget(self.groups_view)

        # All tabs use the same GroupsView - no separate views needed
        # Each tab name maps to the same groups_view (index 0)
        self._view_name_to_index = {"groups": 0, "tmdb": 0, "organize": 0, "rollback": 0, "verify": 0, "cache": 0, "logs": 0}

        # Set initial view
        self.view_stack.setCurrentWidget(self.groups_view)

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        # Header signals
        self.header.settings_clicked.connect(self._on_settings_clicked)
        self.header.scan_clicked.connect(self._on_scan_clicked)

        # Sidebar signals
        self.sidebar.view_changed.connect(self._on_view_changed)

        # Groups view signals
        self.groups_view.group_clicked.connect(self._on_group_clicked)

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

        self.toolbar.match_clicked.connect(self._on_match_clicked)
        self.toolbar.organize_preflight_clicked.connect(self._on_organize_preflight_clicked)
        self.toolbar.organize_execute_clicked.connect(self._on_organize_execute_clicked)

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

        # Get source folder from settings
        source_folder = ""
        if self.app_context.settings.folders and self.app_context.settings.folders.source_folder:
            source_folder = self.app_context.settings.folders.source_folder

        # If no source folder in settings, show file dialog
        if not source_folder:
            directory = QFileDialog.getExistingDirectory(self, "스캔할 디렉터리 선택")
            if not directory:
                return
            source_folder = directory
        else:
            # Use source folder from settings
            directory = source_folder

        # Validate directory exists
        directory_path = Path(directory)
        if not directory_path.exists() or not directory_path.is_dir():
            self.status_bar.set_status(f"설정된 소스 폴더가 유효하지 않습니다: {directory}", "error")
            # Fallback to file dialog
            directory = QFileDialog.getExistingDirectory(self, "스캔할 디렉터리 선택")
            if not directory:
                return
            directory_path = Path(directory)

        self.status_bar.set_current_path(str(directory_path))
        self.scan_controller.scan_directory(directory_path)

    def _on_view_changed(self, view_name: str) -> None:
        """Handle view change - all tabs share the same GroupsView.

        Args:
            view_name: Name of the tab to switch to (groups, tmdb, organize, etc.)
        """
        # All tabs use the same GroupsView (index 0)
        # Only toolbar changes based on view_name
        self.view_stack.setCurrentIndex(0)  # Always show groups_view
        self.toolbar.set_view(view_name)
        self.status_bar.set_status(f"탭 전환: {view_name}", "ok")

        # Ensure the shared view has the latest metadata when switching
        if self._scan_results:
            self.groups_view.set_file_metadata(self._scan_results)

    def _update_all_views_with_metadata(self, metadata: list) -> None:
        """Update all views with the shared file metadata list.

        This ensures all tabs have access to the same file metadata,
        synchronized with the groups view.

        Args:
            metadata: List of FileMetadata instances to share across all views.
        """
        for i in range(self.view_stack.count()):
            widget = self.view_stack.widget(i)
            if isinstance(widget, BaseView):
                widget.set_file_metadata(metadata)

    def _on_group_clicked(self, group_id: int) -> None:
        """Handle group card click."""
        # Find group data
        groups_view = self.groups_view
        group = next((g for g in groups_view._groups if g["id"] == group_id), None)

        if group:
            # Show detail panel
            title = group.get("title", "")
            season = group.get("season", 0)
            episodes = group.get("episodes", 0)
            resolution = group.get("resolution", "")
            meta = f"시즌 {season} | {episodes}화 | {resolution}"

            info_text = f"파일: {group.get('files', 0)}개\n해상도: {resolution}\n언어: {group.get('language', '').upper()}"

            # Generate sample file list
            files = [(f"Episode {i + 1}.mkv", f"{resolution} | {group.get('language', '').upper()}") for i in range(group.get("files", 0))]

            self.detail_panel.set_group_detail(title, meta, info_text, files)
            self.detail_panel.show_panel()

    def _initialize_defaults(self) -> None:
        """Initialize GUI with default values."""
        # Initialize with empty groups
        self.groups_view.set_groups([])

        # Initialize statistics to 0
        self.sidebar.update_statistic("totalGroups", "0")
        self.sidebar.update_statistic("totalFiles", "0")
        self.sidebar.update_statistic("matchedGroups", "0")
        self.sidebar.update_statistic("pendingOrganize", "0")

        # Initialize status bar with default values
        self.status_bar.set_status("unknown", "ok")
        self.status_bar.set_current_path("unknown")
        self.status_bar.set_cache_status("unknown")

    def showEvent(self, event: QShowEvent) -> None:
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
            logger.warning(f"Auto scan on startup: source folder does not exist: {source_folder}")
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

    def _on_scan_started(self) -> None:
        """Handle scan start."""
        self.status_bar.set_status("디렉터리 스캔 시작...", "ok")
        self.loading_overlay.show_loading("디렉터리 스캔 중...")

    def _on_scan_progress(self, progress: OperationProgress) -> None:
        """Handle scan progress updates."""
        message = progress.message or f"{progress.current}/{progress.total}"
        self.status_bar.set_status(message, "ok")

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
        self._scan_results = results
        self._update_all_views_with_metadata(results)

    def _on_scan_error(self, error: OperationError) -> None:
        """Handle scan errors."""
        self.loading_overlay.hide_loading()
        self.status_bar.set_status(error.message, "error")

    def _on_match_clicked(self) -> None:
        """Handle match button click."""
        if not self.match_controller:
            self.status_bar.set_status("매칭 컨트롤러가 초기화되지 않았습니다.", "error")
            return

        if not self._scan_results:
            self.status_bar.set_status("먼저 디렉터리를 스캔하세요.", "warn")
            return

        self.match_controller.match_files(self._scan_results)

    def _on_match_started(self) -> None:
        """Handle match start."""
        self.status_bar.set_status("TMDB 매칭 시작...", "ok")
        self.loading_overlay.show_loading("TMDB 매칭 중...")

    def _on_match_progress(self, progress: OperationProgress) -> None:
        """Handle match progress updates."""
        message = progress.message or f"{progress.current}/{progress.total}"
        self.status_bar.set_status(message, "ok")

    def _on_match_finished(self, results: list) -> None:
        """Handle match completion."""
        self.loading_overlay.hide_loading()
        self.status_bar.set_status("매칭 완료", "ok")
        self._scan_results = results
        self._update_all_views_with_metadata(results)

    def _on_match_error(self, error: OperationError) -> None:
        """Handle match errors."""
        self.loading_overlay.hide_loading()
        self.status_bar.set_status(error.message, "error")

    def _on_organize_preflight_clicked(self) -> None:
        """Handle organize preflight."""
        if not self.organize_controller:
            self.status_bar.set_status("정리 컨트롤러가 초기화되지 않았습니다.", "error")
            return

        if not self._scan_results:
            self.status_bar.set_status("먼저 매칭을 완료하세요.", "warn")
            return

        self.organize_controller.organize_files(self._scan_results, dry_run=True)

    def _on_organize_execute_clicked(self) -> None:
        """Handle organize execution."""
        if not self.organize_controller:
            self.status_bar.set_status("정리 컨트롤러가 초기화되지 않았습니다.", "error")
            return

        if not self._scan_results:
            self.status_bar.set_status("먼저 매칭을 완료하세요.", "warn")
            return

        self.organize_controller.organize_files(self._scan_results, dry_run=False)

    def _on_organize_started(self) -> None:
        """Handle organize start."""
        self.status_bar.set_status("파일 정리 시작...", "ok")
        self.loading_overlay.show_loading("파일 정리 중...")

    def _on_organize_progress(self, progress: OperationProgress) -> None:
        """Handle organize progress updates."""
        message = progress.message or f"{progress.current}/{progress.total}"
        self.status_bar.set_status(message, "ok")

    def _on_organize_finished(self, _results: list) -> None:
        """Handle organize completion."""
        self.loading_overlay.hide_loading()
        self.status_bar.set_status("정리 완료", "ok")

    def _on_organize_error(self, error: OperationError) -> None:
        """Handle organize errors."""
        self.loading_overlay.hide_loading()
        self.status_bar.set_status(error.message, "error")

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Handle window resize event."""
        super().resizeEvent(event)
        # Update detail panel and loading overlay position/size
        if self.detail_panel and self.detail_panel.isVisible():
            self.detail_panel.show_panel()
        if self.loading_overlay:
            self.loading_overlay.setGeometry(0, 0, self.width(), self.height())
