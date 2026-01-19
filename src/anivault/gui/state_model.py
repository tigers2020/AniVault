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
from typing import cast

from PySide6.QtCore import QObject, Signal

from anivault.core.data_structures.linked_hash_table import LinkedHashTable
from anivault.shared.errors import (
    AniVaultError,
    ErrorCode,
    ErrorContext,
)
from anivault.shared.models.metadata import FileMetadata
from anivault.shared.types.metadata_types import FileMetadataDict
from anivault.shared.types.operation_types import OperationHistoryDict
from anivault.shared.utils.metadata_converter import MetadataConverter

from .models import FileItem
from .models.operation_history import (
    OperationDetails,
    OperationHistory,
    OperationHistoryEntry,
)

logger = logging.getLogger(__name__)


class StateModel(QObject):
    """
    State model for managing application state.

    This class manages the shared state of the application including
    the selected directory, scanned files, and their metadata.
    """

    # Signals for state changes
    directory_changed: Signal = Signal(str)  # Emits directory path as string
    files_updated: Signal = Signal(list)  # Emits list[FileItem]
    file_status_changed: Signal = Signal(Path, str)  # Emits (file_path, status)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        # Application state
        self._selected_directory: Path | None = None
        self._scanned_files: list[FileItem] = []
        self._file_status_cache: LinkedHashTable[Path, str] = LinkedHashTable()

        # Metadata cache
        self._metadata_cache: LinkedHashTable[Path, FileMetadata] = LinkedHashTable()

        # Operation tracking
        self._last_operation_id: str | None = None
        self._operation_history = OperationHistory()

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
            self._file_status_cache.put(file_item.file_path, file_item.status)

        self.files_updated.emit(self._scanned_files.copy())
        logger.info("Added %d scanned files to state", len(files))

    def update_file_status(self, file_path: Path, status: str) -> None:
        """Update the status of a specific file."""
        file_path = Path(file_path)

        # Update the cache
        self._file_status_cache.put(file_path, status)

        # Update the file item if it exists
        for file_item in self._scanned_files:
            if file_item.file_path == file_path:
                file_item.status = status
                break

        self.file_status_changed.emit(file_path, status)
        logger.debug("Updated file status: %s -> %s", file_path.name, status)

    def get_file_status(self, file_path: Path) -> str:
        """Get the status of a specific file."""
        status = self._file_status_cache.get(Path(file_path))
        return status if status is not None else "Unknown"

    def get_files_by_status(self, status: str) -> list[FileItem]:
        """Get all files with a specific status."""
        return [f for f in self._scanned_files if f.status == status]

    def set_file_metadata(self, file_path: Path, metadata: FileMetadata) -> None:
        """Set metadata for a specific file."""
        file_path = Path(file_path)
        self._metadata_cache.put(file_path, metadata)

        # Update the file item if it exists
        for file_item in self._scanned_files:
            if file_item.file_path == file_path:
                file_item.metadata = metadata
                break

        logger.debug("Set metadata for file: %s", file_path.name)

    def get_file_metadata(self, file_path: Path) -> FileMetadata | None:
        """Get metadata for a specific file."""
        return self._metadata_cache.get(Path(file_path))

    def log_operation(self, operation_type: str, details: OperationDetails) -> str:
        """Log an operation for audit trail."""
        operation_id = f"{operation_type}_{datetime.now().isoformat()}"
        entry = OperationHistoryEntry(
            id=operation_id,
            type=operation_type,
            timestamp=datetime.now(),
            details=details,
        )

        self._operation_history.add(entry)
        self._last_operation_id = operation_id

        logger.info("Logged operation: %s", operation_type)
        return operation_id

    def get_operation_history(self) -> list[OperationHistoryDict]:
        """Get the operation history.

        Returns:
            List of operation history entries as dictionaries (JSON-serializable)
        """
        return self._operation_history.to_dict()

    def get_operation_history_entries(self) -> list[OperationHistoryEntry]:
        """Get the operation history as strongly-typed entries."""
        return self._operation_history.entries.copy()

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
            "selected_directory": (str(self._selected_directory) if self._selected_directory else None),
            "scanned_files": [f.to_dict() for f in self._scanned_files],
            "file_status_cache": {str(k): v for k, v in self._file_status_cache},
            "metadata_cache": {str(k): MetadataConverter.to_dict(v) for k, v in self._metadata_cache},
            "operation_history": self._operation_history.to_dict(),
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
                metadata_dict = file_data.get("metadata")
                if isinstance(metadata_dict, dict) and metadata_dict:
                    file_item.metadata = MetadataConverter.from_dict(
                        cast(FileMetadataDict, metadata_dict),
                    )
                self._scanned_files.append(file_item)

            # Restore caches
            self._file_status_cache.clear()
            for k, v in state_data.get("file_status_cache", {}).items():
                self._file_status_cache.put(Path(k), v)

            self._metadata_cache.clear()
            metadata_cache = state_data.get("metadata_cache", {})
            if isinstance(metadata_cache, dict):
                for k, v in metadata_cache.items():
                    if isinstance(v, dict):
                        metadata = MetadataConverter.from_dict(
                            cast(FileMetadataDict, v),
                        )
                        self._metadata_cache.put(Path(k), metadata)

            operation_history = state_data.get("operation_history", [])
            if isinstance(operation_history, list):
                typed_history = [cast(OperationHistoryDict, item) for item in operation_history if isinstance(item, dict)]
                self._operation_history = OperationHistory.from_dict_list(typed_history)

            # Emit signals
            self.files_updated.emit(self._scanned_files.copy())

            logger.info("Imported state from: %s", file_path)
            return True

        except (FileNotFoundError, PermissionError):
            logger.exception("Failed to import state: %s", file_path)
            return False
        except OSError:
            logger.exception("Failed to import state: %s", file_path)
            return False
        except json.JSONDecodeError:
            logger.exception("Failed to import state: %s", file_path)
            return False
        except (KeyError, ValueError, TypeError, AttributeError, IndexError):
            logger.exception("Failed to import state: %s", file_path)
            return False
        except Exception as e:  # pylint: disable=broad-exception-caught
            context = ErrorContext(
                file_path=str(file_path),
                operation="import_state",
                additional_data={"error_type": "unexpected"},
            )
            _error = AniVaultError(
                ErrorCode.CONFIG_ERROR,
                f"Unexpected error importing state: {file_path}",
                context,
                original_error=e,
            )
            logger.exception("Failed to import state: %s", file_path)
            return False
