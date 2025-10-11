"""
Main Window Implementation for AniVault GUI

This module contains the main window class that serves as the root container
for all UI elements in the AniVault GUI application.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from anivault.config.settings import get_config
from anivault.shared.constants.gui_messages import DialogMessages, DialogTitles
from anivault.shared.errors import ApplicationError

from .controllers import OrganizeController, ScanController, TMDBController
from .dialogs.organize_preview_dialog import OrganizePreviewDialog
from .dialogs.organize_progress_dialog import OrganizeProgressDialog
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.tmdb_progress_dialog import TMDBProgressDialog
from .state_model import StateModel
from .themes import ThemeManager
from .widgets import GroupGridViewWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window for AniVault GUI.

    This class serves as the root container for all UI elements including
    the file tree, main work area, and log panel.
    """

    # Signals
    directory_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowTitle("AniVault - Anime File Organizer")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize state model
        self.state_model = StateModel(self)

        # Initialize controllers
        self.scan_controller = ScanController(self)
        self.tmdb_controller = TMDBController(parent=self)
        self.organize_controller = OrganizeController(parent=self)

        # Initialize TMDB matching components
        self.tmdb_progress_dialog = None

        # Initialize theme-related attributes
        self.theme_manager = None
        self.theme_action_group = None
        self.config_path = Path("config/config.toml")

        # Initialize UI components
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_status_bar()

        # Connect signals
        self._connect_signals()

        logger.info("MainWindow initialized successfully")

    def _setup_ui(self) -> None:
        """Set up the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panels (vertical layout: top/bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)

        # Group grid view widget (top panel - 80%)
        self.group_view = GroupGridViewWidget()
        splitter.addWidget(self.group_view)

        # Main work area (bottom panel - 20%) - file details view
        self.work_area = QWidget()
        work_layout = QVBoxLayout(self.work_area)

        # Group details header
        self.group_details_label = QLabel("Select a group to view details")
        self.group_details_label.setObjectName("groupDetailsLabel")
        work_layout.addWidget(self.group_details_label)

        # File list for selected group
        self.file_list = QListWidget()
        # Note: Styling is now handled by the central QSS theme system
        work_layout.addWidget(self.file_list)

        splitter.addWidget(self.work_area)

        # Set splitter proportions (top: 80%, bottom: 20% = 4:1 ratio)
        splitter.setSizes([960, 240])

    def _setup_menu(self) -> None:
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        # Open Folder action
        self.open_folder_action = QAction("&Open Folder", self)
        self.open_folder_action.setShortcut("Ctrl+O")
        self.open_folder_action.setObjectName("openFolderAction")
        self.open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(self.open_folder_action)

        file_menu.addSeparator()

        # Organize Files action
        self.organize_action = QAction("📦 &Organize Files...", self)
        self.organize_action.setShortcut("Ctrl+Shift+O")
        self.organize_action.setObjectName("organizeFilesAction")
        self.organize_action.triggered.connect(self.organize_files)
        self.organize_action.setEnabled(False)  # Enabled after matching
        file_menu.addAction(self.organize_action)

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("&Settings")

        # API Key action
        self.api_key_action = QAction("Configure &API Key...", self)
        self.api_key_action.setShortcut("Ctrl+K")
        self.api_key_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(self.api_key_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        # Theme submenu
        theme_menu = view_menu.addMenu("&Theme")

        # Create theme action group for exclusive selection
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)

        # Light theme action
        light_theme_action = QAction("&Light", self)
        light_theme_action.setCheckable(True)
        light_theme_action.setData("light")
        light_theme_action.triggered.connect(
            lambda: self.switch_theme(light_theme_action),
        )
        self.theme_action_group.addAction(light_theme_action)
        theme_menu.addAction(light_theme_action)

        # Dark theme action
        dark_theme_action = QAction("&Dark", self)
        dark_theme_action.setCheckable(True)
        dark_theme_action.setData("dark")
        dark_theme_action.triggered.connect(
            lambda: self.switch_theme(dark_theme_action),
        )
        self.theme_action_group.addAction(dark_theme_action)
        theme_menu.addAction(dark_theme_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self) -> None:
        """Set up the toolbar."""
        toolbar = self.addToolBar("Main Toolbar")

        # Open Folder button - use the same action from menu
        toolbar.addAction(self.open_folder_action)

        toolbar.addSeparator()

        # Organize Files button
        toolbar.addAction(self.organize_action)

        toolbar.addSeparator()

        # Placeholder for future actions
        toolbar.addWidget(QWidget())  # Spacer

    def _setup_status_bar(self) -> None:
        """Set up the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Add cache status label as permanent widget
        self.cache_status_label = QLabel("캐시: 초기화 중...")
        self.cache_status_label.setToolTip("캐시 히트율 및 항목 수 정보")
        self.status_bar.addPermanentWidget(self.cache_status_label)

    def update_cache_status(self, stats: dict[str, Any]) -> None:
        """Update cache status display in status bar.

        Args:
            stats: Dictionary containing cache statistics:
                - hit_ratio: Cache hit ratio percentage (0.0-100.0)
                - total_requests: Total cache requests (hits + misses)
                - cache_items: Total items in cache
                - cache_type: Primary cache type (SQLite/JSON/Hybrid)
        """
        if not isinstance(stats, dict):
            logger.warning("Invalid stats type: %s", type(stats))
            return

        hit_ratio = stats.get("hit_ratio", 0.0)
        cache_items = stats.get("cache_items", 0)
        cache_type = stats.get("cache_type", "Unknown")

        # Format: 캐시: 87.3% 히트율 (1,247 항목) [SQLite]
        status_text = (
            f"캐시: {hit_ratio:.1f}% 히트율 ({cache_items:,} 항목) [{cache_type}]"
        )
        self.cache_status_label.setText(status_text)

    def open_folder(self) -> None:
        """Open folder selection dialog."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Open Folder",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if directory:
            logger.info("Folder opened: %s", directory)
            self.status_bar.showMessage(f"Opened: {directory}")

            # Update state model
            self.state_model.selected_directory = Path(directory)

            # Start file scanning
            self.start_file_scan()

    def switch_theme(self, action: QAction) -> None:
        """Switch the application theme."""
        if not self.theme_manager:
            logger.warning("Theme manager not available")
            return

        # Validate action type
        if not isinstance(action, QAction):
            logger.error("Invalid action type: %s", type(action))
            return

        try:
            theme_name = action.data()
            if not theme_name:
                logger.error("No theme data found in action")
                return

            logger.info("Switching to theme: %s", theme_name)

            # Apply the theme
            app = QApplication.instance()
            if app:
                self.theme_manager.load_and_apply_theme(app, theme_name)
            else:
                logger.error("No QApplication instance found")
                return

            # Save theme preference to settings
            try:
                config = get_config()
                config.app.theme = theme_name
                config.to_toml_file("config/config.toml")
                logger.info("Theme preference saved: %s", theme_name)
            except (OSError, ValueError) as e:
                logger.warning("Failed to save theme preference: %s", e)

            # Update status bar
            self.status_bar.showMessage(f"Theme switched to {theme_name.title()}", 3000)

            logger.info("Theme switched successfully to: %s", theme_name)

        except (OSError, ValueError, RuntimeError) as e:
            logger.exception("Failed to switch theme")
            QMessageBox.warning(
                self,
                DialogTitles.ERROR,
                f"Failed to switch theme: {e}",
            )

    def set_theme_manager(self, theme_manager: ThemeManager) -> None:
        """Set theme manager for theme switching."""
        self.theme_manager = theme_manager

        # Set initial theme selection based on current theme
        if self.theme_manager and self.theme_action_group:
            current_theme = self.theme_manager.get_current_theme()
            if current_theme:
                for action in self.theme_action_group.actions():
                    if action.data() == current_theme:
                        action.setChecked(True)
                        break

    def show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About AniVault",
            "AniVault - Anime File Organizer\n\n"
            "A tool for organizing anime files using TMDB metadata.\n\n"
            "Version: 1.0.0",
        )

    def _connect_signals(self) -> None:
        """Connect signals between components."""
        # Connect state model signals
        self.state_model.files_updated.connect(self.on_files_updated)
        self.state_model.file_status_changed.connect(self.on_file_status_changed)

        # Connect group view signal
        self.group_view.groupSelected.connect(self.on_group_selected)

        # Connect scan controller signals
        self.scan_controller.scan_started.connect(self.on_scan_started)
        self.scan_controller.scan_progress.connect(self.on_scan_progress)
        self.scan_controller.scan_finished.connect(self.on_scan_finished)
        self.scan_controller.scan_error.connect(self.on_scan_error)
        self.scan_controller.files_grouped.connect(self.on_files_grouped)

        # Connect TMDB controller signals
        self.tmdb_controller.matching_started.connect(self.on_tmdb_matching_started)
        self.tmdb_controller.file_matched.connect(self.on_tmdb_file_matched)
        self.tmdb_controller.matching_progress.connect(self.on_tmdb_matching_progress)
        self.tmdb_controller.matching_finished.connect(self.on_tmdb_matching_finished)
        self.tmdb_controller.matching_error.connect(self.on_tmdb_matching_error)
        self.tmdb_controller.matching_cancelled.connect(self.on_tmdb_matching_cancelled)
        self.tmdb_controller.cache_stats_updated.connect(self.update_cache_status)

        # Connect organize controller signals
        self.organize_controller.plan_generated.connect(
            self._on_organize_plan_generated,
        )

    def start_file_scan(self) -> None:
        """Start file scanning using scan controller."""
        if not self.state_model.selected_directory:
            logger.warning("No directory selected for scanning")
            return

        try:
            self.scan_controller.scan_directory(self.state_model.selected_directory)
        except ValueError as e:
            logger.exception("Failed to start file scan")
            self.status_bar.showMessage(DialogMessages.SCAN_ERROR.format(error=e))
            QMessageBox.warning(
                self,
                DialogTitles.SCAN_ERROR,
                f"Failed to start scan:\n{e}",
            )

    def on_scan_started(self) -> None:
        """Handle scan started signal."""
        self.status_bar.showMessage("Scanning for media files...")
        logger.info("File scan started")

    def on_scan_progress(self, progress: int) -> None:
        """Handle scan progress signal."""
        self.status_bar.showMessage(f"Scanning... {progress}%")

    def on_scan_finished(self, file_items: list) -> None:
        """Handle scan finished signal."""
        # Update state model
        self.state_model.add_scanned_files(file_items)

        self.status_bar.showMessage(f"Scan complete. Found {len(file_items)} files")
        logger.info("File scan completed successfully")

        # Start file grouping after scan completion
        if file_items:
            try:
                self.scan_controller.group_files(file_items)
            except ValueError as e:
                logger.exception("File grouping failed")
                self.status_bar.showMessage(f"Grouping failed: {e}")

    def on_scan_error(self, error_msg: str) -> None:
        """Handle scan error signal."""
        self.status_bar.showMessage(f"Scan error: {error_msg}")
        logger.error("File scan error: %s", error_msg)

        # Show error dialog
        QMessageBox.warning(
            self,
            DialogTitles.SCAN_ERROR,
            f"Failed to scan directory:\n{error_msg}",
        )

    def on_files_grouped(self, grouped_files: dict) -> None:
        """Handle files grouped signal and auto-start TMDB matching."""
        self.update_file_tree_with_groups(grouped_files)

        # Auto-start TMDB matching after grouping (only if not already in progress and not a regroup)
        # Skip auto-start if this is a regroup after TMDB matching to prevent infinite loop
        if not self.tmdb_controller.is_matching and not getattr(
            self,
            "_is_regrouping",
            False,
        ):
            logger.info("Auto-starting TMDB matching after file grouping")

            # Check if API key is configured before starting
            try:
                config = get_config()
                api_key = config.tmdb.api_key
            except (ApplicationError, OSError, ValueError):
                logger.warning("Skipping auto TMDB match: Failed to load config")
                return

            if api_key and self.state_model.scanned_files:
                self.start_tmdb_matching()
            else:
                logger.warning(
                    "Skipping auto TMDB match: API key not configured or no files",
                )
        elif self.tmdb_controller.is_matching:
            logger.info("Skipping auto TMDB match: matching already in progress")
        else:
            logger.info("Skipping auto TMDB match: this is a regroup operation")

    def on_files_updated(self, files: list) -> None:
        """Handle files updated signal from state model."""
        logger.info("Files updated in state model: %d files", len(files))

    def on_file_status_changed(self, file_path: Path, status: str) -> None:
        """Handle file status changed signal from state model."""
        # Note: File status updates are now handled by the state model and group view
        # No direct file tree manipulation needed
        logger.debug("File status updated: %s -> %s", file_path.name, status)

    def update_file_tree_with_groups(self, grouped_files: dict) -> None:
        """Update the group grid view with grouped files as cards."""
        # Update the grid view with grouped files and connect click events
        self.group_view.update_groups(grouped_files, self.on_group_selected)

        total_files = sum(len(files) for files in grouped_files.values())
        logger.info(
            "Updated group grid view with %d grouped files in %d groups",
            total_files,
            len(grouped_files),
        )

    def on_group_selected(self, group_name: str, files: list) -> None:
        """Handle group selection from grid view.

        Supports both ScannedFile and FileItem objects.
        """
        # Update group details header
        self.group_details_label.setText(f"📁 {group_name} ({len(files)} files)")

        # Clear and populate file list
        self.file_list.clear()

        for file_item in files:
            # Duck typing: get file path and name safely
            file_path = getattr(file_item, "file_path", None)
            if isinstance(file_path, Path):
                file_name = file_path.name
                file_text = f"{file_name}\n{file_path}"
            else:
                # Fallback for FileItem with file_name attribute
                file_name = getattr(file_item, "file_name", "Unknown")
                file_path_str = str(file_path) if file_path else "Unknown path"
                file_text = f"{file_name}\n{file_path_str}"

            self.file_list.addItem(file_text)

        logger.debug("Selected group: %s with %d files", group_name, len(files))

    def update_file_tree(self, files: list) -> None:
        """Update the group view with scanned files (fallback for ungrouped display)."""
        # Clear existing groups
        self.group_view.clear_groups()

        # Create a single group for all files if no grouping is performed
        if files:
            file_items = list(files)

            self.group_view.add_group("All Files", file_items)

        logger.info("Updated group view with %d files (ungrouped)", len(files))
        self.status_bar.showMessage(f"Found {len(files)} files")

    def open_settings_dialog(self) -> None:
        """Open the settings dialog for API key configuration."""
        try:
            dialog = SettingsDialog(self, self.config_path)

            # Connect signal
            dialog.api_key_saved.connect(self._on_api_key_saved)

            # Show dialog
            dialog.exec()

        except (RuntimeError, OSError) as e:
            logger.exception("Failed to open settings dialog")
            QMessageBox.critical(
                self,
                DialogTitles.ERROR,
                f"Failed to open settings dialog: {e!s}",
            )

    def _on_api_key_saved(self, _api_key: str) -> None:
        """
        Handle API key saved signal.

        Args:
            _api_key: The saved API key (unused, required by signal signature)
        """
        logger.info("API key saved successfully")
        self.status_bar.showMessage("API key saved successfully")

    def start_tmdb_matching(self) -> None:
        """Start TMDB matching process for scanned files."""
        # Check if files are available for matching
        if not self.state_model.scanned_files:
            QMessageBox.warning(
                self,
                DialogTitles.WARNING,
                "Please scan a directory first before starting TMDB matching.",
            )
            return

        # Check if API key is configured
        try:
            config = get_config()
            api_key = config.tmdb.api_key
        except (ApplicationError, OSError, ValueError):
            api_key = None

        if not api_key:
            QMessageBox.warning(
                self,
                DialogTitles.API_KEY_REQUIRED,
                DialogMessages.TMDB_API_KEY_MISSING,
            )
            return

        # Check if TMDB matching is already in progress
        if self.tmdb_controller.is_matching:
            QMessageBox.information(
                self,
                DialogTitles.TMDB_MATCHING,
                "TMDB matching is already in progress. Please wait for it to complete.",
            )
            return

        # Clean up any existing progress dialog
        if self.tmdb_progress_dialog:
            self.tmdb_progress_dialog.close()
            self.tmdb_progress_dialog = None

        # Set API key in controller
        self.tmdb_controller.set_api_key(api_key)

        # Create and show progress dialog
        self.tmdb_progress_dialog = TMDBProgressDialog(self)
        self.tmdb_progress_dialog.cancelled.connect(self._on_tmdb_matching_cancelled)

        # Show dialog
        self.tmdb_progress_dialog.show()

        # Update status bar
        self.status_bar.showMessage("Starting TMDB matching...")
        logger.info(
            "TMDB matching started - %d files to process",
            len(self.state_model.scanned_files),
        )

        # Start TMDB matching using controller
        try:
            self.tmdb_controller.match_files(self.state_model.scanned_files)
        except (ValueError, RuntimeError) as e:
            logger.exception("Failed to start TMDB matching")
            self.status_bar.showMessage(
                DialogMessages.TMDB_MATCHING_ERROR.format(error=e),
            )
            QMessageBox.warning(
                self,
                DialogTitles.TMDB_ERROR,
                f"Failed to start matching:\n{e}",
            )
            if self.tmdb_progress_dialog:
                self.tmdb_progress_dialog.close()
                self.tmdb_progress_dialog = None

    def on_tmdb_matching_started(self) -> None:
        """Handle TMDB matching started signal."""
        self.status_bar.showMessage("TMDB matching started...")
        logger.info("TMDB matching started")

    def on_tmdb_file_matched(self, result: dict) -> None:
        """Handle TMDB file matched signal."""
        file_path = Path(result.get("file_path", ""))
        file_name = result.get("file_name", "Unknown")
        match_result = result.get("match_result")  # Actually use this!
        status = result.get("status", "unknown")

        # Update state model
        if hasattr(self, "state_model") and self.state_model:
            self.state_model.update_file_status(file_path, status)

            # Save TMDB metadata to state model
            if match_result:
                self.state_model.set_file_metadata(
                    file_path,
                    {"match_result": match_result},
                )
                # Get title from MatchResult dataclass
                title = (
                    match_result.title if hasattr(match_result, "title") else "Unknown"
                )
                logger.debug(
                    "Saved TMDB metadata for: %s - %s",
                    file_name,
                    title,
                )

        logger.debug("File matched: %s - %s", file_name, status)

    def on_tmdb_matching_progress(self, progress: int) -> None:
        """Handle TMDB matching progress signal."""
        if self.tmdb_progress_dialog:
            self.tmdb_progress_dialog.update_progress(progress)
        self.status_bar.showMessage(f"TMDB matching... {progress}%")

    def on_tmdb_matching_finished(self, _results: list) -> None:
        """Handle TMDB matching finished signal.

        Args:
            _results: Match results (unused, required by signal signature)
        """
        matched_count = self.tmdb_controller.get_matched_files_count()
        total_count = self.tmdb_controller.get_total_files_count()

        if self.tmdb_progress_dialog:
            self.tmdb_progress_dialog.show_completion(matched_count, total_count)

        self.status_bar.showMessage(
            f"TMDB matching completed: {matched_count}/{total_count} matched",
        )
        logger.info(
            "TMDB matching completed: %d/%d files matched",
            matched_count,
            total_count,
        )

        # Enable organize button if any files matched
        if matched_count > 0:
            self.organize_action.setEnabled(True)
            logger.debug("Organize button enabled (%d files matched)", matched_count)

        # Update UI with match results - re-group files with updated TMDB metadata
        if hasattr(self, "scan_controller") and self.scan_controller:
            try:
                # Set flag to prevent auto-start during regroup
                self._is_regrouping = True

                # Re-group files by TMDB title (merge groups with same TMDB match)
                # Use internal _scanned_files to get updated metadata (scanned_files property returns copy)
                file_items = (
                    self.state_model._scanned_files
                    if hasattr(self.state_model, "_scanned_files")
                    else self.state_model.scanned_files
                )
                if file_items:
                    self.scan_controller.group_files_by_tmdb_title(file_items)
                    logger.info(
                        "Re-grouped %d files by TMDB title (merging groups with same match)",
                        len(file_items),
                    )
            except Exception:
                logger.exception("Failed to re-group files after TMDB matching")
                # Non-critical error, don't show to user
            finally:
                # Reset flag after regroup is complete
                self._is_regrouping = False

    def on_tmdb_matching_error(self, error_msg: str) -> None:
        """Handle TMDB matching error signal."""
        if self.tmdb_progress_dialog:
            self.tmdb_progress_dialog.show_error(error_msg)

        self.status_bar.showMessage(f"TMDB matching error: {error_msg}")
        logger.error("TMDB matching error: %s", error_msg)

        # Show error dialog
        QMessageBox.warning(
            self,
            DialogTitles.TMDB_ERROR,
            f"Failed to match files:\n{error_msg}",
        )

    def on_tmdb_matching_cancelled(self) -> None:
        """Handle TMDB matching cancellation."""
        if self.tmdb_progress_dialog:
            self.tmdb_progress_dialog.close()
            self.tmdb_progress_dialog = None
        self.status_bar.showMessage("TMDB matching cancelled")
        logger.info("TMDB matching cancelled by user")

    def _on_tmdb_matching_cancelled(self) -> None:
        """Handle TMDB matching cancellation from progress dialog."""
        self.tmdb_controller.cancel_matching()

        # Ensure is_matching flag is reset to prevent auto-restart
        self.tmdb_controller.is_matching = False

    def organize_files(self) -> None:
        """Start file organization process with preview."""
        if not self.state_model or not self.state_model.scanned_files:
            QMessageBox.warning(
                self,
                "파일 없음",
                "정리할 파일이 없습니다. 먼저 폴더를 스캔하세요.",
            )
            return

        logger.info(
            "Starting file organization for %d files",
            len(self.state_model.scanned_files),
        )

        try:
            # Generate organization plan
            self.organize_controller.organize_files(
                self.state_model.scanned_files,
                dry_run=True,  # Generate plan only
            )

            # Wait for plan to be generated
            # (In a real implementation, this would be async with signal/slot)

        except (ValueError, RuntimeError) as e:
            logger.exception("Failed to start file organization")
            QMessageBox.warning(
                self,
                "정리 오류",
                f"파일 정리를 시작할 수 없습니다:\n{e}",
            )

    def _on_organize_plan_generated(self, plan: list) -> None:
        """Handle organization plan generated signal.

        Args:
            plan: List of FileOperation objects
        """
        if not plan:
            QMessageBox.information(
                self,
                "정리 불필요",
                "모든 파일이 이미 올바른 위치에 있습니다.",
            )
            return

        # Show preview dialog
        preview_dialog = OrganizePreviewDialog(plan, self)

        if preview_dialog.exec() == QDialog.Accepted and preview_dialog.is_confirmed():
            # User confirmed - execute the plan
            self._execute_organization_plan(plan)
        else:
            logger.info("User cancelled file organization")
            self.status_bar.showMessage("파일 정리가 취소되었습니다.")

    def _execute_organization_plan(self, plan: list) -> None:
        """Execute the file organization plan.

        Args:
            plan: List of FileOperation objects to execute
        """
        # Show progress dialog
        progress_dialog = OrganizeProgressDialog(len(plan), self)
        progress_dialog.show()

        # Connect controller signals to progress dialog
        self.organize_controller.organization_progress.connect(
            progress_dialog.update_progress,
        )
        self.organize_controller.file_organized.connect(
            progress_dialog.add_file_result,
        )
        self.organize_controller.organization_finished.connect(
            lambda results: progress_dialog.show_completion(
                len([r for r in results if r]),
                len(plan),
            ),
        )
        self.organize_controller.organization_error.connect(
            progress_dialog.show_error,
        )

        # Execute plan
        self.organize_controller._execute_organization_plan(plan)
