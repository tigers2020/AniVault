"""
Data models for AniVault GUI

This module contains the data models used by the GUI components,
including the file tree model and related data structures.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QModelIndex, QObject, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel

from anivault.shared.metadata_models import FileMetadata

logger = logging.getLogger(__name__)


class FileItem:
    """Represents a single file item with its properties."""

    def __init__(self, file_path: Path, status: str = "Unknown"):
        self.file_path = Path(file_path)
        self.file_name = self.file_path.name
        self.status = status
        self.metadata: FileMetadata | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Note: metadata is converted to dict for backward compatibility
        with CLI JSON output and serialization.
        """
        metadata_dict = None
        if self.metadata is not None:
            # Convert FileMetadata dataclass to dict
            metadata_dict = {
                "title": self.metadata.title,
                "year": self.metadata.year,
                "season": self.metadata.season,
                "episode": self.metadata.episode,
                "file_path": str(self.metadata.file_path),
                "file_type": self.metadata.file_type,
                "genres": self.metadata.genres,
                "overview": self.metadata.overview,
                "poster_path": self.metadata.poster_path,
                "vote_average": self.metadata.vote_average,
                "tmdb_id": self.metadata.tmdb_id,
                "media_type": self.metadata.media_type,
            }

        return {
            "file_name": self.file_name,
            "file_path": str(self.file_path),
            "status": self.status,
            "metadata": metadata_dict,
        }


class FileTreeModel(QStandardItemModel):
    """
    Model for displaying files in the QTreeView.

    This model manages the file data and provides it to the view
    in a structured format with columns for File Name, Path, and Status.

    Note: For optimal sorting and filtering performance, use FileTreeProxyModel
    as an intermediary between this model and QTreeView.
    """

    # Signals
    file_selected: Signal = Signal(FileItem)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        # Set up column headers
        self.setHorizontalHeaderLabels(
            ["File Name", "Path", "Status", "Matched Series"],
        )

        # Configure model properties
        # Note: Sorting is now handled by FileTreeProxyModel
        # This model only manages data, not sorting/filtering
        self.setSortRole(Qt.DisplayRole)

    def add_file(
        self,
        file_item: FileItem,
        parent_item: QStandardItem | None = None,
    ) -> None:
        """Add a file item to the model."""
        # Create items for each column
        name_item = QStandardItem(file_item.file_name)
        path_item = QStandardItem(str(file_item.file_path))
        status_item = QStandardItem(file_item.status)
        matched_item = QStandardItem("")  # Initially empty for matched series

        # Set data for sorting and filtering
        name_item.setData(file_item.file_name, Qt.DisplayRole)
        path_item.setData(str(file_item.file_path), Qt.DisplayRole)
        status_item.setData(file_item.status, Qt.DisplayRole)
        matched_item.setData("", Qt.DisplayRole)

        # Store the FileItem object in the name item for easy access
        name_item.setData(file_item, Qt.UserRole)

        # Add items to the model
        if parent_item:
            parent_item.appendRow([name_item, path_item, status_item, matched_item])
        else:
            self.appendRow([name_item, path_item, status_item, matched_item])

        logger.debug("Added file to model: %s", file_item.file_name)

    def add_group(self, group_name: str, files: list[FileItem]) -> None:
        """Add a group of files as a hierarchical structure."""
        # Create group parent item
        group_item = QStandardItem(f"📁 {group_name} ({len(files)} files)")
        group_path_item = QStandardItem("")  # Empty for group
        group_status_item = QStandardItem("Group")

        # Set group item properties
        group_item.setData(group_name, Qt.UserRole)
        group_item.setData(files, Qt.UserRole + 1)

        # Make group item bold
        font = group_item.font()
        font.setBold(True)
        group_item.setFont(font)

        # Add group header
        self.appendRow([group_item, group_path_item, group_status_item])

        # Add files as children
        for file_item in files:
            self.add_file(file_item, group_item)

        logger.debug("Added group '%s' with %d files", group_name, len(files))

    def add_files(self, files: list[FileItem]) -> None:
        """Add multiple file items to the model."""
        for file_item in files:
            self.add_file(file_item)

        logger.info("Added %d files to model", len(files))

    def clear_files(self) -> None:
        """Clear all files from the model."""
        self.removeRows(0, self.rowCount())
        logger.debug("Cleared all files from model")

    def get_file_item(self, index: QModelIndex) -> FileItem | None:
        """Get the FileItem object from a model index."""
        if not index.isValid():
            return None

        item = self.itemFromIndex(index)
        if item:
            file_item = item.data(Qt.UserRole)
            return file_item if isinstance(file_item, FileItem) else None
        return None

    def update_file_status(self, file_path: Path, new_status: str) -> None:
        """Update the status of a specific file."""
        for row in range(self.rowCount()):
            name_item = self.item(row, 0)
            if name_item:
                file_item = name_item.data(Qt.UserRole)
                if file_item and file_item.file_path == file_path:
                    # Update the status item
                    status_item = self.item(row, 2)
                    if status_item:
                        status_item.setText(new_status)
                        status_item.setData(new_status, Qt.DisplayRole)  # pylint: disable=line-too-long  # type: ignore[attr-defined]

                    # Update the file item
                    file_item.status = new_status

                    logger.debug(
                        "Updated status for %s: %s",
                        file_path.name,
                        new_status,
                    )
                    break

    def update_file_match_result(
        self,
        file_path: Path,
        match_result: FileMetadata | None,
        status: str,
    ) -> None:
        """
        Update the matched series information for a specific file.

        Args:
            file_path: Path of the file to update
            match_result: FileMetadata instance or None if no match
            status: New status for the file ('Matched', 'Failed', etc.)
        """
        for row in range(self.rowCount()):
            name_item = self.item(row, 0)
            if name_item:
                file_item = name_item.data(Qt.UserRole)
                if file_item and file_item.file_path == file_path:
                    # Update the status item
                    status_item = self.item(row, 2)
                    if status_item:
                        status_item.setText(status)
                        status_item.setData(status, Qt.DisplayRole)

                    # Extract title for display
                    series_title = "Unknown"
                    if match_result:
                        series_title = match_result.title or "Unknown"

                    # Update the matched series item
                    matched_item = self.item(row, 3)
                    if matched_item:
                        if match_result:
                            matched_item.setText(series_title)
                            matched_item.setData(series_title, Qt.DisplayRole)  # pylint: disable=line-too-long  # type: ignore[attr-defined]
                        else:
                            matched_item.setText("No match found")
                            matched_item.setData("No match found", Qt.DisplayRole)

                    # Update the file item status and metadata
                    file_item.status = status
                    file_item.metadata = match_result

                    logger.debug(
                        "Updated match result for %s: %s -> %s",
                        file_path.name,
                        status,
                        series_title if match_result else "No match",
                    )
                    break

    def get_all_files(self) -> list[FileItem]:
        """Get all file items from the model."""
        files = []
        for row in range(self.rowCount()):
            name_item = self.item(row, 0)
            if name_item:
                file_item = name_item.data(Qt.UserRole)
                if file_item:
                    files.append(file_item)
        return files

    def get_files_by_status(self, status: str) -> list[FileItem]:
        """Get all files with a specific status."""
        files = []
        for row in range(self.rowCount()):
            status_item = self.item(row, 2)
            if status_item and status_item.text() == status:
                name_item = self.item(row, 0)
                if name_item:
                    file_item = name_item.data(Qt.UserRole)
                    if file_item:
                        files.append(file_item)
        return files


