"""View Updater for managing UI updates in AniVault.

This module contains the ViewUpdater class that handles view updates
for file trees, groups, and file lists. It centralizes UI update logic
that was previously scattered across MainWindow.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PySide6.QtWidgets import QLabel, QListWidget

    from anivault.gui.managers.status_manager import StatusManager
    from anivault.gui.widgets.group_view import GroupView  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class ViewUpdater:
    """Handles view updates for the AniVault main window.

    This class centralizes UI update logic for:
    - File tree/group views
    - Group selection handling
    - File list displays

    By extracting these responsibilities from MainWindow, we improve
    testability and maintainability of the UI layer.

    Attributes:
        _group_view: GroupView widget for displaying file groups
        _file_list: QListWidget for displaying files in selected group
        _group_details_label: QLabel for showing group information
        _status_manager: StatusManager for status bar updates

    Example:
        >>> updater = ViewUpdater(
        ...     group_view=group_view,
        ...     file_list=file_list,
        ...     group_details_label=details_label,
        ...     status_manager=status_mgr
        ... )
        >>> updater.update_file_tree_with_groups(grouped_files)
    """

    def __init__(
        self,
        group_view: GroupView,
        file_list: QListWidget,
        group_details_label: QLabel,
        status_manager: StatusManager,
    ) -> None:
        """Initialize the view updater.

        Args:
            group_view: GroupView widget for displaying file groups
            file_list: QListWidget for displaying files
            group_details_label: QLabel for group information
            status_manager: StatusManager for status updates
        """
        self._group_view = group_view
        self._file_list = file_list
        self._group_details_label = group_details_label
        self._status_manager = status_manager

    def update_file_tree_with_groups(
        self,
        grouped_files: dict[str, list[Any]],
    ) -> None:
        """Update the group grid view with grouped files as cards.

        This method updates the UI to display files organized into groups,
        with each group shown as a card in the grid view.

        Args:
            grouped_files: Dictionary mapping group names to lists of file items
        """
        # Update the grid view with grouped files
        # Note: on_group_selected callback is set externally via connect_group_selection
        self._group_view.update_groups(grouped_files, self.on_group_selected)

        total_files = sum(len(files) for files in grouped_files.values())
        logger.info(
            "Updated group grid view with %d grouped files in %d groups",
            total_files,
            len(grouped_files),
        )

    def on_group_selected(self, group_name: str, files: list[Any]) -> None:
        """Handle group selection from grid view.

        Updates the file list to show files from the selected group.
        Supports both ScannedFile and FileItem objects through duck typing.

        Args:
            group_name: Name of the selected group
            files: List of file items in the group
        """
        # Update group details header
        self._group_details_label.setText(f"📁 {group_name} ({len(files)} files)")

        # Clear and populate file list
        self._file_list.clear()

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

            self._file_list.addItem(file_text)

        logger.debug("Selected group: %s with %d files", group_name, len(files))

    def update_file_tree(self, files: list[Any]) -> None:
        """Update the group view with scanned files (fallback for ungrouped display).

        This method is used when files are scanned but not grouped. It displays
        all files in a single "All Files" group.

        Args:
            files: List of file items to display
        """
        # Clear existing groups
        self._group_view.clear_groups()

        # Create a single group for all files if no grouping is performed
        if files:
            file_items = list(files)
            self._group_view.add_group("All Files", file_items)

        logger.info("Updated group view with %d files (ungrouped)", len(files))
        self._status_manager.show_message(f"Found {len(files)} files")
