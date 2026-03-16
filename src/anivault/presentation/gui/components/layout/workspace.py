"""Workspace composite component: toolbar + view stack."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from anivault.presentation.gui.views.base_view import BaseView
from anivault.presentation.gui.widgets.toolbar_widget import ToolbarWidget


class WorkspaceComponent(QWidget):
    """Composite workspace: toolbar and stacked view area.

    MainWindow assembles this once and delegates toolbar/view stacking here.
    Signals are forwarded from the toolbar for MainWindow to connect handlers.
    """

    match_clicked = Signal()
    organize_preflight_clicked = Signal()
    organize_execute_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize workspace with toolbar and empty view stack."""
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Build toolbar + view stack layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbar = ToolbarWidget()
        self._view_stack = QStackedWidget()

        layout.addWidget(self.toolbar)
        layout.addWidget(self._view_stack)

    def _connect_signals(self) -> None:
        """Forward toolbar signals to this component."""
        self.toolbar.match_clicked.connect(self.match_clicked.emit)
        self.toolbar.organize_preflight_clicked.connect(self.organize_preflight_clicked.emit)
        self.toolbar.organize_execute_clicked.connect(self.organize_execute_clicked.emit)

    @property
    def view_stack(self) -> QStackedWidget:
        """Expose view stack for MainWindow (e.g. iterate views, set current)."""
        return self._view_stack

    def add_view(self, view: BaseView) -> None:
        """Add a view widget to the stack."""
        self._view_stack.addWidget(view)

    def set_view(self, view_name: str) -> None:
        """Update toolbar for view and keep stack on first (shared) view."""
        self.toolbar.set_view(view_name)
        self._view_stack.setCurrentIndex(0)
