"""Base View Class for GUI v2."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget


class BaseView(QWidget):
    """Base class for all view widgets."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize base view."""
        super().__init__(parent)
        self.view_name = self.__class__.__name__.replace("View", "").lower()

    def refresh(self) -> None:
        """Refresh view data. Override in subclasses."""
        pass
