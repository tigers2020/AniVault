"""Main content area: Sidebar + Workspace."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget

from anivault.presentation.gui.components.layout.workspace import WorkspaceComponent
from anivault.presentation.gui.widgets.sidebar_widget import SidebarWidget


class MainContentComponent(QWidget):
    """Sidebar and workspace in one horizontal layout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build sidebar + workspace layout."""
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._sidebar = SidebarWidget()
        self._workspace = WorkspaceComponent()
        layout.addWidget(self._sidebar)
        layout.addWidget(self._workspace)

    @property
    def sidebar(self) -> SidebarWidget:
        """Sidebar for navigation and statistics."""
        return self._sidebar

    @property
    def workspace(self) -> WorkspaceComponent:
        """Workspace (toolbar + view stack)."""
        return self._workspace
