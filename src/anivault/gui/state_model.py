"""
State management for AniVault GUI

This module contains the state model that manages the application's
shared state, ensuring separation of data from the view.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from .models import FileItem

logger = logging.getLogger(__name__)


class StateModel(QObject):
    """
    State model for managing application state.

    This class manages the shared state of the application including
    the selected directory, scanned files, and their metadata.
    """

    # Signals for state changes
    directory_changed = Signal(str)
    files_updated = Signal(list)
    file_status_changed = Signal(Path, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Application state
        self._selected_directory: Path | None = None
        self._scanned_files: list[FileItem] = []
        self._file_status_cache: dict[Path, str] = {}

        # Metadata cache
        self._metadata_cache: dict[Path, dict[str, Any]] = {}

        # Operation tracking
        self._last_operation_id: str | None = None
        self._operation_history: list[dict[str, Any]] = []

        logger.info("StateModel initialized")

    @property
    def selected_directory(self) -> Path | None:
        """Get the currently selected directory."""
        return self._selected_directory

    @selected_directory.setter
    def selected_directory(self, directory: Path) -> None:
        """Set the selected directory and emit signal."""
        if self._selected_directory != directory:
            self._selected_directory = Path(directory)
            self._clear_file_data()  # Clear previous scan results
            self.directory_changed.emit(str(directory))
            logger.info("Directory changed to: %s", directory)

    @property
    def scanned_files(self) -> list[FileItem]:
        """Get the list of scanned files."""
        return self._scanned_files.copy()

    @property
    def file_count(self) -> int:
        """Get the total number of scanned files."""
        return len(self._scanned_files)

    def add_scanned_files(self, files: list[FileItem]) -> None:
        """Add scanned files to the state."""
        # Clear existing files first
        self._scanned_files.clear()

        # Add new files
        for file_item in files:
            self._scanned_files.append(file_item)
            self._file_status_cache[file_item.file_path] = file_item.status

        self.files_updated.emit(self._scanned_files.copy())
        logger.info("Added %d scanned files to state", len(files))

    def update_file_status(self, file_path: Path, status: str) -> None:
        """Update the status of a specific file."""
        file_path = Path(file_path)

        # Update the cache
        self._file_status_cache[file_path] = status

        # Update the file item if it exists
        for file_item in self._scanned_files:
            if file_item.file_path == file_path:
                file_item.status = status
                break

        self.file_status_changed.emit(file_path, status)
        logger.debug("Updated file status: %s -> %s", file_path.name, status)

    def get_file_status(self, file_path: Path) -> str:
        """Get the status of a specific file."""
        return self._file_status_cache.get(Path(file_path), "Unknown")

    def get_files_by_status(self, status: str) -> list[FileItem]:
        """Get all files with a specific status."""
        return [f for f in self._scanned_files if f.status == status]

    def set_file_metadata(self, file_path: Path, metadata: dict[str, Any]) -> None:
        """Set metadata for a specific file."""
        file_path = Path(file_path)
        self._metadata_cache[file_path] = metadata.copy()

        # Update the file item if it exists
        for file_item in self._scanned_files:
            if file_item.file_path == file_path:
                file_item.metadata = metadata.copy()
                break

        logger.debug("Set metadata for file: %s", file_path.name)

    def get_file_metadata(self, file_path: Path) -> dict[str, Any] | None:
        """Get metadata for a specific file."""
        return self._metadata_cache.get(Path(file_path))

    def log_operation(self, operation_type: str, details: dict[str, Any]) -> str:
        """Log an operation for audit trail."""
        operation_id = f"{operation_type}_{datetime.now().isoformat()}"
        operation = {
            "id": operation_id,
            "type": operation_type,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        }

        self._operation_history.append(operation)
        self._last_operation_id = operation_id

        logger.info("Logged operation: %s", operation_type)
        return operation_id

    def get_operation_history(self) -> list[dict[str, Any]]:
        """Get the operation history."""
        return self._operation_history.copy()

    def get_last_operation_id(self) -> str | None:
        """Get the ID of the last operation."""
        return self._last_operation_id

    def _clear_file_data(self) -> None:
        """Clear file-related data."""
        self._scanned_files.clear()
        self._file_status_cache.clear()
        self._metadata_cache.clear()
        logger.debug("Cleared file data")

    def export_state(self, file_path: Path) -> None:
        """Export current state to a JSON file."""
        state_data = {
            "selected_directory": (
                str(self._selected_directory) if self._selected_directory else None
            ),
            "scanned_files": [f.to_dict() for f in self._scanned_files],
            "file_status_cache": {
                str(k): v for k, v in self._file_status_cache.items()
            },
            "metadata_cache": {str(k): v for k, v in self._metadata_cache.items()},
            "operation_history": self._operation_history,
            "export_timestamp": datetime.now().isoformat(),
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)

        logger.info("Exported state to: %s", file_path)

    def import_state(self, file_path: Path) -> bool:
        """Import state from a JSON file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                state_data = json.load(f)

            # Restore state
            if state_data.get("selected_directory"):
                self._selected_directory = Path(state_data["selected_directory"])

            # Restore scanned files
            self._scanned_files.clear()
            for file_data in state_data.get("scanned_files", []):
                file_item = FileItem(
                    Path(file_data["file_path"]),
                    file_data.get("status", "Unknown"),
                )
                file_item.metadata = file_data.get("metadata")
                self._scanned_files.append(file_item)

            # Restore caches
            self._file_status_cache = {
                Path(k): v for k, v in state_data.get("file_status_cache", {}).items()
            }
            self._metadata_cache = {
                Path(k): v for k, v in state_data.get("metadata_cache", {}).items()
            }

            self._operation_history = state_data.get("operation_history", [])

            # Emit signals
            self.files_updated.emit(self._scanned_files.copy())

            logger.info("Imported state from: %s", file_path)
            return True

        except Exception as e:
            logger.exception("Failed to import state: %s", e)
            return False
