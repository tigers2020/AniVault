"""Tests for group name update UI functionality.

This module tests the GUI components for updating group names
using parser or manual editing.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from anivault.gui.widgets.group_card_widget import GroupCardWidget
from anivault.gui.widgets.group_grid_view import GroupGridViewWidget
from anivault.gui.models import FileItem


@pytest.fixture
def qapp():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_files():
    """Create sample FileItem objects for testing."""
    return [
        FileItem(file_path=Path("test1.mkv"), status="Scanned"),
        FileItem(file_path=Path("test2.mkv"), status="Scanned"),
        FileItem(file_path=Path("test3.mkv"), status="Scanned"),
    ]


class TestGroupCardWidget:
    """Test cases for GroupCardWidget context menu functionality."""

    def test_context_menu_setup(self, qapp, sample_files):
        """Test that context menu is properly set up."""
        card = GroupCardWidget("Test Group", sample_files)
        
        # Check that context menu policy is set
        assert card.contextMenuPolicy() == Qt.CustomContextMenu

    def test_context_menu_actions(self, qapp, sample_files):
        """Test context menu actions."""
        card = GroupCardWidget("Test Group", sample_files)
        
        # Mock parent widget methods
        mock_parent = Mock()
        mock_parent.update_group_name_with_parser = Mock()
        mock_parent.edit_group_name = Mock()
        card.parent_widget = mock_parent
        
        # Trigger context menu
        card._show_context_menu(card.rect().center())
        
        # Verify parent methods would be called if menu actions were triggered
        # (We can't easily test actual menu interaction in unit tests)
        assert hasattr(card, '_update_group_name_with_parser')
        assert hasattr(card, '_edit_group_name')

    def test_update_group_name_with_parser_callback(self, qapp, sample_files):
        """Test update group name with parser callback."""
        card = GroupCardWidget("Test Group", sample_files)
        
        # Mock parent widget
        mock_parent = Mock()
        mock_parent.update_group_name_with_parser = Mock()
        card.parent_widget = mock_parent
        
        # Call the callback
        card._update_group_name_with_parser()
        
        # Verify parent method was called
        mock_parent.update_group_name_with_parser.assert_called_once_with(
            "Test Group", sample_files
        )

    def test_edit_group_name_callback(self, qapp, sample_files):
        """Test edit group name callback."""
        card = GroupCardWidget("Test Group", sample_files)
        
        # Mock parent widget
        mock_parent = Mock()
        mock_parent.edit_group_name = Mock()
        card.parent_widget = mock_parent
        
        # Call the callback
        card._edit_group_name()
        
        # Verify parent method was called
        mock_parent.edit_group_name.assert_called_once_with(
            "Test Group", sample_files
        )


class TestGroupGridViewWidget:
    """Test cases for GroupGridViewWidget group name update functionality."""

    def test_update_group_name_with_parser_success(self, qapp, sample_files):
        """Test successful group name update with parser."""
        widget = GroupGridViewWidget()
        
        # Add a group card
        widget.add_group("Old Group", sample_files)
        
        # Mock AnitopyParser
        with patch('anivault.core.parser.anitopy_parser.AnitopyParser') as mock_parser_class:
            mock_parser = Mock()
            mock_parser_class.return_value = mock_parser
            
            mock_result = Mock()
            mock_result.title = "New Group Name"
            mock_parser.parse.return_value = mock_result
            
            # Update group name
            widget.update_group_name_with_parser("Old Group", sample_files)
            
            # Verify parser was called
            mock_parser.parse.assert_called_once()
            
            # Verify group card was updated
            assert "Old Group" not in widget.group_cards
            assert "New Group Name" in widget.group_cards

    @pytest.mark.skip(reason="Qt modal dialog blocks test execution - needs event loop fix")
    def test_update_group_name_with_parser_no_parser(self, qapp, sample_files):
        """Test group name update when parser is not available."""
        widget = GroupGridViewWidget()
        
        # Add a group card
        widget.add_group("Old Group", sample_files)
        
        # Mock ImportError
        with patch('anivault.core.parser.anitopy_parser.AnitopyParser', side_effect=ImportError):
            with patch('PySide6.QtWidgets.QMessageBox') as mock_msgbox:
                # Update group name
                widget.update_group_name_with_parser("Old Group", sample_files)
                
                # Verify warning was shown
                mock_msgbox.warning.assert_called_once()
                
                # Verify group card was not updated
                assert "Old Group" in widget.group_cards

    def test_update_group_name_with_parser_group_not_found(self, qapp, sample_files):
        """Test group name update when group is not found."""
        widget = GroupGridViewWidget()
        
        # Try to update non-existent group
        widget.update_group_name_with_parser("Non-existent Group", sample_files)
        
        # Should not raise exception, just log warning

    def test_update_group_name_with_parser_empty_files(self, qapp):
        """Test group name update with empty files list."""
        widget = GroupGridViewWidget()
        
        # Add a group card
        widget.add_group("Test Group", [])
        
        # Try to update with empty files
        widget.update_group_name_with_parser("Test Group", [])
        
        # Should not raise exception, just log warning

    @patch('PySide6.QtWidgets.QInputDialog.getText')
    def test_edit_group_name_success(self, mock_get_text, qapp, sample_files):
        """Test successful manual group name edit."""
        mock_get_text.return_value = ("New Group Name", True)
        
        widget = GroupGridViewWidget()
        
        # Add a group card
        widget.add_group("Old Group", sample_files)
        
        # Edit group name
        widget.edit_group_name("Old Group", sample_files)
        
        # Verify dialog was shown
        mock_get_text.assert_called_once_with(
            widget, "Edit Group Name", "Enter new group name:", text="Old Group"
        )
        
        # Verify group card was updated
        assert "Old Group" not in widget.group_cards
        assert "New Group Name" in widget.group_cards

    @patch('PySide6.QtWidgets.QInputDialog.getText')
    def test_edit_group_name_cancelled(self, mock_get_text, qapp, sample_files):
        """Test group name edit when user cancels."""
        mock_get_text.return_value = ("New Group Name", False)  # User cancelled
        
        widget = GroupGridViewWidget()
        
        # Add a group card
        widget.add_group("Old Group", sample_files)
        
        # Try to edit group name
        widget.edit_group_name("Old Group", sample_files)
        
        # Verify group card was not updated
        assert "Old Group" in widget.group_cards
        assert "New Group Name" not in widget.group_cards

    @patch('PySide6.QtWidgets.QInputDialog.getText')
    def test_edit_group_name_same_name(self, mock_get_text, qapp, sample_files):
        """Test group name edit with same name."""
        mock_get_text.return_value = ("Old Group", True)
        
        widget = GroupGridViewWidget()
        
        # Add a group card
        widget.add_group("Old Group", sample_files)
        
        # Edit group name with same name
        widget.edit_group_name("Old Group", sample_files)
        
        # Verify group card was not updated (same name)
        assert "Old Group" in widget.group_cards

    def test_update_group_card_name_unique_name(self, qapp, sample_files):
        """Test updating group card with unique name."""
        widget = GroupGridViewWidget()
        
        # Add a group card
        widget.add_group("Old Group", sample_files)
        
        # Update with unique name
        widget._update_group_card_name("Old Group", "New Group", sample_files)
        
        # Verify update
        assert "Old Group" not in widget.group_cards
        assert "New Group" in widget.group_cards

    def test_update_group_card_name_conflicting_name(self, qapp, sample_files):
        """Test updating group card with conflicting name."""
        widget = GroupGridViewWidget()
        
        # Add two group cards
        widget.add_group("Group A", sample_files)
        widget.add_group("Group B", sample_files)
        
        # Try to update Group B to Group A (conflict)
        widget._update_group_card_name("Group B", "Group A", sample_files)
        
        # Verify update with unique suffix
        assert "Group B" not in widget.group_cards
        assert "Group A (1)" in widget.group_cards

    def test_update_group_card_name_multiple_conflicts(self, qapp, sample_files):
        """Test updating group card with multiple conflicting names."""
        widget = GroupGridViewWidget()
        
        # Add multiple group cards with similar names
        widget.add_group("Group A", sample_files)
        widget.add_group("Group A (1)", sample_files)
        widget.add_group("Group A (2)", sample_files)
        
        # Try to update another group to Group A
        widget.add_group("Group B", sample_files)
        widget._update_group_card_name("Group B", "Group A", sample_files)
        
        # Verify update with correct suffix
        assert "Group B" not in widget.group_cards
        assert "Group A (3)" in widget.group_cards

    def test_update_group_card_name_parent_details_update(self, qapp, sample_files):
        """Test updating parent window group details when group name changes."""
        widget = GroupGridViewWidget()
        
        # Add a group card
        widget.add_group("Old Group", sample_files)
        
        # Mock parent() method to return mock parent
        mock_parent = Mock()
        mock_parent.group_details_label = Mock()
        mock_parent.group_details_label.text.return_value = "📁 Old Group (3 files)"
        mock_parent.on_group_selected = Mock()
        
        with patch.object(widget, 'parent', return_value=mock_parent):
            # Update group name
            widget._update_group_card_name("Old Group", "New Group", sample_files)
            
            # Verify parent details were updated
            mock_parent.group_details_label.setText.assert_called_once_with(
                "📁 New Group (3 files)"
            )

    def test_update_group_card_name_no_parent_details_update(self, qapp, sample_files):
        """Test group name update when parent doesn't have group details label."""
        widget = GroupGridViewWidget()
        
        # Add a group card
        widget.add_group("Old Group", sample_files)
        
        # Mock parent() method to return parent without group_details_label
        mock_parent = Mock()
        mock_parent.on_group_selected = Mock()
        # Remove group_details_label attribute
        del mock_parent.group_details_label
        
        with patch.object(widget, 'parent', return_value=mock_parent):
            # Update group name (should not raise exception)
            widget._update_group_card_name("Old Group", "New Group", sample_files)
            
            # Verify update still worked
            assert "Old Group" not in widget.group_cards
            assert "New Group" in widget.group_cards
