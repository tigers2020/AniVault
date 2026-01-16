"""
Main Window Implementation for AniVault GUI

This module contains the main window class that serves as the root container
for all UI elements in the AniVault GUI application.
"""

# pylint: disable=attribute-defined-outside-init  # PySide6 pattern: widgets created in _setup_ui()

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal

if TYPE_CHECKING:
    from PySide6.QtGui import QAction

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from anivault.config import get_config, reload_config
from anivault.core.file_grouper import Group
from anivault.core.models import FileOperation, ScannedFile

# Additional imports for type hints and runtime usage
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.gui.dialogs.tmdb_progress_dialog import TMDBProgressDialog
from anivault.gui.managers.status_manager import CacheStats
from anivault.gui.models import FileItem
from anivault.shared.constants.gui_messages import DialogMessages, DialogTitles
from anivault.shared.errors import (
    AniVaultError,
    AniVaultParsingError,
    ApplicationError,
    ErrorCode,
    ErrorContextModel,
)
from anivault.shared.metadata_models import FileMetadata

from .controllers import OrganizeController, ScanController, TMDBController
from .factories import DialogFactory
from .handlers import OrganizeEventHandler, ScanEventHandler, TMDBEventHandler
from .managers import MenuManager, SignalCoordinator, StatusManager
from .state_model import StateModel
from .themes import ThemeManager
from .views import ViewUpdater
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

        # Initialize TMDB matching components
        self.tmdb_progress_dialog: TMDBProgressDialog | None = None

        # Initialize theme-related attributes
        self.theme_manager: ThemeManager | None = None
        self.config_path = Path("config/config.toml")

        # Setup components in logical order
        self._setup_controllers()
        self._setup_ui()
        self._setup_managers()
        self._setup_event_handlers()
        self._setup_signal_coordinator()

        logger.info("MainWindow initialized successfully")

    def _setup_controllers(self) -> None:
        """Initialize controllers."""
        self.scan_controller = ScanController(self)
        self.tmdb_controller = TMDBController(parent=self)
        self.organize_controller = OrganizeController(parent=self)

    def _setup_managers(self) -> None:
        """Initialize managers and factories."""
        # Menu manager
        self.menu_manager = MenuManager(self)
        self.menu_manager.setup_all()

        # Status manager
        self.status_manager = StatusManager(self.statusBar())
        self.status_manager.setup_status_bar()

        # Dialog factory
        self.dialog_factory = DialogFactory()

        # View updater
        self.view_updater = ViewUpdater(
            group_view=self.group_view,
            file_list=self.file_list,
            group_details_label=self.group_details_label,
            status_manager=self.status_manager,
        )

    def _setup_event_handlers(self) -> None:
        """Initialize event handlers."""

        self.scan_event_handler: ScanEventHandler = ScanEventHandler(
            status_manager=self.status_manager,
            state_model=self.state_model,
            scan_controller=self.scan_controller,
            update_file_tree_callback=self.view_updater.update_file_tree_with_groups,
        )

        self.tmdb_event_handler: TMDBEventHandler = TMDBEventHandler(
            status_manager=self.status_manager,
            state_model=self.state_model,
            tmdb_controller=self.tmdb_controller,
            tmdb_progress_dialog=None,  # Set later when dialog is created
            enable_organize_callback=self._enable_organize_action,
            regroup_callback=self._regroup_by_tmdb_title,
        )

        self.organize_event_handler: OrganizeEventHandler = OrganizeEventHandler(
            status_manager=self.status_manager,
            state_model=self.state_model,
            scan_controller=self.scan_controller,
            organize_controller=self.organize_controller,
            organize_progress_dialog=None,  # Set later when dialog is created
            show_preview_callback=self._show_organize_preview,
            execute_plan_callback=self._execute_organize_plan_internal,
        )

    def _setup_signal_coordinator(self) -> None:
        """Initialize and connect signal coordinator."""
        self.signal_coordinator = SignalCoordinator(self)
        self.signal_coordinator.connect_all()

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

    def update_cache_status(self, stats: CacheStats) -> None:
        """Update cache status display in status bar.

        Delegates to StatusManager for actual display logic.

        Args:
            stats: Dictionary containing cache statistics from TMDB controller
        """
        self.status_manager.update_cache_status(stats)

    def _get_api_key(self) -> str | None:
        """Get TMDB API key from config.

        Returns:
            API key string if configured, None otherwise
        """
        try:
            config = get_config()
            return config.api.tmdb.api_key
        except (ApplicationError, OSError, ValueError):
            return None

    def _setup_tmdb_progress_dialog(self) -> None:
        """Setup and show TMDB progress dialog."""
        # Clean up any existing progress dialog
        if self.tmdb_progress_dialog:
            self.tmdb_progress_dialog.close()
            self.tmdb_progress_dialog = None

        # Create and show new progress dialog using factory
        self.tmdb_progress_dialog = self.dialog_factory.create_tmdb_progress_dialog(self)
        self.tmdb_progress_dialog.cancelled.connect(self.tmdb_event_handler.on_progress_dialog_cancelled)
        self.tmdb_progress_dialog.show()

        # Update event handler with the new dialog instance
        self.tmdb_event_handler.set_progress_dialog(self.tmdb_progress_dialog)

    def _enable_organize_action(self) -> None:
        """Enable the organize action in the menu."""
        organize_action = self.menu_manager.get_action("organize")
        if organize_action:
            organize_action.setEnabled(True)
            logger.debug("Organize action enabled")

    def _regroup_by_tmdb_title(self) -> None:
        """Re-group files by TMDB title after matching completes."""
        if not hasattr(self, "scan_controller") or not self.scan_controller:
            return

        try:
            # Set flag to prevent auto-start during regroup
            self._is_regrouping = True

            # Get file items with updated metadata
            file_items = (
                self.state_model._scanned_files  # pylint: disable=protected-access
                if hasattr(self.state_model, "_scanned_files")
                else self.state_model.scanned_files
            )

            if file_items:
                self.scan_controller.group_files_by_tmdb_title(file_items)
                logger.info(
                    "Re-grouped %d files by TMDB title (merging groups with same match)",
                    len(file_items),
                )
        except (KeyError, ValueError, AttributeError) as e:
            # Data structure access errors during regrouping
            context = ErrorContextModel(
                operation="regroup_files_after_tmdb_matching",
                additional_data={"file_count": len(file_items) if file_items else 0},
            )
            error = AniVaultParsingError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"Failed to re-group files after TMDB matching: {e}",
                context,
                original_error=e,
            )
            logger.exception("Failed to re-group files after TMDB matching: %s", error.message)
            # Non-critical error, don't show to user
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Unexpected errors during regrouping - log but don't crash GUI
            context = ErrorContextModel(
                operation="regroup_files_after_tmdb_matching",
                additional_data={"file_count": len(file_items) if file_items else 0},
            )
            unexpected_error = AniVaultError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"Unexpected error re-grouping files after TMDB matching: {e}",
                context,
                original_error=e,
            )
            logger.exception("Failed to re-group files after TMDB matching: %s", unexpected_error.message)
            # Non-critical error, don't show to user
        finally:
            # Reset flag after regroup is complete
            self._is_regrouping = False

    def _save_theme_preference(self, theme_name: str) -> None:
        """Save theme preference to config file.

        Args:
            theme_name: Name of the theme to save
        """
        try:
            config = get_config()
            config.app.theme = theme_name
            config.to_toml_file("config/config.toml")
            logger.info("Theme preference saved: %s", theme_name)
        except (OSError, ValueError) as e:
            logger.warning("Failed to save theme preference: %s", e)

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
            self.status_manager.show_message(f"Opened: {directory}")

            # Update state model
            self.state_model.selected_directory = Path(directory)

            # Start file scanning
            self.start_file_scan()

    def switch_theme(self, action: QAction) -> None:
        """Switch the application theme."""
        if not self.theme_manager:
            logger.warning("Theme manager not available")
            return

        # Validate action type (mypy knows action is QAction from parameter type)
        # This check is redundant for type safety but kept for runtime validation

        try:
            theme_name = action.data()
            if not theme_name:
                logger.error("No theme data found in action")
                return

            logger.info("Switching to theme: %s", theme_name)

            # Apply the theme (QApplication auto-detected, with fallback)
            self.theme_manager.apply_theme(theme_name)

            # Save theme preference to settings
            self._save_theme_preference(theme_name)

            # Update status bar
            self.status_manager.show_message(f"Theme switched to {theme_name.title()}", 3000)

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
        if self.theme_manager is not None and self.menu_manager:
            current_theme = self.theme_manager.get_current_theme()
            if current_theme:
                # Get theme action group from MenuManager
                theme_action_group = self.menu_manager._theme_action_group  # pylint: disable=protected-access
                if theme_action_group:
                    for action in theme_action_group.actions():
                        if action.data() == current_theme:
                            action.setChecked(True)
                            break

    def show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About AniVault",
            "AniVault - Anime File Organizer\n\nA tool for organizing anime files using TMDB metadata.\n\nVersion: 1.0.0",
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
            self.status_manager.show_message(DialogMessages.SCAN_ERROR.format(error=e))
            QMessageBox.warning(
                self,
                DialogTitles.SCAN_ERROR,
                f"Failed to start scan:\n{e}",
            )

    def on_files_grouped(self, grouped_files: list[Group]) -> None:
        """Orchestrate TMDB auto-start after file grouping.

        Note: File tree view update is now handled by ScanEventHandler.
        This method focuses solely on workflow orchestration (TMDB auto-start).

        Args:
            grouped_files: List of Group objects (not used, required by signal)
        """
        _ = grouped_files  # Signal parameter, not used in this orchestration method
        # Auto-start TMDB matching after grouping
        # (only if not already in progress and not a regroup)  # pylint: disable=line-too-long
        # Skip auto-start if this is a regroup after TMDB matching
        # to prevent infinite loop
        if not self.tmdb_controller.is_matching and not getattr(
            self,
            "_is_regrouping",
            False,
        ):
            logger.info("Auto-starting TMDB matching after file grouping")

            # Check if API key is configured before starting
            api_key = self._get_api_key()
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

    def on_files_updated(self, files: list[FileItem]) -> None:
        """Handle files updated signal from state model."""
        logger.info("Files updated in state model: %d files", len(files))

    def on_file_status_changed(self, file_path: Path, status: str) -> None:
        """Handle file status changed signal from state model."""
        # Note: File status updates are now handled by the state model and group view
        # No direct file tree manipulation needed
        logger.debug("File status updated: %s -> %s", file_path.name, status)

    def update_file_tree_with_groups(self, grouped_files: dict[str, list[ScannedFile]]) -> None:
        """Update the group grid view with grouped files as cards (delegates to ViewUpdater)."""
        self.view_updater.update_file_tree_with_groups(grouped_files)

    def on_group_selected(self, group_name: str, files: list[ScannedFile]) -> None:
        """Handle group selection from grid view (delegates to ViewUpdater)."""
        self.view_updater.on_group_selected(group_name, files)

    def update_file_tree(self, files: list[FileItem]) -> None:
        """Update the group view with scanned files (delegates to ViewUpdater)."""
        self.view_updater.update_file_tree(files)

    def open_settings_dialog(self) -> None:
        """Open the settings dialog for API key configuration."""
        try:
            # Create dialog using factory
            dialog = self.dialog_factory.create_settings_dialog(self, self.config_path)

            # Connect signals
            dialog.api_key_saved.connect(self._on_api_key_saved)
            dialog.folder_settings_changed.connect(self._on_folder_settings_changed)

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

        Reloads configuration to ensure the new API key is available
        immediately without requiring a restart.

        Args:
            _api_key: The saved API key (unused, required by signal signature)
        """
        try:
            # Reload configuration to get the updated API key
            reload_config()
            logger.info("API key saved and configuration reloaded successfully")
            self.status_manager.show_message("API key saved successfully")
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception("Failed to reload configuration after API key save")
            self.status_manager.show_message(f"API key saved but failed to reload: {e!s}")

    def _on_folder_settings_changed(self) -> None:
        """
        Handle folder settings changed signal.

        Reloads configuration to ensure the new folder settings are available
        immediately without requiring a restart.
        """
        try:
            # Reload configuration to get the updated folder settings
            reload_config()
            logger.info("Folder settings changed and configuration reloaded successfully")
            self.status_manager.show_message("Folder settings updated successfully")
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception("Failed to reload configuration after folder settings change")
            self.status_manager.show_message(f"Folder settings saved but failed to reload: {e!s}")

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
        api_key = self._get_api_key()
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

        # Set API key in controller
        self.tmdb_controller.set_api_key(api_key)

        # Setup progress dialog
        self._setup_tmdb_progress_dialog()

        # Update status bar
        self.status_manager.show_message("Starting TMDB matching...")
        logger.info(
            "TMDB matching started - %d files to process",
            len(self.state_model.scanned_files),
        )

        # Start TMDB matching using controller
        try:
            # Convert FileItem to ScannedFile for TMDB controller
            scanned_files = self._convert_file_items_to_scanned_files(self.state_model.scanned_files)
            self.tmdb_controller.match_files(scanned_files)
        except (ValueError, RuntimeError) as e:
            logger.exception("Failed to start TMDB matching")
            self.status_manager.show_message(
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
                dry_run=True,  # Generate plan only (preview mode)
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

    def _convert_file_items_to_scanned_files(self, file_items: list[FileItem]) -> list[ScannedFile]:
        """Convert FileItem objects to ScannedFile objects for TMDB controller.

        Args:
            file_items: List of FileItem objects from GUI

        Returns:
            List of ScannedFile objects for Core processing
        """
        scanned_files = []
        for file_item in file_items:
            # Create ScannedFile from FileItem
            # Handle None metadata by creating a default ParsingResult
            metadata = file_item.metadata
            if metadata is None:
                parsing_metadata: ParsingResult = ParsingResult(title="Unknown")
            else:
                # metadata is FileMetadata (guaranteed by type annotation)
                # Convert FileMetadata to ParsingResult for ScannedFile

                assert isinstance(metadata, FileMetadata)
                parsing_metadata = ParsingResult(
                    title=metadata.title or "Unknown",
                    season=metadata.season,
                    episode=metadata.episode,
                    year=metadata.year,
                    quality=None,
                    release_group=None,
                    additional_info=ParsingAdditionalInfo(),
                )

            scanned_file = ScannedFile(
                file_path=file_item.file_path,
                metadata=parsing_metadata,
                file_size=(file_item.file_path.stat().st_size if file_item.file_path.exists() else 0),
                last_modified=(file_item.file_path.stat().st_mtime if file_item.file_path.exists() else 0.0),
            )
            scanned_files.append(scanned_file)

        return scanned_files

    def _show_organize_preview(self, plan: list[FileOperation]) -> None:
        """Show organization preview dialog to user.

        This is a callback used by OrganizeEventHandler to display
        the preview dialog and let the user accept or cancel the plan.

        Args:
            plan: List of FileOperation objects
        """
        # Create preview dialog using factory
        preview_dialog = self.dialog_factory.create_organize_preview_dialog(plan, self)

        if preview_dialog.exec() == QDialog.Accepted and preview_dialog.is_confirmed():  # pylint: disable=line-too-long
            # User confirmed - execute the plan via handler
            if self.organize_event_handler._execute_plan_callback:  # pylint: disable=protected-access
                self.organize_event_handler._execute_plan_callback(plan)  # pylint: disable=protected-access
        else:
            logger.info("User cancelled file organization")
            self.status_manager.show_message("파일 정리가 취소되었습니다.")

    def _execute_organize_plan_internal(self, plan: list[FileOperation]) -> None:
        """Execute the file organization plan (internal callback).

        This is a callback used by OrganizeEventHandler to execute the
        organization plan with proper progress dialog management.

        Args:
            plan: List of FileOperation objects to execute
        """
        # Create progress dialog using factory
        progress_dialog = self.dialog_factory.create_organize_progress_dialog(len(plan), self)
        progress_dialog.show()

        # Update handler with progress dialog reference
        self.organize_event_handler.set_progress_dialog(progress_dialog)

        # Connect cancel button to controller
        progress_dialog.rejected.connect(
            self.organize_controller.cancel_organization,
        )

        # Execute plan
        self.organize_controller._execute_organization_plan(plan)  # pylint: disable=protected-access