class FileTreeProxyModel(QSortFilterProxyModel):
    """
    Proxy model for FileTreeModel that handles sorting and filtering.

    This proxy model sits between FileTreeModel and QTreeView, handling
    all sorting and filtering operations at the view level. This prevents
    the need to re-sort the entire model when filter conditions change.

    Usage:
        >>> source_model = FileTreeModel()
        >>> proxy_model = FileTreeProxyModel()
        >>> proxy_model.setSourceModel(source_model)
        >>> tree_view.setModel(proxy_model)
    """

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the proxy model.

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)

        # Configure proxy model properties
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setDynamicSortFilter(True)  # Enable dynamic sorting/filtering

        # Default to sorting by first column (File Name)
        self.setSortRole(Qt.DisplayRole)

    def filterAcceptsRow(
        self,
        source_row: int,
        source_parent: QModelIndex,
    ) -> bool:
        """Determine if a row should be included in the filtered view.

        This method is called by QSortFilterProxyModel to determine
        which rows should be visible based on the current filter.

        Args:
            source_row: Row index in the source model
            source_parent: Parent index in the source model

        Returns:
            True if the row should be shown, False otherwise
        """
        # Get the source model
        source_model = self.sourceModel()
        if not source_model:
            return False

        # Check if any column in the row matches the filter
        filter_pattern = self.filterRegularExpression().pattern()
        if not filter_pattern:
            return True  # No filter, show all rows

        # Check each searchable column (File Name, Path, Status)
        searchable_columns = [0, 1, 2]  # File Name, Path, Status
        for column in searchable_columns:
            index = source_model.index(source_row, column, source_parent)
            if index.isValid():
                data = source_model.data(index, Qt.DisplayRole)
                if data:
                    data_str = str(data).lower()
                    # Use substring matching (setFilterFixedString uses QRegularExpression.escape)
                    if filter_pattern.lower() in data_str:
                        return True

        return False

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Compare two items for sorting.

        This method is called by QSortFilterProxyModel to determine
        the sort order of items.

        Args:
            left: Left index to compare
            right: Right index to compare

        Returns:
            True if left < right, False otherwise
        """
        # Get data from both indices
        left_data = self.sourceModel().data(left, Qt.DisplayRole)
        right_data = self.sourceModel().data(right, Qt.DisplayRole)

        # Handle None values
        if left_data is None:
            return False
        if right_data is None:
            return True

        # Convert to string for comparison
        left_str = str(left_data)
        right_str = str(right_data)

        # Case-insensitive comparison
        return left_str.lower() < right_str.lower()
