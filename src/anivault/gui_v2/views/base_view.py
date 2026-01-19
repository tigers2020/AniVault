"""Base View Class for GUI v2."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from anivault.shared.models.metadata import FileMetadata


class BaseView(QWidget):
    """Base class for all view widgets."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize base view."""
        super().__init__(parent)
        self.view_name = self.__class__.__name__.replace("View", "").lower()
        self._file_metadata: list[FileMetadata] = []

    def refresh(self) -> None:
        """Refresh view data. Override in subclasses."""

    def set_file_metadata(self, files: list[FileMetadata]) -> None:
        """Set file metadata for this view.

        This method stores the shared file metadata list. Subclasses can override
        to implement custom display logic.

        Args:
            files: List of FileMetadata instances shared across all views.
        """
        self._file_metadata = files

    def get_file_metadata(self) -> list[FileMetadata]:
        """Get the shared file metadata list.

        Returns:
            List of FileMetadata instances.
        """
        return self._file_metadata
