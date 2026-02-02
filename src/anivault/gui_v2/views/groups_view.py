"""Groups View for GUI v2."""

from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QGridLayout, QScrollArea, QWidget

from anivault.gui_v2.views.base_view import BaseView
from anivault.gui_v2.widgets.group_card import GroupCard
from anivault.gui_v2.workers.groups_build_worker import (
    GroupsBuildWorker,
    apply_metadata_update_to_groups,
)
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)


class GroupsView(BaseView):
    """Groups management view showing group cards in a grid."""

    # Signals
    group_clicked = Signal(int)  # Emits group ID when a card is clicked

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize groups view."""
        super().__init__(parent)
        self._groups: list[dict] = []
        self._groups_build_thread: QThread | None = None
        self._groups_build_worker: GroupsBuildWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the groups view UI."""
        from PySide6.QtWidgets import QVBoxLayout

        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(0)

        # Scroll area for groups grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("groupsScrollArea")
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        # Grid container
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(24)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(scroll_area)

    def set_groups(self, groups: list[dict]) -> None:
        """Set groups data and update display.

        Args:
            groups: List of group dictionaries with keys:
                - id: int
                - title: str
                - season: int
                - episodes: int
                - files: int
                - matched: bool
                - confidence: int (0-100)
                - resolution: str
                - language: str
        """
        self._groups = groups
        self._update_display()

    def set_file_metadata(self, files: list[FileMetadata]) -> None:
        """Build groups from FileMetadata in background thread and update display."""
        files_with_tmdb = sum(1 for fm in files if getattr(fm, "tmdb_id", None) is not None)
        logger.info(
            "set_file_metadata called with %d files (%d with tmdb_id)",
            len(files),
            files_with_tmdb,
        )
        if not files:
            logger.warning("Empty file list received, clearing groups")
            self.set_groups([])
            return

        # Fast path: metadata-only update (TMDB manual apply) - same paths, no re-grouping
        if self._groups:
            updated = apply_metadata_update_to_groups(self._groups, files)
            if updated is not None:
                logger.info("Fast path: metadata-only update (%d groups)", len(updated))
                self.set_groups(updated)
                return

        # Disconnect and cleanup previous worker if any
        self._cleanup_groups_build_worker()

        # Full rebuild: run grouping off main thread to prevent UI freeze
        worker = GroupsBuildWorker(files)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_groups_built)
        worker.finished.connect(thread.quit)
        worker.error.connect(self._on_groups_build_error)
        worker.error.connect(thread.quit)
        # Cleanup only after thread has fully stopped (prevents "Destroyed while still running")
        thread.finished.connect(lambda t=thread: self._on_groups_thread_finished(t))
        thread.finished.connect(thread.deleteLater)

        self._groups_build_worker = worker
        self._groups_build_thread = thread
        thread.start()

    def _cleanup_groups_build_worker(self) -> None:
        """Disconnect and quit previous groups build worker/thread."""
        if self._groups_build_worker:
            try:
                self._groups_build_worker.finished.disconnect()
                self._groups_build_worker.error.disconnect()
            except (TypeError, RuntimeError):
                pass
            self._groups_build_worker = None
        if self._groups_build_thread and self._groups_build_thread.isRunning():
            self._groups_build_thread.quit()
            self._groups_build_thread.wait(2000)
        self._groups_build_thread = None

    def _on_groups_built(self, groups: list[dict]) -> None:
        """Handle groups build completion (runs on main thread via Qt signal)."""
        logger.info("Received %d groups from worker", len(groups))
        self.set_groups(groups)
        # Do NOT clear _groups_build_worker/thread here - wait for thread.finished

    def _on_groups_build_error(self, error: object) -> None:
        """Handle groups build error (runs on main thread via Qt signal)."""
        logger.warning("Groups build failed: %s", error)
        self.set_groups([])
        # Do NOT clear here - wait for thread.finished (thread.quit was connected)

    def _on_groups_thread_finished(self, thread: QThread) -> None:
        """Clear worker/thread refs only if this is our current thread."""
        if self._groups_build_thread is thread:
            self._groups_build_worker = None
            self._groups_build_thread = None

    def _update_display(self) -> None:
        """Update the groups grid display."""
        logger.debug("_update_display called with %d groups", len(self._groups))
        # Disable updates during bulk changes to avoid per-widget repaints (major perf win)
        self.setUpdatesEnabled(False)
        try:
            # Clear existing cards
            while self.grid_layout.count():
                child = self.grid_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Add group cards
            if not self._groups:
                logger.debug("No groups to display")
                return

            for i, group in enumerate(self._groups):
                card = GroupCard()
                card.set_group_data(group)
                card.card_clicked.connect(self.group_clicked.emit)

                row = i // 3
                col = i % 3
                self.grid_layout.addWidget(card, row, col)

            # Single layout pass after all widgets added
            if self.grid_container:
                self.grid_container.adjustSize()
        finally:
            self.setUpdatesEnabled(True)

    def refresh(self) -> None:
        """Refresh the groups view."""
        self._update_display()
