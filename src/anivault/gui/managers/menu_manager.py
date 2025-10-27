"""Menu and Toolbar Manager.

This module provides MenuManager, which handles all menu bar and toolbar
setup for MainWindow. It encapsulates menu/toolbar creation logic and provides
a clean API for MainWindow to access and control menu actions.

Design Pattern:
    - Follows the controller/manager pattern established in the codebase
    - Inherits from QObject for signal/slot support
    - Delegates business logic to MainWindow handlers
    - Provides action registry for external access

Usage:
    >>> menu_manager = MenuManager(main_window)
    >>> menu_manager.setup_all()
    >>> menu_manager.enable_organize_action()
    >>> action = menu_manager.get_action("organize")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from anivault.gui.main_window import MainWindow


class MenuManager:
    """Manages menu bar and toolbar for MainWindow.

    This class extracts menu/toolbar setup logic from MainWindow to improve
    separation of concerns and maintainability. It creates all menu items,
    toolbar actions, and provides APIs for external control.

    Note: This class does NOT inherit from QObject as it does not emit signals.
    It simply manages QActions and delegates events to MainWindow handlers.

    Attributes:
        _main_window: Reference to the parent MainWindow
        _actions: Registry of all created actions for external access
        _theme_action_group: QActionGroup for exclusive theme selection

    Menu Structure:
        - File: Open Folder, Organize Files, Exit
        - Settings: Configure API Key
        - View > Theme: Light, Dark
        - Help: About

    Toolbar Actions:
        - Open Folder
        - Organize Files
    """

    def __init__(self, main_window: MainWindow) -> None:
        """Initialize MenuManager.

        Args:
            main_window: Parent MainWindow instance for handler connections
        """
        self._main_window = main_window
        self._actions: dict[str, QAction] = {}
        self._theme_action_group: QActionGroup | None = None

    def setup_all(self) -> None:
        """Set up all menus and toolbar.

        This is the main entry point that MainWindow should call during
        initialization to create all menu/toolbar UI elements.
        """
        self._create_actions()
        self._setup_menubar()
        self._setup_toolbar()

    def _create_actions(self) -> None:
        """Create all menu actions and register them.

        Actions are created here and stored in _actions registry for
        later access. Handlers are connected to MainWindow methods.
        """
        # File menu actions
        open_folder_action = QAction("&Open Folder", self._main_window)
        open_folder_action.setShortcut("Ctrl+O")
        open_folder_action.setObjectName("openFolderAction")
        open_folder_action.triggered.connect(self._main_window.open_folder)
        self._actions["open_folder"] = open_folder_action

        organize_action = QAction("📦 &Organize Files...", self._main_window)
        organize_action.setShortcut("Ctrl+Shift+O")
        organize_action.setObjectName("organizeFilesAction")
        organize_action.triggered.connect(self._main_window.organize_files)
        organize_action.setEnabled(False)  # Enabled after matching
        self._actions["organize"] = organize_action

        exit_action = QAction("E&xit", self._main_window)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self._main_window.close)
        self._actions["exit"] = exit_action

        # Settings menu actions
        api_key_action = QAction("Configure &API Key...", self._main_window)
        api_key_action.setShortcut("Ctrl+K")
        api_key_action.triggered.connect(self._main_window.open_settings_dialog)
        self._actions["api_key"] = api_key_action

        # View > Theme actions with exclusive selection
        self._theme_action_group = QActionGroup(self._main_window)
        self._theme_action_group.setExclusive(True)

        light_theme_action = QAction("&Light", self._main_window)
        light_theme_action.setCheckable(True)
        light_theme_action.setData("light")
        light_theme_action.triggered.connect(
            lambda: self._main_window.switch_theme(light_theme_action),
        )
        self._theme_action_group.addAction(light_theme_action)
        self._actions["theme_light"] = light_theme_action

        dark_theme_action = QAction("&Dark", self._main_window)
        dark_theme_action.setCheckable(True)
        dark_theme_action.setData("dark")
        dark_theme_action.triggered.connect(
            lambda: self._main_window.switch_theme(dark_theme_action),
        )
        self._theme_action_group.addAction(dark_theme_action)
        self._actions["theme_dark"] = dark_theme_action

        # Help menu actions
        about_action = QAction("&About", self._main_window)
        about_action.triggered.connect(self._main_window.show_about)
        self._actions["about"] = about_action

    def _setup_menubar(self) -> None:
        """Set up the menu bar structure.

        Creates all menu items and adds actions to appropriate menus.
        """
        menubar = self._main_window.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self._actions["open_folder"])
        file_menu.addSeparator()
        file_menu.addAction(self._actions["organize"])
        file_menu.addSeparator()
        file_menu.addAction(self._actions["exit"])

        # Settings menu
        settings_menu = menubar.addMenu("&Settings")
        settings_menu.addAction(self._actions["api_key"])

        # View menu with Theme submenu
        view_menu = menubar.addMenu("&View")
        theme_menu = view_menu.addMenu("&Theme")
        theme_menu.addAction(self._actions["theme_light"])
        theme_menu.addAction(self._actions["theme_dark"])

        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self._actions["about"])

    def _setup_toolbar(self) -> None:
        """Set up the toolbar with main actions.

        Adds frequently used actions (Open Folder, Organize Files) to toolbar.
        """
        toolbar = self._main_window.addToolBar("Main Toolbar")

        # Add main actions
        toolbar.addAction(self._actions["open_folder"])
        toolbar.addSeparator()
        toolbar.addAction(self._actions["organize"])
        toolbar.addSeparator()

        # Spacer for future actions
        toolbar.addWidget(QWidget())

    # Public API for external control

    def get_action(self, name: str) -> QAction | None:
        """Get action by name from registry.

        Args:
            name: Action name (e.g., "open_folder", "organize", "theme_light")

        Returns:
            QAction if found, None otherwise

        Example:
            >>> organize_action = menu_manager.get_action("organize")
            >>> organize_action.setEnabled(True)
        """
        return self._actions.get(name)

    def enable_organize_action(self) -> None:
        """Enable the Organize Files action.

        Convenience method for MainWindow to enable organize action
        after TMDB matching completes.
        """
        organize_action = self._actions.get("organize")
        if organize_action:
            organize_action.setEnabled(True)

    def disable_organize_action(self) -> None:
        """Disable the Organize Files action.

        Convenience method for MainWindow to disable organize action
        when no files are ready for organization.
        """
        organize_action = self._actions.get("organize")
        if organize_action:
            organize_action.setEnabled(False)
