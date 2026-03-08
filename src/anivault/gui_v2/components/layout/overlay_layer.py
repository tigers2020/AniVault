"""Overlay layer: DetailPanel + LoadingOverlay with shared geometry updates."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from anivault.gui_v2.widgets.detail_panel import DetailPanel
from anivault.gui_v2.widgets.loading_overlay import LoadingOverlay


class OverlayLayerComponent:
    """Holds DetailPanel and LoadingOverlay on a parent; owns placement and resize."""

    def __init__(self, parent: QWidget) -> None:
        """Create overlay widgets on parent and position them."""
        self._parent = parent
        self._detail_panel = DetailPanel(parent)
        self._loading_overlay = LoadingOverlay(parent)
        self._panel_width = 500
        self._update_initial_geometry()

    def _update_initial_geometry(self) -> None:
        """Position both overlays; call after parent has size."""
        if not self._parent:
            return
        p = self._parent
        w, h = p.width(), p.height()
        self._detail_panel.setGeometry(w, 0, self._panel_width, h)
        self._detail_panel.hide()
        self._loading_overlay.setGeometry(0, 0, w, h)
        self._loading_overlay.hide()

    @property
    def detail_panel(self) -> DetailPanel:
        """Detail panel for group details and TMDB match."""
        return self._detail_panel

    @property
    def loading_overlay(self) -> LoadingOverlay:
        """Loading overlay for long operations."""
        return self._loading_overlay

    def update_geometry(self) -> None:
        """Update overlay positions/sizes from parent size; call on resize."""
        if not self._parent:
            return
        p = self._parent
        w, h = p.width(), p.height()
        self._loading_overlay.setGeometry(0, 0, w, h)
        if self._detail_panel.isVisible():
            self._detail_panel.show_panel()
        else:
            self._detail_panel.setGeometry(w, 0, self._panel_width, h)
