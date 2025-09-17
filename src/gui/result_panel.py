"""Result panel for displaying file processing results and real-time status updates."""

import logging
from typing import Any, Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.config_manager import ConfigManager
from ..core.models import AnimeFile, FileGroup
from ..themes.theme_manager import get_theme_manager
from ..viewmodels.base_viewmodel import BaseViewModel

# Logger for this module
logger = logging.getLogger(__name__)


class ResultPanel(QGroupBox):
    """Panel for displaying file processing results and real-time status updates."""

    # Signals
    file_selected = pyqtSignal(str)  # Emits file path when selected
    group_selected = pyqtSignal(str)  # Emits group name when selected
    retry_requested = pyqtSignal(str)  # Emits file path for retry
    clear_requested = pyqtSignal()  # Emits when clear is requested

    def __init__(
        self, parent: Optional[QWidget] = None, config_manager: Optional[ConfigManager] = None
    ) -> None:
        """Initialize the result panel."""
        super().__init__("처리 결과", parent)
        self.theme_manager = get_theme_manager()
        self.config_manager = config_manager or ConfigManager()
        self.setStyleSheet(self.theme_manager.current_theme.get_group_box_style())

        # Data storage
        self._processing_results: list[dict[str, Any]] = []
        self._current_progress = 0
        self._total_files = 0
        self._is_processing = False
        self._viewmodel: Optional[BaseViewModel] = None

        # Setup UI
        self._setup_ui()
        self._populate_sample_data()

        # Setup update timer for real-time updates
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_progress)
        self._update_timer.setInterval(100)  # Update every 100ms

        # Load settings after timer is initialized
        self._load_settings()

        logger.info("ResultPanel initialized")

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Progress section
        progress_widget = self._create_progress_section()
        layout.addWidget(progress_widget)

        # Main content area with vertical splitter
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setChildrenCollapsible(False)

        # Files section (top)
        files_widget = self._create_files_section()
        main_splitter.addWidget(files_widget)

        # Groups section (bottom)
        groups_widget = self._create_groups_section()
        main_splitter.addWidget(groups_widget)

        # Set splitter proportions (files: 60%, groups: 40%)
        main_splitter.setSizes([400, 300])

        layout.addWidget(main_splitter)

        # Control buttons
        controls_widget = self._create_controls_section()
        layout.addWidget(controls_widget)

    def _create_progress_section(self) -> QWidget:
        """Create the progress display section."""
        widget = QFrame()
        widget.frame_type = "progress"
        widget.setStyleSheet(self.theme_manager.current_theme.get_frame_style("progress"))

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(self.theme_manager.current_theme.get_progress_bar_style())

        # Status label
        self.status_label = QLabel("대기 중...")
        self.status_label.setStyleSheet(
            f"color: {self.theme_manager.get_color('text_primary')}; font-weight: bold;"
        )

        # Progress info
        self.progress_info = QLabel("0 / 0 파일 처리됨")
        self.progress_info.setStyleSheet(
            f"color: {self.theme_manager.get_color('text_secondary')};"
        )

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_info)

        return widget

    def _create_files_section(self) -> QWidget:
        """Create the files display section."""
        # Create group box for files
        files_group = QGroupBox("파일 목록")
        files_group.setStyleSheet(self.theme_manager.current_theme.get_group_box_style())

        layout = QVBoxLayout(files_group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Files table
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(6)
        self.files_table.setHorizontalHeaderLabels(
            ["파일명", "크기", "상태", "그룹", "오류", "작업"]
        )

        # Configure table
        self.files_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.files_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSortingEnabled(True)
        self.files_table.setStyleSheet(self.theme_manager.current_theme.get_table_style())

        # Set column widths
        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # File name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Size
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Group
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Error
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Actions

        # Connect selection signal
        self.files_table.itemSelectionChanged.connect(self._on_file_selection_changed)

        # Add "Show All Files" button
        button_layout = QHBoxLayout()
        self.show_all_files_btn = QPushButton("전체 파일 보기")
        self.show_all_files_btn.setStyleSheet(self.theme_manager.current_theme.get_button_style())
        self.show_all_files_btn.clicked.connect(self.show_all_files)
        button_layout.addWidget(self.show_all_files_btn)
        button_layout.addStretch()  # Push button to the left
        
        layout.addLayout(button_layout)
        layout.addWidget(self.files_table)

        return files_group

    def _create_groups_section(self) -> QWidget:
        """Create the groups display section."""
        # Create group box for groups
        groups_group = QGroupBox("그룹 목록")
        groups_group.setStyleSheet(self.theme_manager.current_theme.get_group_box_style())

        layout = QVBoxLayout(groups_group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Groups table
        self.groups_table = QTableWidget()
        self.groups_table.setColumnCount(5)
        self.groups_table.setHorizontalHeaderLabels(["그룹명", "파일 수", "완료", "오류", "상태"])

        # Configure table
        self.groups_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.groups_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.groups_table.setAlternatingRowColors(True)
        self.groups_table.setSortingEnabled(True)
        self.groups_table.setStyleSheet(self.theme_manager.current_theme.get_table_style())

        # Set column widths
        header = self.groups_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Group name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # File count
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Completed
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Errors
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Status

        # Connect selection signal
        self.groups_table.itemSelectionChanged.connect(self._on_group_selection_changed)

        layout.addWidget(self.groups_table)

        return groups_group

    def _create_stat_card(self, label: str, value: str, color_name: str) -> QWidget:
        """Create a statistics card widget."""
        card = QFrame()
        card.frame_type = "card"
        card.setStyleSheet(self.theme_manager.current_theme.get_frame_style("card"))
        card.setMinimumWidth(120)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Value label
        value_label = QLabel(value)
        value_label.label_type = "stat_value"
        value_label.setStyleSheet(
            f"""
            QLabel {{
                font-size: 20px;
                font-weight: bold;
                color: {self.theme_manager.get_color(color_name)};
            }}
        """
        )
        value_label.setAlignment(Qt.AlignCenter)

        # Label
        label_widget = QLabel(label)
        label_widget.label_type = "stat_label"
        label_widget.setStyleSheet(self.theme_manager.current_theme.get_label_style("stat_label"))
        label_widget.setAlignment(Qt.AlignCenter)
        label_widget.setWordWrap(True)

        layout.addWidget(value_label)
        layout.addWidget(label_widget)

        return card

    def _create_controls_section(self) -> QWidget:
        """Create the control buttons section."""
        widget = QFrame()
        widget.setStyleSheet(f"background-color: {self.theme_manager.get_color('bg_secondary')};")

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Only keep clear results button (other controls are in left panel)
        self.clear_btn = QPushButton("결과 지우기")
        self.clear_btn.button_type = "secondary"
        self.clear_btn.setStyleSheet(self.theme_manager.current_theme.get_button_style("secondary"))
        self.clear_btn.clicked.connect(self._clear_results)

        layout.addStretch()
        layout.addWidget(self.clear_btn)

        return widget

    def _load_settings(self) -> None:
        """Load settings from configuration manager."""
        try:
            # Load file organization settings
            organize_mode = self.config_manager.get(
                "application.file_organization.organize_mode", "복사"
            )
            safe_mode = self.config_manager.get("application.file_organization.safe_mode", True)
            backup_before_organize = self.config_manager.get(
                "application.file_organization.backup_before_organize", False
            )

            # Store settings for use in processing
            self._organize_mode = organize_mode
            self._safe_mode = safe_mode
            self._backup_before_organize = backup_before_organize

            # Load auto refresh settings
            auto_refresh_interval = self.config_manager.get(
                "application.file_organization.auto_refresh_interval", 30
            )
            realtime_monitoring = self.config_manager.get(
                "application.file_organization.realtime_monitoring", False
            )

            # Update timer interval based on settings
            if realtime_monitoring:
                self._update_timer.setInterval(
                    auto_refresh_interval * 1000
                )  # Convert to milliseconds
            else:
                self._update_timer.setInterval(100)  # Default 100ms

            logger.info("ResultPanel settings loaded successfully")

        except Exception as e:
            logger.error("Failed to load ResultPanel settings: %s", str(e))

    def update_settings(self) -> None:
        """Update panel based on current settings."""
        try:
            self._load_settings()
            logger.info("ResultPanel settings updated")
        except Exception as e:
            logger.error("Failed to update ResultPanel settings: %s", str(e))

    def _populate_sample_data(self) -> None:
        """Populate the panel with sample data."""
        # Sample files data
        sample_files = [
            ("Ep01_1080p.mkv", "1.2 GB", "완료", "MyAnime 시즌1", "", "이동됨"),
            ("Ep02_1080p.mkv", "1.1 GB", "완료", "MyAnime 시즌1", "", "이동됨"),
            ("Ep03_1080p.mkv", "1.3 GB", "오류", "MyAnime 시즌1", "파일 손상", "재시도"),
            ("Ep04_1080p.mkv", "1.2 GB", "처리 중", "MyAnime 시즌1", "", "대기"),
            ("Ep05_1080p.mkv", "1.1 GB", "대기", "MyAnime 시즌1", "", "대기"),
        ]

        self.files_table.setRowCount(len(sample_files))
        for row, (file_name, size, status, group, error, action) in enumerate(sample_files):
            self._add_file_row(row, file_name, size, status, group, error, action)

        # Sample groups data
        sample_groups = [
            ("MyAnime 시즌1", "5", "3", "1", "처리 중"),
            ("Another Anime", "8", "8", "0", "완료"),
            ("Test Series", "12", "10", "2", "처리 중"),
        ]

        self.groups_table.setRowCount(len(sample_groups))
        for row, (group_name, file_count, completed, errors, status) in enumerate(sample_groups):
            self._add_group_row(row, group_name, file_count, completed, errors, status)

    def _add_file_row(
        self, row: int, file_name: str, size: str, status: str, group: str, error: str, action: str
    ) -> None:
        """Add a file row to the files table."""
        # File name
        name_item = QTableWidgetItem(file_name)
        name_item.setData(Qt.UserRole, file_name)
        self.files_table.setItem(row, 0, name_item)

        # Size
        size_item = QTableWidgetItem(size)
        size_item.setTextAlignment(Qt.AlignCenter)
        self.files_table.setItem(row, 1, size_item)

        # Status
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignCenter)
        self._set_status_color(status_item, status)
        self.files_table.setItem(row, 2, status_item)

        # Group
        group_item = QTableWidgetItem(group)
        group_item.setTextAlignment(Qt.AlignCenter)
        self.files_table.setItem(row, 3, group_item)

        # Error
        error_item = QTableWidgetItem(error)
        error_item.setTextAlignment(Qt.AlignCenter)
        if error:
            from PyQt5.QtGui import QColor

            error_item.setForeground(QColor(self.theme_manager.get_color("error")))
        self.files_table.setItem(row, 4, error_item)

        # Action button
        action_btn = QPushButton(action)
        action_btn.setMaximumWidth(80)
        action_btn.setStyleSheet(self.theme_manager.current_theme.get_button_style("small"))
        if action == "재시도":
            action_btn.clicked.connect(lambda: self.retry_requested.emit(file_name))
        self.files_table.setCellWidget(row, 5, action_btn)

    def _add_group_row(
        self, row: int, group_name: str, file_count: str, completed: str, errors: str, status: str
    ) -> None:
        """Add a group row to the groups table."""
        # Group name
        name_item = QTableWidgetItem(group_name)
        name_item.setData(Qt.UserRole, group_name)
        self.groups_table.setItem(row, 0, name_item)

        # File count
        count_item = QTableWidgetItem(file_count)
        count_item.setTextAlignment(Qt.AlignCenter)
        self.groups_table.setItem(row, 1, count_item)

        # Completed
        completed_item = QTableWidgetItem(completed)
        completed_item.setTextAlignment(Qt.AlignCenter)
        self.groups_table.setItem(row, 2, completed_item)

        # Errors
        errors_item = QTableWidgetItem(errors)
        errors_item.setTextAlignment(Qt.AlignCenter)
        if errors != "0":
            from PyQt5.QtGui import QColor

            errors_item.setForeground(QColor(self.theme_manager.get_color("error")))
        self.groups_table.setItem(row, 3, errors_item)

        # Status
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignCenter)
        self._set_status_color(status_item, status)
        self.groups_table.setItem(row, 4, status_item)

    def _set_status_color(self, item: QTableWidgetItem, status: str) -> None:
        """Set background color for status item based on status."""
        from PyQt5.QtGui import QColor

        if status == "완료":
            color = QColor(self.theme_manager.get_color("success"))
        elif status == "처리 중":
            color = QColor(self.theme_manager.get_color("warning"))
        elif status == "오류":
            color = QColor(self.theme_manager.get_color("error"))
        else:
            color = QColor(self.theme_manager.get_color("text_secondary"))

        item.setBackground(color)

    def _on_file_selection_changed(self) -> None:
        """Handle file selection change."""
        current_row = self.files_table.currentRow()
        if current_row >= 0:
            file_name_item = self.files_table.item(current_row, 0)
            if file_name_item:
                file_name = file_name_item.data(Qt.UserRole)
                self.file_selected.emit(file_name)

    def _on_group_selection_changed(self) -> None:
        """Handle group selection change."""
        current_row = self.groups_table.currentRow()
        if current_row >= 0:
            group_name_item = self.groups_table.item(current_row, 0)
            if group_name_item:
                # Use the group_id from UserRole for reliable lookup
                group_id = group_name_item.data(Qt.UserRole)
                if group_id:
                    self.group_selected.emit(group_id)
                else:
                    # Fallback to displayed text if group_id is not available
                    group_name = group_name_item.text()
                    self.group_selected.emit(group_name)

    def _clear_results(self) -> None:
        """Clear all results."""
        self.files_table.setRowCount(0)
        self.groups_table.setRowCount(0)

        self._current_progress = 0
        self._total_files = 0
        self.progress_bar.setValue(0)
        self.status_label.setText("대기 중...")
        self.progress_info.setText("0 / 0 파일 처리됨")

        self.clear_requested.emit()

    def _update_progress(self) -> None:
        """Update progress bar during processing."""
        if self._is_processing and self._current_progress < self._total_files:
            self._current_progress += 1
            progress = int((self._current_progress / self._total_files) * 100)
            self.progress_bar.setValue(progress)
            self.progress_info.setText(
                f"{self._current_progress} / {self._total_files} 파일 처리됨"
            )

            if self._current_progress >= self._total_files:
                self._is_processing = False
                self._update_timer.stop()
                self.status_label.setText("완료됨")

    def update_file_status(self, file_name: str, status: str, error: str = "") -> None:
        """Update the status of a specific file."""
        for row in range(self.files_table.rowCount()):
            name_item = self.files_table.item(row, 0)
            if name_item and name_item.data(Qt.UserRole) == file_name:
                # Update status
                status_item = self.files_table.item(row, 2)
                if status_item:
                    status_item.setText(status)
                    self._set_status_color(status_item, status)

                # Update error
                error_item = self.files_table.item(row, 4)
                if error_item:
                    error_item.setText(error)
                    if error:
                        from PyQt5.QtGui import QColor

                        error_item.setForeground(QColor(self.theme_manager.get_color("error")))

                break

    def add_processing_result(self, result: dict[str, Any]) -> None:
        """Add a processing result to the panel."""
        self._processing_results.append(result)

        # Add to files table
        row_count = self.files_table.rowCount()
        self.files_table.insertRow(row_count)

        self._add_file_row(
            row_count,
            result.get("file_name", ""),
            result.get("size", ""),
            result.get("status", "대기"),
            result.get("group", ""),
            result.get("error", ""),
            result.get("action", "대기"),
        )

    def set_total_files(self, count: int) -> None:
        """Set the total number of files to process."""
        self._total_files = count
        self.progress_info.setText(f"0 / {count} 파일 처리됨")

    def set_viewmodel(self, viewmodel: BaseViewModel) -> None:
        """
        Set the ViewModel for this panel.

        Args:
            viewmodel: ViewModel instance to connect to
        """
        self._viewmodel = viewmodel
        self._connect_viewmodel_signals()
        logger.debug("ResultPanel connected to ViewModel")

    def _connect_viewmodel_signals(self) -> None:
        """Connect ViewModel signals to panel updates."""
        if not self._viewmodel:
            return

        # Connect property changes
        self._viewmodel.property_changed.connect(self._on_property_changed)

        # Connect processing signals if available
        if hasattr(self._viewmodel, "files_scanned"):
            self._viewmodel.files_scanned.connect(self.update_files)
        if hasattr(self._viewmodel, "files_grouped"):
            self._viewmodel.files_grouped.connect(self.update_groups)
        if hasattr(self._viewmodel, "processing_pipeline_started"):
            self._viewmodel.processing_pipeline_started.connect(self._on_processing_started)
        if hasattr(self._viewmodel, "processing_pipeline_finished"):
            self._viewmodel.processing_pipeline_finished.connect(self._on_processing_finished)
        if hasattr(self._viewmodel, "worker_task_progress"):
            self._viewmodel.worker_task_progress.connect(self._on_progress_updated)

    def update_files(self, files: list[AnimeFile]) -> None:
        """
        Update the files table with scanned files.

        Args:
            files: List of AnimeFile objects
        """
        logger.info(f"ResultPanel.update_files called with {len(files)} files")
        
        # Clear existing data
        self.files_table.setRowCount(0)
        self._processing_results.clear()
        logger.info("Cleared existing data from files table")

        # Add files to table
        for i, file in enumerate(files):
            result = {
                "file_name": file.file_path.name,
                "size": self._format_file_size(file.file_size),
                "status": "스캔됨",
                "group": "",
                "error": "",
                "action": "대기",
            }
            self.add_processing_result(result)
            if i < 5:  # Log first 5 files for debugging
                logger.debug(f"Added file {i+1}: {file.file_path.name}")

        # Update progress
        self.set_total_files(len(files))
        logger.info(f"Updated files table with {len(files)} files")

    def filter_files_by_group(self, group_id: str) -> None:
        """
        Filter files table to show only files from the selected group.
        
        Args:
            group_id: ID of the group to filter by
        """
        logger.info(f"Filtering files by group: {group_id}")
        
        # Get all files from the ViewModel
        if not self._viewmodel:
            logger.warning("No ViewModel connected to ResultPanel")
            return
            
        all_files = self._viewmodel.get_property("scanned_files", [])
        groups = self._viewmodel.get_property("file_groups", [])
        
        # Find the selected group
        selected_group = None
        for group in groups:
            if group.group_id == group_id:
                selected_group = group
                break
        
        if selected_group:
            # Filter files to only show those in the selected group
            group_files = selected_group.files
            logger.info(f"Showing {len(group_files)} files from group: {selected_group.series_title}")
            
            # Update the files table with filtered files
            self._update_files_table(group_files)
        else:
            logger.warning(f"Group not found: {group_id}")
            # Show all files if group not found
            self._update_files_table(all_files)

    def show_all_files(self) -> None:
        """Show all scanned files without group filtering."""
        logger.info("Showing all files")
        if not self._viewmodel:
            logger.warning("No ViewModel connected to ResultPanel")
            return
            
        all_files = self._viewmodel.get_property("scanned_files", [])
        self._update_files_table(all_files)

    def _update_files_table(self, files: list) -> None:
        """
        Update the files table with the provided files.
        
        Args:
            files: List of AnimeFile objects to display
        """
        # Clear existing data
        self.files_table.setRowCount(0)
        self._processing_results.clear()
        logger.info(f"Updating files table with {len(files)} files")
        
        # Add files to table
        for i, file in enumerate(files):
            result = {
                "file_name": file.file_path.name,
                "size": self._format_file_size(file.file_size),
                "status": "스캔됨",
                "group": "",
                "error": "",
                "action": "대기",
            }
            self.add_processing_result(result)
            if i < 5:  # Log first 5 files for debugging
                logger.debug(f"Added file {i+1}: {file.file_path.name}")

        # Update progress
        self.set_total_files(len(files))
        logger.info(f"Updated files table with {len(files)} files")

    def update_groups(self, groups: list[FileGroup]) -> None:
        """
        Update the groups table with file groups.

        Args:
            groups: List of FileGroup objects
        """
        # Clear existing data
        self.groups_table.setRowCount(0)

        # Track series titles to handle duplicates
        title_counts = {}
        
        # Add groups to table
        for group in groups:
            row_count = self.groups_table.rowCount()
            self.groups_table.insertRow(row_count)

            # Group name (use series_title as the display name, make unique if needed)
            if group.series_title:
                base_name = group.series_title
                # Count occurrences of this title
                title_counts[base_name] = title_counts.get(base_name, 0) + 1
                # If this is a duplicate, append a number
                if title_counts[base_name] > 1:
                    group_name = f"{base_name} ({title_counts[base_name]})"
                else:
                    group_name = base_name
            else:
                group_name = f"Group {group.group_id[:8]}"
            
            name_item = QTableWidgetItem(group_name)
            name_item.setData(Qt.UserRole, group.group_id)
            self.groups_table.setItem(row_count, 0, name_item)

            # File count
            count_item = QTableWidgetItem(str(len(group.files)))
            self.groups_table.setItem(row_count, 1, count_item)

            # Status
            status_item = QTableWidgetItem("그룹화됨")
            self._set_status_color(status_item, "그룹화됨")
            self.groups_table.setItem(row_count, 2, status_item)

            # Action
            action_item = QTableWidgetItem("대기")
            self.groups_table.setItem(row_count, 3, action_item)

        logger.info(f"Updated groups table with {len(groups)} groups")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f} {size_names[i]}"

    def _on_property_changed(self, property_name: str, value) -> None:
        """Handle property changes from ViewModel."""
        if property_name == "is_pipeline_running":
            self._is_processing = bool(value)
            if self._is_processing:
                self._update_timer.start()
            else:
                self._update_timer.stop()
        elif property_name == "processing_status":
            self.status_label.setText(str(value))

    def _on_processing_started(self) -> None:
        """Handle processing started signal."""
        self._is_processing = True
        self.status_label.setText("처리 중...")
        self._update_timer.start()

    def _on_processing_finished(self, success: bool) -> None:
        """Handle processing finished signal."""
        self._is_processing = False
        self._update_timer.stop()
        status = "완료됨" if success else "실패"
        self.status_label.setText(status)

    def _on_progress_updated(self, task_name: str, progress: int) -> None:
        """Handle progress updates from ViewModel."""
        self.progress_bar.setValue(progress)
        self.progress_info.setText(f"{progress}% 완료")

    def cleanup(self) -> None:
        """Clean up resources when the panel is destroyed."""
        logger.info("Cleaning up ResultPanel resources")

        if self._update_timer.isActive():
            self._update_timer.stop()

        # Disconnect ViewModel signals safely
        if self._viewmodel:
            try:
                self._viewmodel.property_changed.disconnect(self._on_property_changed)
            except TypeError:
                pass  # Not connected

            try:
                if hasattr(self._viewmodel, "files_scanned"):
                    self._viewmodel.files_scanned.disconnect(self.update_files)
            except TypeError:
                pass

            try:
                if hasattr(self._viewmodel, "files_grouped"):
                    self._viewmodel.files_grouped.disconnect(self.update_groups)
            except TypeError:
                pass

            try:
                if hasattr(self._viewmodel, "processing_pipeline_started"):
                    self._viewmodel.processing_pipeline_started.disconnect(
                        self._on_processing_started
                    )
            except TypeError:
                pass

            try:
                if hasattr(self._viewmodel, "processing_pipeline_finished"):
                    self._viewmodel.processing_pipeline_finished.disconnect(
                        self._on_processing_finished
                    )
            except TypeError:
                pass

            try:
                if hasattr(self._viewmodel, "worker_task_progress"):
                    self._viewmodel.worker_task_progress.disconnect(self._on_progress_updated)
            except TypeError:
                pass

            self._viewmodel = None

        self._processing_results.clear()

        logger.info("ResultPanel cleanup completed")
