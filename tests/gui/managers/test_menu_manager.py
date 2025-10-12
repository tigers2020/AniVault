"""Unit tests for MenuManager.

This module tests MenuManager functionality including:
- Menu and toolbar setup
- Action registration and retrieval
- Action enable/disable control
- Handler connections to MainWindow
"""

from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtWidgets import QMainWindow
from pytestqt.qtbot import QtBot

from anivault.gui.managers.menu_manager import MenuManager

if TYPE_CHECKING:
    from anivault.gui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot: QtBot) -> QMainWindow:
    """Create a real QMainWindow instance for testing.

    Args:
        qtbot: PyTest-Qt fixture for Qt testing

    Returns:
        QMainWindow instance
    """
    window = QMainWindow()
    qtbot.addWidget(window)

    # Mock handler methods (these would normally be implemented in MainWindow)
    window.open_folder = Mock()  # type: ignore
    window.organize_files = Mock()  # type: ignore
    window.open_settings_dialog = Mock()  # type: ignore
    window.switch_theme = Mock()  # type: ignore
    window.show_about = Mock()  # type: ignore

    return window


@pytest.fixture
def menu_manager(main_window: QMainWindow) -> MenuManager:
    """Create a MenuManager instance for testing.

    Args:
        main_window: Main window fixture

    Returns:
        MenuManager instance
    """
    # Cast QMainWindow to MainWindow for type checking
    return MenuManager(cast("MainWindow", main_window))


