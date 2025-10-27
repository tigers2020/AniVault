"""GUI Managers Package.

This package contains manager classes that handle specific UI responsibilities
extracted from MainWindow to improve separation of concerns and maintainability.

Managers:
    MenuManager: Handles menu bar and toolbar creation, configuration, and updates
    StatusManager: Manages status bar messages and cache status display
    SignalCoordinator: Centralizes signal connections between components

Design Pattern:
    Each manager follows the established pattern of gui/controllers:
    - Inherits from QObject for signal/slot support
    - Exposes signals for MainWindow to connect
    - Provides clean public API for MainWindow to call
    - Encapsulates implementation details

Usage:
    Managers are instantiated and owned by MainWindow during initialization.
    MainWindow connects to manager signals and calls manager methods to
    delegate specific UI responsibilities.

Example:
    >>> from anivault.gui.managers import MenuManager
    >>> menu_manager = MenuManager(parent=main_window)
    >>> menu_manager.setup_menus()
    >>> menu_manager.action_triggered.connect(main_window.on_action)
"""

# Managers will be imported here as they are created
from .menu_manager import MenuManager
from .signal_coordinator import SignalCoordinator
from .status_manager import StatusManager

__all__: list[str] = [
    "MenuManager",
    "SignalCoordinator",
    "StatusManager",
]
