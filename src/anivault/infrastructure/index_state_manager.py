"""Index state management for tracking file system changes.

S1: Moved from core.services (deprecated) to infrastructure per s0-owner-mapping.
This module provides IndexStateManager class for tracking file additions,
modifications, and deletions to enable incremental index updates.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from anivault.core.subtitle_hash import calculate_file_hash

logger = logging.getLogger(__name__)

__all__ = ["FileChanges", "FileState", "IndexStateManager", "calculate_file_hash"]


@dataclass
class FileState:
    """Represents the state of a single file.

    Attributes:
        path: Absolute path to the file
        mtime: Last modification time (timestamp)
        size: File size in bytes
        content_hash: SHA256 hash of file content (for subtitle files)
    """

    path: str
    mtime: float
    size: int
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert FileState to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileState:
        """Create FileState from dictionary."""
        return cls(
            path=data["path"],
            mtime=data["mtime"],
            size=data["size"],
            content_hash=data.get("content_hash"),
        )


@dataclass
class FileChanges:
    """Represents detected file system changes.

    Attributes:
        added: List of FileState for newly added files
        modified: List of FileState for modified files
        removed: List of FileState for removed files
    """

    added: list[FileState]
    modified: list[FileState]
    removed: list[FileState]

    def total_changes(self) -> int:
        """Get total number of changes."""
        return len(self.added) + len(self.modified) + len(self.removed)

    def is_empty(self) -> bool:
        """Check if there are no changes."""
        return self.total_changes() == 0


class IndexStateManager:
    """Manages file system state for incremental index updates.

    This class tracks file additions, modifications, and deletions by
    maintaining a state file (index.state.json) that stores file metadata
    (path, mtime, size, content hash) and comparing it with the current
    file system state.

    Attributes:
        state_file: Path to the state file (index.state.json)
        library_root: Root directory of the library being tracked
        _previous_state: Dictionary mapping file paths to FileState objects
    """

    def __init__(self, library_root: Path, state_file: Path | None = None) -> None:
        """Initialize IndexStateManager.

        Args:
            library_root: Root directory of the library to track
            state_file: Optional path to state file. If None, uses
                       library_root / "index.state.json"

        Example:
            >>> manager = IndexStateManager(Path("/anime"))
            >>> changes = manager.get_changes([Path("/anime/file1.mkv")])
        """
        self.library_root = Path(library_root).resolve()
        self.state_file = Path(state_file).resolve() if state_file else self.library_root / "index.state.json"

        # Load previous state if state file exists
        self._previous_state: dict[str, FileState] = {}
        self._load_state()

        logger.info(
            "IndexStateManager initialized for library: %s, state file: %s",
            self.library_root,
            self.state_file,
        )

    def _load_state(self) -> None:
        """Load previous state from state file."""
        if not self.state_file.exists():
            logger.debug("State file does not exist, starting with empty state: %s", self.state_file)
            return

        try:
            with self.state_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # Convert dictionary data to FileState objects
            for file_data in data.get("files", []):
                file_state = FileState.from_dict(file_data)
                self._previous_state[file_state.path] = file_state

            logger.debug("Loaded %d file states from %s", len(self._previous_state), self.state_file)
        except (KeyError, ValueError) as e:
            logger.warning(
                "Failed to load state file %s, starting with empty state: %s",
                self.state_file,
                e,
            )
            self._previous_state = {}

    def save_state(self, files: list[Path], calculate_hash: bool = False) -> None:
        """Save current file system state to state file.

        Args:
            files: List of file paths to track
            calculate_hash: If True, calculate content hash for all files.
                          If False, only calculate hash for subtitle files.

        Example:
            >>> manager = IndexStateManager(Path("/anime"))
            >>> files = [Path("/anime/file1.mkv"), Path("/anime/sub1.srt")]
            >>> manager.save_state(files, calculate_hash=True)
        """
        current_state: dict[str, FileState] = {}

        for file_path in files:
            file_path = Path(file_path).resolve()

            if not file_path.exists():
                continue

            try:
                stat = file_path.stat()
                mtime = stat.st_mtime
                size = stat.st_size

                # Calculate hash for subtitle files or if explicitly requested
                content_hash = None
                is_subtitle = file_path.suffix.lower() in {".srt", ".smi", ".ass", ".ssa", ".vtt", ".sub"}
                if calculate_hash or is_subtitle:
                    try:
                        content_hash = calculate_file_hash(file_path)
                    except OSError as e:
                        logger.warning("Failed to calculate hash for %s: %s", file_path, e)
                        # Continue without hash

                file_state = FileState(
                    path=str(file_path),
                    mtime=mtime,
                    size=size,
                    content_hash=content_hash,
                )
                current_state[str(file_path)] = file_state

            except OSError as e:
                logger.warning("Failed to stat file %s: %s", file_path, e)
                continue

        # Save to state file
        try:
            # Ensure parent directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert FileState objects to dictionaries
            files_data = [state.to_dict() for state in current_state.values()]

            state_data = {
                "library_root": str(self.library_root),
                "files": files_data,
            }

            with self.state_file.open("w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            # Update previous state
            self._previous_state = current_state

            logger.info("Saved state for %d files to %s", len(current_state), self.state_file)
        except OSError:
            logger.exception("Failed to save state file %s", self.state_file)
            raise

    def _file_state_for_path(
        self,
        file_path: Path,
        file_path_str: str,
        calculate_hash: bool,
    ) -> FileState | None:
        """Build FileState for a single path; returns None on I/O error."""
        try:
            stat = file_path.stat()
            content_hash = self._content_hash_for_path(file_path, calculate_hash)
            return FileState(
                path=file_path_str,
                mtime=stat.st_mtime,
                size=stat.st_size,
                content_hash=content_hash,
            )
        except OSError as e:
            logger.warning("Failed to stat file %s: %s", file_path, e)
            return None

    def _content_hash_for_path(self, file_path: Path, calculate_hash: bool) -> str | None:
        """Return content hash for path when requested or for subtitle files."""
        subtitle_suffixes = {".srt", ".smi", ".ass", ".ssa", ".vtt", ".sub"}
        if not (calculate_hash or file_path.suffix.lower() in subtitle_suffixes):
            return None
        try:
            return calculate_file_hash(file_path)
        except OSError as e:
            logger.warning("Failed to calculate hash for %s: %s", file_path, e)
            return None

    def _build_current_state(
        self,
        current_files: list[Path],
        calculate_hash: bool,
    ) -> tuple[dict[str, FileState], set[str]]:
        """Build current state dict and set of resolved paths from file list."""
        current_state: dict[str, FileState] = {}
        current_paths: set[str] = {str(Path(f).resolve()) for f in current_files}

        for file_path in current_files:
            file_path = Path(file_path).resolve()
            file_path_str = str(file_path)
            if not file_path.exists():
                continue
            state = self._file_state_for_path(file_path, file_path_str, calculate_hash)
            if state is not None:
                current_state[file_path_str] = state

        return current_state, current_paths

    @staticmethod
    def _is_file_modified(current: FileState, previous: FileState) -> bool:
        """Return True if current state differs from previous (mtime, size, or hash)."""
        if current.mtime != previous.mtime or current.size != previous.size:
            return True
        if current.content_hash is not None and previous.content_hash is not None:
            return current.content_hash != previous.content_hash
        return False

    def get_changes(
        self,
        current_files: list[Path],
        calculate_hash: bool = False,
    ) -> FileChanges:
        """Detect changes between previous state and current file system.

        Args:
            current_files: List of current file paths in the library
            calculate_hash: If True, calculate content hash for comparison.
                          If False, only calculate hash for subtitle files.

        Returns:
            FileChanges object containing added, modified, and removed files

        Example:
            >>> manager = IndexStateManager(Path("/anime"))
            >>> current = [Path("/anime/file1.mkv"), Path("/anime/file2.mkv")]
            >>> changes = manager.get_changes(current)
            >>> print(f"Added: {len(changes.added)}, Modified: {len(changes.modified)}")
        """
        current_state, current_paths = self._build_current_state(current_files, calculate_hash)
        previous_paths: set[str] = set(self._previous_state.keys())

        added: list[FileState] = [current_state[path] for path in current_paths - previous_paths if path in current_state]
        removed: list[FileState] = [self._previous_state[path] for path in previous_paths - current_paths]

        modified: list[FileState] = []
        for path in current_paths & previous_paths:
            current = current_state.get(path)
            previous = self._previous_state.get(path)
            if current is not None and previous is not None and self._is_file_modified(current, previous):
                modified.append(current)

        changes = FileChanges(added=added, modified=modified, removed=removed)
        logger.info(
            "Detected changes: %d added, %d modified, %d removed",
            len(changes.added),
            len(changes.modified),
            len(changes.removed),
        )
        return changes

    def clear_state(self) -> None:
        """Clear the saved state."""
        if self.state_file.exists():
            try:
                self.state_file.unlink()
                logger.info("Cleared state file: %s", self.state_file)
            except OSError as e:
                logger.warning("Failed to delete state file %s: %s", self.state_file, e)

        self._previous_state = {}