class TestMenuManager:
    """Unit tests for MenuManager class."""

    def test_init(
        self,
        main_window: QMainWindow,
        menu_manager: MenuManager,
    ) -> None:
        """Test MenuManager initialization."""
        assert menu_manager._main_window == main_window
        assert isinstance(menu_manager._actions, dict)
        assert len(menu_manager._actions) == 0
        assert menu_manager._theme_action_group is None

    def test_setup_all_creates_actions(self, menu_manager: MenuManager) -> None:
        """Test that setup_all() creates all required actions."""
        # When: setup_all is called
        menu_manager.setup_all()

        # Then: All actions should be created
        expected_actions = [
            "open_folder",
            "organize",
            "exit",
            "api_key",
            "theme_light",
            "theme_dark",
            "about",
        ]

        for action_name in expected_actions:
            assert (
                action_name in menu_manager._actions
            ), f"Action '{action_name}' should be created"

    def test_setup_all_creates_menubar(
        self,
        main_window: QMainWindow,
        menu_manager: MenuManager,
    ) -> None:
        """Test that setup_all() creates menu bar."""
        # When: setup_all is called
        menu_manager.setup_all()

        # Then: Menu bar should exist
        assert main_window.menuBar() is not None

    def test_setup_all_creates_toolbar(
        self,
        main_window: QMainWindow,
        menu_manager: MenuManager,
    ) -> None:
        """Test that setup_all() creates toolbar."""
        # When: setup_all is called
        menu_manager.setup_all()

        # Then: Toolbar should be created
        toolbars = main_window.findChildren(type(main_window.addToolBar("")))
        assert len(toolbars) > 0

    def test_get_action_existing(self, menu_manager: MenuManager) -> None:
        """Test get_action() for existing action."""
        # Given: Actions are created
        menu_manager.setup_all()

        # When: Getting an existing action
        action = menu_manager.get_action("open_folder")

        # Then: Action should be returned
        assert action is not None
        assert action.text() == "&Open Folder"

    def test_get_action_nonexistent(self, menu_manager: MenuManager) -> None:
        """Test get_action() for nonexistent action."""
        # Given: Actions are created
        menu_manager.setup_all()

        # When: Getting a nonexistent action
        action = menu_manager.get_action("nonexistent")

        # Then: None should be returned
        assert action is None

    def test_enable_organize_action(self, menu_manager: MenuManager) -> None:
        """Test enable_organize_action() enables the action."""
        # Given: Actions are created and organize action is disabled
        menu_manager.setup_all()
        organize_action = menu_manager.get_action("organize")
        assert organize_action is not None
        assert not organize_action.isEnabled()

        # When: enable_organize_action is called
        menu_manager.enable_organize_action()

        # Then: Organize action should be enabled
        assert organize_action.isEnabled()

    def test_disable_organize_action(self, menu_manager: MenuManager) -> None:
        """Test disable_organize_action() disables the action."""
        # Given: Actions are created and organize action is enabled
        menu_manager.setup_all()
        menu_manager.enable_organize_action()
        organize_action = menu_manager.get_action("organize")
        assert organize_action is not None
        assert organize_action.isEnabled()

        # When: disable_organize_action is called
        menu_manager.disable_organize_action()

        # Then: Organize action should be disabled
        assert not organize_action.isEnabled()

    def test_organize_action_disabled_by_default(
        self, menu_manager: MenuManager
    ) -> None:
        """Test that organize action is disabled by default."""
        # When: Actions are created
        menu_manager.setup_all()

        # Then: Organize action should be disabled
        organize_action = menu_manager.get_action("organize")
        assert organize_action is not None
        assert not organize_action.isEnabled()

    def test_theme_action_group_exclusive(self, menu_manager: MenuManager) -> None:
        """Test that theme actions are exclusive."""
        # Given: Actions are created
        menu_manager.setup_all()

        # Then: Theme action group should be exclusive
        assert menu_manager._theme_action_group is not None
        assert menu_manager._theme_action_group.isExclusive()

        # And: Theme actions should be in the group
        light_action = menu_manager.get_action("theme_light")
        dark_action = menu_manager.get_action("theme_dark")
        assert light_action is not None
        assert dark_action is not None

        actions = menu_manager._theme_action_group.actions()
        assert light_action in actions
        assert dark_action in actions

    def test_action_shortcuts(self, menu_manager: MenuManager) -> None:
        """Test that actions have correct shortcuts."""
        # Given: Actions are created
        menu_manager.setup_all()

        # Then: Actions should have correct shortcuts
        open_folder_action = menu_manager.get_action("open_folder")
        organize_action = menu_manager.get_action("organize")
        exit_action = menu_manager.get_action("exit")
        api_key_action = menu_manager.get_action("api_key")

        assert open_folder_action is not None
        assert organize_action is not None
        assert exit_action is not None
        assert api_key_action is not None

        assert open_folder_action.shortcut().toString() == "Ctrl+O"
        assert organize_action.shortcut().toString() == "Ctrl+Shift+O"
        assert exit_action.shortcut().toString() == "Ctrl+Q"
        assert api_key_action.shortcut().toString() == "Ctrl+K"

    def test_action_object_names(self, menu_manager: MenuManager) -> None:
        """Test that actions have correct object names."""
        # Given: Actions are created
        menu_manager.setup_all()

        # Then: Actions should have correct object names
        open_folder_action = menu_manager.get_action("open_folder")
        organize_action = menu_manager.get_action("organize")

        assert open_folder_action is not None
        assert organize_action is not None

        assert open_folder_action.objectName() == "openFolderAction"
        assert organize_action.objectName() == "organizeFilesAction"

    def test_theme_actions_checkable(self, menu_manager: MenuManager) -> None:
        """Test that theme actions are checkable."""
        # Given: Actions are created
        menu_manager.setup_all()

        # Then: Theme actions should be checkable
        light_action = menu_manager.get_action("theme_light")
        dark_action = menu_manager.get_action("theme_dark")

        assert light_action is not None
        assert dark_action is not None
        assert light_action.isCheckable()
        assert dark_action.isCheckable()

    def test_theme_actions_have_data(self, menu_manager: MenuManager) -> None:
        """Test that theme actions have theme data."""
        # Given: Actions are created
        menu_manager.setup_all()

        # Then: Theme actions should have theme data
        light_action = menu_manager.get_action("theme_light")
        dark_action = menu_manager.get_action("theme_dark")

        assert light_action is not None
        assert dark_action is not None
        assert light_action.data() == "light"
        assert dark_action.data() == "dark"
