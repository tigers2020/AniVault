"""Anime groups panel for displaying grouped anime files."""

import logging
from typing import Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..themes.theme_manager import get_theme_manager

# Logger for this module
logger = logging.getLogger(__name__)


class AnimeGroupsPanel(QGroupBox):
    """Panel displaying anime groups in a table format."""

    group_selected = pyqtSignal(str)  # Emits group name when selected

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the anime groups panel."""
        super().__init__("애니 그룹", parent)
        self.theme_manager = get_theme_manager()
        # Apply theme to the GroupBox first
        self.setStyleSheet(self.theme_manager.current_theme.get_group_box_style())
        self._setup_ui()
        self._populate_sample_data()

        # Apply dark theme to all table items after population
        self._apply_dark_theme_to_table()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Create table widget
        self.groups_table = QTableWidget()
        self.groups_table.setColumnCount(3)
        self.groups_table.setHorizontalHeaderLabels(["그룹명", "파일 수", "상태"])

        # Configure table behavior
        self.groups_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.groups_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.groups_table.setAlternatingRowColors(True)
        self.groups_table.setSortingEnabled(True)

        # Configure table appearance
        self.groups_table.setStyleSheet(self.theme_manager.current_theme.get_table_style())

        # Force table to use dark theme
        self.groups_table.setAlternatingRowColors(True)
        self.groups_table.setStyleSheet(self.theme_manager.current_theme.get_table_style())

        # Force dark theme on table items
        self._apply_dark_theme_to_table()

        # Set column widths
        header = self.groups_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.Stretch)  # Group name
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # File count
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status

        # Connect selection signal
        self.groups_table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self.groups_table)

    def _set_status_color(self, status_item: QTableWidgetItem, status: str) -> None:
        """Set background color for status item based on status."""
        from PyQt5.QtGui import QColor

        if status == "완료":
            color = QColor(self.theme_manager.get_color("status_success"))
        elif status == "대기":
            color = QColor(self.theme_manager.get_color("status_warning"))
        else:
            color = QColor(self.theme_manager.get_color("status_error"))

        # Set background color for status items only
        status_item.setBackground(color)
        # Don't set text color - let CSS handle it

    def _set_row_colors(self, row: int) -> None:
        """Set background colors for table row items."""
        # This method is now deprecated - CSS handles all styling
        # Keeping for backward compatibility but not used
        pass

    def _apply_dark_theme_to_table(self) -> None:
        """Force dark theme on all table items."""
        from PyQt5.QtGui import QColor

        # Apply dark theme to all existing items
        for row in range(self.groups_table.rowCount()):
            for col in range(self.groups_table.columnCount()):
                item = self.groups_table.item(row, col)
                if item:
                    # Force dark background and light text
                    if row % 2 == 0:
                        item.setBackground(QColor(self.theme_manager.get_color("table_row_odd")))
                    else:
                        item.setBackground(QColor(self.theme_manager.get_color("bg_secondary")))
                    item.setForeground(QColor(self.theme_manager.get_color("text_primary")))

    def _populate_sample_data(self) -> None:
        """Populate the table with sample data."""
        sample_groups = [
            ("MyAnime 시즌1", "12", "완료"),
            ("MyAnime 시즌2", "10", "대기"),
            ("Another Anime", "8", "완료"),
            ("Test Series", "15", "대기"),
            ("Sample Show", "6", "완료"),
        ]

        self.groups_table.setRowCount(len(sample_groups))

        for row, (group_name, file_count, status) in enumerate(sample_groups):
            # Group name
            name_item = QTableWidgetItem(group_name)
            name_item.setData(
                Qt.ItemDataRole.UserRole, group_name
            )  # Store group name for selection
            self.groups_table.setItem(row, 0, name_item)

            # File count
            count_item = QTableWidgetItem(file_count)
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.groups_table.setItem(row, 1, count_item)

            # Status
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Color code status using theme manager
            self._set_status_color(status_item, status)

            self.groups_table.setItem(row, 2, status_item)

    def _on_selection_changed(self) -> None:
        """Handle selection change in the groups table."""
        current_row = self.groups_table.currentRow()
        if current_row >= 0:
            group_name_item = self.groups_table.item(current_row, 0)
            if group_name_item:
                # Emit the group name (series_title) instead of group ID
                group_name = group_name_item.text()
                self.group_selected.emit(group_name)

    def get_selected_group(self) -> str:
        """Get the currently selected group name."""
        current_row = self.groups_table.currentRow()
        if current_row >= 0:
            group_name_item = self.groups_table.item(current_row, 0)
            if group_name_item:
                return str(group_name_item.text())
        return ""

    def update_groups(self, groups: Any) -> None:
        """Update the groups table with actual group data.

        Args:
            groups: List of FileGroup objects
        """
        logger.debug(f"Updating groups table with {len(groups)} groups")

        # Clear existing data
        self.groups_table.setRowCount(0)

        # Populate with actual group data
        for i, group in enumerate(groups):
            logger.debug(
                f"Adding group {i+1}: ID={group.group_id}, series_title='{group.series_title}'"
            )
            self._add_group_row(group)

        logger.info(f"Updated groups table with {len(groups)} groups")

    def _add_group_row(self, group: Any) -> None:
        """Add a single group row to the table.

        Args:
            group: FileGroup object to add
        """
        row = self.groups_table.rowCount()
        self.groups_table.insertRow(row)

        # Group name (use Korean title if available)
        group_name = group.series_title or group.group_id
        group_name_item = QTableWidgetItem(group_name)
        group_name_item.setData(
            Qt.ItemDataRole.UserRole, group.group_id
        )  # Store group ID for selection

        # File count
        file_count_item = QTableWidgetItem(str(len(group.files)))

        # Status (based on processing state)
        if group.is_processed:
            status = "완료"
        elif group.tmdb_info:
            status = "메타데이터 있음"
        else:
            status = "대기"

        status_item = QTableWidgetItem(status)

        # Set items in table
        self.groups_table.setItem(row, 0, group_name_item)
        self.groups_table.setItem(row, 1, file_count_item)
        self.groups_table.setItem(row, 2, status_item)

        # Apply status color
        self._set_status_color(status_item, status)

        # Apply row colors
        self._set_row_colors(row)

    def add_group(self, group_name: str, file_count: int, status: str) -> None:
        """Add a new group to the table."""
        row_count = self.groups_table.rowCount()
        self.groups_table.insertRow(row_count)

        # Group name
        name_item = QTableWidgetItem(group_name)
        name_item.setData(Qt.ItemDataRole.UserRole, group_name)
        self.groups_table.setItem(row_count, 0, name_item)

        # File count
        count_item = QTableWidgetItem(str(file_count))
        count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.groups_table.setItem(row_count, 1, count_item)

        # Status
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # Color code status using theme manager
        self._set_status_color(status_item, status)

        self.groups_table.setItem(row_count, 2, status_item)

    def update_group_status(self, group_name: str, status: str) -> None:
        """Update the status of a specific group."""
        for row in range(self.groups_table.rowCount()):
            name_item = self.groups_table.item(row, 0)
            if name_item and name_item.data(Qt.ItemDataRole.UserRole) == group_name:
                status_item = self.groups_table.item(row, 2)
                if status_item:
                    status_item.setText(status)
                    # Color code status using theme manager
                    self._set_status_color(status_item, status)
                break
