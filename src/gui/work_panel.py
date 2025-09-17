"""Work panel for file operations and controls."""

import logging

from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.config_manager import ConfigManager
from ..themes.theme_manager import get_theme_manager
from ..viewmodels.base_viewmodel import BaseViewModel

# Logger for this module
logger = logging.getLogger(__name__)


class WorkPanel(QGroupBox):
    """Work panel containing source/target folders and action buttons."""

    scan_requested = pyqtSignal()
    organize_requested = pyqtSignal()
    preview_requested = pyqtSignal()

    def __init__(
        self, parent: QWidget | None = None, config_manager: ConfigManager | None = None
    ) -> None:
        """Initialize the work panel."""
        super().__init__("작업 패널", parent)
        self.theme_manager = get_theme_manager()
        self.config_manager = config_manager or ConfigManager()
        self._viewmodel: BaseViewModel | None = None
        self._is_processing = False

        # Apply theme to the GroupBox first
        self.setStyleSheet(self.theme_manager.current_theme.get_group_box_style())
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Source folder section
        source_layout = QVBoxLayout()
        source_label = QLabel("소스 폴더")
        source_label.setStyleSheet(
            f"font-weight: bold; color: {self.theme_manager.get_color('label_text')};"
        )

        self.source_path_edit = QLineEdit()
        self.source_path_edit.setPlaceholderText("소스 경로를 선택하세요...")
        self.source_path_edit.setStyleSheet(self.theme_manager.current_theme.get_line_edit_style())

        source_browse_btn = QPushButton("찾아보기")
        source_browse_btn.button_type = "default"
        source_browse_btn.setStyleSheet(
            self.theme_manager.current_theme.get_button_style("default")
        )
        source_browse_btn.clicked.connect(self._browse_source_folder)

        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_path_edit)
        source_layout.addWidget(source_browse_btn)

        # Target folder section
        target_layout = QVBoxLayout()
        target_label = QLabel("대상 폴더")
        target_label.setStyleSheet(
            f"font-weight: bold; color: {self.theme_manager.get_color('label_text')};"
        )

        self.target_path_edit = QLineEdit()
        self.target_path_edit.setPlaceholderText("대상 경로를 선택하세요...")
        self.target_path_edit.setStyleSheet(self.theme_manager.current_theme.get_line_edit_style())

        target_browse_btn = QPushButton("찾아보기")
        target_browse_btn.button_type = "default"
        target_browse_btn.setStyleSheet(
            self.theme_manager.current_theme.get_button_style("default")
        )
        target_browse_btn.clicked.connect(self._browse_target_folder)

        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_path_edit)
        target_layout.addWidget(target_browse_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(self.theme_manager.current_theme.get_progress_bar_style())

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.scan_btn = QPushButton("스캔")
        self.scan_btn.button_type = "primary"
        self.scan_btn.setStyleSheet(self.theme_manager.current_theme.get_button_style("primary"))
        self.scan_btn.clicked.connect(self._on_scan_clicked)

        self.organize_btn = QPushButton("정리")
        self.organize_btn.button_type = "secondary"
        self.organize_btn.setStyleSheet(
            self.theme_manager.current_theme.get_button_style("secondary")
        )
        self.organize_btn.clicked.connect(self._on_organize_clicked)

        self.preview_btn = QPushButton("미리보기")
        self.preview_btn.button_type = "accent"
        self.preview_btn.setStyleSheet(self.theme_manager.current_theme.get_button_style("accent"))
        self.preview_btn.clicked.connect(self._on_preview_clicked)

        self.stop_btn = QPushButton("중지")
        self.stop_btn.button_type = "error"
        self.stop_btn.setStyleSheet(self.theme_manager.current_theme.get_button_style("error"))
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.setVisible(False)

        buttons_layout.addWidget(self.scan_btn)
        buttons_layout.addWidget(self.organize_btn)
        buttons_layout.addWidget(self.preview_btn)
        buttons_layout.addWidget(self.stop_btn)

        # Add all sections to main layout
        layout.addLayout(source_layout)
        layout.addLayout(target_layout)
        layout.addWidget(self.progress_bar)
        layout.addLayout(buttons_layout)
        layout.addStretch()

    def _load_settings(self) -> None:
        """Load settings from configuration manager."""
        try:
            # Load last used directories
            last_source = self.config_manager.get_last_source_directory()
            if last_source:
                self.source_path_edit.setText(last_source)

            last_destination = self.config_manager.get_last_destination_directory()
            if last_destination:
                self.target_path_edit.setText(last_destination)

            # Load destination root from file organization settings
            destination_root = self.config_manager.get_destination_root()
            if destination_root and not self.target_path_edit.text():
                self.target_path_edit.setText(destination_root)

            logger.info("WorkPanel settings loaded successfully")

        except Exception as e:
            logger.error("Failed to load WorkPanel settings: %s", str(e))

    def update_settings(self) -> None:
        """Update panel based on current settings."""
        try:
            self._load_settings()
            logger.info("WorkPanel settings updated")
        except Exception as e:
            logger.error("Failed to update WorkPanel settings: %s", str(e))

    def _browse_source_folder(self) -> None:
        """Browse for source folder."""
        # Get last used directory from config
        last_dir = self.config_manager.get_last_source_directory()
        folder = QFileDialog.getExistingDirectory(self, "소스 폴더 선택", last_dir)
        if folder:
            self.source_path_edit.setText(folder)
            # Save to config
            self.config_manager.set_last_source_directory(folder)
            self.config_manager.save_config()

    def _browse_target_folder(self) -> None:
        """Browse for target folder."""
        # Get last used directory from config
        last_dir = self.config_manager.get_last_destination_directory()
        folder = QFileDialog.getExistingDirectory(self, "대상 폴더 선택", last_dir)
        if folder:
            self.target_path_edit.setText(folder)
            # Save to config
            self.config_manager.set_last_destination_directory(folder)
            self.config_manager.save_config()

    def get_source_path(self) -> str:
        """Get the source folder path."""
        return str(self.source_path_edit.text())

    def get_target_path(self) -> str:
        """Get the target folder path."""
        return str(self.target_path_edit.text())

    def scan_files(self) -> None:
        """Trigger scan files action."""
        self.scan_requested.emit()

    def organize_files(self) -> None:
        """Trigger organize files action."""
        self.organize_requested.emit()

    def preview_organization(self) -> None:
        """Trigger preview organization action."""
        self.preview_requested.emit()

    def set_viewmodel(self, viewmodel: BaseViewModel) -> None:
        """
        Set the ViewModel for this panel.

        Args:
            viewmodel: ViewModel instance to connect to
        """
        self._viewmodel = viewmodel
        self._connect_viewmodel_signals()
        logger.debug("WorkPanel connected to ViewModel")

    def _connect_viewmodel_signals(self) -> None:
        """Connect ViewModel signals to panel updates."""
        if not self._viewmodel:
            return

        # Connect property changes
        self._viewmodel.property_changed.connect(self._on_property_changed)

        # Connect processing state changes
        if hasattr(self._viewmodel, "processing_pipeline_started"):
            self._viewmodel.processing_pipeline_started.connect(self._on_processing_started)
        if hasattr(self._viewmodel, "processing_pipeline_finished"):
            self._viewmodel.processing_pipeline_finished.connect(self._on_processing_finished)
        if hasattr(self._viewmodel, "worker_task_progress"):
            self._viewmodel.worker_task_progress.connect(self._on_progress_updated)

        # Connect error handling
        if hasattr(self._viewmodel, "error_occurred"):
            self._viewmodel.error_occurred.connect(self._on_error_occurred)

        # Connect real-time text input binding
        self.source_path_edit.textChanged.connect(self._on_source_path_changed)
        self.target_path_edit.textChanged.connect(self._on_target_path_changed)

    def _on_scan_clicked(self) -> None:
        """Handle scan button click."""
        print("DEBUG: _on_scan_clicked called")  # 강제 출력
        logger.info("Scan button clicked")

        print(f"DEBUG: ViewModel available: {self._viewmodel is not None}")  # 강제 출력
        if self._viewmodel:
            print(f"DEBUG: ViewModel type: {type(self._viewmodel)}")  # 강제 출력
            print(
                f"DEBUG: Has execute_command: {hasattr(self._viewmodel, 'execute_command')}"
            )  # 강제 출력
            if hasattr(self._viewmodel, "execute_command"):
                print(
                    f"DEBUG: execute_command method: {self._viewmodel.execute_command}"
                )  # 강제 출력

        if self._viewmodel and hasattr(self._viewmodel, "execute_command"):
            logger.debug("ViewModel and execute_command method available")
            # Get source path and set as scan directory
            source_path = self.get_source_path()
            logger.info(f"Source path: {source_path}")

            if source_path:
                logger.info("Setting scan directories and starting scan")
                print("DEBUG: About to call execute_command('set_scan_directories')")  # 강제 출력
                try:
                    print("DEBUG: Calling execute_command now...")  # 강제 출력
                    self._viewmodel.execute_command("set_scan_directories", [source_path])
                    print("DEBUG: set_scan_directories command completed")  # 강제 출력
                    logger.debug("set_scan_directories command completed")
                except Exception as e:
                    print(f"DEBUG: Error in set_scan_directories command: {e}")  # 강제 출력
                    logger.error(f"Error in set_scan_directories command: {e}")
                    return

                print("DEBUG: About to call execute_command('scan_directories')")  # 강제 출력
                try:
                    print("DEBUG: Calling scan_directories now...")  # 강제 출력
                    self._viewmodel.execute_command("scan_directories")
                    print("DEBUG: scan_directories command completed")  # 강제 출력
                    logger.debug("scan_directories command completed")
                except Exception as e:
                    print(f"DEBUG: Error in scan_directories command: {e}")  # 강제 출력
                    logger.error(f"Error in scan_directories command: {e}")
                    return
            else:
                logger.warning("No source path specified for scanning")
        else:
            logger.warning("No ViewModel or execute_command method available")
            self.scan_requested.emit()

    def _on_organize_clicked(self) -> None:
        """Handle organize button click."""
        if self._viewmodel and hasattr(self._viewmodel, "execute_command"):
            # Get target path and set it
            target_path = self.get_target_path()
            if target_path:
                self._viewmodel.execute_command("set_target_directory", target_path)
                self._viewmodel.execute_command("organize_files")
            else:
                logger.warning("No target path specified for organization")
        else:
            self.organize_requested.emit()

    def _on_preview_clicked(self) -> None:
        """Handle preview button click."""
        if self._viewmodel and hasattr(self._viewmodel, "get_property"):
            groups = self._viewmodel.get_property("file_groups", [])
            if groups:
                logger.info(f"Preview: {len(groups)} groups available")
            else:
                logger.warning("No groups available for preview")
        else:
            self.preview_requested.emit()

    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        if self._viewmodel and hasattr(self._viewmodel, "execute_command"):
            self._viewmodel.execute_command("stop_processing")
        logger.info("Stop processing requested")

    @pyqtSlot(str, object)
    def _on_property_changed(self, property_name: str, value) -> None:
        """Handle property changes from ViewModel."""
        if property_name == "scan_directories" and isinstance(value, list) and value:
            self.source_path_edit.setText(value[0])
        elif property_name == "target_directory" and isinstance(value, str):
            self.target_path_edit.setText(value)
        elif property_name == "is_pipeline_running":
            self.set_processing_state(bool(value))
        elif property_name == "scan_progress":
            self.update_progress(int(value))

    @pyqtSlot()
    def _on_processing_started(self) -> None:
        """Handle processing started signal."""
        self.set_processing_state(True)

    @pyqtSlot(bool)
    def _on_processing_finished(self, success: bool) -> None:
        """Handle processing finished signal."""
        self.set_processing_state(False)

    @pyqtSlot(str, int)
    def _on_progress_updated(self, task_name: str, progress: int) -> None:
        """Handle progress updates from ViewModel."""
        self.update_progress(progress)

    @pyqtSlot(str)
    def _on_source_path_changed(self, text: str) -> None:
        """Handle source path text change."""
        if self._viewmodel and hasattr(self._viewmodel, "execute_command"):
            # Only update if the text is different from what's already set
            current_dirs = self._viewmodel.get_property("scan_directories", [])
            if not current_dirs or current_dirs[0] != text:
                try:
                    self._viewmodel.execute_command("set_scan_directories", [text])
                    logger.debug(f"Source path updated: {text}")
                except RuntimeError as e:
                    if "already executing" in str(e):
                        logger.debug("set_scan_directories already executing, skipping update")
                    else:
                        raise

    @pyqtSlot(str)
    def _on_target_path_changed(self, text: str) -> None:
        """Handle target path text change."""
        if self._viewmodel and hasattr(self._viewmodel, "execute_command"):
            # Only update if the text is different from what's already set
            current_target = self._viewmodel.get_property("target_directory", "")
            if current_target != text:
                try:
                    self._viewmodel.execute_command("set_target_directory", text)
                    logger.debug(f"Target path updated: {text}")
                except RuntimeError as e:
                    if "already executing" in str(e):
                        logger.debug("set_target_directory already executing, skipping update")
                    else:
                        raise

    @pyqtSlot(str)
    def _on_error_occurred(self, error_message: str) -> None:
        """Handle error signals from ViewModel."""
        logger.error(f"Error in WorkPanel: {error_message}")
        # Update UI to show error state - could show a message box or status indicator
        # For now, just log the error as WorkPanel doesn't have a status label

    def set_processing_state(self, is_processing: bool) -> None:
        """
        Set the processing state of the panel.

        Args:
            is_processing: Whether processing is currently active
        """
        self._is_processing = is_processing

        # Update button states
        self.scan_btn.setEnabled(not is_processing)
        self.organize_btn.setEnabled(not is_processing)
        self.preview_btn.setEnabled(not is_processing)
        self.stop_btn.setVisible(is_processing)

        # Update progress bar visibility
        self.progress_bar.setVisible(is_processing)
        if not is_processing:
            self.progress_bar.setValue(0)

    def update_progress(self, progress: int) -> None:
        """
        Update the progress bar.

        Args:
            progress: Progress percentage (0-100)
        """
        self.progress_bar.setValue(progress)

    def get_scan_directories(self) -> list[str]:
        """Get scan directories from the source path."""
        source_path = self.get_source_path()
        return [source_path] if source_path else []

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._viewmodel:
            # Disconnect signals
            self._viewmodel.property_changed.disconnect(self._on_property_changed)
            if hasattr(self._viewmodel, "processing_pipeline_started"):
                self._viewmodel.processing_pipeline_started.disconnect(self._on_processing_started)
            if hasattr(self._viewmodel, "processing_pipeline_finished"):
                self._viewmodel.processing_pipeline_finished.disconnect(
                    self._on_processing_finished
                )
            if hasattr(self._viewmodel, "worker_task_progress"):
                self._viewmodel.worker_task_progress.disconnect(self._on_progress_updated)

            self._viewmodel = None

        logger.debug("WorkPanel cleaned up")
