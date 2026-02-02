"""Base event handler for MainWindow delegation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anivault.gui_v2.main_window import MainWindow


class BaseEventHandler:
    """Base class for MainWindow event handlers."""

    def __init__(self, window: MainWindow) -> None:
        """Initialize with MainWindow reference."""
        self._window = window
