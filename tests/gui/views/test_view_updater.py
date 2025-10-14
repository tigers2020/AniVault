"""Unit tests for ViewUpdater.

This module tests the ViewUpdater class, which handles view updates
for file trees, groups, and file lists.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from anivault.gui.views.view_updater import ViewUpdater


class TestViewUpdaterInit:
    """Tests for ViewUpdater initialization."""

    def test_init_with_all_dependencies(self) -> None:
        """Test initialization with all required dependencies."""
        group_view = Mock()
        file_list = Mock()
        group_details_label = Mock()
        status_manager = Mock()

        updater = ViewUpdater(
            group_view=group_view,
            file_list=file_list,
            group_details_label=group_details_label,
            status_manager=status_manager,
        )

        assert updater._group_view is group_view
        assert updater._file_list is file_list
        assert updater._group_details_label is group_details_label
        assert updater._status_manager is status_manager


class TestUpdateFileTreeWithGroups:
    """Tests for update_file_tree_with_groups method."""

    def test_update_file_tree_with_groups(self) -> None:
        """Test updating file tree with grouped files."""
        group_view = Mock()
        updater = ViewUpdater(
            group_view=group_view,
            file_list=Mock(),
            group_details_label=Mock(),
            status_manager=Mock(),
        )

        grouped_files = {
            "Group A": [Mock(), Mock()],
            "Group B": [Mock(), Mock(), Mock()],
        }

        updater.update_file_tree_with_groups(grouped_files)

        # Verify group_view.update_groups was called
        group_view.update_groups.assert_called_once()
        call_args = group_view.update_groups.call_args
        assert call_args[0][0] == grouped_files
        # Second argument should be the on_group_selected callback
        assert callable(call_args[0][1])

    def test_update_file_tree_with_empty_groups(self) -> None:
        """Test updating file tree with empty groups dictionary."""
        group_view = Mock()
        updater = ViewUpdater(
            group_view=group_view,
            file_list=Mock(),
            group_details_label=Mock(),
            status_manager=Mock(),
        )

        grouped_files: dict[str, list[Any]] = {}

        updater.update_file_tree_with_groups(grouped_files)

        group_view.update_groups.assert_called_once_with(
            grouped_files,
            updater.on_group_selected,
        )


class TestOnGroupSelected:
    """Tests for on_group_selected method."""

    def test_on_group_selected_with_path_objects(self) -> None:
        """Test group selection with Path objects."""
        file_list = Mock()
        group_details_label = Mock()
        updater = ViewUpdater(
            group_view=Mock(),
            file_list=file_list,
            group_details_label=group_details_label,
            status_manager=Mock(),
        )

        # Mock file items with file_path as Path
        file1 = Mock()
        file1.file_path = Path("/path/to/file1.mkv")
        file2 = Mock()
        file2.file_path = Path("/path/to/file2.mkv")

        files = [file1, file2]

        updater.on_group_selected("Test Group", files)

        # Verify group details label updated
        group_details_label.setText.assert_called_once()
        assert "Test Group" in group_details_label.setText.call_args[0][0]
        assert "2 files" in group_details_label.setText.call_args[0][0]

        # Verify file list cleared and populated
        file_list.clear.assert_called_once()
        assert file_list.addItem.call_count == 2

    def test_on_group_selected_with_file_name_attribute(self) -> None:
        """Test group selection with file_name attribute (fallback)."""
        file_list = Mock()
        group_details_label = Mock()
        updater = ViewUpdater(
            group_view=Mock(),
            file_list=file_list,
            group_details_label=group_details_label,
            status_manager=Mock(),
        )

        # Mock file items with file_name attribute
        file1 = Mock()
        file1.file_path = "/path/to/file1.mkv"  # String, not Path
        file1.file_name = "file1.mkv"
        file2 = Mock()
        file2.file_path = "/path/to/file2.mkv"
        file2.file_name = "file2.mkv"

        files = [file1, file2]

        updater.on_group_selected("Test Group", files)

        # Verify file list populated with fallback format
        assert file_list.addItem.call_count == 2
        # Check that file_name was used
        call_args = [call[0][0] for call in file_list.addItem.call_args_list]
        assert any("file1.mkv" in arg for arg in call_args)
        assert any("file2.mkv" in arg for arg in call_args)

    def test_on_group_selected_with_empty_files(self) -> None:
        """Test group selection with empty file list."""
        file_list = Mock()
        group_details_label = Mock()
        updater = ViewUpdater(
            group_view=Mock(),
            file_list=file_list,
            group_details_label=group_details_label,
            status_manager=Mock(),
        )

        updater.on_group_selected("Empty Group", [])

        # Verify group details label updated
        group_details_label.setText.assert_called_once()
        assert "Empty Group" in group_details_label.setText.call_args[0][0]
        assert "0 files" in group_details_label.setText.call_args[0][0]

        # Verify file list cleared but nothing added
        file_list.clear.assert_called_once()
        file_list.addItem.assert_not_called()

    def test_on_group_selected_with_missing_attributes(self) -> None:
        """Test group selection with files missing expected attributes."""
        file_list = Mock()
        group_details_label = Mock()
        updater = ViewUpdater(
            group_view=Mock(),
            file_list=file_list,
            group_details_label=group_details_label,
            status_manager=Mock(),
        )

        # Mock file item with no file_path or file_name
        file1 = Mock(spec=[])  # Empty spec, no attributes
        files = [file1]

        updater.on_group_selected("Test Group", files)

        # Should still work with fallback values
        file_list.clear.assert_called_once()
        file_list.addItem.assert_called_once()
        # Check that fallback "Unknown" values were used
        call_arg = file_list.addItem.call_args[0][0]
        assert "Unknown" in call_arg


class TestUpdateFileTree:
    """Tests for update_file_tree method."""

    def test_update_file_tree_with_files(self) -> None:
        """Test updating file tree with ungrouped files."""
        group_view = Mock()
        status_manager = Mock()
        updater = ViewUpdater(
            group_view=group_view,
            file_list=Mock(),
            group_details_label=Mock(),
            status_manager=status_manager,
        )

        files = [Mock(), Mock(), Mock()]

        updater.update_file_tree(files)

        # Verify groups cleared
        group_view.clear_groups.assert_called_once()

        # Verify "All Files" group added
        group_view.add_group.assert_called_once_with("All Files", files)

        # Verify status message
        status_manager.show_message.assert_called_once()
        assert "3 files" in status_manager.show_message.call_args[0][0]

    def test_update_file_tree_with_empty_list(self) -> None:
        """Test updating file tree with empty file list."""
        group_view = Mock()
        status_manager = Mock()
        updater = ViewUpdater(
            group_view=group_view,
            file_list=Mock(),
            group_details_label=Mock(),
            status_manager=status_manager,
        )

        files: list[Any] = []

        updater.update_file_tree(files)

        # Verify groups cleared
        group_view.clear_groups.assert_called_once()

        # Verify no group added
        group_view.add_group.assert_not_called()

        # Verify status message still shown
        status_manager.show_message.assert_called_once()
        assert "0 files" in status_manager.show_message.call_args[0][0]

    def test_update_file_tree_preserves_file_list(self) -> None:
        """Test that update_file_tree preserves the original file list."""
        group_view = Mock()
        updater = ViewUpdater(
            group_view=group_view,
            file_list=Mock(),
            group_details_label=Mock(),
            status_manager=Mock(),
        )

        original_files = [Mock(), Mock()]
        files = list(original_files)  # Copy

        updater.update_file_tree(files)

        # Verify add_group was called with a new list (not the original)
        call_args = group_view.add_group.call_args[0]
        assert call_args[1] is not original_files
        assert len(call_args[1]) == len(original_files)
