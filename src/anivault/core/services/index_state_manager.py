"""Index state management for tracking file system changes.

This module provides IndexStateManager class for tracking file additions,
modifications, and deletions to enable incremental index updates.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Chunk size for streaming file hash calculation (64KB)
HASH_CHUNK_SIZE = 65536


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


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file content.

    Args:
        file_path: Path to the file

    Returns:
        SHA256 hash as hexadecimal string

    Raises:
        FileNotFoundError: If file doesn't exist
        OSError: If file cannot be read
    """
    sha256_hash = hashlib.sha256()
    try:
        with file_path.open("rb") as f:
            # Read file in chunks to handle large files efficiently
            while chunk := f.read(HASH_CHUNK_SIZE):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except FileNotFoundError:
        logger.exception("File not found for hash calculation: %s", file_path)
        raise
    except OSError as e:
        logger.exception("Error reading file for hash calculation: %s", file_path)
        error_msg = f"Cannot read file for hash: {file_path}"
        raise OSError(error_msg) from e


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
        self.state_file = (
            Path(state_file).resolve() if state_file else self.library_root / "index.state.json"
        )

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
        except (json.JSONDecodeError, KeyError, ValueError) as e:
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
                    except (FileNotFoundError, OSError) as e:
                        logger.warning("Failed to calculate hash for %s: %s", file_path, e)
                        # Continue without hash

                file_state = FileState(
                    path=str(file_path),
                    mtime=mtime,
                    size=size,
                    content_hash=content_hash,
                )
                current_state[str(file_path)] = file_state

            except (OSError, PermissionError) as e:
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
        # Build current state
        current_state: dict[str, FileState] = {}
        current_paths: set[str] = {str(Path(f).resolve()) for f in current_files}

        for file_path in current_files:
            file_path = Path(file_path).resolve()
            file_path_str = str(file_path)

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
                    except (FileNotFoundError, OSError) as e:
                        logger.warning("Failed to calculate hash for %s: %s", file_path, e)
                        # Continue without hash

                file_state = FileState(
                    path=file_path_str,
                    mtime=mtime,
                    size=size,
                    content_hash=content_hash,
                )
                current_state[file_path_str] = file_state

            except (OSError, PermissionError) as e:
                logger.warning("Failed to stat file %s: %s", file_path, e)
                continue

        # Compare with previous state
        previous_paths: set[str] = set(self._previous_state.keys())

        # Find added files (in current but not in previous)
        added: list[FileState] = [
            current_state[path] for path in current_paths - previous_paths if path in current_state
        ]

        # Find removed files (in previous but not in current)
        removed: list[FileState] = [
            self._previous_state[path] for path in previous_paths - current_paths
        ]

        # Find modified files (in both but different)
        modified: list[FileState] = []
        common_paths = current_paths & previous_paths
        for path in common_paths:
            if path not in current_state:
                continue

            current = current_state[path]
            previous = self._previous_state.get(path)

            if previous is None:
                continue

            # Check if file was modified
            # Compare mtime (most reliable indicator)
            # Compare size (backup check)
            # Compare hash if available (most accurate)
            is_modified = (
                current.mtime != previous.mtime
                or current.size != previous.size
                or (
                    current.content_hash is not None
                    and previous.content_hash is not None
                    and current.content_hash != previous.content_hash
                )
            )

            if is_modified:
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

